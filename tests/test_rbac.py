"""Unit tests for the RBAC decorator and RoleRequired class.

Tests cover:
- ``RoleRequired.check()`` with valid/invalid/missing roles
- ``require_role`` decorator integration with simulated controller classes
- Error messages and exception propagation
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from unittest.mock import MagicMock

import pytest

from src.auth.exceptions import PermissionDeniedError
from src.auth.rbac import RoleRequired, require_role


# ======================================================================
# RoleRequired (non-decorator class)
# ======================================================================

class TestRoleRequired:
    """Tests for the RoleRequired descriptor-style class."""

    def test_allowed_roles_property(self) -> None:
        """allowed_roles returns the roles passed at construction."""
        req = RoleRequired("Admin", "Doctor")
        assert req.allowed_roles == ("Admin", "Doctor")

    def test_single_role(self) -> None:
        """Single role is stored correctly."""
        req = RoleRequired("Admin")
        assert req.allowed_roles == ("Admin",)

    def test_check_valid_role(self) -> None:
        """check() does not raise for an allowed role."""
        req = RoleRequired("Admin", "Doctor")
        req.check("Admin")  # Should not raise
        req.check("Doctor")  # Should not raise

    def test_check_invalid_role(self) -> None:
        """check() raises PermissionDeniedError for a disallowed role."""
        req = RoleRequired("Admin")
        with pytest.raises(PermissionDeniedError) as exc:
            req.check("Receptionist")
        assert "Admin" in str(exc.value)

    def test_check_no_role(self) -> None:
        """check() raises PermissionDeniedError when role is None."""
        req = RoleRequired("Admin")
        with pytest.raises(PermissionDeniedError) as exc:
            req.check(None)
        assert "requires" in str(exc.value).lower()


# ======================================================================
# require_role decorator
# ======================================================================

class TestRequireRoleDecorator:
    """Tests for the require_role decorator applied to class methods."""

    def test_allowed_role_via_current_role_property(self) -> None:
        """A method decorated with @require_role passes when the class has a matching _current_role."""
        class Controller:
            def __init__(self) -> None:
                self._current_role = "Admin"

            @require_role("Admin")
            def sensitive_op(self) -> str:
                return "Done"

        ctrl = Controller()
        result = ctrl.sensitive_op()
        assert result == "Done"

    def test_allowed_role_via_auth_service(self) -> None:
        """A method passes when _auth_service has a matching current_role."""
        class Controller:
            class FakeAuth:
                current_role = "Doctor"

            def __init__(self) -> None:
                self._auth_service = self.FakeAuth()

            @require_role("Doctor")
            def diagnose(self) -> str:
                return "Diagnosed"

        ctrl = Controller()
        result = ctrl.diagnose()
        assert result == "Diagnosed"

    def test_disallowed_role_raises(self) -> None:
        """A user with a non-matching role gets PermissionDeniedError."""
        class Controller:
            def __init__(self) -> None:
                self._current_role = "Receptionist"

            @require_role("Admin")
            def admin_op(self) -> str:
                return "Admin stuff"

        ctrl = Controller()
        with pytest.raises(PermissionDeniedError):
            ctrl.admin_op()

    def test_no_role_raises(self) -> None:
        """When no role is set, the decorator raises PermissionDeniedError."""
        class Controller:
            _current_role = None  # type: ignore[assignment]

            @require_role("Admin")
            def admin_op(self) -> str:
                return "Admin stuff"

        ctrl = Controller()
        with pytest.raises(PermissionDeniedError):
            ctrl.admin_op()

    def test_multiple_allowed_roles(self) -> None:
        """Multiple roles can be specified, any of which passes."""
        class Controller:
            def __init__(self) -> None:
                self._current_role = "Receptionist"

            @require_role("Admin", "Doctor", "Receptionist")
            def schedule_appt(self) -> str:
                return "Scheduled"

        ctrl = Controller()
        result = ctrl.schedule_appt()
        assert result == "Scheduled"

    def test_all_roles_blocked(self) -> None:
        """A role not in the allowed list gets denied."""
        class Controller:
            def __init__(self) -> None:
                self._current_role = "Guest"  # Not a real role

            @require_role("Admin")
            def do_thing(self) -> str:
                return "Thing"

        ctrl = Controller()
        with pytest.raises(PermissionDeniedError):
            ctrl.do_thing()

    def test_first_arg_as_user_dict_not_checked(self) -> None:
        """When _current_role is not available, the decorator does NOT trust the first positional arg.

        Only ``_current_role`` or ``_auth_service.current_role`` are
        trusted role sources.  A user dict passed as an argument is
        intentionally ignored to prevent role-injection attacks.
        """
        class Controller:
            # No _current_role or _auth_service

            @require_role("Admin")
            def delete_user(self, user: Dict[str, Any]) -> str:
                return "Deleted"

        ctrl = Controller()
        admin_user = {"role_name": "Admin"}
        # Without a valid role source, the decorator raises
        with pytest.raises(PermissionDeniedError):
            ctrl.delete_user(admin_user)

    def test_first_arg_as_user_dict_wrong_role(self) -> None:
        """When the first arg user dict has a disallowed role, raise.

        The decorator no longer reads role from positional args, so
        this case is identical to test_first_arg_as_user_dict_not_checked.
        """
        class Controller:
            @require_role("Admin")
            def delete_user(self, user: Dict[str, Any]) -> str:
                return "Deleted"

        ctrl = Controller()
        receptionist_user = {"role_name": "Receptionist"}
        with pytest.raises(PermissionDeniedError):
            ctrl.delete_user(receptionist_user)

    def test_method_return_value_preserved(self) -> None:
        """The decorator preserves the original method's return value."""
        class Controller:
            def __init__(self) -> None:
                self._current_role = "Admin"

            @require_role("Admin")
            def get_count(self) -> int:
                return 42

        ctrl = Controller()
        assert ctrl.get_count() == 42

    def test_method_args_preserved(self) -> None:
        """The decorator passes through positional and keyword arguments."""
        class Controller:
            def __init__(self) -> None:
                self._current_role = "Admin"

            @require_role("Admin")
            def greet(self, name: str, greeting: str = "Hello") -> str:
                return f"{greeting}, {name}!"

        ctrl = Controller()
        result = ctrl.greet("Alice", greeting="Hi")
        assert result == "Hi, Alice!"
