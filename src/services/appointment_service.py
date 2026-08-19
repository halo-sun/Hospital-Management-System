"""Appointment service – business orchestration for appointment management.

All scheduling-specific validation logic has been extracted into
:class:`src.services.scheduling_engine.SchedulingEngine`.  This service
focuses on **orchestration**: composing engine calls, managing audit
trail entries, and coordinating between repositories.

Single responsibility: coordinate the booking lifecycle.
"""
from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import date, time, datetime as dt

import mysql.connector

from src.repositories.appointment_repository import AppointmentRepository
from src.repositories.doctor_repository import DoctorRepository
from src.services.scheduling_engine import (
    SchedulingEngine,
    _to_date as _parse_date,
    _to_time as _parse_time,
)
from src.database.connection import DatabaseConnection
from src.config import app_config
from src.constants import AppointmentStatus

logger = logging.getLogger(__name__)


class _SlotUnavailable(Exception):
    """Internal signal: validation rejected the slot inside a transaction.

    Raised so the transaction rolls back (releasing row locks) and the
    message propagates to the caller as a normal rejection.
    """


class AppointmentService:
    """Handles appointment booking, retrieval, and modification.

    Delegates **all** slot validation and generation to
    ``SchedulingEngine``.  This class owns the lifecycle
    orchestration (book → validate → persist → log).
    """

    def __init__(self) -> None:
        """Initialize AppointmentService with repositories and scheduling engine."""
        self._appt_repo = AppointmentRepository()
        self._doctor_repo = DoctorRepository()
        self._engine = SchedulingEngine(
            appt_repo=self._appt_repo,
        )

    # ── Booking ────────────────────────────────────────────────

    def book_appointment(
        self, data: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[int]]:
        """Book a new appointment after full validation via SchedulingEngine.

        The validation and the INSERT run inside a **single transaction**
        that locks the doctor's existing appointments for the date
        (``SELECT ... FOR UPDATE``), so two concurrent attempts for the
        same doctor/date/slot cannot both pass the overlap check and
        both write.  A DB-level ``IntegrityError`` from the
        ``(doctor_id, appointment_date, start_time)`` unique backstop is
        translated to the same rejection a normal overlap failure
        produces.

        Args:
            data: Dictionary with patient_id, doctor_id, appointment_date,
                  start_time, end_time, created_by, and optional notes.

        Returns:
            Tuple of (success, message, appointment_id_or_None).
        """
        doctor_id = data.get("doctor_id")
        appt_date = data.get("appointment_date")
        start_time = data.get("start_time")
        end_time = data.get("end_time")

        validated_date = _parse_date(appt_date)
        validated_start = _parse_time(start_time)
        validated_end = _parse_time(end_time)

        if not all([doctor_id, validated_date, validated_start, validated_end]):
            return False, "Missing required booking fields.", None

        # ``appointments.created_by`` is a foreign key.  Never substitute a
        # sentinel that turns an actor error into a misleading DB conflict.
        if not data.get("created_by"):
            return False, "A signed-in user is required to book an appointment.", None

        data["appointment_date"] = validated_date
        data["start_time"] = validated_start
        data["end_time"] = validated_end
        data["status"] = AppointmentStatus.BOOKED

        try:
            with DatabaseConnection.transaction() as conn:
                # Lock the doctor's existing appointments for the date so a
                # concurrent booking for the same slot blocks until this
                # transaction commits, then re-checks against the new row.
                locked = self._appt_repo.find_by_doctor_and_date(
                    doctor_id, validated_date, for_update=True, conn=conn,
                )
                valid, msg = self._engine.validate_slot(
                    doctor_id, validated_date, validated_start, validated_end,
                    existing_appointments=locked,
                )
                if not valid:
                    raise _SlotUnavailable(msg)

                appt_id = self._appt_repo.create_appointment(data, conn=conn)
        except _SlotUnavailable as e:
            return False, str(e), None
        except mysql.connector.IntegrityError as e:
            # DB-level backstop for the unique (doctor, date, slot) key —
            # should be unreachable under FOR UPDATE, but never surface a
            # raw DB error and never double-book.
            logger.warning(
                "Booking integrity conflict: doctor=%s date=%s (errno=%s)",
                doctor_id, validated_date, e.errno,
            )
            if e.errno == 1062:
                return False, "This time slot is already booked.", None
            logger.warning("Booking integrity error: errno=%s", e.errno)
            return False, "Booking could not be saved due to a data-integrity error.", None
        except mysql.connector.Error as e:
            # InnoDB can choose either racer as a deadlock victim while both
            # sessions lock the same slot range.  The other transaction has
            # won (or will win) the slot, so expose the same safe, actionable
            # conflict message instead of a stack-trace-style system failure.
            if e.errno == 1213:
                logger.info("Booking deadlock resolved as slot conflict: doctor=%s date=%s", doctor_id, validated_date)
                return False, "This time slot is already booked.", None
            logger.warning("Booking database error: errno=%s", e.errno)
            return False, "Booking failed due to a database error. Please try again.", None
        except Exception:
            logger.exception(
                "Unexpected booking error: doctor=%s date=%s",
                doctor_id, validated_date,
            )
            return False, "Booking failed due to a system error. Please try again.", None

        logger.info(
            "Appointment booked: #%d doctor=%d date=%s %s-%s",
            appt_id, doctor_id, validated_date,
            validated_start.strftime("%H:%M"),
            validated_end.strftime("%H:%M"),
        )
        return True, f"Appointment booked successfully (#{appt_id}).", appt_id

    # ── Retrieval ──────────────────────────────────────────────

    def get_appointment(self, appointment_id: int) -> Optional[Dict[str, Any]]:
        """Get an appointment by ID with patient and doctor details.

        Args:
            appointment_id: The appointment ID.

        Returns:
            Appointment record or None.
        """
        return self._appt_repo.find_by_id_with_details(appointment_id)

    def get_upcoming_appointments(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all upcoming appointments from today onward.

        Args:
            limit: Maximum number of records.

        Returns:
            List of appointment records.
        """
        return self._appt_repo.find_all_upcoming(limit)

    def get_doctor_appointments(
        self, doctor_id: int, appointment_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get appointments for a doctor, optionally filtered by date.

        Args:
            doctor_id: The doctor ID.
            appointment_date: Optional date filter.

        Returns:
            List of appointment records.
        """
        if appointment_date:
            return self._appt_repo.find_by_doctor_and_date(doctor_id, appointment_date)
        return self._appt_repo.find_today_by_doctor(doctor_id)

    def get_patient_appointments(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get all appointments for a patient.

        Args:
            patient_id: The patient ID.

        Returns:
            List of appointment records.
        """
        return self._appt_repo.find_by_patient(patient_id)

    def get_today_appointments(self) -> List[Dict[str, Any]]:
        """Get all appointments scheduled for today across all doctors.

        Returns:
            List of today's appointment records.
        """
        today = dt.now().date()
        all_appts: List[Dict[str, Any]] = []
        doctors = self._doctor_repo.find_all_active()
        for doc in doctors:
            appts = self._appt_repo.find_by_doctor_and_date(doc["doctor_id"], today)
            all_appts.extend(appts)
        return all_appts

    def search_appointments(self, search_term: str) -> List[Dict[str, Any]]:
        """Search appointments by patient name, doctor name, or ID.

        Args:
            search_term: Text to search for.

        Returns:
            List of matching appointment records.
        """
        return self._appt_repo.search_appointments(search_term)

    # ── Modification ───────────────────────────────────────────

    def cancel_appointment(self, appointment_id: int) -> Tuple[bool, str]:
        """Cancel a booked appointment.

        Args:
            appointment_id: The appointment ID.

        Returns:
            Tuple of (success, message).
        """
        appt = self._appt_repo.find_by_id_with_details(appointment_id)
        if not appt:
            return False, "Appointment not found."
        if appt.get("status") != AppointmentStatus.BOOKED:
            return False, "Only booked appointments can be cancelled."

        self._appt_repo.cancel_appointment(appointment_id)
        logger.info("Appointment cancelled: #%d", appointment_id)
        return True, "Appointment cancelled successfully."

    def reschedule_appointment(
        self,
        appointment_id: int,
        new_date: date,
        new_start: time,
        new_end: time,
    ) -> Tuple[bool, str]:
        """Reschedule an existing appointment to a new date/time.

        **Never mutates the original row in place.**  A new ``Booked``
        row is inserted with ``rescheduled_from_id`` pointing at the
        original, and the original is marked ``Cancelled`` (a status
        update, never a delete) inside the same locked transaction.
        If validation of the new slot fails, nothing changes.

        Args:
            appointment_id: The appointment to reschedule.
            new_date: New appointment date.
            new_start: New start time.
            new_end: New end time.

        Returns:
            Tuple of (success, message).
        """
        appt = self._appt_repo.find_by_id_with_details(appointment_id)
        if not appt:
            return False, "Appointment not found."
        if appt.get("status") != AppointmentStatus.BOOKED:
            return False, "Only booked appointments can be rescheduled."

        new_date = _parse_date(new_date) or new_date
        new_start = _parse_time(new_start) or new_start
        new_end = _parse_time(new_end) or new_end

        try:
            with DatabaseConnection.transaction() as conn:
                locked = self._appt_repo.find_by_doctor_and_date(
                    appt["doctor_id"], new_date, for_update=True, conn=conn,
                )
                # Validate the new slot, excluding the original appointment
                # from both the overlap check and the daily cap.
                valid, msg = self._engine.validate_slot(
                    appt["doctor_id"], new_date, new_start, new_end,
                    exclude_appointment_id=appointment_id,
                    existing_appointments=locked,
                )
                if not valid:
                    raise _SlotUnavailable(msg)

                # New linked row — the original is left untouched except
                # for its status (never a hard delete).
                new_appt_id = self._appt_repo.create_appointment({
                    "patient_id": appt["patient_id"],
                    "doctor_id": appt["doctor_id"],
                    "appointment_date": new_date,
                    "start_time": new_start,
                    "end_time": new_end,
                    "status": AppointmentStatus.BOOKED,
                    "created_by": appt.get("created_by", 0),
                    "notes": appt.get("notes"),
                    "rescheduled_from_id": appointment_id,
                }, conn=conn)
                self._appt_repo.cancel_appointment(appointment_id, conn=conn)
        except _SlotUnavailable as e:
            return False, str(e)
        except mysql.connector.IntegrityError as e:
            logger.warning(
                "Reschedule integrity conflict: appt=%s new_date=%s (errno=%s)",
                appointment_id, new_date, e.errno,
            )
            return False, "This time slot is already booked."
        except Exception:
            logger.exception(
                "Unexpected reschedule error: appt=%s new_date=%s",
                appointment_id, new_date,
            )
            return False, "Rescheduling failed due to a system error. Please try again."

        logger.info(
            "Appointment rescheduled: #%d → new #%d (%s %s-%s)",
            appointment_id, new_appt_id, new_date,
            new_start.strftime("%H:%M"),
            new_end.strftime("%H:%M"),
        )
        return True, "Appointment rescheduled successfully."

    def update_status(
        self, appointment_id: int, status: str
    ) -> Tuple[bool, str]:
        """Update the status of an appointment.

        Args:
            appointment_id: The appointment ID.
            status: New status value.

        Returns:
            Tuple of (success, message).
        """
        valid_statuses = [
            AppointmentStatus.BOOKED,
            AppointmentStatus.COMPLETED,
            AppointmentStatus.CANCELLED,
            AppointmentStatus.NO_SHOW,
        ]
        if status not in valid_statuses:
            return False, f"Invalid status: {status}"

        appt = self._appt_repo.find_by_id_with_details(appointment_id)
        if not appt:
            return False, "Appointment not found."

        self._appt_repo.update_appointment(appointment_id, {"status": status})
        logger.info("Appointment status updated: #%d → %s", appointment_id, status)
        return True, f"Appointment status updated to {status}."

    # ── Slot queries (delegated to engine) ─────────────────────

    def get_available_slots(
        self, doctor_id: int, appointment_date: date,
        slot_duration: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get available time slots for a doctor on a given date.

        Delegates to ``SchedulingEngine.get_available_slots``.

        Args:
            doctor_id: The doctor ID.
            appointment_date: The date to generate slots for.
            slot_duration: Optional slot length override.

        Returns:
            List of slot dicts.
        """
        return self._engine.get_available_slots(
            doctor_id, appointment_date, slot_duration=slot_duration,
        )

    def get_department_slots(
        self, department_id: int, appointment_date: date,
        slot_duration: Optional[int] = None,
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Get available slots for all active doctors in a department.

        Args:
            department_id: The department ID.
            appointment_date: The date to check.
            slot_duration: Optional slot length override.

        Returns:
            Dict mapping doctor_id → list of slot dicts.
        """
        return self._engine.get_department_slots(
            department_id, appointment_date, slot_duration=slot_duration,
        )

    def find_earliest_slot(
        self,
        doctor_id: int,
        from_date: Optional[date] = None,
        max_days_ahead: int = 30,
    ) -> Optional[Dict[str, Any]]:
        """Find the earliest available slot for a doctor.

        Args:
            doctor_id: The doctor ID.
            from_date: Start searching from this date (default: today).
            max_days_ahead: Maximum days to search.

        Returns:
            Slot dict or None.
        """
        start = from_date or dt.now().date()
        return self._engine.find_earliest_slot(
            doctor_id, start, max_days_ahead=max_days_ahead,
        )

    def is_date_available(self, doctor_id: int, appt_date: date) -> Tuple[bool, Optional[str]]:
        """Quick availability check for a doctor on a date.

        Args:
            doctor_id: The doctor ID.
            appt_date: The date to check.

        Returns:
            Tuple of (available, reason).
        """
        return self._engine.is_date_available(doctor_id, appt_date)

    # ── Statistics ─────────────────────────────────────────────

    def count_today(self) -> int:
        """Count today's total appointments.

        Returns:
            Number of appointments today.
        """
        return self._appt_repo.count_today()

    def get_status_counts(self) -> List[Dict[str, Any]]:
        """Get appointment counts grouped by status.

        Returns:
            List of dicts with 'status' and 'count'.
        """
        return self._appt_repo.count_by_status()

    def get_department_counts(self) -> List[Dict[str, Any]]:
        """Get appointment counts grouped by department.

        Returns:
            List of dicts with 'department_name' and 'count'.
        """
        return self._appt_repo.count_by_department()

    def get_hourly_distribution(self) -> List[Dict[str, Any]]:
        """Get appointment counts grouped by hour of day.

        Returns:
            List of dicts with 'hour' and 'count'.
        """
        return self._appt_repo.count_by_hour()

    def get_date_range_counts(
        self, start_date: date, end_date: date,
    ) -> List[Dict[str, Any]]:
        """Get daily appointment counts within a date range.

        Args:
            start_date: Range start.
            end_date: Range end.

        Returns:
            List of dicts with 'appointment_date' and 'count'.
        """
        return self._appt_repo.count_by_date_range(start_date, end_date)

    def get_doctor_workload(self) -> List[Dict[str, Any]]:
        """Get appointment counts per doctor.

        Returns:
            List of dicts with doctor info and appointment count.
        """
        return self._appt_repo.get_doctor_workload()
