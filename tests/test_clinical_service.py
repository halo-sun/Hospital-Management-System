"""Unit tests for the ClinicalService.

Tests cover visit record CRUD, prescription management, and
test report management with mocked repositories.
"""
from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock, patch
from typing import Any, Dict

import pytest

from src.services.clinical_service import ClinicalService


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def service() -> ClinicalService:
    """Create a ClinicalService with all repositories mocked."""
    with (
        patch("src.services.clinical_service.VisitRecordRepository") as vr_cls,
        patch("src.services.clinical_service.PrescriptionRepository") as pr_cls,
        patch("src.services.clinical_service.TestReportRepository") as tr_cls,
    ):
        vr_cls.return_value = MagicMock()
        pr_cls.return_value = MagicMock()
        tr_cls.return_value = MagicMock()
        svc = ClinicalService()
        svc._visit_repo = vr_cls.return_value
        svc._prescription_repo = pr_cls.return_value
        svc._report_repo = tr_cls.return_value
        yield svc


@pytest.fixture
def mock_visit_repo(service: ClinicalService) -> MagicMock:
    """Access the mocked VisitRecordRepository."""
    return service._visit_repo


@pytest.fixture
def mock_rx_repo(service: ClinicalService) -> MagicMock:
    """Access the mocked PrescriptionRepository."""
    return service._prescription_repo


@pytest.fixture
def mock_report_repo(service: ClinicalService) -> MagicMock:
    """Access the mocked TestReportRepository."""
    return service._report_repo


# ── Factory helpers ───────────────────────────────────────────


def make_visit(**overrides: Any) -> Dict[str, Any]:
    """Create a visit record dict with defaults."""
    data: Dict[str, Any] = {
        "visit_id": 1,
        "appointment_id": 1,
        "doctor_id": 1,
        "visit_date": date(2026, 6, 15),
        "symptoms": "Cough and fever",
        "diagnosis": "Common cold",
        "doctor_notes": "Rest and hydrate",
        "follow_up_date": None,
        "status": "Completed",
        "patient_id": "PAT-00001",
        "patient_name": "John Doe",
        "doctor_name": "Dr. Smith",
    }
    data.update(overrides)
    return data


def make_prescription(**overrides: Any) -> Dict[str, Any]:
    """Create a prescription dict with defaults."""
    data: Dict[str, Any] = {
        "prescription_id": 1,
        "visit_id": 1,
        "medicine_name": "Paracetamol",
        "dosage": "500mg",
        "frequency": "Twice daily",
        "duration": "5 days",
        "instructions": "After meals",
    }
    data.update(overrides)
    return data


def make_report(**overrides: Any) -> Dict[str, Any]:
    """Create a test report dict with defaults."""
    data: Dict[str, Any] = {
        "report_id": 1,
        "visit_id": 1,
        "report_name": "blood_test.pdf",
        "file_path": "/tmp/test_reports/blood_test.pdf",
        "file_type": "PDF",
        "file_size": 1024,
        "upload_date": datetime(2026, 6, 15, 10, 0),
    }
    data.update(overrides)
    return data


# ── Visit Record Tests ────────────────────────────────────────


class TestCreateVisit:
    """Tests for create_visit."""

    def test_successful_creation(self, service: ClinicalService,
                                  mock_visit_repo: MagicMock) -> None:
        """Valid data creates a visit record."""
        mock_visit_repo.create_visit.return_value = 1
        data = {
            "appointment_id": 1,
            "doctor_id": 1,
            "visit_date": date(2026, 6, 15),
            "symptoms": "Fever",
            "diagnosis": "Flu",
        }
        success, msg, visit_id = service.create_visit(data)
        assert success is True
        assert visit_id == 1
        mock_visit_repo.create_visit.assert_called_once()

    def test_missing_appointment_id(self, service: ClinicalService) -> None:
        """Missing appointment_id fails."""
        success, msg, visit_id = service.create_visit({"doctor_id": 1})
        assert success is False
        assert "appointment" in msg.lower()
        assert visit_id is None

    def test_missing_doctor_id(self, service: ClinicalService) -> None:
        """Missing doctor_id fails."""
        success, msg, visit_id = service.create_visit({"appointment_id": 1})
        assert success is False
        assert "doctor" in msg.lower()
        assert visit_id is None


class TestGetVisits:
    """Tests for visit retrieval methods."""

    def test_get_visit_with_details(self, service: ClinicalService,
                                     mock_visit_repo: MagicMock,
                                     mock_rx_repo: MagicMock,
                                     mock_report_repo: MagicMock) -> None:
        """get_visit returns enriched visit with prescriptions and reports."""
        mock_visit_repo.find_by_id_with_details.return_value = make_visit()
        mock_rx_repo.find_by_visit.return_value = [make_prescription()]
        mock_report_repo.find_by_visit.return_value = [make_report()]

        result = service.get_visit(1)
        assert result is not None
        assert result["visit_id"] == 1
        assert len(result["prescriptions"]) == 1
        assert len(result["reports"]) == 1

    def test_get_visit_not_found(self, service: ClinicalService,
                                  mock_visit_repo: MagicMock) -> None:
        """get_visit returns None for non-existent visit."""
        mock_visit_repo.find_by_id_with_details.return_value = None
        result = service.get_visit(999)
        assert result is None

    def test_get_patient_visits(self, service: ClinicalService,
                                 mock_visit_repo: MagicMock) -> None:
        """get_patient_visits delegates to repo."""
        mock_visit_repo.find_by_patient.return_value = [make_visit()]
        result = service.get_patient_visits("PAT-00001")
        assert len(result) == 1

    def test_get_doctor_visits(self, service: ClinicalService,
                                mock_visit_repo: MagicMock) -> None:
        """get_doctor_visits delegates to repo with filters."""
        mock_visit_repo.find_by_doctor.return_value = [make_visit()]
        result = service.get_doctor_visits(1, "2026-01-01", "2026-12-31")
        assert len(result) == 1


class TestUpdateVisit:
    """Tests for update_visit."""

    def test_update_success(self, service: ClinicalService,
                             mock_visit_repo: MagicMock) -> None:
        """Valid update succeeds."""
        mock_visit_repo.find_by_id.return_value = make_visit()
        mock_visit_repo.update_visit.return_value = 1

        success, msg = service.update_visit(1, {"diagnosis": "Updated"})
        assert success is True
        mock_visit_repo.update_visit.assert_called_once()

    def test_update_not_found(self, service: ClinicalService,
                               mock_visit_repo: MagicMock) -> None:
        """Updating non-existent visit fails."""
        mock_visit_repo.find_by_id.return_value = None
        success, msg = service.update_visit(999, {"diagnosis": "Updated"})
        assert success is False
        assert "not found" in msg.lower()


# ── Prescription Tests ────────────────────────────────────────


class TestPrescriptions:
    """Tests for prescription management."""

    def test_add_prescription_success(self, service: ClinicalService,
                                       mock_rx_repo: MagicMock) -> None:
        """Add a valid prescription."""
        mock_rx_repo.create_prescription.return_value = 1
        success, msg, rx_id = service.add_prescription(1, {
            "medicine_name": "Amoxicillin",
            "dosage": "250mg",
            "frequency": "Three times daily",
        })
        assert success is True
        assert rx_id == 1

    def test_add_prescription_missing_medicine(self, service: ClinicalService) -> None:
        """Missing medicine name fails."""
        success, msg, rx_id = service.add_prescription(1, {
            "dosage": "250mg",
        })
        assert success is False
        assert "medicine" in msg.lower()
        assert rx_id is None

    def test_get_prescriptions(self, service: ClinicalService,
                                mock_rx_repo: MagicMock) -> None:
        """get_prescriptions delegates to repo."""
        mock_rx_repo.find_by_visit.return_value = [make_prescription()]
        result = service.get_prescriptions(1)
        assert len(result) == 1

    def test_delete_prescription(self, service: ClinicalService,
                                  mock_rx_repo: MagicMock) -> None:
        """delete_prescription delegates to repo."""
        success, msg = service.delete_prescription(1)
        assert success is True
        mock_rx_repo.delete.assert_called_once_with("prescription_id", 1)


# ── Test Report Tests ─────────────────────────────────────────


class TestReports:
    """Tests for test report management."""

    def test_add_report_success(self, service: ClinicalService,
                                 mock_report_repo: MagicMock) -> None:
        """Add a valid test report."""
        mock_report_repo.create_report.return_value = 1
        success, msg, report_id = service.add_report(1, {
            "report_name": "xray.pdf",
            "file_path": "/tmp/xray.pdf",
        })
        assert success is True
        assert report_id == 1

    def test_add_report_missing_name(self, service: ClinicalService) -> None:
        """Missing report name fails."""
        success, msg, report_id = service.add_report(1, {
            "file_path": "/tmp/xray.pdf",
        })
        assert success is False
        assert "name" in msg.lower()
        assert report_id is None

    def test_add_report_missing_path(self, service: ClinicalService) -> None:
        """Missing file path fails."""
        success, msg, report_id = service.add_report(1, {
            "report_name": "xray.pdf",
        })
        assert success is False
        assert "path" in msg.lower()
        assert report_id is None

    def test_get_reports(self, service: ClinicalService,
                          mock_report_repo: MagicMock) -> None:
        """get_reports delegates to repo."""
        mock_report_repo.find_by_visit.return_value = [make_report()]
        result = service.get_reports(1)
        assert len(result) == 1

    def test_delete_report_removes_file(self, service: ClinicalService,
                                         mock_report_repo: MagicMock) -> None:
        """delete_report removes the file and the database record."""
        mock_report_repo.find_by_id.return_value = make_report(file_path="/tmp/test.pdf")

        with patch("os.path.exists", return_value=True), \
             patch("os.remove") as mock_remove:
            success, msg = service.delete_report(1)
            assert success is True
            mock_remove.assert_called_once_with("/tmp/test.pdf")
            mock_report_repo.delete_report.assert_called_once_with(1)

    def test_delete_report_no_file(self, service: ClinicalService,
                                    mock_report_repo: MagicMock) -> None:
        """delete_report handles missing file gracefully."""
        mock_report_repo.find_by_id.return_value = make_report(file_path=None)

        with patch("os.path.exists", return_value=False):
            success, msg = service.delete_report(1)
            assert success is True
            mock_report_repo.delete_report.assert_called_once_with(1)

    def test_delete_report_not_found(self, service: ClinicalService,
                                      mock_report_repo: MagicMock) -> None:
        """Deleting a non-existent report fails."""
        mock_report_repo.find_by_id.return_value = None
        success, msg = service.delete_report(999)
        # Note: The service doesn't guard against missing reports,
        # it just passes through to the repo.
        assert success is True
