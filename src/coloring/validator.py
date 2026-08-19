"""Checagem independente de uma coloração.

Este módulo não importa guloso, Welsh–Powell nem DSATUR. A pergunta que
ele responde é só: “este dicionário é uma coloração própria do grafo?”,
olhando arestas e vértices. Se um algoritmo tiver bug, é aqui que o
trabalho percebe — não confiamos na lógica interna de quem pintou.

Duas regras, as do enunciado:
1. todo vértice tem cor, e só os vértices do grafo aparecem no dicionário;
2. nenhuma aresta liga duas pontas com a mesma cor.

O número de cores é a quantidade de valores distintos, contada de novo
aqui (não reutiliza ``count_colors`` do guloso).
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx


@dataclass(frozen=True)
class ValidationResult:
    """Relatório da checagem. ``is_valid`` só é True se as três listas
    abaixo estiverem vazias."""

    is_valid: bool
    n_colors: int
    conflicts: tuple[tuple, ...]
    missing_vertices: tuple
    extra_vertices: tuple

    def summary(self) -> str:
        """Uma linha para imprimir no relatório / no ``__main__``."""
        if self.is_valid:
            return f"coloração válida com {self.n_colors} cor(es)"
        return (
            f"INVÁLIDA | cores={self.n_colors} | "
            f"conflitos={len(self.conflicts)} | "
            f"faltando={len(self.missing_vertices)} | "
            f"sobrando={len(self.extra_vertices)}"
        )


def validate_coloring(graph: nx.Graph, coloring: dict) -> ValidationResult:
    """Percorre o grafo e o dicionário; não chama nenhum algoritmo.

    Parameters
    ----------
    graph:
        Grafo de interferência.
    coloring:
        Mapa ``vértice → cor``. As cores podem ser qualquer valor
        comparável por igualdade (nós usamos inteiros 0, 1, 2, ...).

    Returns
    -------
    ValidationResult
        ``n_colors`` considera só vértices que existem no grafo **e**
        no dicionário. Se faltar vértice, a coloração já é inválida;
        ainda assim reportamos quantas cores apareceram no que foi pintado.
    """
    vertex_set = set(graph.nodes())
    colored_set = set(coloring.keys())

    missing = tuple(sorted(vertex_set - colored_set, key=str))
    extra = tuple(sorted(colored_set - vertex_set, key=str))
    conflicts = tuple(_same_color_edges(graph, coloring))

    used_colors = {
        coloring[vertex]
        for vertex in vertex_set
        if vertex in coloring
    }

    is_valid = (len(missing) == 0) and (len(extra) == 0) and (len(conflicts) == 0)
    return ValidationResult(
        is_valid=is_valid,
        n_colors=len(used_colors),
        conflicts=conflicts,
        missing_vertices=missing,
        extra_vertices=extra,
    )


def _same_color_edges(graph: nx.Graph, coloring: dict) -> list[tuple]:
    """Lista arestas cujas duas pontas existem no dicionário e têm a mesma cor.

    Cada aresta do ``networkx.Graph`` aparece uma vez (grafo não-direcionado).
    Pares são gravados em ordem lexicográfica para o teste ser estável.
    Vértices sem cor não entram aqui: já são reportados em ``missing_vertices``.
    """
    conflicts = []
    for left, right in graph.edges():
        if left not in coloring or right not in coloring:
            continue
        if coloring[left] == coloring[right]:
            if str(left) <= str(right):
                conflicts.append((left, right))
            else:
                conflicts.append((right, left))
    conflicts.sort(key=lambda pair: (str(pair[0]), str(pair[1])))
    return conflicts


if __name__ == "__main__":
    from src.coloring.dsatur import dsatur_coloring
    from src.coloring.greedy_natural import greedy_natural_coloring
    from src.coloring.welsh_powell import welsh_powell_coloring
    from src.data_prep import load_licensed_stations
    from src.graph_builder import (
        DEFAULT_RADIUS_KM,
        build_interference_graph,
    )

    stations = load_licensed_stations()
    graph = build_interference_graph(stations, radius_km=DEFAULT_RADIUS_KM)

    algorithms = (
        ("guloso natural", greedy_natural_coloring),
        ("Welsh–Powell", welsh_powell_coloring),
        ("DSATUR", dsatur_coloring),
    )
    print(f"D = {DEFAULT_RADIUS_KM} km | n = {graph.number_of_nodes()}")
    for name, color_fn in algorithms:
        result = validate_coloring(graph, color_fn(graph))
        print(f"{name}: {result.summary()}")
