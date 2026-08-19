"""Patient document model."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.models.base import BaseModel


@dataclass
class PatientDocument(BaseModel):
    """A document attached to a patient record.

    Maps to the ``patient_documents`` table: documents attach to the
    patient directly (rather than to a visit) — e.g. consent forms,
    referrals, or scans kept at the patient level.

    Security note: ``file_path`` is the **storage** path (a random
    uuid4 name inside the uploads directory); the original filename is
    kept only in ``document_name`` as metadata.
    """

    document_id: Optional[int] = None
    patient_id: str = ""
    document_name: str = ""
    file_path: str = ""
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_by: Optional[int] = None
    upload_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def display_name(self) -> str:
        """Return the original filename of the document."""
        return self.document_name

    @property
    def file_size_str(self) -> str:
        """Return a human-readable file size."""
        size = self.file_size or 0
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.1f} MB"
