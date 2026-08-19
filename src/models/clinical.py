"""Clinical record models."""
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from src.models.base import BaseModel
from src.constants import MedicalStatus


@dataclass
class VisitRecord(BaseModel):
    """Visit record model for clinical encounters."""
    visit_id: Optional[int] = None
    appointment_id: int = 0
    doctor_id: int = 0
    visit_date: Optional[date] = None
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = None
    doctor_notes: Optional[str] = None
    follow_up_date: Optional[date] = None
    status: str = "Completed"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    prescriptions: List['Prescription'] = field(default_factory=list)
    reports: List['TestReport'] = field(default_factory=list)

    @property
    def is_completed(self) -> bool:
        """Check if visit is completed."""
        return self.status == "Completed"

    @property
    def has_follow_up(self) -> bool:
        """Check if a follow-up date is set."""
        return self.follow_up_date is not None


@dataclass
class Prescription(BaseModel):
    """Prescription model for medications."""
    prescription_id: Optional[int] = None
    visit_id: int = 0
    medicine_name: str = ""
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None
    created_at: Optional[datetime] = None

    @property
    def display_name(self) -> str:
        """Return display string for the prescription."""
        parts = [self.medicine_name]
        if self.dosage:
            parts.append(self.dosage)
        if self.frequency:
            parts.append(self.frequency)
        return " - ".join(parts)


@dataclass
class TestReport(BaseModel):
    """Test report model for uploaded files."""
    report_id: Optional[int] = None
    visit_id: int = 0
    report_name: str = ""
    file_path: str = ""
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    upload_date: Optional[datetime] = None

    @property
    def display_name(self) -> str:
        """Return display string for the report."""
        return self.report_name

    @property
    def file_size_str(self) -> str:
        """Return formatted file size string."""
        if not self.file_size:
            return "Unknown"
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        return f"{self.file_size / (1024 * 1024):.1f} MB"
