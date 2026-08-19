"""Clinical repository for visit records, prescriptions, and test reports."""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from src.repositories.base_repository import BaseRepository
from src.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class VisitRecordRepository(BaseRepository):
    """Repository for visit record operations."""

    def __init__(self) -> None:
        """Initialize VisitRecordRepository."""
        super().__init__("visit_records")

    def find_by_id_with_details(self, visit_id: int) -> Optional[Dict[str, Any]]:
        """Find a visit record by ID with patient and doctor details.

        Args:
            visit_id: The visit record ID.

        Returns:
            Visit record with names or None.
        """
        query = """
            SELECT vr.*,
                   a.patient_id,
                   p.full_name as patient_name,
                   doc.full_name as doctor_name
            FROM visit_records vr
            JOIN appointments a ON vr.appointment_id = a.appointment_id
            JOIN patients p ON a.patient_id = p.patient_id
            JOIN doctors doc ON vr.doctor_id = doc.doctor_id
            WHERE vr.visit_id = %s
        """
        return DatabaseConnection.execute_query(query, (visit_id,), fetch_one=True)

    def find_by_appointment(self, appointment_id: int) -> Optional[Dict[str, Any]]:
        """Find a visit record by appointment ID.

        Args:
            appointment_id: The appointment ID.

        Returns:
            Visit record or None.
        """
        results = self.find_where({"appointment_id": appointment_id})
        return results[0] if results else None

    def find_by_patient(self, patient_id: str) -> List[Dict[str, Any]]:
        """Find all visit records for a patient.

        Args:
            patient_id: The patient ID.

        Returns:
            List of visit records.
        """
        query = """
            SELECT vr.*, doc.full_name as doctor_name, d.department_name
            FROM visit_records vr
            JOIN doctors doc ON vr.doctor_id = doc.doctor_id
            JOIN departments d ON doc.department_id = d.department_id
            WHERE vr.appointment_id IN (
                SELECT appointment_id FROM appointments WHERE patient_id = %s
            )
            ORDER BY vr.visit_date DESC
        """
        return DatabaseConnection.execute_query(query, (patient_id,)) or []

    def find_by_doctor(
        self, doctor_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find visit records for a doctor, optionally within a date range.

        Args:
            doctor_id: The doctor ID.
            start_date: Optional start date filter (YYYY-MM-DD).
            end_date: Optional end date filter (YYYY-MM-DD).

        Returns:
            List of visit records.
        """
        query = """
            SELECT vr.*, a.patient_id, p.full_name as patient_name
            FROM visit_records vr
            JOIN appointments a ON vr.appointment_id = a.appointment_id
            JOIN patients p ON a.patient_id = p.patient_id
            WHERE vr.doctor_id = %s
        """
        params: list = [doctor_id]

        if start_date:
            query += " AND vr.visit_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND vr.visit_date <= %s"
            params.append(end_date)

        query += " ORDER BY vr.visit_date DESC"
        return DatabaseConnection.execute_query(query, tuple(params)) or []

    def create_visit(self, data: Dict[str, Any]) -> int:
        """Insert a new visit record.

        Args:
            data: Dictionary of visit fields.

        Returns:
            The new visit record's ID.
        """
        return self.insert(data)

    def update_visit(self, visit_id: int, data: Dict[str, Any]) -> int:
        """Update an existing visit record.

        Args:
            visit_id: The visit record ID.
            data: Fields to update.

        Returns:
            Number of rows affected.
        """
        data["updated_at"] = datetime.now()
        return self.update("visit_id", visit_id, data)


class PrescriptionRepository(BaseRepository):
    """Repository for prescription operations."""

    def __init__(self) -> None:
        """Initialize PrescriptionRepository."""
        super().__init__("prescriptions")

    def find_by_visit(self, visit_id: int) -> List[Dict[str, Any]]:
        """Find all prescriptions for a visit.

        Args:
            visit_id: The visit record ID.

        Returns:
            List of prescription records.
        """
        return self.find_where({"visit_id": visit_id}, order_by="prescription_id ASC")

    def create_prescription(self, data: Dict[str, Any]) -> int:
        """Insert a new prescription.

        Args:
            data: Dictionary of prescription fields.

        Returns:
            The new prescription's ID.
        """
        return self.insert(data)

    def delete_by_visit(self, visit_id: int) -> int:
        """Delete all prescriptions for a visit.

        Args:
            visit_id: The visit record ID.

        Returns:
            Number of rows deleted.
        """
        return self.delete_where({"visit_id": visit_id})


class TestReportRepository(BaseRepository):
    """Repository for test report file operations."""

    def __init__(self) -> None:
        """Initialize TestReportRepository."""
        super().__init__("test_reports")

    def find_by_visit(self, visit_id: int) -> List[Dict[str, Any]]:
        """Find all test reports for a visit.

        Args:
            visit_id: The visit record ID.

        Returns:
            List of test report records.
        """
        return self.find_where(
            {"visit_id": visit_id}, order_by="upload_date DESC"
        )

    def create_report(self, data: Dict[str, Any]) -> int:
        """Insert a new test report.

        Args:
            data: Dictionary of report fields.

        Returns:
            The new report's ID.
        """
        return self.insert(data)

    def delete_report(self, report_id: int) -> int:
        """Delete a test report.

        Args:
            report_id: The report ID.

        Returns:
            Number of rows deleted.
        """
        return self.delete("report_id", report_id)
