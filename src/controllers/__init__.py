"""Controllers package for Hospital Management System."""
from src.controllers.auth_controller import AuthController
from src.controllers.patient_controller import PatientController
from src.controllers.doctor_controller import DoctorController
from src.controllers.appointment_controller import AppointmentController
from src.controllers.report_controller import ReportController
from src.controllers.clinical_controller import ClinicalController

__all__ = [
    "AuthController",
    "PatientController",
    "DoctorController",
    "AppointmentController",
    "ReportController",
    "ClinicalController",
]
