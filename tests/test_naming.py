from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from src.reports.naming import (
    REPORT_KIND_ANNUAL,
    REPORT_KIND_MONTHLY,
    REPORT_KIND_WEEKLY,
    build_report_window,
)


def test_weekly_name_and_period_match_spec():
    dt = datetime(2026, 4, 6, 8, 0, tzinfo=ZoneInfo("Europe/Madrid"))
    window = build_report_window(REPORT_KIND_WEEKLY, dt)

    assert window.file_name == "260406_InformeSemanal.pdf"
    assert window.period_start.isoformat() == "2026-03-30"
    assert window.period_end.isoformat() == "2026-04-05"


def test_monthly_name_and_period_match_spec():
    dt = datetime(2026, 4, 1, 8, 0, tzinfo=ZoneInfo("Europe/Madrid"))
    window = build_report_window(REPORT_KIND_MONTHLY, dt)

    assert window.file_name == "2603_InformeMensual.pdf"
    assert window.period_start.isoformat() == "2026-03-01"
    assert window.period_end.isoformat() == "2026-03-31"


def test_annual_name_and_period_match_spec():
    dt = datetime(2027, 1, 1, 8, 0, tzinfo=ZoneInfo("Europe/Madrid"))
    window = build_report_window(REPORT_KIND_ANNUAL, dt)

    assert window.file_name == "2026_InformeAnual.pdf"
    assert window.period_start.isoformat() == "2026-01-01"
    assert window.period_end.isoformat() == "2026-12-31"
