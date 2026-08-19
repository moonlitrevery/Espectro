"""Testes da coloração Welsh–Powell (guloso por grau decrescente)."""

import networkx as nx

from src.coloring.greedy_natural import count_colors, greedy_natural_coloring
from src.coloring.welsh_powell import (
    _vertices_by_decreasing_degree,
    welsh_powell_coloring,
)


def _is_proper_coloring(graph: nx.Graph, coloring: dict[str, int]) -> bool:
    if set(coloring) != set(graph.nodes()):
        return False
    for u, v in graph.edges():
        if coloring[u] == coloring[v]:
            return False
    return True


def test_empty_graph_returns_empty_coloring():
    assert welsh_powell_coloring(nx.Graph()) == {}


def test_complete_graph_still_needs_n_colors():
    """K4 é clique: qualquer guloso usa 4 cores, a ordem não salva."""
    graph = nx.complete_graph(["A", "B", "C", "D"])
    coloring = welsh_powell_coloring(graph)
    assert _is_proper_coloring(graph, coloring)
    assert count_colors(coloring) == 4


def test_highest_degree_vertex_is_colored_first():
    """Estrela: folhas inseridas antes do centro.

    Guloso natural pinta Y,Z,W com 0 e o centro X com 1.
    Welsh–Powell pinta X primeiro (grau 3) com 0; as folhas ficam com 1.
    É o exemplo para mostrar na banca que só a *ordem* mudou.
    """
    graph = nx.Graph()
    graph.add_nodes_from(["Y", "Z", "W", "X"])
    graph.add_edges_from([("X", "Y"), ("X", "Z"), ("X", "W")])

    natural = greedy_natural_coloring(graph)
    welsh = welsh_powell_coloring(graph)

    assert natural["X"] == 1
    assert welsh["X"] == 0
    assert welsh["Y"] == welsh["Z"] == welsh["W"] == 1
    assert _is_proper_coloring(graph, welsh)


def test_sorts_by_degree_then_station_id():
    """Dois vértices de grau 2: o desempate é o nome, não a inserção."""
    graph = nx.Graph()
    graph.add_nodes_from(["B", "A", "C"])
    graph.add_edges_from([("A", "B"), ("B", "C")])
    ordered = _vertices_by_decreasing_degree(graph)
    # B tem grau 2; A e C têm grau 1, empate resolvido por "A" < "C".
    assert ordered == ["B", "A", "C"]


def test_path_is_properly_2_colored():
    graph = nx.Graph()
    graph.add_nodes_from(["A", "B", "C"])
    graph.add_edges_from([("A", "B"), ("B", "C")])
    coloring = welsh_powell_coloring(graph)
    assert _is_proper_coloring(graph, coloring)
    assert count_colors(coloring) == 2


def test_never_uses_networkx_greedy_color(monkeypatch):
    import networkx.algorithms.coloring as nx_coloring

    def _should_not_run(*_args, **_kwargs):
        raise AssertionError("não podemos chamar networkx.greedy_color")

    monkeypatch.setattr(nx_coloring, "greedy_color", _should_not_run)
    graph = nx.complete_graph(["A", "B", "C"])
    coloring = welsh_powell_coloring(graph)
    assert count_colors(coloring) == 3
