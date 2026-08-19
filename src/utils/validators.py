"""Centralised input validators for the Hospital Management System.

All validation functions follow the same signature::

    (value: str) -> Tuple[bool, str]

where the second element is an empty string on success or a
human-readable error message on failure.

These are the **single source of truth** for validation rules so
that controllers and GUI components never duplicate the logic.
"""
from __future__ import annotations

import re
from datetime import date, datetime, time
from typing import List, Optional, Sequence, Tuple

from src.constants import BloodGroup, Gender

# ── Regex patterns (compiled once) ─────────────────────────────

# Full name: letters, spaces, dots, hyphens, apostrophes
_NAME_RE = re.compile(r"^[a-zA-Z\s.\-']+$")

# Phone: digits, spaces, hyphens, plus, parentheses — 7 to 20 chars
_PHONE_RE = re.compile(r"^[\d\s\-+()]{7,20}$")

# Email: standard format
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Alphanumeric ID (e.g. PAT-00001)
_ID_RE = re.compile(r"^[A-Za-z0-9\-]+$")


# ── Public validation functions ────────────────────────────────


def validate_full_name(name: str, required: bool = False) -> Tuple[bool, str]:
    """Validate a patient's full name.

    Args:
        name: The name string to validate.
        required: Whether an empty string is rejected.

    Returns:
        Tuple of (valid, error_message).
    """
    if required and not name:
        return False, "Full name is required."
    if name and not _NAME_RE.match(name):
        return False, "Full name contains invalid characters. Use letters, spaces, dots, hyphens, or apostrophes."
    return True, ""


def validate_phone(phone: str, required: bool = False) -> Tuple[bool, str]:
    """Validate a contact phone number.

    Accepts digits, spaces, ``-``, ``+``, and ``(`` / ``)``.
    Length must be between 7 and 20 characters.

    Args:
        phone: The phone number string.
        required: Whether an empty string is rejected.

    Returns:
        Tuple of (valid, error_message).
    """
    if required and not phone:
        return False, "Contact number is required."
    if phone and not _PHONE_RE.match(phone):
        return False, "Invalid phone number format. Use digits, spaces, hyphens, plus, or parentheses (7–20 chars)."
    return True, ""


def validate_email(email: str, required: bool = False) -> Tuple[bool, str]:
    """Validate an email address.

    Args:
        email: The email string.
        required: Whether an empty string is rejected.

    Returns:
        Tuple of (valid, error_message).
    """
    if required and not email:
        return False, "Email is required."
    if email and not _EMAIL_RE.match(email):
        return False, "Invalid email address format."
    return True, ""


def validate_date_of_birth(
    dob_str: str, allow_future: bool = False, min_age: int = 0, max_age: int = 150
) -> Tuple[bool, str]:
    """Validate a date-of-birth string and optionally check age range.

    Accepts ``YYYY-MM-DD``, ``YYYY/MM/DD``, or ``DD-MM-YYYY`` formats.

    Args:
        dob_str: The date string to validate.
        allow_future: If True, future dates are accepted (for appointment dates).
        min_age: Minimum allowed age in years (0 = no minimum).
        max_age: Maximum allowed age in years (150 = no practical maximum).

    Returns:
        Tuple of (valid, error_message).  On success the second element
        may be empty or contain an informational age string.
    """
    if not dob_str:
        return True, ""  # Optional field

    # Try multiple formats
    parsed: Optional[date] = None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            parsed = datetime.strptime(dob_str, fmt).date()
            break
        except ValueError:
            continue

    if parsed is None:
        return False, "Invalid date format. Use YYYY-MM-DD."

    today = date.today()

    if not allow_future and parsed > today:
        return False, "Date of birth cannot be in the future."

    if parsed > today:
        return True, ""  # Future date allowed for appt dates

    # Age calculation
    age = today.year - parsed.year - (
        (today.month, today.day) < (parsed.month, parsed.day)
    )
    if age < min_age:
        return False, f"Patient must be at least {min_age} year(s) old."
    if age > max_age:
        return False, f"Patient cannot be older than {max_age} year(s)."

    return True, str(age)


def validate_gender(gender: str) -> Tuple[bool, str]:
    """Validate a gender string against the allowed values.

    Args:
        gender: The gender string.

    Returns:
        Tuple of (valid, error_message).
    """
    if gender and gender not in Gender.ALL:
        return False, f"Invalid gender. Must be one of: {', '.join(Gender.ALL)}"
    return True, ""


def validate_blood_group(blood_group: str) -> Tuple[bool, str]:
    """Validate a blood group string against the allowed values.

    Args:
        blood_group: The blood group string.

    Returns:
        Tuple of (valid, error_message).
    """
    if blood_group and blood_group not in BloodGroup.ALL:
        return False, f"Invalid blood group. Must be one of: {', '.join(BloodGroup.ALL)}"
    return True, ""


def validate_patient_id(pid: str) -> Tuple[bool, str]:
    """Validate a patient ID format (e.g. ``PAT-00001``).

    Args:
        pid: The patient ID string.

    Returns:
        Tuple of (valid, error_message).
    """
    if not pid:
        return False, "Patient ID is required."
    if not _ID_RE.match(pid):
        return False, "Patient ID contains invalid characters."
    return True, ""


# ── Doctor / department validators ──────────────────────────────


def validate_department_name(name: str) -> Tuple[bool, str]:
    """Validate a department name.

    Args:
        name: The department name.

    Returns:
        Tuple of (valid, error_message).
    """
    if not name or not name.strip():
        return False, "Department name is required."
    if len(name.strip()) > 100:
        return False, "Department name must be 100 characters or fewer."
    return True, ""


def validate_doctor_data(data: dict) -> Tuple[bool, str]:
    """Validate doctor form data.

    Args:
        data: Dictionary with full_name, department_id, email,
              consultation_fee, experience_years, etc.

    Returns:
        Tuple of (valid, error_message).
    """
    if not data.get("full_name", "").strip():
        return False, "Full name is required."
    if not data.get("department_id"):
        return False, "Department is required."

    email = data.get("email", "")
    if email:
        valid, msg = validate_email(email)
        if not valid:
            return False, msg

    fee = data.get("consultation_fee", 0)
    if fee is not None:
        try:
            fee = float(fee)
            if fee < 0:
                return False, "Consultation fee cannot be negative."
        except (ValueError, TypeError):
            return False, "Invalid consultation fee."

    exp = data.get("experience_years", 0)
    if exp is not None:
        try:
            exp = int(exp)
            if exp < 0 or exp > 60:
                return False, "Experience years must be between 0 and 60."
        except (ValueError, TypeError):
            return False, "Invalid experience years."

    phone = data.get("contact_number", "")
    if phone:
        valid, msg = validate_phone(phone)
        if not valid:
            return False, msg

    return True, ""


def validate_schedule_data(day_of_week: int, start_time, end_time) -> Tuple[bool, str]:
    """Validate a doctor schedule entry.

    Args:
        day_of_week: Day number (0=Sunday, 6=Saturday).
        start_time: Working start time.
        end_time: Working end time.

    Returns:
        Tuple of (valid, error_message).
    """
    if day_of_week < 0 or day_of_week > 6:
        return False, "Invalid day of week."
    if not start_time:
        return False, "Start time is required."
    if not end_time:
        return False, "End time is required."
    if start_time >= end_time:
        return False, "Start time must be before end time."
    return True, ""


# ── Appointment / booking validators ───────────────────────────


def validate_appointment_date(date_str: str) -> Tuple[bool, str]:
    """Validate an appointment date string.

    Args:
        date_str: Date string in ``YYYY-MM-DD`` format.

    Returns:
        Tuple of (valid, error_message).
    """
    if not date_str:
        return False, "Appointment date is required."
    try:
        parsed = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
        if parsed < date.today():
            return False, "Appointment date cannot be in the past."
    except ValueError:
        return False, "Invalid date format. Use YYYY-MM-DD."
    return True, ""


def validate_time_slot(start_str: str, end_str: str) -> Tuple[bool, str]:
    """Validate a time slot (start and end times).

    Args:
        start_str: Start time string in ``HH:MM`` format.
        end_str: End time string in ``HH:MM`` format.

    Returns:
        Tuple of (valid, error_message).
    """
    if not start_str:
        return False, "Start time is required."
    if not end_str:
        return False, "End time is required."
    try:
        start = datetime.strptime(start_str.strip(), "%H:%M").time()
        end = datetime.strptime(end_str.strip(), "%H:%M").time()
        if start >= end:
            return False, "Start time must be before end time."
    except ValueError:
        return False, "Invalid time format. Use HH:MM (24-hour)."
    return True, ""


def validate_booking_data(data: dict) -> Tuple[bool, str]:
    """Validate complete appointment booking data.

    Composite validator that checks all required appointment fields.

    Args:
        data: Dictionary with patient_id, doctor_id, appointment_date,
              start_time, end_time, and optional notes.

    Returns:
        Tuple of (valid, error_message).
    """
    if not data.get("patient_id"):
        return False, "Patient is required."
    if not data.get("doctor_id"):
        return False, "Doctor is required."

    appt_date = data.get("appointment_date", "")
    if isinstance(appt_date, str):
        valid, msg = validate_appointment_date(appt_date)
        if not valid:
            return False, msg

    start = data.get("start_time", "")
    end = data.get("end_time", "")
    if isinstance(start, str) and isinstance(end, str):
        valid, msg = validate_time_slot(start, end)
        if not valid:
            return False, msg
    elif isinstance(start, time) and isinstance(end, time):
        if start >= end:
            return False, "Start time must be before end time."

    return True, ""


# ── Composite validator for controllers ────────────────────────


def validate_patient_data(
    data: dict,
    is_edit: bool = False,
) -> Tuple[bool, str]:
    """Run **all** patient-field validators and return the first failure.

    This is the convenience entry-point used by ``PatientController``.
    Individual validators can be called directly by tests or other
    controllers.

    Args:
        data: Dictionary with patient fields (full_name, contact_number,
              email, date_of_birth, gender, blood_group).
        is_edit: If True the full_name requirement is relaxed
                 (the name was already set at registration).

    Returns:
        Tuple of (valid, first_error_message).
    """
    checks: List[Tuple[str, Tuple[bool, str]]] = [
        ("full_name", validate_full_name(data.get("full_name", ""), required=not is_edit)),
        ("contact_number", validate_phone(data.get("contact_number", ""), required=True)),
        ("email", validate_email(data.get("email", ""))),
        ("date_of_birth", validate_date_of_birth(data.get("date_of_birth", ""))),
        ("gender", validate_gender(data.get("gender", ""))),
        ("blood_group", validate_blood_group(data.get("blood_group", ""))),
    ]

    for field, (valid, msg) in checks:
        if not valid:
            return False, msg

    return True, ""


def validate_search(search_term: str, min_length: int = 2) -> Tuple[bool, str]:
    """Validate a general search term (reusable across controllers).

    Args:
        search_term: The search text.
        min_length: Minimum character count required.

    Returns:
        Tuple of (valid, error_message).
    """
    if not search_term or not search_term.strip():
        return False, "Search term is required."
    if len(search_term.strip()) < min_length:
        return False, f"Search term must be at least {min_length} characters."
    return True, ""


def clean_strings(data: dict) -> dict:
    """Return a new dict with all string values stripped of whitespace.

    Args:
        data: Raw input dictionary.

    Returns:
        Dict with stripped string values.
    """
    return {
        key: (value.strip() if isinstance(value, str) else value)
        for key, value in data.items()
    }


def strip_control_characters(text: Optional[str]) -> str:
    """Remove control characters (except newline/tab) from free text.

    Control characters such as ``\x00``, ``\x1b``, or ``\x7f`` are
    stripped so they never reach the database or logs.  Newlines and
    tabs are preserved (they are meaningful in notes/descriptions).

    Args:
        text: Raw free-text input (may be None).

    Returns:
        The cleaned string with control characters removed.
    """
    if not text:
        return ""
    return "".join(
        ch for ch in text
        if ch in ("\n", "\t") or ord(ch) >= 32 and ch != "\x7f"
    )


def validate_holiday_date(date_str: str) -> Tuple[bool, str]:
    """Validate a hospital holiday date string.

    Accepts ``YYYY-MM-DD``.  Past dates are allowed (holidays are
    reference data and may be listed historically); only the format
    must be valid.

    Args:
        date_str: Date string in ``YYYY-MM-DD`` format.

    Returns:
        Tuple of (valid, error_message).
    """
    if not date_str or not date_str.strip():
        return False, "Holiday date is required."
    try:
        datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return False, "Invalid date format. Use YYYY-MM-DD."
    return True, ""
