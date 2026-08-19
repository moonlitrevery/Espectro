"""Testes da coloração DSATUR (saturação dinâmica)."""

import networkx as nx

from src.coloring.dsatur import (
    dsatur_coloring,
    pick_next_vertex,
    saturation_degree,
)
from src.coloring.greedy_natural import count_colors, greedy_natural_coloring


def _is_proper_coloring(graph: nx.Graph, coloring: dict[str, int]) -> bool:
    if set(coloring) != set(graph.nodes()):
        return False
    for u, v in graph.edges():
        if coloring[u] == coloring[v]:
            return False
    return True


def test_empty_graph_returns_empty_coloring():
    assert dsatur_coloring(nx.Graph()) == {}


def test_complete_graph_uses_n_colors():
    graph = nx.complete_graph(["A", "B", "C", "D"])
    coloring = dsatur_coloring(graph)
    assert _is_proper_coloring(graph, coloring)
    assert count_colors(coloring) == 4


def test_odd_cycle_needs_three_colors():
    """C5 não é bipartido: χ = 3, e o DSATUR tem que achar essas 3 cores."""
    graph = nx.cycle_graph(["A", "B", "C", "D", "E"])
    coloring = dsatur_coloring(graph)
    assert _is_proper_coloring(graph, coloring)
    assert count_colors(coloring) == 3


def test_bipartite_square_uses_two_colors():
    graph = nx.Graph()
    graph.add_nodes_from(["A", "B", "C", "D"])
    graph.add_edges_from([("A", "B"), ("B", "C"), ("C", "D"), ("D", "A")])
    coloring = dsatur_coloring(graph)
    assert _is_proper_coloring(graph, coloring)
    assert count_colors(coloring) == 2


def test_first_vertex_is_the_unique_maximum_degree():
    """No passo 0 todo mundo tem saturação 0: vale o desempate por grau."""
    graph = nx.Graph()
    graph.add_nodes_from(["Y", "Z", "W", "X"])
    graph.add_edges_from([("X", "Y"), ("X", "Z"), ("X", "W")])
    coloring = dsatur_coloring(graph)
    assert coloring["X"] == 0
    assert _is_proper_coloring(graph, coloring)


def test_saturation_beats_higher_degree():
    """L tem grau 2 e saturação 2; H tem grau 4 e saturação 0.

    A e B já estão pintados com cores diferentes. O DSATUR tem que escolher
    L (mais saturado), não H (mais conectado). É o oposto do Welsh–Powell,
    que nessa altura ainda seguiria a lista estática de grau.
    """
    graph = nx.Graph()
    graph.add_nodes_from(["A", "B", "L", "H", "C", "D", "E", "F"])
    graph.add_edges_from(
        [
            ("L", "A"),
            ("L", "B"),
            ("H", "C"),
            ("H", "D"),
            ("H", "E"),
            ("H", "F"),
        ]
    )
    coloring = {"A": 0, "B": 1}
    uncolored = {"L", "H", "C", "D", "E", "F"}
    degree_of = {vertex: graph.degree(vertex) for vertex in graph.nodes()}

    assert saturation_degree(graph, "L", coloring) == 2
    assert saturation_degree(graph, "H", coloring) == 0
    assert pick_next_vertex(graph, uncolored, coloring, degree_of) == "L"


def test_star_differs_from_natural_order():
    """Folhas inseridas primeiro: natural pinta o centro por último."""
    graph = nx.Graph()
    graph.add_nodes_from(["Y", "Z", "W", "X"])
    graph.add_edges_from([("X", "Y"), ("X", "Z"), ("X", "W")])
    natural = greedy_natural_coloring(graph)
    dsatur = dsatur_coloring(graph)
    assert natural["X"] == 1
    assert dsatur["X"] == 0


def test_never_uses_networkx_greedy_color(monkeypatch):
    import networkx.algorithms.coloring as nx_coloring

    def _should_not_run(*_args, **_kwargs):
        raise AssertionError("não podemos chamar networkx.greedy_color")

    monkeypatch.setattr(nx_coloring, "greedy_color", _should_not_run)
    graph = nx.complete_graph(["A", "B", "C"])
    coloring = dsatur_coloring(graph)
    assert count_colors(coloring) == 3
