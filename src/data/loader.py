"""Load and adapt the Auckland Greenspace GIS datasets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely.geometry import MultiPolygon

PROCESSING_CRS = "EPSG:2193"
DISPLAY_CRS = "EPSG:4326"
SIMPLIFY_CRS = "EPSG:2193"
PRESENTATION_SIMPLIFY_TOLERANCE_M = 1.0

NETWORK_CATEGORY_MAPPING = {
    "footway": "Footway",
    "path": "Path",
    "track": "Track",
    "steps": "Steps",
    "service": "Service road",
    "cycleway": "Cycleway",
    "residential": "Road",
    "primary": "Road",
    "secondary": "Road",
    "tertiary": "Road",
    "living_street": "Road",
    "pedestrian": "Pedestrian",
    "bridleway": "Bridleway",
    "unclassified": "Unclassified",
}


def _network_composition(network: gpd.GeoDataFrame, park_id: str) -> dict[str, float]:
    park_network = network[(network["GlobalID"].notna()) & (network["GlobalID"].astype(str) == park_id)].copy()
    if park_network.empty:
        return {}

    categories: dict[str, float] = {}
    for _, segment in park_network.iterrows():
        highway = str(segment["highway"]).strip().lower() if pd.notna(segment["highway"] ) else "unclassified"
        category = NETWORK_CATEGORY_MAPPING.get(highway, "Other")
        length = pd.to_numeric(pd.Series([segment.get("length_km")]), errors="coerce").iloc[0]
        if pd.isna(length) or length < 0:
            continue
        categories[category] = categories.get(category, 0.0) + float(length)

    total = sum(categories.values())
    if total <= 0:
        return {}
    return {
        category: round(length / total * 100, 1)
        for category, length in sorted(categories.items(), key=lambda item: item[1], reverse=True)
        if length > 0
    }


@dataclass(frozen=True)
class RealData:
    parks: gpd.GeoDataFrame
    presentation_parks: gpd.GeoDataFrame
    park_records: list[dict[str, Any]]
    park_network: gpd.GeoDataFrame
    local_boards: gpd.GeoDataFrame
    auckland_network_loaded: bool
    spatial_network_match_summary: dict[str, int | float]


def _require_columns(frame: gpd.GeoDataFrame, columns: set[str], source: Path) -> None:
    missing = sorted(columns.difference(frame.columns))
    if missing:
        raise ValueError(f"{source} is missing required fields: {', '.join(missing)}")


def _to_processing_crs(frame: gpd.GeoDataFrame, source: Path) -> gpd.GeoDataFrame:
    if frame.crs is None:
        raise ValueError(f"{source} is missing a coordinate reference system")
    if frame.crs.to_epsg() != 2193:
        frame = frame.to_crs(PROCESSING_CRS)
    return frame


def displayable_geometry(geometry: Any) -> bool:
    return (
        geometry is not None
        and hasattr(geometry, "is_empty")
        and not geometry.is_empty
        and hasattr(geometry, "geom_type")
    )


def _displayable_indices(frame: gpd.GeoDataFrame) -> list[int]:
    return [
        index
        for index, geometry in enumerate(frame.geometry)
        if geometry is not None
        and hasattr(geometry, "is_empty")
        and not geometry.is_empty
        and hasattr(geometry, "geom_type")
    ]


def _presentation_parks_geometries(
    frame: gpd.GeoDataFrame, tolerance_metres: float = PRESENTATION_SIMPLIFY_TOLERANCE_M
) -> gpd.GeoDataFrame:
    frame = frame.iloc[_displayable_indices(frame)].copy()
    valid = frame.geometry.apply(lambda geometry: geometry.is_valid)
    invalid = ~valid
    if invalid.any():
        frame.loc[invalid, "geometry"] = frame.loc[invalid, "geometry"].apply(
            lambda geometry: geometry.make_valid()
        )
    # Display copy only: simplify in metres (EPSG:2193), then reproject for the web map.
    frame = frame.to_crs(SIMPLIFY_CRS)
    frame["geometry"] = frame.geometry.simplify(tolerance_metres, preserve_topology=True)
    return frame.to_crs(DISPLAY_CRS)


def _presentation_geometries(frame: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    frame = frame.copy()
    displayable = frame.geometry.apply(lambda geometry: displayable_geometry(geometry))
    valid = displayable & frame.geometry.apply(
        lambda geometry: geometry.is_valid if displayable_geometry(geometry) else False
    )
    invalid = displayable & ~valid
    if invalid.any():
        frame.loc[invalid, "geometry"] = frame.loc[invalid, "geometry"].apply(
            lambda geometry: geometry.make_valid()
        )
    return frame.to_crs(DISPLAY_CRS)


def _bounds_for_geometry(geometry: Any) -> list[list[float]] | None:
    if geometry is None or geometry.is_empty:
        return None
    geometry = geometry if geometry.is_valid else geometry.make_valid()
    min_x, min_y, max_x, max_y = geometry.bounds
    return [[min_y, min_x], [max_y, max_x]]


def load_real_data(
    parks_path: Path,
    auckland_network_path: Path,
    park_network_path: Path,
    local_boards_path: Path,
) -> RealData:
    parks = gpd.read_file(parks_path, layer="parks")
    park_network = gpd.read_file(park_network_path)
    local_boards = gpd.read_file(local_boards_path)

    _require_columns(parks, {"GlobalID", "DESCRIPTION", "LOCALBOARD_OFFICIAL", "area_km2", "path_length_km"}, parks_path)
    _require_columns(park_network, {"highway"}, park_network_path)
    _require_columns(local_boards, {"LocalBoa_2"}, local_boards_path)

    parks = _to_processing_crs(parks, parks_path)
    park_network = _to_processing_crs(park_network, park_network_path)
    local_boards = _to_processing_crs(local_boards, local_boards_path)

    global_ids = parks["GlobalID"].dropna().astype(str)
    if global_ids.duplicated().any():
        duplicates = sorted(global_ids[global_ids.duplicated()].unique().tolist())
        raise ValueError(f"Duplicate park GlobalIDs found: {', '.join(duplicates[:10])}")

    null_global_ids = parks["GlobalID"].isna().sum()
    if null_global_ids:
        raise ValueError(f"{null_global_ids} parks are missing GlobalID")

    records: list[dict[str, Any]] = []
    for _, park in parks.iterrows():
        geometry = park.geometry
        bounds = None
        if geometry is not None and not geometry.is_empty:
            try:
                bounds = _bounds_for_geometry(geometry)
            except (AttributeError, ValueError, TypeError):
                bounds = None
        if geometry is not None and not geometry.is_empty and geometry.is_valid:
            bounds_geometry = geometry
        elif geometry is not None and not geometry.is_empty:
            try:
                bounds_geometry = geometry.make_valid()
            except (AttributeError, ValueError, TypeError):
                bounds_geometry = None
        else:
            bounds_geometry = None
        raw_length = park["path_length_km"]
        length = pd.to_numeric(pd.Series([raw_length]), errors="coerce").iloc[0]
        length = float(length) if pd.notna(length) and length >= 0 else None
        area = pd.to_numeric(pd.Series([park["area_km2"]]), errors="coerce").iloc[0]
        area_hectares = float(area * 100) if pd.notna(area) else None
        records.append({
            "id": str(park["GlobalID"]),
            "name": str(park["DESCRIPTION"]) if pd.notna(park["DESCRIPTION"]) else "Unnamed park",
            "local_board": str(park["LOCALBOARD_OFFICIAL"]) if pd.notna(park["LOCALBOARD_OFFICIAL"]) else "",
            "area": area_hectares,
            "length": length,
            "bounds": bounds,
            "geometry": geometry,
            "network": _network_composition(park_network, str(park["GlobalID"])),
            "duration": {},
        })

    presentation_parks = _presentation_parks_geometries(parks)
    presentation_parks_full = _presentation_geometries(parks)
    bounds_by_global_id = {
        str(park_id): _bounds_for_geometry(geometry)
        for park_id, geometry in presentation_parks_full.set_index("GlobalID").geometry.items()
    }
    for record in records:
        if record["id"] in bounds_by_global_id:
            record["bounds"] = bounds_by_global_id[record["id"]]

    presentation_network = _presentation_geometries(park_network)
    presentation_boards = _presentation_geometries(local_boards)

    # Spatial matching is diagnostic only: no network segment is assigned to a
    # park until a reliable source-level association exists.
    spatial_matches = 0
    ambiguous_matches = 0
    if "SAPID" in park_network.columns:
        linked_records = park_network[park_network["SAPID"].notna() & park_network["SAPID"].isin(parks["SAPID"])].shape[0]
        duplicate_sapids = parks["SAPID"].dropna().duplicated(keep=False).sum() if "SAPID" in parks.columns else 0
        spatial_matches = int(linked_records)
        ambiguous_matches = int(duplicate_sapids)

    # Explicitly avoid loading Auckland-wide lines into browser memory.
    # The file remains available for future viewport/server-side loading.
    auckland_network_loaded = False
    if auckland_network_path.exists():
        with auckland_network_path.open("rb"):
            pass

    presentation_parks = presentation_parks.set_crs(DISPLAY_CRS, allow_override=True)
    presentation_network = presentation_network.set_crs(DISPLAY_CRS, allow_override=True)
    presentation_boards = presentation_boards.set_crs(DISPLAY_CRS, allow_override=True)

    return RealData(
        parks=presentation_parks_full,
        presentation_parks=presentation_parks,
        park_records=records,
        park_network=presentation_network,
        local_boards=presentation_boards,
        auckland_network_loaded=auckland_network_loaded,
        spatial_network_match_summary={
            "source_associated_segments": spatial_matches,
            "duplicate_sapid_rows": ambiguous_matches,
        },
    )
