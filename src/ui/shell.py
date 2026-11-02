from shiny import ui
from shinywidgets import output_widget

from .filters import filter_panel
from .results import results_panel
from .status_bar import status_bar


def app_ui(area_choices: dict[str, str] | None = None, show_demo_notice: bool = True, park_choices: dict[str, str] | None = None) -> ui.Tag:
    return ui.page_fluid(
        ui.tags.head(ui.tags.link(rel="stylesheet", href="styles.css")),
        ui.tags.header(ui.tags.h1("Auckland Greenspace Explorer", class_="app-title"), class_="app-header"),
        ui.tags.div(
            ui.tags.div(
                ui.tags.div(filter_panel(area_choices=area_choices, park_choices=park_choices), class_="filter-panel-slot"),
                ui.tags.div(output_widget("map"), class_="map-container"),
                None if show_demo_notice else ui.input_action_button(
                    "toggle_board_mode", "Select manually", class_="board-mode-button",
                    title="Click a Local Board to switch the geographical area", aria_pressed="false",
                ),
                ui.tags.div(
                    ui.tags.button(
                        ui.HTML('''<svg class="layers-icon" xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z"></path><path d="m22 12.5-9.17 4.17a2 2 0 0 1-1.66 0L2 12.5"></path><path d="m22 17.5-9.17 4.17a2 2 0 0 1-1.66 0L2 17.5"></path></svg>'''),
                        id="layers_toggle",
                        type="button",
                        class_="layers-button",
                        aria_label="Toggle map layers",
                    ),
                    ui.tags.div(
                        ui.tags.h2("Map layers"),
                        ui.tags.p("Main layers", class_="layers-section-title"),
                        ui.input_checkbox("show_parks", "Park boundaries", True),
                        ui.input_checkbox("show_local_boards", "Local Board boundaries", True),
                        ui.input_checkbox("show_networks", "Walking networks", True),
                        ui.tags.p("Walking network types", class_="layers-section-title"),
                        ui.input_checkbox("show_footway", "Footway", True),
                        ui.input_checkbox("show_path", "Path", True),
                        ui.input_checkbox("show_track", "Track", True),
                        ui.input_checkbox("show_steps", "Steps", True),
                        class_="layers-content",
                    ),
                    class_="layers-control",
                ),
                status_bar(),
                ui.tags.div("Illustrative demo data only - not Auckland statistics", class_="demo-notice") if show_demo_notice else None,
                class_="map-workspace",
            ),
            ui.input_action_button("toggle_results_panel", "›", class_="results-toggle", title="Collapse results panel", style="display: none;"),
            ui.tags.div(results_panel(), class_="sliding-panel", id="right_panel"),
            class_="app-shell app-layout",
        ),
        ui.tags.script("""
            document.addEventListener('click', function (event) {
                if (event.target.closest('#layers_toggle')) {
                    event.target.closest('.layers-control')?.classList.toggle('open');
                    return;
                }
                if (!event.target.closest('.layers-control')) {
                    document.querySelector('.layers-control')?.classList.remove('open');
                }
                const result = event.target.closest('[data-park-id]');
                if (result) {
                    Shiny.setInputValue('selected_result_park', result.dataset.parkId, {priority: 'event'});
                    const scroller = document.querySelector('.results-panel');
                    if (scroller) Shiny.setInputValue('results_scroll', scroller.scrollTop, {priority: 'event'});
                }
            });
            function syncCustomFilterInputs() {
                const speedCustom = document.querySelector('#walking_speed input[value="custom"]');
                const timeCustom = document.querySelector('#walk_time input[value="custom"]');
                document.querySelector('.custom-speed')?.classList.toggle('visible', !!speedCustom?.checked);
                document.querySelector('.custom-time')?.classList.toggle('visible', !!timeCustom?.checked);
                document.querySelectorAll('.custom-speed input[type="number"]').forEach(function (input) {
                    input.placeholder = 'Enter speed in km/h';
                });
                document.querySelectorAll('.custom-time input[type="number"]').forEach(function (input) {
                    input.placeholder = 'Enter minutes';
                });
            }
            document.addEventListener('change', function (event) {
                if (event.target.closest('#walking_speed, #walk_time')) syncCustomFilterInputs();
            });
            document.addEventListener('shiny:connected', syncCustomFilterInputs);
            requestAnimationFrame(syncCustomFilterInputs);
            new MutationObserver(syncCustomFilterInputs).observe(document.body, {childList: true, subtree: true});
            const boardTooltip = document.createElement('div');
            boardTooltip.className = 'board-tooltip';
            boardTooltip.innerHTML = '<strong></strong><span>Click to explore this area</span>';
            document.body.appendChild(boardTooltip);
            document.addEventListener('mousemove', function (event) {
                const path = event.target.closest ? event.target.closest('path.board-hit') : null;
                const token = path && Array.from(path.classList).find(function (name) { return name.startsWith('board-name-'); });
                if (!token) {
                    boardTooltip.style.display = 'none';
                    return;
                }
                boardTooltip.firstChild.textContent = decodeURIComponent(token.slice('board-name-'.length));
                boardTooltip.style.display = 'block';
                const x = Math.min(event.clientX + 14, window.innerWidth - boardTooltip.offsetWidth - 8);
                const y = Math.min(event.clientY + 16, window.innerHeight - boardTooltip.offsetHeight - 8);
                boardTooltip.style.left = Math.max(8, x) + 'px';
                boardTooltip.style.top = Math.max(8, y) + 'px';
            });
            function reportMapViewport() {
                const map = document.querySelector('.map-container');
                if (!map || !window.Shiny || !Shiny.setInputValue) return;
                const rect = map.getBoundingClientRect();
                if (rect.width < 10 || rect.height < 10) return;
                const margin = 16;
                let left = margin, top = margin;
                const filter = document.querySelector('.filter-panel-slot .filter-panel');
                if (filter) {
                    const f = filter.getBoundingClientRect();
                    if (f.right - rect.left < rect.width * 0.6) left = Math.max(margin, f.right - rect.left + margin);
                    else top = Math.max(margin, f.bottom - rect.top + margin);
                }
                Shiny.setInputValue('map_viewport', {
                    width: Math.round(rect.width), height: Math.round(rect.height),
                    left: Math.round(left), right: 64, top: Math.round(top), bottom: margin + 24
                });
            }
            let mapViewportObserver = null;
            function observeMapViewport() {
                // Wait for the Leaflet view to exist so layers added afterwards find their widget models.
                const leaflet = document.querySelector('.map-container .leaflet-container');
                const filter = document.querySelector('.filter-panel-slot .filter-panel');
                if (!leaflet || !filter) return setTimeout(observeMapViewport, 100);
                mapViewportObserver = new ResizeObserver(reportMapViewport);
                [document.querySelector('.map-container'), filter].forEach(function (target) { mapViewportObserver.observe(target); });
                reportMapViewport();
            }
            document.addEventListener('shiny:connected', observeMapViewport);
            window.addEventListener('resize', reportMapViewport);
            const activeBoardStyle = document.createElement('style');
            document.head.appendChild(activeBoardStyle);
            Shiny.addCustomMessageHandler('active_board', function (message) {
                // The active board stops receiving pointer events, so it neither highlights nor shows a tooltip.
                if (!message.name) { activeBoardStyle.textContent = ''; return; }
                const token = 'board-name-' + encodeURIComponent(message.name);
                activeBoardStyle.textContent = 'path.board-hit.' + CSS.escape(token) + ' { pointer-events: none !important; }';
                // Clear a hover style left on the board that was under the cursor when it became active.
                document.querySelectorAll('path.board-hit.' + CSS.escape(token)).forEach(function (path) {
                    path.dispatchEvent(new MouseEvent('mouseout', {bubbles: true}));
                });
            });
            Shiny.addCustomMessageHandler('board_mode', function (message) {
                const button = document.getElementById('toggle_board_mode');
                button?.classList.toggle('active', message.active);
                button?.setAttribute('aria-pressed', message.active ? 'true' : 'false');
            });
            Shiny.addCustomMessageHandler('panel_state', function (message) {
                const panel = document.getElementById('right_panel');
                const app = document.querySelector('.app-layout');
                const toggle = document.getElementById('toggle_results_panel');
                if (panel) {
                    panel.classList.toggle('open', message.results_visible);
                    panel.classList.toggle('collapsed', message.results_collapsed);
                }
                app?.classList.toggle('results-collapsed', message.results_collapsed);
                if (toggle) {
                    toggle.style.display = message.results_visible ? 'block' : 'none';
                }
                requestAnimationFrame(function () {
                    if (toggle) {
                        const appRect = app?.getBoundingClientRect();
                        const anchor = message.results_collapsed
                            ? document.querySelector('.map-workspace')?.getBoundingClientRect()
                            : panel?.getBoundingClientRect();
                        if (appRect && anchor) {
                            toggle.style.left = (message.results_collapsed
                                ? anchor.right - appRect.left
                                : anchor.left - appRect.left) + 'px';
                            toggle.style.top = (anchor.top + anchor.height / 2 - appRect.top) + 'px';
                            toggle.style.transform = 'translate(-100%, -50%)';
                        }
                    }
                    window.dispatchEvent(new Event('resize'));
                    document.querySelectorAll('.leaflet-container').forEach(function (container) {
                        if (container._leaflet_map) container._leaflet_map.invalidateSize();
                    });
                });
                if (toggle) {
                    toggle.textContent = message.results_collapsed ? '‹' : '›';
                    toggle.title = message.results_collapsed ? 'Expand results panel' : 'Collapse results panel';
                }
                const filter = document.querySelector('.filter-panel-slot .filter-panel');
                filter?.classList.toggle('collapsed', message.filter_collapsed);
            });
            Shiny.addCustomMessageHandler('restore_results_scroll', function (message) {
                requestAnimationFrame(function () {
                    const scroller = document.querySelector('.results-panel');
                    if (scroller) scroller.scrollTop = message.scroll;
                });
            });
        """),
    )
