"""Testes do carregamento e da deduplicação das estações da ANATEL."""

from pathlib import Path

from src.data_prep import load_licensed_stations

FIXTURE = Path(__file__).parent / "fixtures" / "mini_erbs.csv"


def test_deduplicates_same_station_with_different_frequencies():
    """A estação 100 aparece duas vezes (LTE e WCDMA) e vira um único vértice."""
    stations = load_licensed_stations(csv_path=FIXTURE, municipalities=("Bauru",))
    bauru_ids = set(stations["station_id"])
    assert "100" in bauru_ids
    assert (stations["station_id"] == "100").sum() == 1

    station_100 = stations.loc[stations["station_id"] == "100"].iloc[0]
    assert station_100["license_rows"] == 2
    assert "LTE" in station_100["technologies"]
    assert "WCDMA" in station_100["technologies"]


def test_keeps_colocated_operators_as_separate_stations():
    """Duas operadoras no mesmo lat/long têm NumEstacao diferentes: dois vértices."""
    stations = load_licensed_stations(csv_path=FIXTURE, municipalities=("Bauru",))
    ids = set(stations["station_id"])
    assert {"100", "200"}.issubset(ids)


def test_filters_municipality_and_uf():
    """Agudos-SP entra; Agudos do Sul (PR) e São Paulo ficam de fora."""
    stations = load_licensed_stations(
        csv_path=FIXTURE,
        municipalities=("Bauru", "Agudos", "Pederneiras", "Piratininga"),
    )
    municipalities = set(stations["municipality"])
    assert municipalities == {"Bauru", "Agudos", "Pederneiras", "Piratininga"}
    assert "400" not in set(stations["station_id"])
    assert "800" not in set(stations["station_id"])


def test_drops_invalid_coordinates():
    """Latitude/longitude 0,0 não é uma ERB real e deve ser descartada."""
    stations = load_licensed_stations(csv_path=FIXTURE, municipalities=("Bauru",))
    assert "500" not in set(stations["station_id"])


def test_output_columns_are_stable():
    stations = load_licensed_stations(csv_path=FIXTURE, municipalities=("Bauru",))
    expected = {
        "station_id",
        "municipality",
        "latitude",
        "longitude",
        "operator",
        "address",
        "technologies",
        "license_rows",
        "uf",
    }
    assert expected.issubset(set(stations.columns))
    assert stations["latitude"].dtype.kind == "f"
    assert stations["longitude"].dtype.kind == "f"
