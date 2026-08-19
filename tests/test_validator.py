"""Testes do validador — colorações feitas à mão, sem copiar os algoritmos."""

import inspect

import networkx as nx

from src.coloring import validator as validator_module
from src.coloring.validator import validate_coloring


def test_validator_does_not_import_the_algorithms():
    """Importar o validador não pode puxar guloso/WP/DSATUR.

    O bloco ``if __name__ == "__main__"`` cita os algoritmos só para o
    script de conferência; em uso normal (analysis, testes, dashboard)
    a checagem continua independente.
    """
    assert not hasattr(validator_module, "greedy_natural_coloring")
    assert not hasattr(validator_module, "welsh_powell_coloring")
    assert not hasattr(validator_module, "dsatur_coloring")

    check_source = inspect.getsource(validator_module.validate_coloring)
    check_source += inspect.getsource(validator_module._same_color_edges)
    assert "greedy_natural" not in check_source
    assert "welsh_powell" not in check_source
    assert "dsatur" not in check_source


def test_empty_graph_is_valid_with_zero_colors():
    result = validate_coloring(nx.Graph(), {})
    assert result.is_valid
    assert result.n_colors == 0


def test_proper_path_coloring_is_valid():
    graph = nx.Graph()
    graph.add_edges_from([("A", "B"), ("B", "C")])
    result = validate_coloring(graph, {"A": 0, "B": 1, "C": 0})
    assert result.is_valid
    assert result.n_colors == 2
    assert result.conflicts == ()


def test_same_color_on_an_edge_is_a_conflict():
    graph = nx.Graph()
    graph.add_edges_from([("A", "B"), ("B", "C")])
    result = validate_coloring(graph, {"A": 0, "B": 0, "C": 1})
    assert not result.is_valid
    assert result.conflicts == (("A", "B"),)


def test_missing_vertex_is_invalid():
    graph = nx.Graph()
    graph.add_nodes_from(["A", "B"])
    graph.add_edge("A", "B")
    result = validate_coloring(graph, {"A": 0})
    assert not result.is_valid
    assert result.missing_vertices == ("B",)
    assert result.conflicts == ()


def test_extra_vertex_is_invalid():
    """Sobra de chave = provavelmente pintamos o grafo errado."""
    graph = nx.Graph()
    graph.add_node("A")
    result = validate_coloring(graph, {"A": 0, "Z": 1})
    assert not result.is_valid
    assert result.extra_vertices == ("Z",)
    assert result.n_colors == 1


def test_clique_with_reused_color_lists_every_bad_edge():
    graph = nx.complete_graph(["A", "B", "C"])
    result = validate_coloring(graph, {"A": 0, "B": 0, "C": 1})
    assert not result.is_valid
    assert result.conflicts == (("A", "B"),)
    assert result.n_colors == 2


def test_isolated_vertices_share_a_color_and_that_is_fine():
    graph = nx.Graph()
    graph.add_nodes_from(["A", "B"])
    result = validate_coloring(graph, {"A": 0, "B": 0})
    assert result.is_valid
    assert result.n_colors == 1


def test_accepts_a_coloring_produced_by_greedy():
    """O validador não conhece o guloso; só aceita o dicionário que ele devolve."""
    from src.coloring.greedy_natural import greedy_natural_coloring

    graph = nx.cycle_graph(["A", "B", "C", "D", "E"])
    result = validate_coloring(graph, greedy_natural_coloring(graph))
    assert result.is_valid
    assert result.n_colors >= 3


def test_counts_colors_from_the_graph_not_from_leftovers():
    graph = nx.Graph()
    graph.add_nodes_from(["A", "B"])
    result = validate_coloring(graph, {"A": 0, "B": 3, "Z": 9})
    assert not result.is_valid
    assert result.n_colors == 2
    assert result.extra_vertices == ("Z",)
