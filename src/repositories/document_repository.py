"""Document repository – data access for the ``patient_documents`` table.

All queries are parameterized; file-handling security (extension
allow-list, magic bytes, size caps, random storage names, path
resolution) lives in :mod:`src.services.document_service`, never here.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class DocumentRepository(BaseRepository):
    """Repository for patient document records."""

    def __init__(self) -> None:
        """Initialize DocumentRepository."""
        super().__init__("patient_documents")

    def find_by_patient(self, patient_id: str) -> List[Dict[str, Any]]:
        """Find all documents for a patient, newest first.

        Args:
            patient_id: The patient ID.

        Returns:
            List of document records.
        """
        return self.find_where(
            {"patient_id": patient_id}, order_by="upload_date DESC",
        )

    def find_by_id(self, document_id: int) -> Optional[Dict[str, Any]]:
        """Find a document by its primary key.

        Args:
            document_id: The document ID.

        Returns:
            Document record or None.
        """
        return super().find_by_id("document_id", document_id)

    def create_document(self, data: Dict[str, Any]) -> int:
        """Insert a new document record.

        Args:
            data: Dictionary of document fields.

        Returns:
            The new document's ID.
        """
        return self.insert(data)

    def delete_document(self, document_id: int) -> int:
        """Delete a document record.

        Args:
            document_id: The document ID.

        Returns:
            Number of rows deleted.
        """
        return self.delete("document_id", document_id)
