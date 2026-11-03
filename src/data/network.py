"""Processed park walking network: lengths, eligibility, statistics and road features.

Lengths are geometry lengths in EPSG:2193 (km), precomputed by
scripts/preprocess_park_walking_network.py. Classification (highway_category,
pedestrian_access) is read as stored and is never recomputed here.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import shapely
from shapely.geometry import mapping

HIGHWAY_CATEGORIES: tuple[str, ...] = (
    "Walking paths", "Nature trails", "Shared-use paths", "Local roads", "Major roads",
)
ACCESS_CLASSES: tuple[str, ...] = ("Walkable", "Conditional", "Restricted")
SOURCE_CRS_EPSG = 2193
DISPLAY_CRS = "EPSG:4326"
COORDINATE_PRECISION = 1e-6
PARK_ID_FIELD = "GlobalID"

STATS_COLUMNS = {"park_id", "highway_category", "pedestrian_access", "feature_count", "length_km"}
FEATURE_COLUMNS = [PARK_ID_FIELD, "highway_category", "pedestrian_access", "length_km"]
COLUMN_PAIRS = pd.MultiIndex.from_product([HIGHWAY_CATEGORIES, ACCESS_CLASSES], names=["highway_category", "pedestrian_access"])


@dataclass(frozen=True)
class RoadFilter:
    """An applied or draft Road Filter selection (immutable, so it is safe to share between states)."""

    categories: frozenset[str]
    access: frozenset[str]

    @property
    def is_valid(self) -> bool:
        return bool(self.categories) and bool(self.access)

    @property
    def columns(self) -> list[tuple[str, str]]:
        return [
            (category, access)
            for category in HIGHWAY_CATEGORIES if category in self.categories
            for access in ACCESS_CLASSES if access in self.access
        ]


def make_road_filter(categories: Iterable[str], access: Iterable[str]) -> RoadFilter:
    categories, access = frozenset(categories), frozenset(access)
    unknown = (categories - set(HIGHWAY_CATEGORIES)) | (access - set(ACCESS_CLASSES))
    if unknown:
        raise ValueError(f"Unknown road filter values: {', '.join(sorted(unknown))}")
    return RoadFilter(categories, access)


DEFAULT_ROAD_FILTER = RoadFilter(frozenset(HIGHWAY_CATEGORIES), frozenset({"Walkable"}))


def load_network_stats(path: Path) -> pd.DataFrame:
    """Read the pre-aggregated Parquet statistics and validate its schema and vocabulary."""
    stats = pd.read_parquet(path)
    missing = STATS_COLUMNS - set(stats.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}")
    if stats[["park_id", "highway_category", "pedestrian_access", "length_km"]].isna().any().any():
        raise ValueError(f"{path} contains null keys or lengths")
    if (stats["length_km"] < 0).any():
        raise ValueError(f"{path} contains negative lengths")
    for column, vocabulary in (("highway_category", HIGHWAY_CATEGORIES), ("pedestrian_access", ACCESS_CLASSES)):
        unknown = set(stats[column]) - set(vocabulary)
        if unknown:
            raise ValueError(f"{path} has unexpected {column} values: {', '.join(sorted(map(str, unknown)))}")
    if stats.duplicated(["park_id", "highway_category", "pedestrian_access"]).any():
        raise ValueError(f"{path} has duplicate park/category/access rows")
    return stats


def build_length_table(stats: pd.DataFrame, park_ids: Iterable[str]) -> pd.DataFrame:
    """Dense km table: one row per park, one column per (highway_category, pedestrian_access).

    Parks with no network rows get zeros. Statistics for unknown parks are an error, not silently dropped.
    """
    park_ids = pd.Index([str(park_id) for park_id in park_ids], name="park_id")
    unknown = set(stats["park_id"].astype(str)) - set(park_ids)
    if unknown:
        raise ValueError(f"{len(unknown)} statistics park_ids are not in the park dataset, e.g. {sorted(unknown)[:3]}")
    table = (
        stats.assign(park_id=stats["park_id"].astype(str))
        .pivot_table(index="park_id", columns=["highway_category", "pedestrian_access"], values="length_km", aggfunc="sum")
        .reindex(index=park_ids, columns=COLUMN_PAIRS)
        .fillna(0.0)
    )
    return table


def selected_lengths(table: pd.DataFrame, road: RoadFilter) -> pd.Series:
    """Selected network length (km) per park for a Road Filter selection."""
    columns = road.columns
    if not columns:
        return pd.Series(0.0, index=table.index)
    return table.loc[:, columns].sum(axis=1)


def walking_minutes(length_km: float | pd.Series, speed_kmh: float) -> float | pd.Series:
    return length_km / speed_kmh * 60


def eligible_park_ids(lengths: pd.Series, speed_kmh: float, threshold_minutes: float) -> set[str]:
    """Parks whose walking time is strictly greater than the minimum walking time."""
    if speed_kmh <= 0:
        return set()
    return set(lengths.index[walking_minutes(lengths, speed_kmh) > threshold_minutes])


def matching_park_ids(
    parks: Iterable[Mapping[str, Any]],
    lengths: pd.Series,
    area: str,
    speed_kmh: float,
    threshold_minutes: float,
) -> list[str]:
    """Park ids inside the area ("all" or a Local Board name) with walking time strictly above the threshold.

    Mirrors the application's scope rule: area == "all" or park["local_board"] == area.
    """
    if speed_kmh <= 0:
        return []
    return [
        park["id"] for park in parks
        if (area == "all" or park["local_board"] == area)
        and park["id"] in lengths.index
        and lengths[park["id"]] / speed_kmh * 60 > threshold_minutes
    ]


@dataclass(frozen=True)
class NetworkData:
    """Processed walking-network data, loaded once at startup and shared read-only."""

    length_table: pd.DataFrame
    features_by_park: dict[str, tuple[dict[str, Any], ...]]


def load_network_data(stats_path: Path, features_path: Path, park_ids: Iterable[str]) -> NetworkData:
    """Load and cross-validate both processed datasets against the application's park ids.

    Raises FileNotFoundError, OSError or ValueError so the caller can fall back gracefully.
    """
    park_ids = [str(park_id) for park_id in park_ids]
    for path in (stats_path, features_path):
        if not Path(path).exists():
            raise FileNotFoundError(f"Processed network file not found: {path}")
    stats = load_network_stats(stats_path)
    table = build_length_table(stats, park_ids)
    features = load_network_features(features_path)
    unknown = set(features) - set(park_ids)
    if unknown:
        raise ValueError(f"{len(unknown)} network features reference unknown park ids, e.g. {sorted(unknown)[:3]}")
    if set(features) != set(stats["park_id"].astype(str)):
        raise ValueError("GeoPackage and Parquet cover different parks")
    feature_total = sum(len(group) for group in features.values())
    if feature_total != int(stats["feature_count"].sum()):
        raise ValueError(f"Feature count mismatch: GeoPackage {feature_total} vs Parquet {int(stats['feature_count'].sum())}")
    return NetworkData(table, features)


@dataclass(frozen=True)
class NetworkSummary:
    total_km: float
    by_access: dict[str, float]
    by_category: dict[str, float]


def summarise(table: pd.DataFrame, park_ids: Iterable[str], road: RoadFilter) -> NetworkSummary:
    """Both chart breakdowns come from one filtered slice, so they share the same total."""
    ids = [park_id for park_id in dict.fromkeys(map(str, park_ids)) if park_id in table.index]
    columns = road.columns
    by_access = dict.fromkeys(ACCESS_CLASSES, 0.0)
    by_category = dict.fromkeys(HIGHWAY_CATEGORIES, 0.0)
    if ids and columns:
        totals = table.loc[ids, columns].sum()
        for (category, access), value in totals.items():
            by_access[access] += float(value)
            by_category[category] += float(value)
    return NetworkSummary(sum(by_access.values()), by_access, by_category)


def shares(values: Mapping[str, float], total: float) -> dict[str, float]:
    """Percentages of a shared denominator; empty when there is nothing to show."""
    if total <= 0:
        return {}
    return {key: value / total * 100 for key, value in values.items()}


def load_network_features(path: Path, layer: str = "park_walking_network") -> dict[str, tuple[dict[str, Any], ...]]:
    """Read the processed GeoPackage once; return GeoJSON-like features grouped by park id (EPSG:4326)."""
    frame = gpd.read_file(path, layer=layer, columns=FEATURE_COLUMNS, engine="pyogrio")
    if frame.crs is None or frame.crs.to_epsg() != SOURCE_CRS_EPSG:
        raise ValueError(f"{path} layer {layer} must be EPSG:{SOURCE_CRS_EPSG}, found {frame.crs}")
    if frame[PARK_ID_FIELD].isna().any():
        raise ValueError(f"{path} has road features without {PARK_ID_FIELD}")
    for column, vocabulary in (("highway_category", HIGHWAY_CATEGORIES), ("pedestrian_access", ACCESS_CLASSES)):
        unknown = set(frame[column].dropna()) - set(vocabulary)
        if frame[column].isna().any() or unknown:
            raise ValueError(f"{path} has missing or unexpected {column} values")
    frame = frame.to_crs(DISPLAY_CRS)
    geometries = shapely.set_precision(frame.geometry.to_numpy(), COORDINATE_PRECISION)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for park_id, category, access, geometry in zip(
        frame[PARK_ID_FIELD].astype(str), frame["highway_category"], frame["pedestrian_access"], geometries
    ):
        grouped.setdefault(park_id, []).append({
            "type": "Feature",
            "properties": {"GlobalID": park_id, "highway_category": category, "pedestrian_access": access},
            "geometry": mapping(geometry),
        })
    return {park_id: tuple(features) for park_id, features in grouped.items()}


def feature_collection(
    features_by_park: Mapping[str, Sequence[dict[str, Any]]],
    park_ids: Iterable[str],
    road: RoadFilter,
    style_for: Callable[[str, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """GeoJSON FeatureCollection of the selected roads for the given parks only.

    A per-feature style is embedded in properties.style so ipyleaflet does not need a Python style callback.
    """
    features = []
    for park_id in dict.fromkeys(map(str, park_ids)):
        for feature in features_by_park.get(park_id, ()):
            properties = feature["properties"]
            category, access = properties["highway_category"], properties["pedestrian_access"]
            if category not in road.categories or access not in road.access:
                continue
            if style_for is None:
                features.append(feature)
            else:
                features.append({**feature, "properties": {**properties, "style": style_for(category, access)}})
    return {"type": "FeatureCollection", "features": features}
