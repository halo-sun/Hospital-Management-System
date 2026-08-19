"""Patient repository for patient CRUD operations."""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from src.repositories.base_repository import BaseRepository
from src.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class PatientRepository(BaseRepository):
    """Repository for patient-related database operations."""

    def __init__(self) -> None:
        """Initialize PatientRepository."""
        super().__init__("patients")

    def find_by_id(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Find a patient by patient_id (string).

        Args:
            patient_id: The patient ID string (e.g. PAT-00001).

        Returns:
            Patient dictionary or None if not found.
        """
        return super().find_by_id("patient_id", patient_id)

    def create_patient(self, patient_data: Dict[str, Any]) -> str:
        """Insert a new patient record.

        Args:
            patient_data: Dictionary of patient fields.

        Returns:
            The generated patient_id string.
        """
        self.insert(patient_data)
        return patient_data.get("patient_id", "")

    def update_patient(self, patient_id: str, patient_data: Dict[str, Any]) -> int:
        """Update an existing patient record.

        Args:
            patient_id: The patient ID string.
            patient_data: Dictionary of fields to update.

        Returns:
            Number of rows affected.
        """
        patient_data["updated_at"] = datetime.now()
        return self.update("patient_id", patient_id, patient_data)

    def delete_patient(self, patient_id: str) -> int:
        """Delete a patient record.

        Args:
            patient_id: The patient ID string to delete.

        Returns:
            Number of rows deleted.
        """
        return self.delete("patient_id", patient_id)

    def find_all_patients(
        self, order_by: str = "registered_at DESC", limit: int = 0, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Find all patients with optional pagination.

        Args:
            order_by: Column to order by.
            limit: Maximum number of records.
            offset: Number of records to skip.

        Returns:
            List of patient records.
        """
        return self.find_all(order_by=order_by, limit=limit, offset=offset)

    def search_patients(self, search_term: str) -> List[Dict[str, Any]]:
        """Search patients by ID, name, or phone number.

        Args:
            search_term: Text to search for.

        Returns:
            List of matching patient records.
        """
        return self.search(
            search_columns=["patient_id", "full_name", "contact_number"],
            search_term=search_term,
            order_by="full_name ASC",
            limit=50,
        )

    def find_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Find a patient by contact phone number.

        Args:
            phone_number: The contact number to search for.

        Returns:
            Patient dictionary or None if not found.
        """
        results = self.find_where({"contact_number": phone_number})
        return results[0] if results else None

    def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find a patient by email address.

        Args:
            email: The email address to search for.

        Returns:
            Patient dictionary or None if not found.
        """
        if not email:
            return None
        results = self.find_where({"email": email})
        return results[0] if results else None

    def count_all(self) -> int:
        """Count total registered patients.

        Returns:
            Number of patients in the database.
        """
        return self.count_where()

    def get_next_patient_id(self) -> str:
        """Generate the next sequential patient ID.

        Queries the maximum existing patient_id and increments it.

        Returns:
            The next patient_id string (e.g. PAT-00042).
        """
        query = "SELECT patient_id FROM patients ORDER BY patient_id DESC LIMIT 1"
        result = DatabaseConnection.execute_query(query, fetch_one=True)

        if result and result.get("patient_id"):
            last_id = result["patient_id"]
            try:
                num = int(last_id.split("-")[1]) + 1
            except (IndexError, ValueError):
                num = 1
        else:
            num = 1

        return f"PAT-{num:05d}"

    def find_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Find the most recently registered patients.

        Args:
            limit: Number of records to return.

        Returns:
            List of recent patient records.
        """
        return self.find_all(order_by="registered_at DESC", limit=limit)

    def count_by_gender(self) -> List[Dict[str, Any]]:
        """Count patients grouped by gender.

        Returns:
            List of dicts with 'gender' and 'count' keys.
        """
        query = """
            SELECT gender, COUNT(*) as count
            FROM patients
            GROUP BY gender
            ORDER BY gender
        """
        return DatabaseConnection.execute_query(query) or []

    def count_registrations_by_date(
        self, start_date: date, end_date: date,
    ) -> List[Dict[str, Any]]:
        """Count patient registrations grouped by date within a range.

        Args:
            start_date: Range start date.
            end_date: Range end date.

        Returns:
            List of dicts with 'registration_date' and 'count'.
        """
        query = """
            SELECT DATE(registered_at) as registration_date, COUNT(*) as count
            FROM patients
            WHERE DATE(registered_at) BETWEEN %s AND %s
            GROUP BY DATE(registered_at)
            ORDER BY registration_date
        """
        return DatabaseConnection.execute_query(query, (start_date, end_date)) or []
