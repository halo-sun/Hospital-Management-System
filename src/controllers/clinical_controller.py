"""Clinical controller – coordinates clinical records, prescriptions, test reports.

Separated from ``ReportController`` to give clinical operations a dedicated
interface with validation, audit logging, and search/timeline queries.
"""
from __future__ import annotations

import logging
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from src.services.clinical_service import ClinicalService
from src.services.audit_service import AuditService
from src.constants import AuditAction, ReportType, Role
from src.auth.rbac import require_role
from src.controllers.auth_controller import AuthController
from src.utils.validators import (
    clean_strings,
    validate_patient_id,
    validate_search,
)
from src.services.document_service import (
    random_storage_name,
    resolve_upload_path,
    validate_document_file,
)

logger = logging.getLogger(__name__)


class ClinicalController:
    """Handles clinical record requests from the GUI layer.

    All methods return simple Python types (dicts, lists, tuples) so that
    the GUI layer never needs to import service or repository classes.
    """

    def __init__(self, auth_ctrl: Optional[AuthController] = None) -> None:
        """Initialise ClinicalController with required services.

        Args:
            auth_ctrl: Auth controller providing the current role
                (used by the RBAC decorator).
        """
        self._auth_ctrl = auth_ctrl
        self._clinical_service = ClinicalService()
        self._audit_service = AuditService()

    @property
    def _current_role(self) -> Optional[str]:
        """Return the logged-in user's role for RBAC checks."""
        if self._auth_ctrl is None:
            return None
        return self._auth_ctrl.current_role

    # ── Visit Records ──────────────────────────────────────────

    @require_role(Role.DOCTOR)
    def create_visit(
        self, data: Dict[str, Any], user_id: Optional[int] = None,
    ) -> Tuple[bool, str, Optional[int]]:
        """Create a new visit record with validation.

        Args:
            data: Dictionary with appointment_id, doctor_id, visit_date,
                  symptoms, diagnosis, doctor_notes, follow_up_date.
            user_id: The user creating the record (for audit logging).

        Returns:
            Tuple of (success, message, visit_id_or_None).
        """
        data = clean_strings(data)

        # Validate required fields
        if not data.get("appointment_id"):
            return False, "Appointment ID is required.", None
        if not data.get("doctor_id"):
            return False, "Doctor ID is required.", None

        success, message, visit_id = self._clinical_service.create_visit(data)

        if success and user_id:
            self._audit_service.log(
                user_id=user_id,
                action=AuditAction.CREATE,
                target_entity="VisitRecord",
                target_id=str(visit_id),
                new_values={"appointment_id": data.get("appointment_id")},
            )
            logger.info("Visit record %d created by user %s", visit_id, user_id)

        return success, message, visit_id

    @require_role(Role.DOCTOR)
    def get_visit(self, visit_id: int) -> Optional[Dict[str, Any]]:
        """Get a single visit record with full details.

        Args:
            visit_id: The visit record ID.

        Returns:
            Visit record dict with prescriptions and reports, or None.
        """
        return self._clinical_service.get_visit(visit_id)

    @require_role(Role.DOCTOR)
    def update_visit(
        self, visit_id: int, data: Dict[str, Any], user_id: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """Update a visit record with validation.

        Args:
            visit_id: The visit record ID.
            data: Fields to update.
            user_id: The user making the update (for audit logging).

        Returns:
            Tuple of (success, message).
        """
        data = clean_strings(data)
        success, message = self._clinical_service.update_visit(visit_id, data)

        if success and user_id:
            self._audit_service.log(
                user_id=user_id,
                action=AuditAction.UPDATE,
                target_entity="VisitRecord",
                target_id=str(visit_id),
                new_values=data,
            )

        return success, message

    # ── Patient Timeline ───────────────────────────────────────

    @require_role(Role.DOCTOR)
    def get_patient_visits(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get all visit records for a patient (chronological).

        Args:
            patient_id: The patient ID.

        Returns:
            List of visit records ordered by date descending.
        """
        valid, _ = validate_patient_id(patient_id)
        if not valid:
            return []
        return self._clinical_service.get_patient_visits(patient_id)

    @require_role(Role.DOCTOR)
    def get_patient_timeline(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get a patient's complete clinical timeline.

        Enriches each visit record with its prescriptions and reports
        for a grouped timeline display.

        Args:
            patient_id: The patient ID.

        Returns:
            List of visit records, each with 'prescriptions' and 'reports'.
        """
        visits = self.get_patient_visits(patient_id)
        timeline = []
        for visit in visits:
            visit_id = visit.get("visit_id")
            if visit_id:
                full_visit = self._clinical_service.get_visit(visit_id)
                if full_visit:
                    timeline.append(full_visit)
        return timeline

    # ── Doctor's patient list ──────────────────────────────────

    @require_role(Role.DOCTOR)
    def get_doctor_visits(
        self,
        doctor_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get visit records for a specific doctor.

        Args:
            doctor_id: The doctor ID.
            start_date: Optional start date filter (YYYY-MM-DD).
            end_date: Optional end date filter (YYYY-MM-DD).

        Returns:
            List of visit records.
        """
        return self._clinical_service.get_doctor_visits(
            doctor_id, start_date, end_date,
        )

    @require_role(Role.DOCTOR)
    def search_patient_visits(
        self, doctor_id: int, search_term: str,
    ) -> List[Dict[str, Any]]:
        """Search a doctor's visit records by patient name or ID.

        Args:
            doctor_id: The doctor ID.
            search_term: Patient name or ID fragment.

        Returns:
            List of matching visit records.
        """
        valid, _ = validate_search(search_term)
        if not valid:
            return []

        # Search across all visits and filter by patient name/ID
        all_visits = self._clinical_service.get_doctor_visits(doctor_id)
        term = search_term.lower().strip()
        return [
            v for v in all_visits
            if term in (v.get("patient_name", "") or "").lower()
            or term in (v.get("patient_id", "") or "").lower()
        ]

    # ── Prescriptions ──────────────────────────────────────────

    @require_role(Role.DOCTOR)
    def add_prescription(
        self, visit_id: int, data: Dict[str, Any], user_id: Optional[int] = None,
    ) -> Tuple[bool, str, Optional[int]]:
        """Add a prescription to a visit record.

        Args:
            visit_id: The visit record ID.
            data: Dictionary with medicine_name, dosage, frequency, etc.
            user_id: The user adding the prescription (for audit logging).

        Returns:
            Tuple of (success, message, prescription_id_or_None).
        """
        data = clean_strings(data)
        medicine = data.get("medicine_name", "").strip()
        if not medicine:
            return False, "Medicine name is required.", None

        success, message, rx_id = self._clinical_service.add_prescription(
            visit_id, data,
        )

        if success and user_id:
            self._audit_service.log(
                user_id=user_id,
                action=AuditAction.PRESCRIPTION_CREATE,
                target_entity="Prescription",
                target_id=str(rx_id),
                new_values={"medicine_name": medicine, "visit_id": visit_id},
            )

        return success, message, rx_id

    @require_role(Role.DOCTOR)
    def get_prescriptions(self, visit_id: int) -> List[Dict[str, Any]]:
        """Get all prescriptions for a visit.

        Args:
            visit_id: The visit record ID.

        Returns:
            List of prescription records.
        """
        return self._clinical_service.get_prescriptions(visit_id)

    @require_role(Role.DOCTOR)
    def delete_prescription(
        self, prescription_id: int, user_id: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """Delete a prescription record.

        Args:
            prescription_id: The prescription ID.
            user_id: The user performing the deletion (for audit logging).

        Returns:
            Tuple of (success, message).
        """
        success, message = self._clinical_service.delete_prescription(prescription_id)

        if success and user_id:
            self._audit_service.log(
                user_id=user_id,
                action=AuditAction.DELETE,
                target_entity="Prescription",
                target_id=str(prescription_id),
            )

        return success, message

    # ── Test Reports (Upload / Download / Delete) ──────────────

    @require_role(Role.DOCTOR)
    def upload_report(
        self, visit_id: int, file_path: str, doc_type: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Tuple[bool, str, Optional[int]]:
        """Upload a test report file for a visit record.

        Copies the file into the application's assets directory and
        creates a database record. When ``doc_type`` is given it is
        stored as the report category (e.g. Blood, X-Ray); otherwise
        the file extension is used as a fallback.

        Args:
            visit_id: The visit record ID.
            file_path: Source file path to upload.
            doc_type: Optional report category (see ``ReportType``).
            user_id: The user uploading (for audit logging).

        Returns:
            Tuple of (success, message, report_id_or_None).
        """
        if not file_path or not os.path.isfile(file_path):
            return False, "File not found.", None

        if doc_type is not None and doc_type not in ReportType.ALL:
            return False, (
                f"Invalid report type. Must be one of: {', '.join(ReportType.ALL)}"
            ), None

        # Same security policy as patient documents: extension
        # allow-list, max size before any read, magic-byte check.
        valid, msg = validate_document_file(file_path)
        if not valid:
            return False, msg, None

        from src.config import app_config

        # Determine destination directory
        reports_dir = os.path.join(app_config.ASSETS_DIR, "test_reports")
        os.makedirs(reports_dir, exist_ok=True)

        # Random storage filename (original name kept as metadata only)
        import shutil

        original_name = os.path.basename(file_path)
        storage_name = random_storage_name(file_path)
        dest_path = resolve_upload_path(reports_dir, storage_name)
        if dest_path is None:
            logger.error(
                "Path traversal blocked for report storage name: %r",
                storage_name,
            )
            return False, "Upload failed. Please try again.", None

        try:
            shutil.copy2(file_path, dest_path)
        except OSError as e:
            logger.error("Failed to copy report file: %s", e)
            return False, f"Failed to save file: {e}", None

        # Get file info
        file_size = os.path.getsize(dest_path)
        file_type = doc_type if doc_type else (
            os.path.splitext(original_name)[1].lstrip(".").upper() or "UNKNOWN"
        )

        report_data = {
            "report_name": original_name,
            "file_path": dest_path,
            "file_type": file_type,
            "file_size": file_size,
        }

        success, message, report_id = self._clinical_service.add_report(
            visit_id, report_data,
        )

        if success and user_id:
            self._audit_service.log(
                user_id=user_id,
                action=AuditAction.REPORT_UPLOAD,
                target_entity="TestReport",
                target_id=str(report_id),
                new_values={"report_name": original_name, "visit_id": visit_id},
            )

        return success, message, report_id

    @require_role(Role.DOCTOR)
    def get_reports(self, visit_id: int) -> List[Dict[str, Any]]:
        """Get all test reports for a visit.

        Args:
            visit_id: The visit record ID.

        Returns:
            List of test report records.
        """
        return self._clinical_service.get_reports(visit_id)

    @require_role(Role.DOCTOR)
    def download_report(self, report_id: int, dest_dir: str) -> Tuple[bool, str]:
        """Copy a test report file to a chosen destination.

        Delegates to ClinicalService which handles the report lookup and
        file path management.

        Args:
            report_id: The report ID.
            dest_dir: Destination directory path.

        Returns:
            Tuple of (success, message).
        """
        report = self._clinical_service.get_report(report_id)
        if not report:
            return False, "Report not found."

        src_path = report.get("file_path", "")
        if not src_path or not os.path.isfile(src_path):
            return False, "Report file not found on disk."

        import shutil

        dest_path = os.path.join(dest_dir, report.get("report_name", f"report_{report_id}"))
        try:
            shutil.copy2(src_path, dest_path)
            logger.info("Report %d downloaded to %s", report_id, dest_path)
            return True, f"Report saved to {dest_path}"
        except OSError as e:
            logger.error("Failed to download report: %s", e)
            return False, f"Failed to save file: {e}"

    @require_role(Role.DOCTOR)
    def delete_report(
        self, report_id: int, user_id: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """Delete a test report record and its file.

        Args:
            report_id: The report ID.
            user_id: The user performing the deletion (for audit logging).

        Returns:
            Tuple of (success, message).
        """
        success, message = self._clinical_service.delete_report(report_id)

        if success and user_id:
            self._audit_service.log(
                user_id=user_id,
                action=AuditAction.DELETE,
                target_entity="TestReport",
                target_id=str(report_id),
            )

        return success, message
