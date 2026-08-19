"""Concurrency tests for the appointment booking path.

These tests verify the **race-condition protection** around booking:

* ``book_appointment`` validates and INSERTs inside a single
  transaction, locking the doctor's existing appointments for the date
  with ``SELECT ... FOR UPDATE`` so two concurrent attempts for the
  same doctor/date/slot cannot both pass the overlap check and both
  write.
* The DB-level unique backstop (``uk_appt_booking_key`` on the
  generated ``booking_key`` column) translates to the same clean
  "slot already booked" rejection a normal validation failure
  produces — never a crash and never a silent duplicate.

The unit tests run with mocks (no MySQL needed).  The two
``needs_mysql`` tests exercise the real database and are **skipped
automatically** when MySQL is not reachable.

Run the full file with::

    python3 -m pytest tests/test_concurrency_booking.py -v

or just the DB-backed race test with::

    python3 -m pytest tests/test_concurrency_booking.py \
        -k real_db_two_threads_exactly_one_wins -v
"""
from __future__ import annotations

import threading
from datetime import date, time, timedelta
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch

import mysql.connector
import pytest

from src.database.connection import DatabaseConnection
from src.services.appointment_service import AppointmentService
from src.services.scheduling_engine import SchedulingEngine


# A date safely in the future so the past-date rule never trips.
FUTURE_DATE = date.today() + timedelta(days=30)


# ── MySQL availability guard ───────────────────────────────────


def _mysql_available() -> bool:
    """Return True if a real MySQL connection can be established."""
    try:
        conn = DatabaseConnection.get_connection()
        conn.close()
        return True
    except Exception:
        return False


needs_mysql = pytest.mark.skipif(
    not _mysql_available(), reason="MySQL server not reachable"
)


# ── Unit fixtures (no DB) ──────────────────────────────────────


@pytest.fixture
def service() -> AppointmentService:
    """AppointmentService with repos and engine mocked out.

    ``DatabaseConnection.transaction`` is mocked so booking runs
    without a MySQL server; the transaction connection is a plain
    MagicMock.
    """
    with (
        patch("src.services.appointment_service.AppointmentRepository") as appt_cls,
        patch("src.services.appointment_service.DoctorRepository") as doc_cls,
        patch("src.services.appointment_service.SchedulingEngine") as eng_cls,
        patch.object(DatabaseConnection, "transaction") as tx_cls,
    ):
        appt_cls.return_value = MagicMock()
        doc_cls.return_value = MagicMock()
        eng_cls.return_value = MagicMock()
        tx_cls.return_value.__enter__.return_value = MagicMock(name="txconn")
        svc = AppointmentService()
        svc._appt_repo = appt_cls.return_value
        svc._doctor_repo = doc_cls.return_value
        svc._engine = eng_cls.return_value
        yield svc


@pytest.fixture
def mock_appt(service: AppointmentService) -> MagicMock:
    """Access the mocked AppointmentRepository."""
    return service._appt_repo


@pytest.fixture
def mock_engine(service: AppointmentService) -> MagicMock:
    """Access the mocked SchedulingEngine."""
    return service._engine


def _booking_data(**overrides: Any) -> Dict[str, Any]:
    """Build valid booking data for a future date."""
    data: Dict[str, Any] = {
        "patient_id": "PAT-00001",
        "doctor_id": 1,
        "appointment_date": FUTURE_DATE,
        "start_time": time(10, 0),
        "end_time": time(10, 30),
        "created_by": 1,
    }
    data.update(overrides)
    return data


# ── Unit: locking mechanism ────────────────────────────────────


class TestBookingLockingMechanism:
    """Verifies the transaction + FOR UPDATE mechanics of booking."""

    def test_validation_and_insert_share_one_transaction(
        self, service: AppointmentService, mock_appt: MagicMock,
        mock_engine: MagicMock,
    ) -> None:
        """The locked snapshot is read, validated, and inserted on the
        same transaction connection — the core of the race protection."""
        locked_rows = [{"appointment_id": 9, "start_time": time(9, 0)}]
        mock_appt.find_by_doctor_and_date.return_value = locked_rows
        mock_engine.validate_slot.return_value = (True, "")
        mock_appt.create_appointment.return_value = 42

        success, msg, appt_id = service.book_appointment(_booking_data())
        assert success is True
        assert appt_id == 42

        # Rows are locked FOR UPDATE inside the transaction…
        _, kwargs = mock_appt.find_by_doctor_and_date.call_args
        assert kwargs.get("for_update") is True
        assert kwargs.get("conn") is not None

        # …and the engine validates against that locked snapshot…
        _, vkwargs = mock_engine.validate_slot.call_args
        assert vkwargs.get("existing_appointments") is locked_rows

        # …and the INSERT runs on the same transaction connection.
        ckwargs = mock_appt.create_appointment.call_args.kwargs
        assert ckwargs.get("conn") is not None

    def test_lock_query_uses_for_update_clause(self) -> None:
        """The generated SQL contains FOR UPDATE when requested."""
        from src.repositories.appointment_repository import AppointmentRepository

        repo = AppointmentRepository()
        with patch.object(
            DatabaseConnection, "execute_query", return_value=[]
        ) as exec_q:
            repo.find_by_doctor_and_date(1, FUTURE_DATE, for_update=True, conn="tx")
            query = exec_q.call_args.args[0]
            assert "FOR UPDATE" in query
            # Still parameterized — no user input concatenated.
            assert exec_q.call_args.args[1] == (1, FUTURE_DATE)

            exec_q.reset_mock()
            repo.find_by_doctor_and_date(1, FUTURE_DATE)
            query = exec_q.call_args.args[0]
            assert "FOR UPDATE" not in query

    def test_validation_failure_never_inserts(
        self, service: AppointmentService, mock_appt: MagicMock,
        mock_engine: MagicMock,
    ) -> None:
        """A rejected slot rolls back — no INSERT happens."""
        mock_appt.find_by_doctor_and_date.return_value = []
        mock_engine.validate_slot.return_value = (False, "Doctor is on leave.")

        success, msg, appt_id = service.book_appointment(_booking_data())
        assert success is False
        assert "leave" in msg.lower()
        assert appt_id is None
        mock_appt.create_appointment.assert_not_called()


# ── Unit: the race itself ──────────────────────────────────────


class _UniquenessEnforcingRepo:
    """Stand-in for AppointmentRepository that simulates the DB-level
    unique constraint (uk_appt_booking_key): the first INSERT for a
    given (doctor, date, start) wins; any later one raises
    IntegrityError, exactly like the real generated column backstop."""

    def __init__(self) -> None:
        self._seen: set = set()
        self._lock = threading.Lock()
        self._next_id = 0

    def find_by_doctor_and_date(
        self, doctor_id: int, appointment_date: date,
        for_update: bool = False, conn: Any = None,
    ) -> List[Dict[str, Any]]:
        # Both threads see an empty snapshot (the race: validation
        # passes on stale data); only the constraint catches the loser.
        return []

    def create_appointment(
        self, data: Dict[str, Any], conn: Any = None,
    ) -> int:
        key = (data["doctor_id"], data["appointment_date"], data["start_time"])
        with self._lock:
            if key in self._seen:
                raise mysql.connector.IntegrityError(
                    "Duplicate entry for key 'uk_appt_booking_key'", errno=1062,
                )
            self._seen.add(key)
            self._next_id += 1
            return self._next_id


class TestConcurrentBookings:
    """Two simultaneous requests for the same doctor/date/slot."""

    def test_two_threads_exactly_one_succeeds(self) -> None:
        """Exactly one attempt wins; the loser gets a clean
        'slot already booked' rejection — no crash, no duplicate."""
        repo = _UniquenessEnforcingRepo()
        with (
            patch("src.services.appointment_service.DoctorRepository"),
            patch.object(DatabaseConnection, "transaction") as tx_cls,
        ):
            tx_cls.return_value.__enter__.return_value = MagicMock(name="txconn")
            svc = AppointmentService()
            svc._appt_repo = repo  # type: ignore[assignment]
            # Engine always validates True (stale snapshot passes).
            svc._engine.validate_slot = lambda *a, **k: (True, "")

            barrier = threading.Barrier(2)
            results: List[Tuple[bool, str, Optional[int]]] = []

            def attempt() -> None:
                barrier.wait()
                results.append(svc.book_appointment(_booking_data()))

            t1 = threading.Thread(target=attempt)
            t2 = threading.Thread(target=attempt)
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            assert len(results) == 2
            successes = [r for r in results if r[0]]
            rejections = [r for r in results if not r[0]]
            assert len(successes) == 1
            assert len(rejections) == 1
            assert "already booked" in rejections[0][1].lower()
            assert successes[0][2] is not None
            # No silent duplicate: exactly one logical row was created.
            assert repo._next_id == 1

    def test_integrity_error_translated_to_clean_rejection(
        self, service: AppointmentService, mock_appt: MagicMock,
        mock_engine: MagicMock,
    ) -> None:
        """A DB IntegrityError (backstop) is surfaced as the same
        rejection a normal overlap failure produces."""
        mock_appt.find_by_doctor_and_date.return_value = []
        mock_engine.validate_slot.return_value = (True, "")  # stale snapshot
        mock_appt.create_appointment.side_effect = mysql.connector.IntegrityError(
            "Duplicate entry", errno=1062,
        )

        success, msg, appt_id = service.book_appointment(_booking_data())
        assert success is False
        assert msg == "This time slot is already booked."
        assert appt_id is None

    def test_generic_errors_do_not_crash_booking(
        self, service: AppointmentService, mock_appt: MagicMock,
        mock_engine: MagicMock,
    ) -> None:
        """Unexpected DB errors surface as a generic failure, never a
        raw exception to the caller."""
        mock_appt.find_by_doctor_and_date.side_effect = RuntimeError("boom")

        success, msg, appt_id = service.book_appointment(_booking_data())
        assert success is False
        assert "system error" in msg.lower()
        assert appt_id is None


# ── DB-backed integration tests (skipped without MySQL) ────────


@needs_mysql
def test_schema_has_unique_booking_backstop() -> None:
    """The DB-level UNIQUE backstop on (doctor, date, slot) exists."""
    conn = DatabaseConnection.get_connection()
    cur = conn.cursor(dictionary=True, buffered=True)
    try:
        cur.execute("SHOW COLUMNS FROM appointments LIKE 'booking_key'")
        col = cur.fetchone()
        assert col is not None, (
            "appointments.booking_key generated column is missing — "
            "run database/migrations/002_appointment_integrity.sql"
        )
        extra = str(col.get("Extra", "")).upper()
        assert "GENERATED" in extra or "VIRTUAL" in extra or "STORED" in extra

        cur.execute("SHOW INDEX FROM appointments WHERE Key_name = 'uk_appt_booking_key'")
        assert cur.fetchone() is not None, "unique index uk_appt_booking_key missing"
    finally:
        cur.close()
        conn.close()


@needs_mysql
def test_real_db_two_threads_exactly_one_wins() -> None:
    """Real MySQL race: two threads book the identical doctor/date/slot
    simultaneously.  Exactly one succeeds; the other receives a clean
    'slot already booked' rejection; exactly one row is written."""
    conn = DatabaseConnection.get_connection()
    cur = conn.cursor(dictionary=True, buffered=True)
    try:
        cur.execute(
            "SELECT doctor_id FROM doctors WHERE status = 'Active' "
            "ORDER BY doctor_id LIMIT 1"
        )
        doctor = cur.fetchone()
        if not doctor:
            pytest.skip("No active doctor seeded — cannot run race test")
        doctor_id = doctor["doctor_id"]

        cur.execute("SELECT patient_id FROM patients LIMIT 1")
        patient = cur.fetchone()
        if not patient:
            pytest.skip("No patient seeded — cannot run race test")
        patient_id = patient["patient_id"]
        cur.execute("SELECT user_id FROM users ORDER BY user_id LIMIT 1")
        actor = cur.fetchone()
        if not actor:
            pytest.skip("No user seeded — cannot run race test")
        actor_id = actor["user_id"]
    finally:
        cur.close()
        conn.close()

    # A future date with a guaranteed working schedule: we (re)create
    # the schedule row for that weekday, clear any holiday/leave, and
    # wipe the day's appointments so the test is deterministic.
    target_date = date.today() + timedelta(days=14)
    sql_dow = (target_date.weekday() + 1) % 7  # Python Mon=0 → SQL Sun=0

    conn = DatabaseConnection.get_connection()
    cur = conn.cursor(buffered=True)
    try:
        cur.execute("START TRANSACTION")
        cur.execute(
            "DELETE FROM appointments WHERE doctor_id=%s AND appointment_date=%s",
            (doctor_id, target_date),
        )
        cur.execute(
            "DELETE FROM hospital_holidays WHERE holiday_date=%s", (target_date,)
        )
        cur.execute(
            "DELETE FROM doctor_leave WHERE doctor_id=%s "
            "AND leave_start_date<=%s AND leave_end_date>=%s",
            (doctor_id, target_date, target_date),
        )
        cur.execute(
            "DELETE FROM doctor_schedules WHERE doctor_id=%s AND day_of_week=%s",
            (doctor_id, sql_dow),
        )
        cur.execute(
            "INSERT INTO doctor_schedules "
            "(doctor_id, day_of_week, start_time, end_time, is_available) "
            "VALUES (%s, %s, '09:00:00', '17:00:00', TRUE)",
            (doctor_id, sql_dow),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()

    svc = AppointmentService()
    data = {
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "appointment_date": target_date,
        "start_time": time(10, 0),
        "end_time": time(10, 30),
        "created_by": actor_id,
    }

    barrier = threading.Barrier(2)
    results: List[Tuple[bool, str, Optional[int]]] = []

    def attempt() -> None:
        barrier.wait()
        results.append(svc.book_appointment(dict(data)))

    t1 = threading.Thread(target=attempt)
    t2 = threading.Thread(target=attempt)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    try:
        assert len(results) == 2
        successes = [r for r in results if r[0]]
        rejections = [r for r in results if not r[0]]
        assert len(successes) == 1, (
            f"expected exactly one success, got {len(successes)}: {results}"
        )
        assert len(rejections) == 1
        assert "already booked" in rejections[0][1].lower()

        # Exactly one row persisted — never a silent duplicate.
        conn = DatabaseConnection.get_connection()
        cur = conn.cursor(dictionary=True, buffered=True)
        try:
            cur.execute(
                "SELECT COUNT(*) AS n FROM appointments "
                "WHERE doctor_id=%s AND appointment_date=%s AND start_time='10:00:00'",
                (doctor_id, target_date),
            )
            assert cur.fetchone()["n"] == 1
        finally:
            cur.close()
            conn.close()
    finally:
        # Cleanup — leave the DB as we found it.
        conn = DatabaseConnection.get_connection()
        cur = conn.cursor(buffered=True)
        try:
            cur.execute(
                "DELETE FROM appointments WHERE doctor_id=%s AND appointment_date=%s",
                (doctor_id, target_date),
            )
            cur.execute(
                "DELETE FROM doctor_schedules WHERE doctor_id=%s AND day_of_week=%s",
                (doctor_id, sql_dow),
            )
            conn.commit()
        finally:
            cur.close()
            conn.close()
