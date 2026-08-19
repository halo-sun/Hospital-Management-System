"""User service – dedicated to user account management.

Provides user creation, role resolution, and credential validation
independent of the authentication/session logic in AuthService.
Both AuthService and DoctorService use this service instead of
depending on each other.
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any, Tuple

import bcrypt

from src.repositories.user_repository import UserRepository
from src.config import app_config

logger = logging.getLogger(__name__)


class UserService:
    """Handles user account CRUD and role resolution.

    Single responsibility: manage user records in the database.
    Does NOT manage sessions, login state, or authentication tokens.
    """

    def __init__(self) -> None:
        """Initialise UserService with the user repository."""
        self._user_repo = UserRepository()

    # ── Role resolution ────────────────────────────────────────

    def get_role_id(self, role_name: str) -> Optional[int]:
        """Resolve a role name to its database role_id.

        Args:
            role_name: The role name string (e.g. ``"Doctor"``).

        Returns:
            The role_id if found, else None.
        """
        return self._user_repo.get_role_id(role_name)

    # ── User CRUD ──────────────────────────────────────────────

    def create_user(self, user_data: Dict[str, Any]) -> Tuple[bool, str, Optional[int]]:
        """Create a new user account after validating inputs.

        Args:
            user_data: Dictionary with ``username``, ``password``,
                       ``role_id``, and optional ``email`` / ``full_name``.

        Returns:
            Tuple of (success, message, new_user_id_or_None).
        """
        if not user_data.get("username"):
            return False, "Username is required.", None

        if not user_data.get("password"):
            return False, "Password is required.", None

        if len(user_data["password"]) < app_config.password_min_length:
            return (
                False,
                f"Password must be at least {app_config.password_min_length} characters.",
                None,
            )

        existing = self._user_repo.find_by_username(user_data["username"])
        if existing:
            return False, "Username already exists.", None

        # Hash the password before storing
        raw_pw = user_data.pop("password")
        user_data["password_hash"] = bcrypt.hashpw(
            raw_pw.encode("utf-8"),
            bcrypt.gensalt(app_config.bcrypt_rounds),
        ).decode("utf-8")

        user_id = self._user_repo.create_user(user_data)
        logger.info("User created: %s (id=%d)", user_data.get("username"), user_id)
        return True, "User created successfully.", user_id

    def get_all_users(self) -> list:
        """Retrieve all users with their role information.

        Returns:
            List of user records (dicts).
        """
        return self._user_repo.find_all_with_roles()

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a single user by ID.

        Args:
            user_id: The user's database ID.

        Returns:
            User record dict or None if not found.
        """
        return self._user_repo.find_by_id_with_role(user_id)

    def reset_password(
        self,
        target_user_id: int,
        new_password: str,
    ) -> Tuple[bool, str]:
        """Hash and persist a new password for a user.

        Args:
            target_user_id: The user whose password is being reset.
            new_password: The new plaintext password.

        Returns:
            Tuple of (success, message).
        """
        if len(new_password) < app_config.password_min_length:
            return (
                False,
                f"Password must be at least {app_config.password_min_length} characters.",
            )

        pw_hash = bcrypt.hashpw(
            new_password.encode("utf-8"),
            bcrypt.gensalt(app_config.bcrypt_rounds),
        ).decode("utf-8")
        self._user_repo.reset_password(target_user_id, pw_hash)
        logger.info("Password reset for user_id=%d", target_user_id)
        return True, "Password reset successfully."
