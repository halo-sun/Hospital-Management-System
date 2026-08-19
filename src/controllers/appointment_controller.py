"""Appointment controller – coordinates appointment booking and management."""
import logging
from typing import Optional, Dict, Any, Tuple, List
from datetime import date, time
from src.services.appointment_service import AppointmentService
from src.services.audit_service import AuditService
from src.constants import AuditAction, Role
from src.auth.rbac import require_role
from src.controllers.auth_controller import AuthController

logger = logging.getLogger(__name__)


class AppointmentController:
    """Handles appointment requests from the GUI layer."""

    def __init__(self, auth_ctrl: Optional[AuthController] = None) -> None:
        """Initialize AppointmentController with required services.

        Args:
            auth_ctrl: Auth controller providing the current role
                (used by the RBAC decorator).
        """
        self._auth_ctrl = auth_ctrl
        self._appointment_service = AppointmentService()
        self._audit_service = AuditService()

    @property
    def _current_role(self) -> Optional[str]:
        """Return the logged-in user's role for RBAC checks."""
        if self._auth_ctrl is None:
            return None
        return self._auth_ctrl.current_role

    # ── Input validation ───────────────────────────────────────

    @staticmethod
    def validate_booking_data(data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate appointment booking form data.

        Args:
            data: Dictionary of appointment fields.

        Returns:
            Tuple of (valid, error_message).
        """
        if not data.get("patient_id"):
            return False, "Patient is required."
        if not data.get("doctor_id"):
            return False, "Doctor is required."
        if not data.get("appointment_date"):
            return False, "Appointment date is required."
        if not data.get("start_time"):
            return False, "Start time is required."
        if not data.get("end_time"):
            return False, "End time is required."

        start = data.get("start_time")
        end = data.get("end_time")
        if isinstance(start, str):
            try:
                start = datetime.strptime(start, "%H:%M").time()
            except ValueError:
                return False, "Invalid start time format."
        if isinstance(end, str):
            try:
                end = datetime.strptime(end, "%H:%M").time()
            except ValueError:
                return False, "Invalid end time format."

        if start and end and start >= end:
            return False, "Start time must be before end time."

        return True, ""

    # ── Booking ────────────────────────────────────────────────

    @require_role(Role.RECEPTIONIST, Role.ADMIN)
    def book_appointment(
        self, data: Dict[str, Any], user_id: Optional[int] = None
    ) -> Tuple[bool, str, Optional[int]]:
        """Book a new appointment.

        Args:
            data: Appointment fields.
            user_id: The user booking the appointment.

        Returns:
            Tuple of (success, message, appointment_id_or_None).
        """
        valid, msg = self.validate_booking_data(data)
        if not valid:
            return False, msg, None

        if not user_id:
            return False, "A signed-in user is required to book an appointment.", None
        data["created_by"] = user_id
        success, message, appt_id = self._appointment_service.book_appointment(data)

        if success and appt_id:
            self._audit_service.log(
                AuditAction.APPOINTMENT_BOOK,
                user_id=user_id,
                target_entity="Appointment",
                target_id=str(appt_id),
                new_values={
                    "patient_id": data.get("patient_id"),
                    "doctor_id": data.get("doctor_id"),
                    "date": str(data.get("appointment_date")),
                },
            )
        return success, message, appt_id

    # ── Retrieval ──────────────────────────────────────────────

    @require_role(Role.RECEPTIONIST, Role.ADMIN, Role.DOCTOR)
    def get_appointment(self, appointment_id: int) -> Optional[Dict[str, Any]]:
        """Get an appointment by ID.

        Args:
            appointment_id: The appointment ID.

        Returns:
            Appointment record or None.
        """
        return self._appointment_service.get_appointment(appointment_id)

    @require_role(Role.RECEPTIONIST, Role.ADMIN)
    def get_upcoming_appointments(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get upcoming appointments.

        Args:
            limit: Maximum number of records.

        Returns:
            List of appointment records.
        """
        return self._appointment_service.get_upcoming_appointments(limit)

    @require_role(Role.DOCTOR, Role.ADMIN)
    def get_doctor_appointments(
        self, doctor_id: int, appointment_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get appointments for a doctor.

        Args:
            doctor_id: The doctor ID.
            appointment_date: Optional date filter.

        Returns:
            List of appointment records.
        """
        return self._appointment_service.get_doctor_appointments(doctor_id, appointment_date)

    @require_role(Role.RECEPTIONIST, Role.ADMIN, Role.DOCTOR)
    def get_patient_appointments(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get appointments for a patient.

        Args:
            patient_id: The patient ID.

        Returns:
            List of appointment records.
        """
        return self._appointment_service.get_patient_appointments(patient_id)

    @require_role(Role.RECEPTIONIST, Role.ADMIN)
    def get_today_appointments(self) -> List[Dict[str, Any]]:
        """Get all of today's appointments.

        Returns:
            List of appointment records.
        """
        return self._appointment_service.get_today_appointments()

    @require_role(Role.RECEPTIONIST, Role.ADMIN)
    def search_appointments(self, search_term: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Search appointments.

        Args:
            search_term: Text to search for.

        Returns:
            Tuple of (success, message, results).
        """
        if not search_term or not search_term.strip():
            return False, "Search term is required.", []

        results = self._appointment_service.search_appointments(search_term.strip())
        return True, f"{len(results)} appointment(s) found.", results

    # ── Modification ───────────────────────────────────────────

    @require_role(Role.RECEPTIONIST, Role.ADMIN)
    def cancel_appointment(self, appointment_id: int, user_id: Optional[int] = None) -> Tuple[bool, str]:
        """Cancel an appointment.

        Args:
            appointment_id: The appointment ID.
            user_id: The user performing the cancellation.

        Returns:
            Tuple of (success, message).
        """
        success, message = self._appointment_service.cancel_appointment(appointment_id)
        if success:
            self._audit_service.log(
                AuditAction.APPOINTMENT_CANCEL,
                user_id=user_id,
                target_entity="Appointment",
                target_id=str(appointment_id),
            )
        return success, message

    @require_role(Role.RECEPTIONIST, Role.ADMIN)
    def reschedule_appointment(
        self,
        appointment_id: int,
        new_date: date,
        new_start: time,
        new_end: time,
        user_id: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """Reschedule an appointment.

        Args:
            appointment_id: The appointment ID.
            new_date: New date.
            new_start: New start time.
            new_end: New end time.
            user_id: The user performing the reschedule.

        Returns:
            Tuple of (success, message).
        """
        success, message = self._appointment_service.reschedule_appointment(
            appointment_id, new_date, new_start, new_end
        )
        if success:
            self._audit_service.log(
                AuditAction.APPOINTMENT_RESCHEDULE,
                user_id=user_id,
                target_entity="Appointment",
                target_id=str(appointment_id),
                new_values={"date": str(new_date), "start": str(new_start), "end": str(new_end)},
            )
        return success, message

    @require_role(Role.RECEPTIONIST, Role.ADMIN)
    def update_status(
        self, appointment_id: int, status: str
    ) -> Tuple[bool, str]:
        """Update an appointment's status.

        Args:
            appointment_id: The appointment ID.
            status: New status value.

        Returns:
            Tuple of (success, message).
        """
        return self._appointment_service.update_status(appointment_id, status)

    # ── Slots ──────────────────────────────────────────────────

    @require_role(Role.RECEPTIONIST, Role.ADMIN)
    def get_available_slots(
        self, doctor_id: int, appointment_date: date
    ) -> List[Dict[str, Any]]:
        """Get available time slots for a doctor on a date.

        Args:
            doctor_id: The doctor ID.
            appointment_date: The date to check.

        Returns:
            List of slot dicts with 'start_time', 'end_time', 'available'.
        """
        return self._appointment_service.get_available_slots(doctor_id, appointment_date)

    @require_role(Role.RECEPTIONIST, Role.ADMIN)
    def get_department_slots(
        self, department_id: int, appointment_date: date
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Get available slots for all active doctors in a department.

        Args:
            department_id: The department ID.
            appointment_date: The date to check.

        Returns:
            Dict mapping doctor_id → list of slot dicts.
        """
        return self._appointment_service.get_department_slots(department_id, appointment_date)

    @require_role(Role.RECEPTIONIST, Role.ADMIN)
    def find_earliest_slot(
        self, doctor_id: int, from_date: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        """Find the earliest available slot for a doctor.

        Args:
            doctor_id: The doctor ID.
            from_date: Start searching from this date.

        Returns:
            Slot dict with 'date', 'start_time', 'end_time' or None.
        """
        return self._appointment_service.find_earliest_slot(doctor_id, from_date)

    # ── Stats ──────────────────────────────────────────────────

    @require_role(Role.ADMIN)
    def get_status_counts(self) -> List[Dict[str, Any]]:
        """Get appointment counts by status.

        Returns:
            List of dicts with 'status' and 'count'.
        """
        return self._appointment_service.get_status_counts()

    @require_role(Role.ADMIN)
    def get_department_counts(self) -> List[Dict[str, Any]]:
        """Get appointment counts by department.

        Returns:
            List of dicts with 'department_name' and 'count'.
        """
        return self._appointment_service.get_department_counts()

    @require_role(Role.ADMIN)
    def get_peak_hours(self) -> List[Dict[str, Any]]:
        """Get appointment distribution by hour.

        Returns:
            List of dicts with 'hour' and 'count'.
        """
        return self._appointment_service.get_hourly_distribution()
