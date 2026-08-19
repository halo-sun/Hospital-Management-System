"""Department model."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.models.base import BaseModel


@dataclass
class Department(BaseModel):
    """Hospital department / speciality unit.

    Maps to the ``departments`` table (ARCHITECTURE.md §4): a
    department has a unique name and an optional description.  Doctors
    reference a department via ``doctors.department_id``.
    """

    department_id: Optional[int] = None
    department_name: str = ""
    description: Optional[str] = None
    doctor_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def display_name(self) -> str:
        """Return the display name of the department."""
        return self.department_name
