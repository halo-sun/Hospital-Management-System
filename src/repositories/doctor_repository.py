"""Doctor repository for doctor CRUD operations.

Department persistence lives in ``src.repositories.department_repository``;
``DepartmentRepository`` is re-exported here for backward compatibility
so existing imports (``doctor_service``, ``report_service``,
``repositories/__init__``) keep working unchanged.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from src.repositories.base_repository import BaseRepository
from src.repositories.department_repository import DepartmentRepository  # noqa: F401
from src.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class DoctorRepository(BaseRepository):
    """Repository for doctor-related database operations."""

    def __init__(self) -> None:
        """Initialize DoctorRepository."""
        super().__init__("doctors")

    def find_by_id_with_details(self, doctor_id: int) -> Optional[Dict[str, Any]]:
        """Find a doctor by ID with department information.

        Args:
            doctor_id: The doctor ID.

        Returns:
            Doctor record with department name or None.
        """
        query = """
            SELECT doc.*, d.department_name
            FROM doctors doc
            JOIN departments d ON doc.department_id = d.department_id
            WHERE doc.doctor_id = %s
        """
        return DatabaseConnection.execute_query(query, (doctor_id,), fetch_one=True)

    def find_by_user_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Find a doctor by the associated user_id.

        Args:
            user_id: The linked user ID.

        Returns:
            Doctor record or None.
        """
        query = """
            SELECT doc.*, d.department_name
            FROM doctors doc
            JOIN departments d ON doc.department_id = d.department_id
            WHERE doc.user_id = %s
        """
        return DatabaseConnection.execute_query(query, (user_id,), fetch_one=True)

    def find_all_active(self) -> List[Dict[str, Any]]:
        """Find all active doctors.

        Returns:
            List of active doctor records.
        """
        return self.find_where(
            {"status": "Active"}, order_by="full_name ASC"
        )

    def find_all_with_department(self) -> List[Dict[str, Any]]:
        """Find all doctors with department names.

        Returns:
            List of doctor records with department_name.
        """
        query = """
            SELECT doc.*, d.department_name
            FROM doctors doc
            JOIN departments d ON doc.department_id = d.department_id
            ORDER BY doc.full_name ASC
        """
        return DatabaseConnection.execute_query(query) or []

    def find_by_department(self, department_id: int) -> List[Dict[str, Any]]:
        """Find all active doctors in a department.

        Args:
            department_id: The department ID.

        Returns:
            List of doctor records.
        """
        return self.find_where(
            {"department_id": department_id, "status": "Active"},
            order_by="full_name ASC",
        )

    def create_doctor(self, data: Dict[str, Any]) -> int:
        """Insert a new doctor record.

        Args:
            data: Dictionary of doctor fields.

        Returns:
            The new doctor's ID.
        """
        return self.insert(data)

    def update_doctor(self, doctor_id: int, data: Dict[str, Any]) -> int:
        """Update an existing doctor record.

        Args:
            doctor_id: The doctor ID.
            data: Fields to update.

        Returns:
            Number of rows affected.
        """
        data["updated_at"] = datetime.now()
        return self.update("doctor_id", doctor_id, data)

    def delete_doctor(self, doctor_id: int) -> int:
        """Delete a doctor record.

        Args:
            doctor_id: The doctor ID.

        Returns:
            Number of rows deleted.
        """
        return self.delete("doctor_id", doctor_id)

    def count_all(self) -> int:
        """Count total doctors.

        Returns:
            Number of doctor records.
        """
        return self.count_where()

    def count_active(self) -> int:
        """Count active doctors.

        Returns:
            Number of active doctors.
        """
        return self.count_where({"status": "Active"})

    def search_doctors(self, search_term: str) -> List[Dict[str, Any]]:
        """Search doctors by name, specialization, or email.

        Args:
            search_term: Text to search for.

        Returns:
            List of matching doctor records.
        """
        return self.search(
            search_columns=["full_name", "specialization", "email"],
            search_term=search_term,
            order_by="full_name ASC",
            limit=50,
        )


class DoctorScheduleRepository(BaseRepository):
    """Repository for doctor weekly schedule operations."""

    def __init__(self) -> None:
        """Initialize DoctorScheduleRepository."""
        super().__init__("doctor_schedules")

    def find_by_doctor(self, doctor_id: int) -> List[Dict[str, Any]]:
        """Find all schedule entries for a doctor.

        Args:
            doctor_id: The doctor ID.

        Returns:
            List of schedule records ordered by day_of_week.
        """
        return self.find_where(
            {"doctor_id": doctor_id}, order_by="day_of_week ASC"
        )

    def find_by_doctor_and_day(
        self, doctor_id: int, day_of_week: int
    ) -> Optional[Dict[str, Any]]:
        """Find a specific schedule entry for a doctor on a given day.

        Args:
            doctor_id: The doctor ID.
            day_of_week: Day number (0=Sunday, 6=Saturday).

        Returns:
            Schedule record or None.
        """
        results = self.find_where(
            {"doctor_id": doctor_id, "day_of_week": day_of_week}
        )
        return results[0] if results else None

    def upsert_schedule(self, data: Dict[str, Any]) -> int:
        """Insert or update a schedule entry for a doctor on a specific day.

        Uses a unique key on (doctor_id, day_of_week) to upsert.

        Args:
            data: Dictionary with doctor_id, day_of_week, start_time, etc.

        Returns:
            Number of rows affected.
        """
        existing = self.find_by_doctor_and_day(
            data["doctor_id"], data["day_of_week"]
        )
        if existing:
            return self.update(
                "schedule_id", existing["schedule_id"], data
            )
        return self.insert(data)

    def delete_by_doctor(self, doctor_id: int) -> int:
        """Delete all schedule entries for a doctor.

        Args:
            doctor_id: The doctor ID.

        Returns:
            Number of rows deleted.
        """
        return self.delete_where({"doctor_id": doctor_id})


class DoctorLeaveRepository(BaseRepository):
    """Repository for doctor leave records."""

    def __init__(self) -> None:
        """Initialize DoctorLeaveRepository."""
        super().__init__("doctor_leave")

    def find_by_doctor(self, doctor_id: int) -> List[Dict[str, Any]]:
        """Find all leave records for a doctor.

        Args:
            doctor_id: The doctor ID.

        Returns:
            List of leave records ordered by start date.
        """
        return self.find_where(
            {"doctor_id": doctor_id}, order_by="leave_start_date DESC"
        )

    def find_active_leaves(self, check_date: date) -> List[Dict[str, Any]]:
        """Find all doctors currently on leave on the given date.

        Args:
            check_date: The date to check.

        Returns:
            List of leave records where the date falls within the range.
        """
        query = """
            SELECT * FROM doctor_leave
            WHERE leave_start_date <= %s AND leave_end_date >= %s
            AND status = 'Approved'
        """
        return DatabaseConnection.execute_query(query, (check_date, check_date)) or []

    def create_leave(self, data: Dict[str, Any]) -> int:
        """Insert a new leave record.

        Args:
            data: Dictionary of leave fields.

        Returns:
            The new leave record's ID.
        """
        return self.insert(data)

    def delete_leave(self, leave_id: int) -> int:
        """Delete a leave record.

        Args:
            leave_id: The leave ID.

        Returns:
            Number of rows deleted.
        """
        return self.delete("leave_id", leave_id)
