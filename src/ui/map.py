import os

from ipyleaflet import Map, TileLayer

AUCKLAND_CENTER = (-36.8625, 174.755)
ATTRIBUTION = "&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors &copy; <a href='https://carto.com/attributions'>CARTO</a>"


def create_initial_map() -> Map:
    map_widget = Map(center=AUCKLAND_CENTER, zoom=12, scroll_wheel_zoom=True, zoom_snap=0.25)
    api_key = os.getenv("CARTO_API_KEY", "").strip()
    if api_key:
        tile_url = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png?key={key}"
        tile_url = tile_url.replace("{key}", api_key)
        subdomains = "abcd"
    else:
        tile_url = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        subdomains = None

    tile_options = {
        "url": tile_url,
        "attribution": ATTRIBUTION,
        "max_zoom": 20,
    }
    if subdomains:
        tile_options["subdomains"] = subdomains
    map_widget.add(TileLayer(**tile_options))
    map_widget.layout.height = "100%"
    return map_widget
