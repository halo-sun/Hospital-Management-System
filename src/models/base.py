"""Base model class for all entities."""
from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any, Dict


@dataclass
class BaseModel(ABC):
    """Base class for all models with common fields."""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat() if value else None
            elif hasattr(value, '__dict__'):
                result[key] = value.to_dict() if hasattr(value, 'to_dict') else str(value)
            else:
                result[key] = value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """Create model instance from dictionary."""
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k) or k in cls.__annotations__})