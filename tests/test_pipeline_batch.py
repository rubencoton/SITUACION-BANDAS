from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from src.pipeline import ReportExecutionResult, run_reports_for_kinds


def test_run_reports_for_kinds_builds_context_once(monkeypatch, tmp_path):
    fake_settings = SimpleNamespace(
        timezone_name="Europe/Madrid",
        log_level="INFO",
        log_dir=tmp_path,
    )
    fake_logger = object()
    fake_context = object()
    counters = {"build_calls": 0, "run_calls": 0}

    monkeypatch.setattr("src.pipeline.load_settings", lambda: fake_settings)
    monkeypatch.setattr("src.pipeline.configure_logging", lambda *_: fake_logger)
    monkeypatch.setattr(
        "src.pipeline._current_local_dt",
        lambda settings, now_override=None: datetime(
            2026, 4, 6, 8, 5, tzinfo=ZoneInfo("Europe/Madrid")
        ),
    )

    def _fake_build_context(settings, logger):
        counters["build_calls"] += 1
        return fake_context

    def _fake_run_with_context(context, kind, local_now, force, upload_drive):
        counters["run_calls"] += 1
        return ReportExecutionResult(
            kind=kind,
            report_file=f"{kind}.pdf",
            report_local_path=f"/tmp/{kind}.pdf",
            period_start="2026-04-01",
            period_end="2026-04-07",
            generated_at=local_now.isoformat(),
            source_mode="public_export",
            upload={
                "enabled": False,
                "uploaded": False,
                "skipped_existing": False,
                "reason": "test",
                "drive_file_id": None,
                "folder_ids": None,
            },
            already_exists_local=False,
            snapshot_path=f"/tmp/{kind}.json",
            kpis={"total_bandas": 0},
            insights=[],
        )

    monkeypatch.setattr("src.pipeline._build_execution_context", _fake_build_context)
    monkeypatch.setattr("src.pipeline._run_report_with_context", _fake_run_with_context)

    result = run_reports_for_kinds(["weekly", "monthly"])

    assert counters["build_calls"] == 1
    assert counters["run_calls"] == 2
    assert [item.kind for item in result] == ["weekly", "monthly"]
