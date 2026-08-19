"""Patient model."""
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from src.models.base import BaseModel
from src.constants import Gender, MedicalStatus


@dataclass
class Patient(BaseModel):
    """Patient model."""
    patient_id: str = ""
    full_name: str = ""
    date_of_birth: Optional[date] = None
    gender: str = ""
    contact_number: str = ""
    email: Optional[str] = None
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_number: Optional[str] = None
    blood_group: Optional[str] = None
    allergies: Optional[str] = None
    registered_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    medical_history: List['MedicalHistory'] = field(default_factory=list)
    documents: List['PatientDocument'] = field(default_factory=list)
    
    @property
    def age(self) -> Optional[int]:
        if self.date_of_birth:
            today = date.today()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
    
    @property
    def display_name(self) -> str:
        return f"{self.patient_id} - {self.full_name}"
    
    @property
    def is_male(self) -> bool:
        return self.gender == Gender.MALE
    
    @property
    def is_female(self) -> bool:
        return self.gender == Gender.FEMALE


@dataclass
class MedicalHistory(BaseModel):
    """Medical history model."""
    history_id: Optional[int] = None
    patient_id: str = ""
    condition_name: str = ""
    description: Optional[str] = None
    diagnosed_date: Optional[date] = None
    status: str = MedicalStatus.ACTIVE
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @property
    def is_active(self) -> bool:
        return self.status == MedicalStatus.ACTIVE
    
    @property
    def is_resolved(self) -> bool:
        return self.status == MedicalStatus.RESOLVED
    
    @property
    def is_chronic(self) -> bool:
        return self.status == MedicalStatus.CHRONIC


@dataclass
class PatientDocument(BaseModel):
    """Patient document model."""
    document_id: Optional[int] = None
    patient_id: str = ""
    document_name: str = ""
    file_path: str = ""
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_by: Optional[int] = None
    upload_date: Optional[datetime] = None