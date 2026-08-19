"""Testes do catálogo de instâncias (filtro de município e raios D)."""

from pathlib import Path

import pytest

from src.instances import (
    INSTANCE_SPECS,
    filter_stations,
    get_spec,
    list_instance_ids,
    load_instance,
)
from src.data_prep import load_licensed_stations

FIXTURE = Path(__file__).parent / "fixtures" / "mini_erbs.csv"


def _catalog():
    return load_licensed_stations(csv_path=FIXTURE)


def test_catalog_has_at_least_three_instances():
    assert len(INSTANCE_SPECS) >= 3
    assert {"small", "medium", "large"}.issubset(set(list_instance_ids()))


def test_small_is_neighbors_without_bauru():
    spec = get_spec("small")
    assert spec.municipalities == ("Agudos", "Pederneiras", "Piratininga")
    assert "Bauru" not in spec.municipalities
    assert spec.radius_km == 1.0


def test_medium_is_bauru_only():
    spec = get_spec("medium")
    assert spec.municipalities == ("Bauru",)
    assert spec.radius_km == 1.0


def test_large_is_the_whole_region():
    spec = get_spec("large")
    assert spec.municipalities == ("Bauru", "Agudos", "Pederneiras", "Piratininga")
    assert spec.radius_km == 1.0


def test_d_variants_keep_the_same_vertices_as_large():
    """large / large_d05 / large_d20: mesmos municípios, D diferente."""
    large = get_spec("large")
    tight = get_spec("large_d05")
    wide = get_spec("large_d20")
    assert tight.municipalities == large.municipalities
    assert wide.municipalities == large.municipalities
    assert tight.radius_km == 0.5
    assert wide.radius_km == 2.0
    assert large.radius_km == 1.0


def test_unknown_id_lists_the_options():
    with pytest.raises(ValueError, match="small"):
        get_spec("nao_existe")


def test_filter_small_drops_bauru_stations():
    selected = filter_stations(_catalog(), get_spec("small"))
    assert set(selected["municipality"]) == {"Agudos", "Pederneiras", "Piratininga"}
    assert "100" not in set(selected["station_id"])
    assert set(selected["station_id"]) == {"300", "600", "700"}


def test_filter_medium_keeps_only_bauru():
    selected = filter_stations(_catalog(), get_spec("medium"))
    assert set(selected["municipality"]) == {"Bauru"}
    assert set(selected["station_id"]) == {"100", "200"}


def test_load_instance_builds_a_graph_with_matching_nodes():
    loaded = load_instance("medium", csv_path=FIXTURE)
    assert loaded.n_stations == 2
    assert set(loaded.graph.nodes()) == {"100", "200"}
    # Duas operadoras no mesmo ponto: distância 0 < D, então há aresta.
    assert loaded.graph.has_edge("100", "200")


def test_tighter_radius_does_not_add_edges():
    """Mesmos vértices: D=0,5 não pode ter mais arestas que D=2."""
    catalog = _catalog()
    tight = load_instance("large_d05", stations=catalog)
    wide = load_instance("large_d20", stations=catalog)
    assert tight.n_stations == wide.n_stations
    assert tight.n_edges <= wide.n_edges
