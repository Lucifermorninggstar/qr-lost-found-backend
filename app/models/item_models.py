from pydantic import BaseModel
from typing import Optional


class ItemCreate(BaseModel):
    name: str              # Bike / Car / Bag
    description: Optional[str] = None
    show_phone: bool = False
    show_email: bool = False


class ItemResponse(BaseModel):
    id: str
    name: str
    qr_token: str
    status: str
