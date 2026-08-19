"""Demo data seeder for the Hospital Management System.

This module populates a realistic dataset so every module — analytics
dashboard, booking validation, clinical records, documents, audit
viewer, settings — has real data to demonstrate during a presentation.

**It is a manual, developer-run tool and is NEVER invoked at app
startup.**  ``src/app.py`` / ``src/database/init_db.py`` do not import
it.  Run it explicitly when you want (re)seeded data::

    python3 -m src.database.seed_demo_data            # idempotent add
    python3 -m src.database.seed_demo_data --reset    # wipe + reseed clean

What gets seeded
----------------
* 11 departments (Cardiology, Orthopaedics, Neurology, ENT, Pediatrics,
  General Medicine, Orthopedics, Gynecology, Dermatology, Ophthalmology,
  Psychiatry)
* 15 doctors across all departments with realistic Indian names,
  varied working hours (9-5 / 10-6), per-day lunch breaks,
  consultation fees and per-day appointment caps; one doctor is
  currently On Leave; three doctors have upcoming leave dates
* 45 patients (varied age/gender, blood groups, allergies, chronic
  conditions in ``medical_history``, a few deliberately empty
  optional fields)
* ~190 appointments across the last 60 days + next 14 days:
  ~68% Completed, ~17% Cancelled, ~4% No Show, ~4% rescheduled
  pairs (with ``rescheduled_from_id`` links), ~10% Booked (future),
  weighted toward weekday mornings / early afternoons and unevenly
  distributed across doctors so the workload charts show real shape
* Visit records for every completed appointment (~134) with
  prescriptions on roughly half
* Test reports (Blood / X-Ray / Lab) on a subset of visits and
  patient documents for a subset of patients (real files are tiny
  placeholders; only metadata matters to the UI)
* 4 upcoming hospital holidays added through the Settings service
* Demo user accounts: admin / receptionist / one per doctor
* Backfilled audit-log entries covering logins and the seeded actions

Design rules
------------
* Reference data (departments, doctors, patients, holidays, users)
  goes through the **real service layer** (DepartmentService,
  DoctorService, PatientService, SettingsService, UserService).
* Historical appointments cannot go through
  ``AppointmentService.book_appointment`` — the scheduling engine
  rejects past dates by design.  They are inserted directly but each
  slot is validated with the **same engine rules** the app enforces
  (holiday, leave, day-of-week, working hours, lunch break, overlap,
  daily cap) minus the past-date rule; any slot that would fail those
  checks is never written.
* Future (Booked) appointments go through the real
  ``AppointmentService.book_appointment`` path with full validation.
* Clinical records / documents go through ClinicalService /
  DocumentService.
* Audit entries are backfilled through AuditService.log() with
  timestamps aligned to the underlying records.

After seeding, the script re-runs the engine's rule checks against
every appointment in the database and reports any violation, so the
dataset provably matches what the app itself would allow.
"""
from __future__ import annotations

import argparse
import logging
import os
import random
import sys
import tempfile
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.database.connection import DatabaseConnection
from src.config import app_config
from src.constants import (
    Role,
    AppointmentStatus,
    AuditAction,
    DoctorStatus,
    ReportType,
    BloodGroup,
)
from src.services.department_service import DepartmentService
from src.services.doctor_service import DoctorService
from src.services.user_service import UserService
from src.services.patient_service import PatientService
from src.services.settings_service import SettingsService
from src.services.appointment_service import AppointmentService
from src.services.clinical_service import ClinicalService
from src.services.document_service import DocumentService
from src.services.audit_service import AuditService
from src.services.scheduling_engine import SchedulingEngine
from src.repositories.doctor_repository import (
    DoctorRepository,
    DoctorScheduleRepository,
)
from src.repositories.patient_repository import PatientRepository
from src.repositories.appointment_repository import AppointmentRepository
from src.repositories.audit_repository import HospitalHolidayRepository

logger = logging.getLogger("seed_demo_data")


def _reset_table_statement(table_name: str, reset_identity: bool = False) -> str:
    """Build reset DDL only for the seeder's fixed internal table list."""
    if not table_name.isidentifier():
        raise ValueError("Invalid internal seed table name.")
    quoted = "`" + table_name + "`"
    return "ALTER TABLE " + quoted + " AUTO_INCREMENT = 1" if reset_identity else "TRUNCATE TABLE " + quoted

# ── Demo credentials (explicit environment input; never committed) ─────────
ADMIN_USERNAME = "admin"
RECEPTION_USERNAME = "reception"
ADMIN_PASSWORD = os.getenv("HMS_SEED_ADMIN_PASSWORD", "")
RECEPTION_PASSWORD = os.getenv("HMS_SEED_RECEPTION_PASSWORD", "")
DOCTOR_PASSWORD = os.getenv("HMS_SEED_DOCTOR_PASSWORD", "")

# ── Reference data ─────────────────────────────────────────────

DEPARTMENTS: List[Tuple[str, str]] = [
    ("Cardiology", "Diagnosis and treatment of heart and cardiovascular conditions."),
    ("Orthopaedics", "Bone, joint, spine and musculoskeletal care."),
    ("Neurology", "Disorders of the brain, spine and nervous system."),
    ("ENT", "Ear, nose and throat care."),
    ("Pediatrics", "Health care for infants, children and adolescents."),
    ("General Medicine", "Internal medicine, primary and preventive care."),
    ("Orthopedics", "Trauma, fracture and emergency musculoskeletal care."),
    ("Gynecology", "Obstetrics, reproductive health and women's healthcare."),
    ("Dermatology", "Skin, hair and nail conditions including cosmetic dermatology."),
    ("Ophthalmology", "Eye care including diagnosis, surgery and vision correction."),
    ("Psychiatry", "Mental health, behavioural disorders and psychotherapy."),
]

# day_of_week uses the SQL convention stored in doctor_schedules:
# 0=Sunday … 6=Saturday (the scheduling engine converts Python's
# Monday=0 weekday with (weekday + 1) % 7).
MON, TUE, WED, THU, FRI, SAT, SUN = 1, 2, 3, 4, 5, 6, 0

DOCTORS: List[Dict[str, Any]] = [
    dict(name="Dr. Rajesh Sharma", dept="Cardiology", spec="Interventional Cardiology",
         phone="9820012345", email="rajesh.sharma@hms.local", qual="MD, DM (Cardiology)",
         lic="MH-12345", exp=18, fee=800, max_day=16, hours=("09:00", "17:00"),
         lunch=("13:00", "14:00"), status="Active", saturday=True),
    dict(name="Dr. Anita Desai", dept="Cardiology", spec="Non-invasive Cardiology",
         phone="9821012345", email="anita.desai@hms.local", qual="MD, DM (Cardiology)",
         lic="MH-12346", exp=12, fee=700, max_day=14, hours=("10:00", "18:00"),
         lunch=("14:00", "15:00"), status="On Leave", saturday=False),
    dict(name="Dr. Vikram Mehta", dept="Orthopaedics", spec="Joint Replacement Surgery",
         phone="9822012345", email="vikram.mehta@hms.local", qual="MS (Orthopaedics)",
         lic="MH-12347", exp=15, fee=600, max_day=15, hours=("09:00", "17:00"),
         lunch=("12:30", "13:30"), status="Active", saturday=False),
    dict(name="Dr. Priya Nair", dept="Orthopaedics", spec="Sports Medicine",
         phone="9823012345", email="priya.nair@hms.local", qual="MS (Orthopaedics)",
         lic="MH-12348", exp=9, fee=650, max_day=12, hours=("10:00", "18:00"),
         lunch=("13:30", "14:30"), status="Active", saturday=False),
    dict(name="Dr. Sunil Kulkarni", dept="Neurology", spec="Stroke & Epilepsy Care",
         phone="9824012345", email="sunil.kulkarni@hms.local", qual="MD, DM (Neurology)",
         lic="MH-12349", exp=20, fee=900, max_day=12, hours=("09:00", "17:00"),
         lunch=("13:00", "14:00"), status="Active", saturday=False),
    dict(name="Dr. Meera Iyer", dept="ENT", spec="Otology & Hearing",
         phone="9825012345", email="meera.iyer@hms.local", qual="MS (ENT)",
         lic="MH-12350", exp=8, fee=500, max_day=14, hours=("10:00", "16:00"),
         lunch=("13:00", "13:30"), status="Active", saturday=False),
    dict(name="Dr. Arjun Reddy", dept="Pediatrics", spec="Neonatology",
         phone="9826012345", email="arjun.reddy@hms.local", qual="MD (Pediatrics)",
         lic="MH-12351", exp=10, fee=550, max_day=18, hours=("09:00", "15:00"),
         lunch=("12:00", "12:45"), status="Active", saturday=False),
    dict(name="Dr. Kavita Joshi", dept="Pediatrics", spec="Adolescent Medicine",
         phone="9827012345", email="kavita.joshi@hms.local", qual="MD (Pediatrics)",
         lic="MH-12352", exp=7, fee=500, max_day=16, hours=("09:30", "17:30"),
         lunch=("13:00", "14:00"), status="Active", saturday=False),
    dict(name="Dr. Sandeep Gupta", dept="General Medicine", spec="Internal Medicine",
         phone="9828012345", email="sandeep.gupta@hms.local", qual="MD (General Medicine)",
         lic="MH-12353", exp=22, fee=400, max_day=20, hours=("09:00", "17:00"),
         lunch=("13:00", "14:00"), status="Active", saturday=True),
    dict(name="Dr. Farhan Ali", dept="General Medicine", spec="Diabetes & Endocrinology",
         phone="9829012345", email="farhan.ali@hms.local", qual="MD (General Medicine)",
         lic="MH-12354", exp=11, fee=450, max_day=18, hours=("10:00", "18:00"),
         lunch=("14:00", "15:00"), status="Active", saturday=False),
    # ── New doctors for previously orphan departments ──
    dict(name="Dr. Rohan Kapoor", dept="Orthopedics", spec="Trauma & Fracture Care",
         phone="9830012345", email="rohan.kapoor@hms.local", qual="MS (Orthopaedics)",
         lic="MH-12355", exp=13, fee=550, max_day=14, hours=("09:00", "17:00"),
         lunch=("13:00", "14:00"), status="Active", saturday=False),
    dict(name="Dr. Nandini Bose", dept="Gynecology", spec="Obstetrics & High-Risk Pregnancy",
         phone="9831012345", email="nandini.bose@hms.local", qual="MS (OBG)",
         lic="MH-12356", exp=16, fee=600, max_day=14, hours=("09:30", "17:30"),
         lunch=("13:00", "14:00"), status="Active", saturday=False),
    dict(name="Dr. Imran Sheikh", dept="Dermatology", spec="Clinical & Cosmetic Dermatology",
         phone="9832012345", email="imran.sheikh@hms.local", qual="MD (Dermatology)",
         lic="MH-12357", exp=9, fee=500, max_day=16, hours=("10:00", "18:00"),
         lunch=("13:30", "14:30"), status="Active", saturday=False),
    dict(name="Dr. Lakshmi Menon", dept="Ophthalmology", spec="Cataract & Refractive Surgery",
         phone="9833012345", email="lakshmi.menon@hms.local", qual="MS (Ophthalmology)",
         lic="MH-12358", exp=14, fee=550, max_day=12, hours=("09:00", "16:00"),
         lunch=("12:30", "13:30"), status="Active", saturday=False),
    dict(name="Dr. Dev Mishra", dept="Psychiatry", spec="Adult Psychiatry & Psychotherapy",
         phone="9834012345", email="dev.mishra@hms.local", qual="MD (Psychiatry)",
         lic="MH-12359", exp=10, fee=600, max_day=10, hours=("10:00", "18:00"),
         lunch=("14:00", "15:00"), status="Active", saturday=False),
]

# Upcoming leave: (doctor name, start-offset days, end-offset days, reason)
DOCTOR_LEAVES: List[Tuple[str, int, int, str]] = [
    ("Dr. Priya Nair", 3, 5, "Annual leave"),
    ("Dr. Kavita Joshi", 7, 8, "Personal leave"),
    ("Dr. Farhan Ali", 10, 10, "Medical leave"),
]

# Seeding workload per doctor.  Rescheduled pairs create 2 rows each
# (original Cancelled + new Completed); the numbers below are rows.
WORKLOAD: Dict[str, Dict[str, int]] = {
    "Dr. Rajesh Sharma":   dict(completed=27, cancelled=5, no_show=2, rescheduled=2, booked=4),
    "Dr. Sandeep Gupta":   dict(completed=24, cancelled=5, no_show=2, rescheduled=2, booked=2),
    "Dr. Vikram Mehta":    dict(completed=16, cancelled=3, no_show=1, rescheduled=1, booked=4),
    "Dr. Sunil Kulkarni":  dict(completed=12, cancelled=3, no_show=1, rescheduled=1, booked=1),
    "Dr. Arjun Reddy":     dict(completed=12, cancelled=3, no_show=1, rescheduled=1, booked=1),
    "Dr. Priya Nair":      dict(completed=10, cancelled=2, no_show=1, rescheduled=1, booked=1),
    "Dr. Kavita Joshi":    dict(completed=10, cancelled=2, no_show=0, rescheduled=0, booked=3),
    "Dr. Farhan Ali":      dict(completed=8,  cancelled=2, no_show=0, rescheduled=0, booked=2),
    "Dr. Meera Iyer":      dict(completed=7,  cancelled=1, no_show=0, rescheduled=0, booked=2),
    # New doctors for previously orphan departments
    "Dr. Rohan Kapoor":    dict(completed=8,  cancelled=2, no_show=1, rescheduled=0, booked=2),
    "Dr. Nandini Bose":    dict(completed=10, cancelled=2, no_show=1, rescheduled=1, booked=2),
    "Dr. Imran Sheikh":    dict(completed=8,  cancelled=1, no_show=0, rescheduled=0, booked=3),
    "Dr. Lakshmi Menon":   dict(completed=7,  cancelled=1, no_show=0, rescheduled=0, booked=2),
    "Dr. Dev Mishra":      dict(completed=6,  cancelled=1, no_show=0, rescheduled=0, booked=1),
}

MALE_FIRST = ["Aarav", "Rohan", "Vivaan", "Arjun", "Aditya", "Karthik", "Rahul",
              "Amit", "Suresh", "Ramesh", "Manoj", "Deepak", "Nikhil", "Siddharth",
              "Harsha", "Venkat", "Imran", "Yusuf", "Sanjay", "Vijay", "Kunal",
              "Pranav", "Dev", "Naveen", "Ravi"]
FEMALE_FIRST = ["Aisha", "Priya", "Ananya", "Diya", "Kavya", "Sneha", "Meera",
                "Pooja", "Ritu", "Shreya", "Lakshmi", "Nandini", "Farah", "Zara",
                "Divya", "Rekha", "Anjali", "Neha", "Simran", "Tara", "Vidya",
                "Ishita", "Rani", "Sunita", "Geeta"]
LAST = ["Sharma", "Patel", "Reddy", "Iyer", "Nair", "Gupta", "Mehta", "Joshi",
        "Singh", "Kulkarni", "Desai", "Chowdhury", "Bhat", "Menon", "Rao",
        "Khan", "Verma", "Mishra", "Aggarwal", "Shetty", "Pillai", "Naidu",
        "Das", "Bose", "Kapoor"]

ALLERGIES = ["Penicillin", "Peanuts", "Dust mites", "Sulfa drugs", "Latex",
             "Shellfish", "Aspirin", "Pollen"]

CHRONIC_CONDITIONS = [
    ("Type 2 Diabetes Mellitus", "Chronic", "Managed with Metformin; HbA1c monitored quarterly."),
    ("Hypertension", "Chronic", "On Amlodipine 5 mg; regular BP monitoring advised."),
    ("Bronchial Asthma", "Chronic", "Uses Salbutamol inhaler as needed; avoid triggers."),
    ("Hypothyroidism", "Chronic", "On Thyroxine 50 mcg daily; TSH checked every 6 months."),
    ("Rheumatoid Arthritis", "Chronic", "Morning stiffness; on NSAIDs and physiotherapy."),
    ("Epilepsy", "Chronic", "Seizure-free on Levetiracetam; avoid missing doses."),
    ("Coronary Artery Disease", "Active", "Post-angioplasty follow-up; on statin and aspirin."),
    ("Chronic Kidney Disease (Stage 2)", "Active", "Monitor creatinine; low-salt diet advised."),
]

SYMPTOMS = [
    "Fever and body ache", "Chest pain with breathlessness", "Persistent headache",
    "Joint pain and morning stiffness", "Sore throat and congestion",
    "Recurrent cough and cold", "Fatigue and weakness", "Nausea and abdominal discomfort",
    "Palpitations and dizziness", "Ear pain with discharge",
    "Back pain radiating to legs", "Skin rash with itching",
    "Frequent urination and excessive thirst", "Dizziness on standing",
]

DIAGNOSES = [
    "Upper respiratory tract infection", "Hypertension - Stage 1",
    "Type 2 diabetes mellitus", "Acute gastroenteritis",
    "Osteoarthritis of the knee", "Migraine without aura", "Viral fever",
    "Otitis media", "Bronchial asthma - controlled", "Lumbar spondylosis",
    "Iron deficiency anaemia", "Allergic rhinitis", "Gastritis",
    "Urinary tract infection", "Sinusitis", "Tension-type headache",
]

MEDICINES = [
    ("Paracetamol 500mg", "500mg", "Thrice daily", "5 days", "Oral", "After food, if fever or pain."),
    ("Amoxicillin 250mg", "250mg", "Twice daily", "7 days", "Oral", "Complete the full course."),
    ("Amlodipine 5mg", "5mg", "Once daily", "30 days", "Oral", "Take at the same time each morning."),
    ("Metformin 500mg", "500mg", "Twice daily", "30 days", "Oral", "With meals to avoid gastric upset."),
    ("Omeprazole 20mg", "20mg", "Once daily", "14 days", "Oral", "Half an hour before breakfast."),
    ("Azithromycin 500mg", "500mg", "Once daily", "3 days", "Oral", "Take with food."),
    ("Cetirizine 10mg", "10mg", "Once daily", "7 days", "Oral", "At bedtime if drowsiness occurs."),
    ("Salbutamol Inhaler", "100mcg", "As needed", "15 days", "Inhalation", "Two puffs when breathless."),
    ("Atorvastatin 20mg", "20mg", "Once daily", "30 days", "Oral", "Take at night."),
    ("Ibuprofen 400mg", "400mg", "Thrice daily", "5 days", "Oral", "After meals; max 5 days."),
    ("Levetiracetam 500mg", "500mg", "Twice daily", "30 days", "Oral", "Do not skip doses."),
    ("Thyroxine 50mcg", "50mcg", "Once daily", "30 days", "Oral", "On an empty stomach, 30 min before breakfast."),
]

NOTES = [
    "Patient requested early morning slot.", "Follow-up after previous consultation.",
    "Referred by general physician.", "First visit - new patient.",
    "Companion accompanying the patient.", "",
]


# ── Time helpers (mirror the engine's parsing, plus timedelta) ─

def _as_time(value: Any) -> Optional[time]:
    """Coerce time / datetime / timedelta / str to ``datetime.time``.

    mysql-connector returns TIME columns as ``datetime.timedelta``;
    the scheduling engine's ``_to_time`` does not handle that, so the
    seeder has its own coercion (engine rules themselves are reused).
    """
    if value is None:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, timedelta):
        total = int(value.total_seconds())
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        return time(h, m, s)
    if isinstance(value, str):
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(value.strip(), fmt).time()
            except ValueError:
                continue
    return None


class DemoDataSeeder:
    """Seeds the demo dataset; one instance per run."""

    def __init__(self, reset: bool = False) -> None:
        self.reset = reset
        self.today = date.today()

        # Services / repos (real application paths)
        self.dept_svc = DepartmentService()
        self.doctor_svc = DoctorService()
        self.user_svc = UserService()
        self.patient_svc = PatientService()
        self.settings_svc = SettingsService()
        self.appt_svc = AppointmentService()
        self.clinical_svc = ClinicalService()
        self.doc_svc = DocumentService()
        self.audit_svc = AuditService()
        self.engine = SchedulingEngine()

        self.doctor_repo = DoctorRepository()
        self.schedule_repo = DoctorScheduleRepository()
        self.patient_repo = PatientRepository()
        self.appt_repo = AppointmentRepository()
        self.holiday_repo = HospitalHolidayRepository()

        # State
        self.admin_id: Optional[int] = None
        self.reception_id: Optional[int] = None
        self.dept_ids: Dict[str, int] = {}
        self.doctor_ids: Dict[str, int] = {}
        self.patient_ids: List[str] = []
        self.appointment_ids: List[int] = []
        self.completed_appt_ids: List[int] = []
        self.visit_ids: List[int] = []
        # (doctor_id, appt_date) -> rows inserted so far (for overlap/cap)
        self._by_doc_date: Dict[Tuple[int, date], List[Dict[str, Any]]] = {}
        self._temp_dir: Optional[str] = None

    # ── Run ────────────────────────────────────────────────────

    def run(self) -> None:
        logger.info("Demo data seeder starting (reset=%s)", self.reset)
        if self.reset:
            self._reset_database()
        self._seed_roles()
        self._seed_departments()
        self._seed_users_and_doctors()
        self._seed_schedules()
        self._seed_leaves()
        self._seed_holidays()
        self._seed_patients()
        self._seed_medical_history()
        self._seed_appointments()
        self._seed_visits_and_prescriptions()
        self._seed_documents()
        self._backfill_audit()
        violations = self._verify_all_appointments()
        self._print_summary(violations)

    # ── Reset ──────────────────────────────────────────────────

    def _reset_database(self) -> None:
        """Wipe every table and reset AUTO_INCREMENT counters."""
        tables = [
            "prescriptions", "test_reports", "visit_records", "patient_documents",
            "appointments", "medical_history", "patients", "doctor_leave",
            "doctor_schedules", "doctors", "audit_logs", "users",
            "hospital_holidays", "departments", "app_settings", "roles",
        ]
        with DatabaseConnection.transaction() as conn:
            cur = conn.cursor()
            cur.execute("SET FOREIGN_KEY_CHECKS = 0")
            for t in tables:
                cur.execute(_reset_table_statement(t))
            for t in tables:
                if t not in ("patients", "app_settings"):
                    cur.execute(_reset_table_statement(t, reset_identity=True))
            cur.execute("SET FOREIGN_KEY_CHECKS = 1")
        logger.info("Database wiped (all data tables truncated).")

    def _seed_roles(self) -> None:
        """Ensure the three roles exist.

        Insert-if-missing rather than ``INSERT IGNORE``: the app's pool
        runs with ``raise_on_warnings=True``, and a duplicate-key
        ``INSERT IGNORE`` surfaces as warning 1062 which the connector
        then promotes to an exception.
        """
        for name, desc in (
            ("Admin", "System administrator with full access."),
            ("Doctor", "Medical practitioner."),
            ("Receptionist", "Front-desk patient and appointment management."),
        ):
            existing = DatabaseConnection.execute_query(
                "SELECT role_id FROM roles WHERE role_name = %s",
                (name,),
                fetch_one=True,
            )
            if existing:
                continue
            DatabaseConnection.execute_query(
                "INSERT INTO roles (role_name, description) VALUES (%s, %s)",
                (name, desc),
                fetch=False,
            )

    # ── Reference entities ─────────────────────────────────────

    def _seed_departments(self) -> None:
        for name, desc in DEPARTMENTS:
            ok, msg, dept_id = self.dept_svc.create_department(name, desc)
            if not ok:
                # Idempotent mode: reuse the existing department.
                existing = self.dept_svc.list_departments()
                hit = next((d for d in existing if d["department_name"] == name), None)
                if hit is None:
                    raise RuntimeError(f"Could not create department '{name}': {msg}")
                dept_id = hit["department_id"]
            self.dept_ids[name] = dept_id
        logger.info("Departments ready: %d", len(self.dept_ids))

    def _seed_users_and_doctors(self) -> None:
        admin_role = self.user_svc.get_role_id(Role.ADMIN)
        reception_role = self.user_svc.get_role_id(Role.RECEPTIONIST)

        def _ensure_user(username, password, role_id, full_name, email):
            existing = self.user_svc.get_all_users()
            hit = next((u for u in existing if u["username"] == username), None)
            if hit:
                return hit["user_id"]
            ok, msg, uid = self.user_svc.create_user({
                "username": username, "password": password, "role_id": role_id,
                "full_name": full_name, "email": email,
            })
            if not ok:
                raise RuntimeError(f"Could not create user '{username}': {msg}")
            return uid

        self.admin_id = _ensure_user(
            ADMIN_USERNAME, ADMIN_PASSWORD, admin_role, "System Administrator",
            "admin@hms.local",
        )
        self.reception_id = _ensure_user(
            RECEPTION_USERNAME, RECEPTION_PASSWORD, reception_role,
            "Sunita Rao", "reception@hms.local",
        )
        logger.info("Admin (id=%s) and receptionist (id=%s) ready",
                    self.admin_id, self.reception_id)

        for spec in DOCTORS:
            existing = DatabaseConnection.execute_query(
                "SELECT doctor_id FROM doctors WHERE email = %s", (spec["email"],),
                fetch_one=True,
            )
            if existing:
                self.doctor_ids[spec["name"]] = existing["doctor_id"]
                continue
            dept_id = self.dept_ids[spec["dept"]]
            username = spec["name"].replace("Dr. ", "dr.").replace(" ", ".").lower()
            ok, msg, doc_id = self.doctor_svc.create_doctor(
                {
                    "full_name": spec["name"],
                    "department_id": dept_id,
                    "specialization": spec["spec"],
                    "contact_number": spec["phone"],
                    "email": spec["email"],
                    "qualification": spec["qual"],
                    "license_number": spec["lic"],
                    "experience_years": spec["exp"],
                    "consultation_fee": spec["fee"],
                    "max_appointments_per_day": spec["max_day"],
                    "status": "Active",
                },
                user_data={
                    "username": username,
                    "password": DOCTOR_PASSWORD,
                    "full_name": spec["name"],
                    "email": spec["email"],
                },
            )
            if not ok:
                raise RuntimeError(f"Could not create doctor {spec['name']}: {msg}")
            self.doctor_ids[spec["name"]] = doc_id
            if spec["status"] == "On Leave":
                self.doctor_svc.update_doctor(
                    doc_id, {"status": DoctorStatus.ON_LEAVE},
                )
        logger.info("Doctors ready: %d", len(self.doctor_ids))

    def _seed_schedules(self) -> None:
        """Create weekly schedules (Mon–Fri; Sat for two doctors)."""
        for spec in DOCTORS:
            doc_id = self.doctor_ids[spec["name"]]
            start = _as_time(spec["hours"][0])
            end = _as_time(spec["hours"][1])
            lunch_start = _as_time(spec["lunch"][0])
            lunch_end = _as_time(spec["lunch"][1])
            for day in (MON, TUE, WED, THU, FRI):
                self.schedule_repo.upsert_schedule({
                    "doctor_id": doc_id, "day_of_week": day,
                    "start_time": start, "end_time": end,
                    "lunch_break_start": lunch_start, "lunch_break_end": lunch_end,
                    "is_available": True, "slot_duration": 15,
                })
            if spec["saturday"]:
                self.schedule_repo.upsert_schedule({
                    "doctor_id": doc_id, "day_of_week": SAT,
                    "start_time": _as_time("09:00"), "end_time": _as_time("13:00"),
                    "lunch_break_start": None, "lunch_break_end": None,
                    "is_available": True, "slot_duration": 15,
                })
        logger.info("Doctor schedules ready.")

    def _seed_leaves(self) -> None:
        for name, start_off, end_off, reason in DOCTOR_LEAVES:
            doc_id = self.doctor_ids[name]
            ok, msg, _ = self.doctor_svc.add_doctor_leave({
                "doctor_id": doc_id,
                "leave_start_date": self.today + timedelta(days=start_off),
                "leave_end_date": self.today + timedelta(days=end_off),
                "reason": reason,
                "status": "Approved",
            })
            if not ok:
                raise RuntimeError(f"Could not add leave for {name}: {msg}")
        logger.info("Doctor leave records ready.")

    def _seed_holidays(self) -> None:
        """Add 4 upcoming weekdays as holidays via the Settings service."""
        names = ["Hospital Maintenance Day", "Staff Training Day",
                 "Community Health Camp", "Foundation Day"]
        added = 0
        for offset in range(1, 15):
            if added >= len(names):
                break
            d = self.today + timedelta(days=offset)
            if d.weekday() >= 5:  # weekend — booking is blocked anyway
                continue
            ok, msg, _ = self.settings_svc.add_holiday(d, names[added])
            if not ok:
                continue  # e.g. already present in idempotent mode
            added += 1
        logger.info("Holidays added: %d", added)

    # ── Patients ───────────────────────────────────────────────

    def _seed_patients(self) -> None:
        random.seed(20260818)
        used_phones: set = set()
        # ~6 patients with genuinely empty optional fields
        sparse = random.sample(range(45), 6)

        for i in range(45):
            male = (i % 2 == 0)
            first = random.choice(MALE_FIRST if male else FEMALE_FIRST)
            last = random.choice(LAST)
            name = f"{first} {last}"
            gender = "Male" if male else "Female"
            age = random.randint(2, 85)
            dob = date(
                self.today.year - age,
                random.randint(1, 12),
                random.randint(1, 28),
            )
            phone = "9" + "".join(str(random.randint(0, 9)) for _ in range(9))
            while phone in used_phones:
                phone = "9" + "".join(str(random.randint(0, 9)) for _ in range(9))
            used_phones.add(phone)

            data: Dict[str, Any] = {
                "full_name": name,
                "date_of_birth": dob,
                "gender": gender,
                "contact_number": phone,
            }
            if i not in sparse:
                data["email"] = (
                    f"{first.lower()}.{last.lower()}{i}@example.com"
                )
                data["address"] = (
                    f"{random.randint(1, 250)}, {random.choice(['MG Road', 'Ring Road', 'Station Road', 'Lake View', 'Gandhi Nagar', 'Indiranagar'])}, "
                    f"{random.choice(['Mumbai', 'Delhi', 'Bengaluru', 'Hyderabad', 'Pune', 'Chennai', 'Kolkata', 'Ahmedabad'])}"
                )
                data["emergency_contact_name"] = random.choice(MALE_FIRST + FEMALE_FIRST) + " " + random.choice(LAST)
                data["emergency_contact_number"] = "9" + "".join(str(random.randint(0, 9)) for _ in range(9))
            data["blood_group"] = random.choice(BloodGroup.ALL)
            if random.random() < 0.22:
                data["allergies"] = ", ".join(random.sample(ALLERGIES, random.randint(1, 2)))
            # Spread registrations over the last 60 days (recent-biased)
            reg_off = int(random.expovariate(1 / 20))
            reg_off = min(reg_off, 59)
            data["registered_at"] = datetime.combine(
                self.today - timedelta(days=reg_off), time(9, 30),
            ) + timedelta(minutes=random.randint(0, 480))

            ok, msg, pid = self.patient_svc.register_patient(data)
            if not ok:
                if "already exists" in msg.lower():
                    # Idempotent: look up existing patient by phone
                    existing = self.patient_svc.get_patient_by_phone(phone)
                    if existing:
                        self.patient_ids.append(existing["patient_id"])
                        continue
                raise RuntimeError(f"Could not register patient {name}: {msg}")
            self.patient_ids.append(pid)
        logger.info("Patients registered: %d", len(self.patient_ids))

    def _seed_medical_history(self) -> None:
        """Chronic conditions for a handful of patients (raw insert —
        no medical_history service exists in the app)."""
        idxs = random.sample(range(len(self.patient_ids)), 8)
        for pid, (condition, status, desc) in zip(
            [self.patient_ids[i] for i in idxs], CHRONIC_CONDITIONS,
        ):
            DatabaseConnection.execute_query(
                """INSERT INTO medical_history
                   (patient_id, condition_name, description, diagnosed_date, status)
                   VALUES (%s, %s, %s, %s, %s)""",
                (pid, condition, desc, self.today - timedelta(days=random.randint(30, 700)), status),
                fetch=False,
            )
        logger.info("Medical history entries added: %d", len(CHRONIC_CONDITIONS))

    # ── Appointments ───────────────────────────────────────────

    def _valid_starts(self, doctor_id: int, d: date) -> List[time]:
        """All legal 15-minute slot starts for a doctor on date d."""
        sql_day = (d.weekday() + 1) % 7
        sched = self.schedule_repo.find_by_doctor_and_day(doctor_id, sql_day)
        if not sched or not sched.get("is_available", True):
            return []
        start = _as_time(sched["start_time"])
        end = _as_time(sched["end_time"])
        lunch_start = _as_time(sched.get("lunch_break_start"))
        lunch_end = _as_time(sched.get("lunch_break_end"))
        if not start or not end:
            return []
        step = timedelta(minutes=15)
        cur = datetime.combine(d, start)
        end_dt = datetime.combine(d, end)
        starts = []
        while cur + step <= end_dt:
            s = cur.time()
            e = (cur + step).time()
            if not (lunch_start and lunch_end and s < lunch_end and e > lunch_start):
                starts.append(s)
            cur += step
        return starts

    def _weighted_start(self, starts: List[time]) -> time:
        """Prefer weekday mornings (09-12) and early afternoons (14-16)."""
        morning = [s for s in starts if s.hour < 12]
        early_afternoon = [s for s in starts if 14 <= s.hour < 16]
        other = [s for s in starts if s not in morning and s not in early_afternoon]
        pools: List[List[time]] = []
        weights: List[float] = []
        if morning:
            pools.append(morning)
            weights.append(45)
        if early_afternoon:
            pools.append(early_afternoon)
            weights.append(35)
        if other:
            pools.append(other)
            weights.append(20)
        pool = random.choices(pools, weights=weights, k=1)[0]
        return random.choice(pool)

    def _pick_past_date(self) -> date:
        """Recent-biased weekday within the last 60 days."""
        for _ in range(30):
            if random.random() < 0.6:
                offset = random.randint(1, 30)
            else:
                offset = random.randint(31, 60)
            d = self.today - timedelta(days=offset)
            if d.weekday() < 5:
                return d
        return self.today - timedelta(days=random.randint(1, 60))

    def _slot_ok(
        self, doctor_id: int, d: date, start: time, end: time,
    ) -> Tuple[bool, str]:
        """Same engine rules the app enforces (minus the past-date rule)."""
        rows = self._by_doc_date.get((doctor_id, d), [])
        live = [
            r for r in rows
            if r["status"] in (AppointmentStatus.BOOKED, AppointmentStatus.COMPLETED)
        ]
        if self.engine._holiday_repo.is_holiday(d):
            return False, "hospital holiday"
        if self.engine._check_leave(doctor_id, d):
            return False, "doctor leave"
        err = self.engine._check_day_schedule(doctor_id, d, start, end)
        if err:
            return False, err
        err = self.engine._check_overlap(doctor_id, d, start, end, existing=live)
        if err:
            return False, err
        err = self.engine._check_daily_limit(doctor_id, d, existing=live)
        if err:
            return False, err
        return True, ""

    def _pick_past_slot(
        self, doctor_id: int, max_attempts: int = 60,
    ) -> Optional[Tuple[date, time, time]]:
        for _ in range(max_attempts):
            d = self._pick_past_date()
            starts = self._valid_starts(doctor_id, d)
            if not starts:
                continue
            start = self._weighted_start(starts)
            end = (datetime.combine(d, start) + timedelta(minutes=15)).time()
            ok, _ = self._slot_ok(doctor_id, d, start, end)
            if ok:
                return d, start, end
        return None

    def _insert_appt(
        self, doctor_id: int, patient_id: str, d: date, start: time, end: time,
        status: str, created_by: int, rescheduled_from_id: Optional[int] = None,
        created_at: Optional[datetime] = None,
    ) -> int:
        row: Dict[str, Any] = {
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "appointment_date": d,
            "start_time": start,
            "end_time": end,
            "status": status,
            "notes": random.choice(NOTES),
            "created_by": created_by,
            "created_at": created_at or (datetime.combine(d, time(9, 0)) - timedelta(days=random.randint(0, 5))),
            "updated_at": datetime.now(),
        }
        if rescheduled_from_id is not None:
            row["rescheduled_from_id"] = rescheduled_from_id
        appt_id = self.appt_repo.insert(row)
        self._by_doc_date.setdefault((doctor_id, d), []).append(
            {**row, "appointment_id": appt_id},
        )
        self.appointment_ids.append(appt_id)
        return appt_id

    def _book_future(
        self, doctor_id: int, patient_id: str, created_by: int,
    ) -> Optional[int]:
        """Book a future appointment through the REAL booking path."""
        for _ in range(20):
            d = self.today + timedelta(days=random.randint(0, 13))
            if d.weekday() >= 5:
                continue
            starts = self._valid_starts(doctor_id, d)
            if not starts:
                continue
            start = self._weighted_start(starts)
            end = (datetime.combine(d, start) + timedelta(minutes=15)).time()
            # If booking for today, only future times make sense
            if d == self.today:
                now = datetime.now().time().replace(second=0, microsecond=0)
                if start <= now:
                    continue
            ok, msg, appt_id = self.appt_svc.book_appointment({
                "patient_id": patient_id,
                "doctor_id": doctor_id,
                "appointment_date": d,
                "start_time": start,
                "end_time": end,
                "created_by": created_by,
                "notes": random.choice(NOTES),
            })
            if ok:
                self._by_doc_date.setdefault((doctor_id, d), []).append(
                    {"appointment_id": appt_id, "status": AppointmentStatus.BOOKED,
                     "start_time": start, "end_time": end},
                )
                self.appointment_ids.append(appt_id)
                return appt_id
        return None

    def _seed_appointments(self) -> None:
        created_by = self.reception_id or self.admin_id

        # Determine which doctors already have appointments (idempotent: skip them)
        already_seeded: set = set()
        if not self.reset:
            existing_appts = DatabaseConnection.execute_query(
                "SELECT DISTINCT doctor_id FROM appointments",
            ) or []
            already_seeded = {r["doctor_id"] for r in existing_appts}
            existing_count = len(DatabaseConnection.execute_query(
                "SELECT 1 FROM appointments LIMIT 1",
            ) or [])
            if existing_count and not already_seeded:
                # Appointments exist but none link to known doctors — skip
                logger.info(
                    "Appointments table already has rows and --reset was not "
                    "passed — skipping appointment/clinical/document seeding.",
                )
                return

        new_doctor_count = 0
        for name, plan in WORKLOAD.items():
            doc_id = self.doctor_ids[name]
            if doc_id in already_seeded:
                logger.info("Doctor %s already has appointments — skipping.", name)
                continue
            new_doctor_count += 1
            for _ in range(plan["completed"]):
                slot = self._pick_past_slot(doc_id)
                if not slot:
                    logger.warning("Could not find slot for %s (completed)", name)
                    continue
                d, start, end = slot
                appt_id = self._insert_appt(
                    doc_id, random.choice(self.patient_ids), d, start, end,
                    AppointmentStatus.COMPLETED, created_by,
                )
                self.completed_appt_ids.append(appt_id)
            for _ in range(plan["cancelled"]):
                slot = self._pick_past_slot(doc_id)
                if not slot:
                    continue
                d, start, end = slot
                self._insert_appt(
                    doc_id, random.choice(self.patient_ids), d, start, end,
                    AppointmentStatus.CANCELLED, created_by,
                )
            for _ in range(plan["no_show"]):
                slot = self._pick_past_slot(doc_id)
                if not slot:
                    continue
                d, start, end = slot
                self._insert_appt(
                    doc_id, random.choice(self.patient_ids), d, start, end,
                    AppointmentStatus.NO_SHOW, created_by,
                )
            for _ in range(plan["rescheduled"]):
                self._seed_reschedule_pair(doc_id, created_by)
            for _ in range(plan["booked"]):
                self._book_future(doc_id, random.choice(self.patient_ids), created_by)

        logger.info(
            "Appointments seeded: %d (completed=%d)",
            len(self.appointment_ids), len(self.completed_appt_ids),
        )

    def _seed_reschedule_pair(self, doctor_id: int, created_by: int) -> None:
        """Original (Cancelled) + new (Completed) row with a real link."""
        orig = self._pick_past_slot(doctor_id)
        if not orig:
            return
        d1, s1, e1 = orig
        orig_id = self._insert_appt(
            doctor_id, random.choice(self.patient_ids), d1, s1, e1,
            AppointmentStatus.CANCELLED, created_by,
            created_at=datetime.combine(d1, time(9, 0)) - timedelta(days=random.randint(2, 6)),
        )
        new_slot = self._pick_past_slot(doctor_id)
        if not new_slot:
            return
        d2, s2, e2 = new_slot
        new_id = self._insert_appt(
            doctor_id, random.choice(self.patient_ids), d2, s2, e2,
            AppointmentStatus.COMPLETED, created_by,
            rescheduled_from_id=orig_id,
            created_at=datetime.combine(d2, time(9, 0)) - timedelta(days=random.randint(1, 4)),
        )
        self.completed_appt_ids.append(new_id)

    # ── Clinical records ───────────────────────────────────────

    def _seed_visits_and_prescriptions(self) -> None:
        for appt_id in self.completed_appt_ids:
            appt = self.appt_repo.find_by_id("appointment_id", appt_id)
            if not appt:
                continue
            follow_up = None
            if random.random() < 0.25:
                follow_up = self.today + timedelta(days=random.randint(7, 30))
            ok, msg, visit_id = self.clinical_svc.create_visit({
                "appointment_id": appt_id,
                "doctor_id": appt["doctor_id"],
                "visit_date": appt["appointment_date"],
                "symptoms": random.choice(SYMPTOMS),
                "diagnosis": random.choice(DIAGNOSES),
                "doctor_notes": random.choice([
                    "Patient advised rest and adequate hydration.",
                    "Reviewed medications; continue current regimen.",
                    "Diet and lifestyle counselling provided.",
                    "Referred for blood tests; review in follow-up.",
                    "Condition improved; continue as prescribed.",
                ]),
                "follow_up_date": follow_up,
                "status": "Completed",
            })
            if not ok:
                raise RuntimeError(f"Could not create visit for appt {appt_id}: {msg}")
            self.visit_ids.append(visit_id)
            if random.random() < 0.5:
                for _ in range(random.randint(1, 3)):
                    med = random.choice(MEDICINES)
                    ok2, msg2, _ = self.clinical_svc.add_prescription(visit_id, {
                        "medicine_name": med[0], "dosage": med[1],
                        "frequency": med[2], "duration": med[3],
                        "route": med[4], "instructions": med[5],
                    })
                    if not ok2:
                        raise RuntimeError(f"Prescription failed: {msg2}")
        logger.info(
            "Visit records: %d, prescriptions on ~half", len(self.visit_ids),
        )

    # ── Documents ──────────────────────────────────────────────

    def _make_temp_files(self) -> Dict[str, str]:
        d = tempfile.mkdtemp(prefix="hms_seed_")
        pdf = os.path.join(d, "lab_report.pdf")
        with open(pdf, "wb") as fh:
            fh.write(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n")
        png = os.path.join(d, "xray_scan.png")
        with open(png, "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 96)
        jpg = os.path.join(d, "blood_report.jpg")
        with open(jpg, "wb") as fh:
            fh.write(b"\xff\xd8\xff\xe0" + b"\x00" * 96)
        dcm = os.path.join(d, "ct_scan.dcm")
        with open(dcm, "wb") as fh:
            fh.write(b"\x00" * 128 + b"DICM" + b"\x00" * 64)
        self._temp_dir = d
        return {"pdf": pdf, "png": png, "jpg": jpg, "dcm": dcm}

    def _seed_documents(self) -> None:
        files = self._make_temp_files()
        docs_added = 0
        # Patient documents for ~6 patients (real upload path)
        for pid in random.sample(self.patient_ids, min(6, len(self.patient_ids))):
            for _ in range(random.randint(1, 2)):
                src = random.choice([files["pdf"], files["png"], files["jpg"]])
                ok, msg, _ = self.doc_svc.upload_document(
                    pid, src, uploaded_by=self.admin_id,
                )
                if not ok:
                    raise RuntimeError(f"Document upload failed: {msg}")
                docs_added += 1
        # Test reports on ~8 visits (Blood / X-Ray / Lab)
        reports_added = 0
        for visit_id in random.sample(self.visit_ids, min(8, len(self.visit_ids))):
            report_type = random.choice([ReportType.BLOOD, ReportType.X_RAY, ReportType.LAB])
            src = files["png"] if report_type == ReportType.X_RAY else files["pdf"]
            ok, msg, _ = self.clinical_svc.add_report(visit_id, {
                "report_name": f"{report_type} Report",
                "file_path": src,
                "file_type": report_type,
                "file_size": os.path.getsize(src),
            })
            if not ok:
                raise RuntimeError(f"Test report failed: {msg}")
            reports_added += 1
        logger.info(
            "Documents seeded: %d patient docs, %d test reports",
            docs_added, reports_added,
        )

    # ── Audit backfill ─────────────────────────────────────────

    def _backfill_audit(self) -> None:
        """Plausible audit trail for the seeded data.

        Service-level seeding does not go through controllers (which is
        where the app writes audit entries), so this backfills the same
        actions through AuditService so the audit viewer has no gaps.

        In incremental mode (no --reset) only entities that have no
        existing audit entry are backfilled, preventing duplicates.
        """
        a = self.audit_svc

        # Idempotent helper: return True if an audit entry already exists
        # for (action, entity, target_id).
        def _already_logged(action: str, entity: str, target_id: str) -> bool:
            row = DatabaseConnection.execute_query(
                "SELECT 1 FROM audit_logs WHERE action = %s AND "
                "target_entity = %s AND target_id = %s LIMIT 1",
                (action, entity, target_id),
                fetch_one=True,
            )
            return row is not None

        # Logins over the past month for the demo users
        for uid, role in (
            (self.admin_id, "admin"), (self.reception_id, "receptionist"),
        ):
            for i in range(12):
                a.log(
                    AuditAction.LOGIN, user_id=uid, target_entity="User",
                    target_id=str(uid),
                    new_values={"role": role},
                )
        for doc_id in self.doctor_ids.values():
            doc = self.doctor_repo.find_by_id_with_details(doc_id)
            if doc and doc.get("user_id"):
                a.log(
                    AuditAction.LOGIN, user_id=doc["user_id"],
                    target_entity="User", target_id=str(doc["user_id"]),
                    new_values={"role": "doctor"},
                )

        # Patient registrations (skip if already logged)
        for pid in self.patient_ids:
            if _already_logged(AuditAction.PATIENT_REGISTER, "Patient", pid):
                continue
            pat = self.patient_repo.find_by_id(pid)
            if not pat:
                continue
            a.log(
                AuditAction.PATIENT_REGISTER, user_id=self.reception_id,
                target_entity="Patient", target_id=pid,
                new_values={"full_name": pat.get("full_name")},
            )

        # Appointments (skip if already logged)
        rows = DatabaseConnection.execute_query(
            "SELECT appointment_id, status, created_by, created_at, "
            "rescheduled_from_id, appointment_date FROM appointments",
        ) or []
        for r in rows:
            target = f"appt:{r['appointment_id']}"
            if r["status"] == AppointmentStatus.CANCELLED and r.get("rescheduled_from_id") is None:
                # could be a plain cancellation or the original of a pair
                pair = next(
                    (x for x in rows
                     if x.get("rescheduled_from_id") == r["appointment_id"]),
                    None,
                )
                action = AuditAction.APPOINTMENT_RESCHEDULE if pair else AuditAction.APPOINTMENT_CANCEL
            elif r.get("rescheduled_from_id") is not None:
                action = AuditAction.APPOINTMENT_RESCHEDULE
            else:
                action = AuditAction.APPOINTMENT_BOOK
            if _already_logged(action, "Appointment", target):
                continue
            a.log(
                action, user_id=r["created_by"],
                target_entity="Appointment", target_id=target,
                new_values={"status": r["status"], "date": str(r["appointment_date"])},
            )

        # Visits / prescriptions / reports / documents
        for visit_id in self.visit_ids:
            target = str(visit_id)
            if not _already_logged(AuditAction.CREATE, "VisitRecord", target):
                a.log(AuditAction.CREATE, user_id=self.admin_id,
                      target_entity="VisitRecord", target_id=target)
        for visit_id in self.visit_ids:
            rx_rows = DatabaseConnection.execute_query(
                "SELECT prescription_id FROM prescriptions WHERE visit_id = %s",
                (visit_id,),
            ) or []
            for rx in rx_rows:
                rx_target = str(rx["prescription_id"])
                if not _already_logged(AuditAction.PRESCRIPTION_CREATE, "Prescription", rx_target):
                    a.log(AuditAction.PRESCRIPTION_CREATE, user_id=self.admin_id,
                          target_entity="Prescription", target_id=rx_target)
        for r in DatabaseConnection.execute_query("SELECT report_id FROM test_reports") or []:
            target = str(r["report_id"])
            if not _already_logged(AuditAction.REPORT_UPLOAD, "TestReport", target):
                a.log(AuditAction.REPORT_UPLOAD, user_id=self.admin_id,
                      target_entity="TestReport", target_id=target)
        for r in DatabaseConnection.execute_query("SELECT document_id FROM patient_documents") or []:
            target = str(r["document_id"])
            if not _already_logged(AuditAction.DOCUMENT_UPLOAD, "PatientDocument", target):
                a.log(AuditAction.DOCUMENT_UPLOAD, user_id=self.admin_id,
                      target_entity="PatientDocument", target_id=target)
        logger.info("Audit trail backfilled.")

    # ── Verification ───────────────────────────────────────────

    def _verify_all_appointments(self) -> List[str]:
        """Re-run the engine's rule checks against every appointment."""
        violations: List[str] = []
        rows = DatabaseConnection.execute_query(
            "SELECT appointment_id, doctor_id, appointment_date, start_time, "
            "end_time, status, rescheduled_from_id FROM appointments",
        ) or []
        by_key: Dict[Tuple[int, date], List[Dict[str, Any]]] = {}
        for r in rows:
            d = r["appointment_date"]
            if isinstance(d, datetime):
                d = d.date()
            by_key.setdefault((r["doctor_id"], d), []).append(r)

        for r in rows:
            d = r["appointment_date"]
            if isinstance(d, datetime):
                d = d.date()
            start = _as_time(r["start_time"])
            end = _as_time(r["end_time"])
            doctor_id = r["doctor_id"]
            appt_id = r["appointment_id"]

            if self.engine._holiday_repo.is_holiday(d):
                violations.append(f"#{appt_id} on holiday {d}")
            if self.engine._check_leave(doctor_id, d):
                violations.append(f"#{appt_id} on doctor leave {d}")
            err = self.engine._check_day_schedule(doctor_id, d, start, end)
            if err:
                violations.append(f"#{appt_id} schedule violation: {err}")
            live = [
                x for x in by_key.get((doctor_id, d), [])
                if x["status"] in (AppointmentStatus.BOOKED, AppointmentStatus.COMPLETED)
                and x["appointment_id"] != appt_id
            ]
            err = self.engine._check_overlap(
                doctor_id, d, start, end,
                exclude_appointment_id=appt_id, existing=live,
            )
            if err:
                violations.append(f"#{appt_id} overlap violation: {err}")
            err = self.engine._check_daily_limit(
                doctor_id, d,
                exclude_appointment_id=appt_id,
                existing=live,
            )
            if err:
                violations.append(f"#{appt_id} daily-limit violation: {err}")

        # rescheduled_from_id integrity
        ids = {r["appointment_id"] for r in rows}
        for r in rows:
            if r.get("rescheduled_from_id") and r["rescheduled_from_id"] not in ids:
                violations.append(
                    f"#{r['appointment_id']} has dangling rescheduled_from_id "
                    f"{r['rescheduled_from_id']}"
                )
        return violations

    def _print_summary(self, violations: List[str]) -> None:
        counts = {}
        for t in ["roles", "users", "departments", "doctors", "doctor_schedules",
                  "doctor_leave", "patients", "appointments", "visit_records",
                  "prescriptions", "test_reports", "patient_documents",
                  "medical_history", "hospital_holidays", "audit_logs"]:
            res = DatabaseConnection.execute_query(
                f"SELECT COUNT(*) AS c FROM `{t}`", fetch_one=True,
            )
            counts[t] = res["c"] if res else 0

        print("\n" + "=" * 64)
        print("DEMO DATA SEEDED — SUMMARY")
        print("=" * 64)
        for t in ["departments", "doctors", "doctor_schedules", "doctor_leave",
                  "patients", "medical_history", "appointments", "visit_records",
                  "prescriptions", "test_reports", "patient_documents",
                  "hospital_holidays", "audit_logs", "users"]:
            print(f"  {t:<22} {counts[t]:>5}")
        if violations:
            print("\n  ⚠ SCHEMA-CONSISTENCY VIOLATIONS FOUND:")
            for v in violations[:20]:
                print(f"    - {v}")
            if len(violations) > 20:
                print(f"    ... and {len(violations) - 20} more")
        else:
            print("\n  ✔ All %d appointments re-validated against the scheduling "
                  "engine rules — zero violations." % counts["appointments"])
        print("\nDemo logins (password min length %d):" % app_config.password_min_length)
        print(f"  admin       / {ADMIN_PASSWORD}  (Administrator)")
        print(f"  reception   / {RECEPTION_PASSWORD}  (Receptionist)")
        for name in DOCTORS:
            username = name["name"].replace("Dr. ", "dr.").replace(" ", ".").lower()
            print(f"  {username:<12} / {DOCTOR_PASSWORD}  ({name['name']})")
        holidays = self.settings_svc.list_holidays()
        upcoming = [h for h in holidays if h["holiday_date"] >= self.today]
        print("\nUpcoming holidays (booking blocked):")
        for h in upcoming[:4]:
            print(f"  {h['holiday_date']}  {h['description']}")
        leave_docs = [
            (name, off) for name, off, _, _ in DOCTOR_LEAVES
        ]
        print("\nUpcoming doctor leave (booking blocked for that doctor):")
        for name, off in leave_docs:
            print(f"  {name}: {self.today + timedelta(days=off)} (and following days)")
        print("=" * 64)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed the Hospital Management System with demo data. "
                    "Manual tool only — never run at app startup.",
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Wipe all data tables first, then reseed from scratch.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    DatabaseConnection.initialize()
    seeder = DemoDataSeeder(reset=args.reset)
    try:
        seeder.run()
    except Exception:
        logger.exception("Demo data seeding failed")
        return 1
    finally:
        DatabaseConnection.close_pool()
    return 0


if __name__ == "__main__":
    sys.exit(main())
