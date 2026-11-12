from math import isclose
from pathlib import Path
from unittest import SkipTest
from unittest.mock import patch

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString

from src.data.network import (
    ACCESS_CLASSES,
    DEFAULT_ROAD_FILTER,
    HIGHWAY_CATEGORIES,
    build_length_table,
    eligible_park_ids,
    feature_collection,
    load_network_data,
    load_network_features,
    load_network_stats,
    matching_park_ids,
    make_road_filter,
    selected_lengths,
    shares,
    summarise,
    walking_minutes,
)

STATS = pd.DataFrame(
    [
        ("A", "Walking paths", "Walkable", 3, 1.0),
        ("A", "Walking paths", "Restricted", 1, 0.5),
        ("A", "Local roads", "Conditional", 2, 0.25),
        ("B", "Nature trails", "Walkable", 4, 2.0),
        ("B", "Major roads", "Walkable", 1, 1.0),
    ],
    columns=["park_id", "highway_category", "pedestrian_access", "feature_count", "length_km"],
)
PARKS = ["A", "B", "C"]
EVERYTHING = make_road_filter(HIGHWAY_CATEGORIES, ACCESS_CLASSES)


def make_table():
    return build_length_table(STATS, PARKS)


def raises_value_error(call):
    try:
        call()
    except ValueError:
        return True
    return False


def test_default_filter_is_all_categories_and_walkable_only():
    assert DEFAULT_ROAD_FILTER.categories == frozenset(HIGHWAY_CATEGORIES)
    assert DEFAULT_ROAD_FILTER.access == frozenset({"Walkable"})


def test_table_is_dense_with_zero_for_parks_without_network():
    table = make_table()
    assert list(table.index) == PARKS
    assert table.shape == (3, len(HIGHWAY_CATEGORIES) * len(ACCESS_CLASSES))
    assert table.loc["C"].sum() == 0
    assert isclose(table.values.sum(), STATS["length_km"].sum())


def test_statistics_for_unknown_parks_are_rejected():
    assert raises_value_error(lambda: build_length_table(STATS, ["A"]))


def test_selected_lengths_follow_road_filter():
    table = make_table()
    assert selected_lengths(table, DEFAULT_ROAD_FILTER).to_dict() == {"A": 1.0, "B": 3.0, "C": 0.0}
    assert selected_lengths(table, EVERYTHING).to_dict() == {"A": 1.75, "B": 3.0, "C": 0.0}
    only_local = make_road_filter(["Local roads"], ["Conditional"])
    assert selected_lengths(table, only_local).to_dict() == {"A": 0.25, "B": 0.0, "C": 0.0}


def test_walking_time_threshold_is_strictly_greater():
    lengths = pd.Series({"exact": 1.0, "over": 1.01, "under": 0.5, "none": 0.0})
    assert walking_minutes(1.0, 4) == 15.0
    assert eligible_park_ids(lengths, 4, 15) == {"over"}
    assert eligible_park_ids(lengths, 0, 1) == set()


def test_changing_road_filter_changes_eligibility():
    table = make_table()
    assert eligible_park_ids(selected_lengths(table, DEFAULT_ROAD_FILTER), 4, 20) == {"B"}
    assert eligible_park_ids(selected_lengths(table, EVERYTHING), 4, 20) == {"A", "B"}


def test_both_charts_share_one_denominator():
    road = make_road_filter(HIGHWAY_CATEGORIES, ["Walkable", "Restricted"])
    summary = summarise(make_table(), ["A", "B"], road)
    assert isclose(summary.total_km, 4.5)
    assert isclose(sum(summary.by_access.values()), summary.total_km)
    assert isclose(sum(summary.by_category.values()), summary.total_km)
    assert summary.by_access["Conditional"] == 0
    assert isclose(sum(shares(summary.by_access, summary.total_km).values()), 100)
    assert isclose(sum(shares(summary.by_category, summary.total_km).values()), 100)


def test_summary_only_counts_the_given_parks():
    table = make_table()
    assert isclose(summarise(table, ["A"], DEFAULT_ROAD_FILTER).total_km, 1.0)
    assert summarise(table, [], DEFAULT_ROAD_FILTER).total_km == 0
    assert shares({"Walkable": 0.0}, 0) == {}


def test_invalid_filter_values_are_rejected():
    assert raises_value_error(lambda: make_road_filter(["Motorways"], ["Walkable"]))
    assert not make_road_filter([], ["Walkable"]).is_valid


def _feature(park_id, category, access):
    return {
        "type": "Feature",
        "properties": {"GlobalID": park_id, "highway_category": category, "pedestrian_access": access},
        "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
    }


def test_feature_collection_is_scoped_to_parks_and_filter_with_style():
    features = {
        "A": (_feature("A", "Walking paths", "Walkable"), _feature("A", "Walking paths", "Restricted")),
        "B": (_feature("B", "Local roads", "Walkable"),),
    }
    collection = feature_collection(features, ["A"], DEFAULT_ROAD_FILTER, lambda c, a: {"color": c})
    assert len(collection["features"]) == 1
    properties = collection["features"][0]["properties"]
    assert properties["GlobalID"] == "A" and properties["style"] == {"color": "Walking paths"}
    assert "style" not in features["A"][0]["properties"]
    assert feature_collection(features, [], DEFAULT_ROAD_FILTER)["features"] == []
    assert len(feature_collection(features, ["A", "B", "A"], EVERYTHING)["features"]) == 3


def test_network_features_use_fiona_in_pyodide():
    frame = gpd.GeoDataFrame(
        [{"GlobalID": "A", "highway_category": "Walking paths", "pedestrian_access": "Walkable",
          "length_km": 1.0, "geometry": LineString([(1740000, 5920000), (1740001, 5920001)])}],
        crs="EPSG:2193",
    )
    with patch("src.data.network.sys.platform", "emscripten"), patch(
        "src.data.network.gpd.read_file", return_value=frame
    ) as read_file:
        features = load_network_features(Path("network.gpkg"))
    assert read_file.call_args.kwargs["engine"] == "fiona"
    assert features["A"][0]["properties"]["GlobalID"] == "A"
    assert features["A"][0]["geometry"]["type"] == "LineString"


def test_road_line_style_maps_category_to_colour_and_access_to_dash():
    from src.ui.network_charts import CATEGORY_COLORS, road_line_style

    assert CATEGORY_COLORS == {
        "Walking paths": "#287A55", "Nature trails": "#D99A27", "Shared-use paths": "#258A9B",
        "Local roads": "#6476A5", "Major roads": "#C65D4B",
    }
    styles = {(c, a): road_line_style(c, a) for c in HIGHWAY_CATEGORIES for a in ACCESS_CLASSES}
    assert all(styles[(c, a)]["color"] == CATEGORY_COLORS[c] for c, a in styles)
    assert len({styles[(c, a)]["dashArray"] for c, a in styles if a == "Conditional"}) == 1
    dashes = {a: styles[("Nature trails", a)]["dashArray"] for a in ACCESS_CLASSES}
    assert dashes["Walkable"] == "" and len(set(dashes.values())) == 3
    assert all(style["interactive"] is False for style in styles.values())


def test_details_filter_is_independent_of_applied_filter():
    applied = make_road_filter(["Walking paths"], ["Walkable"])
    details = make_road_filter(HIGHWAY_CATEGORIES, ACCESS_CLASSES)
    assert applied.categories == frozenset({"Walking paths"})
    assert details != applied


STATS_PATH = Path("data/02processed/park_network_statistics.parquet")
FEATURES_PATH = Path("data/02processed/park_walking_network.gpkg")
PARKS_PATH = Path("data/02processed/parks_with_localboard.gpkg")


def require_processed_data():
    missing = [str(path) for path in (STATS_PATH, FEATURES_PATH, PARKS_PATH) if not path.exists()]
    if missing:
        raise SkipTest(f"processed data not available: {missing}")


def real_park_records():
    """Park records with the same id and local_board fields the application builds in load_real_data."""
    import geopandas as gpd

    parks = gpd.read_file(PARKS_PATH, layer="parks", columns=["GlobalID", "LOCALBOARD_OFFICIAL", "path_length_km"], ignore_geometry=True)
    return [
        {
            "id": str(row.GlobalID),
            "local_board": str(row.LOCALBOARD_OFFICIAL) if pd.notna(row.LOCALBOARD_OFFICIAL) else "",
            "length": row.path_length_km,
        }
        for row in parks.itertuples()
    ]


def test_processed_statistics_match_preprocessing_report():
    require_processed_data()
    stats = load_network_stats(STATS_PATH)
    table = build_length_table(stats, stats["park_id"].unique())
    assert isclose(selected_lengths(table, EVERYTHING).sum(), 2512.454, abs_tol=1e-3)
    assert isclose(selected_lengths(table, DEFAULT_ROAD_FILTER).sum(), 2204.915, abs_tol=1e-3)


def test_default_eligibility_counts_on_real_data():
    require_processed_data()
    parks = real_park_records()
    data = load_network_data(STATS_PATH, FEATURES_PATH, [park["id"] for park in parks])
    lengths = selected_lengths(data.length_table, DEFAULT_ROAD_FILTER)
    assert len(matching_park_ids(parks, lengths, "all", 4, 10)) == 643
    assert len(matching_park_ids(parks, lengths, "all", 3, 30)) == 283
    # The Local Board scope is a subset of All Auckland.
    board = next(park["local_board"] for park in parks if park["local_board"])
    in_board = set(matching_park_ids(parks, lengths, board, 4, 10))
    assert in_board and in_board <= set(matching_park_ids(parks, lengths, "all", 4, 10))
    assert all(park["local_board"] == board for park in parks if park["id"] in in_board)


def test_legacy_lengths_remain_unchanged_for_comparison():
    require_processed_data()
    parks = real_park_records()
    legacy = pd.Series({park["id"]: park["length"] for park in parks}).fillna(-1)
    assert len(matching_park_ids(parks, legacy, "all", 4, 10)) == 647
    assert len(matching_park_ids(parks, legacy, "all", 3, 30)) == 286


def test_load_network_data_rejects_bad_inputs_and_missing_files():
    require_processed_data()
    ids = [park["id"] for park in real_park_records()]
    assert raises_value_error(lambda: load_network_data(STATS_PATH, FEATURES_PATH, ids[:10]))
    missing = Path("data/02processed/does_not_exist.parquet")
    try:
        load_network_data(missing, FEATURES_PATH, ids)
    except FileNotFoundError:
        return
    raise AssertionError("expected FileNotFoundError")


def test_matching_park_ids_uses_strict_threshold_and_ignores_unknown_parks():
    parks = [{"id": "a", "local_board": "X"}, {"id": "b", "local_board": "Y"}, {"id": "z", "local_board": "X"}]
    lengths = pd.Series({"a": 1.0, "b": 1.0})
    assert matching_park_ids(parks, lengths, "all", 4, 15) == []
    assert matching_park_ids(parks, lengths, "X", 4, 14.9) == ["a"]
    assert matching_park_ids(parks, lengths, "all", 0, 1) == []

