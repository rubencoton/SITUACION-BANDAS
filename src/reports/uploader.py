from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import logging

from src.config import Settings
from src.drive_service import DriveAccessError, GoogleDriveService
from src.reports.naming import (
    REPORT_KIND_ANNUAL,
    REPORT_KIND_MONTHLY,
    REPORT_KIND_WEEKLY,
    ReportWindow,
)


@dataclass(slots=True)
class UploadResult:
    enabled: bool
    uploaded: bool
    skipped_existing: bool
    reason: str
    drive_file_id: str | None
    folder_ids: dict[str, str] | None


def folder_name_for_kind(kind: str, settings: Settings) -> str:
    if kind == REPORT_KIND_WEEKLY:
        return settings.drive_weekly_folder
    if kind == REPORT_KIND_MONTHLY:
        return settings.drive_monthly_folder
    if kind == REPORT_KIND_ANNUAL:
        return settings.drive_annual_folder
    raise ValueError(f"Tipo de informe no soportado: {kind}")


class ReportUploader:
    def __init__(self, settings: Settings, logger: logging.Logger):
        self.settings = settings
        self.logger = logger
        self.drive = GoogleDriveService(settings, logger)

    def upload_to_drive(
        self,
        window: ReportWindow,
        local_pdf: Path,
        sheet_id: str,
    ) -> UploadResult:
        if not self.drive.is_configured():
            return UploadResult(
                enabled=False,
                uploaded=False,
                skipped_existing=False,
                reason="Drive no configurado: faltan credenciales.",
                drive_file_id=None,
                folder_ids=None,
            )

        try:
            return self._upload_attempt(
                window=window,
                local_pdf=local_pdf,
                sheet_id=sheet_id,
                force_refresh_structure=False,
            )
        except DriveAccessError as exc:
            if "404" in str(exc):
                self.logger.warning(
                    "Cache de carpetas posiblemente obsoleto. Reintentando con refresco."
                )
                try:
                    return self._upload_attempt(
                        window=window,
                        local_pdf=local_pdf,
                        sheet_id=sheet_id,
                        force_refresh_structure=True,
                    )
                except DriveAccessError as second_exc:
                    self.logger.warning("Segundo intento Drive fallido: %s", second_exc)
                    return UploadResult(
                        enabled=True,
                        uploaded=False,
                        skipped_existing=False,
                        reason=f"Drive no accesible: {second_exc}",
                        drive_file_id=None,
                        folder_ids=None,
                    )
            self.logger.warning("No se pudo operar en Drive: %s", exc)
            return UploadResult(
                enabled=True,
                uploaded=False,
                skipped_existing=False,
                reason=f"Drive no accesible: {exc}",
                drive_file_id=None,
                folder_ids=None,
            )

    def _upload_attempt(
        self,
        window: ReportWindow,
        local_pdf: Path,
        sheet_id: str,
        force_refresh_structure: bool,
    ) -> UploadResult:
        folder_ids = self.drive.ensure_reports_structure(
            sheet_id, force_refresh=force_refresh_structure
        )
        target_folder = folder_ids[
            {
                REPORT_KIND_WEEKLY: "weekly_id",
                REPORT_KIND_MONTHLY: "monthly_id",
                REPORT_KIND_ANNUAL: "annual_id",
            }[window.kind]
        ]
        existing = self.drive.find_pdf_by_name(target_folder, window.file_name)
        if existing:
            self.logger.info(
                "No se sube duplicado. Ya existe en Drive: %s (%s)",
                existing.name,
                existing.file_id,
            )
            return UploadResult(
                enabled=True,
                uploaded=False,
                skipped_existing=True,
                reason="Ya existe archivo con ese nombre en la carpeta destino.",
                drive_file_id=existing.file_id,
                folder_ids=folder_ids,
            )

        uploaded = self.drive.upload_pdf(target_folder, local_pdf, window.file_name)
        self.logger.info("PDF subido a Drive: %s (%s)", uploaded.name, uploaded.file_id)
        return UploadResult(
            enabled=True,
            uploaded=True,
            skipped_existing=False,
            reason="Upload OK",
            drive_file_id=uploaded.file_id,
            folder_ids=folder_ids,
        )
