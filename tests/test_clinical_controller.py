"""Unit tests for the ClinicalController.

Tests cover validation, audit logging, file operations, and
passthrough methods with mocked ClinicalService and AuditService.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch, ANY
from typing import Any, Dict

import pytest

from src.controllers.clinical_controller import ClinicalController
from src.constants import Role
from src.auth.exceptions import PermissionDeniedError


# ── RBAC gate ─────────────────────────────────────────────────


class TestRbacGate:
    """Clinical records must be doctor-only."""

    def test_no_session_denied(self, mock_auth_ctrl: MagicMock) -> None:
        """No logged-in user is denied."""
        mock_auth_ctrl.current_role = None
        ctrl = ClinicalController(auth_ctrl=mock_auth_ctrl)
        with pytest.raises(PermissionDeniedError):
            ctrl.get_patient_visits("PAT-00001")

    def test_admin_denied(self, mock_auth_ctrl: MagicMock) -> None:
        """Even an admin cannot access clinical records through this path."""
        mock_auth_ctrl.current_role = Role.ADMIN
        ctrl = ClinicalController(auth_ctrl=mock_auth_ctrl)
        with pytest.raises(PermissionDeniedError):
            ctrl.get_visit(1)


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def mock_auth_ctrl() -> MagicMock:
    """Create a mocked AuthController with a Doctor session."""
    auth = MagicMock()
    auth.current_role = "Doctor"
    return auth


@pytest.fixture
def controller(mock_auth_ctrl: MagicMock) -> ClinicalController:
    """Create a ClinicalController with all services mocked."""
    with (
        patch("src.controllers.clinical_controller.ClinicalService") as cs_cls,
        patch("src.controllers.clinical_controller.AuditService") as as_cls,
    ):
        cs_cls.return_value = MagicMock()
        as_cls.return_value = MagicMock()
        ctrl = ClinicalController(auth_ctrl=mock_auth_ctrl)
        ctrl._clinical_service = cs_cls.return_value
        ctrl._audit_service = as_cls.return_value
        yield ctrl


@pytest.fixture
def mock_service(controller: ClinicalController) -> MagicMock:
    """Access the mocked ClinicalService."""
    return controller._clinical_service


@pytest.fixture
def mock_audit(controller: ClinicalController) -> MagicMock:
    """Access the mocked AuditService."""
    return controller._audit_service


# ── Visit CRUD Tests ──────────────────────────────────────────


class TestCreateVisit:
    """Tests for create_visit."""

    def test_success_with_audit(self, controller: ClinicalController,
                                 mock_service: MagicMock,
                                 mock_audit: MagicMock) -> None:
        """Successful creation logs audit entry."""
        mock_service.create_visit.return_value = (True, "Created", 1)

        success, msg, visit_id = controller.create_visit(
            {"appointment_id": 1, "doctor_id": 1},
            user_id=1,
        )
        assert success is True
        assert visit_id == 1
        mock_audit.log.assert_called_once()

    def test_success_without_audit(self, controller: ClinicalController,
                                    mock_service: MagicMock,
                                    mock_audit: MagicMock) -> None:
        """Successful creation without user_id skips audit."""
        mock_service.create_visit.return_value = (True, "Created", 1)

        success, msg, visit_id = controller.create_visit(
            {"appointment_id": 1, "doctor_id": 1},
        )
        assert success is True
        mock_audit.log.assert_not_called()

    def test_missing_appointment_id(self, controller: ClinicalController) -> None:
        """Missing appointment_id fails validation."""
        success, msg, visit_id = controller.create_visit({"doctor_id": 1})
        assert success is False
        assert visit_id is None

    def test_missing_doctor_id(self, controller: ClinicalController) -> None:
        """Missing doctor_id fails validation."""
        success, msg, visit_id = controller.create_visit({"appointment_id": 1})
        assert success is False
        assert visit_id is None

    def test_strips_whitespace(self, controller: ClinicalController,
                                mock_service: MagicMock) -> None:
        """Strings are stripped before passing to service."""
        mock_service.create_visit.return_value = (True, "Created", 1)
        controller.create_visit(
            {"appointment_id": 1, "doctor_id": 1, "symptoms": "  fever  "},
        )
        call_data = mock_service.create_visit.call_args[0][0]
        assert call_data["symptoms"] == "fever"


class TestGetVisit:
    """Tests for get_visit."""

    def test_get_visit(self, controller: ClinicalController,
                       mock_service: MagicMock) -> None:
        """get_visit delegates to service."""
        mock_service.get_visit.return_value = {"visit_id": 1}
        result = controller.get_visit(1)
        assert result is not None
        assert result["visit_id"] == 1

    def test_get_visit_not_found(self, controller: ClinicalController,
                                  mock_service: MagicMock) -> None:
        """get_visit returns None for non-existent visit."""
        mock_service.get_visit.return_value = None
        result = controller.get_visit(999)
        assert result is None


class TestUpdateVisit:
    """Tests for update_visit."""

    def test_update_success_with_audit(self, controller: ClinicalController,
                                        mock_service: MagicMock,
                                        mock_audit: MagicMock) -> None:
        """Successful update logs audit entry."""
        mock_service.update_visit.return_value = (True, "Updated")
        success, msg = controller.update_visit(1, {"diagnosis": "Updated"}, user_id=1)
        assert success is True
        mock_audit.log.assert_called_once()

    def test_update_failure(self, controller: ClinicalController,
                             mock_service: MagicMock) -> None:
        """Failed update returns error."""
        mock_service.update_visit.return_value = (False, "Not found")
        success, msg = controller.update_visit(999, {"diagnosis": "Updated"})
        assert success is False


# ── Patient Timeline Tests ────────────────────────────────────


class TestPatientTimeline:
    """Tests for patient timeline methods."""

    def test_get_patient_visits(self, controller: ClinicalController,
                                 mock_service: MagicMock) -> None:
        """get_patient_visits delegates to service."""
        mock_service.get_patient_visits.return_value = [{"visit_id": 1}]
        result = controller.get_patient_visits("PAT-00001")
        assert len(result) == 1

    def test_get_patient_visits_invalid_id(self, controller: ClinicalController) -> None:
        """Invalid patient ID returns empty list."""
        result = controller.get_patient_visits("")
        assert result == []

    def test_get_patient_timeline(self, controller: ClinicalController,
                                   mock_service: MagicMock) -> None:
        """get_patient_timeline enriches visits with details."""
        mock_service.get_patient_visits.return_value = [
            {"visit_id": 1, "patient_id": "PAT-00001"},
            {"visit_id": 2, "patient_id": "PAT-00001"},
        ]
        mock_service.get_visit.side_effect = [
            {"visit_id": 1, "prescriptions": [], "reports": []},
            {"visit_id": 2, "prescriptions": [], "reports": []},
        ]
        timeline = controller.get_patient_timeline("PAT-00001")
        assert len(timeline) == 2

    def test_get_patient_timeline_empty(self, controller: ClinicalController,
                                         mock_service: MagicMock) -> None:
        """get_patient_timeline returns empty list for no visits."""
        mock_service.get_patient_visits.return_value = []
        timeline = controller.get_patient_timeline("PAT-00001")
        assert timeline == []


# ── Prescription Tests ────────────────────────────────────────


class TestPrescriptions:
    """Tests for prescription management."""

    def test_add_prescription_success(self, controller: ClinicalController,
                                       mock_service: MagicMock,
                                       mock_audit: MagicMock) -> None:
        """Successful prescription creation logs audit."""
        mock_service.add_prescription.return_value = (True, "Created", 1)
        success, msg, rx_id = controller.add_prescription(
            1, {"medicine_name": "Paracetamol"}, user_id=1,
        )
        assert success is True
        assert rx_id == 1
        mock_audit.log.assert_called_once()

    def test_add_prescription_no_medicine(self, controller: ClinicalController) -> None:
        """Missing medicine name fails validation."""
        success, msg, rx_id = controller.add_prescription(1, {})
        assert success is False
        assert rx_id is None

    def test_get_prescriptions(self, controller: ClinicalController,
                                mock_service: MagicMock) -> None:
        """get_prescriptions delegates to service."""
        mock_service.get_prescriptions.return_value = [{"prescription_id": 1}]
        result = controller.get_prescriptions(1)
        assert len(result) == 1

    def test_delete_prescription(self, controller: ClinicalController,
                                  mock_service: MagicMock,
                                  mock_audit: MagicMock) -> None:
        """Successful deletion logs audit."""
        mock_service.delete_prescription.return_value = (True, "Deleted")
        success, msg = controller.delete_prescription(1, user_id=1)
        assert success is True
        mock_audit.log.assert_called_once()


# ── Report Tests ──────────────────────────────────────────────


class TestReports:
    """Tests for test report management."""

    def test_get_reports(self, controller: ClinicalController,
                          mock_service: MagicMock) -> None:
        """get_reports delegates to service."""
        mock_service.get_reports.return_value = [{"report_id": 1}]
        result = controller.get_reports(1)
        assert len(result) == 1

    def test_delete_report(self, controller: ClinicalController,
                            mock_service: MagicMock,
                            mock_audit: MagicMock) -> None:
        """Successful report deletion logs audit."""
        mock_service.delete_report.return_value = (True, "Deleted")
        success, msg = controller.delete_report(1, user_id=1)
        assert success is True
        mock_audit.log.assert_called_once()

    def test_upload_report_file_not_found(self, controller: ClinicalController) -> None:
        """Uploading a non-existent file fails."""
        with patch("os.path.isfile", return_value=False):
            success, msg, report_id = controller.upload_report(1, "/nonexistent/file.pdf")
            assert success is False
            assert "not found" in msg.lower()
            assert report_id is None

    def test_upload_report_success(self, controller: ClinicalController,
                                    mock_service: MagicMock,
                                    mock_audit: MagicMock) -> None:
        """Successful upload copies file and logs audit."""
        with (
            patch("os.path.isfile", return_value=True),
            patch("os.makedirs"),
            patch("os.path.getsize", return_value=1024),
            patch("shutil.copy2") as mock_copy,
            patch(
                "src.controllers.clinical_controller.validate_document_file",
                return_value=(True, ""),
            ),
            patch("src.controllers.clinical_controller.datetime") as mock_dt,
        ):
            mock_dt.now.return_value = __import__("datetime").datetime(2026, 6, 15, 10, 0)
            mock_service.add_report.return_value = (True, "Uploaded", 1)

            success, msg, report_id = controller.upload_report(
                1, "/tmp/test.pdf", user_id=1,
            )
            assert success is True
            assert report_id == 1
            mock_copy.assert_called_once()
            mock_audit.log.assert_called_once()

    def test_upload_report_with_doc_type(self, controller: ClinicalController,
                                          mock_service: MagicMock,
                                          mock_audit: MagicMock) -> None:
        """doc_type is stored as the report's file_type."""
        with (
            patch("os.path.isfile", return_value=True),
            patch("os.makedirs"),
            patch("os.path.getsize", return_value=1024),
            patch("shutil.copy2"),
            patch(
                "src.controllers.clinical_controller.validate_document_file",
                return_value=(True, ""),
            ),
            patch("src.controllers.clinical_controller.datetime") as mock_dt,
        ):
            mock_dt.now.return_value = __import__("datetime").datetime(2026, 6, 15, 10, 0)
            mock_service.add_report.return_value = (True, "Uploaded", 1)

            success, msg, report_id = controller.upload_report(
                1, "/tmp/xray.png", doc_type="X-Ray", user_id=1,
            )
            assert success is True
            assert report_id == 1
            visit_id_arg, report_data = mock_service.add_report.call_args.args
            assert visit_id_arg == 1
            assert report_data["file_type"] == "X-Ray"
            assert report_data["report_name"] == "xray.png"
            mock_audit.log.assert_called_once()

    def test_upload_report_invalid_doc_type(self, controller: ClinicalController) -> None:
        """An unrecognised report type is rejected before any file work."""
        with patch("os.path.isfile", return_value=True):
            success, msg, report_id = controller.upload_report(
                1, "/tmp/xray.png", doc_type="MRI-Scan",
            )
            assert success is False
            assert "report type" in msg.lower()
            assert report_id is None

    def test_upload_report_security_rejection(self, controller: ClinicalController,
                                               mock_service: MagicMock) -> None:
        """Files failing the security policy (bad magic bytes, wrong
        extension, oversize) are rejected before any copy or insert."""
        with (
            patch("os.path.isfile", return_value=True),
            patch(
                "src.controllers.clinical_controller.validate_document_file",
                return_value=(False, "File content does not match its extension."),
            ),
            patch("shutil.copy2") as mock_copy,
        ):
            success, msg, report_id = controller.upload_report(
                1, "/tmp/spoofed.pdf", user_id=1,
            )
            assert success is False
            assert "content does not match" in msg
            assert report_id is None
            mock_copy.assert_not_called()
            mock_service.add_report.assert_not_called()

    def test_download_report_success(self, controller: ClinicalController,
                                      mock_service: MagicMock) -> None:
        """download_report copies file to destination."""
        mock_service.get_report.return_value = {
            "report_id": 1, "file_path": "/tmp/test.pdf", "report_name": "test.pdf",
        }

        with (
            patch("os.path.isfile", return_value=True),
            patch("shutil.copy2") as mock_copy,
        ):
            success, msg = controller.download_report(1, "/dest")
            assert success is True
            mock_copy.assert_called_once()

    def test_download_report_not_found(self, controller: ClinicalController,
                                        mock_service: MagicMock) -> None:
        """Downloading a non-existent report fails."""
        mock_service.get_report.return_value = None
        success, msg = controller.download_report(999, "/dest")
        assert success is False

    def test_download_report_file_missing(self, controller: ClinicalController,
                                           mock_service: MagicMock) -> None:
        """Downloading a report with missing file fails."""
        mock_service.get_report.return_value = {
            "report_id": 1, "file_path": "/tmp/nonexistent.pdf", "report_name": "test.pdf",
        }
        with patch("os.path.isfile", return_value=False):
            success, msg = controller.download_report(1, "/dest")
            assert success is False


# ── Search / Doctor Visit Tests ───────────────────────────────


class TestSearchAndDoctorVisits:
    """Tests for search and doctor visit methods."""

    def test_get_doctor_visits(self, controller: ClinicalController,
                                mock_service: MagicMock) -> None:
        """get_doctor_visits delegates to service."""
        mock_service.get_doctor_visits.return_value = [{"visit_id": 1}]
        result = controller.get_doctor_visits(1, "2026-01-01", "2026-12-31")
        assert len(result) == 1

    def test_search_patient_visits(self, controller: ClinicalController,
                                    mock_service: MagicMock) -> None:
        """search_patient_visits filters by patient name."""
        mock_service.get_doctor_visits.return_value = [
            {"patient_name": "John Doe", "patient_id": "PAT-00001"},
            {"patient_name": "Jane Smith", "patient_id": "PAT-00002"},
        ]
        result = controller.search_patient_visits(1, "john")
        assert len(result) == 1
        assert result[0]["patient_name"] == "John Doe"

    def test_search_patient_visits_by_id(self, controller: ClinicalController,
                                          mock_service: MagicMock) -> None:
        """search_patient_visits filters by patient ID."""
        mock_service.get_doctor_visits.return_value = [
            {"patient_name": "John Doe", "patient_id": "PAT-00001"},
            {"patient_name": "Jane Smith", "patient_id": "PAT-00002"},
        ]
        result = controller.search_patient_visits(1, "00002")
        assert len(result) == 1
        assert result[0]["patient_id"] == "PAT-00002"

    def test_search_short_term(self, controller: ClinicalController) -> None:
        """Search term shorter than 2 characters returns empty."""
        result = controller.search_patient_visits(1, "a")
        assert result == []

    def test_search_empty_term(self, controller: ClinicalController) -> None:
        """Empty search term returns empty."""
        result = controller.search_patient_visits(1, "")
        assert result == []
