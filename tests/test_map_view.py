"""Tests for src.data.map_view; runnable with pytest or `python -m tests.test_map_view`."""

from math import isclose, log, pi, radians, tan

from src.data.map_view import compute_view, expand_bounds

VIEWPORT = {"width": 1000, "height": 600, "left": 100, "right": 0, "top": 0, "bottom": 0}


def offset_from_centre(latitude, longitude, centre, zoom):
    def xy(lat, lon):
        world = 256 * 2**zoom
        return (lon + 180) / 360 * world, (pi - log(tan(pi / 4 + radians(lat) / 2))) / (2 * pi) * world

    cx, cy = xy(*centre)
    x, y = xy(latitude, longitude)
    return x - cx, y - cy


def test_gain_zooms_closer_without_clipping():
    for bounds in [(-36.95, 174.65, -36.85, 174.80), (-37.2, 174.5, -36.2, 175.2)]:
        base = compute_view(bounds, VIEWPORT)[1]
        centre, zoom = compute_view(bounds, VIEWPORT, gain=0.25)
        assert base <= zoom <= base + 0.25
        west_x, north_y = offset_from_centre(bounds[2], bounds[1], centre, zoom)
        east_x, south_y = offset_from_centre(bounds[0], bounds[3], centre, zoom)
        assert -500 <= west_x and east_x <= 500 and -300 <= north_y and south_y <= 300


def test_bounds_fit_inside_free_area():
    bounds = (-36.95, 174.65, -36.85, 174.80)
    centre, zoom = compute_view(bounds, VIEWPORT)
    west_x, north_y = offset_from_centre(bounds[2], bounds[1], centre, zoom)
    east_x, south_y = offset_from_centre(bounds[0], bounds[3], centre, zoom)
    assert -500 + VIEWPORT["left"] <= west_x and east_x <= 500
    assert -300 <= north_y and south_y <= 300
    doubled = {**VIEWPORT, "width": VIEWPORT["width"] * 2, "height": VIEWPORT["height"] * 2}
    assert compute_view(bounds, doubled)[1] == zoom + 1


def test_left_padding_shifts_centre_west_of_board_centre():
    bounds = (-37.0, 174.6, -36.8, 174.9)
    padded, _ = compute_view(bounds, VIEWPORT)
    plain, _ = compute_view(bounds, {**VIEWPORT, "left": 0})
    assert padded[1] < plain[1]
    assert isclose(plain[1], 174.75, abs_tol=1e-6)


def test_max_zoom_caps_small_bounds_and_expand_bounds_grows_evenly():
    tiny = (-36.9000, 174.7000, -36.8999, 174.7001)
    assert compute_view(tiny, VIEWPORT, max_zoom=16)[1] == 16
    south, west, north, east = expand_bounds((-37.0, 174.0, -36.0, 175.0), 0.5)
    assert (south, west, north, east) == (-37.5, 173.5, -35.5, 175.5)


if __name__ == "__main__":
    test_bounds_fit_inside_free_area()
    test_gain_zooms_closer_without_clipping()
    test_left_padding_shifts_centre_west_of_board_centre()
    test_max_zoom_caps_small_bounds_and_expand_bounds_grows_evenly()
    print("map_view tests passed")
