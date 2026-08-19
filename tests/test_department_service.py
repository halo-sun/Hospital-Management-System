"""Unit tests for the DepartmentService (real backend).

Exercises validation, case-insensitive duplicate handling,
control-character stripping, and the FK-RESTRICT delete messaging
against a mocked repository — no database required.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from unittest.mock import MagicMock

import mysql.connector
import pytest

from src.services.department_service import DepartmentService


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def service() -> DepartmentService:
    """A DepartmentService with a mocked repository."""
    return DepartmentService(repo=MagicMock())


@pytest.fixture
def mock_repo(service: DepartmentService) -> MagicMock:
    """Access the mocked DepartmentRepository."""
    return service._repo


def _dept(**overrides: Any) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "department_id": 2,
        "department_name": "Cardiology",
        "description": "Heart and cardiovascular diseases",
        "doctor_count": 3,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    data.update(overrides)
    return data


# ── Queries ───────────────────────────────────────────────────


class TestQueries:
    """list_departments / get_department."""

    def test_list_delegates(self, service: DepartmentService,
                            mock_repo: MagicMock) -> None:
        """list_departments returns the repo rows with doctor counts."""
        rows = [_dept(department_id=1, department_name="ENT")]
        mock_repo.find_all_departments.return_value = rows
        assert service.list_departments() == rows
        mock_repo.find_all_departments.assert_called_once()

    def test_get_found(self, service: DepartmentService,
                       mock_repo: MagicMock) -> None:
        """get_department returns the row when present."""
        mock_repo.find_by_id.return_value = _dept()
        result = service.get_department(2)
        assert result is not None
        assert result["department_name"] == "Cardiology"
        mock_repo.find_by_id.assert_called_once_with("department_id", 2)

    def test_get_not_found(self, service: DepartmentService,
                           mock_repo: MagicMock) -> None:
        """get_department returns None when absent."""
        mock_repo.find_by_id.return_value = None
        assert service.get_department(999) is None


# ── Create ────────────────────────────────────────────────────


class TestCreateDepartment:
    """create_department validation and persistence."""

    def test_missing_name_rejected(self, service: DepartmentService,
                                   mock_repo: MagicMock) -> None:
        """Empty/whitespace-only names are rejected before any DB call."""
        ok, msg, dept_id = service.create_department("   ")
        assert ok is False
        assert "required" in msg.lower()
        assert dept_id is None
        mock_repo.create_department.assert_not_called()

    def test_overlong_name_rejected(self, service: DepartmentService,
                                    mock_repo: MagicMock) -> None:
        """Names over 100 characters are rejected."""
        ok, msg, _ = service.create_department("X" * 101)
        assert ok is False
        assert "100 characters" in msg
        mock_repo.create_department.assert_not_called()

    def test_duplicate_rejected(self, service: DepartmentService,
                                mock_repo: MagicMock) -> None:
        """A case-insensitive duplicate name is rejected."""
        mock_repo.find_by_name.return_value = _dept()
        ok, msg, dept_id = service.create_department("cardiology")
        assert ok is False
        assert "already exists" in msg.lower()
        assert dept_id is None
        mock_repo.create_department.assert_not_called()

    def test_success_strips_and_inserts(self, service: DepartmentService,
                                        mock_repo: MagicMock) -> None:
        """Valid input is stripped, control chars removed, and inserted."""
        mock_repo.find_by_name.return_value = None
        mock_repo.create_department.return_value = 9
        ok, msg, dept_id = service.create_department(
            "  Oncology  ", "Cancer \x00care\x1b",
        )
        assert ok is True
        assert dept_id == 9
        assert "Oncology" in msg
        call_data = mock_repo.create_department.call_args.args[0]
        assert call_data["department_name"] == "Oncology"
        assert call_data["description"] == "Cancer care"

    def test_integrity_error_mapped_to_duplicate(
        self, service: DepartmentService, mock_repo: MagicMock,
    ) -> None:
        """A DB unique-key race surfaces as the duplicate message."""
        mock_repo.find_by_name.return_value = None
        mock_repo.create_department.side_effect = mysql.connector.IntegrityError(
            "Duplicate entry", errno=1062,
        )
        ok, msg, dept_id = service.create_department("Oncology")
        assert ok is False
        assert "already exists" in msg.lower()
        assert dept_id is None


# ── Update ────────────────────────────────────────────────────


class TestUpdateDepartment:
    """update_department partial-field semantics."""

    def test_not_found(self, service: DepartmentService,
                       mock_repo: MagicMock) -> None:
        """Updating a missing department reports an error."""
        mock_repo.find_by_id.return_value = None
        ok, msg = service.update_department(999, department_name="X")
        assert ok is False
        assert "not found" in msg.lower()
        mock_repo.update_department.assert_not_called()

    def test_invalid_name_rejected(self, service: DepartmentService,
                                   mock_repo: MagicMock) -> None:
        """An invalid new name is rejected before any write."""
        mock_repo.find_by_id.return_value = _dept()
        ok, msg = service.update_department(2, department_name="")
        assert ok is False
        mock_repo.update_department.assert_not_called()

    def test_duplicate_name_conflict(self, service: DepartmentService,
                                     mock_repo: MagicMock) -> None:
        """Renaming to another department's name is rejected."""
        mock_repo.find_by_id.return_value = _dept(department_id=2)
        mock_repo.find_by_name.return_value = _dept(department_id=8, department_name="ENT")
        ok, msg = service.update_department(2, department_name="ENT")
        assert ok is False
        assert "already exists" in msg.lower()

    def test_update_success(self, service: DepartmentService,
                            mock_repo: MagicMock) -> None:
        """Updating name/description persists both fields."""
        mock_repo.find_by_id.return_value = _dept()
        mock_repo.find_by_name.return_value = None
        ok, msg = service.update_department(
            2, department_name="Cardiac Sciences", description="Updated desc",
        )
        assert ok is True
        call_data = mock_repo.update_department.call_args.args[1]
        assert call_data["department_name"] == "Cardiac Sciences"
        assert call_data["description"] == "Updated desc"

    def test_keeps_name_when_omitted(self, service: DepartmentService,
                                     mock_repo: MagicMock) -> None:
        """Passing only a description leaves the name unchanged."""
        mock_repo.find_by_id.return_value = _dept()
        ok, _ = service.update_department(2, description="Just the desc")
        assert ok is True
        call_data = mock_repo.update_department.call_args.args[1]
        assert "department_name" not in call_data
        assert call_data["description"] == "Just the desc"

    def test_no_changes(self, service: DepartmentService,
                        mock_repo: MagicMock) -> None:
        """No fields supplied is a no-op success."""
        mock_repo.find_by_id.return_value = _dept()
        ok, msg = service.update_department(2)
        assert ok is True
        mock_repo.update_department.assert_not_called()


# ── Delete ────────────────────────────────────────────────────


class TestDeleteDepartment:
    """delete_department existence + FK-restrict messaging."""

    def test_not_found(self, service: DepartmentService,
                       mock_repo: MagicMock) -> None:
        """Deleting a non-existent department reports an error."""
        mock_repo.find_by_id.return_value = None
        ok, msg = service.delete_department(999)
        assert ok is False
        assert "not found" in msg.lower()
        mock_repo.delete_department.assert_not_called()

    def test_success(self, service: DepartmentService,
                     mock_repo: MagicMock) -> None:
        """Deleting an existing department removes it."""
        mock_repo.find_by_id.return_value = _dept()
        mock_repo.delete_department.return_value = 1
        ok, msg = service.delete_department(8)
        assert ok is True
        mock_repo.delete_department.assert_called_once_with(8)

    def test_fk_restrict_friendly_message(self, service: DepartmentService,
                                          mock_repo: MagicMock) -> None:
        """Deleting a department with doctors gives a clear message."""
        mock_repo.find_by_id.return_value = _dept()
        mock_repo.delete_department.side_effect = mysql.connector.IntegrityError(
            "Cannot delete or update a parent row", errno=1451,
        )
        ok, msg = service.delete_department(1)
        assert ok is False
        assert "doctors are still assigned" in msg.lower()
