"""Base repository class with common CRUD operations."""
import logging
import re
from typing import Optional, List, Dict, Any, Type, TypeVar, Tuple

from src.database.connection import DatabaseConnection
logger = logging.getLogger(__name__)

T = TypeVar('T')

# Strict allow-list for ORDER BY clauses: only column identifiers with
# optional ASC/DESC and comma separation.  Anything else (quotes,
# semicolons, functions, subqueries, raw user input) is rejected with
# a ValueError, so sort columns can never be concatenated into the
# query from unvalidated input.
_ORDER_BY_RE = re.compile(
    r"^[A-Za-z0-9_]+(\s+(ASC|DESC))?"
    r"(\s*,\s*[A-Za-z0-9_]+(\s+(ASC|DESC))?)*$",
    re.IGNORECASE,
)


class BaseRepository:
    """Base repository providing common database operations.

    All repositories inherit from this class to reuse standard
    CRUD logic while remaining independent of specific model types.
    """

    def __init__(self, table_name: str) -> None:
        """Initialize repository with target table name.

        Args:
            table_name: Name of the database table.
        """
        self.table_name = table_name
        self.logger = logging.getLogger(self.__class__.__name__)

    def find_by_id(self, id_column: str, id_value: Any) -> Optional[Dict[str, Any]]:
        """Find a record by its primary key.

        Args:
            id_column: Name of the primary key column.
            id_value: Value to search for.

        Returns:
            Dictionary of column values or None if not found.
        """
        query = f"SELECT * FROM `{self.table_name}` WHERE `{id_column}` = %s"
        result = DatabaseConnection.execute_query(query, (id_value,), fetch_one=True)
        return result

    def find_all(
        self,
        order_by: str = "",
        limit: int = 0,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Find all records with optional ordering and pagination.

        Args:
            order_by: Column name(s) to order by.
            limit: Maximum number of records to return.
            offset: Number of records to skip.

        Returns:
            List of dictionaries containing record data.
        """
        order_by = self._sanitize_order_by(order_by)
        limit = self._sanitize_limit(limit)
        offset = self._sanitize_limit(offset)
        query = f"SELECT * FROM `{self.table_name}`"
        if order_by:
            query += f" ORDER BY {order_by}"
        if limit > 0:
            query += f" LIMIT {limit}"
            if offset > 0:
                query += f" OFFSET {offset}"

        return DatabaseConnection.execute_query(query) or []

    def find_where(
        self,
        conditions: Dict[str, Any],
        order_by: str = "",
        limit: int = 0,
    ) -> List[Dict[str, Any]]:
        """Find records matching the given conditions.

        Args:
            conditions: Dictionary of column-value pairs to filter by.
            order_by: Column name(s) to order by.
            limit: Maximum number of records to return.

        Returns:
            List of dictionaries containing matching records.
        """
        if not conditions:
            return self.find_all(order_by=order_by, limit=limit)

        order_by = self._sanitize_order_by(order_by)
        limit = self._sanitize_limit(limit)

        where_clauses = []
        params = []
        for col, val in conditions.items():
            where_clauses.append(f"`{col}` = %s")
            params.append(val)

        query = f"SELECT * FROM `{self.table_name}` WHERE {' AND '.join(where_clauses)}"
        if order_by:
            query += f" ORDER BY {order_by}"
        if limit > 0:
            query += f" LIMIT {limit}"

        return DatabaseConnection.execute_query(query, tuple(params)) or []

    @staticmethod
    def _sanitize_order_by(order_by: str) -> str:
        """Validate an ORDER BY clause against an explicit allow-list.

        Only plain column identifiers with optional ``ASC``/``DESC``
        and comma separation are permitted; anything else raises
        ``ValueError`` (fail closed) so unvalidated input can never be
        concatenated into the query.

        Args:
            order_by: The raw ORDER BY clause.

        Returns:
            The validated clause (unchanged) or "" for no ordering.

        Raises:
            ValueError: If the clause contains disallowed characters.
        """
        if not order_by:
            return ""
        if not _ORDER_BY_RE.match(order_by):
            raise ValueError(f"Invalid ORDER BY clause: {order_by!r}")
        return order_by

    @staticmethod
    def _sanitize_limit(value: Any) -> int:
        """Coerce a LIMIT/OFFSET value to a non-negative integer.

        Args:
            value: The raw limit/offset value.

        Returns:
            The value as an int (0 for "no limit").

        Raises:
            ValueError: If the value is not an integer.
        """
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid limit/offset value: {value!r}")
        if value < 0:
            raise ValueError(f"Invalid limit/offset value: {value!r}")
        return value

    def count_where(self, conditions: Optional[Dict[str, Any]] = None) -> int:
        """Count records matching the given conditions.

        Args:
            conditions: Dictionary of column-value pairs to filter by.

        Returns:
            Number of matching records.
        """
        if conditions:
            where_clauses = []
            params = []
            for col, val in conditions.items():
                where_clauses.append(f"`{col}` = %s")
                params.append(val)
            query = f"SELECT COUNT(*) as cnt FROM `{self.table_name}` WHERE {' AND '.join(where_clauses)}"
            result = DatabaseConnection.execute_query(query, tuple(params), fetch_one=True)
        else:
            query = f"SELECT COUNT(*) as cnt FROM `{self.table_name}`"
            result = DatabaseConnection.execute_query(query, fetch_one=True)

        return result['cnt'] if result else 0

    def insert(self, data: Dict[str, Any], allowed_columns: Optional[List[str]] = None, conn: Optional[Any] = None) -> int:
        """Insert a new record.

        If ``allowed_columns`` is provided, only keys present in that
        list will be included in the INSERT, providing a whitelist
        defence against mass-assignment attacks.

        Args:
            data: Dictionary of column-value pairs to insert.
            allowed_columns: Optional whitelist of permitted column names.
            conn: Optional connection to run on (transactional use).

        Returns:
            The ID of the newly inserted record.
        """
        if allowed_columns is not None:
            data = {k: v for k, v in data.items() if k in allowed_columns}

        if not data:
            raise ValueError("No valid columns to insert after field filtering.")

        columns = ', '.join(f"`{col}`" for col in data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO `{self.table_name}` ({columns}) VALUES ({placeholders})"

        return DatabaseConnection.execute_insert(query, tuple(data.values()), conn=conn)

    def update(self, id_column: str, id_value: Any, data: Dict[str, Any], allowed_columns: Optional[List[str]] = None, conn: Optional[Any] = None) -> int:
        """Update an existing record by primary key.

        If ``allowed_columns`` is provided, only keys present in that
        list will be included in the SET clause, providing a whitelist
        defence against mass-assignment attacks.

        Args:
            id_column: Name of the primary key column.
            id_value: Value of the primary key.
            data: Dictionary of column-value pairs to update.
            allowed_columns: Optional whitelist of permitted column names.
            conn: Optional connection to run on (transactional use).

        Returns:
            Number of rows affected.
        """
        if allowed_columns is not None:
            data = {k: v for k, v in data.items() if k in allowed_columns}

        if not data:
            return 0

        set_clauses = ', '.join(f"`{col}` = %s" for col in data.keys())
        query = f"UPDATE `{self.table_name}` SET {set_clauses} WHERE `{id_column}` = %s"

        params = list(data.values()) + [id_value]
        return DatabaseConnection.execute_update(query, tuple(params), conn=conn)

    def delete(self, id_column: str, id_value: Any, conn: Optional[Any] = None) -> int:
        """Delete a record by primary key.

        Args:
            id_column: Name of the primary key column.
            id_value: Value of the primary key.
            conn: Optional connection to run on (transactional use).

        Returns:
            Number of rows deleted.
        """
        query = f"DELETE FROM `{self.table_name}` WHERE `{id_column}` = %s"
        return DatabaseConnection.execute_update(query, (id_value,), conn=conn)

    def delete_where(self, conditions: Dict[str, Any]) -> int:
        """Delete records matching the given conditions.

        Args:
            conditions: Dictionary of column-value pairs to filter by.

        Returns:
            Number of rows deleted.
        """
        where_clauses = []
        params = []
        for col, val in conditions.items():
            where_clauses.append(f"`{col}` = %s")
            params.append(val)

        query = f"DELETE FROM `{self.table_name}` WHERE {' AND '.join(where_clauses)}"
        return DatabaseConnection.execute_update(query, tuple(params))

    def exists(self, id_column: str, id_value: Any) -> bool:
        """Check if a record exists by primary key.

        Args:
            id_column: Name of the primary key column.
            id_value: Value to check.

        Returns:
            True if record exists, False otherwise.
        """
        query = f"SELECT EXISTS(SELECT 1 FROM `{self.table_name}` WHERE `{id_column}` = %s) as ex"
        result = DatabaseConnection.execute_query(query, (id_value,), fetch_one=True)
        return bool(result and result.get('ex', 0))

    def search(
        self,
        search_columns: List[str],
        search_term: str,
        extra_conditions: Optional[Dict[str, Any]] = None,
        order_by: str = "",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search records by text matching across specified columns.

        Args:
            search_columns: List of column names to search within.
            search_term: Text to search for (uses LIKE with wildcards).
            extra_conditions: Additional fixed conditions.
            order_by: Column name(s) to order by.
            limit: Maximum number of records to return.

        Returns:
            List of matching records.
        """
        order_by = self._sanitize_order_by(order_by)
        limit = self._sanitize_limit(limit)
        like_clauses = [f"`{col}` LIKE %s" for col in search_columns]
        params: list = [f"%{search_term}%"] * len(search_columns)

        where_parts = [f"({' OR '.join(like_clauses)})"]

        if extra_conditions:
            for col, val in extra_conditions.items():
                where_parts.append(f"`{col}` = %s")
                params.append(val)

        query = f"SELECT * FROM `{self.table_name}` WHERE {' AND '.join(where_parts)}"
        if order_by:
            query += f" ORDER BY {order_by}"
        query += f" LIMIT {limit}"

        return DatabaseConnection.execute_query(query, tuple(params)) or []
