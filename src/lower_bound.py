"""Piso para o número cromático: tamanho de um clique grande.

Fato de livro: χ(G) ≥ ω(G). Qualquer coloração válida usa pelo menos
tantas cores quanto o tamanho do maior clique. Não calculamos ω de
verdade (é NP-difícil); montamos um clique pelo guloso e repetimos a
partir de cada vértice. O maior conjunto encontrado é um **piso**: o
número cromático não pode ser menor que isso.

Se alguma heurística de coloração empatar com esse piso, ela é ótima
naquela instância — não porque provamos χ, mas porque χ fica espremido
entre ω̂ e o número de cores, e os dois coincidem.

networkx não é usado para achar cliques (``find_cliques``,
``graph_clique_number``, etc.). Só ``neighbors`` / ``has_edge``.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx


@dataclass(frozen=True)
class CliqueEstimate:
    """Clique encontrado pela heurística (não necessariamente máximo)."""

    size: int
    vertices: tuple

    def summary(self) -> str:
        return f"clique de tamanho {self.size} (piso para χ)"


def is_clique(graph: nx.Graph, vertices: list | tuple | set) -> bool:
    """True se cada par do conjunto é uma aresta.

    Checagem independente, no mesmo espírito do validator: não confiamos
    no construtor do clique sem olhar o grafo de novo.
    """
    nodes = list(vertices)
    for i, left in enumerate(nodes):
        if left not in graph:
            return False
        for right in nodes[i + 1 :]:
            if not graph.has_edge(left, right):
                return False
    return True


def greedy_clique_from(
    graph: nx.Graph,
    start,
    neighbors_of: dict | None = None,
) -> list:
    """Clique contendo ``start``, crescendo um vértice por vez.

    Invariante: ``candidates`` é a vizinhança comum de todo mundo que já
    está no clique. Por isso, qualquer candidato que entrássemos
    manteria o conjunto completo. Escolhemos o que tem mais vizinhos
    *dentro dos candidatos* — a ideia é não encolher o poço cedo demais.
    """
    if start not in graph:
        raise ValueError(f"vértice {start!r} não está no grafo")

    if neighbors_of is None:
        neighbors_of = _neighbor_sets(graph)

    clique = [start]
    candidates = set(neighbors_of[start])

    while candidates:
        chosen = _vertex_with_most_neighbors_in(candidates, neighbors_of)
        clique.append(chosen)
        candidates &= neighbors_of[chosen]

    return clique


def estimate_max_clique(graph: nx.Graph) -> CliqueEstimate:
    """Tenta um clique guloso a partir de cada vértice; fica com o maior.

    Não é enumeração de cliques máximos. É “o melhor que o guloso achou
    começando de todos os lados”.

    Poda (correta, não heurística): um vértice de grau d não cabe em
    clique maior que d+1. Se já vimos um clique desse tamanho, pulamos.
    Começamos pelos graus altos para achar um clique grande cedo e podar
    mais.
    """
    neighbors_of = _neighbor_sets(graph)
    starts = sorted(
        graph.nodes(),
        key=lambda vertex: (-len(neighbors_of[vertex]), str(vertex)),
    )

    best_clique: list = []
    for start in starts:
        if len(neighbors_of[start]) + 1 <= len(best_clique):
            continue
        clique = greedy_clique_from(graph, start, neighbors_of=neighbors_of)
        if len(clique) > len(best_clique):
            best_clique = clique

    if best_clique and not is_clique(graph, best_clique):
        raise RuntimeError("a heurística devolveu um conjunto que não é clique")

    vertices = tuple(sorted(best_clique, key=str))
    return CliqueEstimate(size=len(vertices), vertices=vertices)


def _neighbor_sets(graph: nx.Graph) -> dict:
    """Conjunto de vizinhos de cada vértice, calculado uma vez."""
    return {vertex: set(graph.neighbors(vertex)) for vertex in graph.nodes()}


def _vertex_with_most_neighbors_in(candidates: set, neighbors_of: dict):
    """Entre os candidatos, quem é vizinho de mais candidatos.

    Empate: ``station_id`` lexicográfico, a mesma regra dos algoritmos
    de coloração, para o resultado ser reproduzível na apresentação.
    """
    best_vertex = None
    best_count = -1
    best_name = None

    for vertex in candidates:
        neighbor_count = 0
        for neighbor in neighbors_of[vertex]:
            if neighbor in candidates:
                neighbor_count += 1
        name = str(vertex)
        is_better = False
        if neighbor_count > best_count:
            is_better = True
        elif neighbor_count == best_count and (best_name is None or name < best_name):
            is_better = True
        if is_better:
            best_vertex = vertex
            best_count = neighbor_count
            best_name = name

    return best_vertex


if __name__ == "__main__":
    from src.coloring.dsatur import dsatur_coloring
    from src.coloring.greedy_natural import count_colors, greedy_natural_coloring
    from src.coloring.welsh_powell import welsh_powell_coloring
    from src.data_prep import load_licensed_stations
    from src.graph_builder import (
        DEFAULT_RADIUS_KM,
        build_interference_graph,
    )

    stations = load_licensed_stations()
    graph = build_interference_graph(stations, radius_km=DEFAULT_RADIUS_KM)
    estimate = estimate_max_clique(graph)

    print(f"D = {DEFAULT_RADIUS_KM} km | n = {graph.number_of_nodes()}")
    print(estimate.summary())
    print(f"cores guloso natural: {count_colors(greedy_natural_coloring(graph))}")
    print(f"cores Welsh–Powell:   {count_colors(welsh_powell_coloring(graph))}")
    print(f"cores DSATUR:         {count_colors(dsatur_coloring(graph))}")
    print(
        "Se cores == piso, a coloração é ótima nesta instância "
        "(χ fica preso entre os dois)."
    )
