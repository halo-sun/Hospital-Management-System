"""Staff controller – coordinates staff management requests.

Operates independently of DoctorController by delegating to
StaffService for receptionist and staff management logic.
"""
import logging
from typing import Optional, Dict, Any, Tuple, List

from src.services.staff_service import StaffService
from src.services.audit_service import AuditService
from src.constants import Role, AuditAction
from src.auth.rbac import require_role
from src.controllers.auth_controller import AuthController
from src.config import app_config

logger = logging.getLogger(__name__)


class StaffController:
    """Handles staff (receptionist) management requests from the GUI layer.

    Single responsibility: manage non-doctor user accounts.
    """

    def __init__(self, auth_ctrl: Optional[AuthController] = None) -> None:
        """Initialize StaffController with required services.

        Args:
            auth_ctrl: Auth controller providing the current role
                (used by the RBAC decorator).
        """
        self._auth_ctrl = auth_ctrl
        self._staff_service = StaffService()
        self._audit_service = AuditService()

    @property
    def _current_role(self) -> Optional[str]:
        """Return the logged-in user's role for RBAC checks."""
        if self._auth_ctrl is None:
            return None
        return self._auth_ctrl.current_role

    # ── Input validation ───────────────────────────────────────

    @staticmethod
    def validate_staff_data(data: Dict[str, Any], is_new: bool = True) -> Tuple[bool, str]:
        """Validate staff creation / edit form data.

        Args:
            data: Dictionary with username, password, full_name, email, etc.
            is_new: Whether this is a new user (requires username + password).

        Returns:
            Tuple of (valid, error_message).
        """
        if is_new:
            if not data.get("username", "").strip():
                return False, "Username is required."
            if len(data["username"].strip()) < 3:
                return False, "Username must be at least 3 characters."
            if not data.get("password"):
                return False, "Password is required."
            if len(data["password"]) < app_config.password_min_length:
                return False, f"Password must be at least {app_config.password_min_length} characters."

        email = data.get("email", "")
        if email:
            from src.utils.validators import validate_email
            valid, msg = validate_email(email)
            if not valid:
                return False, msg

        return True, ""

    # ── Staff operations ───────────────────────────────────────

    @require_role(Role.ADMIN)
    def get_all_staff(self) -> List[Dict[str, Any]]:
        """Get all staff members with role info.

        Returns:
            List of user records.
        """
        return self._staff_service.get_all_staff()

    @require_role(Role.ADMIN)
    def get_receptionists(self) -> List[Dict[str, Any]]:
        """Get all receptionist users.

        Returns:
            List of receptionist records.
        """
        return self._staff_service.get_receptionists()

    @require_role(Role.ADMIN)
    def get_staff_member(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a single staff member.

        Args:
            user_id: The user ID.

        Returns:
            User record or None.
        """
        return self._staff_service.get_staff_member(user_id)

    @require_role(Role.ADMIN)
    def create_staff(
        self,
        data: Dict[str, Any],
        role_name: str = Role.RECEPTIONIST,
        audit_user_id: Optional[int] = None,
    ) -> Tuple[bool, str, Optional[int]]:
        """Create a new staff user.

        Args:
            data: Form data with username, password, role, etc.
            role_name: Role to assign (default: Receptionist).
            audit_user_id: The current user's ID for audit logging.

        Returns:
            Tuple of (success, message, new_user_id_or_None).
        """
        valid, msg = self.validate_staff_data(data, is_new=True)
        if not valid:
            return False, msg, None

        success, message, user_id = self._staff_service.create_staff(data, role_name)
        if success and user_id and audit_user_id:
            self._audit_service.log_create(
                audit_user_id, "Staff", str(user_id),
                {k: v for k, v in data.items() if k not in ("password",)},
            )
        return success, message, user_id

    @require_role(Role.ADMIN)
    def update_staff(
        self, user_id: int, data: Dict[str, Any], audit_user_id: Optional[int] = None
    ) -> Tuple[bool, str]:
        """Update a staff member.

        Args:
            user_id: The user ID.
            data: Fields to update.
            audit_user_id: The current user's ID for audit logging.

        Returns:
            Tuple of (success, message).
        """
        valid, msg = self.validate_staff_data(data, is_new=False)
        if not valid:
            return False, msg

        success, message = self._staff_service.update_staff(user_id, data)
        if success and audit_user_id:
            self._audit_service.log_update(
                audit_user_id, "Staff", str(user_id), data,
            )
        return success, message

    @require_role(Role.ADMIN)
    def delete_staff(self, user_id: int, audit_user_id: Optional[int] = None) -> Tuple[bool, str]:
        """Delete a staff member.

        Args:
            user_id: The user ID.
            audit_user_id: The current user's ID for audit logging.

        Returns:
            Tuple of (success, message).
        """
        success, message = self._staff_service.delete_staff(user_id)
        if success and audit_user_id:
            self._audit_service.log(
                AuditAction.DELETE,
                user_id=audit_user_id,
                target_entity="Staff",
                target_id=str(user_id),
            )
        return success, message

    @require_role(Role.ADMIN)
    def search_staff(self, search_term: str) -> List[Dict[str, Any]]:
        """Search staff by username, name, or email.

        Args:
            search_term: Text to search for.

        Returns:
            List of matching records.
        """
        return self._staff_service.search_staff(search_term)

    @require_role(Role.ADMIN)
    def activate_staff(self, user_id: int, audit_user_id: Optional[int] = None) -> Tuple[bool, str]:
        """Activate a staff account.

        Args:
            user_id: The user ID.
            audit_user_id: The current user's ID for audit logging.

        Returns:
            Tuple of (success, message).
        """
        return self._staff_service.activate_staff(user_id)

    @require_role(Role.ADMIN)
    def deactivate_staff(self, user_id: int, audit_user_id: Optional[int] = None) -> Tuple[bool, str]:
        """Deactivate a staff account.

        Args:
            user_id: The user ID.
            audit_user_id: The current user's ID for audit logging.

        Returns:
            Tuple of (success, message).
        """
        return self._staff_service.deactivate_staff(user_id)
