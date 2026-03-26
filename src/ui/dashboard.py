from __future__ import annotations

import pandas as pd
import streamlit as st

from src.analytics import AnalyticsResult
from src.data_model import NormalizedDataset


def render_dashboard(dataset: NormalizedDataset, analytics: AnalyticsResult) -> None:
    st.subheader("Cuadro de mando operativo")
    st.caption(
        f"Fuente: Google Sheet {dataset.sheet_id} | modo: {dataset.source_mode} | "
        f"extraccion: {dataset.extraction_ts.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Bandas", analytics.kpis.get("total_bandas", 0))
    col2.metric("Score medio", analytics.kpis.get("score_medio_global", 0.0))
    col3.metric("% CRITICO", f"{analytics.kpis.get('pct_critico', 0.0):.2f}%")
    col4.metric("% OPTIMO", f"{analytics.kpis.get('pct_optimo', 0.0):.2f}%")

    st.markdown("### Distribucion por estado")
    if analytics.state_distribution.empty:
        st.info("Sin datos para distribucion por estado.")
    else:
        chart_df = analytics.state_distribution.set_index("estado")["conteo"]
        st.bar_chart(chart_df)

    st.markdown("### Ranking de bandas")
    if analytics.ranking_bands.empty:
        st.info("Sin datos de ranking.")
    else:
        st.dataframe(
            analytics.ranking_bands.rename(
                columns={
                    "banda": "Banda",
                    "score_global": "Score global",
                    "semaforo": "Semaforo",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### Fases con mayor criticidad")
    if analytics.ranking_phases_critical.empty:
        st.success("No hay fases criticas en este snapshot.")
    else:
        st.dataframe(
            analytics.ranking_phases_critical.rename(
                columns={"fase": "Fase", "total_critico": "Total critico"}
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### Detalle operativo")
    if analytics.detail_table.empty:
        st.info("Sin detalle operativo.")
    else:
        st.dataframe(
            analytics.detail_table,
            use_container_width=True,
            hide_index=True,
        )
