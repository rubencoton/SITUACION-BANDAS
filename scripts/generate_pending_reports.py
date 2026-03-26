from __future__ import annotations

import json
from dataclasses import asdict
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import run_single_report
from src.reports.naming import (
    REPORT_KIND_ANNUAL,
    REPORT_KIND_MONTHLY,
    REPORT_KIND_WEEKLY,
)


if __name__ == "__main__":
    results = []
    for kind in (REPORT_KIND_WEEKLY, REPORT_KIND_MONTHLY, REPORT_KIND_ANNUAL):
        results.append(asdict(run_single_report(kind=kind)))
    print(json.dumps(results, ensure_ascii=False, indent=2))
