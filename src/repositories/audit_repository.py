"""Audit repository for logging user actions."""
import logging
import hashlib
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from src.repositories.base_repository import BaseRepository
from src.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class AuditRepository(BaseRepository):
    """Repository for audit log operations."""

    def __init__(self) -> None:
        """Initialize AuditRepository."""
        super().__init__("audit_logs")

    def log_action(self, data: Dict[str, Any]) -> int:
        """Record an audit log entry.

        Args:
            data: Dictionary with action, user_id, target info, etc.

        Returns:
            The new log entry's ID.
        """
        if "timestamp" not in data:
            data["timestamp"] = datetime.now()
        with DatabaseConnection.transaction() as conn:
            previous = DatabaseConnection.execute_query(
                "SELECT row_hash FROM audit_logs ORDER BY log_id DESC LIMIT 1 FOR UPDATE",
                fetch_one=True, conn=conn,
            )
            previous_hash = previous.get("row_hash") if previous else None
            data["previous_hash"] = previous_hash
            data["row_hash"] = compute_row_hash(data, previous_hash)
            return self.insert(data, conn=conn)

    def find_filtered(self, start_date: Optional[date] = None,
                      end_date: Optional[date] = None,
                      action: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return persisted audit entries filtered for the admin viewer."""
        clauses, params = [], []
        if start_date:
            clauses.append("DATE(al.timestamp) >= %s")
            params.append(start_date)
        if end_date:
            clauses.append("DATE(al.timestamp) <= %s")
            params.append(end_date)
        if action:
            clauses.append("al.action = %s")
            params.append(action)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        query = ("SELECT al.*, u.username FROM audit_logs al "
                 "LEFT JOIN users u ON al.user_id = u.user_id" + where +
                 " ORDER BY al.timestamp DESC, al.log_id DESC")
        return DatabaseConnection.execute_query(query, tuple(params)) or []

    def find_chain(self) -> List[Dict[str, Any]]:
        """Return all hash-chain records in immutable insertion order."""
        return DatabaseConnection.execute_query(
            "SELECT * FROM audit_logs ORDER BY log_id ASC"
        ) or []

    def backfill_hash_chain(self) -> int:
        """Hash legacy rows in order after the hash-chain migration.

        This is intentionally explicit rather than automatic: repairing a
        tamper-evident trail must be an administrator-controlled migration.
        """
        with DatabaseConnection.transaction() as conn:
            rows = DatabaseConnection.execute_query(
                "SELECT * FROM audit_logs ORDER BY log_id ASC FOR UPDATE",
                conn=conn,
            ) or []
            previous_hash: Optional[str] = None
            for row in rows:
                row_hash = compute_row_hash(row, previous_hash)
                DatabaseConnection.execute_update(
                    "UPDATE audit_logs SET previous_hash = %s, row_hash = %s WHERE log_id = %s",
                    (previous_hash, row_hash, row["log_id"]), conn=conn,
                )
                previous_hash = row_hash
            return len(rows)

    def find_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Find recent audit log entries.

        Args:
            limit: Number of records to return.

        Returns:
            List of recent audit log records.
        """
        query = """
            SELECT al.*, u.username
            FROM audit_logs al
            LEFT JOIN users u ON al.user_id = u.user_id
            ORDER BY al.timestamp DESC
            LIMIT %s
        """
        return DatabaseConnection.execute_query(query, (limit,)) or []

    def find_by_user(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Find audit log entries for a specific user.

        Args:
            user_id: The user ID.
            limit: Number of records to return.

        Returns:
            List of audit records for the user.
        """
        query = """
            SELECT al.*, u.username
            FROM audit_logs al
            LEFT JOIN users u ON al.user_id = u.user_id
            WHERE al.user_id = %s
            ORDER BY al.timestamp DESC
            LIMIT %s
        """
        return DatabaseConnection.execute_query(query, (user_id, limit)) or []

    def find_by_date_range(
        self, start_date: date, end_date: date
    ) -> List[Dict[str, Any]]:
        """Find audit log entries within a date range.

        Args:
            start_date: Range start date.
            end_date: Range end date.

        Returns:
            List of audit records in the range.
        """
        query = """
            SELECT al.*, u.username
            FROM audit_logs al
            LEFT JOIN users u ON al.user_id = u.user_id
            WHERE DATE(al.timestamp) BETWEEN %s AND %s
            ORDER BY al.timestamp DESC
        """
        return DatabaseConnection.execute_query(query, (start_date, end_date)) or []

    def count_today(self) -> int:
        """Count today's audit log entries.

        Returns:
            Number of entries today.
        """
        query = "SELECT COUNT(*) as cnt FROM audit_logs WHERE DATE(timestamp) = %s"
        result = DatabaseConnection.execute_query(
            query, (date.today(),), fetch_one=True
        )
        return result["cnt"] if result else 0


def compute_row_hash(data: Dict[str, Any], previous_hash: Optional[str]) -> str:
    """Return a canonical SHA-256 hash for one audit-chain record."""
    timestamp = data.get("timestamp")
    if isinstance(timestamp, datetime):
        # The schema uses TIMESTAMP(6), preserving this value exactly.
        timestamp = timestamp.isoformat(timespec="microseconds")
    payload = {
        "previous_hash": previous_hash or "", "user_id": data.get("user_id"),
        "action": data.get("action"), "target_entity": data.get("target_entity"),
        "target_id": data.get("target_id"), "old_values": data.get("old_values"),
        "new_values": data.get("new_values"), "ip_address": data.get("ip_address"),
        "user_agent": data.get("user_agent"), "timestamp": str(timestamp),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_hash_chain(rows: List[Dict[str, Any]]) -> tuple[bool, Optional[int]]:
    """Verify the sequence and content of a list of audit-chain rows."""
    previous_hash: Optional[str] = None
    for row in rows:
        if row.get("previous_hash") != previous_hash:
            return False, row.get("log_id")
        if row.get("row_hash") != compute_row_hash(row, previous_hash):
            return False, row.get("log_id")
        previous_hash = row.get("row_hash")
    return True, None


class HospitalHolidayRepository(BaseRepository):
    """Repository for hospital holiday operations."""

    def __init__(self) -> None:
        """Initialize HospitalHolidayRepository."""
        super().__init__("hospital_holidays")

    def find_by_date(self, holiday_date: date) -> Optional[Dict[str, Any]]:
        """Find a holiday by date.

        Args:
            holiday_date: The date to check.

        Returns:
            Holiday record or None.
        """
        results = self.find_where({"holiday_date": holiday_date})
        return results[0] if results else None

    def is_holiday(self, check_date: date) -> bool:
        """Check if a date is a hospital holiday.

        Args:
            check_date: The date to check.

        Returns:
            True if the date is a holiday, False otherwise.
        """
        query = """
            SELECT COUNT(*) as cnt
            FROM hospital_holidays
            WHERE (holiday_date = %s AND is_recurring = TRUE)
               OR (holiday_date = %s AND is_recurring = FALSE)
        """
        result = DatabaseConnection.execute_query(
            query, (check_date, check_date), fetch_one=True
        )
        return bool(result and result["cnt"] > 0)

    def find_all_holidays(self) -> List[Dict[str, Any]]:
        """Find all configured holidays.

        Returns:
            List of holiday records ordered by date.
        """
        return self.find_all(order_by="holiday_date ASC")

    def find_upcoming(self, from_date: date) -> List[Dict[str, Any]]:
        """Find holidays on or after a given date.

        Args:
            from_date: The date to start from.

        Returns:
            List of upcoming holiday records.
        """
        query = "SELECT * FROM hospital_holidays WHERE holiday_date >= %s ORDER BY holiday_date ASC"
        return DatabaseConnection.execute_query(query, (from_date,)) or []

    def create_holiday(self, data: Dict[str, Any]) -> int:
        """Insert a new holiday record.

        Args:
            data: Dictionary of holiday fields.

        Returns:
            The new holiday's ID.
        """
        return self.insert(data)

    def delete_holiday(self, holiday_id: int) -> int:
        """Delete a holiday record.

        Args:
            holiday_id: The holiday ID.

        Returns:
            Number of rows deleted.
        """
        return self.delete("holiday_id", holiday_id)
