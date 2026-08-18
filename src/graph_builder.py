"""Monta o grafo de interferência entre ERBs.

Cada estação vira um vértice. Duas estações são ligadas por uma aresta se
a distância geográfica real entre elas (haversine, em km) for **menor**
que o raio de interferência ``D``.

networkx entra só como estrutura (``Graph``, vizinhança, grau). A
coloração fica nos módulos de ``src/coloring/`` — este arquivo não pinta
nada.
"""

from __future__ import annotations

import math

import networkx as nx
import pandas as pd

# Raio médio da Terra em km (valor clássico da fórmula de haversine).
# A diferença para o raio equatorial WGS84 (~6378 km) é < 0,2% — irrelevante
# na escala de 1 km deste modelo.
EARTH_RADIUS_KM = 6371.0

# Padrão usado se ninguém passar D. Ordem de grandeza do alcance de uma
# macrocélula urbana (0,5–2 km). As instâncias do trabalho variam esse valor.
DEFAULT_RADIUS_KM = 1.0

REQUIRED_COLUMNS = ("station_id", "latitude", "longitude")

# Atributos copiados do DataFrame para o vértice (úteis no mapa depois).
OPTIONAL_NODE_COLUMNS = (
    "municipality",
    "operator",
    "address",
    "technologies",
    "license_rows",
    "uf",
)


def haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Distância em km entre dois pontos na superfície da Terra.

    A fórmula trata a Terra como uma esfera. Não usamos distância
    euclidiana sobre graus de latitude/longitude: 1° de longitude no
    equador vale ~111 km, mas em Bauru (~22°S) vale ~103 km, então a
    escala ficaria distorcida.

    Passos (os mesmos da identidade trigonométrica clássica):
    1. converter graus → radianos;
    2. calcular ``a`` (senos do meio-ângulo da diferença);
    3. ``c = 2 * arcsin(sqrt(a))`` é o ângulo central, em radianos;
    4. multiplicar pelo raio da Terra.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    sin_half_phi = math.sin(delta_phi / 2.0)
    sin_half_lambda = math.sin(delta_lambda / 2.0)
    a = (
        sin_half_phi * sin_half_phi
        + math.cos(phi1) * math.cos(phi2) * sin_half_lambda * sin_half_lambda
    )
    # Proteção numérica: a deveria estar em [0, 1], mas arredondamento
    # de ponto flutuante pode passar um fio desses limites.
    a = min(1.0, max(0.0, a))
    central_angle = 2.0 * math.asin(math.sqrt(a))
    return EARTH_RADIUS_KM * central_angle


def build_interference_graph(
    stations: pd.DataFrame,
    radius_km: float = DEFAULT_RADIUS_KM,
) -> nx.Graph:
    """Constrói o grafo não-direcionado de interferência.

    Parameters
    ----------
    stations:
        Saída de ``load_licensed_stations`` (uma linha por ERB).
    radius_km:
        Raio de interferência ``D``, em quilômetros. Aresta existe se
        ``distância < D`` (desigualdade estrita, como no enunciado).

    Returns
    -------
    networkx.Graph
        Vértices identificados por ``station_id``. Sem peso nas arestas.
    """
    if radius_km <= 0:
        raise ValueError("O raio de interferência D precisa ser maior que zero.")
    _require_columns(stations)
    if stations["station_id"].duplicated().any():
        raise ValueError(
            "Há station_id repetido. Deduplique com load_licensed_stations "
            "antes de montar o grafo."
        )

    graph = nx.Graph()
    station_ids = stations["station_id"].astype(str).tolist()
    latitudes = stations["latitude"].tolist()
    longitudes = stations["longitude"].tolist()

    for index, station_id in enumerate(station_ids):
        graph.add_node(
            station_id,
            **_node_attributes(stations.iloc[index]),
        )

    # Par a par, i < j: o grafo é não-direcionado, então cada dupla
    # entra no máximo uma vez. n≈2000 cabe em um duplo for (~2 milhões
    # de pares); a clareza importa mais que um índice espacial aqui.
    n_stations = len(station_ids)
    for i in range(n_stations):
        for j in range(i + 1, n_stations):
            distance = haversine_km(
                latitudes[i],
                longitudes[i],
                latitudes[j],
                longitudes[j],
            )
            if distance < radius_km:
                graph.add_edge(station_ids[i], station_ids[j])

    return graph


def summarize_graph(graph: nx.Graph) -> dict[str, float | int]:
    """Números básicos do grafo, para o relatório e para o ``__main__``.

    Densidade = 2m / (n(n-1)), fração de pares que de fato interferem.
    Isolados = ERBs sem ninguém a menos de D km (grau 0).
    """
    n_nodes = graph.number_of_nodes()
    n_edges = graph.number_of_edges()
    degrees = [degree for _node, degree in graph.degree()]

    if n_nodes <= 1:
        density = 0.0
    else:
        density = (2.0 * n_edges) / (n_nodes * (n_nodes - 1))

    return {
        "n_nodes": n_nodes,
        "n_edges": n_edges,
        "density": density,
        "isolated": sum(1 for degree in degrees if degree == 0),
        "min_degree": min(degrees) if degrees else 0,
        "max_degree": max(degrees) if degrees else 0,
        "mean_degree": (sum(degrees) / n_nodes) if n_nodes else 0.0,
    }


def _require_columns(stations: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in stations.columns]
    if missing:
        raise ValueError(
            "DataFrame sem colunas obrigatórias para o grafo: " + ", ".join(missing)
        )


def _node_attributes(row: pd.Series) -> dict:
    """Latitude/longitude sempre; o resto só se a coluna existir."""
    attributes = {
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"]),
    }
    for column in OPTIONAL_NODE_COLUMNS:
        if column in row.index:
            attributes[column] = row[column]
    return attributes


if __name__ == "__main__":
    from src.data_prep import load_licensed_stations

    stations = load_licensed_stations()
    print(f"Estações carregadas: {len(stations)}")
    for radius in (0.5, 1.0, 2.0, 5.0):
        graph = build_interference_graph(stations, radius_km=radius)
        summary = summarize_graph(graph)
        print(
            f"D={radius:.1f} km | "
            f"n={summary['n_nodes']} | "
            f"m={summary['n_edges']} | "
            f"densidade={summary['density']:.4f} | "
            f"grau médio={summary['mean_degree']:.1f} | "
            f"grau máx={summary['max_degree']} | "
            f"isolados={summary['isolated']}"
        )
