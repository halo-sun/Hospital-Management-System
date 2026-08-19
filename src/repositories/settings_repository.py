"""Settings repository – key/value access to the ``app_settings`` table.

Holds application-level preferences (e.g. the selected UI theme).
Small enough to live in its own repository: values are simple strings,
read and upserted by key.
"""
from __future__ import annotations

import logging
from typing import Optional

from src.repositories.base_repository import BaseRepository
from src.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class SettingsRepository(BaseRepository):
    """Repository for the ``app_settings`` key/value table."""

    def __init__(self) -> None:
        """Initialize SettingsRepository."""
        super().__init__("app_settings")

    def get_value(self, key: str) -> Optional[str]:
        """Return the value stored for a key, or None if unset.

        Args:
            key: The setting key.

        Returns:
            The stored value or None.
        """
        result = DatabaseConnection.execute_query(
            "SELECT setting_value FROM app_settings WHERE setting_key = %s",
            (key,),
            fetch_one=True,
        )
        return result["setting_value"] if result else None

    def set_value(self, key: str, value: str) -> None:
        """Insert or update the value for a key (upsert).

        Args:
            key: The setting key.
            value: The value to store.
        """
        # MySQL 8.0.20+ emits deprecation warning 1287 for the legacy
        # ``VALUES(col)`` upsert syntax, which the connection pool's
        # ``raise_on_warnings`` would promote to an exception.  Use the
        # row-alias form (8.0.19+) so persistence never fails on the
        # deprecation notice.
        DatabaseConnection.execute_query(
            """
            INSERT INTO app_settings (setting_key, setting_value)
            VALUES (%s, %s) AS new
            ON DUPLICATE KEY UPDATE setting_value = new.setting_value
            """,
            (key, value),
            fetch=False,
        )
        logger.info("Setting updated: %s", key)
