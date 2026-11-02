"""Project-relative and environment-configured data paths."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def configured_path(environment_variable: str, relative_path: str) -> Path:
    """Return an external override or a project-relative fallback."""
    configured = os.getenv(environment_variable)
    if configured:
        return Path(configured).expanduser()
    return PROJECT_ROOT / relative_path


DEMO_PARKS_PATH = PROJECT_ROOT / "data" / "demo" / "parks.geojson"
DEMO_NETWORKS_PATH = PROJECT_ROOT / "data" / "demo" / "networks.geojson"

PARKS_PATH = configured_path("GREENSPACE_PARKS_PATH", "data/02processed/parks_with_localboard.gpkg")
AUCKLAND_NETWORKS_PATH = configured_path("GREENSPACE_AUCKLAND_NETWORKS_PATH", "data/01raw/road_network_auckland.gpkg")
PARK_NETWORKS_PATH = configured_path("GREENSPACE_PARK_NETWORKS_PATH", "data/01raw/road_network_in_parks_filtered.gpkg")
LOCAL_BOARDS_PATH = configured_path("GREENSPACE_LOCAL_BOARDS_PATH", "data/01raw/LocalElectoralBoundary_3350795404476040859/Local_Boards_(Outline).shp")
NETWORKS_PATH = configured_path("GREENSPACE_NETWORKS_PATH", "data/external/networks.geojson")
AREAS_PATH = configured_path("GREENSPACE_AREAS_PATH", "data/external/areas.geojson")
