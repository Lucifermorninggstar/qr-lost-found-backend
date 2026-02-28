from pydantic import BaseModel
from typing import Optional


class LostModeUpdate(BaseModel):
    lost: bool
    note: Optional[str] = None
