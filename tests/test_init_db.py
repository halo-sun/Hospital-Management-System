"""Tests for database schema initialization (``src/database/init_db.py``).

Guards the two startup regressions that previously appeared in the logs:

1. **Noisy false error** — ``CREATE DATABASE IF NOT EXISTS`` on an
   existing database emits MySQL warning 1007, which the connection
   config's ``raise_on_warnings=True`` promoted to an exception, logging
   ``Database initialization failed`` on every launch.  The DDL
   connection must tolerate idempotent-DDL warnings.

2. **Missing table** — because the exception aborted init before any
   ``CREATE TABLE`` ran, newly-added tables (e.g. ``app_settings``)
   never got created on existing databases.  Every table referenced by
   the models/repositories must have a matching ``CREATE TABLE IF NOT
   EXISTS`` in the central ``SCHEMA_SQL`` list, and init must verify
   each one actually exists afterwards.

These tests run without a MySQL server (the connection is mocked).
"""
from __future__ import annotations

import logging
import re
from unittest.mock import patch

from src.database.init_db import SCHEMA_SQL, _schema_tables, initialize_database

# Every table the application's models/repositories reference.  If a new
# feature adds a table, it must also be declared in SCHEMA_SQL (the
# single central list) — the first test below enforces that.
EXPECTED_TABLES = {
    "roles",               # models/user.py RoleModel; user_repository
    "users",               # models/user.py User; user_repository
    "departments",         # models/department.py; department_repository
    "doctors",             # models/doctor.py Doctor; doctor_repository
    "patients",            # models/patient.py Patient; patient_repository
    "appointments",        # models/appointment.py; appointment_repository
    "medical_history",     # models/patient.py MedicalHistory
    "visit_records",       # models/clinical.py VisitRecord; clinical_repository
    "prescriptions",       # models/clinical.py Prescription; clinical_repository
    "test_reports",        # models/clinical.py TestReport; clinical_repository
    "audit_logs",          # models/audit.py AuditLog; audit_repository
    "app_settings",        # settings_repository (theme persistence)
    "hospital_holidays",   # models/audit.py HospitalHoliday; audit_repository
    "doctor_schedules",    # models/doctor.py DoctorSchedule; doctor_repository
    "doctor_leave",        # models/doctor.py DoctorLeave; doctor_repository
    "patient_documents",   # models/patient_document.py; document_repository
}

# ── Schema completeness ───────────────────────────────────────


class TestSchemaCompleteness:
    """SCHEMA_SQL must declare every table the application uses."""

    def test_schema_covers_all_referenced_tables(self) -> None:
        """Every model/repository table has a CREATE TABLE in SCHEMA_SQL."""
        assert set(_schema_tables()) == EXPECTED_TABLES

    def test_app_settings_declared_in_schema(self) -> None:
        """app_settings is part of the central schema, not a side file."""
        assert "app_settings" in _schema_tables()

    def test_app_settings_matches_requested_ddl(self) -> None:
        """app_settings uses setting_key VARCHAR(100) + setting_value TEXT."""
        match = re.search(
            r"CREATE TABLE IF NOT EXISTS `app_settings` \((.*)\) ENGINE=InnoDB",
            SCHEMA_SQL,
            re.DOTALL,
        )
        assert match, "app_settings CREATE TABLE missing from SCHEMA_SQL"
        block = match.group(1)
        assert "`setting_key` VARCHAR(100) PRIMARY KEY" in block
        assert "`setting_value` TEXT" in block
        assert "ON UPDATE CURRENT_TIMESTAMP" in block

    def test_all_schema_tables_use_if_not_exists(self) -> None:
        """Schema creation must be idempotent across startups."""
        for table in _schema_tables():
            assert re.search(
                rf"CREATE TABLE IF NOT EXISTS `{table}`", SCHEMA_SQL,
            ), f"{table} is not created with IF NOT EXISTS"


# ── Initialization behaviour (mocked connection) ──────────────


class FakeCursor:
    """Cursor stub that records statements and reports existing tables."""

    def __init__(self, existing_tables: set) -> None:
        self.existing_tables = existing_tables
        self.statements: list = []

    def execute(self, sql: str, params: tuple = None) -> None:
        self.statements.append(sql)

    def fetchall(self) -> list:
        # Information_schema.TABLES rows are (table_name,) tuples.
        return [(t,) for t in sorted(self.existing_tables)]

    def close(self) -> None:
        pass


class FakeConnection:
    """Connection stub delegating to FakeCursor."""

    def __init__(self, existing_tables: set) -> None:
        self._cursor = FakeCursor(existing_tables)

    def cursor(self) -> FakeCursor:
        return self._cursor

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass


def run_init(existing_tables: set):
    """Run initialize_database with a mocked connection.

    Returns:
        (result, cursor, connect_mock) so tests can inspect the executed
        statements and the connection kwargs.
    """
    conn = FakeConnection(existing_tables)
    with patch("mysql.connector.connect", return_value=conn) as mock_connect:
        result = initialize_database()
    return result, conn._cursor, mock_connect


class TestInitialization:
    """initialize_database must be idempotent and warning-tolerant."""

    def test_success_when_all_tables_exist(self, caplog) -> None:
        """A fully-initialized database initializes with no errors."""
        with caplog.at_level(logging.INFO, logger="src.database.init_db"):
            result, cursor, _ = run_init(EXPECTED_TABLES)
        assert result is True
        assert "Database initialization failed" not in caplog.text
        assert "initialized successfully" in caplog.text

    def test_create_database_uses_if_not_exists(self) -> None:
        """CREATE DATABASE is idempotent — no 1007 error on re-runs."""
        _, cursor, _ = run_init(EXPECTED_TABLES)
        ddl = next(s for s in cursor.statements if "CREATE DATABASE" in s)
        assert "CREATE DATABASE IF NOT EXISTS" in ddl

    def test_ddl_connection_does_not_raise_on_warnings(self) -> None:
        """The DDL connection must not promote benign warnings to errors."""
        _, _, mock_connect = run_init(EXPECTED_TABLES)
        kwargs = mock_connect.call_args.kwargs
        assert kwargs.get("raise_on_warnings") is False

    def test_schema_statements_executed(self) -> None:
        """Every CREATE TABLE in SCHEMA_SQL is executed on init."""
        _, cursor, _ = run_init(EXPECTED_TABLES)
        executed = "\n".join(cursor.statements)
        for table in EXPECTED_TABLES:
            assert f"CREATE TABLE IF NOT EXISTS `{table}`" in executed

    def test_missing_table_detected(self, caplog) -> None:
        """A declared table missing after init fails startup loudly."""
        missing = EXPECTED_TABLES - {"app_settings"}
        with caplog.at_level(logging.ERROR, logger="src.database.init_db"):
            result, _, _ = run_init(missing)
        assert result is False
        assert "tables missing" in caplog.text
        assert "app_settings" in caplog.text

    def test_repeat_runs_stay_clean(self, caplog) -> None:
        """Running init twice (two startups) logs no errors either time."""
        with caplog.at_level(logging.ERROR, logger="src.database.init_db"):
            first, _, _ = run_init(EXPECTED_TABLES)
            second, _, _ = run_init(EXPECTED_TABLES)
        assert first is True and second is True
        assert "Database initialization failed" not in caplog.text
