"""Carrega, filtra, limpa e deduplica estações da ANATEL.

O CSV oficial traz uma linha por emissão licenciada: a mesma ERB aparece
várias vezes (frequências e azimutes diferentes). O grafo de interferência
usa um vértice por estação física, então a deduplicação acontece aqui,
antes de qualquer cálculo de distância.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV_PATH = PROJECT_ROOT / "data" / "ERBs - Anatel.csv"

# Municípios da instância principal (Bauru) e da vizinhança usada nas
# instâncias pequena e grande. Nomes exatamente como no CSV da ANATEL.
DEFAULT_MUNICIPALITIES = ("Bauru", "Agudos", "Pederneiras", "Piratininga")

# Recorte geográfico amplo do Brasil, só para descartar lixo numérico
# (0,0), campos vazios ou coordenadas invertidas. Não é um filtro de região.
BRAZIL_LAT_RANGE = (-35.0, 6.0)
BRAZIL_LON_RANGE = (-75.0, -30.0)

# Colunas do CSV Spectrum-E / dados abertos da ANATEL (separador "|").
COL_STATION_ID = "NumEstacao"
COL_MUNICIPALITY = "Municipio.NomeMunicipio"
COL_LATITUDE = "Latitude"
COL_LONGITUDE = "Longitude"
COL_OPERATOR = "NomeEntidade"
COL_ADDRESS = "EnderecoEstacao"
COL_TECHNOLOGY = "Tecnologia"
COL_TX_FREQUENCY = "FreqTxMHz"
COL_UF = "SiglaUf"

RAW_COLUMNS = (
    COL_STATION_ID,
    COL_MUNICIPALITY,
    COL_LATITUDE,
    COL_LONGITUDE,
    COL_OPERATOR,
    COL_ADDRESS,
    COL_TECHNOLOGY,
    COL_TX_FREQUENCY,
    COL_UF,
)

# Nomes internos (inglês) usados no restante do projeto.
RENAME_MAP = {
    COL_STATION_ID: "station_id",
    COL_MUNICIPALITY: "municipality",
    COL_LATITUDE: "latitude",
    COL_LONGITUDE: "longitude",
    COL_OPERATOR: "operator",
    COL_ADDRESS: "address",
    COL_TECHNOLOGY: "technology",
    COL_TX_FREQUENCY: "tx_frequency_mhz",
    COL_UF: "uf",
}


def load_licensed_stations(
    csv_path: str | Path | None = None,
    municipalities: tuple[str, ...] | list[str] | None = None,
    uf: str = "SP",
) -> pd.DataFrame:
    """Lê o CSV da ANATEL e devolve uma linha por estação física.

    Passos (nessa ordem, de propósito):
    1. ler só as colunas necessárias;
    2. filtrar UF e municípios;
    3. converter e validar latitude/longitude;
    4. deduplicar por ``NumEstacao``.

    Parameters
    ----------
    csv_path:
        Caminho do CSV. Se omitido, usa ``data/ERBs - Anatel.csv``.
    municipalities:
        Nomes dos municípios a manter. ``None`` usa
        :data:`DEFAULT_MUNICIPALITIES`.
    uf:
        Sigla da unidade federativa. Padrão ``"SP"`` para não misturar
        homônimos (ex.: Agudos do Sul / PR).

    Returns
    -------
    pandas.DataFrame
        Colunas: ``station_id``, ``municipality``, ``latitude``,
        ``longitude``, ``operator``, ``address``, ``technologies``,
        ``license_rows``, ``uf``.
    """
    path = Path(csv_path) if csv_path is not None else DEFAULT_CSV_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"CSV da ANATEL não encontrado em {path}. "
            "Coloque o arquivo baixado em data/ERBs - Anatel.csv."
        )

    chosen_municipalities = (
        DEFAULT_MUNICIPALITIES if municipalities is None else tuple(municipalities)
    )

    raw = _read_csv(path)
    filtered = _filter_region(raw, municipalities=chosen_municipalities, uf=uf)
    cleaned = _clean_coordinates(filtered)
    valid = _drop_invalid_coordinates(cleaned)
    unique_stations = _deduplicate_stations(valid)
    return unique_stations.reset_index(drop=True)


def _read_csv(path: Path) -> pd.DataFrame:
    """Lê o CSV com separador ``|`` e todas as colunas como texto.

    Tudo entra como ``str`` para evitar que o pandas “adivinhe” tipos
    (``NumEstacao`` virar inteiro, latitude com vírgula falhar, etc.).
    A conversão numérica fica explícita em :func:`_clean_coordinates`.
    """
    try:
        frame = pd.read_csv(
            path,
            sep="|",
            usecols=list(RAW_COLUMNS),
            dtype=str,
            encoding="utf-8",
            keep_default_na=False,
        )
    except UnicodeDecodeError:
        frame = pd.read_csv(
            path,
            sep="|",
            usecols=list(RAW_COLUMNS),
            dtype=str,
            encoding="latin-1",
            keep_default_na=False,
        )

    missing = [column for column in RAW_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(
            "O CSV não tem as colunas esperadas do dataset da ANATEL: "
            + ", ".join(missing)
        )

    return frame.rename(columns=RENAME_MAP)


def _normalize_name(value: str) -> str:
    """Compara nomes de município sem se importar com maiúsculas ou espaços."""
    return str(value).strip().casefold()


def _filter_region(
    frame: pd.DataFrame,
    municipalities: tuple[str, ...],
    uf: str,
) -> pd.DataFrame:
    """Mantém só as linhas da UF e dos municípios pedidos."""
    wanted_municipalities = {_normalize_name(name) for name in municipalities}
    municipality_ok = frame["municipality"].map(_normalize_name).isin(
        wanted_municipalities
    )
    uf_ok = frame["uf"].str.strip().str.upper() == uf.strip().upper()
    return frame.loc[municipality_ok & uf_ok].copy()


def _parse_coordinate(value: str) -> float | None:
    """Converte um campo de coordenada para float, ou ``None`` se inválido.

    Aceita ponto ou vírgula decimal. String vazia, ``"nan"`` e valores
    que não são número viram ``None`` (depois são descartados).
    """
    text = str(value).strip().replace(",", ".")
    if text == "" or text.lower() in {"nan", "none", "null", "-"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _clean_coordinates(frame: pd.DataFrame) -> pd.DataFrame:
    """Transforma latitude e longitude de texto em números."""
    cleaned = frame.copy()
    cleaned["latitude"] = cleaned["latitude"].map(_parse_coordinate)
    cleaned["longitude"] = cleaned["longitude"].map(_parse_coordinate)
    return cleaned


def _drop_invalid_coordinates(frame: pd.DataFrame) -> pd.DataFrame:
    """Remove linhas sem coordenada ou fora do retângulo do Brasil.

    Também exige ``station_id`` não vazio: sem identificador não dá para
    deduplicar com segurança.
    """
    lat_min, lat_max = BRAZIL_LAT_RANGE
    lon_min, lon_max = BRAZIL_LON_RANGE

    has_id = frame["station_id"].str.strip() != ""
    lat_ok = frame["latitude"].between(lat_min, lat_max)
    lon_ok = frame["longitude"].between(lon_min, lon_max)
    return frame.loc[has_id & lat_ok & lon_ok].copy()


def _join_unique_sorted(values: pd.Series) -> str:
    """Junta valores únicos não vazios, em ordem alfabética, separados por vírgula."""
    unique_values = sorted({str(item).strip() for item in values if str(item).strip()})
    return ", ".join(unique_values)


def _deduplicate_stations(frame: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por ``station_id`` (identificador oficial da estação).

    A mesma ERB gera várias linhas no CSV (uma por frequência/azimute).
    Operadoras diferentes no mesmo torre têm ``NumEstacao`` diferentes e
    permanecem como vértices separados: a distância haversine entre elas
    será ~0 km e o grafo as ligará se D > 0.

    Coordenada, município, operadora e endereço vêm da primeira linha
    válida do grupo. Tecnologias são agregadas para o mapa/relatório.
    ``license_rows`` guarda quantas linhas originais aquela estação tinha
    — útil para mostrar no relatório o efeito da deduplicação.
    """
    grouped = frame.groupby("station_id", sort=False)
    return grouped.agg(
        municipality=("municipality", "first"),
        latitude=("latitude", "first"),
        longitude=("longitude", "first"),
        operator=("operator", "first"),
        address=("address", "first"),
        technologies=("technology", _join_unique_sorted),
        license_rows=("station_id", "size"),
        uf=("uf", "first"),
    ).reset_index()


if __name__ == "__main__":
    stations = load_licensed_stations()
    print(f"Estações únicas: {len(stations)}")
    print(stations.groupby("municipality").size().rename("stations").to_string())
    print(f"Linhas originais (após filtro de município): {int(stations['license_rows'].sum())}")
