"""Role-Based Access Control (RBAC) decorator.

Provides the ``@require_role`` decorator that can be applied to
controller methods to enforce that the current user has the required
role before the method is executed.

Usage::

    class PatientController:
        @require_role("Admin", "Receptionist")
        def delete_patient(self, patient_id: str) -> Tuple[bool, str]:
            ...
"""
from __future__ import annotations

import logging
from functools import wraps
from typing import (
    Any,
    Callable,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
)

from src.auth.exceptions import PermissionDeniedError

logger = logging.getLogger(__name__)

# Type for the decorated callable
F = TypeVar("F", bound=Callable[..., Any])


class RoleRequired:
    """Descriptor-style role requirement that stores allowed roles."""

    def __init__(self, *roles: str) -> None:
        """Initialise with the list of roles that are permitted.

        Args:
            *roles: One or more role names (e.g. ``"Admin"``, ``"Doctor"``).
        """
        self._allowed_roles: Tuple[str, ...] = roles

    @property
    def allowed_roles(self) -> Tuple[str, ...]:
        """Return the roles that are permitted by this requirement."""
        return self._allowed_roles

    def check(self, user_role: Optional[str]) -> None:
        """Check whether a user's role satisfies the requirement.

        Args:
            user_role: The current user's role name, or None if not logged in.

        Raises:
            PermissionDeniedError: If the user's role is not in the allowed set.
        """
        if user_role is None:
            raise PermissionDeniedError(required_role="|".join(self._allowed_roles))
        if user_role not in self._allowed_roles:
            logger.warning(
                "Access denied: role '%s' not in %s",
                user_role,
                self._allowed_roles,
            )
            raise PermissionDeniedError(required_role="|".join(self._allowed_roles))


def require_role(*roles: str) -> Callable[[F], F]:
    """Decorator factory that restricts access by user role.

    The decorated method **must** be a bound method of a class that
    provides the current user's role through **one** of these
    mechanisms (checked in order):

    1. A ``_current_role`` property on the instance (preferred).
    2. An ``_auth_service`` attribute with a ``current_role`` property.

    Usage::

        class SomeController:
            @property
            def _current_role(self) -> Optional[str]:
                return self._auth_service.current_role

            @require_role("Admin")
            def sensitive_operation(self) -> str:
                return "Done"

    .. warning::
        The decorator does **not** accept role information from
        positional arguments (e.g. a user dict) to prevent
        role-injection attacks.

    Args:
        *roles: One or more role names permitted to call the decorated method.

    Returns:
        The decorated function with access control applied.
    """

    requirement = RoleRequired(*roles)

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # Determine the current user's role from the instance
            role: Optional[str] = None

            # 1. Check for _current_role property (preferred pattern)
            if hasattr(self, "_current_role"):
                role = getattr(self, "_current_role")
            # 2. Fallback to _auth_service.current_role
            elif hasattr(self, "_auth_service"):
                svc = getattr(self, "_auth_service")
                if hasattr(svc, "current_role"):
                    role = getattr(svc, "current_role")

            # NOTE: We intentionally do NOT accept a role from positional
            # arguments (e.g. a user dict) because that would allow a caller
            # to bypass role checks by injecting a fake user object.

            requirement.check(role)
            return func(self, *args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
