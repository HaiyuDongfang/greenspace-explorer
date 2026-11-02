from shiny import ui


def results_panel() -> ui.Tag:
    return ui.tags.section(
        ui.output_ui("results_content"),
        id="results_panel",
        class_="results-panel",
    )
