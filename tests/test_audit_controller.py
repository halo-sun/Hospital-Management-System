"""Tests for the real, repository-backed audit-log controller."""
from datetime import date
from unittest.mock import MagicMock

import pytest

from src.auth.exceptions import PermissionDeniedError
from src.constants import Role
from src.controllers.audit_controller import AuditController


class FakeAuth:
    def __init__(self, role=None):
        self.current_role = role


@pytest.fixture
def service():
    return MagicMock()


@pytest.fixture
def admin_controller(service):
    return AuditController(FakeAuth(Role.ADMIN), service)


def test_admin_reads_persisted_logs(admin_controller, service):
    service.list_logs.return_value = [{"log_id": 7, "action": "LOGIN"}]
    assert admin_controller.list_audit_logs() == [{"log_id": 7, "action": "LOGIN"}]
    service.list_logs.assert_called_once_with(None, None, None)


@pytest.mark.parametrize("role", [None, Role.DOCTOR, Role.RECEPTIONIST])
def test_non_admin_is_denied(role, service):
    with pytest.raises(PermissionDeniedError):
        AuditController(FakeAuth(role), service).list_audit_logs()


def test_filters_are_forwarded(admin_controller, service):
    start, end = date(2026, 1, 1), date(2026, 1, 31)
    admin_controller.list_audit_logs({"start_date": start, "end_date": end, "action": "LOGIN"})
    service.list_logs.assert_called_once_with(start, end, "LOGIN")


def test_invalid_filter_date_is_rejected(admin_controller):
    with pytest.raises(ValueError):
        admin_controller.list_audit_logs({"start_date": "2026-01-01"})
