"""Roda os três algoritmos em cada instância e compara os resultados.

Para cada par (instância, algoritmo) registramos:
* número de cores — vem do **validador**, não do próprio algoritmo;
* tempo de execução — só a chamada da coloração (``time.perf_counter``);
* se a coloração é própria — de novo o validador;
* o piso por clique da instância, para ver quem empatou com o ótimo.

O tempo do grafo, do clique e da validação fica de fora do cronômetro:
o enunciado pede o tempo de cada **algoritmo de coloração**.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.coloring.dsatur import dsatur_coloring
from src.coloring.greedy_natural import greedy_natural_coloring
from src.coloring.validator import validate_coloring
from src.coloring.welsh_powell import welsh_powell_coloring
from src.data_prep import load_licensed_stations
from src.graph_builder import summarize_graph
from src.instances import LoadedInstance, list_instance_ids, load_instance
from src.lower_bound import estimate_max_clique

# Ordem do relatório: baseline primeiro, depois os dois melhoramentos.
ALGORITHMS: tuple[tuple[str, str, Callable], ...] = (
    ("greedy_natural", "Guloso natural", greedy_natural_coloring),
    ("welsh_powell", "Welsh–Powell", welsh_powell_coloring),
    ("dsatur", "DSATUR", dsatur_coloring),
)


@dataclass(frozen=True)
class AlgorithmResult:
    """Um algoritmo em uma instância."""

    algorithm_id: str
    title: str
    n_colors: int
    elapsed_seconds: float
    is_valid: bool
    coloring: dict


@dataclass(frozen=True)
class InstanceAnalysis:
    """Tudo o que o relatório precisa de uma instância."""

    instance_id: str
    title: str
    radius_km: float
    n_vertices: int
    n_edges: int
    max_degree: int
    clique_size: int
    clique_seconds: float
    runs: tuple[AlgorithmResult, ...]

    def run_for(self, algorithm_id: str) -> AlgorithmResult:
        for run in self.runs:
            if run.algorithm_id == algorithm_id:
                return run
        raise KeyError(algorithm_id)


def analyze_instance(loaded: LoadedInstance) -> InstanceAnalysis:
    """Piso por clique + os três algoritmos no grafo já montado."""
    graph = loaded.graph
    summary = summarize_graph(graph)

    clique_started = time.perf_counter()
    clique = estimate_max_clique(graph)
    clique_seconds = time.perf_counter() - clique_started

    runs = tuple(
        _run_algorithm(algorithm_id, title, color_fn, graph)
        for algorithm_id, title, color_fn in ALGORITHMS
    )

    return InstanceAnalysis(
        instance_id=loaded.spec.instance_id,
        title=loaded.spec.title,
        radius_km=loaded.spec.radius_km,
        n_vertices=int(summary["n_nodes"]),
        n_edges=int(summary["n_edges"]),
        max_degree=int(summary["max_degree"]),
        clique_size=clique.size,
        clique_seconds=clique_seconds,
        runs=runs,
    )


def run_analyses(
    csv_path: str | Path | None = None,
    instance_ids: Sequence[str] | None = None,
    verbose: bool = False,
) -> tuple[InstanceAnalysis, ...]:
    """Lê o CSV uma vez e analisa cada instância pedida (ou todas)."""
    chosen_ids = (
        list(instance_ids) if instance_ids is not None else list(list_instance_ids())
    )
    catalog = load_licensed_stations(csv_path=csv_path)
    analyses = []
    for instance_id in chosen_ids:
        if verbose:
            print(f"→ {instance_id}...", flush=True)
        loaded = load_instance(instance_id, stations=catalog)
        analysis = analyze_instance(loaded)
        analyses.append(analysis)
        if verbose:
            print(
                f"  n={analysis.n_vertices} m={analysis.n_edges} "
                f"piso={analysis.clique_size} "
                f"(clique {analysis.clique_seconds:.1f}s)",
                flush=True,
            )
    return tuple(analyses)


def results_table(analyses: Sequence[InstanceAnalysis]) -> pd.DataFrame:
    """Uma linha por (instância, algoritmo) — para o relatório e o dashboard."""
    rows = []
    for analysis in analyses:
        for run in analysis.runs:
            gap = run.n_colors - analysis.clique_size
            rows.append(
                {
                    "instance_id": analysis.instance_id,
                    "instance": analysis.title,
                    "radius_km": analysis.radius_km,
                    "n_vertices": analysis.n_vertices,
                    "n_edges": analysis.n_edges,
                    "max_degree": analysis.max_degree,
                    "clique_lower_bound": analysis.clique_size,
                    "algorithm_id": run.algorithm_id,
                    "algorithm": run.title,
                    "n_colors": run.n_colors,
                    "gap_to_clique": gap,
                    "is_optimal": run.is_valid and gap == 0,
                    "is_valid": run.is_valid,
                    "elapsed_seconds": run.elapsed_seconds,
                }
            )
    return pd.DataFrame(rows)


def format_report(analyses: Sequence[InstanceAnalysis]) -> str:
    """Texto monoespaçado para colar no relatório / imprimir no terminal."""
    table = results_table(analyses)
    lines = [
        "Análise das instâncias (cores do validador; tempo só da coloração)",
        "",
    ]
    for analysis in analyses:
        lines.append(
            f"{analysis.instance_id} | {analysis.title} | "
            f"n={analysis.n_vertices} m={analysis.n_edges} | "
            f"D={analysis.radius_km} km | "
            f"Δ={analysis.max_degree} | "
            f"piso clique={analysis.clique_size} "
            f"({analysis.clique_seconds:.3f}s)"
        )
        slice_ = table.loc[table["instance_id"] == analysis.instance_id]
        for _, row in slice_.iterrows():
            optimal = "ótima" if row["is_optimal"] else f"gap={int(row['gap_to_clique'])}"
            valid = "ok" if row["is_valid"] else "INVÁLIDA"
            lines.append(
                f"  {row['algorithm']:<16} "
                f"cores={int(row['n_colors']):>4}  "
                f"{optimal:<8}  "
                f"{valid:<8}  "
                f"{row['elapsed_seconds']:.4f}s"
            )
        lines.append("")
    return "\n".join(lines)


def _run_algorithm(
    algorithm_id: str,
    title: str,
    color_fn: Callable,
    graph,
) -> AlgorithmResult:
    started = time.perf_counter()
    coloring = color_fn(graph)
    elapsed = time.perf_counter() - started

    report = validate_coloring(graph, coloring)
    return AlgorithmResult(
        algorithm_id=algorithm_id,
        title=title,
        n_colors=report.n_colors,
        elapsed_seconds=elapsed,
        is_valid=report.is_valid,
        coloring=coloring,
    )


if __name__ == "__main__":
    print("Carregando instâncias e rodando os três algoritmos...\n")
    analyses = run_analyses(verbose=True)
    print(format_report(analyses))
    print("Tabela completa:")
    print(results_table(analyses).to_string(index=False))
