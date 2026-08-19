"""Configuration package for Hospital Management System.

Re-exports configuration classes from ``settings`` and domain constants
from ``src.constants`` so that existing code can continue importing from
``src.config`` without changes during the migration.
"""
from __future__ import annotations

from src.config.settings import (
    DatabaseConfig,
    AppConfig,
    db_config,
    app_config,
)

# Domain constants – re-exported for backward compatibility.
# New code should import directly from ``src.constants`` instead.
from src.constants import (  # noqa: F401  – re-exported for compat
    Role,
    AppointmentStatus,
    UserStatus,
    DoctorStatus,
    Gender,
    MedicalStatus,
    VisitStatus,
    BloodGroup,
    ReportType,
    AuditAction,
    LogAction,
    LogLevel,
)

__all__ = [
    "DatabaseConfig",
    "AppConfig",
    # Backward-compatible re-exports
    "Role",
    "AppointmentStatus",
    "UserStatus",
    "DoctorStatus",
    "Gender",
    "MedicalStatus",
    "VisitStatus",
    "LogAction",
    "BloodGroup",
    "ReportType",
    "AuditAction",
    "LogLevel",
    "db_config",
    "app_config",
]
