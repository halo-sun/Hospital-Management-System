"""Unit tests for the SettingsService (real persistence).

Exercises theme get/set persistence, holiday add/remove/duplicate
handling, and the read-only lockout config against mocked
repositories — no database required.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from src.services.settings_service import SettingsService


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def service() -> SettingsService:
    """A SettingsService with mocked repositories."""
    return SettingsService(settings_repo=MagicMock(), holiday_repo=MagicMock())


@pytest.fixture
def mock_settings(service: SettingsService) -> MagicMock:
    """Access the mocked SettingsRepository."""
    return service._settings_repo


@pytest.fixture
def mock_holiday(service: SettingsService) -> MagicMock:
    """Access the mocked HospitalHolidayRepository."""
    return service._holiday_repo


# ── Theme ─────────────────────────────────────────────────────


class TestTheme:
    """Theme get/set against the app_settings table."""

    def test_default_theme_is_flatly(self, service: SettingsService,
                                     mock_settings: MagicMock) -> None:
        """No stored theme falls back to 'flatly'."""
        mock_settings.get_value.return_value = None
        assert service.get_theme() == "flatly"
        mock_settings.get_value.assert_called_once_with("ui_theme")

    def test_stored_theme_restored(self, service: SettingsService,
                                   mock_settings: MagicMock) -> None:
        """A stored theme is returned lowercase."""
        mock_settings.get_value.return_value = "DARKLY"
        assert service.get_theme() == "darkly"

    def test_invalid_stored_theme_falls_back(self, service: SettingsService,
                                             mock_settings: MagicMock) -> None:
        """An unknown stored value falls back to 'flatly'."""
        mock_settings.get_value.return_value = "midnight"
        assert service.get_theme() == "flatly"

    def test_set_theme_persists(self, service: SettingsService,
                                mock_settings: MagicMock) -> None:
        """set_theme validates and writes to the settings table."""
        ok, msg = service.set_theme("darkly")
        assert ok is True
        assert "darkly" in msg
        mock_settings.set_value.assert_called_once_with("ui_theme", "darkly")

    def test_set_theme_case_insensitive(self, service: SettingsService,
                                        mock_settings: MagicMock) -> None:
        """Theme names are normalised to lowercase."""
        ok, _ = service.set_theme("DARKLY")
        assert ok is True
        mock_settings.set_value.assert_called_once_with("ui_theme", "darkly")

    def test_set_unknown_theme_fails(self, service: SettingsService,
                                     mock_settings: MagicMock) -> None:
        """Unknown themes are rejected and nothing is written."""
        ok, msg = service.set_theme("midnight")
        assert ok is False
        assert "Unknown theme" in msg
        mock_settings.set_value.assert_not_called()


# ── Holidays ──────────────────────────────────────────────────


class TestHolidays:
    """Holiday add/remove against the hospital_holidays table."""

    def test_list_holidays(self, service: SettingsService,
                           mock_holiday: MagicMock) -> None:
        """list_holidays normalises rows to id/date/description."""
        mock_holiday.find_all_holidays.return_value = [
            {"holiday_id": 1, "holiday_date": date(2026, 1, 1),
             "holiday_name": "New Year", "description": "New Year celebration"},
            {"holiday_id": 2, "holiday_date": date(2026, 12, 25),
             "holiday_name": "Christmas", "description": None},
        ]
        holidays = service.list_holidays()
        assert len(holidays) == 2
        assert holidays[0]["holiday_id"] == 1
        assert holidays[0]["holiday_date"] == date(2026, 1, 1)
        # Falls back to holiday_name when description is NULL.
        assert holidays[1]["description"] == "Christmas"

    def test_add_holiday(self, service: SettingsService,
                         mock_holiday: MagicMock) -> None:
        """Adding a holiday inserts a non-recurring row and returns the id."""
        mock_holiday.find_by_date.return_value = None
        mock_holiday.create_holiday.return_value = 3
        ok, msg, holiday_id = service.add_holiday(
            date(2026, 8, 15), "Independence Day",
        )
        assert ok is True
        assert holiday_id == 3
        assert "2026-08-15" in msg
        call_data = mock_holiday.create_holiday.call_args.args[0]
        assert call_data["holiday_date"] == date(2026, 8, 15)
        assert call_data["holiday_name"] == "Independence Day"
        assert call_data["is_recurring"] is False

    def test_add_holiday_accepts_string_date(self, service: SettingsService,
                                             mock_holiday: MagicMock) -> None:
        """A YYYY-MM-DD string date is parsed and validated."""
        mock_holiday.find_by_date.return_value = None
        ok, msg, _ = service.add_holiday("2026-08-15", "Independence Day")
        assert ok is True
        assert mock_holiday.create_holiday.call_args.args[0]["holiday_date"] == date(2026, 8, 15)

    def test_add_holiday_invalid_date_string(self, service: SettingsService,
                                             mock_holiday: MagicMock) -> None:
        """A malformed date string is rejected."""
        ok, msg, _ = service.add_holiday("15/08/2026", "Bad format")
        assert ok is False
        assert "format" in msg.lower()
        mock_holiday.create_holiday.assert_not_called()

    def test_add_holiday_duplicate_rejected(self, service: SettingsService,
                                            mock_holiday: MagicMock) -> None:
        """A duplicate date is rejected before any insert."""
        mock_holiday.find_by_date.return_value = {"holiday_id": 1}
        ok, msg, _ = service.add_holiday(date(2026, 1, 1), "Duplicate")
        assert ok is False
        assert "already exists" in msg.lower()
        mock_holiday.create_holiday.assert_not_called()

    def test_add_holiday_strips_control_chars(self, service: SettingsService,
                                              mock_holiday: MagicMock) -> None:
        """Control characters are stripped from the description."""
        mock_holiday.find_by_date.return_value = None
        service.add_holiday(date(2026, 8, 15), "Holiday \x00\x1b")
        call_data = mock_holiday.create_holiday.call_args.args[0]
        assert call_data["description"] == "Holiday"

    def test_remove_holiday(self, service: SettingsService,
                            mock_holiday: MagicMock) -> None:
        """Removing an existing holiday works."""
        mock_holiday.delete_holiday.return_value = 1
        ok, msg = service.remove_holiday(2)
        assert ok is True
        mock_holiday.delete_holiday.assert_called_once_with(2)

    def test_remove_missing_holiday_fails(self, service: SettingsService,
                                          mock_holiday: MagicMock) -> None:
        """Removing a non-existent holiday reports an error."""
        mock_holiday.delete_holiday.return_value = 0
        ok, msg = service.remove_holiday(99999)
        assert ok is False
        assert "not found" in msg.lower()


# ── Lockout config ────────────────────────────────────────────


class TestLockoutConfig:
    """The lockout config is a read-only display value."""

    def test_returns_expected_keys(self, service: SettingsService) -> None:
        """The config exposes threshold/window and is marked read-only."""
        config = service.get_lockout_config()
        assert "max_login_attempts" in config
        assert "lockout_duration_minutes" in config
        assert config["read_only"] is True

    def test_values_are_positive(self, service: SettingsService) -> None:
        """Threshold and window are positive numbers."""
        config = service.get_lockout_config()
        assert config["max_login_attempts"] > 0
        assert config["lockout_duration_minutes"] > 0
