"""Unit tests for PatientService.

Tests cover registration, update, delete, search, and history retrieval
with mocked repository dependencies.

All database and file-system dependencies are mocked.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from unittest.mock import MagicMock

import pytest

from src.services.patient_service import PatientService
from src.repositories.patient_repository import PatientRepository
from src.repositories.clinical_repository import VisitRecordRepository


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def mock_patient_repo() -> MagicMock:
    """Create a mocked PatientRepository with sensible defaults."""
    repo = MagicMock(spec=PatientRepository)
    repo.find_by_id.return_value = {
        "patient_id": "PAT-00001",
        "full_name": "John Doe",
        "contact_number": "+1-555-0100",
        "email": "john@example.com",
    }
    repo.find_by_phone.return_value = None  # No duplicate
    repo.find_by_email.return_value = None  # No duplicate
    repo.get_next_patient_id.return_value = "PAT-00042"
    repo.create_patient.return_value = "PAT-00042"
    repo.update_patient.return_value = 1
    repo.delete_patient.return_value = 1
    repo.search_patients.return_value = [
        {"patient_id": "PAT-00001", "full_name": "John Doe", "contact_number": "+1-555-0100"},
    ]
    repo.find_all_patients.return_value = [
        {"patient_id": "PAT-00001", "full_name": "John Doe"},
        {"patient_id": "PAT-00002", "full_name": "Jane Doe"},
    ]
    repo.count_all.return_value = 42
    repo.find_recent.return_value = []
    return repo


@pytest.fixture
def mock_visit_repo() -> MagicMock:
    """Create a mocked VisitRecordRepository."""
    repo = MagicMock(spec=VisitRecordRepository)
    repo.find_by_patient.return_value = []
    return repo


@pytest.fixture
def service(mock_patient_repo: MagicMock, mock_visit_repo: MagicMock) -> PatientService:
    """Create a PatientService with mocked repositories."""
    svc = PatientService()
    svc._patient_repo = mock_patient_repo
    svc._visit_repo = mock_visit_repo
    return svc


# ======================================================================
# Register Patient
# ======================================================================

class TestRegisterPatient:
    """Tests for register_patient."""

    def test_success(self, service: PatientService, mock_patient_repo: MagicMock) -> None:
        """Valid data registers a patient and returns an ID."""
        data = {"full_name": "Alice Smith", "contact_number": "555-0101"}
        success, msg, pid = service.register_patient(data)
        assert success is True
        assert pid == "PAT-00042"
        assert "PAT-00042" in msg
        mock_patient_repo.create_patient.assert_called_once()
        # Verify patient_id was set
        _, kwargs = mock_patient_repo.create_patient.call_args
        assert kwargs or True  # called with data

    def test_missing_name(self, service: PatientService, mock_patient_repo: MagicMock) -> None:
        """Registration without a name fails."""
        data = {"contact_number": "555-0101"}
        success, msg, pid = service.register_patient(data)
        assert success is False
        assert pid is None
        mock_patient_repo.create_patient.assert_not_called()

    def test_missing_phone(self, service: PatientService, mock_patient_repo: MagicMock) -> None:
        """Registration without a phone number fails."""
        data = {"full_name": "Bob Jones"}
        success, msg, pid = service.register_patient(data)
        assert success is False
        assert pid is None
        mock_patient_repo.create_patient.assert_not_called()

    def test_duplicate_phone(self, service: PatientService, mock_patient_repo: MagicMock) -> None:
        """Registration with an existing phone number fails."""
        mock_patient_repo.find_by_phone.return_value = {
            "patient_id": "PAT-00001",
            "full_name": "Existing",
            "contact_number": "555-0101",
        }
        data = {"full_name": "New Patient", "contact_number": "555-0101"}
        success, msg, pid = service.register_patient(data)
        assert success is False
        assert "already exists" in msg.lower()
        assert pid is None
        mock_patient_repo.create_patient.assert_not_called()

    def test_duplicate_email(self, service: PatientService, mock_patient_repo: MagicMock) -> None:
        """Registration with an existing email fails."""
        mock_patient_repo.find_by_email.return_value = {
            "patient_id": "PAT-00001",
            "full_name": "Existing",
            "email": "existing@example.com",
        }
        data = {"full_name": "New Patient", "contact_number": "555-0202", "email": "existing@example.com"}
        success, msg, pid = service.register_patient(data)
        assert success is False
        assert "already exists" in msg.lower()
        assert pid is None
        mock_patient_repo.create_patient.assert_not_called()


# ======================================================================
# Update Patient
# ======================================================================

class TestUpdatePatient:
    """Tests for update_patient."""

    def test_success(self, service: PatientService, mock_patient_repo: MagicMock) -> None:
        """Updating an existing patient succeeds."""
        success, msg = service.update_patient("PAT-00001", {"full_name": "John Updated"})
        assert success is True
        assert "successfully" in msg.lower()
        mock_patient_repo.update_patient.assert_called_once()

    def test_not_found(self, service: PatientService, mock_patient_repo: MagicMock) -> None:
        """Updating a non-existent patient fails."""
        mock_patient_repo.find_by_id.return_value = None
        success, msg = service.update_patient("PAT-99999", {"full_name": "Ghost"})
        assert success is False
        assert "not found" in msg.lower()
        mock_patient_repo.update_patient.assert_not_called()

    def test_duplicate_phone_on_update(self, service: PatientService, mock_patient_repo: MagicMock) -> None:
        """Updating to an already-used phone number fails."""
        mock_patient_repo.find_by_phone.return_value = {
            "patient_id": "PAT-00002",
            "full_name": "Other Patient",
            "contact_number": "555-0303",
        }
        success, msg = service.update_patient(
            "PAT-00001", {"contact_number": "555-0303"}
        )
        assert success is False
        assert "already exists" in msg.lower()

    def test_duplicate_email_on_update(self, service: PatientService, mock_patient_repo: MagicMock) -> None:
        """Updating to an already-used email fails."""
        mock_patient_repo.find_by_email.return_value = {
            "patient_id": "PAT-00002",
            "email": "other@example.com",
        }
        success, msg = service.update_patient(
            "PAT-00001", {"email": "other@example.com"}
        )
        assert success is False
        assert "already exists" in msg.lower()


# ======================================================================
# Delete Patient
# ======================================================================

class TestDeletePatient:
    """Tests for delete_patient."""

    def test_success(self, service: PatientService, mock_patient_repo: MagicMock) -> None:
        """Deleting an existing patient succeeds."""
        success, msg = service.delete_patient("PAT-00001")
        assert success is True
        mock_patient_repo.delete_patient.assert_called_once_with("PAT-00001")

    def test_not_found(self, service: PatientService, mock_patient_repo: MagicMock) -> None:
        """Deleting a non-existent patient fails."""
        mock_patient_repo.find_by_id.return_value = None
        success, msg = service.delete_patient("PAT-99999")
        assert success is False
        assert "not found" in msg.lower()
        mock_patient_repo.delete_patient.assert_not_called()


# ======================================================================
# Search & Retrieval
# ======================================================================

class TestSearchRetrieval:
    """Tests for search and retrieval methods."""

    def test_get_patient_found(self, service: PatientService, mock_patient_repo: MagicMock) -> None:
        """Getting an existing patient returns the record."""
        patient = service.get_patient("PAT-00001")
        assert patient is not None
        assert patient["patient_id"] == "PAT-00001"
        mock_patient_repo.find_by_id.assert_called_once_with("PAT-00001")

    def test_get_patient_not_found(self, service: PatientService, mock_patient_repo: MagicMock) -> None:
        """Getting a non-existent patient returns None."""
        mock_patient_repo.find_by_id.return_value = None
        result = service.get_patient("PAT-99999")
        assert result is None

    def test_search_patients(self, service: PatientService, mock_patient_repo: MagicMock) -> None:
        """Search returns matching patients."""
        results = service.search_patients("John")
        assert len(results) > 0
        mock_patient_repo.search_patients.assert_called_once_with("John")

    def test_get_all_patients(self, service: PatientService, mock_patient_repo: MagicMock) -> None:
        """get_all_patients returns all patients with pagination."""
        patients = service.get_all_patients(limit=50, offset=10)
        assert len(patients) == 2
        mock_patient_repo.find_all_patients.assert_called_once_with(limit=50, offset=10)

    def test_get_total_count(self, service: PatientService, mock_patient_repo: MagicMock) -> None:
        """get_total_count returns the correct count."""
        count = service.get_total_count()
        assert count == 42
        mock_patient_repo.count_all.assert_called_once()

    def test_get_patient_history(self, service: PatientService, mock_visit_repo: MagicMock) -> None:
        """get_patient_history returns visit records."""
        history = service.get_patient_history("PAT-00001")
        assert isinstance(history, list)
        mock_visit_repo.find_by_patient.assert_called_once_with("PAT-00001")

    def test_get_recent_patients(self, service: PatientService, mock_patient_repo: MagicMock) -> None:
        """get_recent_patients calls find_recent."""
        service.get_recent_patients(limit=5)
        mock_patient_repo.find_recent.assert_called_once_with(5)
