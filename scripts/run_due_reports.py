from __future__ import annotations

import json
from dataclasses import asdict
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import run_due_reports


if __name__ == "__main__":
    results = run_due_reports()
    print(json.dumps([asdict(item) for item in results], ensure_ascii=False, indent=2))
