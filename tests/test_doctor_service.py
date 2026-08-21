"""Unit tests for the DoctorService.

Tests validate business logic for doctor, department, schedule,
and leave operations with mocked repositories.
"""
from __future__ import annotations

from datetime import time, date
from unittest.mock import MagicMock, patch
from typing import Any, Dict

import pytest

from src.services.doctor_service import DoctorService


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def service() -> DoctorService:
    """Create a DoctorService with all repositories mocked."""
    # Mock the transaction context manager so create_doctor (with user_data)
    # never opens a real MySQL connection.
    mock_conn = MagicMock()
    mock_transaction_ctx = MagicMock()
    mock_transaction_ctx.__enter__ = MagicMock(return_value=mock_conn)
    mock_transaction_ctx.__exit__ = MagicMock(return_value=False)

    with (
        patch("src.services.doctor_service.DoctorRepository") as dr_cls,
        patch("src.services.doctor_service.DepartmentRepository") as dept_cls,
        patch("src.services.doctor_service.DoctorScheduleRepository") as sched_cls,
        patch("src.services.doctor_service.DoctorLeaveRepository") as leave_cls,
        patch("src.services.doctor_service.UserService") as user_svc_cls,
        patch("src.services.doctor_service.DatabaseConnection") as db_cls,
    ):
        dr_cls.return_value = MagicMock()
        dept_cls.return_value = MagicMock()
        sched_cls.return_value = MagicMock()
        leave_cls.return_value = MagicMock()
        user_svc_cls.return_value = MagicMock()
        db_cls.transaction.return_value = mock_transaction_ctx
        yield DoctorService()


@pytest.fixture
def repo(service: DoctorService) -> MagicMock:
    """Access the mocked DoctorRepository."""
    return service._doctor_repo


@pytest.fixture
def dept_repo(service: DoctorService) -> MagicMock:
    """Access the mocked DepartmentRepository."""
    return service._dept_repo


@pytest.fixture
def sched_repo(service: DoctorService) -> MagicMock:
    """Access the mocked DoctorScheduleRepository."""
    return service._schedule_repo


@pytest.fixture
def leave_repo(service: DoctorService) -> MagicMock:
    """Access the mocked DoctorLeaveRepository."""
    return service._leave_repo


@pytest.fixture
def user_svc(service: DoctorService) -> MagicMock:
    """Access the mocked UserService."""
    return service._user_service


# ── Factory helpers ───────────────────────────────────────────


def make_doctor(**overrides: Any) -> Dict[str, Any]:
    """Create a doctor dict with sensible defaults."""
    data: Dict[str, Any] = {
        "doctor_id": 1,
        "user_id": 1,
        "department_id": 1,
        "full_name": "Dr. Jane Smith",
        "specialization": "Cardiology",
        "email": "jane@hospital.com",
        "contact_number": "1234567890",
        "status": "Active",
        "department_name": "Cardiology",
    }
    data.update(overrides)
    return data


def make_department(**overrides: Any) -> Dict[str, Any]:
    """Create a department dict with sensible defaults."""
    data: Dict[str, Any] = {
        "department_id": 1,
        "department_name": "Cardiology",
        "description": "Heart care",
        "doctor_count": 5,
    }
    data.update(overrides)
    return data


# ── Department operations ─────────────────────────────────────


class TestDepartmentOperations:
    """Tests for department CRUD business logic."""

    def test_get_all_departments(self, service: DoctorService, dept_repo: MagicMock) -> None:
        """get_all_departments fetches with doctor count."""
        dept_repo.get_with_doctor_count.return_value = [make_department()]
        result = service.get_all_departments()
        assert len(result) == 1
        dept_repo.get_with_doctor_count.assert_called_once()

    def test_create_department_success(self, service: DoctorService, dept_repo: MagicMock) -> None:
        """Creating a department with valid data."""
        dept_repo.find_by_name.return_value = None
        dept_repo.create_department.return_value = 1

        success, msg, dept_id = service.create_department({"department_name": "Neuro  "})
        assert success is True
        assert dept_id == 1

    def test_create_department_duplicate(self, service: DoctorService, dept_repo: MagicMock) -> None:
        """Creating a department with an existing name fails."""
        dept_repo.find_by_name.return_value = make_department(department_id=1)

        success, msg, dept_id = service.create_department({"department_name": "Cardiology"})
        assert success is False
        assert msg is not None

    def test_delete_department_with_doctors(self, service: DoctorService, repo: MagicMock) -> None:
        """Deleting a department with doctors fails."""
        repo.find_by_department.return_value = [make_doctor()]
        success, msg = service.delete_department(1)
        assert success is False
        assert "doctors" in msg.lower()


# ── Doctor operations ─────────────────────────────────────────


class TestDoctorOperations:
    """Tests for doctor CRUD business logic."""

    def test_get_all_doctors(self, service: DoctorService, repo: MagicMock) -> None:
        """get_all_doctors fetches with department info."""
        repo.find_all_with_department.return_value = [make_doctor()]
        result = service.get_all_doctors()
        assert len(result) == 1

    def test_create_doctor_success(self, service: DoctorService, repo: MagicMock) -> None:
        """Creating a doctor with valid data."""
        repo.create_doctor.return_value = 1
        success, msg, doc_id = service.create_doctor(
            {"full_name": "Dr. John", "department_id": 1}
        )
        assert success is True
        assert doc_id == 1

    def test_create_doctor_missing_field(self, service: DoctorService) -> None:
        """Creating a doctor without required fields fails."""
        success, msg, doc_id = service.create_doctor({"full_name": ""})
        assert success is False
        assert "required" in msg.lower()

    def test_create_doctor_with_user(self, service: DoctorService, repo: MagicMock, user_svc: MagicMock) -> None:
        """Creating a doctor with a linked user account."""
        user_svc.get_role_id.return_value = 2
        user_svc.create_user.return_value = (True, "User created.", 5)
        repo.create_doctor.return_value = 1

        success, msg, doc_id = service.create_doctor(
            {"full_name": "Dr. John", "department_id": 1},
            user_data={"username": "drjohn", "password": "secret123"},
        )
        assert success is True
        assert doc_id == 1
        # Verify both calls happened inside the same transaction context
        user_svc.create_user.assert_called_once()
        repo.create_doctor.assert_called_once()

    def test_create_doctor_with_user_rollback(self, service: DoctorService, repo: MagicMock, user_svc: MagicMock) -> None:
        """When user creation fails, doctor creation must not proceed (rollback)."""
        user_svc.get_role_id.return_value = 2
        user_svc.create_user.return_value = (False, "Username already exists", None)

        success, msg, doc_id = service.create_doctor(
            {"full_name": "Dr. Ghost", "department_id": 1},
            user_data={"username": "taken", "password": "x"},
        )
        assert success is False
        assert "exists" in msg.lower() or "failed" in msg.lower()
        assert doc_id is None
        # Doctor repo must never have been called — the failure rolled back before it
        repo.create_doctor.assert_not_called()

    def test_update_doctor(self, service: DoctorService, repo: MagicMock) -> None:
        """Updating a doctor."""
        repo.find_by_id_with_details.return_value = make_doctor()
        repo.update_doctor.return_value = 1
        success, msg = service.update_doctor(1, {"full_name": "Dr. John Updated"})
        assert success is True

    def test_update_doctor_not_found(self, service: DoctorService, repo: MagicMock) -> None:
        """Updating a non-existent doctor fails."""
        repo.find_by_id_with_details.return_value = None
        success, msg = service.update_doctor(999, {"full_name": "Ghost"})
        assert success is False

    def test_delete_doctor_removes_schedule(self, service: DoctorService, repo: MagicMock, sched_repo: MagicMock) -> None:
        """Deleting a doctor also removes their schedule."""
        repo.find_by_id_with_details.return_value = make_doctor()
        repo.delete_doctor.return_value = 1
        sched_repo.delete_by_doctor.return_value = 0

        success, msg = service.delete_doctor(1)
        assert success is True
        sched_repo.delete_by_doctor.assert_called_once_with(1)

    def test_search_doctors(self, service: DoctorService, repo: MagicMock) -> None:
        """search_doctors delegates to repository."""
        repo.search_doctors.return_value = [make_doctor()]
        result = service.search_doctors("Smith")
        assert len(result) == 1

    def test_get_all_specializations(self, service: DoctorService, repo: MagicMock) -> None:
        """get_all_specializations returns unique sorted list."""
        repo.find_all_with_department.return_value = [
            make_doctor(doctor_id=1, specialization="Cardiology"),
            make_doctor(doctor_id=2, specialization="Neurology"),
            make_doctor(doctor_id=3, specialization="Cardiology"),
        ]
        specs = service.get_all_specializations()
        assert specs == ["Cardiology", "Neurology"]

    def test_get_doctor_by_user_id(self, service: DoctorService, repo: MagicMock) -> None:
        """get_doctor_by_user_id delegates to repository."""
        repo.find_by_user_id.return_value = make_doctor()
        result = service.get_doctor_by_user_id(1)
        assert result is not None
        assert result["full_name"] == "Dr. Jane Smith"


# ── Schedule operations ───────────────────────────────────────


class TestScheduleOperations:
    """Tests for doctor schedule business logic."""

    def test_get_doctor_schedule(self, service: DoctorService, sched_repo: MagicMock) -> None:
        """get_doctor_schedule delegates to repository."""
        sched_repo.find_by_doctor.return_value = [{"day_of_week": 1}]
        result = service.get_doctor_schedule(1)
        assert len(result) == 1

    def test_update_doctor_schedule_upserts(self, service: DoctorService, sched_repo: MagicMock) -> None:
        """update_doctor_schedule calls upsert."""
        sched_repo.upsert_schedule.return_value = 1
        success, msg = service.update_doctor_schedule(1, 1, time(9, 0), time(17, 0))
        assert success is True
        sched_repo.upsert_schedule.assert_called_once()

    def test_update_schedule_invalid_times(self, service: DoctorService) -> None:
        """End time before start time fails."""
        success, msg = service.update_doctor_schedule(1, 1, time(17, 0), time(9, 0))
        assert success is False


# ── Leave operations ─────────────────────────────────────────


class TestLeaveOperations:
    """Tests for doctor leave business logic."""

    def test_add_doctor_leave(self, service: DoctorService, leave_repo: MagicMock) -> None:
        """Adding a valid leave record."""
        leave_repo.create_leave.return_value = 1
        data = {"doctor_id": 1, "leave_start_date": date(2026, 1, 1), "leave_end_date": date(2026, 1, 5)}
        success, msg, leave_id = service.add_doctor_leave(data)
        assert success is True
        assert leave_id == 1

    def test_add_leave_invalid_dates(self, service: DoctorService) -> None:
        """Start date after end date fails."""
        data = {"doctor_id": 1, "leave_start_date": date(2026, 1, 10), "leave_end_date": date(2026, 1, 5)}
        success, msg, leave_id = service.add_doctor_leave(data)
        assert success is False

    def test_delete_doctor_leave(self, service: DoctorService, leave_repo: MagicMock) -> None:
        """Deleting a leave record."""
        leave_repo.delete_leave.return_value = 1
        success, msg = service.delete_doctor_leave(1)
        assert success is True
