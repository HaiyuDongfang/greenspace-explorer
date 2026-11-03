from shiny import ui

from src.data.network import ACCESS_CLASSES, DEFAULT_ROAD_FILTER, HIGHWAY_CATEGORIES


SEARCH_ICON = ui.HTML('<svg class="park-search-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"></circle><path d="m21 21-4.3-4.3"></path></svg>')


def road_filter_controls() -> list[ui.Tag]:
    """Draft Road Filter widgets. Their values are read only when the shared Apply button is pressed."""
    return [
        ui.tags.div(
            ui.input_checkbox_group(
                "road_highway", "Highway category", {name: name for name in HIGHWAY_CATEGORIES},
                selected=[name for name in HIGHWAY_CATEGORIES if name in DEFAULT_ROAD_FILTER.categories],
            ),
            ui.input_checkbox_group(
                "road_access", "Pedestrian accessibility", {name: name for name in ACCESS_CLASSES},
                selected=[name for name in ACCESS_CLASSES if name in DEFAULT_ROAD_FILTER.access],
            ),
            class_="road-check-groups",
        ),
    ]


def filter_panel(collapsed: bool = False, area_choices: dict[str, str] | None = None, park_choices: dict[str, str] | None = None, road_filter: bool = False) -> ui.Tag:
    choices = area_choices or {"all": "All Auckland"}
    park_controls = [
        ui.tags.div(
            SEARCH_ICON,
            ui.input_selectize(
                "park_search", None, {"": "", **(park_choices or {})},
                options={"placeholder": "Search park name...", "maxOptions": 8, "plugins": ["clear_button"], "openOnFocus": False, "onType": ui.js_eval("function(text) { if (!text) { this.close(); } }")},
            ),
            class_="park-search",
        ),
        ui.input_select("area", "Geographical area", choices, selected="all"),
        ui.input_radio_buttons("walking_speed", "Walking speed", {
            "2": ui.tags.span(ui.tags.strong("2", class_="chip-value"), ui.tags.span("km/h", class_="chip-unit"), class_="filter-chip-content"),
            "3": ui.tags.span(ui.tags.strong("3", class_="chip-value"), ui.tags.span("km/h", class_="chip-unit"), class_="filter-chip-content"),
            "4": ui.tags.span(ui.tags.strong("4", class_="chip-value"), ui.tags.span("km/h", class_="chip-unit"), class_="filter-chip-content"),
            "custom": ui.tags.span(ui.tags.strong("Custom", class_="chip-value chip-value-custom"), ui.tags.span("km/h", class_="chip-unit"), class_="filter-chip-content"),
        }, selected="4"),
        ui.tags.div(ui.input_numeric("custom_walking_speed", "Custom walking speed (km/h)", None, min=0.1, max=30), class_="custom-speed"),
        ui.input_radio_buttons("walk_time", "Minimum walking time", {
            "10": ui.tags.span(ui.tags.strong("10", class_="chip-value"), ui.tags.span("min", class_="chip-unit"), class_="filter-chip-content"),
            "30": ui.tags.span(ui.tags.strong("30", class_="chip-value"), ui.tags.span("min", class_="chip-unit"), class_="filter-chip-content"),
            "60": ui.tags.span(ui.tags.strong("60", class_="chip-value"), ui.tags.span("min", class_="chip-unit"), class_="filter-chip-content"),
            "custom": ui.tags.span(ui.tags.strong("Custom", class_="chip-value chip-value-custom"), ui.tags.span("minutes", class_="chip-unit"), class_="filter-chip-content"),
        }, selected="10"),
        ui.tags.div(ui.input_numeric("custom_minutes", "Custom walking time (minutes)", None, min=1, max=180), class_="custom-time"),
    ]
    # Both panes stay in the DOM, so each tab keeps its draft values while the other is shown.
    controls = (
        [ui.navset_tab(
            ui.nav_panel("Park Filter", *park_controls, value="Park Filter"),
            ui.nav_panel("Road Filter", *road_filter_controls(), value="Road Filter"),
            id="filter_tab",
        )]
        if road_filter else park_controls
    )
    return ui.tags.aside(
        ui.input_action_button(
            "toggle_filter_panel",
            ui.tags.span(
                ui.tags.span("Park filters", class_="filter-title"),
                ui.tags.span("⌄", class_="filter-chevron", aria_hidden="true"),
                class_="filter-toggle-content",
            ),
            class_="filter-toggle",
        ),
        ui.tags.div(
            *controls,
            ui.tags.div(
                ui.input_action_button("apply_filters", "Apply filters", class_="primary-action"),
                ui.input_action_button("reset_filters", "Reset", class_="secondary-action"),
                class_="filter-actions",
            ),
            ui.output_ui("filter_error"),
            class_="filter-content",
        ),
        class_= "filter-panel collapsed" if collapsed else "filter-panel",
    )
