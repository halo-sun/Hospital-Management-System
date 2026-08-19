"""Unit tests for the StaffController.

Tests validate correct delegation to StaffService and input validation
for receptionist/staff management operations.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from typing import Any, Dict

import pytest

from src.controllers.staff_controller import StaffController
from src.constants import Role
from src.auth.exceptions import PermissionDeniedError


# ── RBAC gate ─────────────────────────────────────────────────


class TestRbacGate:
    """Staff management must be admin-only."""

    def test_no_session_denied(self, mock_auth_ctrl: MagicMock) -> None:
        """No logged-in user is denied."""
        mock_auth_ctrl.current_role = None
        ctrl = StaffController(auth_ctrl=mock_auth_ctrl)
        with pytest.raises(PermissionDeniedError):
            ctrl.get_all_staff()

    def test_receptionist_denied(self, mock_auth_ctrl: MagicMock) -> None:
        """A receptionist is denied staff management."""
        mock_auth_ctrl.current_role = Role.RECEPTIONIST
        ctrl = StaffController(auth_ctrl=mock_auth_ctrl)
        with pytest.raises(PermissionDeniedError):
            ctrl.create_staff({"username": "x"})


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def mock_auth_ctrl() -> MagicMock:
    """Create a mocked AuthController with an Admin session."""
    auth = MagicMock()
    auth.current_role = "Admin"
    return auth


@pytest.fixture
def controller(mock_auth_ctrl: MagicMock) -> StaffController:
    """Create a StaffController with mocked dependencies."""
    with (
        patch("src.controllers.staff_controller.StaffService") as svc_cls,
        patch("src.controllers.staff_controller.AuditService") as aud_cls,
    ):
        svc_cls.return_value = MagicMock()
        aud_cls.return_value = MagicMock()
        yield StaffController(auth_ctrl=mock_auth_ctrl)


@pytest.fixture
def mock_staff_service(controller: StaffController) -> MagicMock:
    """Access the mocked StaffService from the controller."""
    return controller._staff_service


# ── Factory helpers ───────────────────────────────────────────


def make_staff(**overrides: Any) -> Dict[str, Any]:
    """Create a staff user dict with sensible defaults."""
    data: Dict[str, Any] = {
        "user_id": 1,
        "username": "jane.reception",
        "full_name": "Jane Doe",
        "email": "jane@hospital.com",
        "role_name": "Receptionist",
        "status": "Active",
        "last_login": None,
    }
    data.update(overrides)
    return data


# ── Validation tests ──────────────────────────────────────────


class TestValidateStaffData:
    """Tests for the validate_staff_data static method."""

    def test_valid_new_user(self) -> None:
        """Valid new staff data passes validation."""
        data = {"username": "jane", "password": "password123", "email": "jane@hospital.com"}
        valid, msg = StaffController.validate_staff_data(data, is_new=True)
        assert valid is True

    def test_missing_username(self) -> None:
        """Missing username should fail for new users."""
        data = {"password": "password123"}
        valid, msg = StaffController.validate_staff_data(data, is_new=True)
        assert valid is False
        assert "username" in msg.lower()

    def test_short_username(self) -> None:
        """Username under 3 chars should fail."""
        data = {"username": "ab", "password": "password123"}
        valid, msg = StaffController.validate_staff_data(data, is_new=True)
        assert valid is False
        assert "3" in msg

    def test_missing_password(self) -> None:
        """Missing password should fail for new users."""
        data = {"username": "jane"}
        valid, msg = StaffController.validate_staff_data(data, is_new=True)
        assert valid is False
        assert "password" in msg.lower()

    def test_short_password(self) -> None:
        """Password under 8 chars should fail."""
        data = {"username": "jane", "password": "1234567"}
        valid, msg = StaffController.validate_staff_data(data, is_new=True)
        assert valid is False
        assert "8" in msg

    def test_invalid_email(self) -> None:
        """Invalid email should fail."""
        data = {"username": "jane", "password": "password123", "email": "notanemail"}
        valid, msg = StaffController.validate_staff_data(data, is_new=True)
        assert valid is False
        assert "email" in msg.lower()

    def test_edit_mode_skip_password(self) -> None:
        """Edit mode should not require password."""
        data = {"username": "jane"}
        valid, msg = StaffController.validate_staff_data(data, is_new=False)
        assert valid is True


# ── Staff CRUD operations ─────────────────────────────────────


class TestStaffOperations:
    """Tests for staff CRUD via controller."""

    def test_get_all_staff(self, controller: StaffController, mock_staff_service: MagicMock) -> None:
        """get_all_staff delegates to service."""
        mock_staff_service.get_all_staff.return_value = [make_staff()]
        result = controller.get_all_staff()
        assert len(result) == 1

    def test_get_receptionists(self, controller: StaffController, mock_staff_service: MagicMock) -> None:
        """get_receptionists delegates to service."""
        mock_staff_service.get_receptionists.return_value = [make_staff()]
        result = controller.get_receptionists()
        assert len(result) == 1

    def test_get_staff_member(self, controller: StaffController, mock_staff_service: MagicMock) -> None:
        """get_staff_member delegates to service."""
        mock_staff_service.get_staff_member.return_value = make_staff()
        result = controller.get_staff_member(1)
        assert result is not None
        assert result["username"] == "jane.reception"

    def test_create_staff_valid(self, controller: StaffController, mock_staff_service: MagicMock) -> None:
        """Valid staff creation."""
        mock_staff_service.create_staff.return_value = (True, "Created.", 1)
        data = {"username": "newstaff", "password": "password123", "role_id": 3}
        result = controller.create_staff(data, audit_user_id=1)
        assert result[0] is True

    def test_create_staff_invalid(self, controller: StaffController) -> None:
        """Invalid data fails at controller level."""
        result = controller.create_staff({"username": ""}, audit_user_id=1)
        assert result[0] is False

    def test_update_staff(self, controller: StaffController, mock_staff_service: MagicMock) -> None:
        """update_staff delegates to service."""
        mock_staff_service.update_staff.return_value = (True, "Updated.")
        result = controller.update_staff(1, {"full_name": "Jane Updated"}, audit_user_id=1)
        assert result[0] is True

    def test_delete_staff(self, controller: StaffController, mock_staff_service: MagicMock) -> None:
        """delete_staff delegates to service."""
        mock_staff_service.delete_staff.return_value = (True, "Deleted.")
        result = controller.delete_staff(1, audit_user_id=1)
        assert result[0] is True

    def test_search_staff(self, controller: StaffController, mock_staff_service: MagicMock) -> None:
        """search_staff delegates to service."""
        mock_staff_service.search_staff.return_value = [make_staff()]
        result = controller.search_staff("jane")
        assert len(result) == 1

    def test_activate_staff(self, controller: StaffController, mock_staff_service: MagicMock) -> None:
        """activate_staff delegates to service."""
        mock_staff_service.activate_staff.return_value = (True, "Activated.")
        result = controller.activate_staff(1, audit_user_id=1)
        assert result[0] is True

    def test_deactivate_staff(self, controller: StaffController, mock_staff_service: MagicMock) -> None:
        """deactivate_staff delegates to service."""
        mock_staff_service.deactivate_staff.return_value = (True, "Deactivated.")
        result = controller.deactivate_staff(1, audit_user_id=1)
        assert result[0] is True
