"""Web Mercator view calculation for fitting bounds inside a padded viewport."""

from math import atan, degrees, exp, floor, log, log2, pi, radians, sinh, tan

TILE_SIZE = 256
MIN_ZOOM = 1
MAX_ZOOM = 18


def _mercator_y(latitude: float) -> float:
    return log(tan(pi / 4 + radians(latitude) / 2))


def _latitude_from_mercator_y(y: float) -> float:
    return degrees(atan(sinh(y)))


def expand_bounds(bounds: tuple[float, float, float, float], fraction: float) -> tuple[float, float, float, float]:
    """Grow (south, west, north, east) by fraction of its own height/width on every side."""
    south, west, north, east = bounds
    dy, dx = (north - south) * fraction, (east - west) * fraction
    return (max(south - dy, -85.0), west - dx, min(north + dy, 85.0), east + dx)


def compute_view(
    bounds: tuple[float, float, float, float],
    viewport: dict[str, float],
    max_zoom: int = MAX_ZOOM,
    gain: float = 0.0,
) -> tuple[tuple[float, float], float]:
    """Return ((latitude, longitude), zoom) showing bounds inside the unobstructed viewport area.

    bounds is (south, west, north, east) in EPSG:4326 degrees. viewport holds pixel
    values: width, height and the padding left, right, top, bottom that is covered by
    overlays or kept as margin. The zoom is an integer so tiles stay sharp.
    """
    south, west, north, east = bounds
    width, height = float(viewport["width"]), float(viewport["height"])
    pad_left, pad_right = float(viewport.get("left", 0)), float(viewport.get("right", 0))
    pad_top, pad_bottom = float(viewport.get("top", 0)), float(viewport.get("bottom", 0))
    free_width = max(width - pad_left - pad_right, 64.0)
    free_height = max(height - pad_top - pad_bottom, 64.0)

    longitude_fraction = max((east - west) / 360, 1e-9)
    latitude_fraction = max((_mercator_y(north) - _mercator_y(south)) / (2 * pi), 1e-9)
    zoom = min(
        log2(free_width / (TILE_SIZE * longitude_fraction)),
        log2(free_height / (TILE_SIZE * latitude_fraction)),
    )
    zoom = max(MIN_ZOOM, min(max_zoom, zoom))
    base = float(max(MIN_ZOOM, floor(zoom)))
    if gain:
        # Move gain closer than the integer fit, limited by the exact fit with halved margins so no clipping.
        tight_width = max(width - (pad_left + pad_right) / 2, 64.0)
        tight_height = max(height - (pad_top + pad_bottom) / 2, 64.0)
        limit = min(
            log2(tight_width / (TILE_SIZE * longitude_fraction)),
            log2(tight_height / (TILE_SIZE * latitude_fraction)),
        )
        zoom = max(base, min(base + gain, limit, max_zoom))
        zoom = floor(zoom * 64) / 64
    else:
        zoom = base

    world = TILE_SIZE * 2**zoom
    centre_x = ((west + east) / 2 + 180) / 360 * world
    centre_y = (pi - (_mercator_y(north) + _mercator_y(south)) / 2) / (2 * pi) * world
    # Shift the map centre so the bounds are centred in the free area, not the whole map.
    centre_x += (pad_right - pad_left) / 2
    centre_y += (pad_bottom - pad_top) / 2
    longitude = centre_x / world * 360 - 180
    latitude = _latitude_from_mercator_y(pi - centre_y / world * 2 * pi)
    return (latitude, longitude), zoom
