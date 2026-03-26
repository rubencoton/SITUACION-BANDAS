from __future__ import annotations

from src.history import HistoryRepository


def test_upsert_entry_replaces_same_kind_and_token(tmp_path):
    repo = HistoryRepository(tmp_path)
    index = [
        {
            "report_kind": "weekly",
            "report_token": "260406",
            "generated_at": "2026-04-06T08:00:00",
            "snapshot_path": "/tmp/old.json",
        },
        {
            "report_kind": "monthly",
            "report_token": "2603",
            "generated_at": "2026-04-01T08:00:00",
            "snapshot_path": "/tmp/month.json",
        },
    ]

    updated = repo._upsert_entry(
        index,
        {
            "report_kind": "weekly",
            "report_token": "260406",
            "generated_at": "2026-04-06T08:15:00",
            "snapshot_path": "/tmp/new.json",
        },
    )

    assert len(updated) == 2
    weekly = [
        item
        for item in updated
        if item["report_kind"] == "weekly" and item["report_token"] == "260406"
    ]
    assert len(weekly) == 1
    assert weekly[0]["snapshot_path"] == "/tmp/new.json"
