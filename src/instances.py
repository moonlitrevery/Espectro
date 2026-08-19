"""Catálogo das instâncias de teste do trabalho.

Pelo enunciado precisamos de pelo menos três instâncias com tamanhos
diferentes, documentadas com município, número de estações (depois da
deduplicação) e raio D. Aqui elas são *declaradas*, não calculadas na
hora: o ``analysis.py`` e o dashboard só escolhem um ``instance_id``.

Como o enunciado pede os vizinhos “para a instância pequena e para
compor a grande”:

* **pequena** — Agudos + Pederneiras + Piratininga (sem Bauru), D = 1 km;
* **média** — só Bauru (a instância principal), D = 1 km;
* **grande** — Bauru + os três vizinhos, D = 1 km.

As duas últimas variam só o raio, no mesmo conjunto de vértices da
grande. Assim o relatório separa “efeito do tamanho” de “efeito de D”.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import networkx as nx
import pandas as pd

from src.data_prep import DEFAULT_MUNICIPALITIES, load_licensed_stations
from src.graph_builder import DEFAULT_RADIUS_KM, build_interference_graph, summarize_graph

NEIGHBOR_MUNICIPALITIES = ("Agudos", "Pederneiras", "Piratininga")
BAURU = ("Bauru",)
REGION = DEFAULT_MUNICIPALITIES  # Bauru + vizinhos


@dataclass(frozen=True)
class InstanceSpec:
    """Receita de uma instância: onde e com qual D. Ainda sem o grafo."""

    instance_id: str
    title: str
    municipalities: tuple[str, ...]
    radius_km: float
    description: str


@dataclass(frozen=True)
class LoadedInstance:
    """Instância já materializada: estações deduplicadas + grafo."""

    spec: InstanceSpec
    stations: pd.DataFrame
    graph: nx.Graph

    @property
    def n_stations(self) -> int:
        return len(self.stations)

    @property
    def n_edges(self) -> int:
        return self.graph.number_of_edges()


INSTANCE_SPECS: tuple[InstanceSpec, ...] = (
    InstanceSpec(
        instance_id="small",
        title="Pequena — vizinhos de Bauru (D = 1 km)",
        municipalities=NEIGHBOR_MUNICIPALITIES,
        radius_km=DEFAULT_RADIUS_KM,
        description=(
            "Agudos, Pederneiras e Piratininga, sem a sede. "
            "Menos estações e malha mais espalhada que Bauru."
        ),
    ),
    InstanceSpec(
        instance_id="medium",
        title="Média — Bauru (D = 1 km)",
        municipalities=BAURU,
        radius_km=DEFAULT_RADIUS_KM,
        description=(
            "Instância principal: só o município de Bauru, raio urbano padrão."
        ),
    ),
    InstanceSpec(
        instance_id="large",
        title="Grande — Bauru e vizinhos (D = 1 km)",
        municipalities=REGION,
        radius_km=DEFAULT_RADIUS_KM,
        description=(
            "Região completa. Mesmo D da pequena e da média, para comparar "
            "o efeito do número de vértices."
        ),
    ),
    InstanceSpec(
        instance_id="large_d05",
        title="Grande — D = 0,5 km",
        municipalities=REGION,
        radius_km=0.5,
        description=(
            "Mesmos vértices da grande; raio menor. Menos arestas, "
            "interferência mais local."
        ),
    ),
    InstanceSpec(
        instance_id="large_d20",
        title="Grande — D = 2 km",
        municipalities=REGION,
        radius_km=2.0,
        description=(
            "Mesmos vértices da grande; raio maior. Grafo mais denso, "
            "mais cores esperadas."
        ),
    ),
)

# Recortes geográficos do dashboard (o slider cobre as variações de D).
GEOGRAPHIC_INSTANCE_IDS = ("small", "medium", "large")

_SPECS_BY_ID = {spec.instance_id: spec for spec in INSTANCE_SPECS}


def list_instance_ids() -> tuple[str, ...]:
    """Identificadores na ordem em que aparecem no relatório."""
    return tuple(spec.instance_id for spec in INSTANCE_SPECS)


def get_spec(instance_id: str) -> InstanceSpec:
    """Devolve a receita; não lê o CSV."""
    if instance_id not in _SPECS_BY_ID:
        known = ", ".join(list_instance_ids())
        raise ValueError(
            f"Instância desconhecida: {instance_id!r}. Opções: {known}."
        )
    return _SPECS_BY_ID[instance_id]


def filter_stations(stations: pd.DataFrame, spec: InstanceSpec) -> pd.DataFrame:
    """Recorta o catálogo já carregado pelos municípios da instância.

    O CSV é lido uma vez (os quatro municípios). Cada instância só filtra
    linhas — não relê o arquivo de 2 milhões de linhas.
    """
    wanted = set(spec.municipalities)
    filtered = stations.loc[stations["municipality"].isin(wanted)].copy()
    return filtered.reset_index(drop=True)


def load_instance(
    instance_id: str,
    csv_path: str | Path | None = None,
    stations: pd.DataFrame | None = None,
    radius_km: float | None = None,
) -> LoadedInstance:
    """Lê (ou reutiliza) as estações, filtra municípios e monta o grafo.

    Parameters
    ----------
    stations:
        Catálogo já deduplicado. Se ``None``, carrega o CSV. O
        ``analysis.py`` passa o catálogo para não reler o arquivo em
        cada instância.
    radius_km:
        Se informado, substitui o D da receita (o slider do dashboard).
    """
    spec = get_spec(instance_id)
    if radius_km is not None:
        spec = replace(spec, radius_km=radius_km)
    catalog = (
        stations
        if stations is not None
        else load_licensed_stations(csv_path=csv_path)
    )
    selected = filter_stations(catalog, spec)
    graph = build_interference_graph(selected, radius_km=spec.radius_km)
    return LoadedInstance(spec=spec, stations=selected, graph=graph)


if __name__ == "__main__":
    catalog = load_licensed_stations()
    print(
        f"{'id':<12} {'D_km':>5} {'n':>6} {'m':>8} "
        f"{'dens':>7} {'isol':>5}  municípios"
    )
    for spec in INSTANCE_SPECS:
        loaded = load_instance(spec.instance_id, stations=catalog)
        summary = summarize_graph(loaded.graph)
        places = ", ".join(spec.municipalities)
        print(
            f"{spec.instance_id:<12} {spec.radius_km:>5.1f} "
            f"{loaded.n_stations:>6} {loaded.n_edges:>8} "
            f"{summary['density']:>7.4f} {summary['isolated']:>5}  {places}"
        )
        print(f"             {spec.title}")
