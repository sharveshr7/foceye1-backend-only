from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserSignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    full_name: str
    role: str = "clinician"
    clinic_name: Optional[str] = "FOCEYE Vision Center"


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, description="Password is required")


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict
