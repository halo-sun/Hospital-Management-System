"""Database connection module with connection pooling."""
import logging
from contextlib import contextmanager
from typing import Optional, Generator, List, Dict, Tuple
import mysql.connector
from mysql.connector import pooling, Error, MySQLConnection

from src.config import db_config

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manages MySQL database connection pool."""
    
    _pool: Optional[pooling.MySQLConnectionPool] = None
    _initialized: bool = False
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize the connection pool."""
        if cls._initialized:
            return
            
        try:
            # get_connection_config() returns ALL connection parameters
            # including pool_name and pool_size — single source of truth.
            config = db_config.get_connection_config()
            cls._pool = pooling.MySQLConnectionPool(**config)
            cls._initialized = True
            logger.info("Database connection pool initialized successfully")
        except Error as e:
            logger.error(f"Failed to initialize database connection pool: {e}")
            raise
    
    @classmethod
    def get_connection(cls) -> MySQLConnection:
        """Get a connection from the pool."""
        if not cls._initialized:
            cls.initialize()
        
        try:
            return cls._pool.get_connection()
        except Error as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise
    
    @classmethod
    @contextmanager
    def transaction(cls) -> Generator[MySQLConnection, None, None]:
        """Run a block of statements inside a single transaction.

        Yields a dedicated connection so callers can execute multiple
        queries (including ``SELECT ... FOR UPDATE`` row locks and the
        final INSERT/UPDATE) against the same transaction.  Commits on
        success, rolls back on error, and always returns the connection
        to the pool.

        Usage::

            with DatabaseConnection.transaction() as conn:
                locked = repo.find_by_doctor_and_date(doc, day, conn=conn, for_update=True)
                ...
                repo.create_appointment(data, conn=conn)

        Yields:
            A ``MySQLConnection`` in an open transaction.
        """
        conn = cls.get_connection()
        try:
            conn.autocommit = False
            conn.start_transaction()
            yield conn
            conn.commit()
        except Error:
            conn.rollback()
            raise
        finally:
            conn.close()

    @classmethod
    @contextmanager
    def get_cursor(cls, dictionary: bool = True) -> Generator:
        """Get a cursor from the pool with automatic cleanup."""
        conn = cls.get_connection()
        cursor = conn.cursor(dictionary=dictionary, buffered=True)
        try:
            yield cursor
            conn.commit()
        except Error as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    @classmethod
    def execute_query(
        cls, 
        query: str, 
        params: Tuple = None, 
        fetch: bool = True, 
        dictionary: bool = True,
        fetch_one: bool = False,
        conn: Optional[MySQLConnection] = None
    ) -> Optional[List[Dict]]:
        """Execute a SELECT query and return results.

        Args:
            query: The SQL statement.
            params: Bound parameters.
            fetch: Whether to return rows.
            dictionary: Whether rows are returned as dicts.
            fetch_one: Return a single row instead of a list.
            conn: Optional connection to run on (for transactional use).
                When omitted a pooled cursor is used.
        """
        if conn is not None:
            cursor = conn.cursor(dictionary=dictionary, buffered=True)
            try:
                cursor.execute(query, params or ())
                if fetch:
                    if fetch_one:
                        return cursor.fetchone()
                    return cursor.fetchall()
                return None
            finally:
                cursor.close()
        with cls.get_cursor(dictionary=dictionary) as cursor:
            cursor.execute(query, params or ())
            if fetch:
                if fetch_one:
                    return cursor.fetchone()
                return cursor.fetchall()
            return None
    
    @classmethod
    def execute_update(cls, query: str, params: Tuple = None, conn: Optional[MySQLConnection] = None) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows.

        Args:
            query: The SQL statement.
            params: Bound parameters.
            conn: Optional connection to run on (for transactional use).
        """
        if conn is not None:
            cursor = conn.cursor(dictionary=False)
            try:
                cursor.execute(query, params or ())
                return cursor.rowcount
            finally:
                cursor.close()
        with cls.get_cursor(dictionary=False) as cursor:
            cursor.execute(query, params or ())
            return cursor.rowcount
    
    @classmethod
    def execute_insert(cls, query: str, params: Tuple = None, conn: Optional[MySQLConnection] = None) -> int:
        """Execute an INSERT query and return the last inserted ID.

        Args:
            query: The SQL statement.
            params: Bound parameters.
            conn: Optional connection to run on (for transactional use).
        """
        if conn is not None:
            cursor = conn.cursor(dictionary=False)
            try:
                cursor.execute(query, params or ())
                return cursor.lastrowid
            finally:
                cursor.close()
        with cls.get_cursor(dictionary=False) as cursor:
            cursor.execute(query, params or ())
            return cursor.lastrowid
    
    @classmethod
    def execute_many(cls, query: str, params_list: List[Tuple]) -> int:
        """Execute multiple queries with different parameters."""
        conn = cls.get_connection()
        cursor = conn.cursor()
        try:
            cursor.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount
        except Error as e:
            conn.rollback()
            logger.error(f"Batch execute error: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    @classmethod
    def execute_script(cls, script: str) -> None:
        """Execute multiple SQL statements from a script."""
        conn = cls.get_connection()
        cursor = conn.cursor()
        try:
            for statement in script.split(';'):
                stmt = statement.strip()
                if stmt:
                    cursor.execute(stmt)
            conn.commit()
        except Error as e:
            conn.rollback()
            logger.error(f"Script execution error: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    @classmethod
    def test_connection(cls) -> bool:
        """Test if database connection is working."""
        try:
            conn = cls.get_connection()
            conn.ping(reconnect=True)
            conn.close()
            return True
        except Error as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    @classmethod
    def close_pool(cls) -> None:
        """Close all connections in the pool.

        ``MySQLConnectionPool`` in this connector version has no public
        ``close()``, so each pooled connection is closed individually
        by draining the internal connection queue.  Defensive: any
        failure closing a single connection is logged, not raised.
        """
        if cls._pool:
            try:
                queue = getattr(cls._pool, "_cnx_queue", None)
                if queue is not None:
                    while True:
                        try:
                            conn = queue.get_nowait()
                        except Exception:
                            break  # queue empty
                        try:
                            conn.close()
                        except Exception as e:
                            logger.warning("Failed to close pooled connection: %s", e)
            except Exception as e:
                logger.warning("Error while closing pool connections: %s", e)
            cls._pool = None
            cls._initialized = False
            logger.info("Database connection pool closed")

