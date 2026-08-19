"""Unit tests for the SchedulingEngine.

Tests all validation rules in isolation, slot generation with various
constraints, and the department-wide / earliest-slot queries.
"""
from __future__ import annotations

from datetime import date, time, timedelta
from unittest.mock import MagicMock, patch
from typing import Any, Dict

import pytest

from src.services.scheduling_engine import (
    SchedulingEngine,
    _to_time,
    _to_date,
    _time_to_minutes,
    _overlaps,
)
from src.constants import AppointmentStatus

# A date safely in the future so the past-date validation rule never
# trips on the fixed fixtures.
FUTURE_DATE = date.today() + timedelta(days=30)


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def engine() -> SchedulingEngine:
    """Create a SchedulingEngine with all repositories mocked."""
    with (
        patch("src.services.scheduling_engine.AppointmentRepository") as appt_cls,
        patch("src.services.scheduling_engine.DoctorRepository") as doc_cls,
        patch("src.services.scheduling_engine.DoctorScheduleRepository") as sched_cls,
        patch("src.services.scheduling_engine.DoctorLeaveRepository") as leave_cls,
        patch("src.services.scheduling_engine.HospitalHolidayRepository") as hol_cls,
    ):
        appt_cls.return_value = MagicMock()
        doc_cls.return_value = MagicMock()
        sched_cls.return_value = MagicMock()
        leave_cls.return_value = MagicMock()
        hol_cls.return_value = MagicMock()
        yield SchedulingEngine(
            appt_repo=appt_cls.return_value,
            doctor_repo=doc_cls.return_value,
            schedule_repo=sched_cls.return_value,
            leave_repo=leave_cls.return_value,
            holiday_repo=hol_cls.return_value,
        )


@pytest.fixture
def mock_doctor(engine: SchedulingEngine) -> MagicMock:
    """Access the mocked DoctorRepository."""
    return engine._doctor_repo


@pytest.fixture
def mock_schedule(engine: SchedulingEngine) -> MagicMock:
    """Access the mocked DoctorScheduleRepository."""
    return engine._schedule_repo


@pytest.fixture
def mock_leave(engine: SchedulingEngine) -> MagicMock:
    """Access the mocked DoctorLeaveRepository."""
    return engine._leave_repo


@pytest.fixture
def mock_holiday(engine: SchedulingEngine) -> MagicMock:
    """Access the mocked HospitalHolidayRepository."""
    return engine._holiday_repo


@pytest.fixture
def mock_appt(engine: SchedulingEngine) -> MagicMock:
    """Access the mocked AppointmentRepository."""
    return engine._appt_repo


# ── Factory helpers ───────────────────────────────────────────


def make_doctor(**overrides: Any) -> Dict[str, Any]:
    """Create a doctor dict with sensible defaults."""
    data: Dict[str, Any] = {
        "doctor_id": 1,
        "full_name": "Dr. Smith",
        "status": "Active",
        "department_id": 1,
        "max_appointments_per_day": 20,
        "lunch_break_start": None,
        "lunch_break_end": None,
    }
    data.update(overrides)
    return data


def make_schedule(**overrides: Any) -> Dict[str, Any]:
    """Create a schedule dict with sensible defaults."""
    data: Dict[str, Any] = {
        "doctor_id": 1,
        "day_of_week": 1,  # Monday (SQL: Sun=0)
        "start_time": time(9, 0),
        "end_time": time(17, 0),
        "is_available": True,
        "lunch_break_start": None,
        "lunch_break_end": None,
    }
    data.update(overrides)
    return data


def make_appointment(**overrides: Any) -> Dict[str, Any]:
    """Create an appointment dict."""
    data: Dict[str, Any] = {
        "appointment_id": 1,
        "doctor_id": 1,
        "patient_id": "PAT-00001",
        "appointment_date": FUTURE_DATE,
        "start_time": time(10, 0),
        "end_time": time(10, 30),
        "status": AppointmentStatus.BOOKED,
    }
    data.update(overrides)
    return data


# ── Pure helper tests ─────────────────────────────────────────


class TestHelpers:
    """Tests for _to_time, _to_date, _time_to_minutes, _overlaps."""

    def test_to_time_from_time(self) -> None:
        result = _to_time(time(14, 30))
        assert result == time(14, 30)

    def test_to_time_from_string(self) -> None:
        result = _to_time("14:30")
        assert result == time(14, 30)

    def test_to_time_from_iso_string(self) -> None:
        result = _to_time("14:30:00")
        assert result == time(14, 30)

    def test_to_time_none(self) -> None:
        assert _to_time(None) is None

    def test_to_time_empty_string(self) -> None:
        assert _to_time("") is None

    def test_to_date_from_date(self) -> None:
        d = FUTURE_DATE
        assert _to_date(d) == d

    def test_to_date_from_string(self) -> None:
        assert _to_date("2026-06-15") == date(2026, 6, 15)

    def test_to_date_none(self) -> None:
        assert _to_date(None) is None

    def test_time_to_minutes(self) -> None:
        assert _time_to_minutes(time(9, 30)) == 570
        assert _time_to_minutes(time(0, 0)) == 0
        assert _time_to_minutes(time(23, 59)) == 1439

    def test_overlaps_true(self) -> None:
        assert _overlaps(time(10, 0), time(11, 0), time(10, 30), time(11, 30)) is True

    def test_overlaps_false(self) -> None:
        assert _overlaps(time(10, 0), time(10, 30), time(11, 0), time(11, 30)) is False

    def test_overlaps_adjacent(self) -> None:
        """Adjacent slots do not overlap."""
        assert _overlaps(time(10, 0), time(10, 30), time(10, 30), time(11, 0)) is False


# ── validate_slot tests ───────────────────────────────────────


class TestValidateSlot:
    """Tests for the validate_slot method — each check in isolation."""

    def test_valid_slot(self, engine: SchedulingEngine, mock_doctor: MagicMock,
                        mock_schedule: MagicMock, mock_leave: MagicMock,
                        mock_holiday: MagicMock, mock_appt: MagicMock) -> None:
        """All checks pass for a valid slot."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor()
        mock_holiday.is_holiday.return_value = False
        mock_leave.find_by_doctor.return_value = []
        mock_schedule.find_by_doctor_and_day.return_value = make_schedule()
        mock_appt.find_by_doctor_and_date.return_value = []

        valid, msg = engine.validate_slot(1, FUTURE_DATE, time(10, 0), time(10, 30))
        assert valid is True
        assert msg == ""

    def test_doctor_not_found(self, engine: SchedulingEngine, mock_doctor: MagicMock) -> None:
        """Non-existent doctor fails."""
        mock_doctor.find_by_id_with_details.return_value = None
        valid, msg = engine.validate_slot(999, FUTURE_DATE, time(10, 0), time(10, 30))
        assert valid is False
        assert "not found" in msg.lower()

    def test_doctor_inactive(self, engine: SchedulingEngine, mock_doctor: MagicMock) -> None:
        """Inactive doctor fails."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor(status="Inactive")
        valid, msg = engine.validate_slot(1, FUTURE_DATE, time(10, 0), time(10, 30))
        assert valid is False
        assert "active" in msg.lower()

    def test_holiday(self, engine: SchedulingEngine, mock_doctor: MagicMock,
                     mock_holiday: MagicMock) -> None:
        """Hospital holiday fails."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor()
        mock_holiday.is_holiday.return_value = True
        valid, msg = engine.validate_slot(1, FUTURE_DATE, time(10, 0), time(10, 30))
        assert valid is False
        assert "holiday" in msg.lower()

    def test_on_leave(self, engine: SchedulingEngine, mock_doctor: MagicMock,
                      mock_holiday: MagicMock, mock_leave: MagicMock) -> None:
        """Doctor on leave fails."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor()
        mock_holiday.is_holiday.return_value = False
        mock_leave.find_by_doctor.return_value = [
            {
                "leave_start_date": FUTURE_DATE - timedelta(days=5),
                "leave_end_date": FUTURE_DATE + timedelta(days=5),
            }
        ]
        valid, msg = engine.validate_slot(1, FUTURE_DATE, time(10, 0), time(10, 30))
        assert valid is False
        assert "leave" in msg.lower()

    def test_no_schedule_for_day(self, engine: SchedulingEngine, mock_doctor: MagicMock,
                                 mock_holiday: MagicMock, mock_leave: MagicMock,
                                 mock_schedule: MagicMock) -> None:
        """Day with no schedule fails."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor()
        mock_holiday.is_holiday.return_value = False
        mock_leave.find_by_doctor.return_value = []
        mock_schedule.find_by_doctor_and_day.return_value = None
        valid, msg = engine.validate_slot(1, FUTURE_DATE, time(10, 0), time(10, 30))
        assert valid is False

    def test_outside_working_hours(self, engine: SchedulingEngine, mock_doctor: MagicMock,
                                    mock_holiday: MagicMock, mock_leave: MagicMock,
                                    mock_schedule: MagicMock) -> None:
        """Slot outside working hours fails."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor()
        mock_holiday.is_holiday.return_value = False
        mock_leave.find_by_doctor.return_value = []
        mock_schedule.find_by_doctor_and_day.return_value = make_schedule(
            start_time=time(9, 0), end_time=time(17, 0),
        )
        valid, msg = engine.validate_slot(1, FUTURE_DATE, time(8, 0), time(8, 30))
        assert valid is False
        assert "working hours" in msg.lower()

    def test_overlaps_lunch_break(self, engine: SchedulingEngine, mock_doctor: MagicMock,
                                   mock_holiday: MagicMock, mock_leave: MagicMock,
                                   mock_schedule: MagicMock) -> None:
        """Slot overlapping lunch break fails."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor()
        mock_holiday.is_holiday.return_value = False
        mock_leave.find_by_doctor.return_value = []
        mock_schedule.find_by_doctor_and_day.return_value = make_schedule(
            lunch_break_start=time(13, 0), lunch_break_end=time(14, 0),
        )
        mock_appt = engine._appt_repo
        mock_appt.find_by_doctor_and_date.return_value = []

        valid, msg = engine.validate_slot(1, FUTURE_DATE, time(13, 0), time(13, 30))
        assert valid is False
        assert "lunch" in msg.lower()

    def test_overlap_with_existing_booking(self, engine: SchedulingEngine,
                                            mock_doctor: MagicMock,
                                            mock_holiday: MagicMock,
                                            mock_leave: MagicMock,
                                            mock_schedule: MagicMock,
                                            mock_appt: MagicMock) -> None:
        """Slot overlapping an existing booking fails."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor()
        mock_holiday.is_holiday.return_value = False
        mock_leave.find_by_doctor.return_value = []
        mock_schedule.find_by_doctor_and_day.return_value = make_schedule()
        mock_appt.find_by_doctor_and_date.return_value = [
            make_appointment(start_time=time(10, 0), end_time=time(10, 30))
        ]
        valid, msg = engine.validate_slot(1, FUTURE_DATE, time(10, 0), time(10, 30))
        assert valid is False
        assert "already booked" in msg.lower()

    def test_daily_limit_exceeded(self, engine: SchedulingEngine,
                                   mock_doctor: MagicMock,
                                   mock_holiday: MagicMock,
                                   mock_leave: MagicMock,
                                   mock_schedule: MagicMock,
                                   mock_appt: MagicMock) -> None:
        """Exceeding daily max appointments fails."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor(max_appointments_per_day=2)
        mock_holiday.is_holiday.return_value = False
        mock_leave.find_by_doctor.return_value = []
        mock_schedule.find_by_doctor_and_day.return_value = make_schedule()
        # 2 existing appointments = limit reached
        mock_appt.find_by_doctor_and_date.return_value = [
            make_appointment(appointment_id=1, start_time=time(9, 0), end_time=time(9, 30)),
            make_appointment(appointment_id=2, start_time=time(11, 0), end_time=time(11, 30)),
        ]
        valid, msg = engine.validate_slot(1, FUTURE_DATE, time(14, 0), time(14, 30))
        assert valid is False
        assert "maximum" in msg.lower()

    def test_exclude_appointment_id(self, engine: SchedulingEngine,
                                     mock_doctor: MagicMock,
                                     mock_holiday: MagicMock,
                                     mock_leave: MagicMock,
                                     mock_schedule: MagicMock,
                                     mock_appt: MagicMock) -> None:
        """Excluding an appointment ID ignores its time range (for reschedule)."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor()
        mock_holiday.is_holiday.return_value = False
        mock_leave.find_by_doctor.return_value = []
        mock_schedule.find_by_doctor_and_day.return_value = make_schedule()
        mock_appt.find_by_doctor_and_date.return_value = [
            make_appointment(appointment_id=5, start_time=time(10, 0), end_time=time(10, 30))
        ]
        # Exclude appointment 5 — should pass even though it would overlap
        valid, msg = engine.validate_slot(
            1, FUTURE_DATE, time(10, 0), time(10, 30),
            exclude_appointment_id=5,
        )
        assert valid is True

    def test_past_date_rejected(self, engine: SchedulingEngine,
                                mock_doctor: MagicMock,
                                mock_holiday: MagicMock,
                                mock_leave: MagicMock,
                                mock_schedule: MagicMock,
                                mock_appt: MagicMock) -> None:
        """Booking a date in the past is rejected (final pipeline step)."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor()
        mock_holiday.is_holiday.return_value = False
        mock_leave.find_by_doctor.return_value = []
        mock_schedule.find_by_doctor_and_day.return_value = make_schedule()
        mock_appt.find_by_doctor_and_date.return_value = []

        yesterday = date.today() - timedelta(days=1)
        valid, msg = engine.validate_slot(1, yesterday, time(10, 0), time(10, 30))
        assert valid is False
        assert "past" in msg.lower()

    def test_existing_snapshot_avoids_requery(self, engine: SchedulingEngine,
                                              mock_doctor: MagicMock,
                                              mock_holiday: MagicMock,
                                              mock_leave: MagicMock,
                                              mock_schedule: MagicMock,
                                              mock_appt: MagicMock) -> None:
        """Passing existing_appointments skips the repository overlap query
        so callers can feed the FOR UPDATE locked snapshot."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor()
        mock_holiday.is_holiday.return_value = False
        mock_leave.find_by_doctor.return_value = []
        mock_schedule.find_by_doctor_and_day.return_value = make_schedule()

        existing = [
            make_appointment(appointment_id=5, start_time=time(10, 0), end_time=time(10, 30)),
        ]
        valid, msg = engine.validate_slot(
            1, FUTURE_DATE, time(11, 0), time(11, 30),
            existing_appointments=existing,
        )
        assert valid is True
        mock_appt.find_by_doctor_and_date.assert_not_called()


# ── Slot generation tests ─────────────────────────────────────


class TestGetAvailableSlots:
    """Tests for the get_available_slots method."""

    def test_returns_slots_on_working_day(self, engine: SchedulingEngine,
                                           mock_doctor: MagicMock,
                                           mock_holiday: MagicMock,
                                           mock_leave: MagicMock,
                                           mock_schedule: MagicMock,
                                           mock_appt: MagicMock) -> None:
        """A normal working day returns slots."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor()
        mock_holiday.is_holiday.return_value = False
        mock_leave.find_by_doctor.return_value = []
        mock_schedule.find_by_doctor_and_day.return_value = make_schedule()  # 9-5
        mock_appt.find_by_doctor_and_date.return_value = []

        slots = engine.get_available_slots(1, FUTURE_DATE, slot_duration=30)
        assert len(slots) > 0
        # 9:00 to 17:00 = 8 hours = 16 slots of 30 min
        assert len(slots) == 16

    def test_holiday_returns_empty(self, engine: SchedulingEngine,
                                    mock_doctor: MagicMock,
                                    mock_holiday: MagicMock) -> None:
        """Holiday returns empty list."""
        mock_holiday.is_holiday.return_value = True
        slots = engine.get_available_slots(1, FUTURE_DATE)
        assert slots == []

    def test_inactive_doctor_returns_empty(self, engine: SchedulingEngine,
                                            mock_doctor: MagicMock,
                                            mock_holiday: MagicMock) -> None:
        """Inactive doctor returns empty list."""
        mock_holiday.is_holiday.return_value = False
        mock_doctor.find_by_id_with_details.return_value = make_doctor(status="Inactive")
        slots = engine.get_available_slots(1, FUTURE_DATE)
        assert slots == []

    def test_leave_returns_empty(self, engine: SchedulingEngine,
                                  mock_doctor: MagicMock,
                                  mock_holiday: MagicMock,
                                  mock_leave: MagicMock) -> None:
        """Doctor on leave returns empty list."""
        mock_holiday.is_holiday.return_value = False
        mock_doctor.find_by_id_with_details.return_value = make_doctor()
        mock_leave.find_by_doctor.return_value = [
            {
                "leave_start_date": FUTURE_DATE - timedelta(days=5),
                "leave_end_date": FUTURE_DATE + timedelta(days=5),
            }
        ]
        slots = engine.get_available_slots(1, FUTURE_DATE)
        assert slots == []

    def test_no_schedule_returns_empty(self, engine: SchedulingEngine,
                                        mock_doctor: MagicMock,
                                        mock_holiday: MagicMock,
                                        mock_leave: MagicMock,
                                        mock_schedule: MagicMock) -> None:
        """No schedule for this day returns empty list."""
        mock_holiday.is_holiday.return_value = False
        mock_doctor.find_by_id_with_details.return_value = make_doctor()
        mock_leave.find_by_doctor.return_value = []
        mock_schedule.find_by_doctor_and_day.return_value = None
        slots = engine.get_available_slots(1, FUTURE_DATE)
        assert slots == []

    def test_booked_slots_marked_unavailable(self, engine: SchedulingEngine,
                                              mock_doctor: MagicMock,
                                              mock_holiday: MagicMock,
                                              mock_leave: MagicMock,
                                              mock_schedule: MagicMock,
                                              mock_appt: MagicMock) -> None:
        """Existing bookings are correctly marked as unavailable."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor()
        mock_holiday.is_holiday.return_value = False
        mock_leave.find_by_doctor.return_value = []
        mock_schedule.find_by_doctor_and_day.return_value = make_schedule()
        mock_appt.find_by_doctor_and_date.return_value = [
            make_appointment(start_time=time(10, 0), end_time=time(10, 30)),
        ]

        slots = engine.get_available_slots(1, FUTURE_DATE, slot_duration=30)
        # Slot starting at 10:00 should be unavailable
        slot_10 = next(s for s in slots if s["start_time"] == time(10, 0))
        assert slot_10["available"] is False


# ── Department / earliest slot tests ──────────────────────────


class TestAdvancedQueries:
    """Tests for department_slots, earliest_slot, is_date_available."""

    def test_department_slots(self, engine: SchedulingEngine,
                               mock_doctor: MagicMock,
                               mock_holiday: MagicMock,
                               mock_leave: MagicMock,
                               mock_schedule: MagicMock,
                               mock_appt: MagicMock) -> None:
        """Department slots returns slots grouped by doctor."""
        # Patch the doctor_repo.find_by_department to return 2 doctors
        with patch.object(engine._doctor_repo, "find_by_department") as find_dept:
            find_dept.return_value = [
                {"doctor_id": 1, "full_name": "Dr. A"},
                {"doctor_id": 2, "full_name": "Dr. B"},
            ]
            mock_doctor.find_by_id_with_details.side_effect = [
                make_doctor(doctor_id=1),
                make_doctor(doctor_id=2),
            ]
            mock_holiday.is_holiday.return_value = False
            mock_leave.find_by_doctor.return_value = []
            mock_schedule.find_by_doctor_and_day.return_value = make_schedule()
            mock_appt.find_by_doctor_and_date.return_value = []

            result = engine.get_department_slots(1, FUTURE_DATE, slot_duration=30)
            assert len(result) == 2
            assert 1 in result
            assert 2 in result

    def test_earliest_slot_finds_first_available(self, engine: SchedulingEngine,
                                                  mock_doctor: MagicMock,
                                                  mock_holiday: MagicMock,
                                                  mock_leave: MagicMock,
                                                  mock_schedule: MagicMock,
                                                  mock_appt: MagicMock) -> None:
        """find_earliest_slot finds the first available slot."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor()
        mock_holiday.is_holiday.return_value = False
        mock_leave.find_by_doctor.return_value = []
        mock_schedule.find_by_doctor_and_day.return_value = make_schedule()
        mock_appt.find_by_doctor_and_date.return_value = []

        result = engine.find_earliest_slot(
            1, from_date=FUTURE_DATE, preferred_duration=30, max_days_ahead=5,
        )
        assert result is not None
        assert result["date"] == FUTURE_DATE
        assert result["start_time"] == time(9, 0)  # First slot of the day

    def test_is_date_available(self, engine: SchedulingEngine,
                                mock_doctor: MagicMock,
                                mock_holiday: MagicMock,
                                mock_leave: MagicMock,
                                mock_schedule: MagicMock) -> None:
        """is_date_available returns True for a valid work day."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor()
        mock_holiday.is_holiday.return_value = False
        mock_leave.find_by_doctor.return_value = []
        mock_schedule.find_by_doctor_and_day.return_value = make_schedule()

        available, reason = engine.is_date_available(1, FUTURE_DATE)
        assert available is True
        assert reason is None

    def test_is_date_not_available_holiday(self, engine: SchedulingEngine,
                                            mock_doctor: MagicMock,
                                            mock_holiday: MagicMock) -> None:
        """is_date_available returns False for a holiday."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor()
        mock_holiday.is_holiday.return_value = True
        available, reason = engine.is_date_available(1, FUTURE_DATE)
        assert available is False


# ── Edge case tests ───────────────────────────────────────────


class TestEdgeCases:
    """Edge case tests for scheduling logic."""

    def test_lunch_break_splits_slots(self, engine: SchedulingEngine,
                                       mock_doctor: MagicMock,
                                       mock_holiday: MagicMock,
                                       mock_leave: MagicMock,
                                       mock_schedule: MagicMock,
                                       mock_appt: MagicMock) -> None:
        """Slots on either side of lunch break are available, but not during."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor()
        mock_holiday.is_holiday.return_value = False
        mock_leave.find_by_doctor.return_value = []
        mock_schedule.find_by_doctor_and_day.return_value = make_schedule(
            start_time=time(9, 0), end_time=time(12, 0),
            lunch_break_start=time(10, 30), lunch_break_end=time(11, 0),
        )
        mock_appt.find_by_doctor_and_date.return_value = []

        slots = engine.get_available_slots(1, FUTURE_DATE, slot_duration=15)
        # 9:00-12:00 = 180 min = 12 slots total. Lunch slots are marked unavailable, not removed.
        assert len(slots) == 12

        slot_1030 = next(s for s in slots if s["start_time"] == time(10, 30))
        assert slot_1030["available"] is False  # Overlaps lunch (10:30-11:00)

        slot_1045 = next(s for s in slots if s["start_time"] == time(10, 45))
        assert slot_1045["available"] is False  # Overlaps lunch

        slot_1100 = next(s for s in slots if s["start_time"] == time(11, 0))
        assert slot_1100["available"] is True  # After lunch ends

    def test_concurrent_bookings_marked_unavailable(self, engine: SchedulingEngine,
                                                     mock_doctor: MagicMock,
                                                     mock_holiday: MagicMock,
                                                     mock_leave: MagicMock,
                                                     mock_schedule: MagicMock,
                                                     mock_appt: MagicMock) -> None:
        """Multiple concurrent bookings on the same day."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor()
        mock_holiday.is_holiday.return_value = False
        mock_leave.find_by_doctor.return_value = []
        mock_schedule.find_by_doctor_and_day.return_value = make_schedule()
        mock_appt.find_by_doctor_and_date.return_value = [
            make_appointment(appointment_id=1, start_time=time(9, 0), end_time=time(10, 0)),
            make_appointment(appointment_id=2, start_time=time(11, 0), end_time=time(12, 0)),
            make_appointment(appointment_id=3, start_time=time(14, 0), end_time=time(15, 0)),
        ]

        slots = engine.get_available_slots(1, FUTURE_DATE, slot_duration=30)
        # 9:00-10:00 booked, 11:00-12:00 booked, 14:00-15:00 booked
        slot_9 = next(s for s in slots if s["start_time"] == time(9, 0))
        slot_930 = next(s for s in slots if s["start_time"] == time(9, 30))
        slot_11 = next(s for s in slots if s["start_time"] == time(11, 0))
        slot_14 = next(s for s in slots if s["start_time"] == time(14, 0))

        assert slot_9["available"] is False
        assert slot_930["available"] is False
        assert slot_11["available"] is False
        assert slot_14["available"] is False

        # But 10:00-11:00 should be available
        slot_10 = next(s for s in slots if s["start_time"] == time(10, 0))
        assert slot_10["available"] is True

    def test_daily_limit_exact_boundary(self, engine: SchedulingEngine,
                                         mock_doctor: MagicMock,
                                         mock_holiday: MagicMock,
                                         mock_leave: MagicMock,
                                         mock_schedule: MagicMock,
                                         mock_appt: MagicMock) -> None:
        """Exactly at daily limit (N existing = N max) — should fail."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor(max_appointments_per_day=3)
        mock_holiday.is_holiday.return_value = False
        mock_leave.find_by_doctor.return_value = []
        mock_schedule.find_by_doctor_and_day.return_value = make_schedule()
        mock_appt.find_by_doctor_and_date.return_value = [
            make_appointment(appointment_id=1, start_time=time(9, 0), end_time=time(9, 30)),
            make_appointment(appointment_id=2, start_time=time(10, 0), end_time=time(10, 30)),
            make_appointment(appointment_id=3, start_time=time(11, 0), end_time=time(11, 30)),
        ]

        valid, msg = engine.validate_slot(1, FUTURE_DATE, time(14, 0), time(14, 30))
        assert valid is False
        assert "maximum" in msg.lower()

    def test_reschedule_excludes_self_overlap(self, engine: SchedulingEngine,
                                               mock_doctor: MagicMock,
                                               mock_holiday: MagicMock,
                                               mock_leave: MagicMock,
                                               mock_schedule: MagicMock,
                                               mock_appt: MagicMock) -> None:
        """Rescheduling to the same time slot should pass (self-exclusion)."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor()
        mock_holiday.is_holiday.return_value = False
        mock_leave.find_by_doctor.return_value = []
        mock_schedule.find_by_doctor_and_day.return_value = make_schedule()
        # One existing appointment at 10:00-10:30
        mock_appt.find_by_doctor_and_date.return_value = [
            make_appointment(appointment_id=5, start_time=time(10, 0), end_time=time(10, 30)),
        ]

        # Rescheduling appointment 5 to its own slot without exclude should fail
        valid, msg = engine.validate_slot(1, FUTURE_DATE, time(10, 0), time(10, 30))
        assert valid is False  # Overlaps with itself if not excluded

        # With exclude_appointment_id=5, it should pass
        valid, msg = engine.validate_slot(
            1, FUTURE_DATE, time(10, 0), time(10, 30),
            exclude_appointment_id=5,
        )
        assert valid is True

    def test_schedule_not_available_day(self, engine: SchedulingEngine,
                                         mock_doctor: MagicMock,
                                         mock_holiday: MagicMock,
                                         mock_leave: MagicMock,
                                         mock_schedule: MagicMock) -> None:
        """Doctor with is_available=False on a day returns no slots."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor()
        mock_holiday.is_holiday.return_value = False
        mock_leave.find_by_doctor.return_value = []
        mock_schedule.find_by_doctor_and_day.return_value = make_schedule(is_available=False)

        available, _ = engine.is_date_available(1, FUTURE_DATE)
        assert available is False

        slots = engine.get_available_slots(1, FUTURE_DATE)
        assert slots == []

    def test_lunch_break_from_doctor_level(self, engine: SchedulingEngine,
                                            mock_doctor: MagicMock,
                                            mock_holiday: MagicMock,
                                            mock_leave: MagicMock,
                                            mock_schedule: MagicMock,
                                            mock_appt: MagicMock) -> None:
        """Lunch break from doctor-level field (not schedule-level)."""
        mock_doctor.find_by_id_with_details.return_value = make_doctor(
            lunch_break_start=time(12, 0), lunch_break_end=time(13, 0),
        )
        mock_holiday.is_holiday.return_value = False
        mock_leave.find_by_doctor.return_value = []
        mock_schedule.find_by_doctor_and_day.return_value = make_schedule(
            start_time=time(9, 0), end_time=time(17, 0),
            lunch_break_start=None, lunch_break_end=None,  # No schedule-level lunch
        )
        mock_appt.find_by_doctor_and_date.return_value = []

        slots = engine.get_available_slots(1, FUTURE_DATE, slot_duration=30)
        # 9:00-17:00 = 8 hours = 16 slots total. Lunch slots are marked unavailable, not removed.
        assert len(slots) == 16

        slot_12 = next(s for s in slots if s["start_time"] == time(12, 0))
        assert slot_12["available"] is False  # Doctor-level lunch (12:00-13:00)

        slot_1230 = next(s for s in slots if s["start_time"] == time(12, 30))
        assert slot_1230["available"] is False  # Overlaps lunch

        slot_13 = next(s for s in slots if s["start_time"] == time(13, 0))
        assert slot_13["available"] is True  # After lunch ends
