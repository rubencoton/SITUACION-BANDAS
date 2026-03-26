from __future__ import annotations

import json
from dataclasses import asdict
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import run_single_report
from src.reports.naming import REPORT_KIND_WEEKLY


if __name__ == "__main__":
    result = run_single_report(kind=REPORT_KIND_WEEKLY)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
