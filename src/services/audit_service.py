"""Audit service for logging and retrieving user activity."""
import logging
import json
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from src.repositories.audit_repository import AuditRepository, verify_hash_chain
from src.constants import AuditAction

logger = logging.getLogger(__name__)


class AuditService:
    """Handles audit logging and activity retrieval."""

    def __init__(self) -> None:
        """Initialize AuditService with required repositories."""
        self._audit_repo = AuditRepository()

    def log(
        self,
        action: str,
        user_id: Optional[int] = None,
        target_entity: Optional[str] = None,
        target_id: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Record an audit log entry.

        Args:
            action: The action being logged (use AuditAction constants).
            user_id: The ID of the user performing the action.
            target_entity: The entity type being acted upon.
            target_id: The ID of the entity being acted upon.
            old_values: Previous values (for updates).
            new_values: New values (for updates or creates).

        Returns:
            The new log entry's ID.
        """
        data: Dict[str, Any] = {
            "action": action,
            "timestamp": datetime.now(),
        }
        if user_id is not None:
            data["user_id"] = user_id
        if target_entity:
            data["target_entity"] = target_entity
        if target_id:
            data["target_id"] = str(target_id)
        if old_values:
            data["old_values"] = json.dumps(old_values, default=str)
        if new_values:
            data["new_values"] = json.dumps(new_values, default=str)

        log_id = self._audit_repo.log_action(data)
        logger.info(f"Audit: {action} user={user_id} entity={target_entity} id={target_id}")
        return log_id

    def get_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit log entries.

        Args:
            limit: Number of records to return.

        Returns:
            List of audit records.
        """
        return self._audit_repo.find_recent(limit)

    def list_logs(self, start_date: Optional[date] = None,
                  end_date: Optional[date] = None,
                  action: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return persisted audit records for the administrator viewer."""
        return self._audit_repo.find_filtered(start_date, end_date, action)

    def verify_chain(self) -> tuple[bool, Optional[int]]:
        """Verify the tamper-evident audit hash chain."""
        return verify_hash_chain(self._audit_repo.find_chain())

    def backfill_chain(self) -> int:
        """Backfill hashes for legacy records after the schema migration."""
        return self._audit_repo.backfill_hash_chain()

    def get_user_activity(
        self, user_id: int, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get audit log entries for a specific user.

        Args:
            user_id: The user ID.
            limit: Number of records.

        Returns:
            List of audit records for the user.
        """
        return self._audit_repo.find_by_user(user_id, limit)

    def get_activity_by_date(
        self, start_date: date, end_date: date
    ) -> List[Dict[str, Any]]:
        """Get audit log entries within a date range.

        Args:
            start_date: Range start.
            end_date: Range end.

        Returns:
            List of audit records in the range.
        """
        return self._audit_repo.find_by_date_range(start_date, end_date)

    def get_today_count(self) -> int:
        """Count today's audit log entries.

        Returns:
            Number of entries today.
        """
        return self._audit_repo.count_today()

    def log_login(self, user_id: int, success: bool) -> int:
        """Log a login attempt.

        Args:
            user_id: The user ID.
            success: Whether the login succeeded.

        Returns:
            The log entry ID.
        """
        action = AuditAction.LOGIN if success else AuditAction.LOGIN_FAILED
        return self.log(action, user_id=user_id, target_entity="User", target_id=str(user_id))

    def log_logout(self, user_id: int) -> int:
        """Log a logout event.

        Args:
            user_id: The user ID.

        Returns:
            The log entry ID.
        """
        return self.log(AuditAction.LOGOUT, user_id=user_id, target_entity="User", target_id=str(user_id))

    def log_create(
        self, user_id: int, entity: str, entity_id: str, values: Dict[str, Any]
    ) -> int:
        """Log a record creation.

        Args:
            user_id: The acting user's ID.
            entity: Entity type name.
            entity_id: The new entity's ID.
            values: The created values.

        Returns:
            The log entry ID.
        """
        return self.log(
            AuditAction.CREATE, user_id=user_id,
            target_entity=entity, target_id=entity_id, new_values=values,
        )

    def log_update(
        self,
        user_id: int,
        entity: str,
        entity_id: str,
        old_values: Dict[str, Any],
        new_values: Dict[str, Any],
    ) -> int:
        """Log a record update.

        Args:
            user_id: The acting user's ID.
            entity: Entity type name.
            entity_id: The entity's ID.
            old_values: Previous values.
            new_values: Updated values.

        Returns:
            The log entry ID.
        """
        return self.log(
            AuditAction.UPDATE, user_id=user_id,
            target_entity=entity, target_id=entity_id,
            old_values=old_values, new_values=new_values,
        )

    def log_delete(
        self, user_id: int, entity: str, entity_id: str
    ) -> int:
        """Log a record deletion.

        Args:
            user_id: The acting user's ID.
            entity: Entity type name.
            entity_id: The deleted entity's ID.

        Returns:
            The log entry ID.
        """
        return self.log(
            AuditAction.DELETE, user_id=user_id,
            target_entity=entity, target_id=entity_id,
        )

    def log_export(self, user_id: int, report_type: str) -> int:
        """Log a report export.

        Args:
            user_id: The acting user's ID.
            report_type: The type of report exported.

        Returns:
            The log entry ID.
        """
        return self.log(
            AuditAction.EXPORT, user_id=user_id,
            target_entity="Report", target_id=report_type,
        )
