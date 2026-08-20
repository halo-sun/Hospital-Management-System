"""Patient service for patient management business logic.

Delegates data cleaning and validation to the controller layer.
This service focuses solely on persistence and duplicate detection.
"""
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from src.repositories.patient_repository import PatientRepository
from src.repositories.clinical_repository import VisitRecordRepository

logger = logging.getLogger(__name__)


class PatientService:
    """Handles patient registration, search, and record management."""

    def __init__(self) -> None:
        """Initialize PatientService with required repositories."""
        self._patient_repo = PatientRepository()
        self._visit_repo = VisitRecordRepository()

    def register_patient(self, data: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """Register a new patient.

        Data is expected to be already cleaned and validated by the
        controller.  This method checks for duplicate phone/email,
        generates a patient ID, and inserts the record.

        Args:
            data: Dictionary with patient fields (cleaned).

        Returns:
            Tuple of (success, message, patient_id_or_None).
        """
        # Required fields (defensive check — controller should have validated)
        if not data.get("full_name"):
            return False, "Full name is required.", None
        if not data.get("contact_number"):
            return False, "Contact number is required.", None

        # Duplicate phone
        phone = data["contact_number"]
        existing_phone = self._patient_repo.find_by_phone(phone)
        if existing_phone:
            return False, "A patient with this phone number already exists.", None

        # Duplicate email
        email = data.get("email", "")
        if email:
            existing_email = self._patient_repo.find_by_email(email)
            if existing_email:
                return False, "A patient with this email address already exists.", None

        patient_id = self._patient_repo.get_next_patient_id()
        data["patient_id"] = patient_id
        data["registered_at"] = datetime.now()

        # Convert DOB string to date object for MySQL DATE column
        self._convert_dob(data)

        self._patient_repo.create_patient(data)
        logger.info("Patient registered: %s - %s", patient_id, data.get("full_name"))
        return True, f"Patient registered with ID: {patient_id}", patient_id

    def update_patient(
        self, patient_id: str, data: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Update an existing patient record.

        Checks for duplicate phone/email before updating.

        Args:
            patient_id: The patient ID.
            data: Fields to update (cleaned).

        Returns:
            Tuple of (success, message).
        """
        existing = self._patient_repo.find_by_id(patient_id)
        if not existing:
            return False, "Patient not found."

        # Duplicate phone (skip if unchanged)
        phone = data.get("contact_number")
        if phone and phone != existing.get("contact_number"):
            dup = self._patient_repo.find_by_phone(phone)
            if dup and dup.get("patient_id") != patient_id:
                return False, "Another patient with this phone number already exists."

        # Duplicate email (skip if unchanged)
        email = data.get("email", "")
        if email and email != existing.get("email"):
            dup_email = self._patient_repo.find_by_email(email)
            if dup_email and dup_email.get("patient_id") != patient_id:
                return False, "Another patient with this email address already exists."

        # Convert DOB string to date object for MySQL DATE column
        self._convert_dob(data)

        self._patient_repo.update_patient(patient_id, data)
        logger.info("Patient updated: %s", patient_id)
        return True, "Patient updated successfully."

    @staticmethod
    def _convert_dob(data: Dict[str, Any]) -> None:
        """Convert a DOB string to a date object for DB storage.

        Mutates *data* in place: if ``date_of_birth`` is a string,
        it is parsed into a ``date`` object so MySQL's DATE column
        receives the correct type regardless of the display format
        the user entered (DD-MM-YYYY, YYYY-MM-DD, etc.).

        Args:
            data: Patient data dictionary (mutated in place).
        """
        from src.utils.formatters import _parse_date_string
        dob = data.get("date_of_birth")
        if isinstance(dob, str) and dob.strip():
            parsed = _parse_date_string(dob)
            if parsed is not None:
                data["date_of_birth"] = parsed

    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get a patient record by ID.

        Args:
            patient_id: The patient ID string.

        Returns:
            Patient dictionary or None.
        """
        return self._patient_repo.find_by_id(patient_id)

    def search_patients(self, search_term: str) -> List[Dict[str, Any]]:
        """Search patients by ID, name, or phone number.

        Args:
            search_term: Text to search for.

        Returns:
            List of matching patient records.
        """
        return self._patient_repo.search_patients(search_term)

    def get_all_patients(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all patients with pagination.

        Args:
            limit: Maximum number of records.
            offset: Number of records to skip.

        Returns:
            List of patient records.
        """
        return self._patient_repo.find_all_patients(limit=limit, offset=offset)

    def delete_patient(self, patient_id: str) -> Tuple[bool, str]:
        """Delete a patient record.

        Args:
            patient_id: The patient ID to delete.

        Returns:
            Tuple of (success, message).
        """
        existing = self._patient_repo.find_by_id(patient_id)
        if not existing:
            return False, "Patient not found."

        self._patient_repo.delete_patient(patient_id)
        logger.info("Patient deleted: %s", patient_id)
        return True, "Patient deleted successfully."

    def get_patient_history(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get a patient's visit history.

        Args:
            patient_id: The patient ID.

        Returns:
            List of visit records.
        """
        return self._visit_repo.find_by_patient(patient_id)

    def get_recent_patients(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently registered patients.

        Args:
            limit: Number of records.

        Returns:
            List of recent patient records.
        """
        return self._patient_repo.find_recent(limit)

    def get_total_count(self) -> int:
        """Get the total number of registered patients.

        Returns:
            Total patient count.
        """
        return self._patient_repo.count_all()

    def get_stats_by_gender(self) -> List[Dict[str, Any]]:
        """Get patient count grouped by gender.

        Returns:
            List of dicts with 'gender' and 'count'.
        """
        return self._patient_repo.count_by_gender()

    def get_patient_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get a patient by phone number.

        Args:
            phone: The phone number to search for.

        Returns:
            Patient record or None.
        """
        return self._patient_repo.find_by_phone(phone)
