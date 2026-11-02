from shiny import ui


def park_details_panel() -> ui.Tag:
    """Return the placeholder park detail view."""
    return ui.tags.section(
        ui.input_action_button("back_to_results", "Back to results"),
        ui.tags.div("Select a park to view details.", id="park_detail_content"),
        id="park_details_panel",
        class_="park-details-panel",
    )
