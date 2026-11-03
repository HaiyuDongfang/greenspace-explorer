"""Preprocess the in-park road network into the park walking network dataset.

Reads the raw GeoPackage (read-only), removes excluded features, assigns
highway_category and pedestrian_access, and writes:

* data/02processed/park_walking_network.gpkg (layer park_walking_network)
* data/02processed/park_network_statistics.parquet
* audits/road_network_access_audit/preprocessing_report.md

Lengths are geometry lengths in EPSG:2193 (metres, reported in km); the source
``length`` attribute is not used. Only the three outputs above are overwritten.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import geopandas as gpd
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = PROJECT_ROOT / "data" / "01raw" / "road_network_in_parks_auckland_overlay.gpkg"
OUTPUT_DIR = PROJECT_ROOT / "data" / "02processed"
OUTPUT_GPKG = OUTPUT_DIR / "park_walking_network.gpkg"
OUTPUT_STATS = OUTPUT_DIR / "park_network_statistics.parquet"
REPORT_PATH = PROJECT_ROOT / "audits" / "road_network_access_audit" / "preprocessing_report.md"
LAYER_NAME = "park_walking_network"
SOURCE_LAYER = "road_network_in_parks_auckland_overlay"
EXPECTED_CRS = 2193
PARK_ID_FIELD = "GlobalID"

EXCLUDED_HIGHWAYS = ("motorway", "motorway_link", "trunk_link", "busway", "via_ferrata")
EXCLUDED_BRIDGE = "viaduct"

HIGHWAY_CATEGORIES = {
    "Walking paths": ("footway", "pedestrian", "steps", "corridor"),
    "Nature trails": ("path", "track", "bridleway"),
    "Shared-use paths": ("cycleway",),
    "Local roads": ("service", "residential", "living_street", "unclassified"),
    "Major roads": ("tertiary", "secondary", "primary", "primary_link", "secondary_link"),
}
HIGHWAY_TO_CATEGORY = {value: cat for cat, values in HIGHWAY_CATEGORIES.items() for value in values}
CATEGORY_ORDER = list(HIGHWAY_CATEGORIES)

RESTRICTIVE = {"no", "private", "use_sidepath"}
CONDITIONAL = {"permissive", "destination", "customers", "permit", "forestry", "emergency", "tidal"}
EXPLICIT_PERMISSION = {"yes", "designated", "foot"}
ACCESS_ORDER = ["Walkable", "Conditional", "Restricted"]


def normalise(series: pd.Series) -> pd.Series:
    """Trim whitespace, lower-case, and turn empty strings into NA."""
    cleaned = series.astype("string").str.strip().str.lower()
    return cleaned.mask(cleaned == "")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def classify_access(access: str | None, foot: str | None) -> tuple[str, str]:
    """Return (pedestrian_access, basis) from the access and foot tags only."""
    values = {v for v in (access, foot) if v is not None}
    if values & RESTRICTIVE:
        return "Restricted", "restrictive access/foot value"
    if values & CONDITIONAL:
        return "Conditional", "conditional access/foot value"
    if values & EXPLICIT_PERMISSION:
        return "Walkable", "explicit permission (yes/designated/foot)"
    if not values:
        return "Walkable", "both access and foot missing (working assumption)"
    return "Walkable", "other unrecognised access/foot value"


def md_table(frame: pd.DataFrame) -> str:
    header = [str(c) for c in frame.columns]
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(str(v) for v in row) + " |" for row in frame.itertuples(index=False)]
    return "\n".join(lines)


def summary(frame: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    out = frame.groupby(by, dropna=False).agg(features=("length_km", "size"), length_km=("length_km", "sum")).reset_index()
    out["length_km"] = out["length_km"].round(3)
    return out


def as_bool(mask: pd.Series) -> pd.Series:
    return mask.fillna(False).astype(bool)


def main() -> None:
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(SOURCE_PATH)
    hash_before = sha256(SOURCE_PATH)

    raw = gpd.read_file(SOURCE_PATH, layer=SOURCE_LAYER).copy()
    assert raw.crs is not None and raw.crs.to_epsg() == EXPECTED_CRS, f"Unexpected CRS: {raw.crs}"
    assert raw.geometry.notna().all() and not raw.geometry.is_empty.any(), "Null or empty geometries"
    assert raw[PARK_ID_FIELD].notna().all(), f"{PARK_ID_FIELD} has nulls"
    raw["length_km"] = raw.geometry.length / 1000.0
    n_original, len_original = len(raw), raw["length_km"].sum()

    highway = normalise(raw["highway"])
    bridge = normalise(raw["bridge"])
    access = normalise(raw["access"])
    foot = normalise(raw["foot"])

    # 1. Exclusions, with overlap handling
    excl_highway = as_bool(highway.isin(EXCLUDED_HIGHWAYS))
    excl_bridge = as_bool(bridge == EXCLUDED_BRIDGE)
    excluded = excl_highway | excl_bridge
    primary_reason = pd.Series(pd.NA, index=raw.index, dtype="string")
    primary_reason[excl_highway] = "highway=" + highway[excl_highway]
    primary_reason[excl_bridge & ~excl_highway] = "bridge=viaduct"
    removed = raw[excluded].assign(reason=primary_reason[excluded])
    overlap = raw[excl_highway & excl_bridge]
    kept_mask = ~excluded
    retained = raw[kept_mask].copy()
    highway_k, access_k, foot_k = highway[kept_mask], access[kept_mask], foot[kept_mask]

    # 2. Highway category (no silent fallback)
    category = highway_k.map(HIGHWAY_TO_CATEGORY)
    unclassified_mask = category.isna()
    unrecognised = retained[unclassified_mask]
    assert not unclassified_mask.any(), (
        f"{int(unclassified_mask.sum())} retained features have missing/unrecognised highway: "
        f"{sorted(highway_k[unclassified_mask].fillna('<missing>').unique())}"
    )
    retained["highway_category"] = category.astype(str)

    # 3. Pedestrian access
    results = [
        classify_access(a if pd.notna(a) else None, f if pd.notna(f) else None)
        for a, f in zip(access_k, foot_k)
    ]
    retained["pedestrian_access"] = [r[0] for r in results]
    basis = pd.Series([r[1] for r in results], index=retained.index)

    # Mutually exclusive and exhaustive: independent vectorised re-derivation of each class.
    is_restricted = as_bool(access_k.isin(RESTRICTIVE) | foot_k.isin(RESTRICTIVE)).to_numpy()
    is_conditional = (
        as_bool(access_k.isin(CONDITIONAL) | foot_k.isin(CONDITIONAL)).to_numpy() & ~is_restricted
    )
    is_walkable = ~(is_restricted | is_conditional)
    class_flags = pd.DataFrame(
        {"Walkable": is_walkable, "Conditional": is_conditional, "Restricted": is_restricted}
    )
    assert (class_flags.sum(axis=1) == 1).all(), "Accessibility classes are not mutually exclusive and exhaustive"
    assert retained["pedestrian_access"].notna().all() and retained["pedestrian_access"].isin(ACCESS_ORDER).all()
    assert (retained["pedestrian_access"].to_numpy() == class_flags.idxmax(axis=1).to_numpy()).all()

    # Ambiguous / conflicting tags
    permissive_vals = EXPLICIT_PERMISSION | CONDITIONAL
    conflict = as_bool(
        (access_k.isin(RESTRICTIVE) & foot_k.isin(permissive_vals))
        | (foot_k.isin(RESTRICTIVE) & access_k.isin(permissive_vals))
    )
    known = RESTRICTIVE | CONDITIONAL | EXPLICIT_PERMISSION
    unknown_value = as_bool(access_k.notna() & ~access_k.isin(known)) | as_bool(foot_k.notna() & ~foot_k.isin(known))
    both_missing = (access_k.isna() & foot_k.isna()).to_numpy()
    cases = [
        ("access and foot conflict (restrictive vs permissive/conditional) -> Restricted", conflict),
        ("unrecognised access/foot value -> classified only if the other tag is restrictive/conditional", unknown_value),
        ("access and foot both missing or empty -> Walkable (working assumption)", pd.Series(both_missing, index=retained.index)),
    ]
    ambiguous_df = pd.DataFrame(
        [[name, int(m.sum()), round(float(retained.loc[m, "length_km"].sum()), 3)] for name, m in cases],
        columns=["Case", "features", "length_km"],
    )

    # 4. Write outputs (only our own files)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    assert OUTPUT_GPKG.resolve() != SOURCE_PATH.resolve()
    if OUTPUT_GPKG.exists():
        OUTPUT_GPKG.unlink()
    retained = retained.reset_index(drop=True)
    retained.to_file(OUTPUT_GPKG, layer=LAYER_NAME, driver="GPKG", SPATIAL_INDEX="YES", engine="pyogrio")

    # 5. Statistics
    stats = (
        retained.groupby([PARK_ID_FIELD, "highway_category", "pedestrian_access"])
        .agg(feature_count=("length_km", "size"), length_km=("length_km", "sum"))
        .reset_index()
        .rename(columns={PARK_ID_FIELD: "park_id"})
    )
    stats["park_id"] = stats["park_id"].astype(str)
    stats.to_parquet(OUTPUT_STATS, index=False)

    # Validation
    check = gpd.read_file(OUTPUT_GPKG, layer=LAYER_NAME)
    assert check.crs.to_epsg() == EXPECTED_CRS and len(check) == len(retained)
    assert len(retained) + len(removed) == n_original
    assert abs(retained["length_km"].sum() + removed["length_km"].sum() - len_original) < 1e-9
    assert abs(check.geometry.length.sum() / 1000 - retained["length_km"].sum()) < 1e-9
    assert abs(check["length_km"].sum() - retained["length_km"].sum()) < 1e-9
    assert abs(stats["length_km"].sum() - retained["length_km"].sum()) < 1e-9
    assert stats["feature_count"].sum() == len(retained)
    keys = ["park_id", "highway_category", "pedestrian_access"]
    from_gpkg = (
        check.assign(park_id=check[PARK_ID_FIELD].astype(str))
        .groupby(keys)
        .agg(feature_count=("length_km", "size"), length_km=("length_km", "sum"))
        .reset_index()
    )
    from_parquet = pd.read_parquet(OUTPUT_STATS)
    merged = from_gpkg.merge(from_parquet, on=keys, how="outer", suffixes=("_gpkg", "_parquet"), indicator=True)
    assert (merged["_merge"] == "both").all(), "Parquet and GeoPackage group keys differ"
    assert (merged["feature_count_gpkg"] == merged["feature_count_parquet"]).all()
    assert ((merged["length_km_gpkg"] - merged["length_km_parquet"]).abs() < 1e-9).all()
    assert not from_parquet.duplicated(keys).any()
    for access_class in ACCESS_ORDER:
        in_gpkg = check[check["pedestrian_access"] == access_class]
        in_stats = from_parquet[from_parquet["pedestrian_access"] == access_class]
        assert len(in_gpkg) == in_stats["feature_count"].sum()
        assert abs(in_gpkg["length_km"].sum() - in_stats["length_km"].sum()) < 1e-9
    assert retained.geometry.geom_equals(raw.loc[kept_mask].geometry.reset_index(drop=True)).all()
    with sqlite3.connect(f"file:{OUTPUT_GPKG.as_posix()}?mode=ro", uri=True) as conn:
        rtree = conn.execute(
            "SELECT COUNT(*) FROM gpkg_extensions WHERE table_name=? AND extension_name='gpkg_rtree_index'",
            (LAYER_NAME,),
        ).fetchone()[0]
        layers = [r[0] for r in conn.execute("SELECT table_name FROM gpkg_contents")]
    assert rtree == 1 and layers == [LAYER_NAME], (rtree, layers)
    hash_after = sha256(SOURCE_PATH)
    assert hash_before == hash_after, "Source GeoPackage changed!"

    # Report
    removal = removed.groupby("reason").agg(features=("length_km", "size"), length_km=("length_km", "sum")).reset_index()
    removal["length_km"] = removal["length_km"].round(3)
    removal.loc[len(removal)] = ["**Total removed**", len(removed), round(removed["length_km"].sum(), 3)]
    bridge_counts = bridge.fillna("<missing>").value_counts().rename_axis("bridge").reset_index(name="features")
    by_cat = summary(retained, ["highway_category"]).set_index("highway_category").loc[CATEGORY_ORDER].reset_index()
    by_acc = summary(retained, ["pedestrian_access"]).set_index("pedestrian_access").loc[ACCESS_ORDER].reset_index()
    cross_len = retained.pivot_table(
        index="highway_category", columns="pedestrian_access", values="length_km", aggfunc="sum", fill_value=0
    ).reindex(index=CATEGORY_ORDER, columns=ACCESS_ORDER, fill_value=0)
    cross_cnt = retained.pivot_table(
        index="highway_category", columns="pedestrian_access", values="length_km", aggfunc="size", fill_value=0
    ).reindex(index=CATEGORY_ORDER, columns=ACCESS_ORDER, fill_value=0)
    cross = pd.DataFrame({"highway_category": CATEGORY_ORDER})
    for col in ACCESS_ORDER:
        cross[col] = [f"{cross_cnt.loc[c, col]} / {cross_len.loc[c, col]:.3f} km" for c in CATEGORY_ORDER]
    by_basis = summary(retained.assign(basis=basis.to_numpy()), ["basis"])
    by_highway = summary(
        retained.assign(highway_value=highway_k.to_numpy()), ["highway_category", "highway_value"]
    )
    n_retained, len_retained = len(retained), retained["length_km"].sum()

    lines = [
        "# Park walking network preprocessing report",
        "",
        "Generated by `scripts/preprocess_park_walking_network.py`. Lengths are geometry lengths in EPSG:2193 "
        "(metres / 1000 = km); the source `length` attribute is not used. Totals are feature lengths: the source "
        "overlays roads with parks, so a road crossing several parks appears once per park feature "
        "(see the audit report) and is not unique road length.",
        "",
        "## Source and output",
        "",
        f"- Source: `{SOURCE_PATH.relative_to(PROJECT_ROOT).as_posix()}` (layer `{SOURCE_LAYER}`), CRS EPSG:{EXPECTED_CRS}",
        f"- Output GeoPackage: `{OUTPUT_GPKG.relative_to(PROJECT_ROOT).as_posix()}` (layer `{LAYER_NAME}`, "
        "R-tree spatial index, source CRS retained, all source attributes plus `highway_category`, "
        "`pedestrian_access`, `length_km`)",
        f"- Output statistics: `{OUTPUT_STATS.relative_to(PROJECT_ROOT).as_posix()}` "
        f"({len(stats)} rows; `park_id` = source `{PARK_ID_FIELD}`)",
        f"- Park identifier: `{PARK_ID_FIELD}` is the id the app uses (`src/data/loader.py`); no nulls on road features, "
        "and every road GlobalID exists in `parks_with_localboard.gpkg`.",
        "",
        "## 1. Original data",
        "",
        f"- Features: **{n_original}**; total length: **{len_original:.3f} km**",
        "",
        "## 2. Exclusions",
        "",
        "Rules (tags trimmed, case-insensitive): `highway` in "
        f"{', '.join(EXCLUDED_HIGHWAYS)}; or `bridge = viaduct` (a `bridge` value, not a `highway` value).",
        "Each removed feature is counted once, under its primary reason (highway rule first, then viaduct).",
        "",
        md_table(removal),
        "",
        f"Features meeting both conditions (highway exclusion and bridge=viaduct): **{len(overlap)}** "
        f"({overlap['length_km'].sum():.3f} km). Features removed only by `bridge=viaduct`: "
        f"**{int((excl_bridge & ~excl_highway).sum())}**.",
        "",
        "Bridge values in the source (normalised):",
        "",
        md_table(bridge_counts),
        "",
        "## 3. Retained features",
        "",
        f"- Features: **{n_retained}**; total length: **{len_retained:.3f} km**",
        "",
        "### By highway category",
        "",
        md_table(by_cat),
        "",
        "Highway values per category:",
        "",
        md_table(by_highway),
        "",
        "### By pedestrian accessibility",
        "",
        md_table(by_acc),
        "",
        "### Highway category x pedestrian accessibility (features / length)",
        "",
        md_table(cross),
        "",
        "## 4. Missing or unrecognised highway values (retained features)",
        "",
        f"- Features: **{len(unrecognised)}**; length: **{unrecognised['length_km'].sum():.3f} km**. "
        "The script asserts this is zero; otherwise it stops rather than assigning a category.",
        "",
        "## 5. Pedestrian access rules and ambiguous cases",
        "",
        "Classification uses only the `access` and `foot` tags (trimmed, case-insensitive; empty = missing). "
        "`highway` and `highway_category` play no part. Priority:",
        "",
        "1. **Restricted**: `access` or `foot` is one of no, private, use_sidepath, regardless of the other tag.",
        "2. **Conditional**: no restrictive value, and either tag is one of permissive, destination, customers, "
        "permit, forestry, emergency, tidal.",
        "3. **Walkable**: everything else, including features where both `access` and `foot` are missing or empty.",
        "",
        "> **Working assumption:** features with both `access` and `foot` missing are treated as Walkable. "
        "This is a working assumption, **not verified evidence** of pedestrian access: absence of a tag does "
        "not confirm that pedestrians are permitted. The previous highway-based Conditional fallback for "
        "service and major roads has been removed. Treat the 'both missing' count below as the unverified portion "
        "of Walkable.",
        "",
        md_table(ambiguous_df),
        "",
        "Basis of classification:",
        "",
        md_table(by_basis),
        "",
        "## 6. Validation",
        "",
        f"- Retained + removed = original: {n_retained} + {len(removed)} = {n_retained + len(removed)} (original {n_original}) - PASS",
        f"- Length reconciles: {len_retained:.6f} + {removed['length_km'].sum():.6f} = "
        f"{len_retained + removed['length_km'].sum():.6f} km (original {len_original:.6f}) - PASS",
        "- Every retained feature has exactly one `highway_category` and one `pedestrian_access` (no nulls) - PASS",
        "- Walkable / Conditional / Restricted are mutually exclusive and exhaustive (independent re-derivation: "
        "exactly one class per feature, matches the assigned field) - PASS",
        "- Parquet and GeoPackage agree on feature counts and lengths per park x category x access, and per "
        "access class - PASS",
        f"- Output GPKG re-read: {len(check)} features, CRS EPSG:{check.crs.to_epsg()}, length sum "
        f"{check['length_km'].sum():.6f} km - PASS",
        f"- Statistics parquet: feature_count sum {int(stats['feature_count'].sum())}, length_km sum "
        f"{stats['length_km'].sum():.6f} km (equals retained) - PASS",
        "- Geometries identical to the retained source geometries (no simplification or reprojection) - PASS",
        "- GeoPackage R-tree spatial index registered for the layer; single layer present - PASS",
        f"- Source GeoPackage not modified: SHA-256 before and after `{hash_after}` - PASS",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"original={n_original} removed={len(removed)} retained={n_retained} length_km={len_retained:.3f}")


if __name__ == "__main__":
    main()
