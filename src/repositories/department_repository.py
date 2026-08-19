"""Department repository – dedicated data access for the ``departments`` table.

The single source of truth for department persistence.  Doctor CRUD
uses this class (via re-export from ``doctor_repository``) so the
admin department view, the doctor form's department dropdown, and the
doctor-profile queries all read from the same real table.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.repositories.base_repository import BaseRepository
from src.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class DepartmentRepository(BaseRepository):
    """Repository for department-related database operations."""

    def __init__(self) -> None:
        """Initialize DepartmentRepository."""
        super().__init__("departments")

    def find_all_departments(self) -> List[Dict[str, Any]]:
        """Find all departments with their current doctor counts.

        Returns:
            List of department records (with ``doctor_count``) ordered
            alphabetically by name.
        """
        query = """
            SELECT d.department_id,
                   d.department_name,
                   d.description,
                   d.created_at,
                   d.updated_at,
                   COUNT(doc.doctor_id) AS doctor_count
            FROM departments d
            LEFT JOIN doctors doc ON doc.department_id = d.department_id
            GROUP BY d.department_id, d.department_name, d.description,
                     d.created_at, d.updated_at
            ORDER BY d.department_name ASC
        """
        return DatabaseConnection.execute_query(query) or []

    def find_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find a department by name (case-insensitive).

        The unique index on ``department_name`` is case-sensitive under
        the default collation, so a case-insensitive lookup is done
        explicitly to mirror the app's duplicate-name policy.

        Args:
            name: Department name to search for.

        Returns:
            Department record or None.
        """
        query = """
            SELECT * FROM departments
            WHERE LOWER(department_name) = LOWER(%s)
            LIMIT 1
        """
        return DatabaseConnection.execute_query(
            query, (name,), fetch_one=True,
        )

    def create_department(self, data: Dict[str, Any]) -> int:
        """Insert a new department.

        Args:
            data: Dictionary of department fields.

        Returns:
            The new department's ID.
        """
        return self.insert(data)

    def update_department(self, department_id: int, data: Dict[str, Any]) -> int:
        """Update an existing department.

        Args:
            department_id: The department ID.
            data: Fields to update.

        Returns:
            Number of rows affected.
        """
        data["updated_at"] = __import__("datetime").datetime.now()
        return self.update("department_id", department_id, data)

    def delete_department(self, department_id: int) -> int:
        """Delete a department.

        Args:
            department_id: The department ID.

        Returns:
            Number of rows deleted.
        """
        return self.delete("department_id", department_id)

    def count_all(self) -> int:
        """Count total departments.

        Returns:
            Number of departments.
        """
        return self.count_where()

    def get_with_doctor_count(self) -> List[Dict[str, Any]]:
        """Get all departments with their doctor count.

        Returns:
            List of department records including doctor_count.
        """
        query = """
            SELECT d.*, COUNT(doc.doctor_id) as doctor_count
            FROM departments d
            LEFT JOIN doctors doc ON d.department_id = doc.department_id
            GROUP BY d.department_id
            ORDER BY d.department_name ASC
        """
        return DatabaseConnection.execute_query(query) or []
