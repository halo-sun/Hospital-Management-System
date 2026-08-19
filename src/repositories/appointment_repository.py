"""Appointment repository for appointment CRUD operations."""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date, time
from src.repositories.base_repository import BaseRepository
from src.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class AppointmentRepository(BaseRepository):
    """Repository for appointment-related database operations."""

    def __init__(self) -> None:
        """Initialize AppointmentRepository."""
        super().__init__("appointments")

    def find_by_id_with_details(self, appointment_id: int) -> Optional[Dict[str, Any]]:
        """Find an appointment by ID with patient and doctor names.

        Args:
            appointment_id: The appointment ID.

        Returns:
            Appointment record with names or None.
        """
        query = """
            SELECT a.*,
                   p.full_name as patient_name,
                   doc.full_name as doctor_name,
                   d.department_name
            FROM appointments a
            JOIN patients p ON a.patient_id = p.patient_id
            JOIN doctors doc ON a.doctor_id = doc.doctor_id
            JOIN departments d ON doc.department_id = d.department_id
            WHERE a.appointment_id = %s
        """
        return DatabaseConnection.execute_query(query, (appointment_id,), fetch_one=True)

    def find_by_doctor_and_date(
        self,
        doctor_id: int,
        appointment_date: date,
        for_update: bool = False,
        conn: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Find all appointments for a doctor on a specific date.

        When ``for_update`` is True the rows are locked with
        ``SELECT ... FOR UPDATE`` inside the caller's transaction so
        concurrent booking attempts for the same doctor/date cannot
        both pass the overlap check.

        Args:
            doctor_id: The doctor ID.
            appointment_date: The date to check.
            for_update: Lock the returned rows (must run inside a
                ``DatabaseConnection.transaction()``).
            conn: The transaction connection to run on.

        Returns:
            List of appointment records for that day.
        """
        lock_clause = " FOR UPDATE" if for_update else ""
        query = f"""
            SELECT a.*, p.full_name as patient_name
            FROM appointments a
            JOIN patients p ON a.patient_id = p.patient_id
            WHERE a.doctor_id = %s AND a.appointment_date = %s
            AND a.status IN ('Booked', 'Completed')
            ORDER BY a.start_time ASC{lock_clause}
        """
        return DatabaseConnection.execute_query(
            query, (doctor_id, appointment_date), conn=conn,
        ) or []

    def find_by_patient(self, patient_id: str) -> List[Dict[str, Any]]:
        """Find all appointments for a patient.

        Args:
            patient_id: The patient ID.

        Returns:
            List of appointment records.
        """
        query = """
            SELECT a.*, doc.full_name as doctor_name, d.department_name
            FROM appointments a
            JOIN doctors doc ON a.doctor_id = doc.doctor_id
            JOIN departments d ON doc.department_id = d.department_id
            WHERE a.patient_id = %s
            ORDER BY a.appointment_date DESC, a.start_time DESC
        """
        return DatabaseConnection.execute_query(query, (patient_id,)) or []

    def find_today_by_doctor(self, doctor_id: int) -> List[Dict[str, Any]]:
        """Find today's appointments for a doctor.

        Args:
            doctor_id: The doctor ID.

        Returns:
            List of today's appointment records.
        """
        today = date.today()
        return self.find_by_doctor_and_date(doctor_id, today)

    def find_all_upcoming(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Find all upcoming appointments from today onward.

        Args:
            limit: Maximum number of records.

        Returns:
            List of upcoming appointment records.
        """
        query = """
            SELECT a.*,
                   p.full_name as patient_name,
                   doc.full_name as doctor_name,
                   d.department_name
            FROM appointments a
            JOIN patients p ON a.patient_id = p.patient_id
            JOIN doctors doc ON a.doctor_id = doc.doctor_id
            JOIN departments d ON doc.department_id = d.department_id
            WHERE a.appointment_date >= %s AND a.status = 'Booked'
            ORDER BY a.appointment_date ASC, a.start_time ASC
            LIMIT %s
        """
        return DatabaseConnection.execute_query(query, (date.today(), limit)) or []

    def count_by_date_range(
        self, start_date: date, end_date: date
    ) -> List[Dict[str, Any]]:
        """Count appointments grouped by date within a range.

        Args:
            start_date: Range start date.
            end_date: Range end date.

        Returns:
            List of dicts with 'appointment_date' and 'count'.
        """
        query = """
            SELECT appointment_date, COUNT(*) as count
            FROM appointments
            WHERE appointment_date BETWEEN %s AND %s
            GROUP BY appointment_date
            ORDER BY appointment_date
        """
        return DatabaseConnection.execute_query(query, (start_date, end_date)) or []

    def count_by_status(self) -> List[Dict[str, Any]]:
        """Count appointments grouped by status.

        Returns:
            List of dicts with 'status' and 'count'.
        """
        query = """
            SELECT status, COUNT(*) as count
            FROM appointments
            GROUP BY status
        """
        return DatabaseConnection.execute_query(query) or []

    def count_by_department(self) -> List[Dict[str, Any]]:
        """Count appointments grouped by department.

        Returns:
            List of dicts with 'department_name' and 'count'.
        """
        query = """
            SELECT d.department_name, COUNT(*) as count
            FROM appointments a
            JOIN doctors doc ON a.doctor_id = doc.doctor_id
            JOIN departments d ON doc.department_id = d.department_id
            GROUP BY d.department_name
            ORDER BY count DESC
        """
        return DatabaseConnection.execute_query(query) or []

    def count_by_hour(self) -> List[Dict[str, Any]]:
        """Count appointments grouped by hour of day.

        Returns:
            List of dicts with 'hour' and 'count'.
        """
        query = """
            SELECT HOUR(start_time) as hour, COUNT(*) as count
            FROM appointments
            WHERE status IN ('Booked', 'Completed')
            GROUP BY HOUR(start_time)
            ORDER BY hour
        """
        return DatabaseConnection.execute_query(query) or []

    def get_doctor_workload(self) -> List[Dict[str, Any]]:
        """Get appointment counts per doctor.

        Returns:
            List of dicts with doctor info and appointment count.
        """
        query = """
            SELECT doc.doctor_id, doc.full_name as doctor_name,
                   d.department_name, COUNT(a.appointment_id) as appointment_count
            FROM doctors doc
            JOIN departments d ON doc.department_id = d.department_id
            LEFT JOIN appointments a ON doc.doctor_id = a.doctor_id
            GROUP BY doc.doctor_id, doc.full_name, d.department_name
            ORDER BY appointment_count DESC
        """
        return DatabaseConnection.execute_query(query) or []

    def create_appointment(self, data: Dict[str, Any], conn: Optional[Any] = None) -> int:
        """Insert a new appointment record.

        Args:
            data: Dictionary of appointment fields.
            conn: Optional connection to run on (transactional use).

        Returns:
            The new appointment's ID.
        """
        return self.insert(data, conn=conn)

    def update_appointment(
        self, appointment_id: int, data: Dict[str, Any], conn: Optional[Any] = None,
    ) -> int:
        """Update an existing appointment record.

        Args:
            appointment_id: The appointment ID.
            data: Fields to update.
            conn: Optional connection to run on (transactional use).

        Returns:
            Number of rows affected.
        """
        data["updated_at"] = datetime.now()
        return self.update("appointment_id", appointment_id, data, conn=conn)

    def cancel_appointment(self, appointment_id: int, conn: Optional[Any] = None) -> int:
        """Cancel an appointment by setting its status (never a hard delete).

        Args:
            appointment_id: The appointment ID.
            conn: Optional connection to run on (transactional use).

        Returns:
            Number of rows affected.
        """
        return self.update_appointment(
            appointment_id, {"status": "Cancelled"}, conn=conn,
        )

    def search_appointments(self, search_term: str) -> List[Dict[str, Any]]:
        """Search appointments by patient name, doctor name, or appointment ID.

        Args:
            search_term: Text to search for.

        Returns:
            List of matching appointment records.
        """
        query = """
            SELECT a.*,
                   p.full_name as patient_name,
                   doc.full_name as doctor_name,
                   d.department_name
            FROM appointments a
            JOIN patients p ON a.patient_id = p.patient_id
            JOIN doctors doc ON a.doctor_id = doc.doctor_id
            JOIN departments d ON doc.department_id = d.department_id
            WHERE a.appointment_id = %s
               OR p.full_name LIKE %s
               OR doc.full_name LIKE %s
            ORDER BY a.appointment_date DESC, a.start_time DESC
            LIMIT 50
        """
        like = f"%{search_term}%"
        return DatabaseConnection.execute_query(query, (search_term, like, like)) or []

    def find_by_date_range(
        self, start_date: date, end_date: date
    ) -> List[Dict[str, Any]]:
        """Find all appointments within a date range.

        Args:
            start_date: Range start date.
            end_date: Range end date.

        Returns:
            List of appointment records.
        """
        query = """
            SELECT a.*,
                   p.full_name as patient_name,
                   doc.full_name as doctor_name,
                   d.department_name
            FROM appointments a
            JOIN patients p ON a.patient_id = p.patient_id
            JOIN doctors doc ON a.doctor_id = doc.doctor_id
            JOIN departments d ON doc.department_id = d.department_id
            WHERE a.appointment_date BETWEEN %s AND %s
            ORDER BY a.appointment_date ASC, a.start_time ASC
        """
        return DatabaseConnection.execute_query(query, (start_date, end_date)) or []

    def count_today(self) -> int:
        """Count today's total appointments.

        Returns:
            Number of appointments today.
        """
        return self.count_where({"appointment_date": date.today()})

    def count_cancelled_by_date_range(
        self, start_date: date, end_date: date,
    ) -> List[Dict[str, Any]]:
        """Count cancelled appointments grouped by date within a range.

        Args:
            start_date: Range start date.
            end_date: Range end date.

        Returns:
            List of dicts with 'appointment_date' and 'count'.
        """
        query = """
            SELECT appointment_date, COUNT(*) as count
            FROM appointments
            WHERE status = 'Cancelled'
              AND appointment_date BETWEEN %s AND %s
            GROUP BY appointment_date
            ORDER BY appointment_date
        """
        return DatabaseConnection.execute_query(query, (start_date, end_date)) or []

    def count_total_by_date_range(
        self, start_date: date, end_date: date,
    ) -> List[Dict[str, Any]]:
        """Count total (non-cancelled) appointments grouped by date.

        Args:
            start_date: Range start date.
            end_date: Range end date.

        Returns:
            List of dicts with 'appointment_date' and 'count'.
        """
        query = """
            SELECT appointment_date, COUNT(*) as count
            FROM appointments
            WHERE status != 'Cancelled'
              AND appointment_date BETWEEN %s AND %s
            GROUP BY appointment_date
            ORDER BY appointment_date
        """
        return DatabaseConnection.execute_query(query, (start_date, end_date)) or []
