"""Staff service – dedicated to receptionist and staff management.

Provides business logic for managing non-doctor staff (receptionists)
independent of the doctor-specific logic in DoctorService.
"""
from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from src.repositories.user_repository import UserRepository
from src.services.user_service import UserService
from src.constants import Role, UserStatus

logger = logging.getLogger(__name__)


class StaffService:
    """Handles receptionist/staff account management.

    Single responsibility: manage staff user accounts (non-doctor
    personnel) — creation, listing, status management, and search.
    """

    def __init__(self) -> None:
        """Initialise StaffService with required services and repos."""
        self._user_repo = UserRepository()
        self._user_service = UserService()

    # ── Staff listing ──────────────────────────────────────────

    def get_all_staff(self) -> List[Dict[str, Any]]:
        """Get all staff members (users with non-admin roles).

        Returns:
            List of user records with role information.
        """
        return self._user_repo.find_all_with_roles()

    def get_receptionists(self) -> List[Dict[str, Any]]:
        """Get all receptionist users.

        Returns:
            List of receptionist user records.
        """
        return self._user_repo.find_by_role(Role.RECEPTIONIST)

    def get_staff_member(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a single staff member by user ID.

        Args:
            user_id: The user ID.

        Returns:
            User record or None if not found.
        """
        return self._user_repo.find_by_id_with_role(user_id)

    # ── Staff CRUD ─────────────────────────────────────────────

    def create_staff(
        self, data: Dict[str, Any], role_name: str = Role.RECEPTIONIST
    ) -> Tuple[bool, str, Optional[int]]:
        """Create a new staff user account.

        Args:
            data: Dictionary with username, password, full_name, email, etc.
            role_name: The role to assign (default: Receptionist).

        Returns:
            Tuple of (success, message, new_user_id_or_None).
        """
        role_id = self._user_service.get_role_id(role_name)
        if not role_id:
            return False, f"'{role_name}' role not found in system.", None

        data["role_id"] = role_id
        success, msg, user_id = self._user_service.create_user(data)
        if success:
            logger.info("Staff created: %s (id=%d, role=%s)", data.get("username"), user_id, role_name)
        return success, msg, user_id

    def update_staff(self, user_id: int, data: Dict[str, Any]) -> Tuple[bool, str]:
        """Update a staff member's profile fields.

        Args:
            user_id: The user ID to update.
            data: Fields to update (full_name, email, status, etc.).

        Returns:
            Tuple of (success, message).
        """
        existing = self._user_repo.find_by_id_with_role(user_id)
        if not existing:
            return False, "Staff member not found."

        data["updated_at"] = datetime.now()
        self._user_repo.update_user(user_id, data)
        logger.info("Staff updated: user_id=%d", user_id)
        return True, "Staff member updated successfully."

    def delete_staff(self, user_id: int) -> Tuple[bool, str]:
        """Delete a staff user account.

        Args:
            user_id: The user ID to delete.

        Returns:
            Tuple of (success, message).
        """
        existing = self._user_repo.find_by_id_with_role(user_id)
        if not existing:
            return False, "Staff member not found."

        self._user_repo.delete_user(user_id)
        logger.info("Staff deleted: user_id=%d", user_id)
        return True, "Staff member deleted successfully."

    # ── Staff search ───────────────────────────────────────────

    def search_staff(self, search_term: str) -> List[Dict[str, Any]]:
        """Search staff members by username, full name, or email.

        Args:
            search_term: Text to search for.

        Returns:
            List of matching user records.
        """
        return self._user_repo.search_users(search_term)

    # ── Status management ──────────────────────────────────────

    def activate_staff(self, user_id: int) -> Tuple[bool, str]:
        """Activate a staff member's account.

        Args:
            user_id: The user ID.

        Returns:
            Tuple of (success, message).
        """
        existing = self._user_repo.find_by_id_with_role(user_id)
        if not existing:
            return False, "Staff member not found."

        self._user_repo.update_user(user_id, {"status": UserStatus.ACTIVE})
        logger.info("Staff activated: user_id=%d", user_id)
        return True, "Staff member activated."

    def deactivate_staff(self, user_id: int) -> Tuple[bool, str]:
        """Deactivate a staff member's account.

        Args:
            user_id: The user ID.

        Returns:
            Tuple of (success, message).
        """
        existing = self._user_repo.find_by_id_with_role(user_id)
        if not existing:
            return False, "Staff member not found."

        self._user_repo.update_user(user_id, {"status": UserStatus.INACTIVE})
        logger.info("Staff deactivated: user_id=%d", user_id)
        return True, "Staff member deactivated."
