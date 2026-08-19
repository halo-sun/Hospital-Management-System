"""Security audit regression tests.

Covers the RBAC gates on the appointment/report controllers and the
SQL-injection allow-list hardening on ``BaseRepository`` (ORDER BY,
LIMIT/OFFSET).
"""
from __future__ import annotations

from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from src.auth.exceptions import PermissionDeniedError
from src.controllers.appointment_controller import AppointmentController
from src.controllers.report_controller import ReportController
from src.repositories.base_repository import BaseRepository
from src.constants import Role


class FakeAuth:
    """Minimal stand-in for AuthController exposing current_role."""

    def __init__(self, role: Optional[str] = None) -> None:
        self.current_role = role


# ── Appointment controller RBAC ───────────────────────────────


class TestAppointmentRbac:
    """Appointment booking/management methods must be role-gated."""

    def test_no_session_denied(self) -> None:
        """No logged-in user cannot book or read appointments."""
        ctrl = AppointmentController(auth_ctrl=FakeAuth(None))
        with pytest.raises(PermissionDeniedError):
            ctrl.get_upcoming_appointments()
        with pytest.raises(PermissionDeniedError):
            ctrl.book_appointment({}, user_id=1)

    def test_doctor_cannot_book(self) -> None:
        """Doctors cannot book appointments (receptionist/admin only)."""
        ctrl = AppointmentController(auth_ctrl=FakeAuth(Role.DOCTOR))
        with pytest.raises(PermissionDeniedError):
            ctrl.book_appointment({}, user_id=1)

    def test_receptionist_allowed(self) -> None:
        """A receptionist can call booking methods."""
        ctrl = AppointmentController(auth_ctrl=FakeAuth(Role.RECEPTIONIST))
        with patch.object(ctrl, "_appointment_service") as svc:
            svc.get_upcoming_appointments.return_value = []
            assert ctrl.get_upcoming_appointments() == []


# ── Report controller RBAC ────────────────────────────────────


class TestReportRbac:
    """Analytics/export must be admin(+receptionist dashboard); clinical passthroughs doctor-only."""

    def test_no_session_denied(self) -> None:
        """No logged-in user cannot read analytics."""
        ctrl = ReportController(auth_ctrl=FakeAuth(None))
        with pytest.raises(PermissionDeniedError):
            ctrl.get_dashboard_stats()

    def test_doctor_denied_analytics(self) -> None:
        """Doctors cannot access admin analytics."""
        ctrl = ReportController(auth_ctrl=FakeAuth(Role.DOCTOR))
        with pytest.raises(PermissionDeniedError):
            ctrl.get_analytics_data(None, None)  # type: ignore[arg-type]

    def test_receptionist_allowed_dashboard(self) -> None:
        """Receptionists can read the dashboard stats."""
        ctrl = ReportController(auth_ctrl=FakeAuth(Role.RECEPTIONIST))
        with patch.object(ctrl, "_report_service") as svc:
            svc.get_dashboard_stats.return_value = {"total_patients": 1}
            assert ctrl.get_dashboard_stats()["total_patients"] == 1

    def test_clinical_passthrough_doctor_only(self) -> None:
        """The legacy clinical passthroughs on ReportController are doctor-only."""
        ctrl = ReportController(auth_ctrl=FakeAuth(Role.ADMIN))
        with pytest.raises(PermissionDeniedError):
            ctrl.get_visit(1)


# ── SQL injection allow-list (BaseRepository) ─────────────────


class TestOrderByAllowList:
    """ORDER BY / LIMIT / OFFSET must never accept raw input."""

    @pytest.fixture
    def repo(self) -> BaseRepository:
        return BaseRepository("users")

    def test_valid_order_by_accepted(self, repo: BaseRepository) -> None:
        """Plain identifier + direction passes through."""
        with patch("src.repositories.base_repository.DatabaseConnection.execute_query") as eq:
            eq.return_value = []
            repo.find_all(order_by="full_name ASC", limit=10)
            query = eq.call_args.args[0]
            assert "ORDER BY full_name ASC" in query

    def test_composite_order_by_accepted(self, repo: BaseRepository) -> None:
        """Comma-separated identifiers with directions are allowed."""
        with patch("src.repositories.base_repository.DatabaseConnection.execute_query") as eq:
            eq.return_value = []
            repo.find_all(order_by="department_id ASC, full_name DESC", limit=5)
            query = eq.call_args.args[0]
            assert "ORDER BY department_id ASC, full_name DESC" in query

    @pytest.mark.parametrize("malicious", [
        "full_name; DROP TABLE users; --",
        "full_name) UNION SELECT password_hash FROM users--",
        "full_name ASC, (SELECT 1)",
        "full_name` = 'x' OR '1'='1",
        "full_name DESC /*",
    ])
    def test_malicious_order_by_rejected(
        self, repo: BaseRepository, malicious: str,
    ) -> None:
        """Anything beyond identifiers/ASC/DESC raises ValueError (fail closed)."""
        with pytest.raises(ValueError):
            repo.find_all(order_by=malicious)

    def test_non_integer_limit_rejected(self, repo: BaseRepository) -> None:
        """A string limit cannot be concatenated into the query."""
        with pytest.raises(ValueError):
            repo.find_all(limit="5 OR 1=1")

    def test_negative_limit_rejected(self, repo: BaseRepository) -> None:
        with pytest.raises(ValueError):
            repo.find_all(limit=-1)

    def test_integer_limit_coerced(self, repo: BaseRepository) -> None:
        """Numeric strings are coerced safely."""
        with patch("src.repositories.base_repository.DatabaseConnection.execute_query") as eq:
            eq.return_value = []
            repo.find_all(limit="10")
            query = eq.call_args.args[0]
            assert "LIMIT 10" in query

    def test_search_uses_parameterized_like(self, repo: BaseRepository) -> None:
        """LIKE wildcards go through %s parameters, never concatenation."""
        with patch("src.repositories.base_repository.DatabaseConnection.execute_query") as eq:
            eq.return_value = []
            repo.search(["username"], "x'; DROP TABLE users; --")
            params = eq.call_args.args[1]
            assert any("%x" in str(p) for p in params)
            # The raw payload must not appear in the SQL text.
            query = eq.call_args.args[0]
            assert "DROP TABLE" not in query
