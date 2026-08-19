"""Unit tests for the DoctorController.

Tests validate correct delegation to DoctorService, input validation
using the centralized validators, and schedule/leave operations.
"""
from __future__ import annotations

from datetime import time
from unittest.mock import MagicMock, patch
from typing import Any, Dict

import pytest

from src.controllers.doctor_controller import DoctorController
from src.utils.validators import validate_doctor_data, validate_department_name
from src.auth.exceptions import PermissionDeniedError


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def mock_auth_ctrl() -> MagicMock:
    """Create a mocked AuthController with an Admin session."""
    auth = MagicMock()
    auth.current_role = "Admin"
    return auth


@pytest.fixture
def controller(mock_auth_ctrl: MagicMock) -> DoctorController:
    """Create a DoctorController with mocked dependencies."""
    with patch("src.controllers.doctor_controller.DoctorService") as mock_cls:
        with patch("src.controllers.doctor_controller.AuditService") as mock_audit:
            mock_cls.return_value = MagicMock()
            mock_audit.return_value = MagicMock()
            yield DoctorController(auth_ctrl=mock_auth_ctrl)


# ── RBAC gate ─────────────────────────────────────────────────


class TestRbacGate:
    """Doctor/department operations must be gated to the correct roles."""

    def test_no_session_denied(self, mock_auth_ctrl: MagicMock) -> None:
        """No logged-in user is denied."""
        mock_auth_ctrl.current_role = None
        ctrl = DoctorController(auth_ctrl=mock_auth_ctrl)
        with pytest.raises(PermissionDeniedError):
            ctrl.get_all_doctors()

    def test_management_admin_only(self, mock_auth_ctrl: MagicMock) -> None:
        """Doctor creation is admin-only even for receptionists."""
        mock_auth_ctrl.current_role = "Receptionist"
        ctrl = DoctorController(auth_ctrl=mock_auth_ctrl)
        with pytest.raises(PermissionDeniedError):
            ctrl.create_doctor({"full_name": "Dr. X"})


@pytest.fixture
def mock_doctor_service(controller: DoctorController) -> MagicMock:
    """Access the mocked DoctorService from the controller."""
    return controller._doctor_service


# ── Validation tests (delegated to centralized validators) ────


class TestValidateDoctorData:
    """Tests for the validate_doctor_data static method."""

    def test_valid_data(self) -> None:
        """Valid doctor data passes validation."""
        data = {"full_name": "John Smith", "department_id": 1}
        valid, msg = DoctorController.validate_doctor_data(data)
        assert valid is True
        assert msg == ""

    def test_missing_name(self) -> None:
        """Missing full_name should fail."""
        data = {"department_id": 1}
        valid, msg = DoctorController.validate_doctor_data(data)
        assert valid is False
        assert "name" in msg.lower()

    def test_missing_department(self) -> None:
        """Missing department_id should fail."""
        data = {"full_name": "John Smith"}
        valid, msg = DoctorController.validate_doctor_data(data)
        assert valid is False
        assert "department" in msg.lower()

    def test_invalid_email(self) -> None:
        """Invalid email should fail."""
        data = {"full_name": "John Smith", "department_id": 1, "email": "notanemail"}
        valid, msg = DoctorController.validate_doctor_data(data)
        assert valid is False
        assert "email" in msg.lower()

    def test_valid_email(self) -> None:
        """Valid email passes."""
        data = {"full_name": "John Smith", "department_id": 1, "email": "john@example.com"}
        valid, msg = DoctorController.validate_doctor_data(data)
        assert valid is True

    def test_negative_consultation_fee(self) -> None:
        """Negative fee should fail."""
        data = {"full_name": "John Smith", "department_id": 1, "consultation_fee": -10}
        valid, msg = DoctorController.validate_doctor_data(data)
        assert valid is False
        assert "fee" in msg.lower()

    def test_invalid_experience_years(self) -> None:
        """Experience over 60 should fail."""
        data = {"full_name": "John Smith", "department_id": 1, "experience_years": 100}
        valid, msg = DoctorController.validate_doctor_data(data)
        assert valid is False
        assert "experience" in msg.lower()

    def test_delegates_to_validator_module(self) -> None:
        """validate_doctor_data should match the centralized validator output."""
        data = {"full_name": "John Smith", "department_id": 1}
        controller_result = DoctorController.validate_doctor_data(data)
        validator_result = validate_doctor_data(data)
        assert controller_result == validator_result


class TestValidateDepartmentData:
    """Tests for the validate_department_data static method."""

    def test_valid_name(self) -> None:
        """Valid department name passes."""
        valid, msg = DoctorController.validate_department_data({"department_name": "Cardiology"})
        assert valid is True

    def test_empty_name(self) -> None:
        """Empty name should fail."""
        valid, msg = DoctorController.validate_department_data({"department_name": ""})
        assert valid is False

    def test_long_name(self) -> None:
        """Name over 100 chars should fail."""
        valid, msg = DoctorController.validate_department_data(
            {"department_name": "X" * 101}
        )
        assert valid is False

    def test_delegates_to_validator(self) -> None:
        """validate_department_data should match validator output."""
        result = DoctorController.validate_department_data({"department_name": "Cardiology"})
        expected = validate_department_name("Cardiology")
        assert result == expected


class TestValidateScheduleData:
    """Tests for the validate_schedule_data static method."""

    def test_valid_schedule(self) -> None:
        """Valid day/time passes."""
        valid, msg = DoctorController.validate_schedule_data(1, time(9, 0), time(17, 0))
        assert valid is True

    def test_invalid_day(self) -> None:
        """Day outside 0-6 range should fail."""
        valid, msg = DoctorController.validate_schedule_data(7, time(9, 0), time(17, 0))
        assert valid is False
        assert "day" in msg.lower()

    def test_end_before_start(self) -> None:
        """End time before start time should fail."""
        valid, msg = DoctorController.validate_schedule_data(1, time(17, 0), time(9, 0))
        assert valid is False
        assert "before" in msg.lower()


# ── Department operations ─────────────────────────────────────


class TestDepartmentOperations:
    """Tests for department CRUD."""

    def test_get_all_departments(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """get_all_departments delegates to service."""
        mock_doctor_service.get_all_departments.return_value = [{"department_id": 1, "department_name": "Cardiology"}]
        result = controller.get_all_departments()
        assert len(result) == 1
        assert result[0]["department_name"] == "Cardiology"

    def test_get_department(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """get_department delegates to service."""
        mock_doctor_service.get_department.return_value = {"department_id": 1, "department_name": "Cardiology"}
        result = controller.get_department(1)
        assert result is not None
        assert result["department_name"] == "Cardiology"

    def test_create_department_valid(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """Valid department creation."""
        mock_doctor_service.create_department.return_value = (True, "Created.", 1)
        result = controller.create_department({"department_name": "Neuro  "})
        assert result[0] is True
        # Check that name was stripped
        args, _ = mock_doctor_service.create_department.call_args
        assert args[0]["department_name"] == "Neuro"

    def test_create_department_invalid(self, controller: DoctorController) -> None:
        """Invalid department name fails at controller level."""
        result = controller.create_department({"department_name": ""})
        assert result[0] is False

    def test_update_department(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """update_department delegates to service."""
        mock_doctor_service.update_department.return_value = (True, "Updated.")
        result = controller.update_department(1, {"department_name": "Neuro Updated"})
        assert result[0] is True

    def test_delete_department(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """delete_department delegates to service."""
        mock_doctor_service.delete_department.return_value = (True, "Deleted.")
        result = controller.delete_department(1)
        assert result[0] is True


# ── Doctor operations ─────────────────────────────────────────


class TestDoctorOperations:
    """Tests for doctor CRUD."""

    def test_get_all_doctors(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """get_all_doctors delegates to service."""
        mock_doctor_service.get_all_doctors.return_value = [{"doctor_id": 1, "full_name": "Dr. Smith"}]
        result = controller.get_all_doctors()
        assert len(result) == 1

    def test_get_doctor(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """get_doctor delegates to service."""
        mock_doctor_service.get_doctor.return_value = {"doctor_id": 1, "full_name": "Dr. Smith"}
        result = controller.get_doctor(1)
        assert result is not None

    def test_create_doctor_valid(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """Valid doctor creation."""
        mock_doctor_service.create_doctor.return_value = (True, "Created.", 1)
        result = controller.create_doctor({"full_name": "Dr. Jane", "department_id": 1})
        assert result[0] is True

    def test_create_doctor_invalid(self, controller: DoctorController) -> None:
        """Invalid data fails at controller level."""
        result = controller.create_doctor({"full_name": ""})
        assert result[0] is False

    def test_update_doctor(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """update_doctor delegates to service."""
        mock_doctor_service.update_doctor.return_value = (True, "Updated.")
        result = controller.update_doctor(1, {"full_name": "Dr. Jane Updated", "department_id": 1})
        assert result[0] is True

    def test_delete_doctor(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """delete_doctor delegates to service."""
        mock_doctor_service.delete_doctor.return_value = (True, "Deleted.")
        result = controller.delete_doctor(1)
        assert result[0] is True

    def test_search_doctors(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """search_doctors delegates to service."""
        mock_doctor_service.search_doctors.return_value = [{"doctor_id": 1}]
        result = controller.search_doctors("Smith")
        assert len(result) == 1

    def test_filter_doctors(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """filter_doctors delegates to service."""
        mock_doctor_service.filter_doctors.return_value = [{"doctor_id": 1}]
        result = controller.filter_doctors(department_id=1, specialization="Cardiology", status="Active")
        assert len(result) == 1

    def test_get_all_specializations(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """get_all_specializations delegates to service."""
        mock_doctor_service.get_all_specializations.return_value = ["Cardiology", "Neurology"]
        result = controller.get_all_specializations()
        assert "Cardiology" in result
        assert len(result) == 2

    def test_get_active_doctors(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """get_active_doctors delegates to service."""
        mock_doctor_service.get_active_doctors.return_value = [{"doctor_id": 1}]
        result = controller.get_active_doctors()
        assert len(result) == 1

    def test_get_doctors_by_department(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """get_doctors_by_department delegates to service."""
        mock_doctor_service.get_doctors_by_department.return_value = [{"doctor_id": 1}]
        result = controller.get_doctors_by_department(1)
        assert len(result) == 1

    def test_get_doctor_by_user_id(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """get_doctor_by_user_id delegates to service."""
        mock_doctor_service.get_doctor_by_user_id.return_value = {"doctor_id": 1}
        result = controller.get_doctor_by_user_id(1)
        assert result is not None

    def test_create_doctor_with_user_data(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """create_doctor with user_data passes through."""
        mock_doctor_service.create_doctor.return_value = (True, "Created.", 1)
        result = controller.create_doctor(
            {"full_name": "Dr. Jane", "department_id": 1},
            user_data={"username": "drjane", "password": "secret123"},
        )
        assert result[0] is True
        mock_doctor_service.create_doctor.assert_called_once()


# ── Schedule and Leave operations ─────────────────────────────


class TestScheduleAndLeave:
    """Tests for doctor schedule and leave operations."""

    def test_get_doctor_schedule(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """get_doctor_schedule delegates to service."""
        mock_doctor_service.get_doctor_schedule.return_value = [{"day_of_week": 1}]
        result = controller.get_doctor_schedule(1)
        assert len(result) == 1

    def test_update_doctor_schedule_valid(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """Valid schedule update."""
        mock_doctor_service.update_doctor_schedule.return_value = (True, "Updated.")
        result = controller.update_doctor_schedule(1, 1, time(9, 0), time(17, 0))
        assert result[0] is True

    def test_update_doctor_schedule_invalid(self, controller: DoctorController) -> None:
        """Invalid schedule (end before start) fails at controller level."""
        result = controller.update_doctor_schedule(1, 1, time(17, 0), time(9, 0))
        assert result[0] is False

    def test_get_doctor_leaves(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """get_doctor_leaves delegates to service."""
        mock_doctor_service.get_doctor_leaves.return_value = [{"leave_id": 1}]
        result = controller.get_doctor_leaves(1)
        assert len(result) == 1

    def test_add_doctor_leave(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """add_doctor_leave delegates to service."""
        mock_doctor_service.add_doctor_leave.return_value = (True, "Leave added.", 1)
        data = {"doctor_id": 1, "leave_start_date": "2026-01-01", "leave_end_date": "2026-01-05"}
        result = controller.add_doctor_leave(data)
        assert result[0] is True

    def test_delete_doctor_leave(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """delete_doctor_leave delegates to service."""
        mock_doctor_service.delete_doctor_leave.return_value = (True, "Deleted.")
        result = controller.delete_doctor_leave(1)
        assert result[0] is True

    def test_get_stats(self, controller: DoctorController, mock_doctor_service: MagicMock) -> None:
        """get_total_doctors and get_active_doctors_count delegate correctly."""
        mock_doctor_service.get_total_doctors.return_value = 10
        mock_doctor_service.get_active_doctors_count.return_value = 8

        assert controller.get_total_doctors() == 10
        assert controller.get_active_doctors_count() == 8
