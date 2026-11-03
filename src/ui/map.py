from collections.abc import Sequence
from typing import TypeVar

from ipyleaflet import Map, TileLayer

_Layer = TypeVar("_Layer")

AUCKLAND_CENTER = (-36.8625, 174.755)
ESRI_BASE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
ESRI_REFERENCE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}"
ATTRIBUTION = "Tiles &copy; <a href='https://www.esri.com'>Esri</a> &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors, and the GIS user community"
# Esri Light Gray Canvas tiles are published to zoom 16; higher zooms upscale those tiles.
ESRI_MAX_NATIVE_ZOOM = 16
# Non-interactive road pane. It must sit above Leaflet's overlay pane (z 400, park polygons): matching parks
# are filled at 0.9 opacity, which hides any road drawn below them. pointer-events are disabled in styles.css.
ROAD_PANE = "road_network"
ROAD_PANE_Z = 410
PARK_SELECTION_STYLE = {
    "color": "#00E5FF",
    "weight": 3,
    "opacity": 1,
    "fillColor": "#00FFFF",
    "fillOpacity": 0.25,
}


def selected_park_layer_order(
    layers: Sequence[_Layer],
    park_layers: Sequence[_Layer],
    selected_layer: _Layer,
) -> tuple[_Layer, ...]:
    """Move the selected park to the last position occupied by a park layer."""
    ordered_layers = list(layers)
    selected_index = next(
        (index for index, layer in enumerate(ordered_layers) if layer is selected_layer),
        None,
    )
    park_indices = [
        index for index, layer in enumerate(ordered_layers)
        if any(layer is park_layer for park_layer in park_layers)
    ]
    if selected_index is None or not park_indices:
        return tuple(ordered_layers)

    top_park_index = max(park_indices)
    if selected_index != top_park_index:
        ordered_layers.insert(top_park_index, ordered_layers.pop(selected_index))
    return tuple(ordered_layers)


def create_initial_map() -> Map:
    # Custom panes order the Local Board layers: mask below the interactive board hit layer, both below parks.
    map_widget = Map(
        center=AUCKLAND_CENTER, zoom=12, scroll_wheel_zoom=True, zoom_snap=0.25,
        panes={"area_mask": {"zIndex": 340}, "board_hit": {"zIndex": 350}, ROAD_PANE: {"zIndex": ROAD_PANE_Z}},
    )
    tile_options = {"attribution": ATTRIBUTION, "max_zoom": 20, "max_native_zoom": ESRI_MAX_NATIVE_ZOOM}
    # Replaces ipyleaflet's default OSM layer. Tile layers sit in Leaflet's tile pane, below all vector overlays.
    map_widget.layers = (
        TileLayer(url=ESRI_BASE_URL, name="Esri Light Gray Base", **tile_options),
        TileLayer(url=ESRI_REFERENCE_URL, name="Esri Light Gray Reference", **tile_options),
    )
    map_widget.layout.height = "100%"
    return map_widget