from __future__ import annotations

from dataclasses import replace
import logging

from src.config import load_settings
from src.drive_service import GoogleDriveService


def test_drive_folder_cache_roundtrip(tmp_path):
    settings = replace(
        load_settings(),
        history_dir=tmp_path,
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path / "logs",
    )
    service = GoogleDriveService(settings, logging.getLogger("test.drive.cache"))
    sheet_id = "sheet-test-id"
    expected = {
        "sheet_parent_id": "p1",
        "informes_id": "f1",
        "weekly_id": "w1",
        "monthly_id": "m1",
        "annual_id": "a1",
    }

    service._save_cached_folder_ids(sheet_id, expected)
    loaded = service._load_cached_folder_ids(sheet_id)

    assert loaded == expected


def test_ensure_reports_structure_uses_cache_without_api_calls(tmp_path):
    settings = replace(
        load_settings(),
        history_dir=tmp_path,
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path / "logs",
    )
    service = GoogleDriveService(settings, logging.getLogger("test.drive.cache.hit"))
    sheet_id = "sheet-cache-hit"
    expected = {
        "sheet_parent_id": "p2",
        "informes_id": "f2",
        "weekly_id": "w2",
        "monthly_id": "m2",
        "annual_id": "a2",
    }
    service._save_cached_folder_ids(sheet_id, expected)

    def _unexpected(*args, **kwargs):
        raise AssertionError("No deberia llamar a API con cache valida")

    service.resolve_sheet_parent_folder = _unexpected
    service.ensure_folder = _unexpected

    result = service.ensure_reports_structure(sheet_id)
    assert result == expected
