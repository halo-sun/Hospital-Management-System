"""Domain-level enumerations and constant definitions for the Hospital Management System.

This module contains all constant/enum classes that define the domain
vocabulary of the system. These are separated from `src.config.settings`
which holds environment-specific configuration.

All enum classes intentionally use class-based constants rather than
Python's `enum.Enum` to keep usage simple (string comparison) and
consistent with database string columns.
"""
from __future__ import annotations

from typing import ClassVar, List


class Role:
    """User role constants defining permitted access levels."""
    ADMIN: ClassVar[str] = "Admin"
    DOCTOR: ClassVar[str] = "Doctor"
    RECEPTIONIST: ClassVar[str] = "Receptionist"


class UserStatus:
    """User account status constants."""
    ACTIVE: ClassVar[str] = "Active"
    INACTIVE: ClassVar[str] = "Inactive"


class DoctorStatus:
    """Doctor employment status constants."""
    ACTIVE: ClassVar[str] = "Active"
    INACTIVE: ClassVar[str] = "Inactive"
    ON_LEAVE: ClassVar[str] = "On Leave"


class AppointmentStatus:
    """Appointment lifecycle status constants."""
    BOOKED: ClassVar[str] = "Booked"
    COMPLETED: ClassVar[str] = "Completed"
    CANCELLED: ClassVar[str] = "Cancelled"
    NO_SHOW: ClassVar[str] = "No Show"


class Gender:
    """Patient gender constants."""
    MALE: ClassVar[str] = "Male"
    FEMALE: ClassVar[str] = "Female"
    OTHER: ClassVar[str] = "Other"
    ALL: ClassVar[List[str]] = [MALE, FEMALE, OTHER]


class MedicalStatus:
    """Medical condition status constants."""
    ACTIVE: ClassVar[str] = "Active"
    RESOLVED: ClassVar[str] = "Resolved"
    CHRONIC: ClassVar[str] = "Chronic"


class VisitStatus:
    """Visit record status constants."""
    COMPLETED: ClassVar[str] = "Completed"
    IN_PROGRESS: ClassVar[str] = "In Progress"
    CANCELLED: ClassVar[str] = "Cancelled"


class BloodGroup:
    """Blood group type constants."""
    A_POS: ClassVar[str] = "A+"
    A_NEG: ClassVar[str] = "A-"
    B_POS: ClassVar[str] = "B+"
    B_NEG: ClassVar[str] = "B-"
    AB_POS: ClassVar[str] = "AB+"
    AB_NEG: ClassVar[str] = "AB-"
    O_POS: ClassVar[str] = "O+"
    O_NEG: ClassVar[str] = "O-"
    ALL: ClassVar[List[str]] = [A_POS, A_NEG, B_POS, B_NEG, AB_POS, AB_NEG, O_POS, O_NEG]


class ReportType:
    """Test report category constants for clinical documents.

    These are the report categories a doctor can attach to a visit
    record (stored in ``test_reports.file_type``).
    """
    BLOOD: ClassVar[str] = "Blood"
    X_RAY: ClassVar[str] = "X-Ray"
    MRI: ClassVar[str] = "MRI"
    CT: ClassVar[str] = "CT"
    ECG: ClassVar[str] = "ECG"
    LAB: ClassVar[str] = "Lab"
    ALL: ClassVar[List[str]] = [BLOOD, X_RAY, MRI, CT, ECG, LAB]


class AuditAction:
    """Audit log action type constants.

    These are used when recording user activities in the audit_logs table.
    """
    LOGIN: ClassVar[str] = "Login"
    LOGOUT: ClassVar[str] = "Logout"
    LOGIN_FAILED: ClassVar[str] = "Login Failed"
    CREATE: ClassVar[str] = "Create"
    UPDATE: ClassVar[str] = "Update"
    DELETE: ClassVar[str] = "Delete"
    VIEW: ClassVar[str] = "View"
    EXPORT: ClassVar[str] = "Export"
    APPOINTMENT_BOOK: ClassVar[str] = "Appointment Booked"
    APPOINTMENT_CANCEL: ClassVar[str] = "Appointment Cancelled"
    APPOINTMENT_RESCHEDULE: ClassVar[str] = "Appointment Rescheduled"
    PATIENT_REGISTER: ClassVar[str] = "Patient Registered"
    PATIENT_UPDATE: ClassVar[str] = "Patient Updated"
    DOCTOR_CREATE: ClassVar[str] = "Doctor Created"
    DOCTOR_UPDATE: ClassVar[str] = "Doctor Updated"
    PRESCRIPTION_CREATE: ClassVar[str] = "Prescription Created"
    REPORT_UPLOAD: ClassVar[str] = "Report Uploaded"
    DOCUMENT_UPLOAD: ClassVar[str] = "Document Uploaded"
    PASSWORD_RESET: ClassVar[str] = "Password Reset"
    PASSWORD_CHANGE: ClassVar[str] = "Password Changed"


class LogLevel:
    """Logging severity level constants matching Python's logging module."""
    DEBUG: ClassVar[str] = "DEBUG"
    INFO: ClassVar[str] = "INFO"
    WARNING: ClassVar[str] = "WARNING"
    ERROR: ClassVar[str] = "ERROR"
    CRITICAL: ClassVar[str] = "CRITICAL"
