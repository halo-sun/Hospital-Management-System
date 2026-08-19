"""Custom exception classes for the authentication subsystem.

These allow the controller layer (and ultimately the GUI) to catch
specific error types rather than parsing string messages.
"""
from __future__ import annotations


class AuthenticationError(Exception):
    """Base exception for all authentication-related errors."""

    def __init__(self, message: str = "Authentication failed.") -> None:
        """Initialise with a human-readable message.

        Args:
            message: Description of the error.
        """
        self.message = message
        super().__init__(self.message)


class AccountLockedError(AuthenticationError):
    """Raised when a user attempts to log into a locked account."""

    def __init__(self, remaining_minutes: int = 0) -> None:
        """Initialise with lockout duration info.

        Args:
            remaining_minutes: How many minutes until the lock expires.
        """
        self.remaining_minutes = remaining_minutes
        if remaining_minutes > 0:
            msg = f"Account is locked. Try again in {remaining_minutes} minute(s)."
        else:
            msg = "Account is locked due to too many failed attempts."
        super().__init__(msg)


class AccountInactiveError(AuthenticationError):
    """Raised when a user with inactive status tries to log in."""

    def __init__(self) -> None:
        """Initialise with a standard message."""
        super().__init__("Account is inactive. Contact administrator.")


class SessionExpiredError(AuthenticationError):
    """Raised when an operation requires a valid session but none exists."""

    def __init__(self) -> None:
        """Initialise with a standard message."""
        super().__init__("Session has expired. Please log in again.")


class PermissionDeniedError(AuthenticationError):
    """Raised when a user attempts an action they are not authorised for."""

    def __init__(self, required_role: str = "") -> None:
        """Initialise with the role that was required.

        Args:
            required_role: The role name that was required.
        """
        if required_role:
            msg = f"This action requires the '{required_role}' role."
        else:
            msg = "You do not have permission to perform this action."
        super().__init__(msg)
