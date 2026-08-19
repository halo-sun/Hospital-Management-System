"""Department service – business logic for department management.

Validates input (reusing ``src.utils.validators``), enforces the
case-insensitive duplicate-name policy, and translates database-level
constraint errors (e.g. deleting a department that still has doctors
— ``ON DELETE RESTRICT``) into user-facing messages.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import mysql.connector

from src.repositories.department_repository import DepartmentRepository
from src.utils.validators import (
    validate_department_name,
    strip_control_characters,
)

logger = logging.getLogger(__name__)


class DepartmentService:
    """Handles department CRUD against the real ``departments`` table."""

    def __init__(self, repo: Optional[DepartmentRepository] = None) -> None:
        """Initialize DepartmentService.

        Args:
            repo: Repository to use (injectable for tests).
                Defaults to the real ``DepartmentRepository``.
        """
        self._repo = repo or DepartmentRepository()

    # ── Queries ────────────────────────────────────────────────

    def list_departments(self) -> List[Dict[str, Any]]:
        """Return all departments with doctor counts, sorted by name.

        Returns:
            List of department dicts (department_id, department_name,
            description, doctor_count).
        """
        return self._repo.find_all_departments()

    def get_department(self, department_id: int) -> Optional[Dict[str, Any]]:
        """Return a department by ID.

        Args:
            department_id: The department ID.

        Returns:
            Department record or None.
        """
        return self._repo.find_by_id("department_id", department_id)

    # ── Mutations ─────────────────────────────────────────────

    def create_department(
        self, department_name: str, description: str = "",
    ) -> Tuple[bool, str, Optional[int]]:
        """Create a new department.

        Args:
            department_name: The department's display name.
            description: Short description of the department.

        Returns:
            Tuple of (success, message, new_id_or_None).
        """
        valid, msg = validate_department_name(department_name)
        if not valid:
            return False, msg, None

        name = department_name.strip()
        if self._repo.find_by_name(name):
            return False, "A department with this name already exists.", None

        data: Dict[str, Any] = {
            "department_name": name,
            "description": strip_control_characters(description).strip(),
        }
        try:
            dept_id = self._repo.create_department(data)
        except mysql.connector.IntegrityError:
            # Unique key on department_name — raced another insert.
            return False, "A department with this name already exists.", None

        logger.info("Department created: %s (id=%d)", name, dept_id)
        return True, f"Department '{name}' created successfully.", dept_id

    def update_department(
        self,
        department_id: int,
        department_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Update a department.

        Only the fields supplied are changed; pass None to keep the
        current value.

        Args:
            department_id: The department ID.
            department_name: New name (optional).
            description: New description (optional).

        Returns:
            Tuple of (success, message).
        """
        existing = self._repo.find_by_id("department_id", department_id)
        if not existing:
            return False, "Department not found."

        data: Dict[str, Any] = {}
        if department_name is not None:
            valid, msg = validate_department_name(department_name)
            if not valid:
                return False, msg
            name = department_name.strip()
            # Renaming to another department's name is a conflict.
            dup = self._repo.find_by_name(name)
            if dup and dup["department_id"] != department_id:
                return False, "A department with this name already exists."
            data["department_name"] = name
        if description is not None:
            data["description"] = strip_control_characters(description).strip()

        if not data:
            return True, "No changes to apply."

        self._repo.update_department(department_id, data)
        logger.info("Department updated: %s", department_id)
        return True, "Department updated successfully."

    def delete_department(self, department_id: int) -> Tuple[bool, str]:
        """Delete a department.

        Args:
            department_id: The department ID.

        Returns:
            Tuple of (success, message).
        """
        existing = self._repo.find_by_id("department_id", department_id)
        if not existing:
            return False, "Department not found."

        try:
            self._repo.delete_department(department_id)
        except mysql.connector.IntegrityError:
            # FK fk_doctors_department is ON DELETE RESTRICT — the
            # department still has doctors assigned.
            return (
                False,
                "Cannot delete this department because doctors are still "
                "assigned to it. Reassign or remove those doctors first.",
            )

        logger.info("Department deleted: %s", department_id)
        return True, "Department deleted successfully."
