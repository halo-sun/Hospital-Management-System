"""Unit tests for AuthController.

Tests cover input validation, login/logout flow, password management,
role checking, and Remember-Me integration.

All service-layer dependencies are mocked.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from unittest.mock import MagicMock, patch

import pytest

from src.controllers.auth_controller import AuthController
from src.constants import AuditAction
from tests.conftest import make_user_dict


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def mock_auth_service() -> MagicMock:
    """Create a mocked AuthService with sensible defaults."""
    service = MagicMock()
    service.current_user = make_user_dict()
    service.is_logged_in = True
    service.current_role = "Admin"
    service.current_user_id = 1
    service.current_username = "admin"
    service.is_admin.return_value = True
    service.is_doctor.return_value = False
    service.is_receptionist.return_value = False
    service.has_role.return_value = True
    service.remember_me_exists = False
    service.login.return_value = (True, "Login successful", make_user_dict())
    service.restore_session.return_value = make_user_dict()
    service.logout.return_value = True
    service.is_session_expired.return_value = False
    service.change_password.return_value = (True, "Password changed successfully.")
    service.reset_password.return_value = (True, "Password reset successfully.")
    service.get_all_users.return_value = [make_user_dict()]
    service.get_user_by_id.return_value = make_user_dict()
    service.create_user.return_value = (True, "User created successfully.", 99)
    return service


@pytest.fixture
def mock_audit_service() -> MagicMock:
    """Create a mocked AuditService with no side effects."""
    service = MagicMock()
    service.log.return_value = None
    service.log_login.return_value = None
    service.log_logout.return_value = None
    service.log_create.return_value = None
    return service


@pytest.fixture
def controller(mock_auth_service: MagicMock, mock_audit_service: MagicMock) -> AuthController:
    """Create an AuthController with mocked dependencies."""
    ctrl = AuthController()
    ctrl._auth_service = mock_auth_service
    ctrl._audit_service = mock_audit_service
    return ctrl


# ======================================================================
# Input Validation
# ======================================================================

class TestValidateLogin:
    """Tests for the static validate_login method."""

    def test_valid_input(self) -> None:
        """Valid username and password pass validation."""
        valid, msg = AuthController.validate_login("admin", "secret123")
        assert valid is True
        assert msg == ""

    def test_empty_username(self) -> None:
        """Empty username fails validation."""
        valid, msg = AuthController.validate_login("", "secret123")
        assert valid is False
        assert "Username" in msg

    def test_whitespace_username(self) -> None:
        """Whitespace-only username fails validation."""
        valid, msg = AuthController.validate_login("   ", "secret123")
        assert valid is False
        assert "Username" in msg

    def test_empty_password(self) -> None:
        """Empty password fails validation."""
        valid, msg = AuthController.validate_login("admin", "")
        assert valid is False
        assert "Password" in msg

    def test_short_username(self) -> None:
        """Username shorter than 3 characters fails."""
        valid, msg = AuthController.validate_login("ab", "secret123")
        assert valid is False
        assert "at least 3" in msg or "characters" in msg.lower()


class TestValidatePasswordChange:
    """Tests for the static validate_password_change method."""

    def test_valid_input(self) -> None:
        """Matching passwords with sufficient length pass."""
        valid, msg = AuthController.validate_password_change(
            "old_pass", "new_pass_123", "new_pass_123"
        )
        assert valid is True
        assert msg == ""

    def test_empty_current(self) -> None:
        """Empty current password fails."""
        valid, msg = AuthController.validate_password_change("", "new12345", "new12345")
        assert valid is False
        assert "Current password" in msg

    def test_empty_new(self) -> None:
        """Empty new password fails."""
        valid, msg = AuthController.validate_password_change("old12345", "", "")
        assert valid is False
        assert "New password" in msg

    def test_mismatched_passwords(self) -> None:
        """Mismatched confirmation fails."""
        valid, msg = AuthController.validate_password_change(
            "old12345", "new12345", "different"
        )
        assert valid is False
        assert "do not match" in msg

    def test_too_short(self) -> None:
        """Password shorter than 8 characters fails."""
        valid, msg = AuthController.validate_password_change(
            "old12345", "short", "short"
        )
        assert valid is False
        assert "at least 8" in msg


# ======================================================================
# Login
# ======================================================================

class TestLogin:
    """Tests for the login method."""

    def test_successful_login(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """A valid login returns success with user data."""
        mock_auth_service.login.return_value = (True, "Login successful", make_user_dict())

        success, msg, user = controller.login("admin", "password", remember_me=False)

        assert success is True
        assert msg == "Login successful"
        assert user is not None
        mock_auth_service.login.assert_called_once_with(
            "admin", "password", remember_me=False
        )

    def test_failed_login(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """A failed login returns failure without user data."""
        mock_auth_service.login.return_value = (False, "Invalid credentials", None)

        success, msg, user = controller.login("admin", "wrong", remember_me=False)

        assert success is False
        assert "Invalid" in msg
        assert user is None

    def test_login_with_remember_me(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """Remember Me=True is forwarded to AuthService."""
        controller.login("admin", "password", remember_me=True)
        mock_auth_service.login.assert_called_once_with(
            "admin", "password", remember_me=True
        )

    def test_login_invalid_input(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """Invalid input returns early without calling AuthService."""
        success, msg, user = controller.login("", "password", remember_me=False)

        assert success is False
        assert "Username" in msg
        assert user is None
        mock_auth_service.login.assert_not_called()

    def test_login_audit_on_success(self, controller: AuthController, mock_audit_service: MagicMock) -> None:
        """Successful login triggers log_login audit."""
        controller.login("admin", "password")
        mock_audit_service.log_login.assert_called_once_with(1, True)

    def test_login_audit_on_failure(self, controller: AuthController, mock_auth_service: MagicMock, mock_audit_service: MagicMock) -> None:
        """Failed login triggers LOGIN_FAILED audit."""
        mock_auth_service.login.return_value = (False, "Bad password", None)
        controller.login("admin", "wrong")
        mock_audit_service.log.assert_called_once_with(
            AuditAction.LOGIN_FAILED,
            target_entity="User",
            target_id="admin",
        )


# ======================================================================
# Remember Me / Session Restore
# ======================================================================

class TestRememberMe:
    """Tests for Remember-Me and session restore."""

    def test_remember_me_exists(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """remember_me_exists delegates to AuthService."""
        mock_auth_service.remember_me_exists = True
        assert controller.remember_me_exists is True

    def test_restore_session(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """restore_session returns user dict from AuthService."""
        user = controller.restore_session()
        assert user is not None
        assert user["username"] == "admin"
        mock_auth_service.restore_session.assert_called_once()

    def test_restore_session_returns_none(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """restore_session returns None when no token exists."""
        mock_auth_service.restore_session.return_value = None
        result = controller.restore_session()
        assert result is None


# ======================================================================
# Logout
# ======================================================================

class TestLogout:
    """Tests for the logout method."""

    def test_logout_succeeds(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """Logout clears the session."""
        result = controller.logout()
        assert result is True
        mock_auth_service.logout.assert_called_once()

    def test_logout_triggers_audit(self, controller: AuthController, mock_audit_service: MagicMock) -> None:
        """Logout records an audit entry."""
        controller.logout()
        mock_audit_service.log_logout.assert_called_once_with(1)


# ======================================================================
# Password Management
# ======================================================================

class TestPasswordManagement:
    """Tests for change_password and reset_password."""

    def test_change_password_success(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """Changing password with valid inputs succeeds."""
        mock_auth_service.change_password.return_value = (True, "Password changed.")

        success, msg = controller.change_password("old", "new_long_pass", "new_long_pass")

        assert success is True
        mock_auth_service.change_password.assert_called_once_with(1, "old", "new_long_pass")

    def test_change_password_fails_validation(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """Short new password fails before calling AuthService."""
        success, msg = controller.change_password("old", "short", "short")
        assert success is False
        assert "at least 8" in msg
        mock_auth_service.change_password.assert_not_called()

    def test_change_password_no_user(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """Change password fails when no user is logged in."""
        mock_auth_service.current_user_id = None
        success, msg = controller.change_password("old", "new_long_pass", "new_long_pass")
        assert success is False
        assert "No user logged in" in msg

    def test_change_password_audit_on_success(self, controller: AuthController, mock_auth_service: MagicMock, mock_audit_service: MagicMock) -> None:
        """Successful password change triggers audit."""
        controller.change_password("old", "new_long_pass", "new_long_pass")
        mock_audit_service.log.assert_called_once_with(
            AuditAction.PASSWORD_CHANGE,
            user_id=1,
            target_entity="User",
            target_id="1",
        )

    def test_reset_password_success(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """Admin can reset another user's password."""
        success, msg = controller.reset_password(2, "new_long_pass")
        assert success is True
        mock_auth_service.reset_password.assert_called_once_with(
            2, "new_long_pass", admin_id=1
        )

    def test_reset_password_not_admin(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """Non-admin users cannot reset passwords."""
        mock_auth_service.is_admin.return_value = False
        success, msg = controller.reset_password(2, "new_long_pass")
        assert success is False
        assert "administrators" in msg.lower()
        mock_auth_service.reset_password.assert_not_called()

    def test_reset_password_too_short(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """Short password fails validation before calling AuthService."""
        success, msg = controller.reset_password(2, "short")
        assert success is False
        assert "at least 8" in msg
        mock_auth_service.reset_password.assert_not_called()

    def test_reset_password_audit_on_success(self, controller: AuthController, mock_auth_service: MagicMock, mock_audit_service: MagicMock) -> None:
        """Successful password reset triggers audit."""
        controller.reset_password(2, "new_long_pass")
        mock_audit_service.log.assert_called_once_with(
            AuditAction.PASSWORD_RESET,
            user_id=1,
            target_entity="User",
            target_id="2",
        )


# ======================================================================
# Role Checking
# ======================================================================

class TestRoleChecking:
    """Tests for role-checking methods."""

    def test_is_admin(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """is_admin delegates correctly."""
        mock_auth_service.is_admin.return_value = True
        assert controller.is_admin() is True
        mock_auth_service.is_admin.return_value = False
        assert controller.is_admin() is False

    def test_is_doctor(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """is_doctor delegates correctly."""
        mock_auth_service.is_doctor.return_value = True
        assert controller.is_doctor() is True

    def test_is_receptionist(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """is_receptionist delegates correctly."""
        mock_auth_service.is_receptionist.return_value = True
        assert controller.is_receptionist() is True

    def test_has_role(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """has_role delegates correctly."""
        controller.has_role("Admin", "Doctor")
        mock_auth_service.has_role.assert_called_once_with("Admin", "Doctor")

    def test_session_expired(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """is_session_expired delegates correctly."""
        mock_auth_service.is_session_expired.return_value = True
        assert controller.is_session_expired() is True


# ======================================================================
# User Management
# ======================================================================

class TestUserManagement:
    """Tests for admin user management methods."""

    def test_get_all_users(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """get_all_users returns user list from AuthService."""
        users = controller.get_all_users()
        assert len(users) == 1
        mock_auth_service.get_all_users.assert_called_once()

    def test_get_user_by_id(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """get_user returns a single user."""
        user = controller.get_user(1)
        assert user is not None
        mock_auth_service.get_user_by_id.assert_called_once_with(1)

    def test_create_user_admin(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """Admin can create users."""
        data = {"username": "new_user", "password": "secret123"}
        success, msg, user_id = controller.create_user(data)
        assert success is True
        assert user_id == 99
        mock_auth_service.create_user.assert_called_once_with(data)

    def test_create_user_not_admin(self, controller: AuthController, mock_auth_service: MagicMock) -> None:
        """Non-admin gets rejected."""
        mock_auth_service.is_admin.return_value = False
        data = {"username": "new_user", "password": "secret123"}
        success, msg, user_id = controller.create_user(data)
        assert success is False
        assert "administrators" in msg.lower()
        assert user_id is None
        mock_auth_service.create_user.assert_not_called()

    def test_create_user_audit(self, controller: AuthController, mock_auth_service: MagicMock, mock_audit_service: MagicMock) -> None:
        """Successful user creation triggers audit."""
        data = {"username": "new_user", "password": "secret123", "full_name": "New User"}
        controller.create_user(data)
        mock_audit_service.log_create.assert_called_once()
