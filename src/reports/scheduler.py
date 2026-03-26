from __future__ import annotations

from datetime import datetime

from src.reports.naming import (
    REPORT_KIND_ANNUAL,
    REPORT_KIND_MONTHLY,
    REPORT_KIND_WEEKLY,
)


def due_report_kinds(now_local_dt: datetime) -> list[str]:
    """
    Reglas de disparo:
    - semanal: lunes entre 08:00 y 08:59 hora local
    - mensual: dia 1 entre 08:00 y 08:59 hora local
    - anual: 1 de enero entre 08:00 y 08:59 hora local
    """
    if now_local_dt.hour != 8:
        return []

    due: list[str] = []
    if now_local_dt.weekday() == 0:
        due.append(REPORT_KIND_WEEKLY)
    if now_local_dt.day == 1:
        due.append(REPORT_KIND_MONTHLY)
    if now_local_dt.day == 1 and now_local_dt.month == 1:
        due.append(REPORT_KIND_ANNUAL)
    return due
