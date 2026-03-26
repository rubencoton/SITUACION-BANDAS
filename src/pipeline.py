from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from src.analytics import AnalyticsResult, compute_analytics
from src.config import Settings, load_settings
from src.history import HistoryRepository
from src.insights import build_executive_insights
from src.logging_utils import configure_logging
from src.reports.generator import GeneratedReport, PdfReportGenerator
from src.reports.naming import (
    REPORT_KIND_ANNUAL,
    REPORT_KIND_MONTHLY,
    REPORT_KIND_WEEKLY,
    build_report_window,
)
from src.reports.scheduler import due_report_kinds
from src.reports.uploader import UploadResult, ReportUploader
from src.sheets_reader import SheetsReader


@dataclass(slots=True)
class ReportExecutionResult:
    kind: str
    report_file: str
    report_local_path: str
    period_start: str
    period_end: str
    generated_at: str
    source_mode: str
    upload: dict
    already_exists_local: bool
    snapshot_path: str
    kpis: dict
    insights: list[str]


def _current_local_dt(settings: Settings, now_override: datetime | None = None) -> datetime:
    if now_override is not None:
        if now_override.tzinfo is None:
            return now_override.replace(tzinfo=ZoneInfo(settings.timezone_name))
        return now_override.astimezone(ZoneInfo(settings.timezone_name))
    return datetime.now(ZoneInfo(settings.timezone_name))


def run_single_report(
    kind: str,
    now_override: datetime | None = None,
    force: bool = False,
    upload_drive: bool = True,
) -> ReportExecutionResult:
    settings = load_settings()
    logger = configure_logging(settings.log_level, settings.log_dir)
    logger.info("Inicio pipeline informe tipo=%s", kind)

    local_now = _current_local_dt(settings, now_override=now_override)
    window = build_report_window(kind, local_now)

    reader = SheetsReader(settings, logger)
    dataset = reader.extract_dataset(settings.google_sheet_id)
    analytics = compute_analytics(dataset.bands_df, dataset.phases_df)

    history_repo = HistoryRepository(settings.history_dir)
    previous = history_repo.load_previous_equivalent(kind, window.token)
    insights = build_executive_insights(
        analytics.kpis,
        analytics.ranking_phases_critical,
        previous_snapshot=previous,
    )

    generator = PdfReportGenerator(settings, logger)
    generated = generator.generate(
        window,
        analytics,
        dataset.bands_df,
        dataset.phases_df,
        insights,
        force=force,
    )

    uploader = ReportUploader(settings, logger)
    upload_result: UploadResult
    if upload_drive:
        upload_result = uploader.upload_to_drive(
            window=window,
            local_pdf=generated.local_path,
            sheet_id=settings.google_sheet_id,
        )
    else:
        upload_result = UploadResult(
            enabled=False,
            uploaded=False,
            skipped_existing=False,
            reason="Upload Drive desactivado en ejecucion.",
            drive_file_id=None,
            folder_ids=None,
        )

    snapshot_path = history_repo.save_snapshot(
        report_kind=kind,
        report_token=window.token,
        period_start=window.period_start.isoformat(),
        period_end=window.period_end.isoformat(),
        report_filename=window.file_name,
        source_mode=dataset.source_mode,
        analytics=analytics,
        bands_df=dataset.bands_df,
        phases_df=dataset.phases_df,
    )

    logger.info("Fin pipeline informe tipo=%s", kind)
    return ReportExecutionResult(
        kind=kind,
        report_file=window.file_name,
        report_local_path=str(generated.local_path),
        period_start=window.period_start.isoformat(),
        period_end=window.period_end.isoformat(),
        generated_at=window.generated_at_local.isoformat(),
        source_mode=dataset.source_mode,
        upload={
            "enabled": upload_result.enabled,
            "uploaded": upload_result.uploaded,
            "skipped_existing": upload_result.skipped_existing,
            "reason": upload_result.reason,
            "drive_file_id": upload_result.drive_file_id,
            "folder_ids": upload_result.folder_ids,
        },
        already_exists_local=generated.already_exists,
        snapshot_path=str(snapshot_path),
        kpis=analytics.kpis,
        insights=insights,
    )


def run_due_reports(now_override: datetime | None = None) -> list[ReportExecutionResult]:
    settings = load_settings()
    logger = configure_logging(settings.log_level, settings.log_dir)
    local_now = _current_local_dt(settings, now_override=now_override)
    due = due_report_kinds(local_now)
    logger.info("Comprobacion de informes pendientes en %s. Due=%s", local_now, due)
    results: list[ReportExecutionResult] = []
    for kind in due:
        results.append(run_single_report(kind=kind, now_override=local_now))
    return results


def kinds_supported() -> tuple[str, str, str]:
    return (
        REPORT_KIND_WEEKLY,
        REPORT_KIND_MONTHLY,
        REPORT_KIND_ANNUAL,
    )


def result_to_dict(result: ReportExecutionResult) -> dict:
    return asdict(result)
