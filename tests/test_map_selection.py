from src.ui.map import PARK_SELECTION_STYLE, selected_park_layer_order


def test_park_selection_style_matches_cyan_selection():
    assert PARK_SELECTION_STYLE == {
        "color": "#00E5FF",
        "weight": 3,
        "opacity": 1,
        "fillColor": "#00FFFF",
        "fillOpacity": 0.25,
    }


def test_selected_park_is_above_other_parks_without_reordering_other_layers():
    base, first_park, second_park, network, board = object(), object(), object(), object(), object()
    layers = (base, first_park, second_park, network, board)

    ordered = selected_park_layer_order(
        layers,
        (first_park, second_park),
        first_park,
    )

    assert ordered == (base, second_park, first_park, network, board)
    assert ordered.index(first_park) > ordered.index(second_park)
    assert ordered.index(network) == layers.index(network)
    assert ordered.index(board) == layers.index(board)


def test_selected_park_layer_order_is_unchanged_when_selection_is_not_visible():
    layers = (object(), object())

    assert selected_park_layer_order(layers, (object(),), object()) == layers
