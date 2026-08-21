"""Authentication controller – coordinates login/logout/password ops."""
import logging
from typing import Optional, Dict, Any, Tuple, List

from src.services.auth_service import AuthService
from src.services.audit_service import AuditService
from src.config import app_config
from src.constants import AuditAction, Role
from src.auth.rbac import require_role

logger = logging.getLogger(__name__)


class AuthController:
    """Handles authentication requests from the GUI layer.

    Validates input, delegates to AuthService, and records audit entries.
    """

    def __init__(self) -> None:
        """Initialize AuthController with required services."""
        self._auth_service = AuthService()
        self._audit_service = AuditService()

    @property
    def current_user(self) -> Optional[Dict[str, Any]]:
        """Return the currently logged-in user."""
        return self._auth_service.current_user

    @property
    def is_logged_in(self) -> bool:
        """Check whether a user is logged in."""
        return self._auth_service.is_logged_in

    @property
    def current_role(self) -> Optional[str]:
        """Return the role name of the current user."""
        return self._auth_service.current_role

    @property
    def current_user_id(self) -> Optional[int]:
        """Return the current user's ID."""
        return self._auth_service.current_user_id

    # ── Input validation helpers ───────────────────────────────

    @staticmethod
    def validate_login(username: str, password: str) -> Tuple[bool, str]:
        """Validate login form inputs.

        Args:
            username: The username entered.
            password: The password entered.

        Returns:
            Tuple of (valid, error_message).
        """
        if not username or not username.strip():
            return False, "Username is required."
        if not password:
            return False, "Password is required."
        if len(username.strip()) < 3:
            return False, "Username must be at least 3 characters."
        return True, ""

    @staticmethod
    def validate_password_change(
        current_pw: str, new_pw: str, confirm_pw: str
    ) -> Tuple[bool, str]:
        """Validate password change form inputs.

        Args:
            current_pw: The current password.
            new_pw: The new password.
            confirm_pw: Confirmation of the new password.

        Returns:
            Tuple of (valid, error_message).
        """
        if not current_pw:
            return False, "Current password is required."
        if not new_pw:
            return False, "New password is required."
        if new_pw != confirm_pw:
            return False, "New passwords do not match."
        if len(new_pw) < 8:
            return False, "Password must be at least 8 characters."
        return True, ""

    # ── Authentication operations ──────────────────────────────

    def login(
        self, username: str, password: str, remember_me: bool = False,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Authenticate a user with optional Remember-Me persistence.

        Args:
            username: The username.
            password: The plaintext password.
            remember_me: Whether to save a session token for future launches.

        Returns:
            Tuple of (success, message, user_data_or_None).

        Raises:
            AccountLockedError: Via AuthService, caught by caller for UX.
            AccountInactiveError: Via AuthService, caught by caller for UX.
        """
        valid, msg = self.validate_login(username, password)
        if not valid:
            return False, msg, None

        success, message, user = self._auth_service.login(
            username.strip(), password, remember_me=remember_me,
        )

        if user:
            self._audit_service.log_login(user["user_id"], success)
        else:
            self._audit_service.log(
                AuditAction.LOGIN_FAILED,
                target_entity="User",
                target_id=username.strip(),
            )

        return success, message, user

    @property
    def remember_me_exists(self) -> bool:
        """Check whether a Remember-Me token is present on disk."""
        return self._auth_service.remember_me_exists

    def restore_session(self) -> Optional[Dict[str, Any]]:
        """Try to restore a session from the Remember-Me token.

        Returns:
            User dict if restored, else None.
        """
        return self._auth_service.restore_session()

    def logout(self) -> bool:
        """Log out the current user and clear the Remember-Me token.

        Returns:
            True if logout succeeded.
        """
        if self.current_user_id:
            self._audit_service.log_logout(self.current_user_id)
        return self._auth_service.logout()

    def is_session_expired(self) -> bool:
        """Check whether the current session has timed out.

        Returns:
            True if the session is expired.
        """
        return self._auth_service.is_session_expired()

    def refresh_session(self) -> None:
        """Reset the session timeout clock on user activity.

        Should be called whenever the user performs an action
        (navigation, button click) so the session does not expire
        during active use.
        """
        self._auth_service.refresh_session()

    def change_password(
        self, current_password: str, new_password: str, confirm_password: str
    ) -> Tuple[bool, str]:
        """Change the current user's password.

        Args:
            current_password: The current password for verification.
            new_password: The new password.
            confirm_password: Confirmation of the new password.

        Returns:
            Tuple of (success, message).
        """
        valid, msg = self.validate_password_change(
            current_password, new_password, confirm_password
        )
        if not valid:
            return False, msg

        if not self.current_user_id:
            return False, "No user logged in."

        success, message = self._auth_service.change_password(
            self.current_user_id, current_password, new_password
        )
        if success:
            self._audit_service.log(
                AuditAction.PASSWORD_CHANGE,
                user_id=self.current_user_id,
                target_entity="User",
                target_id=str(self.current_user_id),
            )
        return success, message

    @require_role(Role.ADMIN)
    def reset_password(
        self, target_user_id: int, new_password: str
    ) -> Tuple[bool, str]:
        """Reset a user's password (admin only).

        Args:
            target_user_id: The user whose password is being reset.
            new_password: The new password.

        Returns:
            Tuple of (success, message).
        """
        if not self._auth_service.is_admin():
            return False, "Only administrators can reset passwords."

        if len(new_password) < app_config.password_min_length:
            return False, f"Password must be at least {app_config.password_min_length} characters."

        success, message = self._auth_service.reset_password(
            target_user_id, new_password, admin_id=self.current_user_id
        )
        if success:
            self._audit_service.log(
                AuditAction.PASSWORD_RESET,
                user_id=self.current_user_id,
                target_entity="User",
                target_id=str(target_user_id),
            )
        return success, message

    # ── Role checks ────────────────────────────────────────────

    def is_admin(self) -> bool:
        """Check whether the current user is an admin."""
        return self._auth_service.is_admin()

    def is_doctor(self) -> bool:
        """Check whether the current user is a doctor."""
        return self._auth_service.is_doctor()

    def is_receptionist(self) -> bool:
        """Check whether the current user is a receptionist."""
        return self._auth_service.is_receptionist()

    def has_role(self, *roles: str) -> bool:
        """Check whether the current user has one of the given roles."""
        return self._auth_service.has_role(*roles)

    # ── User management (admin) ────────────────────────────────

    @require_role(Role.ADMIN)
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users with role info.

        Returns:
            List of user records.
        """
        return self._auth_service.get_all_users()

    @require_role(Role.ADMIN)
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a user by ID.

        Args:
            user_id: The user ID.

        Returns:
            User record or None.
        """
        return self._auth_service.get_user_by_id(user_id)

    @require_role(Role.ADMIN)
    def create_user(
        self, user_data: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[int]]:
        """Create a new user account (admin only).

        Args:
            user_data: Dictionary with username, password, role_id, etc.

        Returns:
            Tuple of (success, message, new_user_id_or_None).
        """
        if not self._auth_service.is_admin():
            return False, "Only administrators can create users.", None

        success, message, user_id = self._auth_service.create_user(user_data)
        if success and user_id:
            self._audit_service.log_create(
                self.current_user_id, "User", str(user_id),
                {k: v for k, v in user_data.items() if k != "password"},
            )
        return success, message, user_id
