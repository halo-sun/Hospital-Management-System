"""Unit tests for the SettingsController (service-backed).

The controller is a thin RBAC-gated façade over SettingsService:
these tests verify the admin-only gate and delegation.  Service-level
behaviour (persistence, duplicates) lives in ``test_settings_service.py``.
"""
from __future__ import annotations

from datetime import date
from typing import Optional
from unittest.mock import MagicMock

import pytest

from src.auth.exceptions import PermissionDeniedError
from src.controllers.settings_controller import SettingsController
from src.constants import Role


# ── Fixtures ──────────────────────────────────────────────────


class FakeAuth:
    """Minimal stand-in for AuthController exposing current_role."""

    def __init__(self, role: Optional[str] = None) -> None:
        self.current_role = role


@pytest.fixture
def admin_controller() -> SettingsController:
    """A SettingsController with an admin session and mocked service."""
    return SettingsController(
        auth_ctrl=FakeAuth(Role.ADMIN), service=MagicMock(),
    )


@pytest.fixture
def mock_service(admin_controller: SettingsController) -> MagicMock:
    """Access the mocked SettingsService."""
    return admin_controller._service


# ── RBAC gate ─────────────────────────────────────────────────


class TestRbacGate:
    """All settings operations must be admin-only."""

    def test_receptionist_denied(self) -> None:
        """A receptionist gets PermissionDeniedError on every method."""
        ctrl = SettingsController(auth_ctrl=FakeAuth(Role.RECEPTIONIST))
        with pytest.raises(PermissionDeniedError):
            ctrl.get_theme()
        with pytest.raises(PermissionDeniedError):
            ctrl.set_theme("darkly")
        with pytest.raises(PermissionDeniedError):
            ctrl.list_holidays()
        with pytest.raises(PermissionDeniedError):
            ctrl.add_holiday(date(2026, 12, 25), "Christmas")
        with pytest.raises(PermissionDeniedError):
            ctrl.remove_holiday(1)
        with pytest.raises(PermissionDeniedError):
            ctrl.get_lockout_config()

    def test_no_session_denied(self) -> None:
        """No logged-in user gets PermissionDeniedError."""
        ctrl = SettingsController(auth_ctrl=FakeAuth(None))
        with pytest.raises(PermissionDeniedError):
            ctrl.list_holidays()


# ── Delegation ────────────────────────────────────────────────


class TestDelegation:
    """Every method forwards to the SettingsService."""

    def test_get_theme_delegates(self, admin_controller: SettingsController,
                                 mock_service: MagicMock) -> None:
        """get_theme returns the service value."""
        mock_service.get_theme.return_value = "darkly"
        assert admin_controller.get_theme() == "darkly"
        mock_service.get_theme.assert_called_once()

    def test_set_theme_delegates(self, admin_controller: SettingsController,
                                 mock_service: MagicMock) -> None:
        """set_theme forwards the name and the tuple."""
        mock_service.set_theme.return_value = (True, "Theme switched to 'darkly'.")
        assert admin_controller.set_theme("darkly") == (True, "Theme switched to 'darkly'.")
        mock_service.set_theme.assert_called_once_with("darkly")

    def test_list_holidays_delegates(self, admin_controller: SettingsController,
                                     mock_service: MagicMock) -> None:
        """list_holidays returns the service rows."""
        rows = [{"holiday_id": 1, "holiday_date": date(2026, 1, 1), "description": "New Year"}]
        mock_service.list_holidays.return_value = rows
        assert admin_controller.list_holidays() == rows

    def test_add_holiday_delegates(self, admin_controller: SettingsController,
                                   mock_service: MagicMock) -> None:
        """add_holiday forwards date/description and the tuple."""
        mock_service.add_holiday.return_value = (True, "Holiday added for 2026-12-25.", 3)
        result = admin_controller.add_holiday(date(2026, 12, 25), "Christmas")
        assert result == (True, "Holiday added for 2026-12-25.", 3)
        mock_service.add_holiday.assert_called_once_with(
            date(2026, 12, 25), "Christmas",
        )

    def test_remove_holiday_delegates(self, admin_controller: SettingsController,
                                      mock_service: MagicMock) -> None:
        """remove_holiday forwards the id and the tuple."""
        mock_service.remove_holiday.return_value = (True, "Holiday removed.")
        assert admin_controller.remove_holiday(1) == (True, "Holiday removed.")
        mock_service.remove_holiday.assert_called_once_with(1)

    def test_lockout_config_delegates(self, admin_controller: SettingsController,
                                      mock_service: MagicMock) -> None:
        """get_lockout_config returns the service dict."""
        config = {"max_login_attempts": 5, "lockout_duration_minutes": 15, "read_only": True}
        mock_service.get_lockout_config.return_value = config
        assert admin_controller.get_lockout_config() == config
