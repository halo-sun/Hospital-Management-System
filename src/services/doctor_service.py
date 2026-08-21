"""Doctor service for doctor and department management."""
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, time
from src.repositories.doctor_repository import (
    DoctorRepository,
    DepartmentRepository,
    DoctorScheduleRepository,
    DoctorLeaveRepository,
)
from src.services.user_service import UserService
from src.database.connection import DatabaseConnection
from src.config import app_config
from src.constants import Role

logger = logging.getLogger(__name__)


class DoctorService:
    """Handles doctor and department management business logic."""

    def __init__(self) -> None:
        """Initialize DoctorService with required repositories."""
        self._doctor_repo = DoctorRepository()
        self._dept_repo = DepartmentRepository()
        self._schedule_repo = DoctorScheduleRepository()
        self._leave_repo = DoctorLeaveRepository()
        self._user_service = UserService()

    # ── Department Operations ──────────────────────────────────

    def get_all_departments(self) -> List[Dict[str, Any]]:
        """Get all departments.

        Returns:
            List of department records.
        """
        return self._dept_repo.get_with_doctor_count()

    def get_department(self, department_id: int) -> Optional[Dict[str, Any]]:
        """Get a department by ID.

        Args:
            department_id: The department ID.

        Returns:
            Department record or None.
        """
        return self._dept_repo.find_by_id("department_id", department_id)

    def create_department(self, data: Dict[str, Any]) -> Tuple[bool, str, Optional[int]]:
        """Create a new department.

        Args:
            data: Dictionary with department_name and optional description.

        Returns:
            Tuple of (success, message, new_id_or_None).
        """
        if not data.get("department_name", "").strip():
            return False, "Department name is required.", None

        existing = self._dept_repo.find_by_name(data["department_name"].strip())
        if existing:
            return False, "A department with this name already exists.", None

        dept_id = self._dept_repo.create_department(data)
        logger.info(f"Department created: {data['department_name']} (id={dept_id})")
        return True, "Department created successfully.", dept_id

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
        existing = self._dept_repo.find_by_id("department_id", department_id)
        if not existing:
            return False, "Department not found."

        if data.get("department_name"):
            dup = self._dept_repo.find_by_name(data["department_name"])
            if dup and dup["department_id"] != department_id:
                return False, "Another department with this name already exists."

        self._dept_repo.update_department(department_id, data)
        logger.info(f"Department updated: {department_id}")
        return True, "Department updated successfully."

    def delete_department(self, department_id: int) -> Tuple[bool, str]:
        """Delete a department if it has no doctors.

        Args:
            department_id: The department ID.

        Returns:
            Tuple of (success, message).
        """
        doctors = self._doctor_repo.find_by_department(department_id)
        if doctors:
            return False, "Cannot delete department with assigned doctors."

        self._dept_repo.delete_department(department_id)
        logger.info(f"Department deleted: {department_id}")
        return True, "Department deleted successfully."

    # ── Doctor Operations ──────────────────────────────────────

    def get_all_doctors(self) -> List[Dict[str, Any]]:
        """Get all doctors with department information.

        Returns:
            List of doctor records.
        """
        return self._doctor_repo.find_all_with_department()

    def get_active_doctors(self) -> List[Dict[str, Any]]:
        """Get all active doctors.

        Returns:
            List of active doctor records.
        """
        return self._doctor_repo.find_all_active()

    def get_doctors_by_department(self, department_id: int) -> List[Dict[str, Any]]:
        """Get active doctors in a department.

        Args:
            department_id: The department ID.

        Returns:
            List of doctor records.
        """
        return self._doctor_repo.find_by_department(department_id)

    def get_doctor(self, doctor_id: int) -> Optional[Dict[str, Any]]:
        """Get a doctor by ID with department info.

        Args:
            doctor_id: The doctor ID.

        Returns:
            Doctor record or None.
        """
        return self._doctor_repo.find_by_id_with_details(doctor_id)

    def get_doctor_by_user_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a doctor by associated user_id.

        Args:
            user_id: The linked user ID.

        Returns:
            Doctor record or None.
        """
        return self._doctor_repo.find_by_user_id(user_id)

    def create_doctor(
        self, doctor_data: Dict[str, Any], user_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Optional[int]]:
        """Create a new doctor, optionally creating a linked user account.

        When ``user_data`` is provided, both the user account and the
        doctor record are created inside a single database transaction
        so a failure on the second insert rolls back the first — no
        orphaned login accounts are left behind.

        Args:
            doctor_data: Dictionary of doctor fields.
            user_data: Optional dictionary with username/password for the user.

        Returns:
            Tuple of (success, message, new_doctor_id_or_None).
        """
        required = ["full_name", "department_id"]
        for field in required:
            if not doctor_data.get(field):
                return False, f"{field.replace('_', ' ').title()} is required.", None

        if user_data:
            pw = user_data.pop("password", "")
            role_id = self._user_service.get_role_id(Role.DOCTOR)
            if not role_id:
                return False, "Doctor role not found in system.", None
            user_data["role_id"] = role_id
            user_data["password"] = pw

            # Atomic: user + doctor in one transaction
            try:
                with DatabaseConnection.transaction() as conn:
                    success, msg, user_id = self._user_service.create_user(
                        user_data, conn=conn,
                    )
                    if not success:
                        # Validation error — transaction will roll back
                        raise ValueError(msg)
                    doctor_data["user_id"] = user_id
                    doctor_id = self._doctor_repo.create_doctor(
                        doctor_data, conn=conn,
                    )
            except ValueError as e:
                return False, str(e), None
            except Exception:
                logger.exception("Doctor creation failed — full rollback")
                return False, "Doctor creation failed due to a system error.", None

            logger.info("Doctor created: %s (id=%d)", doctor_data["full_name"], doctor_id)
            return True, "Doctor created successfully.", doctor_id

        # No user account — just create the doctor record
        doctor_id = self._doctor_repo.create_doctor(doctor_data)
        logger.info("Doctor created: %s (id=%d)", doctor_data["full_name"], doctor_id)
        return True, "Doctor created successfully.", doctor_id

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
        existing = self._doctor_repo.find_by_id_with_details(doctor_id)
        if not existing:
            return False, "Doctor not found."

        self._doctor_repo.update_doctor(doctor_id, data)
        logger.info(f"Doctor updated: {doctor_id}")
        return True, "Doctor updated successfully."

    def delete_doctor(self, doctor_id: int) -> Tuple[bool, str]:
        """Delete a doctor record.

        Args:
            doctor_id: The doctor ID.

        Returns:
            Tuple of (success, message).
        """
        existing = self._doctor_repo.find_by_id_with_details(doctor_id)
        if not existing:
            return False, "Doctor not found."

        self._schedule_repo.delete_by_doctor(doctor_id)
        self._doctor_repo.delete_doctor(doctor_id)
        logger.info(f"Doctor deleted: {doctor_id}")
        return True, "Doctor deleted successfully."

    def search_doctors(self, search_term: str) -> List[Dict[str, Any]]:
        """Search doctors by name, specialization, or email.

        Args:
            search_term: Text to search for.

        Returns:
            List of matching doctor records.
        """
        return self._doctor_repo.search_doctors(search_term)

    def get_all_specializations(self) -> List[str]:
        """Get list of unique specializations from all doctors.

        Returns:
            Sorted list of specialization strings.
        """
        doctors = self._doctor_repo.find_all_with_department()
        specs = sorted(set(
            d.get("specialization", "") for d in doctors
            if d.get("specialization")
        ))
        return specs

    def get_total_doctors(self) -> int:
        """Get total number of doctors.

        Returns:
            Total doctor count.
        """
        return self._doctor_repo.count_all()

    def get_active_doctors_count(self) -> int:
        """Get number of active doctors.

        Returns:
            Active doctor count.
        """
        return self._doctor_repo.count_active()

    # ── Schedule Operations ────────────────────────────────────

    def get_doctor_schedule(self, doctor_id: int) -> List[Dict[str, Any]]:
        """Get a doctor's weekly schedule.

        Args:
            doctor_id: The doctor ID.

        Returns:
            List of schedule records.
        """
        return self._schedule_repo.find_by_doctor(doctor_id)

    def update_doctor_schedule(
        self, doctor_id: int, day_of_week: int, start_time: time, end_time: time, is_available: bool = True
    ) -> Tuple[bool, str]:
        """Set or update a doctor's schedule for a specific day.

        Args:
            doctor_id: The doctor ID.
            day_of_week: Day number (0=Sunday, 6=Saturday).
            start_time: Start of working hours.
            end_time: End of working hours.
            is_available: Whether the doctor is available on this day.

        Returns:
            Tuple of (success, message).
        """
        if start_time >= end_time:
            return False, "Start time must be before end time."

        data = {
            "doctor_id": doctor_id,
            "day_of_week": day_of_week,
            "start_time": start_time,
            "end_time": end_time,
            "is_available": is_available,
        }
        self._schedule_repo.upsert_schedule(data)
        logger.info(f"Schedule updated for doctor {doctor_id}, day {day_of_week}")
        return True, "Schedule updated successfully."

    def is_doctor_available_on_date(
        self, doctor_id: int, check_date: date
    ) -> bool:
        """Check whether a doctor is available on a given date.

        Considers weekly schedule, leaves, and hospital holidays.

        Args:
            doctor_id: The doctor ID.
            check_date: The date to check.

        Returns:
            True if the doctor is available.
        """
        schedule = self._schedule_repo.find_by_doctor_and_day(
            doctor_id, check_date.weekday()
        )
        if not schedule or not schedule.get("is_available", True):
            return False

        leaves = self._leave_repo.find_by_doctor(doctor_id)
        for leave in leaves:
            if leave["leave_start_date"] <= check_date <= leave["leave_end_date"]:
                return False

        return True

    # ── Leave Operations ───────────────────────────────────────

    def get_doctor_leaves(self, doctor_id: int) -> List[Dict[str, Any]]:
        """Get all leave records for a doctor.

        Args:
            doctor_id: The doctor ID.

        Returns:
            List of leave records.
        """
        return self._leave_repo.find_by_doctor(doctor_id)

    def add_doctor_leave(
        self, data: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[int]]:
        """Add a leave record for a doctor.

        Args:
            data: Dictionary with doctor_id, leave_start_date, leave_end_date, etc.

        Returns:
            Tuple of (success, message, leave_id_or_None).
        """
        start = data.get("leave_start_date")
        end = data.get("leave_end_date")
        if not start or not end:
            return False, "Leave start and end dates are required.", None
        if start > end:
            return False, "Start date must be before end date.", None

        leave_id = self._leave_repo.create_leave(data)
        logger.info(f"Leave added for doctor {data.get('doctor_id')}: {leave_id}")
        return True, "Leave record created.", leave_id

    def delete_doctor_leave(self, leave_id: int) -> Tuple[bool, str]:
        """Delete a leave record.

        Args:
            leave_id: The leave record ID.

        Returns:
            Tuple of (success, message).
        """
        self._leave_repo.delete_leave(leave_id)
        logger.info(f"Leave deleted: {leave_id}")
        return True, "Leave record deleted."
