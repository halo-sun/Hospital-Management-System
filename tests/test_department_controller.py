"""Unit tests for the DepartmentController (service-backed).

The controller is a thin RBAC-gated façade over DepartmentService:
these tests verify the admin-only gate and that every method
delegates to the service.  Service-level behaviour (validation,
duplicate handling, FK-restrict messaging) lives in
``test_department_service.py``.
"""
from __future__ import annotations

from typing import Optional
from unittest.mock import MagicMock

import pytest

from src.auth.exceptions import PermissionDeniedError
from src.controllers.department_controller import DepartmentController
from src.constants import Role


# ── Fixtures ──────────────────────────────────────────────────


class FakeAuth:
    """Minimal stand-in for AuthController exposing current_role."""

    def __init__(self, role: Optional[str] = None) -> None:
        self.current_role = role


@pytest.fixture
def admin_controller() -> DepartmentController:
    """A DepartmentController with an admin session and mocked service."""
    service = MagicMock()
    return DepartmentController(
        auth_ctrl=FakeAuth(Role.ADMIN), service=service,
    )


@pytest.fixture
def mock_service(admin_controller: DepartmentController) -> MagicMock:
    """Access the mocked DepartmentService."""
    return admin_controller._service


# ── RBAC gate ─────────────────────────────────────────────────


class TestRbacGate:
    """All department operations must be admin-only."""

    def test_receptionist_denied(self) -> None:
        """A receptionist gets PermissionDeniedError on every method."""
        ctrl = DepartmentController(auth_ctrl=FakeAuth(Role.RECEPTIONIST))
        with pytest.raises(PermissionDeniedError):
            ctrl.list_departments()
        with pytest.raises(PermissionDeniedError):
            ctrl.get_department(1)
        with pytest.raises(PermissionDeniedError):
            ctrl.create_department("Oncology", "Cancer care")
        with pytest.raises(PermissionDeniedError):
            ctrl.update_department(1, department_name="Renamed")
        with pytest.raises(PermissionDeniedError):
            ctrl.delete_department(1)

    def test_no_session_denied(self) -> None:
        """No logged-in user gets PermissionDeniedError."""
        ctrl = DepartmentController(auth_ctrl=FakeAuth(None))
        with pytest.raises(PermissionDeniedError):
            ctrl.list_departments()


# ── Delegation ────────────────────────────────────────────────


class TestDelegation:
    """Every method forwards to the DepartmentService."""

    def test_list_delegates(self, admin_controller: DepartmentController,
                            mock_service: MagicMock) -> None:
        """list_departments returns the service result unchanged."""
        rows = [{"department_id": 1, "department_name": "Cardiology", "doctor_count": 3}]
        mock_service.list_departments.return_value = rows
        assert admin_controller.list_departments() == rows
        mock_service.list_departments.assert_called_once()

    def test_get_delegates(self, admin_controller: DepartmentController,
                           mock_service: MagicMock) -> None:
        """get_department forwards the id and returns the row."""
        mock_service.get_department.return_value = {"department_id": 2}
        assert admin_controller.get_department(2) == {"department_id": 2}
        mock_service.get_department.assert_called_once_with(2)

    def test_create_delegates(self, admin_controller: DepartmentController,
                              mock_service: MagicMock) -> None:
        """create_department forwards name/description and the tuple."""
        mock_service.create_department.return_value = (True, "Created", 9)
        result = admin_controller.create_department("Oncology", "Cancer care")
        assert result == (True, "Created", 9)
        mock_service.create_department.assert_called_once_with(
            "Oncology", "Cancer care",
        )

    def test_update_delegates(self, admin_controller: DepartmentController,
                              mock_service: MagicMock) -> None:
        """update_department forwards id and kwargs."""
        mock_service.update_department.return_value = (True, "Updated")
        result = admin_controller.update_department(
            2, department_name="Cardiac Sciences",
        )
        assert result == (True, "Updated")
        mock_service.update_department.assert_called_once_with(
            2, department_name="Cardiac Sciences", description=None,
        )

    def test_delete_delegates(self, admin_controller: DepartmentController,
                              mock_service: MagicMock) -> None:
        """delete_department forwards the id and the tuple."""
        mock_service.delete_department.return_value = (True, "Deleted")
        assert admin_controller.delete_department(8) == (True, "Deleted")
        mock_service.delete_department.assert_called_once_with(8)
