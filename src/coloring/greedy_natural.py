"""Coloração gulosa em ordem natural — o baseline do trabalho.

Ideia, em uma frase: percorra os vértices na ordem em que eles já estão
no grafo e, para cada um, escolha a menor cor que nenhum vizinho
*já colorido* esteja usando.

Por que isso é o baseline: não reordena nada (ao contrário do
Welsh-Powell, que ordena por grau) e não olha saturação (ao contrário do
DSATUR). Qualquer ganho dos outros dois algoritmos é medido contra este.

Não garante o número cromático. O teorema de Brooks só assegura que o
guloso nunca usa mais do que Δ+1 cores (Δ = grau máximo).
"""

from __future__ import annotations

import networkx as nx

# Cores são inteiros 0, 1, 2, ...  O número de canais é quantos inteiros
# distintos aparecem no dicionário final.


def greedy_natural_coloring(graph: nx.Graph) -> dict[str, int]:
    """Pinta o grafo no sentido guloso, sem reordenar os vértices.

    A ordem natural é a ordem de inserção no ``networkx.Graph``. No nosso
    pipeline isso coincide com a ordem das estações no DataFrame depois
    da deduplicação (primeira ocorrência de cada ``NumEstacao`` no CSV).

    Parameters
    ----------
    graph:
        Grafo de interferência (não-direcionado). Só usamos
        ``graph.nodes()`` e ``graph.neighbors()``.

    Returns
    -------
    dict
        ``station_id → cor``. Vértices isolados recebem a cor 0.
    """
    coloring: dict[str, int] = {}

    # ``graph.nodes()`` em networkx 3 / Python 3.7+ segue a ordem de
    # inserção — não é um conjunto embaralhado.
    for vertex in graph.nodes():
        coloring[vertex] = _smallest_free_color(graph, vertex, coloring)

    return coloring


def _smallest_free_color(
    graph: nx.Graph,
    vertex: str,
    coloring: dict[str, int],
) -> int:
    """Menor inteiro ≥ 0 que nenhum vizinho já pintado está usando.

    Vizinhos ainda não pintados não entram na conta: o guloso só olha o
    passado, nunca o futuro. É exatamente isso que o DSATUR vai melhorar
    depois, olhando também os vizinhos não coloridos (saturação).
    """
    colors_already_taken = set()
    for neighbor in graph.neighbors(vertex):
        if neighbor in coloring:
            colors_already_taken.add(coloring[neighbor])

    color = 0
    while color in colors_already_taken:
        color += 1
    return color


def count_colors(coloring: dict[str, int]) -> int:
    """Quantas cores distintas a coloração usou (0 se o grafo for vazio)."""
    if not coloring:
        return 0
    return len(set(coloring.values()))


if __name__ == "__main__":
    from src.data_prep import load_licensed_stations
    from src.graph_builder import (
        DEFAULT_RADIUS_KM,
        build_interference_graph,
        summarize_graph,
    )

    stations = load_licensed_stations()
    graph = build_interference_graph(stations, radius_km=DEFAULT_RADIUS_KM)
    coloring = greedy_natural_coloring(graph)
    summary = summarize_graph(graph)
    n_colors = count_colors(coloring)
    max_degree = int(summary["max_degree"])

    print(f"D = {DEFAULT_RADIUS_KM} km")
    print(f"Vértices: {summary['n_nodes']} | Arestas: {summary['n_edges']}")
    print(f"Grau máximo Δ = {max_degree}  →  teto guloso Δ+1 = {max_degree + 1}")
    print(f"Cores usadas pelo guloso natural: {n_colors}")
