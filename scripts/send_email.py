from __future__ import annotations

import argparse
import json
from dataclasses import asdict
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_settings
from src.emailing.preview import build_email_preview
from src.emailing.sender import EmailService
from src.logging_utils import configure_logging
from src.sheets_reader import SheetsReader


def _latest_report_pdf(root_reports_dir: Path) -> Path | None:
    candidates = sorted(root_reports_dir.rglob("*.pdf"), key=lambda p: p.stat().st_mtime)
    return candidates[-1] if candidates else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Envio manual de informe. Por defecto siempre dry-run."
    )
    parser.add_argument(
        "--subject",
        default="Informe corporativo SITUACION BANDAS",
        help="Asunto del correo",
    )
    parser.add_argument(
        "--body",
        default=(
            "Adjuntamos el informe corporativo de SITUACION BANDAS. "
            "Este envio ha sido lanzado manualmente por operador autorizado."
        ),
        help="Cuerpo del correo",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fuerza simulacion sin envio real",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Solicita envio real (si la configuracion lo permite).",
    )
    parser.add_argument(
        "--confirm-live",
        action="store_true",
        help="Confirmacion explicita para envios reales.",
    )
    args = parser.parse_args()

    settings = load_settings()
    logger = configure_logging(settings.log_level, settings.log_dir)
    reader = SheetsReader(settings, logger)
    dataset = reader.extract_dataset(settings.google_sheet_id)
    preview = build_email_preview(dataset.bands_df, args.subject)
    recipients = preview["destinatarios"]

    attachment = _latest_report_pdf(settings.reports_local_root)
    attachments = [attachment] if attachment else []

    service = EmailService(settings, logger)
    dry_run_mode = True
    if args.live and not args.dry_run:
        dry_run_mode = False
    result = service.send_manual(
        recipients=recipients,
        subject=args.subject,
        body=args.body,
        attachments=attachments,
        dry_run=dry_run_mode,
        confirm_live=args.confirm_live,
    )
    payload = {
        "preview": preview,
        "attachment": str(attachment) if attachment else None,
        "result": asdict(result),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
