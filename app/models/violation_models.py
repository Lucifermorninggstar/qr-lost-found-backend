from pydantic import BaseModel
from typing import Optional
from enum import Enum


class ViolationType(str, Enum):
    NO_PARKING = "NO_PARKING"
    BLOCKING = "BLOCKING"
    GENERAL = "GENERAL"


class ViolationCreate(BaseModel):
    type: ViolationType
    message: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
