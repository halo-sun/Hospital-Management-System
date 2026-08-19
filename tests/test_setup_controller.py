"""Unit tests for the SetupController (first-run admin setup).

Covers the startup admin check, server-side per-field validation, and
admin creation that reuses the normal user-creation flow with an audit
entry.  All repository/service dependencies are mocked so the tests
run without a MySQL server or bcrypt.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.controllers.setup_controller import (
    SetupController,
    WEAK_PASSWORDS,
)
from src.constants import Role, UserStatus

VALID_PASSWORD = "Str0ng!Pass2026"


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def mock_user_repo() -> MagicMock:
    """Create a mocked UserRepository with safe defaults."""
    repo = MagicMock()
    repo.count_by_role.return_value = 0
    repo.find_by_username.return_value = None
    repo.get_role_id.return_value = 1
    return repo


@pytest.fixture
def mock_auth_service() -> MagicMock:
    """Create a mocked AuthService with a successful create_user."""
    service = MagicMock()
    service.create_user.return_value = (True, "User created successfully.", 99)
    return service


@pytest.fixture
def mock_audit_service() -> MagicMock:
    """Create a mocked AuditService with no side effects."""
    service = MagicMock()
    service.log_create.return_value = None
    return service


@pytest.fixture
def controller(
    mock_user_repo: MagicMock,
    mock_auth_service: MagicMock,
    mock_audit_service: MagicMock,
) -> SetupController:
    """Create a SetupController with mocked dependencies."""
    return SetupController(
        user_repo=mock_user_repo,
        auth_service=mock_auth_service,
        audit_service=mock_audit_service,
    )


# ── Startup check ─────────────────────────────────────────────


class TestHasAdmin:
    """Tests for the launch-time admin existence check."""

    def test_no_admin_returns_false(
        self, controller: SetupController, mock_user_repo: MagicMock,
    ) -> None:
        """A fresh DB with zero users reports no admin."""
        mock_user_repo.count_by_role.return_value = 0
        assert controller.has_admin() is False

    def test_admin_exists_returns_true(
        self, controller: SetupController, mock_user_repo: MagicMock,
    ) -> None:
        """An existing admin user reports True."""
        mock_user_repo.count_by_role.return_value = 3
        assert controller.has_admin() is True

    def test_queries_admin_role(
        self, controller: SetupController, mock_user_repo: MagicMock,
    ) -> None:
        """The check counts users with the Admin role specifically."""
        controller.has_admin()
        mock_user_repo.count_by_role.assert_called_once_with(Role.ADMIN)


# ── Username validation ───────────────────────────────────────


class TestValidateUsername:
    """Tests for username validation rules."""

    def test_required(self, controller: SetupController) -> None:
        errors = controller.validate("", VALID_PASSWORD, VALID_PASSWORD)
        assert "required" in errors["username"].lower()

    def test_too_short(self, controller: SetupController) -> None:
        errors = controller.validate("ab", VALID_PASSWORD, VALID_PASSWORD)
        assert "at least 3" in errors["username"]

    def test_whitespace_rejected(self, controller: SetupController) -> None:
        errors = controller.validate("admin user", VALID_PASSWORD, VALID_PASSWORD)
        assert "spaces" in errors["username"].lower()

    def test_taken_rejected(
        self, controller: SetupController, mock_user_repo: MagicMock,
    ) -> None:
        """An existing username is reported as taken."""
        mock_user_repo.find_by_username.return_value = {"user_id": 1, "username": "admin"}
        errors = controller.validate("admin", VALID_PASSWORD, VALID_PASSWORD)
        assert "taken" in errors["username"].lower()

    def test_surrounding_whitespace_stripped(self, controller: SetupController) -> None:
        """Outer whitespace is stripped before validation."""
        errors = controller.validate("  admin  ", VALID_PASSWORD, VALID_PASSWORD)
        assert "username" not in errors


# ── Password validation ───────────────────────────────────────


class TestValidatePassword:
    """Tests for password strength validation rules."""

    def test_required(self, controller: SetupController) -> None:
        errors = controller.validate("admin", "", "")
        assert "required" in errors["password"].lower()

    def test_min_length(self, controller: SetupController) -> None:
        errors = controller.validate("admin", "Str0ng!1", "Str0ng!1")
        assert "at least 10" in errors["password"]

    def test_requires_uppercase(self, controller: SetupController) -> None:
        errors = controller.validate("admin", "str0ng!pass2026", "str0ng!pass2026")
        assert "uppercase" in errors["password"]

    def test_requires_lowercase(self, controller: SetupController) -> None:
        errors = controller.validate("admin", "STR0NG!PASS2026", "STR0NG!PASS2026")
        assert "lowercase" in errors["password"]

    def test_requires_digit(self, controller: SetupController) -> None:
        errors = controller.validate("admin", "Strong!Password", "Strong!Password")
        assert "number" in errors["password"]

    def test_requires_symbol(self, controller: SetupController) -> None:
        errors = controller.validate("admin", "StrongPass2026", "StrongPass2026")
        assert "symbol" in errors["password"]

    def test_denylisted_rejected(self, controller: SetupController) -> None:
        """The exact credential we are trying to stop is rejected."""
        errors = controller.validate("admin", "admin123", "admin123")
        assert "too common" in errors["password"]

    def test_multiple_rules_accumulated(self, controller: SetupController) -> None:
        """All failing rules are reported together, not just the first."""
        errors = controller.validate("admin", "weak", "weak")
        msg = errors["password"]
        assert "at least 10" in msg
        assert "number" in msg
        assert "symbol" in msg

    def test_valid_password_passes(self, controller: SetupController) -> None:
        errors = controller.validate("admin", VALID_PASSWORD, VALID_PASSWORD)
        assert "password" not in errors

    def test_denylist_covers_specified_values(self) -> None:
        """The denylist contains the weak passwords named in the spec."""
        assert "admin123" in WEAK_PASSWORDS
        assert "password123" in WEAK_PASSWORDS
        assert "12345678" in WEAK_PASSWORDS


# ── Confirm password validation ───────────────────────────────


class TestValidateConfirm:
    """Tests for the password confirmation rule."""

    def test_mismatch(self, controller: SetupController) -> None:
        errors = controller.validate(
            "admin", VALID_PASSWORD, VALID_PASSWORD + "x",
        )
        assert "do not match" in errors["confirm"].lower()

    def test_empty_both_no_mismatch(self, controller: SetupController) -> None:
        """Two empty passwords match — only the required error remains."""
        errors = controller.validate("admin", "", "")
        assert "confirm" not in errors


# ── Admin creation ────────────────────────────────────────────


class TestCreateAdmin:
    """Tests for create_admin round-tripping through auth_service."""

    def test_field_errors_short_circuit(
        self, controller: SetupController, mock_auth_service: MagicMock,
    ) -> None:
        """Invalid input never reaches the creation path."""
        success, message, errors = controller.create_admin("ab", "weak", "weak")
        assert success is False
        assert errors
        mock_auth_service.create_user.assert_not_called()

    def test_role_not_found(
        self, controller: SetupController, mock_user_repo: MagicMock,
    ) -> None:
        """A missing Admin role is a general (non-field) failure."""
        mock_user_repo.get_role_id.return_value = None
        success, message, errors = controller.create_admin(
            "admin", VALID_PASSWORD, VALID_PASSWORD,
        )
        assert success is False
        assert not errors
        assert "role" in message.lower()

    def test_success_reuses_auth_service(
        self,
        controller: SetupController,
        mock_auth_service: MagicMock,
        mock_audit_service: MagicMock,
    ) -> None:
        """A valid submission creates the admin via AuthService + audit."""
        success, message, errors = controller.create_admin(
            "admin", VALID_PASSWORD, VALID_PASSWORD,
        )
        assert success is True
        assert not errors

        user_data = mock_auth_service.create_user.call_args.args[0]
        assert user_data["username"] == "admin"
        assert user_data["role_id"] == 1
        assert user_data["status"] == UserStatus.ACTIVE
        assert user_data["password"] == VALID_PASSWORD  # plaintext → service hashes it

        # Audit entry for the account-creation event
        log_args = mock_audit_service.log_create.call_args.args
        assert log_args[0] == 99          # new user's ID
        assert log_args[1] == "User"
        assert log_args[3]["role"] == Role.ADMIN

    def test_service_reports_duplicate(
        self,
        controller: SetupController,
        mock_user_repo: MagicMock,
        mock_auth_service: MagicMock,
    ) -> None:
        """A duplicate surfaced by the service maps to the username field."""
        mock_user_repo.find_by_username.return_value = None
        mock_auth_service.create_user.return_value = (
            False, "Username already exists.", None,
        )
        success, message, errors = controller.create_admin(
            "admin", VALID_PASSWORD, VALID_PASSWORD,
        )
        assert success is False
        assert "username" in errors
