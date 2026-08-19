"""First-run setup controller – administrator account creation before login.

Shown on application launch when the ``users`` table contains no admin
account.  Provides the startup check (``has_admin``), server-side
per-field validation (the GUI never relies on client-side checks
alone), and admin creation that **reuses** the normal user-creation
flow (``AuthService.create_user``) plus an audit entry — there is no
second, separate insertion path.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

from src.constants import AuditAction, Role, UserStatus
from src.repositories.user_repository import UserRepository
from src.services.auth_service import AuthService
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)

# Minimum rules for the first-run administrator credential.  These are
# deliberately stricter than the general password policy.
PASSWORD_MIN_LENGTH = 10
USERNAME_MIN_LENGTH = 3

# Common/weak passwords rejected during first-run setup.  Matching is
# case-insensitive.
WEAK_PASSWORDS = frozenset({
    "admin", "password", "admin123", "password123",
    "12345678", "123456789", "1234567890",
    "qwerty", "qwerty123", "letmein", "welcome", "welcome123",
    "abc123", "password1", "admin1234", "hospital", "hospital123",
    "letmein123", "iloveyou", "monkey", "dragon",
})


class SetupController:
    """Coordinates first-run administrator account creation.

    Not RBAC-gated — it runs before any user can log in.  The
    ``has_admin`` check runs at every application launch against the
    users table (the source of truth), not against a marker file.
    """

    def __init__(
        self,
        user_repo: Optional[UserRepository] = None,
        auth_service: Optional[AuthService] = None,
        audit_service: Optional[AuditService] = None,
    ) -> None:
        """Initialise SetupController with optional dependency injection.

        Args:
            user_repo: Repository for user data. Created automatically if omitted.
            auth_service: Authentication service. Created automatically.
            audit_service: Audit logging service. Created automatically.
        """
        self._user_repo = user_repo or UserRepository()
        self._auth_service = auth_service or AuthService()
        self._audit_service = audit_service or AuditService()

    # ── Startup check ──────────────────────────────────────────

    def has_admin(self) -> bool:
        """Return True if at least one admin user exists in the database.

        Returns:
            True if any user with the Admin role exists.
        """
        return self._user_repo.count_by_role(Role.ADMIN) > 0

    # ── Server-side validation ─────────────────────────────────

    def validate(
        self, username: str, password: str, confirm_password: str,
    ) -> Dict[str, str]:
        """Validate first-run setup inputs, returning per-field errors.

        The GUI relies on this method (not client-side checks) as the
        authority.  Each failing rule is reported on its own field so
        the user knows exactly what to fix.

        Args:
            username: The desired admin username.
            password: The desired password.
            confirm_password: Password confirmation.

        Returns:
            Dict mapping field name (``username``, ``password``,
            ``confirm``) to a human-readable error message.  Empty when
            the input is valid.
        """
        errors: Dict[str, str] = {}

        username = (username or "").strip()
        if not username:
            errors["username"] = "Username is required."
        elif len(username) < USERNAME_MIN_LENGTH:
            errors["username"] = (
                f"Username must be at least {USERNAME_MIN_LENGTH} characters."
            )
        elif any(ch.isspace() for ch in username):
            errors["username"] = "Username cannot contain spaces."
        elif self._user_repo.find_by_username(username):
            errors["username"] = "Username is already taken."

        if not password:
            errors["password"] = "Password is required."
        else:
            pw_errors = []
            if len(password) < PASSWORD_MIN_LENGTH:
                pw_errors.append(
                    f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
                )
            if not any(c.isupper() for c in password):
                pw_errors.append(
                    "Password must contain at least one uppercase letter."
                )
            if not any(c.islower() for c in password):
                pw_errors.append(
                    "Password must contain at least one lowercase letter."
                )
            if not any(c.isdigit() for c in password):
                pw_errors.append("Password must contain at least one number.")
            if not any(not c.isalnum() for c in password):
                pw_errors.append(
                    "Password must contain at least one symbol (e.g. !@#$%)."
                )
            if password.lower() in WEAK_PASSWORDS:
                pw_errors.append(
                    "This password is too common. Choose a stronger password."
                )
            if pw_errors:
                errors["password"] = " ".join(pw_errors)

        if confirm_password != password:
            errors["confirm"] = "Passwords do not match."

        return errors

    # ── Admin creation ─────────────────────────────────────────

    def create_admin(
        self, username: str, password: str, confirm_password: str,
    ) -> Tuple[bool, str, Dict[str, str]]:
        """Validate and create the first administrator account.

        Runs the same server-side validation as ``validate``, then
        reuses ``AuthService.create_user`` (bcrypt hashing + repository
        insert) with the Admin role — no separate insertion path — and
        records an audit entry for the account creation.

        Args:
            username: The desired admin username.
            password: The desired password.
            confirm_password: Password confirmation.

        Returns:
            Tuple of (success, message, field_errors).  Field errors
            are populated when validation fails; ``message`` carries
            general failures (e.g. missing Admin role).
        """
        errors = self.validate(username, password, confirm_password)
        if errors:
            return False, "", errors

        username = username.strip()

        role_id = self._user_repo.get_role_id(Role.ADMIN)
        if not role_id:
            return False, (
                "Admin role not found. Please ensure the database has been initialized."
            ), {}

        user_data = {
            "username": username,
            "password": password,
            "role_id": role_id,
            "status": UserStatus.ACTIVE,
            "full_name": username,
        }

        success, message, user_id = self._auth_service.create_user(user_data)
        if not success:
            if "already exists" in message.lower():
                return False, "", {"username": message}
            return False, message, {}

        if user_id:
            self._audit_service.log_create(
                user_id,
                "User",
                str(user_id),
                {"username": username, "role": Role.ADMIN},
            )
            logger.info(
                "First-run admin account created: %s (id=%s)",
                username, user_id,
            )

        return True, "Admin account created successfully.", {}
