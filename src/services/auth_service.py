"""Authentication service for login, logout, and password management.

Enhancements over the original:

- **Remember Me** – persists a local token so returning users can
  skip the login screen (managed via ``RememberTokenManager``).
- **Structured exceptions** – ``AccountLockedError``, ``AccountInactiveError``,
  etc. let callers catch typed errors instead of parsing strings.
- **Restore by token** – ``restore_session()`` re-hydrates a session
  from a saved token without asking for credentials.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

import bcrypt

from src.repositories.user_repository import UserRepository
from src.config import app_config
from src.constants import Role
from src.auth.exceptions import (
    AccountInactiveError,
    AccountLockedError,
    AuthenticationError,
    SessionExpiredError,
)
from src.auth.remember_token import RememberTokenManager

logger = logging.getLogger(__name__)


class AuthService:
    """Handles user authentication, session management, and password operations.

    Single responsibility: authenticate users and manage their in-memory
    session.  Delegates user CRUD to ``UserService`` and persistent
    tokens to ``RememberTokenManager``.
    """

    def __init__(
        self,
        user_repo: Optional[UserRepository] = None,
        token_manager: Optional[RememberTokenManager] = None,
    ) -> None:
        """Initialise AuthService with optional dependency injection.

        Args:
            user_repo: Repository for user data. Created automatically if omitted.
            token_manager: Remember-Me token manager. Created automatically.
        """
        self._user_repo = user_repo or UserRepository()
        self._token_manager = token_manager or RememberTokenManager()
        self._current_user: Optional[Dict[str, Any]] = None
        self._session_start: Optional[datetime] = None

    # ── Session properties ─────────────────────────────────────

    @property
    def current_user(self) -> Optional[Dict[str, Any]]:
        """Return the currently logged-in user dict, or None."""
        return self._current_user

    @property
    def is_logged_in(self) -> bool:
        """Check if a user is currently logged in."""
        return self._current_user is not None

    @property
    def current_user_id(self) -> Optional[int]:
        """Return the current user's ID, or None."""
        if self._current_user:
            return self._current_user.get("user_id")
        return None

    @property
    def current_role(self) -> Optional[str]:
        """Return the current user's role name, or None."""
        if self._current_user:
            return self._current_user.get("role_name")
        return None

    @property
    def current_username(self) -> Optional[str]:
        """Return the current user's username, or None."""
        if self._current_user:
            return self._current_user.get("username")
        return None

    @property
    def remember_me_exists(self) -> bool:
        """Check whether a Remember-Me token exists on disk."""
        return self._token_manager.exists

    # ── Session time ───────────────────────────────────────────

    @property
    def session_elapsed_minutes(self) -> float:
        """Return how many minutes have passed since login.

        Returns:
            Minutes elapsed, or 0 if no active session.
        """
        if not self._session_start:
            return 0.0
        return (datetime.now() - self._session_start).total_seconds() / 60.0

    # ── Core authentication ────────────────────────────────────

    def login(
        self,
        username: str,
        password: str,
        remember_me: bool = False,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Authenticate a user with username and password.

        Performs credential verification, account-lock checks, and
        failed-attempt tracking.  If ``remember_me`` is True a local
        token is written so the user can skip login on next launch.

        Args:
            username: The username to authenticate.
            password: The plaintext password to verify.
            remember_me: Whether to persist a session token for future launches.

        Returns:
            Tuple of (success, message, user_data_or_None).

        Raises:
            AccountLockedError: If the account is temporarily locked.
            AccountInactiveError: If the account status is Inactive.
        """
        user = self._user_repo.find_by_username(username)
        if not user:
            logger.warning("Login attempt for unknown user: %s", username)
            return False, "Invalid username or password", None

        # Account active?
        if user.get("status") == "Inactive":
            logger.warning("Login attempt for inactive user: %s", username)
            raise AccountInactiveError()

        # Account locked?
        if user.get("locked_until"):
            locked_until = user["locked_until"]
            if isinstance(locked_until, str):
                locked_until = datetime.fromisoformat(locked_until)
            if datetime.now() < locked_until:
                remaining = int((locked_until - datetime.now()).total_seconds() // 60)
                raise AccountLockedError(remaining_minutes=remaining)

        # Password check
        if not self._verify_password(password, user.get("password_hash", "")):
            self._user_repo.update_login_info(user["user_id"], success=False)
            attempts = user.get("failed_login_attempts", 0) + 1
            if attempts >= app_config.max_login_attempts:
                lockout = datetime.now() + timedelta(
                    minutes=app_config.lockout_duration_minutes
                )
                self._user_repo.set_locked(user["user_id"], lockout)
                logger.warning("Account locked due to failed attempts: %s", username)
                return False, "Too many failed attempts. Account locked.", None
            remaining = app_config.max_login_attempts - attempts
            return False, f"Invalid credentials. {remaining} attempts remaining.", None

        # Success
        self._user_repo.update_login_info(user["user_id"], success=True)
        self._start_session(user)

        if remember_me:
            self._token_manager.save(username)

        logger.info("User logged in: %s (%s)", username, user.get("role_name"))
        return True, "Login successful", user

    def restore_session(self) -> Optional[Dict[str, Any]]:
        """Attempt to restore a session from a Remember-Me token.

        Called at application startup.  If a valid token exists the
        corresponding user is looked up and a session is started
        without requiring a password.

        Returns:
            The user dict if the session was restored, else None.
        """
        username = self._token_manager.load()
        if not username:
            return None

        user = self._user_repo.find_by_username(username)
        if not user or user.get("status") != "Active":
            self._token_manager.clear()
            return None

        self._start_session(user)
        logger.info("Session restored via Remember-Me for: %s", username)
        return user

    # ── Logout ─────────────────────────────────────────────────

    def logout(self) -> bool:
        """Log out the current user and clear session data.

        Also clears the Remember-Me token if one exists.

        Returns:
            True if logout succeeded, False if no user was logged in.
        """
        if not self._current_user:
            return False
        username = self._current_user.get("username", "unknown")
        self._clear_session()
        self._token_manager.clear()
        logger.info("User logged out: %s", username)
        return True

    def is_session_expired(self) -> bool:
        """Check whether the current session has timed out.

        Returns:
            True if the session is expired or no session exists.
        """
        if not self._session_start:
            return False
        elapsed = datetime.now() - self._session_start
        if elapsed.total_seconds() > app_config.session_timeout_minutes * 60:
            self._clear_session()
            return True
        return False

    # ── Password management ────────────────────────────────────

    def reset_password(
        self,
        target_user_id: int,
        new_password: str,
        admin_id: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """Reset a user's password (admin operation).

        Args:
            target_user_id: ID of the user whose password is being reset.
            new_password: The new plaintext password.
            admin_id: ID of the admin performing the reset, for audit.

        Returns:
            Tuple of (success, message).
        """
        if len(new_password) < app_config.password_min_length:
            return False, f"Password must be at least {app_config.password_min_length} characters."

        pw_hash = self._hash_password(new_password)
        self._user_repo.reset_password(target_user_id, pw_hash)
        logger.info(
            "Password reset for user_id=%d by admin_id=%s",
            target_user_id, admin_id,
        )
        return True, "Password reset successfully."

    def change_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> Tuple[bool, str]:
        """Change the current user's own password.

        Args:
            user_id: The user's ID.
            current_password: The current password for verification.
            new_password: The new password.

        Returns:
            Tuple of (success, message).
        """
        user = self._user_repo.find_by_id_with_role(user_id)
        if not user:
            return False, "User not found."

        if not self._verify_password(current_password, user.get("password_hash", "")):
            return False, "Current password is incorrect."

        if len(new_password) < app_config.password_min_length:
            return False, f"Password must be at least {app_config.password_min_length} characters."

        pw_hash = self._hash_password(new_password)
        self._user_repo.reset_password(user_id, pw_hash)
        logger.info("Password changed for user_id=%d", user_id)
        return True, "Password changed successfully."

    # ── Role checks ────────────────────────────────────────────

    def has_role(self, *role_names: str) -> bool:
        """Check whether the current user has one of the specified roles.

        Args:
            *role_names: One or more acceptable role names.

        Returns:
            True if the current user's role matches any of the given names.
        """
        if not self._current_user:
            return False
        return self._current_user.get("role_name") in role_names

    def is_admin(self) -> bool:
        """Check whether the current user is an administrator."""
        return self.has_role(Role.ADMIN)

    def is_doctor(self) -> bool:
        """Check whether the current user is a doctor."""
        return self.has_role(Role.DOCTOR)

    def is_receptionist(self) -> bool:
        """Check whether the current user is a receptionist."""
        return self.has_role(Role.RECEPTIONIST)

    # ── User management ────────────────────────────────────────

    def get_all_users(self) -> list:
        """Retrieve all users with their role information.

        Returns:
            List of user record dicts.
        """
        return self._user_repo.find_all_with_roles()

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a single user by ID with role info.

        Args:
            user_id: The user's database ID.

        Returns:
            User dict or None.
        """
        return self._user_repo.find_by_id_with_role(user_id)

    def create_user(self, user_data: Dict[str, Any]) -> Tuple[bool, str, Optional[int]]:
        """Create a new user account.

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
            return False, f"Password must be at least {app_config.password_min_length} characters.", None

        existing = self._user_repo.find_by_username(user_data["username"])
        if existing:
            return False, "Username already exists.", None

        user_data["password_hash"] = self._hash_password(user_data.pop("password"))
        user_id = self._user_repo.create_user(user_data)
        logger.info("User created: %s (id=%d)", user_data.get("username"), user_id)
        return True, "User created successfully.", user_id

    # ── Internal helpers ───────────────────────────────────────

    def _start_session(self, user: Dict[str, Any]) -> None:
        """Establish an in-memory session for the given user.

        Args:
            user: The authenticated user dict.
        """
        self._current_user = user
        self._session_start = datetime.now()

    def _clear_session(self) -> None:
        """Destroy the in-memory session without touching the token file."""
        self._current_user = None
        self._session_start = None

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash a password using bcrypt.

        Args:
            password: The plaintext password.

        Returns:
            The hashed password string.
        """
        return bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(app_config.bcrypt_rounds),
        ).decode("utf-8")

    @staticmethod
    def _verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against a bcrypt hash.

        Args:
            password: The plaintext password to check.
            password_hash: The stored hash to compare against.

        Returns:
            True if the password matches the hash, False otherwise.
        """
        if not password_hash:
            logger.warning("Empty password_hash provided for verification")
            return False
        if not password:
            return False
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"), password_hash.encode("utf-8")
            )
        except (TypeError, ValueError, AttributeError) as e:
            logger.error("Password verification failed with unexpected input: %s", e)
            return False
