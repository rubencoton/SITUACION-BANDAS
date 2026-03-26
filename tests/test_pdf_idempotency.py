from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
import logging
from zoneinfo import ZoneInfo

import pandas as pd

from src.analytics import AnalyticsResult
from src.config import load_settings
from src.reports.generator import PdfReportGenerator
from src.reports.naming import ReportWindow


def test_pdf_generation_skips_chart_build_when_file_exists(monkeypatch, tmp_path):
    settings = replace(
        load_settings(),
        output_dir=tmp_path / "outputs",
        history_dir=tmp_path / "history",
        log_dir=tmp_path / "logs",
    )
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_local_root.mkdir(parents=True, exist_ok=True)

    window = ReportWindow(
        kind="weekly",
        generated_at_local=datetime(2026, 4, 6, 8, 0, tzinfo=ZoneInfo("Europe/Madrid")),
        period_start=date(2026, 3, 30),
        period_end=date(2026, 4, 5),
        token="260406",
        file_stem="260406_InformeSemanal",
        file_name="260406_InformeSemanal.pdf",
        folder_name="InformeSemanal",
    )
    target_dir = settings.reports_local_root / window.folder_name
    target_dir.mkdir(parents=True, exist_ok=True)
    target_pdf = target_dir / window.file_name
    target_pdf.write_bytes(b"%PDF-1.4\n%%EOF")

    analytics = AnalyticsResult(
        kpis={},
        state_distribution=pd.DataFrame(),
        phase_distribution=pd.DataFrame(),
        ranking_bands=pd.DataFrame(),
        ranking_phases_critical=pd.DataFrame(),
        heatmap_matrix=pd.DataFrame(),
        detail_table=pd.DataFrame(),
    )

    def _unexpected_chart_build(*args, **kwargs):
        raise AssertionError("No deberia generar graficos si el PDF ya existe")

    monkeypatch.setattr("src.reports.generator.build_report_charts", _unexpected_chart_build)

    generator = PdfReportGenerator(settings, logging.getLogger("test.pdf.idempotency"))
    result = generator.generate(
        window=window,
        analytics=analytics,
        bands_df=pd.DataFrame(),
        phases_df=pd.DataFrame(),
        insights=[],
        force=False,
    )

    assert result.already_exists is True
    assert result.local_path == target_pdf
