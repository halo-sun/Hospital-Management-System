"""Settings controller – coordinates admin settings requests.

All methods are RBAC-gated to admins via the shared ``@require_role``
decorator and delegate to :class:`SettingsService`, which persists the
theme to ``app_settings`` and holidays to the ``hospital_holidays``
table (the same table the scheduling engine's holiday check reads).
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from src.controllers.auth_controller import AuthController
from src.auth.rbac import require_role
from src.constants import Role
from src.services.settings_service import SettingsService, THEMES

logger = logging.getLogger(__name__)


class SettingsController:
    """Handles admin settings requests from the GUI layer (admin only)."""

    THEMES: Tuple[str, ...] = THEMES

    def __init__(
        self,
        auth_ctrl: Optional[AuthController] = None,
        service: Optional[SettingsService] = None,
    ) -> None:
        """Initialise SettingsController.

        Args:
            auth_ctrl: The shared AuthController used for RBAC checks.
                Defaults to a new instance; the admin factory passes the
                application-wide controller so the session is shared.
            service: The settings service (injectable for tests).
                Defaults to the real ``SettingsService``.
        """
        self._auth_ctrl = auth_ctrl or AuthController()
        self._service = service or SettingsService()

    @property
    def _current_role(self) -> Optional[str]:
        """Return the current user's role for ``@require_role`` checks."""
        return self._auth_ctrl.current_role

    # ── Appearance ─────────────────────────────────────────────

    @require_role(Role.ADMIN)
    def get_theme(self) -> str:
        """Return the currently selected theme name.

        Returns:
            Theme name (e.g. 'flatly' or 'darkly').
        """
        return self._service.get_theme()

    @require_role(Role.ADMIN)
    def set_theme(self, theme_name: str) -> Tuple[bool, str]:
        """Persist the selected theme.

        Args:
            theme_name: One of ``SettingsController.THEMES``.

        Returns:
            Tuple of (success, message).
        """
        return self._service.set_theme(theme_name)

    # ── Hospital holidays ──────────────────────────────────────

    @require_role(Role.ADMIN)
    def list_holidays(self) -> List[Dict[str, Any]]:
        """Return all configured holidays, sorted by date.

        Returns:
            List of dicts with holiday_id, holiday_date, description.
        """
        return self._service.list_holidays()

    @require_role(Role.ADMIN)
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
        return self._service.add_holiday(holiday_date, description)

    @require_role(Role.ADMIN)
    def remove_holiday(self, holiday_id: int) -> Tuple[bool, str]:
        """Remove a hospital holiday.

        Args:
            holiday_id: The holiday record's ID.

        Returns:
            Tuple of (success, message).
        """
        return self._service.remove_holiday(holiday_id)

    # ── Security (read-only) ───────────────────────────────────

    @require_role(Role.ADMIN)
    def get_lockout_config(self) -> Dict[str, Any]:
        """Return the current account-lockout settings (read-only).

        Returns:
            Dict with max_login_attempts, lockout_duration_minutes,
            and read_only flag.
        """
        return self._service.get_lockout_config()
