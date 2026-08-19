"""Unit tests for PatientController.

Validation tests now call the centralised ``src.utils.validators``
functions directly (the controller delegates to them).  CRUD tests
still exercise ``PatientController`` with mocked services.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from unittest.mock import MagicMock, patch

import pytest

from src.controllers.patient_controller import PatientController
from src.utils.validators import validate_patient_data, validate_search
from src.constants import AuditAction, Role
from src.auth.exceptions import PermissionDeniedError
from datetime import date


# ======================================================================
# RBAC gate
# ======================================================================

class TestRbacGate:
    """Patient operations must be gated to the correct roles."""

    def test_no_session_denied(self, mock_auth_ctrl: MagicMock) -> None:
        """No logged-in user is denied."""
        mock_auth_ctrl.current_role = None
        ctrl = PatientController(auth_ctrl=mock_auth_ctrl)
        with pytest.raises(PermissionDeniedError):
            ctrl.get_all_patients()

    def test_deletion_admin_only(self, mock_auth_ctrl: MagicMock) -> None:
        """delete_patient is admin-only even for receptionists."""
        mock_auth_ctrl.current_role = Role.RECEPTIONIST
        ctrl = PatientController(auth_ctrl=mock_auth_ctrl)
        with pytest.raises(PermissionDeniedError):
            ctrl.delete_patient("PAT-00001")


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def mock_patient_service() -> MagicMock:
    """Create a mocked PatientService with sensible defaults."""
    service = MagicMock()
    service.register_patient.return_value = (True, "Registered", "PAT-00001")
    service.update_patient.return_value = (True, "Updated")
    service.delete_patient.return_value = (True, "Deleted")
    service.get_patient.return_value = {
        "patient_id": "PAT-00001",
        "full_name": "John Doe",
        "contact_number": "+1-555-0100",
        "gender": "Male",
        "email": "john@example.com",
    }
    service.search_patients.return_value = [
        {"patient_id": "PAT-00001", "full_name": "John Doe", "contact_number": "+1-555-0100"},
    ]
    service.get_all_patients.return_value = [
        {"patient_id": "PAT-00001", "full_name": "John Doe"},
        {"patient_id": "PAT-00002", "full_name": "Jane Doe"},
    ]
    service.get_patient_history.return_value = []
    service.get_recent_patients.return_value = []
    service.get_total_count.return_value = 42
    return service


@pytest.fixture
def mock_audit_service() -> MagicMock:
    """Create a mocked AuditService."""
    service = MagicMock()
    service.log.return_value = None
    return service


@pytest.fixture
def mock_auth_ctrl() -> MagicMock:
    """Create a mocked AuthController with an Admin session."""
    auth = MagicMock()
    auth.current_role = "Admin"
    return auth


@pytest.fixture
def controller(
    mock_patient_service: MagicMock,
    mock_audit_service: MagicMock,
    mock_auth_ctrl: MagicMock,
) -> PatientController:
    """Create a PatientController with mocked dependencies."""
    ctrl = PatientController(auth_ctrl=mock_auth_ctrl)
    ctrl._patient_service = mock_patient_service
    ctrl._audit_service = mock_audit_service
    return ctrl


# ======================================================================
# Validation  (via centralised validators module)
# ======================================================================

class TestValidatePatientData:
    """Tests for ``validate_patient_data`` from ``src.utils.validators``."""

    def test_valid_data(self) -> None:
        """All valid fields pass validation."""
        data = {
            "full_name": "John Doe",
            "contact_number": "+1-555-0100",
            "email": "john@example.com",
            "date_of_birth": "1990-01-15",
            "gender": "Male",
            "blood_group": "A+",
        }
        valid, msg = validate_patient_data(data)
        assert valid is True, msg

    def test_missing_name(self) -> None:
        """Registration without a name fails."""
        data = {"contact_number": "555-0100"}
        valid, msg = validate_patient_data(data)
        assert valid is False
        assert "name" in msg.lower()

    def test_missing_phone(self) -> None:
        """Registration without a phone number fails."""
        data = {"full_name": "John Doe"}
        valid, msg = validate_patient_data(data)
        assert valid is False
        assert "contact" in msg.lower() or "phone" in msg.lower()

    def test_invalid_email(self) -> None:
        """An incorrectly formatted email fails."""
        data = {"full_name": "John Doe", "contact_number": "555-0100", "email": "not-an-email"}
        valid, msg = validate_patient_data(data)
        assert valid is False
        assert "email" in msg.lower()

    def test_invalid_phone(self) -> None:
        """A phone number with invalid characters fails."""
        data = {"full_name": "John Doe", "contact_number": "abc"}
        valid, msg = validate_patient_data(data)
        assert valid is False
        assert "phone" in msg.lower() or "contact" in msg.lower()

    def test_empty_phone_fails(self) -> None:
        """An empty phone number fails (required field)."""
        data = {"full_name": "John Doe", "contact_number": ""}
        valid, msg = validate_patient_data(data)
        assert valid is False

    def test_invalid_name_chars(self) -> None:
        """A name with numbers fails."""
        data = {"full_name": "John123", "contact_number": "555-0100"}
        valid, msg = validate_patient_data(data)
        assert valid is False
        assert "invalid" in msg.lower() or "characters" in msg.lower()

    def test_invalid_gender(self) -> None:
        """An invalid gender string fails."""
        data = {"full_name": "John Doe", "contact_number": "555-0100", "gender": "Xenon"}
        valid, msg = validate_patient_data(data)
        assert valid is False
        assert "gender" in msg.lower()

    def test_invalid_blood_group(self) -> None:
        """An invalid blood group fails."""
        data = {"full_name": "John Doe", "contact_number": "555-0100", "blood_group": "Super-O"}
        valid, msg = validate_patient_data(data)
        assert valid is False
        assert "blood" in msg.lower()

    def test_invalid_date_of_birth(self) -> None:
        """An incorrectly formatted DOB fails."""
        data = {"full_name": "John Doe", "contact_number": "555-0100", "date_of_birth": "32-13-2020"}
        valid, msg = validate_patient_data(data)
        assert valid is False

    def test_future_date_of_birth(self) -> None:
        """A future date of birth fails."""
        data = {"full_name": "John Doe", "contact_number": "555-0100", "date_of_birth": "2099-01-01"}
        valid, msg = validate_patient_data(data)
        assert valid is False
        assert "future" in msg.lower()

    def test_edit_skips_name_requirement(self) -> None:
        """Editing allows empty name (it was already set)."""
        data = {"contact_number": "555-0101"}
        valid, msg = validate_patient_data(data, is_edit=True)
        assert valid is True, msg


class TestValidateSearch:
    """Tests for ``validate_search`` from ``src.utils.validators``."""

    def test_valid_search(self) -> None:
        """A search term with 2+ characters is valid."""
        valid, msg = validate_search("Jo")
        assert valid is True

    def test_empty_search(self) -> None:
        """An empty search term fails."""
        valid, msg = validate_search("")
        assert valid is False

    def test_short_search(self) -> None:
        """A single-character search fails."""
        valid, msg = validate_search("J")
        assert valid is False
        assert "at least 2" in msg.lower()


# ======================================================================
# CRUD Operations
# ======================================================================

class TestRegisterPatient:
    """Tests for register_patient."""

    def test_success(self, controller: PatientController, mock_patient_service: MagicMock) -> None:
        """A valid registration succeeds and returns a patient ID."""
        data = {"full_name": "Jane Doe", "contact_number": "555-0200"}
        success, msg, pid = controller.register_patient(data, audit_user_id=1)
        assert success is True
        assert pid == "PAT-00001"
        mock_patient_service.register_patient.assert_called_once()

    def test_validation_failure(self, controller: PatientController, mock_patient_service: MagicMock) -> None:
        """Invalid data fails before calling the service."""
        data = {"full_name": "", "contact_number": ""}
        success, msg, pid = controller.register_patient(data, audit_user_id=1)
        assert success is False
        assert pid is None
        mock_patient_service.register_patient.assert_not_called()

    def test_audit_on_success(self, controller: PatientController, mock_audit_service: MagicMock) -> None:
        """Successful registration triggers audit log."""
        data = {"full_name": "Jane Doe", "contact_number": "555-0200"}
        controller.register_patient(data, audit_user_id=1)
        mock_audit_service.log.assert_called_once()


class TestUpdatePatient:
    """Tests for update_patient."""

    def test_success(self, controller: PatientController, mock_patient_service: MagicMock) -> None:
        """A valid update succeeds."""
        data = {"contact_number": "555-0300"}
        success, msg = controller.update_patient("PAT-00001", data, audit_user_id=1)
        assert success is True
        mock_patient_service.update_patient.assert_called_once_with("PAT-00001", data)

    def test_validation_failure(self, controller: PatientController, mock_patient_service: MagicMock) -> None:
        """Invalid edit data fails before calling the service."""
        data = {"contact_number": "abc"}
        success, msg = controller.update_patient("PAT-00001", data, audit_user_id=1)
        assert success is False
        mock_patient_service.update_patient.assert_not_called()

    def test_audit_on_success(self, controller: PatientController, mock_audit_service: MagicMock) -> None:
        """Successful update triggers audit."""
        data = {"full_name": "Jane Updated", "contact_number": "555-0400"}
        controller.update_patient("PAT-00001", data, audit_user_id=1)
        mock_audit_service.log.assert_called_once()


class TestDeletePatient:
    """Tests for delete_patient."""

    def test_success(self, controller: PatientController, mock_patient_service: MagicMock) -> None:
        """Delete succeeds when patient exists."""
        success, msg = controller.delete_patient("PAT-00001", audit_user_id=1)
        assert success is True
        mock_patient_service.delete_patient.assert_called_once_with("PAT-00001")

    def test_audit_on_success(self, controller: PatientController, mock_audit_service: MagicMock) -> None:
        """Successful deletion triggers audit."""
        controller.delete_patient("PAT-00001", audit_user_id=1)
        mock_audit_service.log.assert_called_once()

    def test_no_audit_without_user(self, controller: PatientController, mock_audit_service: MagicMock) -> None:
        """No audit entry without a user ID."""
        controller.delete_patient("PAT-00001")
        mock_audit_service.log.assert_not_called()


class TestGetPatient:
    """Tests for get_patient."""

    def test_found(self, controller: PatientController, mock_patient_service: MagicMock) -> None:
        """Getting an existing patient returns the record."""
        patient = controller.get_patient("PAT-00001")
        assert patient is not None
        assert patient["full_name"] == "John Doe"
        mock_patient_service.get_patient.assert_called_once_with("PAT-00001")

    def test_not_found(self, controller: PatientController, mock_patient_service: MagicMock) -> None:
        """Getting a non-existent patient returns None."""
        mock_patient_service.get_patient.return_value = None
        result = controller.get_patient("PAT-99999")
        assert result is None


class TestSearchPatients:
    """Tests for search_patients."""

    def test_valid_search(self, controller: PatientController, mock_patient_service: MagicMock) -> None:
        """A valid search returns results."""
        success, msg, results = controller.search_patients("John")
        assert success is True
        assert len(results) > 0
        mock_patient_service.search_patients.assert_called_once_with("John")

    def test_short_search(self, controller: PatientController, mock_patient_service: MagicMock) -> None:
        """A search term shorter than 2 characters fails validation."""
        success, msg, results = controller.search_patients("J")
        assert success is False
        assert len(results) == 0
        mock_patient_service.search_patients.assert_not_called()


class TestGetAllPatients:
    """Tests for get_all_patients."""

    def test_returns_list(self, controller: PatientController, mock_patient_service: MagicMock) -> None:
        """get_all_patients returns a list of patients."""
        patients = controller.get_all_patients(limit=10)
        assert len(patients) == 2
        mock_patient_service.get_all_patients.assert_called_once_with(10, 0)


class TestGetPatientHistory:
    """Tests for get_patient_history."""

    def test_returns_history(self, controller: PatientController, mock_patient_service: MagicMock) -> None:
        """get_patient_history returns visit records."""
        history = controller.get_patient_history("PAT-00001")
        assert isinstance(history, list)
        mock_patient_service.get_patient_history.assert_called_once_with("PAT-00001")


class TestGetTotalCount:
    """Tests for get_total_count."""

    def test_returns_count(self, controller: PatientController, mock_patient_service: MagicMock) -> None:
        """get_total_count returns the total number of patients."""
        count = controller.get_total_count()
        assert count == 42
        mock_patient_service.get_total_count.assert_called_once()
