"""Unit tests for the AppointmentService.

Tests orchestration logic — booking, cancellation, rescheduling,
and retrieval — with mocked repositories and SchedulingEngine.
"""
from __future__ import annotations

from datetime import date, time
from unittest.mock import MagicMock, patch
from typing import Any, Dict

import pytest

from src.services.appointment_service import AppointmentService
from src.constants import AppointmentStatus
from src.database.connection import DatabaseConnection


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def service() -> AppointmentService:
    """Create an AppointmentService with all dependencies mocked.

    ``DatabaseConnection.transaction`` is mocked so booking/reschedule
    tests run without a MySQL server; the transaction connection is a
    plain MagicMock.
    """
    with (
        patch("src.services.appointment_service.AppointmentRepository") as appt_cls,
        patch("src.services.appointment_service.DoctorRepository") as doc_cls,
        patch("src.services.appointment_service.SchedulingEngine") as eng_cls,
        patch.object(DatabaseConnection, "transaction") as tx_cls,
    ):
        appt_cls.return_value = MagicMock()
        doc_cls.return_value = MagicMock()
        eng_cls.return_value = MagicMock()
        tx_cls.return_value.__enter__.return_value = MagicMock(name="txconn")
        svc = AppointmentService()
        svc._appt_repo = appt_cls.return_value
        svc._doctor_repo = doc_cls.return_value
        svc._engine = eng_cls.return_value
        yield svc


@pytest.fixture
def mock_appt(service: AppointmentService) -> MagicMock:
    """Access the mocked AppointmentRepository."""
    return service._appt_repo


@pytest.fixture
def mock_engine(service: AppointmentService) -> MagicMock:
    """Access the mocked SchedulingEngine."""
    return service._engine


# ── Factory helpers ───────────────────────────────────────────


def make_appointment(**overrides: Any) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "appointment_id": 1,
        "patient_id": "PAT-00001",
        "doctor_id": 1,
        "appointment_date": date(2026, 6, 15),
        "start_time": time(10, 0),
        "end_time": time(10, 30),
        "status": AppointmentStatus.BOOKED,
        "created_by": 1,
        "patient_name": "John Doe",
        "doctor_name": "Dr. Smith",
    }
    data.update(overrides)
    return data


# ── Booking tests ─────────────────────────────────────────────


class TestBookAppointment:
    """Tests for the book_appointment method."""

    def test_successful_booking(self, service: AppointmentService,
                                 mock_engine: MagicMock,
                                 mock_appt: MagicMock) -> None:
        """Valid booking creates an appointment."""
        mock_engine.validate_slot.return_value = (True, "")
        mock_appt.create_appointment.return_value = 1

        data = {
            "patient_id": "PAT-00001",
            "doctor_id": 1,
            "appointment_date": date(2026, 6, 15),
            "start_time": time(10, 0),
            "end_time": time(10, 30),
            "created_by": 1,
        }
        success, msg, appt_id = service.book_appointment(data)
        assert success is True
        assert appt_id == 1
        mock_appt.create_appointment.assert_called_once()

    def test_missing_fields(self, service: AppointmentService) -> None:
        """Missing required fields fails."""
        success, msg, appt_id = service.book_appointment({})
        assert success is False
        assert appt_id is None

    def test_engine_rejects_slot(self, service: AppointmentService,
                                  mock_engine: MagicMock) -> None:
        """When engine validation fails, booking fails."""
        mock_engine.validate_slot.return_value = (False, "Doctor is not available.")

        data = {
            "patient_id": "PAT-00001",
            "doctor_id": 1,
            "appointment_date": date(2026, 6, 15),
            "start_time": time(10, 0),
            "end_time": time(10, 30),
            "created_by": 1,
        }
        success, msg, appt_id = service.book_appointment(data)
        assert success is False
        assert "not available" in msg
        assert appt_id is None

    def test_rejects_missing_created_by(self, service: AppointmentService,
                                        mock_engine: MagicMock,
                                        mock_appt: MagicMock) -> None:
        """Booking must not substitute an invalid foreign-key actor."""

        data = {
            "patient_id": "PAT-00001",
            "doctor_id": 1,
            "appointment_date": date(2026, 6, 15),
            "start_time": time(10, 0),
            "end_time": time(10, 30),
        }
        success, msg, appt_id = service.book_appointment(data)
        assert success is False
        assert appt_id is None
        assert "signed-in user" in msg
        mock_appt.create_appointment.assert_not_called()


# ── Retrieval tests ───────────────────────────────────────────


class TestGetAppointments:
    """Tests for appointment retrieval methods."""

    def test_get_appointment(self, service: AppointmentService, mock_appt: MagicMock) -> None:
        """get_appointment delegates to repo."""
        mock_appt.find_by_id_with_details.return_value = make_appointment()
        result = service.get_appointment(1)
        assert result is not None
        assert result["appointment_id"] == 1

    def test_get_upcoming(self, service: AppointmentService, mock_appt: MagicMock) -> None:
        """get_upcoming_appointments delegates to repo."""
        mock_appt.find_all_upcoming.return_value = [make_appointment()]
        result = service.get_upcoming_appointments()
        assert len(result) == 1

    def test_get_doctor_appointments(self, service: AppointmentService, mock_appt: MagicMock) -> None:
        """get_doctor_appointments with date."""
        mock_appt.find_by_doctor_and_date.return_value = [make_appointment()]
        result = service.get_doctor_appointments(1, date(2026, 6, 15))
        assert len(result) == 1

    def test_get_doctor_appointments_today(self, service: AppointmentService, mock_appt: MagicMock) -> None:
        """get_doctor_appointments without date returns today's."""
        mock_appt.find_today_by_doctor.return_value = [make_appointment()]
        result = service.get_doctor_appointments(1)
        assert len(result) == 1

    def test_get_patient_appointments(self, service: AppointmentService, mock_appt: MagicMock) -> None:
        """get_patient_appointments delegates to repo."""
        mock_appt.find_by_patient.return_value = [make_appointment()]
        result = service.get_patient_appointments("PAT-00001")
        assert len(result) == 1

    def test_search_appointments(self, service: AppointmentService, mock_appt: MagicMock) -> None:
        """search_appointments delegates to repo."""
        mock_appt.search_appointments.return_value = [make_appointment()]
        result = service.search_appointments("Smith")
        assert len(result) == 1


# ── Modification tests ────────────────────────────────────────


class TestCancelAppointment:
    """Tests for appointment cancellation."""

    def test_cancel_success(self, service: AppointmentService, mock_appt: MagicMock) -> None:
        """Cancelling a booked appointment succeeds."""
        mock_appt.find_by_id_with_details.return_value = make_appointment()
        mock_appt.cancel_appointment.return_value = 1
        success, msg = service.cancel_appointment(1)
        assert success is True

    def test_cancel_not_found(self, service: AppointmentService, mock_appt: MagicMock) -> None:
        """Cancelling a non-existent appointment fails."""
        mock_appt.find_by_id_with_details.return_value = None
        success, msg = service.cancel_appointment(999)
        assert success is False
        assert "not found" in msg.lower()

    def test_cancel_already_cancelled(self, service: AppointmentService, mock_appt: MagicMock) -> None:
        """Cancelling an already-cancelled appointment fails."""
        mock_appt.find_by_id_with_details.return_value = make_appointment(status="Cancelled")
        success, msg = service.cancel_appointment(1)
        assert success is False
        assert "only booked" in msg.lower()


class TestRescheduleAppointment:
    """Tests for appointment rescheduling."""

    def test_reschedule_creates_new_linked_row(self, service: AppointmentService,
                                                mock_appt: MagicMock, mock_engine: MagicMock) -> None:
        """Reschedule inserts a NEW row linked via rescheduled_from_id and
        marks the original Cancelled — the original is never mutated."""
        mock_appt.find_by_id_with_details.return_value = make_appointment()
        mock_engine.validate_slot.return_value = (True, "")
        mock_appt.create_appointment.return_value = 2

        success, msg = service.reschedule_appointment(
            1, date(2026, 6, 16), time(14, 0), time(14, 30),
        )
        assert success is True

        # A new row is created, linked to the original
        call_data = mock_appt.create_appointment.call_args.args[0]
        assert call_data["rescheduled_from_id"] == 1
        assert call_data["appointment_date"] == date(2026, 6, 16)
        assert call_data["start_time"] == time(14, 0)
        assert call_data["status"] == AppointmentStatus.BOOKED

        # The original is cancelled (status update) — never mutated in place
        mock_appt.cancel_appointment.assert_called_once()
        assert mock_appt.cancel_appointment.call_args.args[0] == 1
        mock_appt.update_appointment.assert_not_called()

    def test_reschedule_not_found(self, service: AppointmentService, mock_appt: MagicMock) -> None:
        """Rescheduling a non-existent appointment fails."""
        mock_appt.find_by_id_with_details.return_value = None
        success, msg = service.reschedule_appointment(
            999, date(2026, 6, 16), time(14, 0), time(14, 30),
        )
        assert success is False

    def test_reschedule_invalid_slot(self, service: AppointmentService,
                                      mock_appt: MagicMock,
                                      mock_engine: MagicMock) -> None:
        """Rescheduling to an invalid slot fails."""
        mock_appt.find_by_id_with_details.return_value = make_appointment()
        mock_engine.validate_slot.return_value = (False, "Slot not available.")

        success, msg = service.reschedule_appointment(
            1, date(2026, 6, 16), time(8, 0), time(8, 30),
        )
        assert success is False

    def test_reschedule_excludes_current_appt(self, service: AppointmentService,
                                               mock_appt: MagicMock,
                                               mock_engine: MagicMock) -> None:
        """Reschedule excludes current appointment from overlap check."""
        mock_appt.find_by_id_with_details.return_value = make_appointment()
        mock_engine.validate_slot.return_value = (True, "")
        mock_appt.update_appointment.return_value = 1

        service.reschedule_appointment(1, date(2026, 6, 15), time(10, 0), time(10, 30))
        # Verify exclude_appointment_id was passed
        call_kwargs = mock_engine.validate_slot.call_args[1]
        assert call_kwargs.get("exclude_appointment_id") == 1


class TestUpdateStatus:
    """Tests for status updates."""

    def test_update_status_valid(self, service: AppointmentService, mock_appt: MagicMock) -> None:
        """Valid status update succeeds."""
        mock_appt.find_by_id_with_details.return_value = make_appointment()
        mock_appt.update_appointment.return_value = 1
        success, msg = service.update_status(1, AppointmentStatus.COMPLETED)
        assert success is True

    def test_update_status_invalid(self, service: AppointmentService) -> None:
        """Invalid status fails."""
        success, msg = service.update_status(1, "InvalidStatus")
        assert success is False

    def test_update_status_not_found(self, service: AppointmentService, mock_appt: MagicMock) -> None:
        """Updating a non-existent appointment fails."""
        mock_appt.find_by_id_with_details.return_value = None
        success, msg = service.update_status(999, AppointmentStatus.COMPLETED)
        assert success is False


# ── Slot / stats tests ────────────────────────────────────────


class TestSlotAndStats:
    """Tests for slot queries and statistics."""

    def test_get_available_slots(self, service: AppointmentService, mock_engine: MagicMock) -> None:
        """get_available_slots delegates to engine."""
        mock_engine.get_available_slots.return_value = [{"start_time": time(9, 0), "available": True}]
        result = service.get_available_slots(1, date(2026, 6, 15))
        assert len(result) == 1

    def test_get_department_slots(self, service: AppointmentService, mock_engine: MagicMock) -> None:
        """get_department_slots delegates to engine."""
        mock_engine.get_department_slots.return_value = {1: [{"start_time": time(9, 0)}]}
        result = service.get_department_slots(1, date(2026, 6, 15))
        assert 1 in result

    def test_find_earliest_slot(self, service: AppointmentService, mock_engine: MagicMock) -> None:
        """find_earliest_slot delegates to engine."""
        mock_engine.find_earliest_slot.return_value = {"date": date(2026, 6, 15), "start_time": time(9, 0)}
        result = service.find_earliest_slot(1)
        assert result is not None

    def test_is_date_available(self, service: AppointmentService, mock_engine: MagicMock) -> None:
        """is_date_available delegates to engine."""
        mock_engine.is_date_available.return_value = (True, None)
        available, reason = service.is_date_available(1, date(2026, 6, 15))
        assert available is True

    def test_count_today(self, service: AppointmentService, mock_appt: MagicMock) -> None:
        """count_today delegates to repo."""
        mock_appt.count_today.return_value = 5
        assert service.count_today() == 5

    def test_get_status_counts(self, service: AppointmentService, mock_appt: MagicMock) -> None:
        """get_status_counts delegates to repo."""
        mock_appt.count_by_status.return_value = [{"status": "Booked", "count": 10}]
        result = service.get_status_counts()
        assert len(result) == 1
