"""Testes da distância haversine e do grafo de interferência."""

import math

import pandas as pd
import pytest

from src.graph_builder import (
    EARTH_RADIUS_KM,
    build_interference_graph,
    haversine_km,
    summarize_graph,
)


def test_haversine_same_point_is_zero():
    assert haversine_km(-22.3149, -49.0606, -22.3149, -49.0606) == 0.0


def test_haversine_one_degree_on_equator():
    """1° de longitude no equador deve ser 2πR / 360 km."""
    expected = 2.0 * math.pi * EARTH_RADIUS_KM / 360.0
    assert haversine_km(0.0, 0.0, 0.0, 1.0) == pytest.approx(expected, rel=1e-6)


def test_haversine_is_symmetric():
    a = haversine_km(-22.31, -49.06, -22.47, -48.97)
    b = haversine_km(-22.47, -48.97, -22.31, -49.06)
    assert a == pytest.approx(b)


def _stations(*rows: dict) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_edge_exists_only_inside_radius():
    """A e B estão a ~0,5 km (mesmo meridiano); C fica longe (~20 km)."""
    # 0,5 km para o norte ≈ 0,5 * 360 / (2πR) graus de latitude.
    delta_lat = 0.5 * 360.0 / (2.0 * math.pi * EARTH_RADIUS_KM)
    stations = _stations(
        {"station_id": "A", "latitude": -22.3149, "longitude": -49.0606},
        {"station_id": "B", "latitude": -22.3149 + delta_lat, "longitude": -49.0606},
        {"station_id": "C", "latitude": -22.47, "longitude": -48.97},
    )

    close = build_interference_graph(stations, radius_km=1.0)
    assert close.has_edge("A", "B")
    assert not close.has_edge("A", "C")
    assert not close.has_edge("B", "C")

    too_small = build_interference_graph(stations, radius_km=0.4)
    assert not too_small.has_edge("A", "B")


def test_colocated_stations_are_connected():
    """Duas operadoras no mesmo ponto: distância 0 < D, então há aresta."""
    stations = _stations(
        {"station_id": "100", "latitude": -22.3149, "longitude": -49.0606},
        {"station_id": "200", "latitude": -22.3149, "longitude": -49.0606},
    )
    graph = build_interference_graph(stations, radius_km=1.0)
    assert graph.has_edge("100", "200")


def test_graph_is_undirected_without_self_loops():
    stations = _stations(
        {"station_id": "A", "latitude": -22.31, "longitude": -49.06},
        {"station_id": "B", "latitude": -22.31, "longitude": -49.06},
    )
    graph = build_interference_graph(stations, radius_km=1.0)
    assert not graph.is_directed()
    assert graph.number_of_nodes() == 2
    assert graph.number_of_edges() == 1
    assert not graph.has_edge("A", "A")


def test_isolated_station_stays_as_vertex():
    stations = _stations(
        {"station_id": "A", "latitude": -22.31, "longitude": -49.06},
        {"station_id": "Z", "latitude": -23.55, "longitude": -46.63},
    )
    graph = build_interference_graph(stations, radius_km=1.0)
    assert set(graph.nodes()) == {"A", "Z"}
    assert graph.number_of_edges() == 0
    summary = summarize_graph(graph)
    assert summary["isolated"] == 2


def test_rejects_non_positive_radius():
    stations = _stations(
        {"station_id": "A", "latitude": -22.31, "longitude": -49.06},
    )
    with pytest.raises(ValueError):
        build_interference_graph(stations, radius_km=0)
    with pytest.raises(ValueError):
        build_interference_graph(stations, radius_km=-1)


def test_rejects_duplicate_station_ids():
    stations = _stations(
        {"station_id": "A", "latitude": -22.31, "longitude": -49.06},
        {"station_id": "A", "latitude": -22.32, "longitude": -49.07},
    )
    with pytest.raises(ValueError, match="station_id repetido"):
        build_interference_graph(stations, radius_km=1.0)


def test_copies_node_attributes_for_the_map():
    stations = _stations(
        {
            "station_id": "A",
            "latitude": -22.31,
            "longitude": -49.06,
            "municipality": "Bauru",
            "operator": "VIVO",
        },
    )
    graph = build_interference_graph(stations, radius_km=1.0)
    assert graph.nodes["A"]["municipality"] == "Bauru"
    assert graph.nodes["A"]["operator"] == "VIVO"
    assert graph.nodes["A"]["latitude"] == pytest.approx(-22.31)
