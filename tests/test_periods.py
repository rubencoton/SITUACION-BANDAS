from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from src.reports.naming import (
    REPORT_KIND_MONTHLY,
    REPORT_KIND_WEEKLY,
    build_report_window,
)
from src.reports.scheduler import due_report_kinds


def test_weekly_uses_last_completed_week_even_if_run_sunday():
    dt = datetime(2026, 4, 5, 8, 30, tzinfo=ZoneInfo("Europe/Madrid"))  # domingo
    window = build_report_window(REPORT_KIND_WEEKLY, dt)
    assert window.period_start.isoformat() == "2026-03-23"
    assert window.period_end.isoformat() == "2026-03-29"


def test_monthly_year_boundary():
    dt = datetime(2027, 1, 1, 8, 15, tzinfo=ZoneInfo("Europe/Madrid"))
    window = build_report_window(REPORT_KIND_MONTHLY, dt)
    assert window.file_name == "2612_InformeMensual.pdf"
    assert window.period_start.isoformat() == "2026-12-01"
    assert window.period_end.isoformat() == "2026-12-31"


def test_scheduler_due_weekly_and_monthly_at_local_0800():
    dt = datetime(2026, 6, 1, 8, 10, tzinfo=ZoneInfo("Europe/Madrid"))  # lunes, dia 1
    due = due_report_kinds(dt)
    assert "weekly" in due
    assert "monthly" in due


def test_scheduler_not_due_outside_hour():
    dt = datetime(2026, 6, 1, 9, 0, tzinfo=ZoneInfo("Europe/Madrid"))
    due = due_report_kinds(dt)
    assert due == []
