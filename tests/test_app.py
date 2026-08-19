"""Testes das funções puras do mapa (sem subir o Streamlit)."""

import pandas as pd

from app import channel_hex, make_folium_map, stations_with_channels


def test_channel_hex_is_a_css_color():
    color = channel_hex(0)
    assert color.startswith("#")
    assert len(color) == 7
    assert channel_hex(0) != channel_hex(1)


def test_stations_with_channels_are_one_based_for_display():
    stations = pd.DataFrame(
        {
            "station_id": ["100", "200"],
            "latitude": [-22.3, -22.3],
            "longitude": [-49.0, -49.0],
            "municipality": ["Bauru", "Bauru"],
            "operator": ["VIVO", "CLARO"],
        }
    )
    painted = stations_with_channels(stations, {"100": 0, "200": 1})
    assert list(painted["channel"]) == [0, 1]
    assert list(painted["canal"]) == [1, 2]


def test_folium_map_has_one_marker_per_station():
    painted = pd.DataFrame(
        {
            "station_id": ["100", "200"],
            "latitude": [-22.31, -22.32],
            "longitude": [-49.06, -49.07],
            "municipality": ["Bauru", "Bauru"],
            "operator": ["VIVO", "CLARO"],
            "channel": [0, 1],
            "canal": [1, 2],
        }
    )
    fmap = make_folium_map(painted)
    markers = [
        child
        for child in fmap._children.values()
        if child.__class__.__name__ == "CircleMarker"
    ]
    assert len(markers) == 2
