
import geopandas as gpd
import pandas as pd
from pathlib import Path

parks = gpd.read_file(
    "data/02processed/parks_with_localboard.gpkg",
    layer="parks"
)

network = gpd.read_file(
    "data/01raw/road_network_in_parks_filtered.gpkg"
)

# Keep only duplicated non-null SAPIDs
duplicate_ids = (
    parks.loc[parks["SAPID"].notna(), "SAPID"]
    .value_counts()
)

duplicate_ids = duplicate_ids[
    duplicate_ids > 1
].index.tolist()

duplicate_parks = parks[
    parks["SAPID"].isin(duplicate_ids)
].copy()

# --------------------------------------------------
# 1. Summary for each duplicated SAPID
# --------------------------------------------------

summary = (
    duplicate_parks
    .groupby("SAPID")
    .agg(
        record_count=("GlobalID", "count"),
        board=("LOCALBOARD_OFFICIAL", "first"),
        total_polygon_area_km2=("area_km2", "sum"),
        unique_sites=("SITE", "nunique")
    )
    .reset_index()
)

network_summary = (
    network[network["SAPID"].isin(duplicate_ids)]
    .groupby("SAPID")
    .agg(
        network_segments=("SAPID", "size"),
        network_length_km=("length_km", "sum")
    )
    .reset_index()
)

summary = summary.merge(
    network_summary,
    on="SAPID",
    how="left"
)

print("\n--- DUPLICATE SAPID SUMMARY ---")
print(summary.to_string(index=False))


# --------------------------------------------------
# 2. Inspect individual park polygons
# --------------------------------------------------

print("\n--- INDIVIDUAL PARK RECORDS ---")

print(
    duplicate_parks[
        [
            "SAPID",
            "GlobalID",
            "SITE",
            "area_km2",
            "LOCALBOARD_OFFICIAL",
            "geometry"
        ]
    ][
        [
            "SAPID",
            "GlobalID",
            "SITE",
            "area_km2",
            "LOCALBOARD_OFFICIAL"
        ]
    ].to_string(index=False)
)


# --------------------------------------------------
# 3. Calculate pairwise polygon overlap
# --------------------------------------------------

overlap_results = []

for sapid, group in duplicate_parks.groupby("SAPID"):

    records = list(group.iterrows())

    for i in range(len(records)):
        idx_a, park_a = records[i]

        for j in range(i + 1, len(records)):
            idx_b, park_b = records[j]

            geom_a = park_a.geometry
            geom_b = park_b.geometry

            if (
                geom_a is None or geom_a.is_empty
                or geom_b is None or geom_b.is_empty
            ):
                continue

            if not geom_a.is_valid:
                geom_a = geom_a.make_valid()

            if not geom_b.is_valid:
                geom_b = geom_b.make_valid()

            overlap_area = geom_a.intersection(
                geom_b
            ).area

            overlap_results.append({
                "SAPID": sapid,
                "GlobalID_A": park_a["GlobalID"],
                "GlobalID_B": park_b["GlobalID"],
                "overlap_area_m2": overlap_area
            })

overlap_df = pd.DataFrame(overlap_results)

print("\n--- PAIRWISE POLYGON OVERLAP ---")
print(overlap_df.to_string(index=False))


# --------------------------------------------------
# 4. Save diagnostic outputs
# --------------------------------------------------

output_dir = Path("outputs/data_validation")
output_dir.mkdir(parents=True, exist_ok=True)

summary.to_csv(
    output_dir / "duplicate_sapid_summary.csv",
    index=False
)

overlap_df.to_csv(
    output_dir / "duplicate_sapid_overlap.csv",
    index=False
)

print("\nDiagnostic reports saved.")
