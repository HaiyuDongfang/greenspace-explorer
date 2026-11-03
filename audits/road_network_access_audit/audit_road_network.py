"""Read-only audit of pedestrian access and walkability tags in the park-road GPKG."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "data" / "01raw" / "road_network_in_parks_auckland_overlay.gpkg"
OUTPUT_DIR = Path(__file__).resolve().parent
TAG_COLUMNS = ("access", "foot", "highway", "service", "bicycle", "motor_vehicle")

PUBLIC = {"yes", "designated"}
CONDITIONAL = {"permissive", "customers"}
RESTRICTED = {"no", "private", "use_sidepath"}
ACCESS_PUBLIC = {"yes", "foot"}
ACCESS_CONDITIONAL = {"permissive", "destination", "customers", "permit", "forestry", "tidal", "emergency"}
ACCESS_RESTRICTED = {"no", "private"}

PEDESTRIAN_ORIENTED = {"footway", "path", "steps", "pedestrian", "track", "bridleway"}
SHARED_ROAD = {"service", "residential", "living_street", "unclassified", "tertiary", "secondary", "primary"}
CYCLEWAY = {"cycleway"}
MOTOR_HIGHWAY = {"motorway", "motorway_link", "trunk", "trunk_link"}
SPECIAL_HIGHWAY = {"corridor", "via_ferrata", "busway", "primary_link", "secondary_link"}


def normalize_tag(series: pd.Series) -> pd.Series:
    """Normalize tag text for comparisons while leaving source columns untouched."""
    return series.astype("string").str.strip().str.lower().replace("", pd.NA)


def classify_access(foot: object, access: object) -> tuple[str, str]:
    """Resolve pedestrian access; a present foot tag always takes precedence."""
    if pd.notna(foot):
        value = str(foot)
        if value in PUBLIC:
            return "Public", "foot"
        if value in CONDITIONAL:
            return "Conditional", "foot"
        if value in RESTRICTED:
            return "Restricted", "foot"
        return "Unspecified", "unrecognized foot value"

    if pd.isna(access):
        return "Unspecified", "both tags missing"
    value = str(access)
    if value in ACCESS_PUBLIC:
        return "Public", "access"
    if value in ACCESS_CONDITIONAL:
        return "Conditional", "access"
    if value in ACCESS_RESTRICTED:
        return "Restricted", "access"
    return "Unspecified", "unrecognized access value"


def classify_walkability(highway: object, access_class: str, foot: object) -> str:
    """Classify pedestrian suitability conservatively, separately from legal access."""
    if access_class == "Restricted":
        return "Restricted by pedestrian-access tag"

    if highway in MOTOR_HIGHWAY:
        if pd.notna(foot) and str(foot) in PUBLIC | CONDITIONAL:
            return "Uncertain: pedestrian permission on motor-highway"
        return "Not pedestrian-suitable highway"

    if highway in SPECIAL_HIGHWAY:
        return "Uncertain: specialist or link highway"

    if highway in CYCLEWAY:
        if access_class == "Conditional":
            return "Conditional or purpose-limited"
        if access_class == "Public":
            return "Walkable: pedestrian access explicit"
        return "Uncertain: cycleway access unspecified"

    if highway in PEDESTRIAN_ORIENTED:
        if access_class == "Conditional":
            return "Conditional or purpose-limited"
        if access_class == "Public":
            return "Walkable: pedestrian-oriented highway"
        return "Potential: pedestrian-oriented type, access unspecified"

    if highway in SHARED_ROAD:
        if access_class == "Conditional":
            return "Conditional or purpose-limited"
        if access_class == "Public":
            return "Walkable: shared-road highway"
        return "Potential: road-like type, access unspecified"

    return "Uncertain: unrecognized highway"


def display_tag(value: object) -> str:
    return "(missing)" if pd.isna(value) else str(value)


def grouped_summary(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    return (
        frame.groupby(column, dropna=False)
        .agg(features=("geometry_length_km", "size"), length_km=("geometry_length_km", "sum"))
        .sort_values(["length_km", "features"], ascending=False)
        .reset_index()
    )


def write_tag_value_counts(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in TAG_COLUMNS:
        summary = grouped_summary(frame, f"{column}_normalized")
        for item in summary.itertuples(index=False):
            rows.append(
                {
                    "field": column,
                    "value": display_tag(item[0]),
                    "features": int(item.features),
                    "geometry_length_km": item.length_km,
                }
            )
    result = pd.DataFrame(rows)
    result.to_csv(OUTPUT_DIR / "tag_value_counts.csv", index=False, float_format="%.6f")
    return result


def write_conflicts(frame: pd.DataFrame) -> pd.DataFrame:
    foot_status = frame["foot_normalized"].map(
        lambda value: classify_access(value, pd.NA)[0] if pd.notna(value) else pd.NA
    )
    access_status = frame["access_normalized"].map(
        lambda value: classify_access(pd.NA, value)[0] if pd.notna(value) else pd.NA
    )
    conflicts = frame[
        frame["foot_normalized"].notna()
        & frame["access_normalized"].notna()
        & foot_status.fillna("").ne(access_status.fillna(""))
    ].copy()
    conflicts["foot_tag_access_class"] = foot_status.loc[conflicts.index]
    conflicts["general_access_class"] = access_status.loc[conflicts.index]
    columns = [
        "audit_row_number", "id", "osm_type", "DESCRIPTION", "highway_normalized", "foot_normalized",
        "access_normalized", "foot_tag_access_class", "general_access_class",
        "geometry_length_km",
    ]
    conflicts[columns].to_csv(OUTPUT_DIR / "foot_access_conflicts.csv", index=False, float_format="%.6f")
    return conflicts


def write_review_examples(frame: pd.DataFrame) -> pd.DataFrame:
    flags = {
        "foot_use_sidepath": frame["foot_normalized"].eq("use_sidepath"),
        "foot_access_conflict": frame["tag_conflict"],
        "cycleway_access_unspecified": (
            frame["highway_normalized"].eq("cycleway")
            & frame["pedestrian_access"].eq("Unspecified")
        ),
        "special_or_link_highway": frame["highway_normalized"].isin(SPECIAL_HIGHWAY | MOTOR_HIGHWAY),
        "unrecognized_highway": ~frame["highway_normalized"].isin(
            PEDESTRIAN_ORIENTED | SHARED_ROAD | CYCLEWAY | MOTOR_HIGHWAY | SPECIAL_HIGHWAY
        ),
    }
    columns = [
        "audit_flag", "audit_row_number", "id", "osm_type", "DESCRIPTION", "highway_normalized",
        "service_normalized", "foot_normalized", "access_normalized",
        "bicycle_normalized", "motor_vehicle_normalized", "pedestrian_access",
        "walkability", "geometry_length_km",
    ]
    examples = []
    for flag, mask in flags.items():
        examples.append(frame.loc[mask].head(5).assign(audit_flag=flag)[columns])
    result = pd.concat(examples, ignore_index=True) if examples else pd.DataFrame(columns=columns)
    result.to_csv(OUTPUT_DIR / "review_examples.csv", index=False, float_format="%.6f")
    return result


def write_combo_summaries(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    service_combinations = (
        frame.groupby(["highway_normalized", "service_normalized"], dropna=False)
        .agg(features=("geometry_length_km", "size"), length_km=("geometry_length_km", "sum"))
        .reset_index()
        .sort_values(["features", "length_km"], ascending=False)
    )
    service_combinations = service_combinations.rename(
        columns={"highway_normalized": "highway", "service_normalized": "service"}
    )
    service_combinations.to_csv(
        OUTPUT_DIR / "highway_service_combinations.csv", index=False, float_format="%.6f"
    )

    highway_review = frame[
        frame["highway_normalized"].isin(CYCLEWAY | MOTOR_HIGHWAY | SPECIAL_HIGHWAY)
    ]
    review_summary = (
        highway_review.groupby(["highway_normalized", "pedestrian_access", "walkability"], dropna=False)
        .agg(features=("geometry_length_km", "size"), length_km=("geometry_length_km", "sum"))
        .reset_index()
        .sort_values(["features", "length_km"], ascending=False)
    )
    review_summary = review_summary.rename(columns={"highway_normalized": "highway"})
    review_summary.to_csv(OUTPUT_DIR / "highway_review_summary.csv", index=False, float_format="%.6f")
    return service_combinations, review_summary


def markdown_table(frame: pd.DataFrame, columns: list[str], headers: list[str] | None = None) -> str:
    selected = frame[columns].copy()
    if headers:
        selected.columns = headers

    def format_cell(value: object) -> str:
        if pd.isna(value):
            return "(missing)"
        if isinstance(value, float):
            return f"{value:.3f}"
        return str(value).replace("|", "\\|").replace("\n", " ")

    header = list(selected.columns)
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    lines.extend(
        "| " + " | ".join(format_cell(value) for value in row) + " |"
        for row in selected.itertuples(index=False, name=None)
    )
    return "\n".join(lines)


def write_report(
    source: Path,
    frame: pd.DataFrame,
    info: dict,
    tag_values: pd.DataFrame,
    conflicts: pd.DataFrame,
) -> None:
    tag_sections = []
    for column in TAG_COLUMNS:
        values = tag_values[tag_values["field"].eq(column)]
        tag_sections.append(
            f"### `{column}`\n\n"
            + markdown_table(values, ["value", "features", "geometry_length_km"], ["Value", "Features", "Geometry length (km)"])
        )

    by_highway = grouped_summary(frame, "highway_normalized").rename(columns={"highway_normalized": "highway"})
    by_access = grouped_summary(frame, "access_normalized").rename(columns={"access_normalized": "access"})
    for table, field in ((by_highway, "highway"), (by_access, "access")):
        table[field] = table[field].map(display_tag)
    access_classes = grouped_summary(frame, "pedestrian_access")
    walkability = grouped_summary(frame, "walkability")
    combo = (
        frame.groupby(["foot_normalized", "access_normalized", "highway_normalized"], dropna=False)
        .agg(features=("geometry_length_km", "size"), length_km=("geometry_length_km", "sum"))
        .sort_values(["features", "length_km"], ascending=False)
        .head(25)
        .reset_index()
    )
    for column in ("foot_normalized", "access_normalized", "highway_normalized"):
        combo[column] = combo[column].map(display_tag)

    missing = pd.DataFrame(
        [
            {"field": column, "missing_features": int(frame[f"{column}_normalized"].isna().sum())}
            for column in TAG_COLUMNS
        ]
    )
    geometry_length = frame["geometry_length_km"].sum()
    stored_length_total = pd.to_numeric(frame["length"], errors="coerce").sum()
    repeated_ids = int(frame["id"].duplicated(keep=False).sum())
    repeated_id_values = int(frame.loc[frame["id"].duplicated(keep=False), "id"].nunique())
    duplicate_geometry_rows = int(frame.geometry.to_wkb().duplicated(keep=False).sum())
    duplicate_geometry_groups = int(frame.geometry.to_wkb().value_counts().gt(1).sum())
    max_length_difference_m = frame["length_difference_m"].abs().max()
    invalid = int((~frame.geometry.is_valid).sum())
    null_geometry = int(frame.geometry.isna().sum())
    empty_geometry = int(frame.geometry.is_empty.sum())
    foot_no = int(frame["foot_normalized"].eq("no").sum())
    foot_no_km = frame.loc[frame["foot_normalized"].eq("no"), "geometry_length_km"].sum()

    service_combinations, review_summary = write_combo_summaries(frame)
    for column in ("highway", "service"):
        service_combinations[column] = service_combinations[column].map(display_tag)
    review_summary["highway"] = review_summary["highway"].map(display_tag)

    content = f"""# Auckland park road network access audit

## Scope and method

- Source: `{source.relative_to(ROOT) if source.is_relative_to(ROOT) else source.name}`
- Source SHA-256: `{hashlib.sha256(source.read_bytes()).hexdigest()}`
- GeoPackage layer: `{info['layer_name']}`
- CRS: `{info['crs']}`; geometry type: `{info['geometry_type']}`
- Features: {len(frame):,}; attributes: {len(info['fields'])}
- Geometry length: **{geometry_length:,.3f} km** summed from line geometry in EPSG:2193 (metres converted to kilometres).
- The source `length` attribute sums to {stored_length_total:,.3f} numeric units; its units and semantics were not documented, so it is excluded from all length totals. If those units are metres, its sum would be {stored_length_total / 1000:,.3f} km. Compared numerically with geometry length in metres, per-feature absolute differences have a {frame['length_difference_m'].abs().median():,.3f} median and {max_length_difference_m:,.3f} maximum. Confirm the field's provenance before using it.
- Totals describe the features as stored, without dissolving, de-duplicating or clipping again. Repeated OSM `id` values occur on {repeated_ids:,} rows ({repeated_id_values:,} distinct ids); identical geometries occur on {duplicate_geometry_rows:,} rows ({duplicate_geometry_groups:,} repeated geometry groups). Treat totals as represented feature-length, not a deduplicated unique-road estimate.
- Geometry QA: {null_geometry} null, {empty_geometry} empty, {invalid} invalid geometries.

## GeoPackage structure and fields

This file contains one layer, `{info['layer_name']}`, with MultiLineString geometry. Fields, in source order:

`{', '.join(map(str, info['fields']))}`

## Tag values, feature counts and lengths

Missing counts are shown as `(missing)`. Length is measured from geometry, not the source `length` attribute.

{chr(10).join(tag_sections)}

## Geometry length by `highway` and general `access`

{markdown_table(by_highway, ['highway', 'features', 'length_km'], ['Highway', 'Features', 'Geometry length (km)'])}

{markdown_table(by_access, ['access', 'features', 'length_km'], ['General access', 'Features', 'Geometry length (km)'])}

## Proposed pedestrian-access classification

Resolve `foot` first whenever it is present; do not let a general `access` value override it. Only fall back to `access` when `foot` is missing.

| Class | `foot` value (takes precedence) | Fallback `access` value |
|---|---|---|
| Public | `yes`, `designated` | `yes`, `foot` |
| Conditional | `permissive`, `customers` | `permissive`, `destination`, `customers`, `permit`, `forestry`, `tidal`, `emergency` |
| Restricted | `no`, `private`, `use_sidepath` | `no`, `private` |
| Unspecified | missing, unknown or unrecognized value | missing, unknown or unrecognized value |

`use_sidepath` is treated as restricted on the mapped segment because it directs pedestrians to another way; flag it for review rather than assuming the alternative is present. `permissive` is conditional because permission can be withdrawn. Unrecognized non-empty values remain Unspecified and should be reviewed; they are not treated as public.

{markdown_table(access_classes, ['pedestrian_access', 'features', 'length_km'], ['Pedestrian access', 'Features', 'Geometry length (km)'])}

### Walkability rules

Walkability is a separate, conservative assessment of the highway form and pedestrian restrictions; it is not proof of legal public access.

1. Restricted pedestrian access (`foot=no/private/use_sidepath`, or fallback `access=no/private`) overrides highway type. In particular, `foot=no` is an explicit restriction even on a footway/path.
2. `footway`, `path`, `steps`, `pedestrian`, `track`, and `bridleway` are pedestrian-oriented highway forms. With Public access they are classified as walkable; with Conditional access as conditional; with Unspecified access as potential only, with legal access unverified.
3. `service`, `residential`, `living_street`, `unclassified`, `primary`, `secondary`, and `tertiary` are road-like/shared forms. They are classed walkable only where pedestrian access is Public; conditional access stays conditional, and unspecified access stays potential/unverified.
4. `cycleway` alone does not establish pedestrian permission. It is walkable only with explicit Public pedestrian access, conditional where access is Conditional, and otherwise uncertain.
5. `motorway`, `motorway_link`, `trunk`, and `trunk_link` are not presumed suitable for pedestrians. A positive pedestrian-specific tag on them is a conflict/review case, not an automatic walkability grant.
6. `corridor`, `via_ferrata`, `busway`, `primary_link`, `secondary_link`, and unrecognized highway values are uncertain/specialist and need review; do not infer suitability from missing tags.

{markdown_table(walkability, ['walkability', 'features', 'length_km'], ['Walkability category', 'Features', 'Geometry length (km)'])}

## Foot/access/highway combinations

Top 25 combinations by feature count (all combinations are in `foot_access_highway_combinations.csv`).

{markdown_table(combo, ['foot_normalized', 'access_normalized', 'highway_normalized', 'features', 'length_km'], ['foot', 'access', 'highway', 'Features', 'Geometry length (km)'])}

### `highway` and `service` combinations

{markdown_table(service_combinations.head(25), ['highway', 'service', 'features', 'length_km'], ['Highway', 'Service', 'Features', 'Geometry length (km)'])}

## Conflicts and ambiguous records

There are **{len(conflicts):,}** records where both `foot` and `access` are populated and their independent mapped access classes disagree. Under the proposed rule, the `foot` classification wins, but these should be checked against source tagging before any production interpretation.

{markdown_table(
    conflicts.groupby(['foot_normalized', 'access_normalized', 'highway_normalized'], dropna=False)
    .agg(features=('geometry_length_km', 'size'), length_km=('geometry_length_km', 'sum'))
    .sort_values(['features', 'length_km'], ascending=False)
    .head(20).reset_index().assign(
        foot_normalized=lambda x: x['foot_normalized'].map(display_tag),
        access_normalized=lambda x: x['access_normalized'].map(display_tag),
        highway_normalized=lambda x: x['highway_normalized'].map(display_tag),
    ),
    ['foot_normalized', 'access_normalized', 'highway_normalized', 'features', 'length_km'],
    ['foot', 'access', 'highway', 'Features', 'Geometry length (km)'],
)}

Other important review cases:

- `foot=no` occurs on {foot_no:,} features ({foot_no_km:,.3f} km), including footways, paths, cycleways, steps and motorways; it must remain a restriction.
- `cycleway` with no pedestrian access classification is kept uncertain rather than assumed walkable.
- Motorway and specialist/link highway tags are rare and/or have unexpected tag combinations. Counts by access and walkability assessment:

{markdown_table(review_summary, ['highway', 'pedestrian_access', 'walkability', 'features', 'length_km'], ['Highway', 'Pedestrian access', 'Walkability', 'Features', 'Geometry length (km)'])}

- `foot=use_sidepath` is not evidence that the sidepath is included in this dataset or usable.
- `bicycle` and `motor_vehicle` tags describe other modes; they are not used to infer pedestrian permission. A segment marked `motor_vehicle=no` can still have Unspecified pedestrian access.
- The source includes repeated OSM ids and exact geometry duplicates. Assess whether those represent separate park overlays or duplicate records before treating summed lengths as unique network length.
- `review_examples.csv` includes up to five representative rows for each review flag; `audit_row_number` identifies source read order, while `id` is the OSM id and may repeat.

## Recommended map styling (proposal only)

- Use distinct, legible styles for Public, Conditional, Restricted and Unspecified access; avoid styling Unspecified as publicly available.
- Within accessible segments, differentiate pedestrian-oriented paths from road-like/shared segments.
- Render Restricted segments muted or dashed, conditional segments with a separate dash/pattern, and Unspecified/uncertain features with a subdued review style.
- Use a high-contrast warning style and/or exclude from default pedestrian routes for motor-highway classes and unresolved specialist types.
- Keep access state and walkability state as separate attributes so a visually pedestrian-friendly path is not mistaken for verified public access.

## Output files

- `tag_value_counts.csv`: all observed values, counts and geometry lengths for the six requested tags.
- `length_by_highway.csv` and `length_by_access_raw.csv`: category totals.
- `pedestrian_access_counts.csv` and `walkability_counts.csv`: proposed classification totals.
- `foot_access_highway_combinations.csv`: full three-tag combination table.
- `highway_service_combinations.csv`: `service` subtype by highway.
- `highway_review_summary.csv`: cycleway, motor-highway and specialist/link counts by access and walkability.
- `foot_access_conflicts.csv`: records where `foot` and general `access` resolve to different classes.
- `review_examples.csv`: representative edge cases.
- Run this audit with `python audits/road_network_access_audit/audit_road_network.py [path-to-gpkg]`.
"""
    (OUTPUT_DIR / "report.md").write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()

    source = args.source.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"GeoPackage not found: {source}")
    frame = gpd.read_file(source)
    if frame.crs is None or frame.crs.to_epsg() != 2193:
        raise ValueError(f"Expected EPSG:2193 to measure geometry in metres; found {frame.crs}")
    if frame.geometry.name != "geometry":
        frame = frame.rename_geometry("geometry")
    if frame.geometry.isna().any() or frame.geometry.is_empty.any():
        raise ValueError("Null or empty geometries must be reviewed before length aggregation")

    import pyogrio

    layers = pyogrio.list_layers(source)
    if len(layers) != 1:
        raise ValueError(f"Expected one GeoPackage layer for this audit, found {len(layers)}")
    info = pyogrio.read_info(source, layer=str(layers[0, 0]))

    required = {*TAG_COLUMNS, "length", "id", "osm_type", "DESCRIPTION"}
    absent = required.difference(frame.columns)
    if absent:
        raise ValueError(f"Missing expected fields: {', '.join(sorted(absent))}")

    frame["audit_row_number"] = range(1, len(frame) + 1)
    frame["geometry_length_km"] = frame.geometry.length / 1000
    frame["length_difference_m"] = pd.to_numeric(frame["length"], errors="coerce") - frame.geometry.length
    for column in TAG_COLUMNS:
        frame[f"{column}_normalized"] = normalize_tag(frame[column])

    resolved = frame.apply(
        lambda row: classify_access(row["foot_normalized"], row["access_normalized"]),
        axis=1,
        result_type="expand",
    )
    resolved.columns = ["pedestrian_access", "access_source"]
    frame[["pedestrian_access", "access_source"]] = resolved
    frame["walkability"] = frame.apply(
        lambda row: classify_walkability(
            row["highway_normalized"], row["pedestrian_access"], row["foot_normalized"]
        ),
        axis=1,
    )
    foot_status = frame["foot_normalized"].map(
        lambda value: classify_access(value, pd.NA)[0] if pd.notna(value) else pd.NA
    )
    access_status = frame["access_normalized"].map(
        lambda value: classify_access(pd.NA, value)[0] if pd.notna(value) else pd.NA
    )
    frame["tag_conflict"] = (
        frame["foot_normalized"].notna()
        & frame["access_normalized"].notna()
        & foot_status.fillna("").ne(access_status.fillna(""))
    )

    tag_values = write_tag_value_counts(frame)
    conflicts = write_conflicts(frame)
    write_review_examples(frame)
    for column, filename in (
        ("highway_normalized", "length_by_highway.csv"),
        ("access_normalized", "length_by_access_raw.csv"),
        ("pedestrian_access", "pedestrian_access_counts.csv"),
        ("walkability", "walkability_counts.csv"),
    ):
        grouped_summary(frame, column).rename(columns={column: "category"}).to_csv(
            OUTPUT_DIR / filename, index=False, float_format="%.6f"
        )
    combos = (
        frame.groupby(
            ["foot_normalized", "access_normalized", "highway_normalized"], dropna=False
        )
        .agg(features=("geometry_length_km", "size"), length_km=("geometry_length_km", "sum"))
        .reset_index()
        .sort_values(["features", "length_km"], ascending=False)
    )
    combos.rename(
        columns={
            "foot_normalized": "foot",
            "access_normalized": "access",
            "highway_normalized": "highway",
        }
    ).to_csv(OUTPUT_DIR / "foot_access_highway_combinations.csv", index=False, float_format="%.6f")
    write_report(source, frame, info, tag_values, conflicts)


if __name__ == "__main__":
    main()
