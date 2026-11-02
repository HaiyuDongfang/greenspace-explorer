from shiny import ui


def status_bar() -> ui.Tag:
    return ui.tags.div(ui.output_ui("status_text"), class_="status-bar", role="status")
