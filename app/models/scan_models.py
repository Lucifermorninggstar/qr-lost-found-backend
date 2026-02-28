from pydantic import BaseModel
from typing import Optional


class ScanRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    message: Optional[str] = None
