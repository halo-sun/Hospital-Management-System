"""Clinical service for visit records, prescriptions, and reports."""
import logging
import os
import shutil
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from src.repositories.clinical_repository import (
    VisitRecordRepository,
    PrescriptionRepository,
    TestReportRepository,
)
from src.config import app_config

logger = logging.getLogger(__name__)


class ClinicalService:
    """Handles clinical records: visits, prescriptions, and test reports."""

    def __init__(self) -> None:
        """Initialize ClinicalService with required repositories."""
        self._visit_repo = VisitRecordRepository()
        self._prescription_repo = PrescriptionRepository()
        self._report_repo = TestReportRepository()

    # ── Visit Records ──────────────────────────────────────────

    def create_visit(self, data: Dict[str, Any]) -> Tuple[bool, str, Optional[int]]:
        """Create a new visit record.

        Args:
            data: Dictionary with appointment_id, doctor_id, visit_date,
                  symptoms, diagnosis, doctor_notes, follow_up_date.

        Returns:
            Tuple of (success, message, visit_id_or_None).
        """
        if not data.get("appointment_id"):
            return False, "Appointment ID is required.", None
        if not data.get("doctor_id"):
            return False, "Doctor ID is required.", None

        visit_id = self._visit_repo.create_visit(data)
        logger.info(f"Visit record created: id={visit_id}")
        return True, "Visit record created successfully.", visit_id

    def get_visit(self, visit_id: int) -> Optional[Dict[str, Any]]:
        """Get a visit record by ID with full details.

        Args:
            visit_id: The visit record ID.

        Returns:
            Visit record with patient/doctor names or None.
        """
        visit = self._visit_repo.find_by_id_with_details(visit_id)
        if visit:
            visit["prescriptions"] = self._prescription_repo.find_by_visit(visit_id)
            visit["reports"] = self._report_repo.find_by_visit(visit_id)
        return visit

    def get_patient_visits(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get all visit records for a patient.

        Args:
            patient_id: The patient ID.

        Returns:
            List of visit records.
        """
        return self._visit_repo.find_by_patient(patient_id)

    def get_report(self, report_id: int) -> Optional[Dict[str, Any]]:
        """Get a single test report by ID.

        Args:
            report_id: The report ID.

        Returns:
            Report dict or None if not found.
        """
        return self._report_repo.find_by_id("report_id", report_id)

    def get_doctor_visits(
        self, doctor_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get visit records for a doctor.

        Args:
            doctor_id: The doctor ID.
            start_date: Optional start date filter.
            end_date: Optional end date filter.

        Returns:
            List of visit records.
        """
        return self._visit_repo.find_by_doctor(doctor_id, start_date, end_date)

    def update_visit(
        self, visit_id: int, data: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Update a visit record.

        Args:
            visit_id: The visit record ID.
            data: Fields to update.

        Returns:
            Tuple of (success, message).
        """
        existing = self._visit_repo.find_by_id("visit_id", visit_id)
        if not existing:
            return False, "Visit record not found."

        self._visit_repo.update_visit(visit_id, data)
        logger.info(f"Visit record updated: {visit_id}")
        return True, "Visit record updated successfully."

    # ── Prescriptions ──────────────────────────────────────────

    def add_prescription(
        self, visit_id: int, data: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[int]]:
        """Add a prescription to a visit record.

        Args:
            visit_id: The visit record ID.
            data: Dictionary with medicine_name, dosage, frequency, etc.

        Returns:
            Tuple of (success, message, prescription_id_or_None).
        """
        if not data.get("medicine_name", "").strip():
            return False, "Medicine name is required.", None

        data["visit_id"] = visit_id
        prescription_id = self._prescription_repo.create_prescription(data)
        logger.info(
            f"Prescription added: visit={visit_id} rx={prescription_id}"
        )
        return True, "Prescription added successfully.", prescription_id

    def get_prescriptions(self, visit_id: int) -> List[Dict[str, Any]]:
        """Get all prescriptions for a visit.

        Args:
            visit_id: The visit record ID.

        Returns:
            List of prescription records.
        """
        return self._prescription_repo.find_by_visit(visit_id)

    def delete_prescription(self, prescription_id: int) -> Tuple[bool, str]:
        """Delete a prescription record.

        Args:
            prescription_id: The prescription ID.

        Returns:
            Tuple of (success, message).
        """
        self._prescription_repo.delete("prescription_id", prescription_id)
        logger.info(f"Prescription deleted: {prescription_id}")
        return True, "Prescription deleted successfully."

    # ── Test Reports ───────────────────────────────────────────

    def add_report(
        self, visit_id: int, data: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[int]]:
        """Record a test report attachment for a visit.

        Args:
            visit_id: The visit record ID.
            data: Dictionary with report_name, file_path, file_type, file_size.

        Returns:
            Tuple of (success, message, report_id_or_None).
        """
        if not data.get("report_name", "").strip():
            return False, "Report name is required.", None
        if not data.get("file_path"):
            return False, "File path is required.", None

        data["visit_id"] = visit_id
        data["upload_date"] = datetime.now()
        report_id = self._report_repo.create_report(data)
        logger.info(f"Test report added: visit={visit_id} report={report_id}")
        return True, "Test report added successfully.", report_id

    def get_reports(self, visit_id: int) -> List[Dict[str, Any]]:
        """Get all test reports for a visit.

        Args:
            visit_id: The visit record ID.

        Returns:
            List of test report records.
        """
        return self._report_repo.find_by_visit(visit_id)

    def delete_report(self, report_id: int) -> Tuple[bool, str]:
        """Delete a test report record and its file.

        Args:
            report_id: The report ID.

        Returns:
            Tuple of (success, message).
        """
        report = self._report_repo.find_by_id("report_id", report_id)
        if report and report.get("file_path"):
            try:
                if os.path.exists(report["file_path"]):
                    os.remove(report["file_path"])
            except OSError as e:
                logger.warning(f"Failed to delete report file: {e}")

        self._report_repo.delete_report(report_id)
        logger.info(f"Test report deleted: {report_id}")
        return True, "Test report deleted successfully."
