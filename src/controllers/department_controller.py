"""Department controller – coordinates admin department management.

All methods are RBAC-gated to admins via the shared ``@require_role``
decorator and delegate to :class:`DepartmentService`, which persists
to the real ``departments`` table (via ``DepartmentRepository``).
The doctor form's department dropdown and the admin department view
both source from this controller, so doctor and department data stay
consistent.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from src.controllers.auth_controller import AuthController
from src.auth.rbac import require_role
from src.constants import Role
from src.services.department_service import DepartmentService

logger = logging.getLogger(__name__)


class DepartmentController:
    """Handles department requests from the GUI layer (admin only)."""

    def __init__(
        self,
        auth_ctrl: Optional[AuthController] = None,
        service: Optional[DepartmentService] = None,
    ) -> None:
        """Initialise DepartmentController.

        Args:
            auth_ctrl: The shared AuthController used for RBAC checks.
                Defaults to a new instance; the admin factory passes the
                application-wide controller so the session is shared.
            service: The department service (injectable for tests).
                Defaults to the real ``DepartmentService``.
        """
        self._auth_ctrl = auth_ctrl or AuthController()
        self._service = service or DepartmentService()

    @property
    def _current_role(self) -> Optional[str]:
        """Return the current user's role for ``@require_role`` checks."""
        return self._auth_ctrl.current_role

    # ── Department operations ─────────────────────────────────

    @require_role(Role.ADMIN)
    def list_departments(self) -> List[Dict[str, Any]]:
        """Return all departments, sorted by name, with doctor counts.

        Returns:
            List of dicts with department_id, department_name,
            description, and doctor_count.
        """
        return self._service.list_departments()

    @require_role(Role.ADMIN)
    def get_department(self, department_id: int) -> Optional[Dict[str, Any]]:
        """Return a department by ID.

        Args:
            department_id: The department ID.

        Returns:
            Department record or None.
        """
        return self._service.get_department(department_id)

    @require_role(Role.ADMIN)
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
        return self._service.create_department(department_name, description)

    @require_role(Role.ADMIN)
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
        return self._service.update_department(
            department_id,
            department_name=department_name,
            description=description,
        )

    @require_role(Role.ADMIN)
    def delete_department(self, department_id: int) -> Tuple[bool, str]:
        """Delete a department.

        Args:
            department_id: The department ID.

        Returns:
            Tuple of (success, message).
        """
        return self._service.delete_department(department_id)
