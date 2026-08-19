"""Dashboard Streamlit: instância, raio D, comparação e mapa por canal.

Só a interface vive aqui. Grafo, coloração, validação e clique continuam
nos módulos de ``src/``. O botão **Rodar** dispara o cálculo; mover o
slider sozinho não reconstroi o grafo (senão cada pixel do slider
custaria segundos).
"""

from __future__ import annotations

import colorsys
from pathlib import Path

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

from src.analysis import analyze_instance, results_table
from src.data_prep import DEFAULT_CSV_PATH, load_licensed_stations
from src.instances import get_spec, load_instance

# No dashboard o clique não tenta todos os começos (na instância grande
# com D=2 isso passou de 3 minutos). 15 vértices de maior grau bastam
# para um piso honesto na hora da apresentação.
DASHBOARD_CLIQUE_STARTS = 15


def channel_hex(color_index: int) -> str:
    """Cor HTML para o canal ``color_index`` (0, 1, 2, ...).

    192 canais não cabem em paleta qualitativa. Espalhamos no círculo
    HSV com o número de ouro para canais vizinhos não ficarem irmãos
    na escala de cor (o olho ainda não distingue 192 tons — é um mapa
    de tendência, não uma legenda de 192 entradas).
    """
    hue = (color_index * 0.618033988749895) % 1.0
    red, green, blue = colorsys.hsv_to_rgb(hue, 0.72, 0.92)
    return f"#{int(red * 255):02x}{int(green * 255):02x}{int(blue * 255):02x}"


def stations_with_channels(stations: pd.DataFrame, coloring: dict) -> pd.DataFrame:
    """Acrescenta a cor do algoritmo (0-based) e o canal exibido (1-based)."""
    painted = stations.copy()
    painted["channel"] = painted["station_id"].astype(str).map(coloring)
    painted["canal"] = painted["channel"] + 1
    return painted


def make_folium_map(painted: pd.DataFrame) -> folium.Map:
    """Um círculo por ERB, pintado pelo canal atribuído."""
    center_lat = float(painted["latitude"].mean())
    center_lon = float(painted["longitude"].mean())
    fmap = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles="OpenStreetMap",
    )
    for row in painted.itertuples():
        popup = (
            f"<b>Estação {row.station_id}</b><br>"
            f"Canal {int(row.canal)}<br>"
            f"{row.municipality}<br>"
            f"{row.operator}"
        )
        folium.CircleMarker(
            location=[row.latitude, row.longitude],
            radius=5,
            color=channel_hex(int(row.channel)),
            fill=True,
            fill_opacity=0.85,
            weight=1,
            popup=folium.Popup(popup, max_width=280),
        ).add_to(fmap)
    return fmap


def main() -> None:
    st.set_page_config(
        page_title="Espectro — coloração de ERBs",
        layout="wide",
    )
    st.title("Alocação de canais entre ERBs (Bauru e vizinhos)")
    st.caption(
        "Cada cor é um canal. Vértices adjacentes (ERBs a menos de D km) "
        "não podem ter o mesmo canal. Coloração implementada do zero; "
        "networkx só segura o grafo."
    )

    if not Path(DEFAULT_CSV_PATH).exists():
        st.error(
            f"CSV da ANATEL não encontrado em `{DEFAULT_CSV_PATH}`. "
            "Coloque o arquivo baixado nessa pasta."
        )
        return

    with st.sidebar:
        st.header("Parâmetros")
        geo_labels = {
            "small": "Pequena — vizinhos (sem Bauru)",
            "medium": "Média — só Bauru",
            "large": "Grande — Bauru e vizinhos",
        }
        chosen_label = st.selectbox(
            "Instância (recorte geográfico)",
            list(geo_labels.values()),
        )
        instance_id = next(
            instance_id
            for instance_id, label in geo_labels.items()
            if label == chosen_label
        )
        spec = get_spec(instance_id)

        st.caption(" · ".join(spec.municipalities))

        radius_km = st.slider(
            "Raio de interferência D (km)",
            min_value=0.5,
            max_value=3.0,
            value=float(spec.radius_km),
            step=0.1,
            key=f"radius_{instance_id}",
            help=(
                "D é uma simplificação: interferência real também depende "
                "de potência, relevo e azimute — não modelamos isso."
            ),
        )
        compute_clique = st.checkbox(
            "Calcular piso por clique (15 maiores graus)",
            value=True,
            help=(
                "O relatório tenta todos os começos. Aqui limitamos a 15 "
                "para o mapa não ficar minutos carregando."
            ),
        )
        run_clicked = st.button("Rodar coloração", type="primary")

    if run_clicked:
        with st.spinner(
            "Montando o grafo (haversine) e rodando os três algoritmos…"
        ):
            catalog = _load_catalog()
            loaded = load_instance(
                instance_id,
                stations=catalog,
                radius_km=radius_km,
            )
            analysis = analyze_instance(
                loaded,
                compute_clique=compute_clique,
                clique_max_starts=(
                    DASHBOARD_CLIQUE_STARTS if compute_clique else None
                ),
            )
            st.session_state["dashboard"] = {
                "instance_id": instance_id,
                "radius_km": radius_km,
                "stations": loaded.stations,
                "analysis": analysis,
            }

    payload = st.session_state.get("dashboard")
    if payload is None:
        st.info("Escolha a instância e o raio D, depois clique em **Rodar coloração**.")
        return

    analysis = payload["analysis"]
    stations = payload["stations"]
    stale = (
        payload["instance_id"] != instance_id
        or abs(payload["radius_km"] - radius_km) > 1e-9
    )
    if stale:
        st.warning(
            "Os parâmetros da barra lateral mudaram. "
            "O mapa ainda mostra a última execução. Clique em **Rodar coloração**."
        )

    _render_results(analysis, stations)


@st.cache_data(show_spinner="Lendo o CSV da ANATEL…")
def _load_catalog() -> pd.DataFrame:
    """CSV cacheado pelo Streamlit: um read por sessão, não por clique."""
    return load_licensed_stations()


def _render_results(analysis, stations: pd.DataFrame) -> None:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Estações (n)", f"{analysis.n_vertices}")
    m2.metric("Arestas (m)", f"{analysis.n_edges}")
    m3.metric("Grau máximo Δ", f"{analysis.max_degree}")
    if analysis.clique_computed:
        m4.metric("Piso χ (clique)", f"{analysis.clique_size}")
    else:
        m4.metric("Piso χ (clique)", "—")

    table = results_table([analysis])
    algo_cols = st.columns(3)
    for column, run in zip(algo_cols, analysis.runs):
        with column:
            st.subheader(run.title)
            st.metric("Cores / canais", run.n_colors)
            st.write(f"Tempo: **{run.elapsed_seconds:.3f} s**")
            st.write("Validação: **ok**" if run.is_valid else "Validação: **INVÁLIDA**")
            if analysis.clique_computed:
                gap = run.n_colors - analysis.clique_size
                if gap == 0 and run.is_valid:
                    st.success("Ótima nesta instância (empatou com o clique).")
                else:
                    st.caption(f"Gap para o piso: {gap}")

    chart_colors = px.bar(
        table,
        x="algorithm",
        y="n_colors",
        title="Cores usadas por algoritmo",
        labels={"algorithm": "Algoritmo", "n_colors": "Cores"},
    )
    chart_time = px.bar(
        table,
        x="algorithm",
        y="elapsed_seconds",
        title="Tempo de coloração (s)",
        labels={"algorithm": "Algoritmo", "elapsed_seconds": "Segundos"},
    )
    c1, c2 = st.columns(2)
    c1.plotly_chart(chart_colors, use_container_width=True)
    c2.plotly_chart(chart_time, use_container_width=True)

    st.subheader("Mapa das ERBs por canal")
    map_labels = {run.title: run.algorithm_id for run in analysis.runs}
    chosen_algo = st.radio(
        "Coloração exibida no mapa",
        list(map_labels),
        horizontal=True,
    )
    run = analysis.run_for(map_labels[chosen_algo])
    painted = stations_with_channels(stations, run.coloring)
    fmap = make_folium_map(painted)
    components.html(fmap.get_root().render(), height=560)
    st.caption(
        f"{len(painted)} estações · canal = cor + 1 · "
        "tons próximos no mapa podem ser canais diferentes "
        f"(são {run.n_colors} canais no total)."
    )


if __name__ == "__main__":
    main()
