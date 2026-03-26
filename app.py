from __future__ import annotations

import streamlit as st

from src.analytics import compute_analytics
from src.config import load_settings
from src.emailing.preview import build_email_preview
from src.logging_utils import configure_logging
from src.sheets_reader import SheetsReader
from src.ui.dashboard import render_dashboard
from src.ui.reports_page import render_reports_page


st.set_page_config(
    page_title="SITUACION BANDAS",
    page_icon="SB",
    layout="wide",
)

settings = load_settings()
logger = configure_logging(settings.log_level, settings.log_dir)


@st.cache_data(ttl=300, show_spinner=False)
def _load_dataset_and_analytics(sheet_id: str):
    local_settings = load_settings()
    local_logger = configure_logging(local_settings.log_level, local_settings.log_dir)
    reader = SheetsReader(local_settings, local_logger)
    dataset = reader.extract_dataset(sheet_id)
    analytics = compute_analytics(dataset.bands_df, dataset.phases_df)
    return dataset, analytics


st.title("SITUACION BANDAS")
st.caption("Artes Buho | Dashboard operativo e informes corporativos")
st.markdown(
    """
    <style>
      .stApp { background: linear-gradient(180deg, #fffdf4 0%, #ffffff 35%, #ffffff 100%); }
      h1, h2, h3 { color: #C62828 !important; }
      [data-testid="stMetricValue"] { color: #C62828; }
    </style>
    """,
    unsafe_allow_html=True,
)

header_col1, header_col2 = st.columns([1, 1])
with header_col1:
    st.caption("Cache de datos: 5 minutos")
with header_col2:
    if st.button("Actualizar datos ahora"):
        st.cache_data.clear()
        st.rerun()

dataset, analytics = _load_dataset_and_analytics(settings.google_sheet_id)

tab_dashboard, tab_reports, tab_email = st.tabs(
    ["Dashboard", "Informes", "Preview correo"]
)

with tab_dashboard:
    render_dashboard(dataset, analytics)

with tab_reports:
    render_reports_page()

with tab_email:
    st.subheader("Preview de envio (dry-run)")
    preview = build_email_preview(
        dataset.bands_df,
        subject="Informe corporativo SITUACION BANDAS",
    )
    st.write(f"Total destinatarios detectados: {preview['total_destinatarios']}")
    st.dataframe(
        {"destinatario": preview["destinatarios"]},
        use_container_width=True,
        hide_index=True,
    )
