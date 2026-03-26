from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path

import pandas as pd

from src.analytics import AnalyticsResult


@dataclass(slots=True)
class SnapshotPayload:
    report_kind: str
    report_token: str
    generated_at: str
    period_start: str
    period_end: str
    report_filename: str
    source_mode: str
    kpis: dict
    bands: list[dict]
    phases: list[dict]


class HistoryRepository:
    def __init__(self, history_dir: Path):
        self.history_dir = history_dir
        self.index_path = self.history_dir / "snapshots_index.json"
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def save_snapshot(
        self,
        report_kind: str,
        report_token: str,
        period_start: str,
        period_end: str,
        report_filename: str,
        source_mode: str,
        analytics: AnalyticsResult,
        bands_df: pd.DataFrame,
        phases_df: pd.DataFrame,
    ) -> Path:
        payload = SnapshotPayload(
            report_kind=report_kind,
            report_token=report_token,
            generated_at=datetime.now().isoformat(),
            period_start=period_start,
            period_end=period_end,
            report_filename=report_filename,
            source_mode=source_mode,
            kpis=analytics.kpis,
            bands=json.loads(
                bands_df.to_json(orient="records", force_ascii=False, date_format="iso")
            ),
            phases=json.loads(
                phases_df.to_json(orient="records", force_ascii=False, date_format="iso")
            ),
        )
        snap_name = f"{report_kind}_{report_token}_snapshot.json"
        snap_path = self.history_dir / snap_name
        snap_path.write_text(
            json.dumps(asdict(payload), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        index = self._load_index()
        index.append(
            {
                "report_kind": report_kind,
                "report_token": report_token,
                "generated_at": payload.generated_at,
                "snapshot_path": str(snap_path),
            }
        )
        self.index_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return snap_path

    def load_previous_equivalent(self, report_kind: str, report_token: str) -> dict | None:
        entries = self._load_index()
        candidates = [
            item
            for item in entries
            if item.get("report_kind") == report_kind
            and str(item.get("report_token")) < str(report_token)
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda x: x.get("report_token", ""), reverse=True)
        latest = candidates[0]
        snapshot_path = Path(latest["snapshot_path"])
        if not snapshot_path.exists():
            return None
        return json.loads(snapshot_path.read_text(encoding="utf-8"))

    def _load_index(self) -> list[dict]:
        if not self.index_path.exists():
            return []
        try:
            raw = json.loads(self.index_path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                return raw
            return []
        except json.JSONDecodeError:
            return []
