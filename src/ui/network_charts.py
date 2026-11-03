"""Rendering helpers for the walking-network charts and road line styles (no business rules).

Visual encoding: colour always means highway category (donut, legend, map lines);
pedestrian accessibility uses neutral greys with solid/striped/dotted textures instead.
"""

from __future__ import annotations

from collections.abc import Mapping

from shiny import ui

from src.data.network import ACCESS_CLASSES, HIGHWAY_CATEGORIES, NetworkSummary, shares

# One palette for map road lines, the donut and the legends.
CATEGORY_COLORS = {
    "Walking paths": "#287A55",
    "Nature trails": "#D99A27",
    "Shared-use paths": "#258A9B",
    "Local roads": "#6476A5",
    "Major roads": "#C65D4B",
}
# Neutral textures: solid, dash-dot, dots. Deliberately not part of the highway palette.
ACCESS_FILLS = {
    "Walkable": "#4B5563",
    "Conditional": "repeating-linear-gradient(90deg, #4B5563 0 4px, #E5E7EB 4px 6px, #4B5563 6px 8px, #E5E7EB 8px 10px)",
    "Restricted": "radial-gradient(#4B5563 1.2px, #E5E7EB 1.4px) 0 0 / 5px 5px",
}
# Leaflet dashArray: solid, dash-dot, dotted.
ACCESS_DASH = {"Walkable": "", "Conditional": "10 4 2 4", "Restricted": "1 5"}

EMPTY_NETWORK_TEXT = "No road segments match the selected filters."
WORKING_ASSUMPTION_NOTE = (
    "Missing access and foot tags are treated as Walkable as a working assumption, "
    "not as verified pedestrian accessibility."
)


def road_line_style(category: str, access: str) -> dict:
    """Colour by highway category, dash by pedestrian access. Roads never take pointer events."""
    return {
        "color": CATEGORY_COLORS[category],
        "weight": 3,
        "opacity": 0.9,
        "dashArray": ACCESS_DASH[access],
        "interactive": False,
    }


def _legend(values: Mapping[str, float], fills: Mapping[str, str], percentages: Mapping[str, float], order: tuple[str, ...]) -> ui.Tag:
    return ui.tags.div(
        *[
            ui.tags.div(
                ui.tags.span(class_="composition-swatch", style=f"background:{fills[name]}"),
                ui.tags.span(name, class_="composition-label"),
                ui.tags.span(f"{values[name]:.1f} km · {percentages[name]:.1f}%", class_="composition-value"),
                class_="composition-row",
            )
            for name in order if values.get(name, 0.0) > 0
        ],
        class_="composition-legend",
    )


def _stacked_bar(title: str, values: Mapping[str, float], fills: Mapping[str, str], total: float, order: tuple[str, ...]) -> ui.Tag:
    percentages = shares(values, total)
    segments = [
        ui.tags.span(class_="stack-segment", style=f"width:{percentages[name]:.2f}%;background:{fills[name]}", title=f"{name}: {percentages[name]:.1f}%")
        for name in order if percentages.get(name, 0.0) > 0
    ]
    return ui.tags.div(
        ui.h2(title),
        ui.tags.div(*segments, class_="stack-bar", role="img", aria_label=title),
        _legend(values, fills, percentages, order),
        class_="network-chart",
    )


def _donut(title: str, values: Mapping[str, float], fills: Mapping[str, str], total: float, order: tuple[str, ...]) -> ui.Tag:
    percentages = shares(values, total)
    stops, cursor = [], 0.0
    for name in order:
        share = percentages.get(name, 0.0)
        if share <= 0:
            continue
        stops.extend([f"{fills[name]} {cursor:.2f}%", f"{fills[name]} {min(cursor + share, 100):.2f}%"])
        cursor += share
    return ui.tags.div(
        ui.h2(title),
        ui.tags.div(
            ui.tags.div(ui.tags.div(class_="network-donut-hole"), class_="network-donut", style="background: conic-gradient(" + ", ".join(stops) + ");"),
            _legend(values, fills, percentages, order),
            class_="network-composition-chart",
        ),
        class_="network-chart",
    )


def network_bars(summary: NetworkSummary, empty_text: str = EMPTY_NETWORK_TEXT) -> ui.Tag:
    """Results layout: two compact stacked bars drawn from one summary (one shared total)."""
    if summary.total_km <= 0:
        return ui.tags.p(empty_text, class_="muted network-empty")
    return ui.tags.div(
        _stacked_bar("Network accessibility", summary.by_access, ACCESS_FILLS, summary.total_km, ACCESS_CLASSES),
        _stacked_bar("Network composition", summary.by_category, CATEGORY_COLORS, summary.total_km, HIGHWAY_CATEGORIES),
        class_="network-bars",
    )


def network_donuts(summary: NetworkSummary, empty_text: str = EMPTY_NETWORK_TEXT) -> ui.Tag:
    """Details layout: composition donut with the accessibility stacked bar below it, from one summary."""
    if summary.total_km <= 0:
        return ui.tags.p(empty_text, class_="muted network-empty")
    return ui.tags.div(
        _donut("Network composition", summary.by_category, CATEGORY_COLORS, summary.total_km, HIGHWAY_CATEGORIES),
        _stacked_bar("Network accessibility", summary.by_access, ACCESS_FILLS, summary.total_km, ACCESS_CLASSES),
        class_="network-donuts",
    )
