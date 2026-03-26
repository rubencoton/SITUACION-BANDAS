from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


REPORT_KIND_WEEKLY = "weekly"
REPORT_KIND_MONTHLY = "monthly"
REPORT_KIND_ANNUAL = "annual"

REPORT_FOLDER_BY_KIND = {
    REPORT_KIND_WEEKLY: "InformeSemanal",
    REPORT_KIND_MONTHLY: "InformeMensual",
    REPORT_KIND_ANNUAL: "InformeAnual",
}


@dataclass(slots=True)
class ReportWindow:
    kind: str
    generated_at_local: datetime
    period_start: date
    period_end: date
    token: str
    file_stem: str
    file_name: str
    folder_name: str

    @property
    def period_label(self) -> str:
        if self.kind == REPORT_KIND_ANNUAL:
            return f"Anio {self.period_start.year}"
        return (
            f"{self.period_start.strftime('%d/%m/%Y')} - "
            f"{self.period_end.strftime('%d/%m/%Y')}"
        )


def now_local(timezone_name: str) -> datetime:
    return datetime.now(tz=ZoneInfo(timezone_name))


def build_report_window(kind: str, current_local_dt: datetime) -> ReportWindow:
    if kind == REPORT_KIND_WEEKLY:
        return build_weekly_window(current_local_dt)
    if kind == REPORT_KIND_MONTHLY:
        return build_monthly_window(current_local_dt)
    if kind == REPORT_KIND_ANNUAL:
        return build_annual_window(current_local_dt)
    raise ValueError(f"Tipo de informe no soportado: {kind}")


def build_weekly_window(generated_at_local: datetime) -> ReportWindow:
    generation_date = generated_at_local.date()
    reference_date = generation_date - timedelta(days=1)
    offset = (reference_date.weekday() - 6) % 7
    period_end = reference_date - timedelta(days=offset)
    period_start = period_end - timedelta(days=6)

    token = generation_date.strftime("%y%m%d")
    stem = f"{token}_InformeSemanal"
    return ReportWindow(
        kind=REPORT_KIND_WEEKLY,
        generated_at_local=generated_at_local,
        period_start=period_start,
        period_end=period_end,
        token=token,
        file_stem=stem,
        file_name=f"{stem}.pdf",
        folder_name=REPORT_FOLDER_BY_KIND[REPORT_KIND_WEEKLY],
    )


def build_monthly_window(generated_at_local: datetime) -> ReportWindow:
    generation_date = generated_at_local.date()
    first_day_current = generation_date.replace(day=1)
    period_end = first_day_current - timedelta(days=1)
    period_start = period_end.replace(day=1)

    token = period_start.strftime("%y%m")
    stem = f"{token}_InformeMensual"
    return ReportWindow(
        kind=REPORT_KIND_MONTHLY,
        generated_at_local=generated_at_local,
        period_start=period_start,
        period_end=period_end,
        token=token,
        file_stem=stem,
        file_name=f"{stem}.pdf",
        folder_name=REPORT_FOLDER_BY_KIND[REPORT_KIND_MONTHLY],
    )


def build_annual_window(generated_at_local: datetime) -> ReportWindow:
    generation_date = generated_at_local.date()
    previous_year = generation_date.year - 1
    period_start = date(previous_year, 1, 1)
    period_end = date(previous_year, 12, 31)

    token = str(previous_year)
    stem = f"{token}_InformeAnual"
    return ReportWindow(
        kind=REPORT_KIND_ANNUAL,
        generated_at_local=generated_at_local,
        period_start=period_start,
        period_end=period_end,
        token=token,
        file_stem=stem,
        file_name=f"{stem}.pdf",
        folder_name=REPORT_FOLDER_BY_KIND[REPORT_KIND_ANNUAL],
    )


def build_due_anchor(timezone_name: str, day_value: date | None = None) -> datetime:
    local_date = day_value or now_local(timezone_name).date()
    return datetime.combine(
        local_date,
        time(hour=8, minute=0, second=0),
        tzinfo=ZoneInfo(timezone_name),
    )
