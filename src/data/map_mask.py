"""Inverse-polygon mask geometry: everything outside the selected boundary."""

from __future__ import annotations

import json

from shapely.geometry import box, mapping
from shapely.ops import unary_union
from shapely.validation import make_valid

# Web Mercator cannot show beyond about +/-85.05 latitude.
WORLD = box(-180.0, -85.0, 180.0, 85.0)


def mask_feature_collection(boards, area: str, name_column: str = "LocalBoa_2") -> dict:
    """GeoJSON FeatureCollection with one polygon: the world minus the selected boundary.

    boards must be in EPSG:4326. area "all" uses the union of every Local Board as the Auckland
    boundary. Returns an empty collection when no matching boundary geometry exists.
    """
    selected = boards if area == "all" else boards[boards[name_column].astype(str) == area]
    geometries = [
        make_valid(geometry) if not geometry.is_valid else geometry
        for geometry in selected.geometry
        if geometry is not None and not geometry.is_empty
    ]
    if not geometries:
        return {"type": "FeatureCollection", "features": []}
    boundary = unary_union(geometries)
    mask = WORLD.difference(boundary)
    feature = {"type": "Feature", "properties": {"mask": area}, "geometry": mapping(mask)}
    return json.loads(json.dumps({"type": "FeatureCollection", "features": [feature]}))
