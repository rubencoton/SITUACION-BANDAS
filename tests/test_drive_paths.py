from __future__ import annotations

from src.config import load_settings
from src.reports.uploader import folder_name_for_kind


def test_drive_folder_mapping():
    settings = load_settings()
    assert folder_name_for_kind("weekly", settings) == settings.drive_weekly_folder
    assert folder_name_for_kind("monthly", settings) == settings.drive_monthly_folder
    assert folder_name_for_kind("annual", settings) == settings.drive_annual_folder
