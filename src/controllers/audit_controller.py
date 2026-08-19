"""Audit log controller – coordinates real audit-log viewing requests."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from src.auth.rbac import require_role
from src.constants import Role
from src.controllers.auth_controller import AuthController
from src.services.audit_service import AuditService


class AuditController:
    """Handles real, immutable audit-log queries for administrators."""

    def __init__(self, auth_ctrl: Optional[AuthController] = None,
                 audit_service: Optional[AuditService] = None) -> None:
        self._auth_ctrl = auth_ctrl or AuthController()
        self._audit_service = audit_service or AuditService()

    @property
    def _current_role(self) -> Optional[str]:
        return self._auth_ctrl.current_role

    @require_role(Role.ADMIN)
    def list_audit_logs(
        self, filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Return persisted audit records, newest first, with optional filters."""
        filters = filters or {}
        start_date = filters.get("start_date")
        end_date = filters.get("end_date")
        action = filters.get("action")
        if start_date is not None and not isinstance(start_date, date):
            raise ValueError("start_date must be a date.")
        if end_date is not None and not isinstance(end_date, date):
            raise ValueError("end_date must be a date.")
        return self._audit_service.list_logs(start_date, end_date, action)
