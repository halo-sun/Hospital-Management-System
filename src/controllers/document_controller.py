"""Document controller – coordinates patient document management.

All methods are RBAC-gated to doctors via the shared ``@require_role``
decorator and delegate to :class:`DocumentService`, which enforces the
upload security policy (extension allow-list, magic-byte checks, size
cap, random storage names, path-traversal-safe resolution).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from src.controllers.auth_controller import AuthController
from src.auth.rbac import require_role
from src.constants import AuditAction, Role
from src.services.document_service import DocumentService
from src.services.audit_service import AuditService
from src.utils.validators import validate_patient_id

logger = logging.getLogger(__name__)


class DocumentController:
    """Handles patient document requests from the GUI layer (doctor only)."""

    def __init__(
        self,
        auth_ctrl: Optional[AuthController] = None,
        service: Optional[DocumentService] = None,
    ) -> None:
        """Initialise DocumentController.

        Args:
            auth_ctrl: The shared AuthController used for RBAC checks.
            service: The document service (injectable for tests).
                Defaults to the real ``DocumentService``.
        """
        self._auth_ctrl = auth_ctrl
        self._service = service or DocumentService()
        self._audit_service = AuditService()

    @property
    def _current_role(self) -> Optional[str]:
        """Return the current user's role for ``@require_role`` checks."""
        if self._auth_ctrl is None:
            return None
        return self._auth_ctrl.current_role

    def _get_current_doctor_id(self) -> Optional[int]:
        """Return the doctor_id linked to the current user, or None."""
        if self._auth_ctrl is None or self._auth_ctrl.current_user is None:
            return None
        user_id = self._auth_ctrl.current_user_id
        if user_id is None:
            return None
        from src.repositories.doctor_repository import DoctorRepository
        repo = DoctorRepository()
        doctor = repo.find_by_user_id(user_id)
        return doctor.get("doctor_id") if doctor else None

    def _has_treated_patient(self, patient_id: str) -> bool:
        """Check whether the current doctor has any visit record for the patient.

        Returns:
            True if at least one visit exists linking this doctor to the patient.
        """
        doctor_id = self._get_current_doctor_id()
        if doctor_id is None:
            return False
        from src.services.clinical_service import ClinicalService
        clinical = ClinicalService()
        visits = clinical.get_doctor_visits(doctor_id)
        return any(v.get("patient_id") == patient_id for v in visits)

    # ── Upload ─────────────────────────────────────────────────

    @require_role(Role.DOCTOR)
    def upload_document(
        self,
        patient_id: str,
        file_path: str,
        user_id: Optional[int] = None,
    ) -> Tuple[bool, str, Optional[int]]:
        """Upload a document for a patient (validated + securely stored).

        Args:
            patient_id: The patient the document belongs to.
            file_path: Source file path.
            user_id: The user uploading (for audit logging).

        Returns:
            Tuple of (success, message, document_id_or_None).
        """
        valid, msg = validate_patient_id(patient_id)
        if not valid:
            return False, msg, None

        if not self._has_treated_patient(patient_id):
            return False, "Access denied: you can only manage documents for patients you have treated.", None

        success, message, document_id = self._service.upload_document(
            patient_id, file_path, uploaded_by=user_id,
        )

        if success and user_id:
            doc = self._service.get_document(document_id) if document_id else None
            self._audit_service.log(
                user_id=user_id,
                action=AuditAction.DOCUMENT_UPLOAD,
                target_entity="PatientDocument",
                target_id=str(document_id),
                new_values={
                    "patient_id": patient_id,
                    "document_name": doc.get("document_name", "") if doc else "",
                },
            )

        return success, message, document_id

    # ── Queries ────────────────────────────────────────────────

    @require_role(Role.DOCTOR)
    def list_documents(self, patient_id: str) -> List[Dict[str, Any]]:
        """Return all documents for a patient, newest first.

        Args:
            patient_id: The patient ID.

        Returns:
            List of document records.
        """
        if not self._has_treated_patient(patient_id):
            return []
        return self._service.list_documents(patient_id)

    @require_role(Role.DOCTOR)
    def get_document(self, document_id: int) -> Optional[Dict[str, Any]]:
        """Return a document record by ID.

        Args:
            document_id: The document ID.

        Returns:
            Document record or None.
        """
        return self._service.get_document(document_id)

    # ── Delete ─────────────────────────────────────────────────

    @require_role(Role.DOCTOR)
    def delete_document(
        self, document_id: int, user_id: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """Delete a document and its stored file.

        Args:
            document_id: The document ID.
            user_id: The user deleting (for audit logging).

        Returns:
            Tuple of (success, message).
        """
        success, message = self._service.delete_document(document_id)

        if success and user_id:
            self._audit_service.log(
                user_id=user_id,
                action=AuditAction.DELETE,
                target_entity="PatientDocument",
                target_id=str(document_id),
            )

        return success, message
