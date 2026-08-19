"""Settings service – real persistence for admin settings.

* **Theme** — persisted in the ``app_settings`` key/value table and
  restored on every launch.
* **Hospital holidays** — the ``hospital_holidays`` table (the same
  table the scheduling engine's holiday check reads, so dates added
  here genuinely block appointment booking).
* **Lockout config** — read-only display values sourced from
  ``app_config`` (changing them is out of scope).
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from src.config import app_config
from src.repositories.settings_repository import SettingsRepository
from src.repositories.audit_repository import HospitalHolidayRepository
from src.utils.validators import (
    strip_control_characters,
    validate_holiday_date,
)

logger = logging.getLogger(__name__)

THEME_KEY = "ui_theme"
THEMES: Tuple[str, ...] = ("flatly", "darkly")


class SettingsService:
    """Handles admin settings against real persistence."""

    def __init__(
        self,
        settings_repo: Optional[SettingsRepository] = None,
        holiday_repo: Optional[HospitalHolidayRepository] = None,
    ) -> None:
        """Initialize SettingsService.

        Args:
            settings_repo: Key/value repository (injectable for tests).
            holiday_repo: Holiday repository (injectable for tests).
        """
        self._settings_repo = settings_repo or SettingsRepository()
        self._holiday_repo = holiday_repo or HospitalHolidayRepository()

    # ── Appearance / theme ─────────────────────────────────────

    def get_theme(self) -> str:
        """Return the persisted theme name (defaults to 'flatly').

        Returns:
            Theme name (e.g. 'flatly' or 'darkly').
        """
        stored = self._settings_repo.get_value(THEME_KEY)
        if stored and stored.lower() in THEMES:
            return stored.lower()
        return "flatly"

    def set_theme(self, theme_name: str) -> Tuple[bool, str]:
        """Persist the selected theme.

        Args:
            theme_name: One of ``THEMES``.

        Returns:
            Tuple of (success, message).
        """
        name = (theme_name or "").strip().lower()
        if name not in THEMES:
            return False, (
                f"Unknown theme '{theme_name}'. Choose from {', '.join(THEMES)}."
            )
        self._settings_repo.set_value(THEME_KEY, name)
        logger.info("Theme changed to '%s'", name)
        return True, f"Theme switched to '{name}'."

    # ── Hospital holidays ──────────────────────────────────────

    def list_holidays(self) -> List[Dict[str, Any]]:
        """Return all configured holidays, sorted by date.

        Returns:
            List of dicts with holiday_id, holiday_date, description.
        """
        holidays = []
        for row in self._holiday_repo.find_all_holidays():
            holidays.append({
                "holiday_id": row["holiday_id"],
                "holiday_date": row["holiday_date"],
                "description": row.get("description")
                or row.get("holiday_name", ""),
            })
        return holidays

    def add_holiday(
        self, holiday_date: date, description: str = "",
    ) -> Tuple[bool, str, Optional[int]]:
        """Add a hospital holiday (dates on which booking is blocked).

        Args:
            holiday_date: The date the hospital is closed.
            description: Short label for the holiday.

        Returns:
            Tuple of (success, message, holiday_id_or_None).
        """
        if isinstance(holiday_date, str):
            valid, msg = validate_holiday_date(holiday_date)
            if not valid:
                return False, msg, None
            from datetime import datetime
            holiday_date = datetime.strptime(
                holiday_date.strip(), "%Y-%m-%d",
            ).date()

        if not isinstance(holiday_date, date):
            return False, "Holiday date is required.", None

        if self._holiday_repo.find_by_date(holiday_date):
            return (
                False,
                f"A holiday already exists on {holiday_date.isoformat()}.",
                None,
            )

        desc = strip_control_characters(description).strip()
        holiday_id = self._holiday_repo.create_holiday({
            "holiday_date": holiday_date,
            "holiday_name": desc or holiday_date.isoformat(),
            "description": desc,
            "is_recurring": False,
        })
        logger.info("Holiday added for %s", holiday_date.isoformat())
        return (
            True,
            f"Holiday added for {holiday_date.isoformat()}.",
            holiday_id,
        )

    def remove_holiday(self, holiday_id: int) -> Tuple[bool, str]:
        """Remove a hospital holiday.

        Args:
            holiday_id: The holiday record's ID.

        Returns:
            Tuple of (success, message).
        """
        deleted = self._holiday_repo.delete_holiday(holiday_id)
        if not deleted:
            return False, "Holiday not found."
        logger.info("Holiday %d removed", holiday_id)
        return True, "Holiday removed."

    # ── Security (read-only) ───────────────────────────────────

    def get_lockout_config(self) -> Dict[str, Any]:
        """Return the account lockout settings (read-only display).

        Returns:
            Dict with max_login_attempts, lockout_duration_minutes,
            and read_only flag.
        """
        return {
            "max_login_attempts": app_config.max_login_attempts,
            "lockout_duration_minutes": app_config.lockout_duration_minutes,
            "read_only": True,
        }
