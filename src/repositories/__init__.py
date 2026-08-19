"""Repositories package for Hospital Management System."""
from src.repositories.base_repository import BaseRepository
from src.repositories.user_repository import UserRepository
from src.repositories.patient_repository import PatientRepository
from src.repositories.department_repository import DepartmentRepository
from src.repositories.doctor_repository import (
    DoctorRepository,
    DoctorScheduleRepository,
    DoctorLeaveRepository,
)
from src.repositories.appointment_repository import AppointmentRepository
from src.repositories.clinical_repository import (
    VisitRecordRepository,
    PrescriptionRepository,
    TestReportRepository,
)
from src.repositories.audit_repository import (
    AuditRepository,
    HospitalHolidayRepository,
)

__all__ = [
    "BaseRepository",
    "UserRepository",
    "PatientRepository",
    "DepartmentRepository",
    "DoctorRepository",
    "DoctorScheduleRepository",
    "DoctorLeaveRepository",
    "AppointmentRepository",
    "VisitRecordRepository",
    "PrescriptionRepository",
    "TestReportRepository",
    "AuditRepository",
    "HospitalHolidayRepository",
]
