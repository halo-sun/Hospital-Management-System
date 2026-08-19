"""Appointment model."""
from dataclasses import dataclass, field
from datetime import datetime, date, time
from typing import Optional, List, Dict, Any
from src.models.base import BaseModel
from src.constants import AppointmentStatus


@dataclass
class Appointment(BaseModel):
    """Appointment model linking patients to doctors."""
    appointment_id: Optional[int] = None
    patient_id: str = ""
    doctor_id: int = 0
    appointment_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    status: str = AppointmentStatus.BOOKED
    notes: Optional[str] = None
    created_by: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    department_name: Optional[str] = None

    @property
    def is_booked(self) -> bool:
        """Check if appointment is booked."""
        return self.status == AppointmentStatus.BOOKED

    @property
    def is_completed(self) -> bool:
        """Check if appointment is completed."""
        return self.status == AppointmentStatus.COMPLETED

    @property
    def is_cancelled(self) -> bool:
        """Check if appointment is cancelled."""
        return self.status == AppointmentStatus.CANCELLED

    @property
    def is_no_show(self) -> bool:
        """Check if appointment was a no-show."""
        return self.status == AppointmentStatus.NO_SHOW

    @property
    def display_name(self) -> str:
        """Return display string for the appointment."""
        return f"#{self.appointment_id} - {self.patient_name or self.patient_id}"

    @property
    def time_slot(self) -> str:
        """Return formatted time slot string."""
        if self.start_time and self.end_time:
            return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"
        return ""
