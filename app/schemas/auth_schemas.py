from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserSignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    full_name: str
    role: str = "clinician"
    clinic_name: Optional[str] = "FOCEYE Vision Center"
    hospital_name: Optional[str] = None
    hospital_registration_number: Optional[str] = None
    hospital_type: Optional[str] = None
    mobile_number: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, description="Password is required")


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(..., min_length=8, description="New password must be at least 8 characters")


class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400


class UserProfileSchema(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    clinic_name: Optional[str] = None
    hospital_name: Optional[str] = None
    hospital_registration_number: Optional[str] = None
    hospital_type: Optional[str] = None
    mobile_number: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

