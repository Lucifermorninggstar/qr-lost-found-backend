# from pydantic import BaseModel, EmailStr, Field
# from typing import Optional
# from fastapi import Form


# class UserCreate(BaseModel):
#     name: str
#     email: EmailStr
#     mobile_number: str = Field(..., min_length=10, max_length=15)
#     password: str
#     date_of_birth: str = Form(None),
#     address:       str = Form(None),
#     city:          str = Form(None),
#     state:         str = Form(None),
#     pincode:       str = Form(None),



# class UserLogin(BaseModel):
#     email: EmailStr
#     password: str

# class UserResponse(BaseModel):
#     id: str
#     name: str
#     email: EmailStr


# app/models/user_models.py
from pydantic import BaseModel, EmailStr
from typing import Optional


# ── Used for JSON body login ──────────────────────────────────
class UserLogin(BaseModel):
    email:    EmailStr
    password: str


# ── Used for FormData signup (photo upload support) ───────────
# Note: This is NOT a Pydantic model — fields are extracted
# directly as Form() params in the router. See auth.py router.


# ── Response shape ────────────────────────────────────────────
class UserResponse(BaseModel):
    id:    str
    name:  str
    email: EmailStr