"""Main Shiny application entry point."""

import json
import time
from math import ceil
from pathlib import Path

import pandas as pd
from ipyleaflet import GeoJSON, Polygon, Popup, Polyline
from ipywidgets import HTML
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget

from src.mock_data import DEMO_PARKS, DEMO_ROUTES, NETWORK_STYLES
from src.data.loader import load_real_data
from src.data.map_mask import mask_feature_collection
from src.data.map_view import compute_view, expand_bounds
from config.paths import AUCKLAND_NETWORKS_PATH, LOCAL_BOARDS_PATH, PARK_NETWORKS_PATH, PARKS_PATH
from src.ui.filters import filter_panel
from src.ui.results import results_panel
from src.ui.status_bar import status_bar
from src.ui.map import AUCKLAND_CENTER, create_initial_map
from src.ui.shell import app_ui


try:
    REAL_DATA = load_real_data(PARKS_PATH, AUCKLAND_NETWORKS_PATH, PARK_NETWORKS_PATH, LOCAL_BOARDS_PATH)
    APPLICATION_PARKS = REAL_DATA.park_records
except (FileNotFoundError, ValueError, OSError) as error:
    print(f"Real Auckland data unavailable; using demo data: {error}")
    REAL_DATA = None
    APPLICATION_PARKS = DEMO_PARKS

PARKS_BY_ID = {park["id"]: park for park in APPLICATION_PARKS}


def displayable_geometry(geometry):
    return (
        geometry is not None
        and bool(getattr(geometry, "is_empty", True)) is False
        and hasattr(geometry, "geom_type")
    )


def displayable_frame(frame):
    return frame.iloc[[index for index, geometry in enumerate(frame.geometry) if displayable_geometry(geometry)]].copy()

PARK_FOCUS_BUFFER, PARK_FOCUS_MAX_ZOOM = 0.9, 16
# Local Board / Auckland fits zoom in by this many levels (2**0.25 is about 19% closer) when the bounds still fit.
AREA_ZOOM_GAIN = 0.25
PARK_CLOSE_BUFFER, PARK_CLOSE_MAX_ZOOM = 0.2, 18

PARK_STYLE_DEFAULT = {"color": "#39785A", "weight": 2, "fillColor": "#78A67E", "fillOpacity": 0.28}
PARK_STYLE_OUTSIDE = {"color": "#3E6450", "weight": 1, "fillColor": "#4E7A5E", "fillOpacity": 0.5}
PARK_STYLE_INSIDE = {"color": "#78A67E", "weight": 0.9, "fillColor": "#B9D5BC", "fillOpacity": 0.8}
PARK_STYLE_MATCH = {"color": "#245B45", "weight": 1.1, "fillColor": "#39785A", "fillOpacity": 0.85}
# interactive=False keeps the mask and board layers (drawn above the parks) from intercepting park clicks.
MASK_STYLE = {"stroke": False, "fillColor": "#0F1F17", "fillOpacity": 0.38, "interactive": False}
BOARD_STYLE_DEFAULT = {"color": "#7A8A7F", "weight": 1, "opacity": 1, "fillColor": "#7A8A7F", "fillOpacity": 0, "dashArray": "4", "interactive": False}
BOARD_STYLE_SELECTED = {"color": "#245B45", "weight": 1, "opacity": 0.35, "fillColor": "#245B45", "fillOpacity": 0, "dashArray": "", "interactive": False}
BOARD_STYLE_MUTED = {"color": "#C3C9C5", "weight": 1, "opacity": 1, "fillColor": "#E6E9E7", "fillOpacity": 0.05, "dashArray": "4", "interactive": False}


def park_style_for(board: str, matching_ids=None):
    """Style by Local Board membership (local_board) and applied-filter match (GlobalID).

    matching_ids None means no filters are applied to the map: neutral styling.
    """
    def style(feature):
        if board == "all" and matching_ids is None:
            return PARK_STYLE_DEFAULT
        properties = feature.get("properties", {})
        if board != "all" and str(properties.get("local_board") or "") != board:
            return PARK_STYLE_OUTSIDE
        if matching_ids is not None and str(properties.get("GlobalID") or "") in matching_ids:
            return PARK_STYLE_MATCH
        return PARK_STYLE_INSIDE
    return style


def board_style_for(board: str):
    def style(feature):
        if board == "all":
            return BOARD_STYLE_DEFAULT
        name = str(feature.get("properties", {}).get("LocalBoa_2") or "")
        return BOARD_STYLE_SELECTED if name == board else BOARD_STYLE_MUTED
    return style


LOCAL_BOARD_CHOICES = {"all": "All Auckland"}
LOCAL_BOARD_CHOICES.update({
    board: board
    for board in sorted({
        park["local_board"]
        for park in APPLICATION_PARKS
        if park.get("local_board")
    })
})


def leaflet_polygon_locations(geometry):
    if geometry is None or geometry.is_empty:
        return None
    polygons = [geometry] if geometry.geom_type == "Polygon" else list(geometry.geoms) if geometry.geom_type == "MultiPolygon" else []
    locations = []
    for polygon in polygons:
        ring = [[coordinate[1], coordinate[0]] for coordinate in polygon.exterior.coords]
        locations.append(ring)
    return locations[0] if len(locations) == 1 else locations


def leaflet_line_locations(geometry):
    if geometry is None or geometry.is_empty:
        return []
    if geometry.geom_type == "LineString":
        return [[[coordinate[1], coordinate[0]] for coordinate in geometry.coords]]
    if geometry.geom_type == "MultiLineString":
        return [[[coordinate[1], coordinate[0]] for coordinate in line.coords] for line in geometry.geoms]
    return []


def server(input, output, session):
    applied = reactive.Value({"area": "all", "speed": 4, "threshold": 10, "custom": False, "custom_speed": False})
    results_snapshot = reactive.Value([])
    has_searched = reactive.Value(False)
    view_state = reactive.Value("map")
    selected_park = reactive.Value(None)
    navigation_source = reactive.Value(None)
    filter_panel_collapsed = reactive.Value(False)
    results_panel_collapsed = reactive.Value(False)
    show_details = reactive.Value(False)
    sort_key = reactive.Value("name")
    results_scroll = reactive.Value(0)

    map_widget = create_initial_map()
    map_layers = {"parks": [], "networks": {network_type: [] for network_type in NETWORK_STYLES}}

    def add_park_layers():
        for layer in map_layers["parks"]:
            map_widget.remove_layer(layer)
        map_layers["parks"] = []
        if REAL_DATA is not None:
            parks = displayable_frame(REAL_DATA.presentation_parks)
            parks["GlobalID"] = parks["GlobalID"].astype(str)
            parks.rename(columns={"DESCRIPTION": "description", "LOCALBOARD_OFFICIAL": "local_board"}, inplace=True)
            park_geojson = GeoJSON(
                data=json.loads(parks[["GlobalID", "description", "local_board", "geometry"]].to_json()),
                style={},
                style_callback=park_style_for("all"),
                hover_style={"fillOpacity": 0.45},
                name="Park boundaries",
            )

            def select_park(feature=None, **_event):
                properties = (feature or {}).get("properties", {})
                park_id = str(properties.get("GlobalID", properties.get("id", "")))
                if park_id in PARKS_BY_ID:
                    navigation_source.set("map")
                    view_state.set("details")
                    selected_park.set(park_id)
                    show_details.set(True)
                    focus_park(park_id)

            park_geojson.on_click(select_park)
            map_layers["parks"] = [park_geojson]
            # Added by toggle_parks once the browser map view exists.
            return

        for park in APPLICATION_PARKS:
            polygon = Polygon(locations=park["bounds"], color="#39785A", weight=2, fill_color="#78A67E", fill_opacity=0.28, name=park["name"])
            def select_polygon(event, park_id=park["id"]):
                navigation_source.set("map")
                view_state.set("details")
                selected_park.set(park_id)
                show_details.set(True)
                focus_park(park_id)
            polygon.on_click(select_polygon)
            map_layers["parks"].append(polygon)
            map_widget.add(polygon)

    def add_network_layers():
        for layers in map_layers["networks"].values():
            for layer in layers:
                map_widget.remove_layer(layer)
        map_layers["networks"] = {network_type: [] for network_type in NETWORK_STYLES}
        if REAL_DATA is not None:
            return
        for park_id, routes in DEMO_ROUTES.items():
            for network_type, locations in routes:
                style = NETWORK_STYLES[network_type]
                line = Polyline(
                    locations=locations,
                    color=style["color"],
                    weight=style["weight"],
                    dash_array=style["dash"] if style["dash"] != "solid" else None,
                    name=f"{network_type}: {PARKS_BY_ID[park_id]['name']}",
                )
                map_layers["networks"][network_type].append(line)
                map_widget.add(line)

    local_board_layer = None
    if REAL_DATA is not None:
        boards = displayable_frame(REAL_DATA.local_boards)
        local_board_layer = GeoJSON(
            data=json.loads(boards[["LocalBoa_2", "geometry"]].to_json()),
            style={},
            style_callback=board_style_for("all"),
            name="Local Board boundaries",
        )
        map_widget.add(local_board_layer)

    mask_cache = {}

    def mask_data(area):
        if area not in mask_cache:
            mask_cache[area] = mask_feature_collection(REAL_DATA.local_boards, area)
        return mask_cache[area]

    mask_layer = None
    if REAL_DATA is not None:
        # Added by toggle_parks, below the parks layer.
        mask_layer = GeoJSON(data=mask_data("all"), style=dict(MASK_STYLE), name="Area mask")

    highlight_layer = GeoJSON(
        data={"type": "FeatureCollection", "features": []},
        style={"color": "#245B45", "weight": 5, "fillColor": "#245B45", "fillOpacity": 0.42},
        name="Selected park",
    )

    add_park_layers()
    add_network_layers()

    @render_widget
    def map():
        return map_widget

    def calculate_matches(filters):
        speed = filters["speed"]
        threshold = filters["threshold"]
        area = filters["area"]

        def duration_at_speed(park):
            if REAL_DATA is None:
                if speed in park["duration"]:
                    return park["duration"][speed]
                base_speed = 3
                return park["duration"][base_speed] * base_speed / speed
            length = park.get("length")
            if length is None or length < 0 or speed <= 0:
                return None
            return length / speed * 60

        return [
            park for park in APPLICATION_PARKS
            if (area == "all" or park["local_board"] == area)
            and (duration_at_speed(park) is not None and duration_at_speed(park) > threshold)
        ]

    filter_error_text = reactive.Value("")

    @reactive.effect
    async def sync_panel_state():
        results_visible = view_state() == "details" or (has_searched() and view_state() == "results")
        await session.send_custom_message("panel_state", {
            "results_visible": results_visible,
            "results_collapsed": results_panel_collapsed(),
            "filter_collapsed": filter_panel_collapsed(),
        })

    @reactive.effect
    @reactive.event(input.toggle_filter_panel)
    def toggle_filter_panel():
        filter_panel_collapsed.set(not filter_panel_collapsed())

    @reactive.effect
    @reactive.event(input.toggle_results_panel)
    def toggle_results_panel():
        results_panel_collapsed.set(not results_panel_collapsed())

    @reactive.effect
    @reactive.event(input.apply_filters)
    def apply_filters():
        try:
            custom_speed_value = input.custom_walking_speed()
            custom_time_value = input.custom_minutes()
            custom_speed = input.walking_speed() == "custom"
            custom_time = input.walk_time() == "custom"
            if custom_speed and custom_speed_value in (None, ""):
                raise ValueError("Enter a walking speed greater than 0 km/h.")
            if custom_time and custom_time_value in (None, ""):
                raise ValueError("Enter a walking time greater than 0 minutes.")
            speed = float(custom_speed_value) if custom_speed else float(input.walking_speed())
            threshold = float(custom_time_value) if custom_time else float(input.walk_time())
            if speed <= 0 or speed > 30:
                raise ValueError("Walking speed must be between 0.1 and 30 km/h.")
            if threshold <= 0 or threshold > 180:
                raise ValueError("Walking time must be between 1 and 180 minutes.")
            next_filters = {
                "area": input.area(),
                "speed": speed,
                "threshold": ceil(threshold) if custom_time else int(threshold),
                "custom": custom_time,
                "custom_speed": custom_speed,
            }
            filter_error_text.set("")
        except (TypeError, ValueError) as error:
            filter_error_text.set(str(error))
            return

        applied.set(next_filters)
        next_matches = calculate_matches(next_filters)
        results_snapshot.set(next_matches)
        refresh_applied_map_styles(next_filters, next_matches)
        has_searched.set(True)
        view_state.set("results")
        results_panel_collapsed.set(False)
        show_details.set(False)
        selected_park.set(None)
        fit_after_layout(next_filters)

    @reactive.effect
    @reactive.event(input.reset_filters)
    def reset_filters():
        ui.update_select("area", selected="all")
        ui.update_radio_buttons("walking_speed", selected="4")
        ui.update_radio_buttons("walk_time", selected="10")
        ui.update_numeric("custom_walking_speed", value="")
        ui.update_numeric("custom_minutes", value="")
        filter_error_text.set("")
        reset_filters_state = {
            "area": "all",
            "speed": 4,
            "threshold": 10,
            "custom": False,
            "custom_speed": False,
        }
        applied.set(reset_filters_state)
        results_snapshot.set(calculate_matches(reset_filters_state))
        has_searched.set(True)
        refresh_applied_map_styles(reset_filters_state, None)
        view_state.set("results")
        results_panel_collapsed.set(False)
        show_details.set(False)
        selected_park.set(None)
        fit_after_layout(reset_filters_state)

    @render.ui
    def filter_error():
        if filter_error_text():
            return ui.tags.div(filter_error_text(), class_="filter-error", role="alert")
        return ui.tags.div()

    @reactive.effect
    def toggle_parks():
        input.map_viewport()  # first value arrives after the browser map view has been created
        if mask_layer is not None and mask_layer not in map_widget.layers:
            map_widget.add(mask_layer)
        for layer in map_layers["parks"]:
            if isinstance(layer, GeoJSON):
                if not hasattr(layer, "_greenspace_all_data"):
                    setattr(layer, "_greenspace_all_data", layer.data)
                should_show = input.show_parks()
            else:
                should_show = input.show_parks()
            if should_show and layer not in map_widget.layers:
                map_widget.add(layer)
            elif not should_show and layer in map_widget.layers:
                map_widget.remove_layer(layer)

    @reactive.effect
    def toggle_local_boards():
        should_show = bool(input.show_local_boards()) and local_board_layer is not None
        if should_show and local_board_layer not in map_widget.layers:
            map_widget.add(local_board_layer)
        elif local_board_layer is not None and not should_show and local_board_layer in map_widget.layers:
            map_widget.remove_layer(local_board_layer)

    @reactive.effect
    @reactive.event(input.show_networks)
    def toggle_networks():
        for layers in map_layers["networks"].values():
            for layer in layers:
                if input.show_networks() and layer not in map_widget.layers:
                    map_widget.add(layer)
                elif not input.show_networks() and layer in map_widget.layers:
                    map_widget.remove_layer(layer)

    @reactive.effect
    def toggle_network_types():
        visibility = {
            "Footway": input.show_footway(),
            "Path": input.show_path(),
            "Track": input.show_track(),
            "Steps": input.show_steps(),
        }
        for network_type, layers in map_layers["networks"].items():
            for layer in layers:
                should_show = input.show_networks() and visibility[network_type]
                if should_show and layer not in map_widget.layers:
                    map_widget.add(layer)
                elif not should_show and layer in map_widget.layers:
                    map_widget.remove_layer(layer)

    @reactive.effect
    @reactive.event(input.selected_result_park)
    def select_result_park():
        park_id = input.selected_result_park()
        if park_id in PARKS_BY_ID:
            navigation_source.set("results")
            view_state.set("details")
            selected_park.set(park_id)
            show_details.set(True)
            focus_park(park_id)

    def padded_bounds(bounds):
        min_latitude, min_longitude, max_latitude, max_longitude = bounds
        latitude_padding = max((max_latitude - min_latitude) * 0.12, 0.008)
        longitude_padding = max((max_longitude - min_longitude) * 0.12, 0.008)
        return (
            min_latitude - latitude_padding,
            min_longitude - longitude_padding,
            max_latitude + latitude_padding,
            max_longitude + longitude_padding,
        )

    def area_bounds(area):
        """(south, west, north, east) of the selected Local Board boundary, or of all boards."""
        if REAL_DATA is None:
            return None
        boards = REAL_DATA.local_boards
        if area != "all":
            boards = boards[boards["LocalBoa_2"].astype(str) == area]
        if boards.empty:
            return None
        min_x, min_y, max_x, max_y = boards.total_bounds
        return (min_y, min_x, max_y, max_x)

    def current_viewport():
        with reactive.isolate():
            try:
                return input.map_viewport()
            except Exception as error:
                print(f"map viewport unavailable: {error!r}")
                return None

    def fit_applied_area(filters):
        if REAL_DATA is None:
            map_widget.center = AUCKLAND_CENTER
            map_widget.zoom = 12
            return
        bounds = area_bounds(filters["area"])
        if bounds is None:
            return
        viewport = current_viewport()
        if viewport is None:
            south, west, north, east = padded_bounds(bounds)
            map_widget.fit_bounds([[south, west], [north, east]])
            return
        center, zoom = compute_view(bounds, viewport, gain=AREA_ZOOM_GAIN)
        map_widget.center = center
        map_widget.zoom = zoom

    pending_fit = {"filters": None, "until": 0.0}

    def fit_after_layout(filters):
        # The Results panel opens after Apply and resizes the map, so keep refitting to the
        # applied area for a short window as the browser reports the new map size.
        fit_applied_area(filters)
        pending_fit["filters"] = filters
        pending_fit["until"] = time.monotonic() + 1.5

    initial_fit_done = {"value": False}

    @reactive.effect
    def fit_on_viewport_change():
        input.map_viewport()
        if not initial_fit_done["value"]:
            initial_fit_done["value"] = True
            with reactive.isolate():
                fit_applied_area(applied())
        elif pending_fit["filters"] is not None and time.monotonic() < pending_fit["until"]:
            fit_applied_area(pending_fit["filters"])

    styled_state = {"key": ("all", None)}

    def refresh_applied_map_styles(filters, matches):
        selected_board = filters["area"]
        matching_ids = None if matches is None else frozenset(park["id"] for park in matches)
        key = (selected_board, matching_ids)
        if styled_state["key"] == key:
            return
        styled_state["key"] = key
        # Restyling re-creates a layer's paths in the browser, so restyle bottom-up: mask, parks, then boards.
        if mask_layer is not None:
            data = mask_data(selected_board)
            if mask_layer.data is not data:
                mask_layer.data = data
        for layer in map_layers["parks"]:
            if isinstance(layer, GeoJSON):
                layer.style_callback = park_style_for(selected_board, matching_ids)
        if local_board_layer is not None:
            local_board_layer.style_callback = board_style_for(selected_board)

    def park_bounds(park_id):
        coordinates = PARKS_BY_ID[park_id]["bounds"]
        latitudes = [coordinate[0] for coordinate in coordinates]
        longitudes = [coordinate[1] for coordinate in coordinates]
        return (min(latitudes), min(longitudes), max(latitudes), max(longitudes))

    def focus_park(park_id, closer=False):
        """Shared park zoom for map clicks, Results cards and "Zoom to park".

        The park bounds are expanded by a buffer so streets around the park stay visible, then
        fitted inside the unobstructed map area. The buffer scales with park size, and a maximum
        zoom stops small parks becoming extreme close-ups. closer=True uses a smaller buffer and
        a higher zoom cap, so it is never further out than the initial view.
        """
        if park_id not in PARKS_BY_ID:
            return
        buffer, max_zoom = (PARK_CLOSE_BUFFER, PARK_CLOSE_MAX_ZOOM) if closer else (PARK_FOCUS_BUFFER, PARK_FOCUS_MAX_ZOOM)
        bounds = expand_bounds(park_bounds(park_id), buffer)
        viewport = current_viewport()
        if viewport is None:
            map_widget.fit_bounds([[bounds[0], bounds[1]], [bounds[2], bounds[3]]])
            return
        center, zoom = compute_view(bounds, viewport, max_zoom=max_zoom)
        # Setting centre and zoom makes the browser animate the view change.
        map_widget.center = center
        map_widget.zoom = zoom

    def fit_selected_park():
        focus_park(selected_park(), closer=True)

    @reactive.effect
    def highlight_selected():
        park_id = selected_park()
        if REAL_DATA is None:
            for layer in map_layers["parks"]:
                if layer.name == PARKS_BY_ID.get(park_id, {}).get("name"):
                    layer.color = "#245B45"
                    layer.weight = 4
                    layer.fill_opacity = 0.52
                else:
                    layer.color = "#39785A"
                    layer.weight = 2
                    layer.fill_opacity = 0.28
            return
        feature = None
        if park_id and REAL_DATA is not None:
            for park in getattr(map_layers["parks"][0], "_greenspace_all_data", {}).get("features", []):
                if str(park["properties"].get("GlobalID", "")) == str(park_id):
                    feature = park
                    break
        highlight_data = {"type": "FeatureCollection", "features": [feature] if feature else []}
        if highlight_layer.data != highlight_data:
            highlight_layer.data = highlight_data
        if feature and highlight_layer not in map_widget.layers:
            map_widget.add(highlight_layer)
        elif not feature and highlight_layer in map_widget.layers:
            map_widget.remove_layer(highlight_layer)

    @render.ui
    def status_text():
        filters = applied()
        threshold = f"{filters['threshold']} min custom" if filters["custom"] else f"{filters['threshold']} min"
        area = "All Auckland" if filters["area"] == "all" else filters["area"]
        return ui.tags.span(f"{area} | {filters['speed']:g} km/h | {threshold}")

    def sorted_matches():
        parks = list(results_snapshot())
        key = sort_key()
        reverse = key == "area"
        if key == "area":
            return sorted(parks, key=lambda park: park.get("area") if park.get("area") is not None else -1, reverse=True)
        if key == "length":
            return sorted(parks, key=lambda park: park.get("length") if park.get("length") is not None else -1, reverse=True)
        return sorted(parks, key=lambda park: park["name"])

    @render.ui
    def results_content():
        if not has_searched() and view_state() == "map":
            return ui.tags.div()
        if show_details() and selected_park() in PARKS_BY_ID:
            park = PARKS_BY_ID[selected_park()]
            network_composition = park.get("network") or {}
            composition_palette = {
                "Footway": "#245B45", "Path": "#D97706", "Track": "#7C5C3C", "Steps": "#8B4FB3",
                "Service road": "#5C7D8A", "Cycleway": "#2F855A", "Road": "#687A70",
                "Pedestrian": "#B7791F", "Bridleway": "#A0522D", "Unclassified": "#8A9190", "Other": "#555555",
            }
            composition_colors = []
            cursor = 0.0
            for kind, percentage in network_composition.items():
                color = composition_palette.get(kind, "#555555")
                start = cursor
                cursor += percentage
                composition_colors.extend([f"{color} {start:.1f}%", f"{color} {min(cursor, 100):.1f}%"])
            donut_style = "background: conic-gradient(" + ", ".join(composition_colors) + ");"
            composition = ui.tags.div(
                ui.tags.div(ui.tags.div(class_="network-donut-hole"), class_="network-donut", style=donut_style),
                ui.tags.div(*[
                    ui.tags.div(
                        ui.tags.span(class_="composition-swatch", style=f"background:{composition_palette.get(kind, '#555555')}"),
                        ui.tags.span(kind, class_="composition-label"),
                        ui.tags.span(f"{percentage:.1f}%".rstrip("0").rstrip("."), class_="composition-value"),
                        class_="composition-row",
                    )
                    for kind, percentage in network_composition.items() if percentage > 0
                ], class_="composition-legend"),
                class_="network-composition-chart",
            ) if network_composition else ui.tags.p("Network composition unavailable", class_="muted")

            applied_speed = float(applied()["speed"])
            if REAL_DATA is not None:
                length = park.get("length")
                if length is not None and applied_speed > 0:
                    duration_minutes = length / applied_speed * 60
                    duration_rows = ui.tags.div(
                        ui.tags.span(f"At {applied_speed:g} km/h", class_="walking-speed-label"),
                        ui.tags.strong(f"{duration_minutes:.1f} min", class_="walking-duration"),
                        class_="walking-duration-summary",
                    )
                else:
                    duration_rows = ui.tags.p("Network length unavailable", class_="muted")
            elif applied_speed in park["duration"]:
                duration_rows = ui.tags.div(
                    ui.tags.span(f"At {applied_speed:g} km/h", class_="walking-speed-label"),
                    ui.tags.strong(f"{park['duration'][applied_speed]:.1f} min", class_="walking-duration"),
                    class_="walking-duration-summary",
                )
            else:
                duration_minutes = park.get("length", 0) / applied_speed * 60 if applied_speed > 0 and park.get("length") else None
                duration_rows = ui.tags.div(
                    ui.tags.span(f"At {applied_speed:g} km/h", class_="walking-speed-label"),
                    ui.tags.strong(f"{duration_minutes:.1f} min", class_="walking-duration"),
                    class_="walking-duration-summary",
                ) if duration_minutes is not None else ui.tags.p("Walking time unavailable", class_="muted")
            return ui.tags.div(
                ui.tags.div(
                    ui.input_action_button("back_results", ui.tags.span("← Back", class_="back-button"), class_="back-link"),
                    ui.input_action_button("zoom_park", "Zoom to park", class_="zoom-button"),
                    class_="detail-toolbar",
                ),
                ui.tags.p("ILLUSTRATIVE DEMO", class_="demo-label") if REAL_DATA is None else None,
                ui.h1(park["name"]),
                ui.tags.p(f"{park['local_board']} Local Board", class_="detail-area"),
                ui.tags.div(
                    ui.tags.div(ui.tags.span("Park area", class_="metric-label"), ui.tags.strong(f"{park['area']:.1f} ha" if park.get('area') is not None else "Unavailable"), class_="detail-metric"),
                    ui.tags.div(ui.tags.span("Network length", class_="metric-label"), ui.tags.strong(f"{park['length']:.1f} km" if park.get('length') is not None else "Unavailable"), class_="detail-metric"),
                    class_="detail-metrics",
                ),
                ui.h2("Estimated walking time"),
                duration_rows,
                ui.tags.p("Estimated time to walk the entire mapped path network.", class_="duration-explanation"),
                ui.h2("Environmental characteristics"),
                ui.tags.div(
                    ui.tags.span("Mean NDVI", class_="environment-label"),
                    ui.tags.span("Data unavailable", class_="environment-value unavailable"),
                    ui.tags.span("Tree canopy cover", class_="environment-label"),
                    ui.tags.span("Data unavailable", class_="environment-value unavailable"),
                    class_="environment-grid",
                ),
                ui.tags.p("Validated park-level environmental data has not been integrated.", class_="detail-note"),
                ui.h2("Walking network composition"),
                composition,
                ui.tags.p("Percentages use verified mapped network length. Road category groups primary, secondary, tertiary, residential and living-street segments; all other known categories retain their OSM highway name.", class_="detail-note") if network_composition else None,
                class_="details-content",
            )

        parks = sorted_matches()
        count = len(parks)
        areas = [park["area"] for park in parks if park.get("area") is not None]
        lengths = [park["length"] for park in parks if park.get("length") is not None]
        average_area = sum(areas) / len(areas) if areas else 0
        average_length = sum(lengths) / len(lengths) if lengths else 0
        cards = []
        for park in parks:
            cards.append(ui.tags.button(
                ui.tags.span(park["name"], class_="park-name"),
                ui.tags.span(
                    (
                        f"{park['area']:.1f} ha" +
                        (f"  |  {park['length']:.1f} km network" if park.get('length') is not None else "  |  Network unavailable")
                        if park.get('area') is not None else
                        "Area unavailable" +
                        (f"  |  {park['length']:.1f} km network" if park.get('length') is not None else "  |  Network unavailable")
                    ),
                    class_="park-meta",
                ),
                ui.tags.span("›", class_="park-arrow"),
                type="button",
                class_="park-result",
                data_park_id=park["id"],
            ))
        return ui.tags.div(
            ui.tags.p("ILLUSTRATIVE DEMO", class_="demo-label") if REAL_DATA is None else None,
            ui.h1("Search results"),
            ui.tags.div(
                ui.tags.div(ui.tags.strong(str(count)), ui.tags.span("matching parks", class_="summary-label"), class_="summary-item"),
                ui.tags.div(ui.tags.strong(f"{average_area:.1f}"), ui.tags.span("average ha", class_="summary-label"), class_="summary-item"),
                ui.tags.div(ui.tags.strong(f"{average_length:.1f}"), ui.tags.span("average km network", class_="summary-label"), class_="summary-item"),
                class_="search-summary",
            ),
            ui.tags.div(
                ui.tags.span("Sort by", class_="sort-label"),
                ui.input_select("sort_results", None, {"name": "Park name", "area": "Area", "length": "Network length"}, selected=sort_key()),
                class_="sort-control",
            ),
            ui.tags.div(
                *cards,
                ui.tags.div("No parks match the applied filters.", class_="empty-results") if count == 0 else None,
                id="park_results_list",
                class_="park-results",
            ),
            class_="results-content",
        )

    @reactive.effect
    def update_sort():
        value = input.sort_results()
        if value in {"name", "area", "length"}:
            sort_key.set(value)

    @reactive.effect
    @reactive.event(input.back_results)
    async def back_to_results():
        show_details.set(False)
        selected_park.set(None)
        if navigation_source() == "results":
            view_state.set("results")
            await session.send_custom_message("restore_results_scroll", {"scroll": results_scroll()})
        else:
            view_state.set("map")

    @reactive.effect
    @reactive.event(input.zoom_park)
    def zoom_selected():
        fit_selected_park()

    @reactive.effect
    def capture_results_scroll():
        value = input.results_scroll()
        if isinstance(value, (int, float)):
            results_scroll.set(float(value))


app = App(app_ui(area_choices=LOCAL_BOARD_CHOICES), server, static_assets={"/": Path(__file__).parent / "www"})

if __name__ == "__main__":
    app.run()
