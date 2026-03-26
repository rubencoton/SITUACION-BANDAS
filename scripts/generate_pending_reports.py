from __future__ import annotations

import json
from dataclasses import asdict
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import run_reports_for_kinds
from src.reports.naming import (
    REPORT_KIND_ANNUAL,
    REPORT_KIND_MONTHLY,
    REPORT_KIND_WEEKLY,
)


if __name__ == "__main__":
    results = [
        asdict(item)
        for item in run_reports_for_kinds(
            [REPORT_KIND_WEEKLY, REPORT_KIND_MONTHLY, REPORT_KIND_ANNUAL]
        )
    ]
    print(json.dumps(results, ensure_ascii=False, indent=2))
