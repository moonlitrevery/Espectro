"""Testes da heurística de clique (piso para o número cromático)."""

import networkx as nx
import pytest

from src.lower_bound import (
    estimate_max_clique,
    greedy_clique_from,
    is_clique,
)


def test_empty_graph_has_clique_zero():
    estimate = estimate_max_clique(nx.Graph())
    assert estimate.size == 0
    assert estimate.vertices == ()


def test_single_vertex_is_a_clique_of_one():
    graph = nx.Graph()
    graph.add_node("A")
    estimate = estimate_max_clique(graph)
    assert estimate.size == 1
    assert estimate.vertices == ("A",)


def test_complete_graph_is_found_entirely():
    graph = nx.complete_graph(["A", "B", "C", "D"])
    estimate = estimate_max_clique(graph)
    assert estimate.size == 4
    assert set(estimate.vertices) == {"A", "B", "C", "D"}
    assert is_clique(graph, estimate.vertices)


def test_bipartite_graph_has_clique_two():
    """Grafos bipartidos sem isolados: ω = 2 (uma aresta já é clique)."""
    graph = nx.Graph()
    graph.add_edges_from([("A", "B"), ("B", "C"), ("C", "D"), ("D", "A")])
    estimate = estimate_max_clique(graph)
    assert estimate.size == 2
    assert is_clique(graph, estimate.vertices)


def test_finds_the_triangle_not_just_an_edge():
    """Triângulo ABC + folha D ligada em A: o clique máximo tem tamanho 3."""
    graph = nx.Graph()
    graph.add_edges_from([("A", "B"), ("B", "C"), ("C", "A"), ("A", "D")])
    estimate = estimate_max_clique(graph)
    assert estimate.size == 3
    assert set(estimate.vertices) == {"A", "B", "C"}


def test_two_cliques_keeps_the_larger_one():
    graph = nx.Graph()
    graph.add_edges_from(
        [
            ("A", "B"),
            ("B", "C"),
            ("C", "A"),
            ("W", "X"),
            ("X", "Y"),
            ("Y", "Z"),
            ("Z", "W"),
            ("W", "Y"),
            ("X", "Z"),
        ]
    )
    estimate = estimate_max_clique(graph)
    assert estimate.size == 4
    assert set(estimate.vertices) == {"W", "X", "Y", "Z"}


def test_greedy_from_a_leaf_still_grows_into_the_triangle():
    """Começando na folha D, o guloso entra em A e ainda pode fechar ABC."""
    graph = nx.Graph()
    graph.add_edges_from([("A", "B"), ("B", "C"), ("C", "A"), ("A", "D")])
    clique = greedy_clique_from(graph, "D")
    assert "D" in clique
    assert is_clique(graph, clique)
    assert len(clique) >= 2


def test_is_clique_rejects_a_path():
    graph = nx.Graph()
    graph.add_edges_from([("A", "B"), ("B", "C")])
    assert is_clique(graph, ["A", "B"])
    assert not is_clique(graph, ["A", "B", "C"])


def test_does_not_call_networkx_clique_routines(monkeypatch):
    import networkx.algorithms.clique as nx_clique

    def _should_not_run(*_args, **_kwargs):
        raise AssertionError("não usar find_cliques do networkx")

    monkeypatch.setattr(nx_clique, "find_cliques", _should_not_run)
    graph = nx.complete_graph(["A", "B", "C"])
    assert estimate_max_clique(graph).size == 3


def test_unknown_start_raises():
    graph = nx.Graph()
    graph.add_node("A")
    with pytest.raises(ValueError):
        greedy_clique_from(graph, "Z")


def test_max_starts_still_finds_complete_graph_from_one_vertex():
    """Um único começo em K4 já devolve o clique inteiro."""
    graph = nx.complete_graph(["A", "B", "C", "D"])
    estimate = estimate_max_clique(graph, max_starts=1)
    assert estimate.size == 4
