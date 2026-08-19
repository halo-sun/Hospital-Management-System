"""Services package for Hospital Management System."""
from src.services.auth_service import AuthService
from src.services.user_service import UserService
from src.services.patient_service import PatientService
from src.services.doctor_service import DoctorService
from src.services.appointment_service import AppointmentService
from src.services.clinical_service import ClinicalService
from src.services.report_service import ReportService
from src.services.audit_service import AuditService

__all__ = [
    "AuthService",
    "UserService",
    "PatientService",
    "DoctorService",
    "AppointmentService",
    "ClinicalService",
    "ReportService",
    "AuditService",
]
