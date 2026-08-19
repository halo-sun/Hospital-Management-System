"""Patient controller – coordinates patient management requests.

Uses the centralised validators from ``src.utils.validators`` so that
all validation rules live in **one** place shared by controllers and
GUI components alike.
"""
import logging
from typing import Optional, Dict, Any, Tuple, List

from src.services.patient_service import PatientService
from src.services.audit_service import AuditService
from src.constants import AuditAction, Role
from src.auth.rbac import require_role
from src.controllers.auth_controller import AuthController
from src.utils.validators import (
    clean_strings,
    validate_patient_data,
    validate_search,
)

logger = logging.getLogger(__name__)


class PatientController:
    """Handles patient-related requests from the GUI layer.

    Validates patient inputs using centralised ``src.utils.validators``
    and delegates all persistence work to ``PatientService``.  Audit
    entries are written for register, update, and delete operations.
    """

    def __init__(self, auth_ctrl: Optional[AuthController] = None) -> None:
        """Initialize PatientController with required services.

        Args:
            auth_ctrl: Auth controller providing the current role
                (used by the RBAC decorator).
        """
        self._auth_ctrl = auth_ctrl
        self._patient_service = PatientService()
        self._audit_service = AuditService()

    @property
    def _current_role(self) -> Optional[str]:
        """Return the logged-in user's role for RBAC checks."""
        if self._auth_ctrl is None:
            return None
        return self._auth_ctrl.current_role

    # ── CRUD operations ────────────────────────────────────────

    @require_role(Role.RECEPTIONIST, Role.ADMIN)
    def register_patient(
        self, data: Dict[str, Any], audit_user_id: Optional[int] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """Register a new patient.

        Args:
            data: Dictionary with patient fields.
            audit_user_id: The user performing the registration, for audit.

        Returns:
            Tuple of (success, message, patient_id_or_None).
        """
        clean = clean_strings(data)
        valid, msg = validate_patient_data(clean)
        if not valid:
            return False, msg, None

        success, message, patient_id = self._patient_service.register_patient(clean)
        if success and patient_id and audit_user_id:
            self._audit_service.log(
                AuditAction.PATIENT_REGISTER,
                user_id=audit_user_id,
                target_entity="Patient",
                target_id=patient_id,
                new_values={
                    "full_name": clean.get("full_name"),
                    "contact_number": clean.get("contact_number"),
                },
            )
        return success, message, patient_id

    @require_role(Role.RECEPTIONIST, Role.ADMIN)
    def update_patient(
        self, patient_id: str, data: Dict[str, Any], audit_user_id: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """Update an existing patient.

        Args:
            patient_id: The patient ID.
            data: Fields to update.
            audit_user_id: The user performing the update, for audit.

        Returns:
            Tuple of (success, message).
        """
        clean = clean_strings(data)
        valid, msg = validate_patient_data(clean, is_edit=True)
        if not valid:
            return False, msg

        success, message = self._patient_service.update_patient(patient_id, clean)
        if success and audit_user_id:
            self._audit_service.log(
                AuditAction.PATIENT_UPDATE,
                user_id=audit_user_id,
                target_entity="Patient",
                target_id=patient_id,
                new_values=clean,
            )
        return success, message

    @require_role(Role.RECEPTIONIST, Role.ADMIN, Role.DOCTOR)
    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get a patient record by ID.

        Args:
            patient_id: The patient ID string.

        Returns:
            Patient record or None.
        """
        return self._patient_service.get_patient(patient_id)

    @require_role(Role.RECEPTIONIST, Role.ADMIN, Role.DOCTOR)
    def search_patients(
        self, search_term: str
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Search patients by ID, name, or phone.

        Args:
            search_term: The search text.

        Returns:
            Tuple of (success, message, results).
        """
        valid, msg = validate_search(search_term)
        if not valid:
            return False, msg, []

        results = self._patient_service.search_patients(search_term.strip())
        return True, f"{len(results)} patient(s) found.", results

    @require_role(Role.RECEPTIONIST, Role.ADMIN)
    def get_all_patients(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all patients.

        Args:
            limit: Maximum records.
            offset: Skip count.

        Returns:
            List of patient records.
        """
        return self._patient_service.get_all_patients(limit, offset)

    @require_role(Role.ADMIN)
    def delete_patient(
        self, patient_id: str, audit_user_id: Optional[int] = None
    ) -> Tuple[bool, str]:
        """Delete a patient record.

        Args:
            patient_id: The patient ID string.
            audit_user_id: The user performing the deletion, for audit.

        Returns:
            Tuple of (success, message).
        """
        success, message = self._patient_service.delete_patient(patient_id)
        if success and audit_user_id:
            self._audit_service.log(
                AuditAction.DELETE,
                user_id=audit_user_id,
                target_entity="Patient",
                target_id=patient_id,
            )
        return success, message

    @require_role(Role.RECEPTIONIST, Role.ADMIN)
    def get_patient_history(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get a patient's visit history.

        Args:
            patient_id: The patient ID.

        Returns:
            List of visit records.
        """
        return self._patient_service.get_patient_history(patient_id)

    @require_role(Role.RECEPTIONIST, Role.ADMIN)
    def get_recent_patients(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently registered patients.

        Args:
            limit: Number of records.

        Returns:
            List of recent patients.
        """
        return self._patient_service.get_recent_patients(limit)

    @require_role(Role.ADMIN)
    def get_total_count(self) -> int:
        """Get total patient count.

        Returns:
            Total number of patients.
        """
        return self._patient_service.get_total_count()

    @require_role(Role.ADMIN)
    def get_stats_by_gender(self) -> List[Dict[str, Any]]:
        """Get patient counts grouped by gender.

        Returns:
            List of dicts with 'gender' and 'count'.
        """
        return self._patient_service.get_stats_by_gender()
