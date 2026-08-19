"""Audit log and hospital holiday models."""
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional
from src.models.base import BaseModel


@dataclass
class AuditLog(BaseModel):
    """Audit log model for tracking user actions."""
    log_id: Optional[int] = None
    user_id: Optional[int] = None
    action: str = ""
    target_entity: Optional[str] = None
    target_id: Optional[str] = None
    old_values: Optional[str] = None
    new_values: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: Optional[datetime] = None
    username: Optional[str] = None


@dataclass
class HospitalHoliday(BaseModel):
    """Hospital holiday model."""
    holiday_id: Optional[int] = None
    holiday_date: Optional[date] = None
    holiday_name: str = ""
    description: Optional[str] = None
    is_recurring: bool = False
    created_at: Optional[datetime] = None

    @property
    def display_name(self) -> str:
        """Return display string for the holiday."""
        date_str = self.holiday_date.strftime('%Y-%m-%d') if self.holiday_date else ""
        return f"{self.holiday_name} ({date_str})"
