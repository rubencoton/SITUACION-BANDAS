from __future__ import annotations

import streamlit as st

from src.pipeline import result_to_dict, run_single_report
from src.reports.naming import (
    REPORT_KIND_ANNUAL,
    REPORT_KIND_MONTHLY,
    REPORT_KIND_WEEKLY,
)


def render_reports_page() -> None:
    st.subheader("Generacion manual de informes")
    st.caption("El sistema es idempotente: no duplica si ya existe el archivo del periodo.")

    selected_kind = st.selectbox(
        "Tipo de informe",
        options=[
            REPORT_KIND_WEEKLY,
            REPORT_KIND_MONTHLY,
            REPORT_KIND_ANNUAL,
        ],
    )
    force = st.checkbox("Forzar regeneracion local", value=False)
    upload_drive = st.checkbox("Intentar subida a Drive", value=True)

    if st.button("Generar informe ahora", type="primary"):
        with st.spinner("Generando informe..."):
            result = run_single_report(
                kind=selected_kind,
                force=force,
                upload_drive=upload_drive,
            )
        st.success(f"Informe procesado: {result.report_file}")
        st.json(result_to_dict(result))
