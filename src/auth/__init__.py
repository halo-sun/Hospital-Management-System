"""Authentication and authorisation package for the Hospital Management System.

Provides:

- ``AuthService`` / ``AuthController`` – login, logout, session management
- ``RememberTokenManager`` – persistent "Remember Me" across restarts
- ``require_role`` decorator – declarative role-based access control
- Custom exception classes for structured error handling
"""
from src.auth.exceptions import (
    AuthenticationError,
    AccountLockedError,
    AccountInactiveError,
    SessionExpiredError,
    PermissionDeniedError,
)
from src.auth.remember_token import RememberTokenManager
from src.auth.rbac import require_role, RoleRequired

__all__ = [
    "AuthenticationError",
    "AccountLockedError",
    "AccountInactiveError",
    "SessionExpiredError",
    "PermissionDeniedError",
    "RememberTokenManager",
    "require_role",
    "RoleRequired",
]
