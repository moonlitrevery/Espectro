"""Coloração DSATUR — o próximo vértice é o mais saturado.

Saturação de um vértice ainda não pintado = quantas cores **distintas**
já aparecem na vizinhança. Intuição: se uma ERB já tem vizinhos nos
canais 0, 1 e 4, ela está mais “apertada” do que uma ERB cujo único
vizinho pintado usa o canal 0. Pintar a apertada agora evita descobrir
tarde demais que faltou cor.

A cada passo:
1. escolhe o não-pintado de maior saturação;
2. empate: maior grau (o grau original, estático, como no Welsh–Powell);
3. ainda empatado: ``station_id``;
4. pinta com a menor cor livre (o mesmo laço dos outros dois algoritmos).

No começo ninguém tem cor, então saturação = 0 para todos e o primeiro
vértice é o de maior grau — igual ao Welsh–Powell. A diferença nasce no
segundo passo, quando a saturação passa a variar.

Também é heurística: não garante o número cromático. Em grafos bipartidos
o DSATUR clássico acerta χ = 2; não vamos tratar isso como teorema no
código, só como motivo para incluí-lo no trabalho.

Referência: Brélaz, D. (1979). New methods to color the vertices of a
graph. Communications of the ACM.
"""

from __future__ import annotations

import networkx as nx


def dsatur_coloring(graph: nx.Graph) -> dict[str, int]:
    """Pinta o grafo escolhendo sempre o vértice mais saturado.

    Parameters
    ----------
    graph:
        Grafo de interferência (não-direcionado). Usamos ``nodes()``,
        ``neighbors()`` e ``degree()``.

    Returns
    -------
    dict
        ``station_id → cor`` (inteiros 0, 1, 2, ...).
    """
    coloring: dict = {}
    uncolored = set(graph.nodes())
    degree_of = {vertex: graph.degree(vertex) for vertex in graph.nodes()}

    while uncolored:
        vertex = pick_next_vertex(graph, uncolored, coloring, degree_of)
        coloring[vertex] = _smallest_free_color(graph, vertex, coloring)
        uncolored.remove(vertex)

    return coloring


def pick_next_vertex(
    graph: nx.Graph,
    uncolored: set,
    coloring: dict,
    degree_of: dict,
):
    """Devolve o próximo vértice segundo a regra DSATUR.

    Função pública de propósito: na apresentação dá para montar um grafo
    pequeno, pintar dois vértices na mão e perguntar “quem o algoritmo
    escolheria agora?” — e o teste faz exatamente isso.
    """
    best_vertex = None
    best_saturation = -1
    best_degree = -1
    best_name = None

    for vertex in uncolored:
        saturation = saturation_degree(graph, vertex, coloring)
        degree = degree_of[vertex]
        name = str(vertex)

        # Três comparações em cascata, na ordem da regra. Sem tuple-trick:
        # na banca dá para apontar cada ``if``.
        is_better = False
        if saturation > best_saturation:
            is_better = True
        elif saturation == best_saturation and degree > best_degree:
            is_better = True
        elif (
            saturation == best_saturation
            and degree == best_degree
            and (best_name is None or name < best_name)
        ):
            is_better = True

        if is_better:
            best_vertex = vertex
            best_saturation = saturation
            best_degree = degree
            best_name = name

    return best_vertex


def saturation_degree(graph: nx.Graph, vertex, coloring: dict) -> int:
    """Quantas cores distintas já existem entre os vizinhos pintados.

    Recalcula do zero a cada chamada. Para ~2000 ERBs isso é instantâneo
    e, na apresentação, não precisa explicar um vetor auxiliar sendo
    incrementado.
    """
    distinct_colors = set()
    for neighbor in graph.neighbors(vertex):
        if neighbor in coloring:
            distinct_colors.add(coloring[neighbor])
    return len(distinct_colors)


def _smallest_free_color(graph: nx.Graph, vertex, coloring: dict) -> int:
    """Menor inteiro ≥ 0 que nenhum vizinho já pintado está usando."""
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
    from src.coloring.welsh_powell import welsh_powell_coloring
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
    dsatur = dsatur_coloring(graph)

    print(f"D = {DEFAULT_RADIUS_KM} km")
    print(f"Vértices: {summary['n_nodes']} | Arestas: {summary['n_edges']}")
    print(f"Grau máximo Δ = {int(summary['max_degree'])}")
    print(f"Cores (guloso natural): {count_colors(natural)}")
    print(f"Cores (Welsh–Powell):   {count_colors(welsh)}")
    print(f"Cores (DSATUR):         {count_colors(dsatur)}")
