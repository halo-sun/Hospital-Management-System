"""User and role models."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from src.models.base import BaseModel
from src.constants import Role, UserStatus


@dataclass
class RoleModel(BaseModel):
    """Role model."""
    role_id: Optional[int] = None
    role_name: str = ""
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    
    @property
    def is_admin(self) -> bool:
        return self.role_name == Role.ADMIN
    
    @property
    def is_doctor(self) -> bool:
        return self.role_name == Role.DOCTOR
    
    @property
    def is_receptionist(self) -> bool:
        return self.role_name == Role.RECEPTIONIST


@dataclass
class User(BaseModel):
    """User model."""
    user_id: Optional[int] = None
    username: str = ""
    password_hash: str = ""
    role_id: int = 0
    role: Optional[RoleModel] = None
    status: str = UserStatus.ACTIVE
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.role_id and not self.role:
            self.role = RoleModel(role_id=self.role_id)
    
    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE
    
    @property
    def is_locked(self) -> bool:
        if self.locked_until:
            return datetime.now() < self.locked_until
        return False
    
    @property
    def role_name(self) -> str:
        return self.role.role_name if self.role else ""
    
    @property
    def is_admin(self) -> bool:
        return self.role_name == Role.ADMIN
    
    @property
    def is_doctor(self) -> bool:
        return self.role_name == Role.DOCTOR
    
    @property
    def is_receptionist(self) -> bool:
        return self.role_name == Role.RECEPTIONIST
    
    def to_dict(self, include_password: bool = False) -> Dict[str, Any]:
        """Convert to dictionary, optionally excluding password hash."""
        data = super().to_dict()
        if not include_password:
            data.pop('password_hash', None)
        return data