from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_settings
from src.emailing.preview import build_email_preview
from src.logging_utils import configure_logging
from src.sheets_reader import SheetsReader


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview de destinatarios de correo.")
    parser.add_argument(
        "--subject",
        default="Informe corporativo SITUACION BANDAS",
        help="Asunto de correo a previsualizar",
    )
    args = parser.parse_args()

    settings = load_settings()
    logger = configure_logging(settings.log_level, settings.log_dir)
    reader = SheetsReader(settings, logger)
    dataset = reader.extract_dataset(settings.google_sheet_id)
    preview = build_email_preview(dataset.bands_df, args.subject)
    print(json.dumps(preview, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
