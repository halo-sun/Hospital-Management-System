"""Application configuration settings.

Environment-specific configuration that changes per deployment.
Domain constants and enumerations live in ``src.constants.enums``.

When running inside a PyInstaller frozen bundle (``sys.frozen`` is
set), writable user data directories are placed under the
OS-appropriate per-user data path instead of beside the executable:

* **Windows:** ``%LOCALAPPDATA%\\HospitalScheduler\\``
* **Linux / macOS:** ``~/.local/share/hospital-scheduler/``

This avoids writing into ``Program Files`` (which requires admin
rights on Windows) or into a read-only bundle directory.
"""
from __future__ import annotations

import os
import sys
from typing import ClassVar, List, Optional

from dotenv import load_dotenv

load_dotenv()


# ── Frozen-mode detection ────────────────────────────────────
FROZEN: bool = getattr(sys, "frozen", False)

APP_DIR_NAME: str = "HospitalScheduler"


def _user_data_dir() -> str:
    """Return the OS-appropriate per-user data directory.

    On Windows this is ``%LOCALAPPDATA%\\HospitalScheduler\\``,
    on Linux/macOS it follows the XDG Base Directory spec at
    ``~/.local/share/hospital-scheduler/``.
    """
    if sys.platform == "win32":
        base = os.getenv("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
        return os.path.join(base, APP_DIR_NAME)
    # XDG_DATA_HOME defaults to ~/.local/share
    base = os.getenv("XDG_DATA_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "share"
    )
    return os.path.join(base, "hospital-scheduler")


class DatabaseConfig:
    """Database connection and pool configuration."""

    HOST: ClassVar[str] = os.getenv("DB_HOST", "localhost")
    PORT: ClassVar[int] = int(os.getenv("DB_PORT", "3306"))
    USER: ClassVar[str] = os.getenv("DB_USER", "root")
    PASSWORD: ClassVar[str] = os.getenv("DB_PASSWORD", "")
    # Optional elevated credentials used only for schema initialisation
    # (CREATE DATABASE/TABLE).  When set, the runtime connection pool
    # can use a least-privilege account (e.g. ``hms_app``) while the
    # one-time DDL runs as an admin account.
    ADMIN_USER: ClassVar[Optional[str]] = os.getenv("DB_ADMIN_USER") or None
    ADMIN_PASSWORD: ClassVar[Optional[str]] = os.getenv("DB_ADMIN_PASSWORD") or None
    DATABASE: ClassVar[str] = os.getenv("DB_NAME", "hospital_db")
    POOL_SIZE: ClassVar[int] = int(os.getenv("DB_POOL_SIZE", "10"))
    POOL_NAME: ClassVar[str] = "hospital_pool"
    CHARSET: ClassVar[str] = "utf8mb4"
    COLLATION: ClassVar[str] = "utf8mb4_unicode_ci"
    AUTOCOMMIT: ClassVar[bool] = False
    CONNECTION_TIMEOUT: ClassVar[int] = 10

    def get_connection_config(self, include_db: bool = True, admin: bool = False) -> dict:
        """Return database connection parameters as a dictionary.

        Args:
            include_db: Whether to include the database name in the result.
            admin: Use the elevated ``DB_ADMIN_USER``/``DB_ADMIN_PASSWORD``
                credentials (for schema DDL).  Falls back to the app user
                when no admin credentials are configured.

        Returns:
            Dictionary of keyword arguments suitable for ``mysql.connector.connect``.
        """
        if admin and self.ADMIN_USER:
            user = self.ADMIN_USER
            password = self.ADMIN_PASSWORD or ""
        else:
            user = self.USER
            password = self.PASSWORD

        config = {
            "host": self.HOST,
            "port": self.PORT,
            "user": user,
            "password": password,
            "pool_size": self.POOL_SIZE,
            "pool_name": self.POOL_NAME,
            "charset": self.CHARSET,
            "collation": self.COLLATION,
            "autocommit": self.AUTOCOMMIT,
            "connection_timeout": self.CONNECTION_TIMEOUT,
            "raise_on_warnings": True,
        }
        if include_db:
            config["database"] = self.DATABASE
        return config

    @property
    def host(self) -> str:
        """Database host address."""
        return self.HOST

    @property
    def port(self) -> int:
        """Database port number."""
        return self.PORT

    @property
    def user(self) -> str:
        """Database user name."""
        return self.USER

    @property
    def password(self) -> str:
        """Database user password."""
        return self.PASSWORD

    @property
    def database(self) -> str:
        """Database name."""
        return self.DATABASE

    @property
    def pool_name(self) -> str:
        """Connection pool identifier."""
        return self.POOL_NAME

    @property
    def pool_size(self) -> int:
        """Maximum connections in the pool."""
        return self.POOL_SIZE


class AppConfig:
    """Application-wide configuration values not related to deployment.

    .. note::
        Visual theme colours have been removed from this class.
        Use ``src.gui.theme.Theme`` as the single source of truth
        for all UI colour and font constants.
    """

    # ── Identity ───────────────────────────────────────────────
    NAME: ClassVar[str] = "Hospital Management System"
    VERSION: ClassVar[str] = "1.0.3"
    PUBLISHER: ClassVar[str] = "Sidd & Contributors"
    APP_DESCRIPTION: ClassVar[str] = (
        "A desktop hospital management system for scheduling, "
        "patient records, clinical workflows, and analytics."
    )
    COPYRIGHT: ClassVar[str] = "2026 Sidd & Contributors"

    # ── Behaviour ──────────────────────────────────────────────
    DEBUG: ClassVar[bool] = os.getenv("DEBUG", "False").lower() == "true"
    SESSION_TIMEOUT_MINUTES: ClassVar[int] = int(os.getenv("SESSION_TIMEOUT", "30"))
    MAX_LOGIN_ATTEMPTS: ClassVar[int] = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    LOCKOUT_DURATION_MINUTES: ClassVar[int] = int(os.getenv("LOCKOUT_DURATION", "15"))
    BCRYPT_ROUNDS: ClassVar[int] = 12
    PASSWORD_MIN_LENGTH: ClassVar[int] = 8
    DEFAULT_SLOT_DURATION: ClassVar[int] = 15       # minutes
    MAX_APPOINTMENTS_PER_DAY: ClassVar[int] = 20
    MAX_BOOKING_DAYS_AHEAD: ClassVar[int] = int(os.getenv("MAX_BOOKING_DAYS", "90"))

    # ── Window geometry ───────────────────────────────────────
    WINDOW_WIDTH: ClassVar[int] = 1400
    WINDOW_HEIGHT: ClassVar[int] = 900
    MIN_WINDOW_WIDTH: ClassVar[int] = 1200
    MIN_WINDOW_HEIGHT: ClassVar[int] = 700

    # ── Pagination ────────────────────────────────────────────
    DEFAULT_PAGE_SIZE: ClassVar[int] = 20
    MAX_PAGE_SIZE: ClassVar[int] = 100

    # ── Theme mode ────────────────────────────────────────────
    THEME: ClassVar[str] = "clam"

    # ── Report export formats ─────────────────────────────────
    REPORT_FORMATS: ClassVar[List[str]] = ["pdf", "excel"]

    # ── Directories ───────────────────────────────────────────
    # When running as a PyInstaller frozen bundle, writable user data
    # lives under the OS-appropriate per-user directory (e.g.
    # ``%LOCALAPPDATA%\\HospitalScheduler`` on Windows).  When
    # running from source, paths stay relative to the project root.
    _SOURCE_BASE: ClassVar[str] = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    _USER_DATA: ClassVar[str] = _user_data_dir() if FROZEN else _SOURCE_BASE

    BASE_DIR: ClassVar[str] = _USER_DATA
    REPORTS_DIR: ClassVar[str] = os.path.join(_USER_DATA, "reports")
    EXPORTS_DIR: ClassVar[str] = os.path.join(_USER_DATA, "exports")
    LOGS_DIR: ClassVar[str] = os.path.join(_USER_DATA, "logs")
    ASSETS_DIR: ClassVar[str] = os.path.join(_USER_DATA, "assets")

    # ── Property accessors (instance-style) ────────────────────

    @property
    def name(self) -> str:
        """Application display name."""
        return self.NAME

    @property
    def version(self) -> str:
        """Application version string."""
        return self.VERSION

    @property
    def publisher(self) -> str:
        """Publisher / author name."""
        return self.PUBLISHER

    @property
    def description(self) -> str:
        """Short application description."""
        return self.APP_DESCRIPTION

    @property
    def copyright(self) -> str:
        """Copyright notice string."""
        return self.COPYRIGHT

    @property
    def window_width(self) -> int:
        """Default main window width in pixels."""
        return self.WINDOW_WIDTH

    @property
    def window_height(self) -> int:
        """Default main window height in pixels."""
        return self.WINDOW_HEIGHT

    @property
    def min_window_width(self) -> int:
        """Minimum allowed main window width."""
        return self.MIN_WINDOW_WIDTH

    @property
    def min_window_height(self) -> int:
        """Minimum allowed main window height."""
        return self.MIN_WINDOW_HEIGHT

    @property
    def session_timeout_minutes(self) -> int:
        """Minutes of inactivity before auto-logout."""
        return self.SESSION_TIMEOUT_MINUTES

    @property
    def bcrypt_rounds(self) -> int:
        """Number of bcrypt hashing rounds for password storage."""
        return self.BCRYPT_ROUNDS

    @property
    def max_login_attempts(self) -> int:
        """Failed login attempts before account lockout."""
        return self.MAX_LOGIN_ATTEMPTS

    @property
    def lockout_duration_minutes(self) -> int:
        """How long an account stays locked in minutes."""
        return self.LOCKOUT_DURATION_MINUTES

    @property
    def password_min_length(self) -> int:
        """Minimum characters required for user passwords."""
        return self.PASSWORD_MIN_LENGTH

    @property
    def default_slot_duration(self) -> int:
        """Default appointment slot length in minutes."""
        return self.DEFAULT_SLOT_DURATION

    @property
    def max_appointments_per_day(self) -> int:
        """Maximum appointments a doctor can have in one day."""
        return self.MAX_APPOINTMENTS_PER_DAY

    @classmethod
    def ensure_directories(cls) -> None:
        """Create all required application directories if they don't exist."""
        for directory in (cls.REPORTS_DIR, cls.EXPORTS_DIR, cls.LOGS_DIR, cls.ASSETS_DIR):
            os.makedirs(directory, exist_ok=True)


# ── Singleton instances ────────────────────────────────────────
db_config = DatabaseConfig()
app_config = AppConfig()

# Ensure required directories exist on import
app_config.ensure_directories()
