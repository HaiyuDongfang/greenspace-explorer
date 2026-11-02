"""Public GIS processing entry points for the application."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd


def load_demo_data(parks_path: Path, networks_path: Path) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Load the small demonstration datasets."""
    parks = gpd.read_file(parks_path)
    networks = gpd.read_file(networks_path)
    return parks, networks


def validate_dataset(dataset: gpd.GeoDataFrame, expected_geometry_types: set[str]) -> None:
    """Perform initial geometry and CRS safety checks."""
    if dataset.crs is None:
        raise ValueError("Dataset is missing a coordinate reference system (CRS).")
    if not set(dataset.geom_type).issubset(expected_geometry_types):
        raise ValueError(
            f"Expected geometry types {sorted(expected_geometry_types)}, "
            f"found {sorted(set(dataset.geom_type))}."
        )
