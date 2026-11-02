from shiny import ui


SEARCH_ICON = ui.HTML('<svg class="park-search-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"></circle><path d="m21 21-4.3-4.3"></path></svg>')


def filter_panel(collapsed: bool = False, area_choices: dict[str, str] | None = None, park_choices: dict[str, str] | None = None) -> ui.Tag:
    choices = area_choices or {"all": "All Auckland"}
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
