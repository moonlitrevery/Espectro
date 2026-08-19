"""Testes da análise comparativa (usa o CSV miniatura, não o da ANATEL)."""

from pathlib import Path

from src.analysis import (
    ALGORITHMS,
    analyze_instance,
    results_table,
    run_analyses,
)
from src.instances import load_instance

FIXTURE = Path(__file__).parent / "fixtures" / "mini_erbs.csv"


def test_three_algorithms_are_registered_in_baseline_order():
    ids = [algorithm_id for algorithm_id, _title, _fn in ALGORITHMS]
    assert ids == ["greedy_natural", "welsh_powell", "dsatur"]


def test_analyze_medium_fixture_is_valid_and_matches_clique():
    """Duas operadoras no mesmo ponto: clique 2, qualquer guloso usa 2 cores."""
    loaded = load_instance("medium", csv_path=FIXTURE)
    analysis = analyze_instance(loaded)

    assert analysis.instance_id == "medium"
    assert analysis.n_vertices == 2
    assert analysis.clique_size == 2
    assert len(analysis.runs) == 3

    for run in analysis.runs:
        assert run.is_valid
        assert run.n_colors == 2
        assert run.elapsed_seconds >= 0.0
        assert run.n_colors >= analysis.clique_size


def test_run_analyses_two_instances_from_fixture():
    analyses = run_analyses(csv_path=FIXTURE, instance_ids=("small", "medium"))
    assert [item.instance_id for item in analyses] == ["small", "medium"]

    small = analyses[0]
    # Agudos, Pederneiras e Piratininga no fixture: 3 estações longe.
    assert small.n_vertices == 3
    for run in small.runs:
        assert run.is_valid
        assert run.n_colors >= small.clique_size


def test_results_table_has_one_row_per_algorithm():
    analyses = run_analyses(csv_path=FIXTURE, instance_ids=("medium",))
    table = results_table(analyses)
    assert len(table) == 3
    assert set(table["algorithm_id"]) == {
        "greedy_natural",
        "welsh_powell",
        "dsatur",
    }
    assert bool(table["is_valid"].all())
    assert bool((table["n_colors"] >= table["clique_lower_bound"]).all())


def test_n_colors_come_from_the_validator_not_len_of_dict():
    """Coloração com furos seria invalidada; cores contadas só nos vértices."""
    loaded = load_instance("medium", csv_path=FIXTURE)
    analysis = analyze_instance(loaded)
    run = analysis.run_for("dsatur")
    assert set(run.coloring) == set(loaded.graph.nodes())
    assert run.n_colors == len(set(run.coloring.values()))


def test_skipping_clique_does_not_claim_optimality():
    loaded = load_instance("medium", csv_path=FIXTURE)
    analysis = analyze_instance(loaded, compute_clique=False)
    assert analysis.clique_computed is False
    table = results_table([analysis])
    assert not bool(table["is_optimal"].any())
    assert table["clique_lower_bound"].isna().all()
