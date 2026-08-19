"""Constants package for Hospital Management System.

Contains all domain-level enumerations and constant definitions,
separated from environment-specific configuration settings.

Usage:
    from src.constants import Role, AppointmentStatus, AuditAction
"""
from src.constants.enums import (
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
    LogLevel,
)

# Backward-compatible alias
LogAction = AuditAction

__all__ = [
    "Role",
    "AppointmentStatus",
    "UserStatus",
    "DoctorStatus",
    "Gender",
    "MedicalStatus",
    "VisitStatus",
    "BloodGroup",
    "ReportType",
    "AuditAction",
    "LogAction",
    "LogLevel",
]
