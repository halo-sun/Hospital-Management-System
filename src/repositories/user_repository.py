"""User repository for user and role CRUD operations."""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from src.repositories.base_repository import BaseRepository
from src.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository):
    """Repository for user-related database operations."""

    def __init__(self) -> None:
        """Initialize UserRepository."""
        super().__init__("users")

    def find_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Find a user by username.

        Args:
            username: The username to search for.

        Returns:
            User dictionary or None if not found.
        """
        query = """
            SELECT u.*, r.role_name, r.description as role_description
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
            WHERE u.username = %s
        """
        return DatabaseConnection.execute_query(query, (username,), fetch_one=True)

    def find_by_id_with_role(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Find a user by ID with role information.

        Args:
            user_id: The user ID to search for.

        Returns:
            User dictionary with role data or None if not found.
        """
        query = """
            SELECT u.*, r.role_name, r.description as role_description
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
            WHERE u.user_id = %s
        """
        return DatabaseConnection.execute_query(query, (user_id,), fetch_one=True)

    def find_all_with_roles(
        self, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find all users with their role information.

        Args:
            status: Optional status filter (Active/Inactive).

        Returns:
            List of user dictionaries with role data.
        """
        query = """
            SELECT u.user_id, u.username, u.email, u.full_name, u.status,
                   u.last_login, u.failed_login_attempts, u.locked_until,
                   u.created_at, u.updated_at,
                   r.role_id, r.role_name
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
        """
        params: list = []
        if status:
            query += " WHERE u.status = %s"
            params.append(status)

        query += " ORDER BY u.created_at DESC"
        return DatabaseConnection.execute_query(query, tuple(params)) or []

    def create_user(self, user_data: Dict[str, Any], conn=None) -> int:
        """Insert a new user record.

        Args:
            user_data: Dictionary of user fields.
            conn: Optional transactional connection.

        Returns:
            The new user's ID.
        """
        return self.insert(user_data, conn=conn)

    def update_user(self, user_id: int, user_data: Dict[str, Any]) -> int:
        """Update an existing user record.

        Args:
            user_id: The user ID to update.
            user_data: Dictionary of fields to update.

        Returns:
            Number of rows affected.
        """
        user_data['updated_at'] = datetime.now()
        return self.update("user_id", user_id, user_data)

    def update_login_info(self, user_id: int, success: bool) -> None:
        """Update login metadata after an authentication attempt.

        Args:
            user_id: The user ID.
            success: Whether the login was successful.
        """
        if success:
            query = """
                UPDATE users
                SET last_login = %s, failed_login_attempts = 0, locked_until = NULL
                WHERE user_id = %s
            """
            DatabaseConnection.execute_update(query, (datetime.now(), user_id))
        else:
            query = """
                UPDATE users
                SET failed_login_attempts = failed_login_attempts + 1
                WHERE user_id = %s
            """
            DatabaseConnection.execute_update(query, (user_id,))

    def set_locked(self, user_id: int, locked_until: datetime) -> int:
        """Lock a user account until the specified time.

        Args:
            user_id: The user ID to lock.
            locked_until: When the lock expires.

        Returns:
            Number of rows affected.
        """
        return self.update("user_id", user_id, {"locked_until": locked_until})

    def reset_password(self, user_id: int, new_password_hash: str) -> int:
        """Reset a user's password.

        Args:
            user_id: The user ID.
            new_password_hash: The new hashed password.

        Returns:
            Number of rows affected.
        """
        return self.update("user_id", user_id, {
            "password_hash": new_password_hash,
            "failed_login_attempts": 0,
            "locked_until": None,
            "updated_at": datetime.now(),
        })

    def search_users(self, search_term: str) -> List[Dict[str, Any]]:
        """Search users by username, full name, or email.

        Args:
            search_term: Text to search for.

        Returns:
            List of matching user records.
        """
        return self.search(
            search_columns=["username", "full_name", "email"],
            search_term=search_term,
            order_by="username ASC",
            limit=50,
        )

    def find_by_role(self, role_name: str) -> List[Dict[str, Any]]:
        """Find all users with a specific role.

        Args:
            role_name: The role name to filter by.

        Returns:
            List of user records with the given role.
        """
        query = """
            SELECT u.*, r.role_name
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
            WHERE r.role_name = %s AND u.status = 'Active'
            ORDER BY u.full_name ASC
        """
        return DatabaseConnection.execute_query(query, (role_name,)) or []

    def get_role_id(self, role_name: str) -> Optional[int]:
        """Get the role_id for a given role name.

        Args:
            role_name: The role name to look up.

        Returns:
            The role_id or None if not found.
        """
        result = DatabaseConnection.execute_query(
            "SELECT role_id FROM roles WHERE role_name = %s",
            (role_name,),
            fetch_one=True,
        )
        return result['role_id'] if result else None

    def count_active_users(self) -> int:
        """Count the total number of active users.

        Returns:
            Number of active users.
        """
        return self.count_where({"status": "Active"})

    def count_by_role(self, role_name: str) -> int:
        """Count users assigned a specific role (any status).

        Args:
            role_name: The role name to count (e.g. "Admin").

        Returns:
            Number of users with the given role.
        """
        query = """
            SELECT COUNT(*) AS total
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
            WHERE r.role_name = %s
        """
        result = DatabaseConnection.execute_query(
            query, (role_name,), fetch_one=True,
        )
        return result["total"] if result else 0

    def delete_user(self, user_id: int) -> int:
        """Delete a user by ID.

        Args:
            user_id: The user ID to delete.

        Returns:
            Number of rows deleted.
        """
        return self.delete("user_id", user_id)
