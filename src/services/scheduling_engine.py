"""Reusable scheduling engine for appointment time-slot management.

This module is the **single source of truth** for all scheduling
validation logic.  It has zero GUI dependencies and can be used
by any layer (service, CLI, API) to validate and generate slots.

Design principles:
* Every validation rule is an independent, testable method.
* The engine works with plain dicts — no model instances required.
* Time parsing is centralised so callers never need to worry about
  ``str`` vs ``datetime.time`` vs ``datetime.datetime`` differences.
* Slot generation uses an interval-list algorithm (O(n log n))
  instead of naive minute-by-minute iteration.

Usage::

    engine = SchedulingEngine(repos)
    valid, msg = engine.validate_slot(doctor_id, date, start, end)
    slots = engine.get_available_slots(doctor_id, date)
    dept_slots = engine.get_department_slots(department_id, date)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import date, datetime, time, timedelta

from src.config import app_config
from src.constants import AppointmentStatus
from src.repositories.appointment_repository import AppointmentRepository
from src.repositories.doctor_repository import (
    DoctorRepository,
    DoctorScheduleRepository,
    DoctorLeaveRepository,
)
from src.repositories.audit_repository import HospitalHolidayRepository

logger = logging.getLogger(__name__)


# ── Type alias ────────────────────────────────────────────────

SlotDict = Dict[str, Any]
"""A single time-slot dict with keys ``start_time``, ``end_time``, ``available``."""


# ── Public engine ─────────────────────────────────────────────

class SchedulingEngine:
    """Pure scheduling logic — no GUI, no controllers, no services.

    Every method accepts and returns plain Python types so the
    engine is trivially testable and framework-independent.
    """

    def __init__(
        self,
        appt_repo: Optional[AppointmentRepository] = None,
        doctor_repo: Optional[DoctorRepository] = None,
        schedule_repo: Optional[DoctorScheduleRepository] = None,
        leave_repo: Optional[DoctorLeaveRepository] = None,
        holiday_repo: Optional[HospitalHolidayRepository] = None,
    ) -> None:
        """Initialise the engine with optional repository overrides.

        Args:
            appt_repo: Appointment repository. Created automatically if omitted.
            doctor_repo: Doctor repository. Created automatically if omitted.
            schedule_repo: Doctor schedule repository. Created automatically if omitted.
            leave_repo: Doctor leave repository. Created automatically if omitted.
            holiday_repo: Hospital holiday repository. Created automatically if omitted.
        """
        self._appt_repo = appt_repo or AppointmentRepository()
        self._doctor_repo = doctor_repo or DoctorRepository()
        self._schedule_repo = schedule_repo or DoctorScheduleRepository()
        self._leave_repo = leave_repo or DoctorLeaveRepository()
        self._holiday_repo = holiday_repo or HospitalHolidayRepository()

    # ── Public API ─────────────────────────────────────────────

    def validate_slot(
        self,
        doctor_id: int,
        appt_date: date,
        start_time: time,
        end_time: time,
        exclude_appointment_id: Optional[int] = None,
        existing_appointments: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[bool, str]:
        """Validate whether a single time slot is bookable.

        Runs **all** checks in order::

            1. Doctor exists and is active
            2. Date is not a hospital holiday
            3. Doctor is not on leave for the date
            4. Day-of-week is in the doctor's weekly schedule
            5. Slot falls within the doctor's working hours
            6. Slot does not overlap with lunch break
            7. Slot does not overlap with existing bookings
            8. Daily appointment limit not exceeded
            9. Date is not in the past

        Args:
            doctor_id: The doctor to check.
            appt_date: The appointment date.
            start_time: Proposed start time.
            end_time: Proposed end time.
            exclude_appointment_id: If set, ignore this appointment's time
                range when checking for overlaps (useful for rescheduling).
            existing_appointments: Optional pre-fetched list of the doctor's
                appointments for *appt_date*.  Callers running inside a
                transaction can pass rows locked with ``SELECT ... FOR UPDATE``
                so the overlap and daily-cap checks read the locked snapshot
                instead of issuing a fresh (unlocked) query.

        Returns:
            Tuple of (is_valid, error_or_empty_message).
        """
        # 1. Doctor check
        doctor = self._doctor_repo.find_by_id_with_details(doctor_id)
        if not doctor:
            return False, "Doctor not found."
        if doctor.get("status") != "Active":
            return False, "Doctor is not currently active."

        # 2. Holiday check
        if self._holiday_repo.is_holiday(appt_date):
            return False, "Cannot book on a hospital holiday."

        # 3. Leave check
        leave_error = self._check_leave(doctor_id, appt_date)
        if leave_error:
            return False, leave_error

        # 4. Schedule / working hours / lunch checks (pass doctor to avoid re-query)
        day_error = self._check_day_schedule(
            doctor_id, appt_date, start_time, end_time, doctor=doctor,
        )
        if day_error:
            return False, day_error

        # 5. Overlap check (uses the locked snapshot when provided)
        overlap_error = self._check_overlap(
            doctor_id, appt_date, start_time, end_time,
            exclude_appointment_id=exclude_appointment_id,
            existing=existing_appointments,
        )
        if overlap_error:
            return False, overlap_error

        # 6. Daily limit check (doctor already fetched; excludes the slot being moved)
        limit_error = self._check_daily_limit(
            doctor_id, appt_date, doctor=doctor,
            existing=existing_appointments,
            exclude_appointment_id=exclude_appointment_id,
        )
        if limit_error:
            return False, limit_error

        # 7. Past-date check
        if appt_date < date.today():
            return False, "Cannot book an appointment in the past."

        return True, ""

    def get_available_slots(
        self,
        doctor_id: int,
        appt_date: date,
        slot_duration: Optional[int] = None,
    ) -> List[SlotDict]:
        """Generate available time slots for a doctor on a given date.

        Uses an **interval-list** approach — collects all booked
        time ranges, then walks through working hours to produce
        non-overlapping available slots.

        Args:
            doctor_id: The doctor ID.
            appt_date: The date to generate slots for.
            slot_duration: Slot length in minutes (default: from config).

        Returns:
            List of ``SlotDict`` with ``start_time``, ``end_time``,
            ``available`` keys.  Returns an empty list if the doctor
            is unavailable (leave, holiday, no schedule).
        """
        duration = timedelta(minutes=slot_duration or app_config.default_slot_duration)
        slots: List[SlotDict] = []

        # Holiday
        if self._holiday_repo.is_holiday(appt_date):
            return slots

        # Doctor exists and is active
        doctor = self._doctor_repo.find_by_id_with_details(doctor_id)
        if not doctor or doctor.get("status") != "Active":
            return slots

        # Leave
        if self._check_leave(doctor_id, appt_date):
            return slots

        # Schedule for day-of-week
        schedule = self._get_schedule_for_date(doctor_id, appt_date)
        if not schedule:
            return slots

        sched_start = _to_time(schedule["start_time"])
        sched_end = _to_time(schedule["end_time"])
        lunch_start, lunch_end = _resolve_lunch(schedule, doctor)

        # Collect booked intervals as (start, end) pairs
        booked = self._get_booked_intervals(doctor_id, appt_date)

        # Walk through working hours in slot_duration steps
        current = datetime.combine(appt_date, sched_start)
        end_dt = datetime.combine(appt_date, sched_end)

        while current + duration <= end_dt:
            slot_start = current.time()
            slot_end = (current + duration).time()

            available = True

            # Lunch break
            if lunch_start and lunch_end:
                if _overlaps(slot_start, slot_end, lunch_start, lunch_end):
                    available = False

            # Existing bookings
            if available:
                for b_start, b_end in booked:
                    if _overlaps(slot_start, slot_end, b_start, b_end):
                        available = False
                        break

            slots.append({
                "start_time": slot_start,
                "end_time": slot_end,
                "available": available,
            })
            current += duration

        return slots

    def get_department_slots(
        self,
        department_id: int,
        appt_date: date,
        slot_duration: Optional[int] = None,
    ) -> Dict[int, List[SlotDict]]:
        """Get available slots for **all active doctors** in a department.

        Useful for department-level booking views.

        Args:
            department_id: The department ID.
            appt_date: The date to check.
            slot_duration: Optional slot length override.

        Returns:
            Dict mapping ``doctor_id`` → list of ``SlotDict``.
            Only includes doctors who have at least one available slot.
        """
        doctors = self._doctor_repo.find_by_department(department_id)

        result: Dict[int, List[SlotDict]] = {}
        for doc in doctors:
            doc_id = doc["doctor_id"]
            slots = self.get_available_slots(doc_id, appt_date, slot_duration)
            if slots:
                result[doc_id] = slots
        return result

    def is_date_available(
        self,
        doctor_id: int,
        appt_date: date,
    ) -> Tuple[bool, Optional[str]]:
        """Quick check: is a doctor available at all on a given date?

        Args:
            doctor_id: The doctor ID.
            appt_date: The date to check.

        Returns:
            Tuple of (available, reason_if_not).
        """
        doctor = self._doctor_repo.find_by_id_with_details(doctor_id)
        if not doctor:
            return False, "Doctor not found."
        if doctor.get("status") != "Active":
            return False, "Doctor is not active."

        if self._holiday_repo.is_holiday(appt_date):
            return False, "Hospital holiday."

        leave_error = self._check_leave(doctor_id, appt_date)
        if leave_error:
            return False, leave_error

        schedule = self._get_schedule_for_date(doctor_id, appt_date)
        if not schedule:
            return False, "Doctor is not scheduled on this day."

        return True, None

    def find_earliest_slot(
        self,
        doctor_id: int,
        from_date: date,
        preferred_duration: Optional[int] = None,
        max_days_ahead: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Find the earliest available slot for a doctor within a date range.

        Useful for offering alternative suggestions when a slot is unavailable.

        Args:
            doctor_id: The doctor ID.
            from_date: Start searching from this date.
            preferred_duration: Desired slot length in minutes.
            max_days_ahead: Maximum number of days to search.
                Defaults to ``app_config.MAX_BOOKING_DAYS_AHEAD``.

        Returns:
            Dict with ``date``, ``start_time``, ``end_time`` keys, or ``None``.
        """
        duration = preferred_duration or app_config.default_slot_duration
        if max_days_ahead is None:
            max_days_ahead = app_config.MAX_BOOKING_DAYS_AHEAD

        for day_offset in range(max_days_ahead):
            check_date = from_date + timedelta(days=day_offset)
            slots = self.get_available_slots(doctor_id, check_date, slot_duration=duration)
            for slot in slots:
                if slot["available"]:
                    return {
                        "date": check_date,
                        "start_time": slot["start_time"],
                        "end_time": slot["end_time"],
                    }
        return None

    # ── Internal helpers ───────────────────────────────────────

    def _check_leave(self, doctor_id: int, appt_date: date) -> Optional[str]:
        """Check if the doctor is on leave for the given date.

        Returns:
            Error message string if on leave, ``None`` otherwise.
        """
        leaves = self._leave_repo.find_by_doctor(doctor_id)
        for leave in leaves:
            ls = _to_date(leave["leave_start_date"])
            le = _to_date(leave["leave_end_date"])
            if ls <= appt_date <= le:
                return "Doctor is on leave for the selected date."
        return None

    def _check_day_schedule(
        self,
        doctor_id: int,
        appt_date: date,
        start_time: time,
        end_time: time,
        doctor: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Check that the slot falls within the doctor's weekly schedule.

        Validates day-of-week presence, working hours, and lunch break.
        Accepts an optional *doctor* dict to avoid a redundant DB query
        when the caller has already fetched the doctor record.

        Returns:
            Error message string or ``None``.
        """
        schedule = self._get_schedule_for_date(doctor_id, appt_date)
        if not schedule:
            return "Doctor is not available on this day of the week."

        sched_start = _to_time(schedule["start_time"])
        sched_end = _to_time(schedule["end_time"])
        if not sched_start or not sched_end:
            return "Doctor has no working hours configured for this day."

        if start_time < sched_start or end_time > sched_end:
            return (
                f"Slot must fall within working hours "
                f"({sched_start.strftime('%H:%M')} - {sched_end.strftime('%H:%M')})."
            )

        # Lunch break — prefer schedule-level lunch, fall back to doctor-level
        lunch_start, lunch_end = _resolve_lunch(schedule, doctor or {})
        if lunch_start and lunch_end and _overlaps(start_time, end_time, lunch_start, lunch_end):
            return "Slot overlaps with lunch break."

        return None

    def _check_overlap(
        self,
        doctor_id: int,
        appt_date: date,
        start_time: time,
        end_time: time,
        exclude_appointment_id: Optional[int] = None,
        existing: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[str]:
        """Check for double-booking with existing appointments.

        Args:
            doctor_id: The doctor ID.
            appt_date: The appointment date.
            start_time: Proposed start.
            end_time: Proposed end.
            exclude_appointment_id: Appointment to ignore (rescheduling).
            existing: Optional pre-fetched appointment rows (e.g. the
                FOR UPDATE snapshot from the caller's transaction).

        Returns:
            Error message if overlap detected, ``None`` otherwise.
        """
        if existing is None:
            existing = self._appt_repo.find_by_doctor_and_date(doctor_id, appt_date)
        for appt in existing:
            if appt.get("status") not in (AppointmentStatus.BOOKED, AppointmentStatus.COMPLETED):
                continue
            if exclude_appointment_id and appt.get("appointment_id") == exclude_appointment_id:
                continue
            exist_start = _to_time(appt["start_time"])
            exist_end = _to_time(appt["end_time"])
            if exist_start and exist_end and _overlaps(start_time, end_time, exist_start, exist_end):
                return "This time slot is already booked."
        return None

    def _check_daily_limit(
        self,
        doctor_id: int,
        appt_date: date,
        doctor: Optional[Dict[str, Any]] = None,
        existing: Optional[List[Dict[str, Any]]] = None,
        exclude_appointment_id: Optional[int] = None,
    ) -> Optional[str]:
        """Check that the daily appointment count is not exceeded.

        Args:
            doctor_id: The doctor ID.
            appt_date: The appointment date.
            doctor: Optional pre-fetched doctor record.
            existing: Optional pre-fetched appointment rows (FOR UPDATE snapshot).
            exclude_appointment_id: Appointment to exclude from the count
                (the original row when rescheduling on the same day).

        Returns:
            Error message if limit reached, ``None`` otherwise.
        """
        if not doctor:
            doctor = self._doctor_repo.find_by_id_with_details(doctor_id)
        max_per_day = (doctor or {}).get("max_appointments_per_day") or app_config.max_appointments_per_day
        if existing is None:
            existing = self._appt_repo.find_by_doctor_and_date(doctor_id, appt_date)
        count = sum(
            1 for appt in existing
            if not (exclude_appointment_id and appt.get("appointment_id") == exclude_appointment_id)
        )
        if count >= max_per_day:
            return f"Doctor has reached the maximum of {max_per_day} appointments for this day."
        return None

    def _get_schedule_for_date(
        self,
        doctor_id: int,
        appt_date: date,
    ) -> Optional[Dict[str, Any]]:
        """Get the doctor's schedule entry for the day-of-week of *appt_date*.

        Converts Python weekday (Mon=0) to SQL weekday (Sun=0).

        Args:
            doctor_id: The doctor ID.
            appt_date: The date to get the schedule for.

        Returns:
            Schedule record or ``None``.
        """
        sql_day = (appt_date.weekday() + 1) % 7  # Mon=0 → Sun=0 conversion
        schedule = self._schedule_repo.find_by_doctor_and_day(doctor_id, sql_day)
        if not schedule or not schedule.get("is_available", True):
            return None
        return schedule

    def _get_booked_intervals(
        self,
        doctor_id: int,
        appt_date: date,
    ) -> List[Tuple[time, time]]:
        """Get booked time intervals as (start, end) pairs for overlap checks.

        This is the **interval-list** data structure that makes slot
        generation O(n log n) instead of O(n × m).

        Args:
            doctor_id: The doctor ID.
            appt_date: The date to query.

        Returns:
            List of (start_time, end_time) tuples, sorted by start time.
        """
        existing = self._appt_repo.find_by_doctor_and_date(doctor_id, appt_date)
        intervals = []
        for appt in existing:
            if appt.get("status") not in (AppointmentStatus.BOOKED, AppointmentStatus.COMPLETED):
                continue
            es = _to_time(appt["start_time"])
            ee = _to_time(appt["end_time"])
            if es and ee:
                intervals.append((es, ee))
        # Sort by start time for faster lookups in interval-list
        intervals.sort(key=lambda pair: _time_to_minutes(pair[0]))
        return intervals


# ── Pure helper functions ─────────────────────────────────────


def _to_time(value: Any) -> Optional[time]:
    """Safely convert a value to ``datetime.time``.

    Handles ``datetime.time``, ``datetime.datetime``, and ISO ``HH:MM`` /
    ``HH:MM:SS`` string formats.

    Args:
        value: The value to convert.

    Returns:
        A ``time`` object or ``None``.
    """
    if value is None:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, timedelta):
        # mysql-connector returns TIME columns as datetime.timedelta.
        total = int(value.total_seconds())
        h, rem = divmod(total, 3600)
        m, sec = divmod(rem, 60)
        return time(h, m, sec)
    if isinstance(value, str):
        for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M:%S %p"):
            try:
                return datetime.strptime(value.strip(), fmt).time()
            except ValueError:
                continue
        logger.warning("Unable to parse time string: %s", value)
        return None
    if hasattr(value, "hour"):
        return time(value.hour, value.minute, value.second)
    return None


def _to_date(value: Any) -> Optional[date]:
    """Safely convert a value to ``datetime.date``.

    Args:
        value: The value to convert.

    Returns:
        A ``date`` object or ``None``.
    """
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
        logger.warning("Unable to parse date string: %s", value)
        return None
    return None


def _time_to_minutes(t: time) -> int:
    """Convert a ``time`` to minutes since midnight.

    Args:
        t: The time to convert.

    Returns:
        Integer minutes (0–1439).
    """
    return t.hour * 60 + t.minute


def _resolve_lunch(
    schedule: Dict[str, Any],
    doctor: Dict[str, Any],
) -> Tuple[Optional[time], Optional[time]]:
    """Resolve lunch break times from schedule- or doctor-level data.

    Prefers schedule-level fields; falls back to doctor-level fields.
    This is used in two places (``_check_day_schedule`` and
    ``get_available_slots``) so the fallback logic lives here once.

    Args:
        schedule: The doctor's weekly schedule dict.
        doctor: The doctor record dict.

    Returns:
        Tuple of (lunch_start, lunch_end) — either or both may be ``None``.
    """
    return (
        _to_time(schedule.get("lunch_break_start") or doctor.get("lunch_break_start")),
        _to_time(schedule.get("lunch_break_end") or doctor.get("lunch_break_end")),
    )


def _overlaps(
    a_start: time, a_end: time,
    b_start: time, b_end: time,
) -> bool:
    """Check whether two time ranges overlap.

    Args:
        a_start: Start of range A.
        a_end: End of range A.
        b_start: Start of range B.
        b_end: End of range B.

    Returns:
        ``True`` if the ranges overlap.
    """
    return a_start < b_end and a_end > b_start
