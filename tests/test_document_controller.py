"""Unit tests for the DocumentController.

The controller is a thin RBAC-gated façade over DocumentService:
these tests verify the doctor-only gate and that every method
delegates, including audit logging on upload/delete.  File-security
behaviour lives in ``test_document_service.py``.
"""
from __future__ import annotations

from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from src.auth.exceptions import PermissionDeniedError
from src.controllers.document_controller import DocumentController
from src.constants import Role


# ── Fixtures ──────────────────────────────────────────────────


class FakeAuth:
    """Minimal stand-in for AuthController exposing current_role."""

    def __init__(self, role: Optional[str] = None) -> None:
        self.current_role = role
        self.current_user = {"user_id": 1, "role_name": role} if role else None
        self.current_user_id = 1 if role else None


@pytest.fixture
def doctor_controller() -> DocumentController:
    """A DocumentController with a doctor session and mocked service/audit."""
    with (
        patch("src.controllers.document_controller.AuditService") as audit_cls,
        patch("src.repositories.doctor_repository.DoctorRepository") as doc_repo_cls,
        patch("src.services.clinical_service.ClinicalService") as clinical_cls,
    ):
        audit_cls.return_value = MagicMock()
        mock_repo = MagicMock()
        mock_repo.find_by_user_id.return_value = {"doctor_id": 1}
        doc_repo_cls.return_value = mock_repo
        # Mock clinical service so _has_treated_patient returns True
        mock_clinical = MagicMock()
        mock_clinical.get_doctor_visits.return_value = [
            {"patient_id": "PAT-00001"},
            {"patient_id": "PAT-00002"},
            {"patient_id": "PAT-1"},
        ]
        clinical_cls.return_value = mock_clinical
        ctrl = DocumentController(
            auth_ctrl=FakeAuth(Role.DOCTOR), service=MagicMock(),
        )
        ctrl._audit_service = audit_cls.return_value
        yield ctrl


@pytest.fixture
def mock_service(doctor_controller: DocumentController) -> MagicMock:
    """Access the mocked DocumentService."""
    return doctor_controller._service


@pytest.fixture
def mock_audit(doctor_controller: DocumentController) -> MagicMock:
    """Access the mocked AuditService."""
    return doctor_controller._audit_service


# ── RBAC gate ─────────────────────────────────────────────────


class TestRbacGate:
    """All document operations must be doctor-only."""

    def test_receptionist_denied(self) -> None:
        """A receptionist gets PermissionDeniedError on every method."""
        ctrl = DocumentController(auth_ctrl=FakeAuth(Role.RECEPTIONIST))
        with pytest.raises(PermissionDeniedError):
            ctrl.upload_document("PAT-1", "/tmp/f.pdf")
        with pytest.raises(PermissionDeniedError):
            ctrl.list_documents("PAT-1")
        with pytest.raises(PermissionDeniedError):
            ctrl.get_document(1)
        with pytest.raises(PermissionDeniedError):
            ctrl.delete_document(1)

    def test_admin_denied(self) -> None:
        """An admin is not allowed to manage patient documents."""
        ctrl = DocumentController(auth_ctrl=FakeAuth(Role.ADMIN))
        with pytest.raises(PermissionDeniedError):
            ctrl.list_documents("PAT-1")

    def test_no_session_denied(self) -> None:
        """No logged-in user gets PermissionDeniedError."""
        ctrl = DocumentController(auth_ctrl=FakeAuth(None))
        with pytest.raises(PermissionDeniedError):
            ctrl.list_documents("PAT-1")


# ── Delegation ────────────────────────────────────────────────


class TestDelegation:
    """Every method forwards to the DocumentService."""

    def test_upload_delegates_and_audits(self, doctor_controller: DocumentController,
                                         mock_service: MagicMock,
                                         mock_audit: MagicMock) -> None:
        """upload_document validates the patient, delegates, and audits."""
        mock_service.upload_document.return_value = (True, "Uploaded", 11)
        mock_service.get_document.return_value = {
            "document_id": 11, "document_name": "scan.pdf",
        }
        result = doctor_controller.upload_document(
            "PAT-00001", "/tmp/scan.pdf", user_id=7,
        )
        assert result == (True, "Uploaded", 11)
        mock_service.upload_document.assert_called_once_with(
            "PAT-00001", "/tmp/scan.pdf", uploaded_by=7,
        )
        mock_audit.log.assert_called_once()

    def test_upload_invalid_patient_rejected(self, doctor_controller: DocumentController,
                                             mock_service: MagicMock) -> None:
        """An invalid patient id fails before the service is called."""
        ok, msg, _ = doctor_controller.upload_document("bad id!", "/tmp/f.pdf")
        assert ok is False
        assert "patient" in msg.lower()
        mock_service.upload_document.assert_not_called()

    def test_list_delegates(self, doctor_controller: DocumentController,
                            mock_service: MagicMock) -> None:
        rows = [{"document_id": 1, "document_name": "scan.pdf"}]
        mock_service.list_documents.return_value = rows
        assert doctor_controller.list_documents("PAT-1") == rows
        mock_service.list_documents.assert_called_once_with("PAT-1")

    def test_get_delegates(self, doctor_controller: DocumentController,
                           mock_service: MagicMock) -> None:
        mock_service.get_document.return_value = {"document_id": 3}
        assert doctor_controller.get_document(3) == {"document_id": 3}
        mock_service.get_document.assert_called_once_with(3)

    def test_delete_delegates_and_audits(self, doctor_controller: DocumentController,
                                         mock_service: MagicMock,
                                         mock_audit: MagicMock) -> None:
        """delete_document delegates and audits on success."""
        mock_service.delete_document.return_value = (True, "Deleted")
        ok, msg = doctor_controller.delete_document(5, user_id=7)
        assert ok is True
        mock_service.delete_document.assert_called_once_with(5)
        mock_audit.log.assert_called_once()

    def test_delete_failure_no_audit(self, doctor_controller: DocumentController,
                                     mock_service: MagicMock,
                                     mock_audit: MagicMock) -> None:
        """Failed deletions are not audited."""
        mock_service.delete_document.return_value = (False, "Not found")
        ok, _ = doctor_controller.delete_document(99, user_id=7)
        assert ok is False
        mock_audit.log.assert_not_called()
