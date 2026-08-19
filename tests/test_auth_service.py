"""Unit tests for AuthService.

These tests verify the authentication, session management, password
operations, role checking, and Remember-Me functionality.

All database and file-system dependencies are mocked.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.services.auth_service import AuthService
from src.auth.exceptions import (
    AccountInactiveError,
    AccountLockedError,
    AuthenticationError,
)
from tests.conftest import make_user_dict


# ======================================================================
# Login
# ======================================================================

class TestLogin:
    """Tests for the ``login`` method."""

    def test_successful_login(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """A valid username and password returns the user dict."""
        user = make_user_dict()
        mock_user_repo.find_by_username.return_value = user
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)

        success, msg, result = service.login("admin", "password")

        assert success is True
        assert msg == "Login successful"
        assert result is not None
        assert result["username"] == "admin"
        assert service.is_logged_in is True
        assert service.current_user_id == 1
        assert service.current_role == "Admin"

    def test_login_invalid_username(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """An unknown username returns a generic error."""
        mock_user_repo.find_by_username.return_value = None
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)

        success, msg, result = service.login("nobody", "password")

        assert success is False
        assert "Invalid" in msg
        assert result is None

    def test_login_inactive_account(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """An inactive account raises AccountInactiveError."""
        user = make_user_dict(status="Inactive")
        mock_user_repo.find_by_username.return_value = user
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)

        with pytest.raises(AccountInactiveError):
            service.login("inactive_user", "password")

    def test_login_locked_account(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """A locked account (locked_until in the future) raises AccountLockedError."""
        locked_until = datetime.now() + timedelta(minutes=15)
        user = make_user_dict()
        user["locked_until"] = locked_until
        mock_user_repo.find_by_username.return_value = user
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)

        with pytest.raises(AccountLockedError) as exc:
            service.login("locked_user", "password")
        assert exc.value.remaining_minutes > 0

    def test_login_wrong_password(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """An incorrect password returns a failure message and increments attempts."""
        user = make_user_dict()
        mock_user_repo.find_by_username.return_value = user
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)

        success, msg, result = service.login("admin", "wrongpassword")

        assert success is False
        assert "Invalid credentials" in msg
        assert result is None

    def test_login_too_many_failures(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """After max_login_attempts failures the account is locked."""
        user = make_user_dict()
        user["failed_login_attempts"] = 4  # One more fails
        mock_user_repo.find_by_username.return_value = user
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)

        success, msg, result = service.login("admin", "wrongpassword")

        assert success is False
        assert "locked" in msg.lower()
        assert result is None
        mock_user_repo.set_locked.assert_called_once()

    def test_login_with_remember_me(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """Remember Me=True saves a token after successful login."""
        user = make_user_dict()
        mock_user_repo.find_by_username.return_value = user
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)

        service.login("admin", "password", remember_me=True)

        mock_token_manager.save.assert_called_once_with("admin")

    def test_login_without_remember_me(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """Remember Me=False does NOT save a token."""
        user = make_user_dict()
        mock_user_repo.find_by_username.return_value = user
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)

        service.login("admin", "password", remember_me=False)

        mock_token_manager.save.assert_not_called()


# ======================================================================
# Remember Me / Session Restore
# ======================================================================

class TestRestoreSession:
    """Tests for the ``restore_session`` method."""

    def test_restore_valid_token(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """A valid token restores the session without prompting for password."""
        user = make_user_dict()
        mock_token_manager.load.return_value = "admin"
        mock_user_repo.find_by_username.return_value = user
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)

        result = service.restore_session()

        assert result is not None
        assert result["username"] == "admin"
        assert service.is_logged_in is True

    def test_restore_no_token(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """No token on disk returns None (normal login screen flow)."""
        mock_token_manager.load.return_value = None
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)

        result = service.restore_session()

        assert result is None
        assert service.is_logged_in is False

    def test_restore_expired_token_deleted_user(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """A token for a deleted/inactive user clears the token and returns None."""
        mock_token_manager.load.return_value = "deleted_user"
        mock_user_repo.find_by_username.return_value = None
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)

        result = service.restore_session()

        assert result is None
        mock_token_manager.clear.assert_called_once()


# ======================================================================
# Logout
# ======================================================================

class TestLogout:
    """Tests for the ``logout`` method."""

    def test_logout_logged_in(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """Logging out clears the session and the token file."""
        user = make_user_dict()
        mock_user_repo.find_by_username.return_value = user
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)
        service.login("admin", "password")
        assert service.is_logged_in is True

        result = service.logout()

        assert result is True
        assert service.is_logged_in is False
        assert service.current_user is None
        mock_token_manager.clear.assert_called_once()

    def test_logout_not_logged_in(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """Logging out when not logged in returns False."""
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)
        result = service.logout()
        assert result is False


# ======================================================================
# Session Management
# ======================================================================

class TestSessionManagement:
    """Tests for session expiry and status checks."""

    def test_session_not_expired_after_login(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """A freshly started session is not expired."""
        user = make_user_dict()
        mock_user_repo.find_by_username.return_value = user
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)
        service.login("admin", "password")

        assert service.is_session_expired() is False

    def test_session_not_expired_no_session(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """Without a session, is_session_expired returns False (not True)."""
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)
        assert service.is_session_expired() is False

    def test_session_elapsed_minutes(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """session_elapsed_minutes returns a positive value after login."""
        user = make_user_dict()
        mock_user_repo.find_by_username.return_value = user
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)
        service.login("admin", "password")

        elapsed = service.session_elapsed_minutes
        assert elapsed > 0

    def test_session_elapsed_no_session(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """Without a session, elapsed minutes is 0."""
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)
        assert service.session_elapsed_minutes == 0.0


# ======================================================================
# Password Management
# ======================================================================

class TestPasswordManagement:
    """Tests for password change and reset."""

    def test_change_password_success(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """Changing password with correct current password succeeds."""
        user = make_user_dict()
        mock_user_repo.find_by_id_with_role.return_value = user
        mock_user_repo.find_by_username.return_value = user
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)
        service.login("admin", "password")

        success, msg = service.change_password(1, "password", "newpassword123")

        assert success is True
        mock_user_repo.reset_password.assert_called_once()

    def test_change_password_wrong_current(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """Changing password with wrong current password fails."""
        user = make_user_dict()
        mock_user_repo.find_by_id_with_role.return_value = user
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)

        success, msg = service.change_password(1, "wrong", "newpassword123")

        assert success is False
        assert "incorrect" in msg.lower()

    def test_reset_password_too_short(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """Resetting to a password shorter than minimum length fails."""
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)
        success, msg = service.reset_password(1, "short")
        assert success is False
        assert "characters" in msg.lower()

    def test_reset_password_success(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """A valid password reset succeeds."""
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)
        success, msg = service.reset_password(1, "validpassword123")
        assert success is True
        mock_user_repo.reset_password.assert_called_once()


# ======================================================================
# Role Checking
# ======================================================================

class TestRoleChecking:
    """Tests for role-based access control methods."""

    def test_has_role_admin(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """is_admin returns True for an admin user."""
        user = make_user_dict(role_name="Admin")
        mock_user_repo.find_by_username.return_value = user
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)
        service.login("admin", "password")

        assert service.is_admin() is True
        assert service.is_doctor() is False
        assert service.is_receptionist() is False
        assert service.has_role("Admin") is True
        assert service.has_role("Admin", "Doctor") is True

    def test_has_role_doctor(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """Role checks return correctly for a doctor."""
        user = make_user_dict(role_name="Doctor")
        mock_user_repo.find_by_username.return_value = user
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)
        service.login("dr.sharma", "password")

        assert service.is_admin() is False
        assert service.is_doctor() is True
        assert service.is_receptionist() is False

    def test_has_role_not_logged_in(self, mock_user_repo: MagicMock, mock_token_manager: MagicMock) -> None:
        """All role checks return False when no user is logged in."""
        service = AuthService(user_repo=mock_user_repo, token_manager=mock_token_manager)
        assert service.is_admin() is False
        assert service.is_doctor() is False
        assert service.has_role("Admin") is False


# ======================================================================
# RememberTokenManager (integration-style)
# ======================================================================

class TestRealRememberTokenManager:
    """Tests against a REAL RememberTokenManager writing to a temp dir."""

    def test_save_and_load(self, real_token_manager) -> None:
        """Saving a token then loading it returns the username."""
        real_token_manager.save("admin")
        result = real_token_manager.load()
        assert result == "admin"

    def test_load_no_file(self, real_token_manager) -> None:
        """Loading when no file exists returns None."""
        result = real_token_manager.load()
        assert result is None

    def test_clear_removes_file(self, real_token_manager) -> None:
        """Clearing removes the token file."""
        real_token_manager.save("admin")
        assert real_token_manager.exists is True
        real_token_manager.clear()
        assert real_token_manager.exists is False
        assert real_token_manager.load() is None

    def test_exists_property(self, real_token_manager) -> None:
        """exists reflects the presence of a saved token."""
        assert real_token_manager.exists is False
        real_token_manager.save("admin")
        assert real_token_manager.exists is True
