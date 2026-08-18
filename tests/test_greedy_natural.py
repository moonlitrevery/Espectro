"""Testes da coloração gulosa em ordem natural."""

import networkx as nx

from src.coloring.greedy_natural import (
    count_colors,
    greedy_natural_coloring,
)


def _is_proper_coloring(graph: nx.Graph, coloring: dict[str, int]) -> bool:
    """Checagem local (o validator.py oficial vem em um módulo separado)."""
    if set(coloring) != set(graph.nodes()):
        return False
    for u, v in graph.edges():
        if coloring[u] == coloring[v]:
            return False
    return True


def test_empty_graph_returns_empty_coloring():
    assert greedy_natural_coloring(nx.Graph()) == {}
    assert count_colors({}) == 0


def test_isolated_vertex_gets_color_zero():
    graph = nx.Graph()
    graph.add_node("A")
    coloring = greedy_natural_coloring(graph)
    assert coloring == {"A": 0}


def test_complete_graph_uses_one_color_per_vertex():
    """Em K4 todo mundo é vizinho de todo mundo: o guloso precisa de 4 cores."""
    graph = nx.complete_graph(["A", "B", "C", "D"])
    coloring = greedy_natural_coloring(graph)
    assert _is_proper_coloring(graph, coloring)
    assert count_colors(coloring) == 4
    assert coloring == {"A": 0, "B": 1, "C": 2, "D": 3}


def test_path_reuses_color_zero_on_the_third_vertex():
    """A—B—C, nessa ordem: A=0, B=1, C=0 (C só vê B)."""
    graph = nx.Graph()
    graph.add_nodes_from(["A", "B", "C"])
    graph.add_edges_from([("A", "B"), ("B", "C")])
    coloring = greedy_natural_coloring(graph)
    assert coloring == {"A": 0, "B": 1, "C": 0}
    assert _is_proper_coloring(graph, coloring)


def test_insertion_order_changes_the_coloring():
    """Mesmo P3, nós inseridos A, C, B: A=0, C=0, B=1.

    Mostra na apresentação que “ordem natural” = ordem de inserção, não
    uma ordenação mágica. Welsh-Powell vai ordenar por grau; aqui não.
    """
    graph = nx.Graph()
    graph.add_nodes_from(["A", "C", "B"])
    graph.add_edges_from([("A", "B"), ("B", "C")])
    coloring = greedy_natural_coloring(graph)
    assert coloring == {"A": 0, "C": 0, "B": 1}


def test_bipartite_square_is_2_colored_in_this_order():
    """C4: ciclo par, 2-colorível. Guloso nesta ordem também usa 2 cores."""
    graph = nx.Graph()
    graph.add_nodes_from(["A", "B", "C", "D"])
    graph.add_edges_from([("A", "B"), ("B", "C"), ("C", "D"), ("D", "A")])
    coloring = greedy_natural_coloring(graph)
    assert _is_proper_coloring(graph, coloring)
    assert count_colors(coloring) == 2


def test_never_uses_networkx_greedy_color(monkeypatch):
    """Regra do enunciado: coloração pronta de biblioteca é proibida."""
    import networkx.algorithms.coloring as nx_coloring

    def _should_not_run(*_args, **_kwargs):
        raise AssertionError("não podemos chamar networkx.greedy_color")

    monkeypatch.setattr(nx_coloring, "greedy_color", _should_not_run)
    graph = nx.complete_graph(["A", "B", "C"])
    coloring = greedy_natural_coloring(graph)
    assert count_colors(coloring) == 3
