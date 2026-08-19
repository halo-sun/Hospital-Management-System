"""Doctor controller – coordinates doctor and department management."""
import logging
from typing import Optional, Dict, Any, Tuple, List
from datetime import time
from src.services.doctor_service import DoctorService
from src.services.audit_service import AuditService
from src.constants import Role
from src.auth.rbac import require_role
from src.controllers.auth_controller import AuthController
from src.utils.validators import validate_doctor_data, validate_department_name, validate_schedule_data

logger = logging.getLogger(__name__)


class DoctorController:
    """Handles doctor and department requests from the GUI layer.

    Delegates input validation to ``src.utils.validators`` and all
    business logic to ``DoctorService``.
    """

    def __init__(self, auth_ctrl: Optional[AuthController] = None) -> None:
        """Initialize DoctorController with required services.

        Args:
            auth_ctrl: Auth controller providing the current role
                (used by the RBAC decorator).
        """
        self._auth_ctrl = auth_ctrl
        self._doctor_service = DoctorService()
        self._audit_service = AuditService()

    @property
    def _current_role(self) -> Optional[str]:
        """Return the logged-in user's role for RBAC checks."""
        if self._auth_ctrl is None:
            return None
        return self._auth_ctrl.current_role

    # ── Input validation (delegates to centralized validators) ──

    @staticmethod
    def validate_doctor_data(data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate doctor form data.

        Args:
            data: Dictionary of doctor fields.

        Returns:
            Tuple of (valid, error_message).
        """
        return validate_doctor_data(data)

    @staticmethod
    def validate_department_data(data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate department form data.

        Args:
            data: Dictionary of department fields.

        Returns:
            Tuple of (valid, error_message).
        """
        return validate_department_name(data.get("department_name", ""))

    @staticmethod
    def validate_schedule_data(
        day_of_week: int, start_time: time, end_time: time
    ) -> Tuple[bool, str]:
        """Validate doctor schedule data.

        Args:
            day_of_week: Day number (0-6).
            start_time: Working start time.
            end_time: Working end time.

        Returns:
            Tuple of (valid, error_message).
        """
        return validate_schedule_data(day_of_week, start_time, end_time)

    # ── Department operations ──────────────────────────────────

    @require_role(Role.ADMIN, Role.RECEPTIONIST)
    def get_all_departments(self) -> List[Dict[str, Any]]:
        """Get all departments with doctor counts.

        Returns:
            List of department records.
        """
        return self._doctor_service.get_all_departments()

    @require_role(Role.ADMIN, Role.RECEPTIONIST)
    def get_department(self, department_id: int) -> Optional[Dict[str, Any]]:
        """Get a department by ID.

        Args:
            department_id: The department ID.

        Returns:
            Department record or None.
        """
        return self._doctor_service.get_department(department_id)

    @require_role(Role.ADMIN)
    def create_department(self, data: Dict[str, Any]) -> Tuple[bool, str, Optional[int]]:
        """Create a new department.

        Args:
            data: Department fields.

        Returns:
            Tuple of (success, message, new_id_or_None).
        """
        valid, msg = self.validate_department_data(data)
        if not valid:
            return False, msg, None

        data["department_name"] = data["department_name"].strip()
        return self._doctor_service.create_department(data)

    @require_role(Role.ADMIN)
    def update_department(
        self, department_id: int, data: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Update a department.

        Args:
            department_id: The department ID.
            data: Fields to update.

        Returns:
            Tuple of (success, message).
        """
        if data.get("department_name"):
            valid, msg = self.validate_department_data(data)
            if not valid:
                return False, msg

        return self._doctor_service.update_department(department_id, data)

    @require_role(Role.ADMIN)
    def delete_department(self, department_id: int) -> Tuple[bool, str]:
        """Delete a department.

        Args:
            department_id: The department ID.

        Returns:
            Tuple of (success, message).
        """
        return self._doctor_service.delete_department(department_id)

    # ── Doctor operations ──────────────────────────────────────

    @require_role(Role.ADMIN)
    def get_all_doctors(self) -> List[Dict[str, Any]]:
        """Get all doctors.

        Returns:
            List of doctor records.
        """
        return self._doctor_service.get_all_doctors()

    @require_role(Role.ADMIN, Role.RECEPTIONIST, Role.DOCTOR)
    def get_active_doctors(self) -> List[Dict[str, Any]]:
        """Get all active doctors.

        Returns:
            List of active doctor records.
        """
        return self._doctor_service.get_active_doctors()

    @require_role(Role.ADMIN, Role.RECEPTIONIST)
    def get_doctors_by_department(self, department_id: int) -> List[Dict[str, Any]]:
        """Get active doctors in a department.

        Args:
            department_id: The department ID.

        Returns:
            List of doctor records.
        """
        return self._doctor_service.get_doctors_by_department(department_id)

    @require_role(Role.ADMIN, Role.RECEPTIONIST, Role.DOCTOR)
    def get_doctor(self, doctor_id: int) -> Optional[Dict[str, Any]]:
        """Get a doctor by ID.

        Args:
            doctor_id: The doctor ID.

        Returns:
            Doctor record or None.
        """
        return self._doctor_service.get_doctor(doctor_id)

    @require_role(Role.DOCTOR, Role.ADMIN)
    def get_doctor_by_user_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a doctor by associated user_id.

        Args:
            user_id: The linked user ID.

        Returns:
            Doctor record or None.
        """
        return self._doctor_service.get_doctor_by_user_id(user_id)

    @require_role(Role.ADMIN)
    def create_doctor(
        self, doctor_data: Dict[str, Any], user_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Optional[int]]:
        """Create a new doctor.

        Args:
            doctor_data: Doctor fields.
            user_data: Optional user account fields.

        Returns:
            Tuple of (success, message, doctor_id_or_None).
        """
        valid, msg = self.validate_doctor_data(doctor_data)
        if not valid:
            return False, msg, None

        return self._doctor_service.create_doctor(doctor_data, user_data)

    @require_role(Role.ADMIN)
    def update_doctor(
        self, doctor_id: int, data: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Update a doctor record.

        Args:
            doctor_id: The doctor ID.
            data: Fields to update.

        Returns:
            Tuple of (success, message).
        """
        valid, msg = self.validate_doctor_data(data)
        if not valid:
            return False, msg

        return self._doctor_service.update_doctor(doctor_id, data)

    @require_role(Role.ADMIN)
    def delete_doctor(self, doctor_id: int) -> Tuple[bool, str]:
        """Delete a doctor record.

        Args:
            doctor_id: The doctor ID.

        Returns:
            Tuple of (success, message).
        """
        return self._doctor_service.delete_doctor(doctor_id)

    @require_role(Role.ADMIN)
    def search_doctors(self, search_term: str) -> List[Dict[str, Any]]:
        """Search doctors by name, specialization, or email.

        Args:
            search_term: Text to search for.

        Returns:
            List of matching records.
        """
        return self._doctor_service.search_doctors(search_term)

    @require_role(Role.ADMIN)
    def filter_doctors(
        self,
        search_term: Optional[str] = None,
        department_id: Optional[int] = None,
        specialization: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Filter doctors by multiple criteria.

        Args:
            search_term: Optional text search.
            department_id: Optional department ID.
            specialization: Optional specialization filter.
            status: Optional status filter.

        Returns:
            Filtered list of doctor records.
        """
        return self._doctor_service.filter_doctors(
            search_term=search_term,
            department_id=department_id,
            specialization=specialization,
            status=status,
        )

    @require_role(Role.ADMIN, Role.RECEPTIONIST)
    def get_all_specializations(self) -> List[str]:
        """Get all unique specializations.

        Returns:
            Sorted list of specialization strings.
        """
        return self._doctor_service.get_all_specializations()

    # ── Schedule operations ────────────────────────────────────

    @require_role(Role.DOCTOR, Role.ADMIN, Role.RECEPTIONIST)
    def get_doctor_schedule(self, doctor_id: int) -> List[Dict[str, Any]]:
        """Get a doctor's weekly schedule.

        Args:
            doctor_id: The doctor ID.

        Returns:
            List of schedule records.
        """
        return self._doctor_service.get_doctor_schedule(doctor_id)

    @require_role(Role.ADMIN)
    def update_doctor_schedule(
        self,
        doctor_id: int,
        day_of_week: int,
        start_time: time,
        end_time: time,
        is_available: bool = True,
    ) -> Tuple[bool, str]:
        """Update a doctor's schedule for a specific day.

        Args:
            doctor_id: The doctor ID.
            day_of_week: Day number (0=Sunday, 6=Saturday).
            start_time: Working start time.
            end_time: Working end time.
            is_available: Whether the doctor is available.

        Returns:
            Tuple of (success, message).
        """
        valid, msg = self.validate_schedule_data(day_of_week, start_time, end_time)
        if not valid:
            return False, msg

        return self._doctor_service.update_doctor_schedule(
            doctor_id, day_of_week, start_time, end_time, is_available
        )

    # ── Leave operations ───────────────────────────────────────

    @require_role(Role.DOCTOR, Role.ADMIN)
    def get_doctor_leaves(self, doctor_id: int) -> List[Dict[str, Any]]:
        """Get all leaves for a doctor.

        Args:
            doctor_id: The doctor ID.

        Returns:
            List of leave records.
        """
        return self._doctor_service.get_doctor_leaves(doctor_id)

    @require_role(Role.ADMIN)
    def add_doctor_leave(self, data: Dict[str, Any]) -> Tuple[bool, str, Optional[int]]:
        """Add a leave record for a doctor.

        Args:
            data: Leave fields.

        Returns:
            Tuple of (success, message, leave_id_or_None).
        """
        return self._doctor_service.add_doctor_leave(data)

    @require_role(Role.ADMIN)
    def delete_doctor_leave(self, leave_id: int) -> Tuple[bool, str]:
        """Delete a leave record.

        Args:
            leave_id: The leave record ID.

        Returns:
            Tuple of (success, message).
        """
        return self._doctor_service.delete_doctor_leave(leave_id)

    # ── Stats ──────────────────────────────────────────────────

    @require_role(Role.ADMIN)
    def get_total_doctors(self) -> int:
        """Get total doctor count.

        Returns:
            Total number of doctors.
        """
        return self._doctor_service.get_total_doctors()

    @require_role(Role.ADMIN)
    def get_active_doctors_count(self) -> int:
        """Get active doctor count.

        Returns:
            Number of active doctors.
        """
        return self._doctor_service.get_active_doctors_count()
