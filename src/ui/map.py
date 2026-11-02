from ipyleaflet import Map, TileLayer

AUCKLAND_CENTER = (-36.8625, 174.755)
ESRI_BASE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
ESRI_REFERENCE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}"
ATTRIBUTION = "Tiles &copy; <a href='https://www.esri.com'>Esri</a> &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors, and the GIS user community"
# Esri Light Gray Canvas tiles are published to zoom 16; higher zooms upscale those tiles.
ESRI_MAX_NATIVE_ZOOM = 16


def create_initial_map() -> Map:
    # Custom panes order the Local Board layers: mask below the interactive board hit layer, both below parks.
    map_widget = Map(
        center=AUCKLAND_CENTER, zoom=12, scroll_wheel_zoom=True, zoom_snap=0.25,
        panes={"area_mask": {"zIndex": 340}, "board_hit": {"zIndex": 350}},
    )
    tile_options = {"attribution": ATTRIBUTION, "max_zoom": 20, "max_native_zoom": ESRI_MAX_NATIVE_ZOOM}
    # Replaces ipyleaflet's default OSM layer. Tile layers sit in Leaflet's tile pane, below all vector overlays.
    map_widget.layers = (
        TileLayer(url=ESRI_BASE_URL, name="Esri Light Gray Base", **tile_options),
        TileLayer(url=ESRI_REFERENCE_URL, name="Esri Light Gray Reference", **tile_options),
    )
    map_widget.layout.height = "100%"
    return map_widget