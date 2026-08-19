"""Doctor and department models."""
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Optional, List, Dict, Any
from src.models.base import BaseModel
from src.constants import DoctorStatus


@dataclass
class Department(BaseModel):
    """Department model."""
    department_id: Optional[int] = None
    department_name: str = ""
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    doctor_count: int = 0


@dataclass
class DoctorSchedule(BaseModel):
    """Doctor weekly schedule model."""
    schedule_id: Optional[int] = None
    doctor_id: int = 0
    day_of_week: int = 0  # 0=Sunday, 6=Saturday
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    is_available: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @property
    def day_name(self) -> str:
        days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        return days[self.day_of_week] if 0 <= self.day_of_week <= 6 else "Unknown"


@dataclass
class DoctorLeave(BaseModel):
    """Doctor leave model."""
    leave_id: Optional[int] = None
    doctor_id: int = 0
    leave_start_date: Optional[datetime] = None
    leave_end_date: Optional[datetime] = None
    reason: Optional[str] = None
    status: str = "Approved"
    created_at: Optional[datetime] = None
    
    def is_on_leave(self, check_date: datetime.date) -> bool:
        """Check if doctor is on leave on a specific date."""
        if self.leave_start_date and self.leave_end_date:
            start = self.leave_start_date.date() if isinstance(self.leave_start_date, datetime) else self.leave_start_date
            end = self.leave_end_date.date() if isinstance(self.leave_end_date, datetime) else self.leave_end_date
            return start <= check_date <= end
        return False


@dataclass
class Doctor(BaseModel):
    """Doctor model."""
    doctor_id: Optional[int] = None
    user_id: Optional[int] = None
    department_id: int = 0
    department: Optional[Department] = None
    full_name: str = ""
    specialization: Optional[str] = None
    contact_number: Optional[str] = None
    email: Optional[str] = None
    qualification: Optional[str] = None
    experience_years: int = 0
    working_hours_start: Optional[time] = None
    working_hours_end: Optional[time] = None
    lunch_break_start: Optional[time] = None
    lunch_break_end: Optional[time] = None
    max_appointments_per_day: int = 20
    consultation_fee: float = 0.0
    status: str = DoctorStatus.ACTIVE
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    schedules: List[DoctorSchedule] = field(default_factory=list)
    leaves: List[DoctorLeave] = field(default_factory=list)
    user: Optional['User'] = None
    
    @property
    def is_active(self) -> bool:
        return self.status == DoctorStatus.ACTIVE
    
    @property
    def is_on_leave(self) -> bool:
        return self.status == DoctorStatus.ON_LEAVE
    
    @property
    def display_name(self) -> str:
        title = "Dr." if self.full_name and not self.full_name.startswith("Dr.") else ""
        return f"{title}{self.full_name}"
    
    @property
    def department_name(self) -> str:
        return self.department.department_name if self.department else ""


# Import User here to avoid circular import
from src.models.user import User