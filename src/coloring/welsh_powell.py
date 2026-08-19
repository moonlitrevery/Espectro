"""Coloração de Welsh–Powell — guloso depois de ordenar por grau.

Diferença para o baseline: **quem** é pintado primeiro muda. O laço que
escolhe a cor é o mesmo (menor inteiro que nenhum vizinho já colorido
usa). Aqui os vértices entram em ordem de **grau decrescente**: os mais
conectados (ERBs no meio de um aglomerado) recebem cor cedo, quando ainda
há poucas restrições, e tendem a “reservar” as cores baixas.

Ainda é uma heurística. Ordenar por grau não garante o número cromático;
só muda a ordem do guloso.

Há uma variante do artigo original (Welsh & Powell, 1967) que, a cada
cor, percorre a lista e pinta de uma vez todos os vértices não adjacentes
àquela classe. O enunciado deste trabalho pede o guloso **ordenado por
grau decrescente**, que é a forma ensinada na maior parte dos cursos e a
que contrasta em uma linha com o baseline.
"""

from __future__ import annotations

import networkx as nx


def welsh_powell_coloring(graph: nx.Graph) -> dict[str, int]:
    """Pinta o grafo no sentido guloso, vértices em grau decrescente.

    Parameters
    ----------
    graph:
        Grafo de interferência (não-direcionado). Usamos ``nodes()``,
        ``neighbors()`` e ``degree()`` — nunca a coloração do networkx.

    Returns
    -------
    dict
        ``station_id → cor`` (inteiros 0, 1, 2, ...).
    """
    coloring: dict[str, int] = {}
    for vertex in _vertices_by_decreasing_degree(graph):
        coloring[vertex] = _smallest_free_color(graph, vertex, coloring)
    return coloring


def _vertices_by_decreasing_degree(graph: nx.Graph) -> list:
    """Lista os vértices do mais conectado para o menos conectado.

    O grau é anotado uma vez só, antes da ordenação: durante a coloração
    o grafo não muda, então o grau é estático (não é o DSATUR).

    Empate: ``station_id`` em ordem lexicográfica. Sem isso, a ordem
    entre dois vértices de mesmo grau dependeria de detalhes internos e
    a apresentação não conseguiria reproduzir o mesmo resultado.
    """
    degree_of = {vertex: graph.degree(vertex) for vertex in graph.nodes()}
    return sorted(
        graph.nodes(),
        key=lambda vertex: (-degree_of[vertex], str(vertex)),
    )


def _smallest_free_color(
    graph: nx.Graph,
    vertex,
    coloring: dict,
) -> int:
    """Menor inteiro ≥ 0 que nenhum vizinho já pintado está usando.

    Cópia proposital do laço do guloso natural: cada algoritmo fica
    legível sozinho na apresentação, sem pular de arquivo no meio do
    passo principal.
    """
    colors_already_taken = set()
    for neighbor in graph.neighbors(vertex):
        if neighbor in coloring:
            colors_already_taken.add(coloring[neighbor])

    color = 0
    while color in colors_already_taken:
        color += 1
    return color


if __name__ == "__main__":
    from src.coloring.greedy_natural import (
        count_colors,
        greedy_natural_coloring,
    )
    from src.data_prep import load_licensed_stations
    from src.graph_builder import (
        DEFAULT_RADIUS_KM,
        build_interference_graph,
        summarize_graph,
    )

    stations = load_licensed_stations()
    graph = build_interference_graph(stations, radius_km=DEFAULT_RADIUS_KM)
    summary = summarize_graph(graph)

    natural = greedy_natural_coloring(graph)
    welsh = welsh_powell_coloring(graph)

    print(f"D = {DEFAULT_RADIUS_KM} km")
    print(f"Vértices: {summary['n_nodes']} | Arestas: {summary['n_edges']}")
    print(f"Grau máximo Δ = {int(summary['max_degree'])}")
    print(f"Cores (guloso natural): {count_colors(natural)}")
    print(f"Cores (Welsh–Powell):   {count_colors(welsh)}")
