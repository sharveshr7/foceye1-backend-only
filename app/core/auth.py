import datetime
from typing import List, Optional
import uuid
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from app.core.config import settings

security = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    sub: str
    email: str
    role: str = "clinician"
    hospital_name: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None
    jti: Optional[str] = None


class UserProfile(BaseModel):
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


def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.datetime.now(datetime.timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + datetime.timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4())
    })
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt



def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )


import bcrypt

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))
    except Exception:
        return False


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserProfile:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided. Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject identity.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email = payload.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user email.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    role = payload.get("role", "clinician")
    full_name = payload.get("full_name") or email.split("@")[0]
    clinic_name = payload.get("clinic_name")
    hospital_name = payload.get("hospital_name") or clinic_name
    hospital_registration_number = payload.get("hospital_registration_number")
    hospital_type = payload.get("hospital_type")
    mobile_number = payload.get("mobile_number")
    city = payload.get("city")
    state = payload.get("state")
    
    return UserProfile(
        id=user_id,
        email=email,
        full_name=full_name,
        role=role,
        clinic_name=clinic_name,
        hospital_name=hospital_name,
        hospital_registration_number=hospital_registration_number,
        hospital_type=hospital_type,
        mobile_number=mobile_number,
        city=city,
        state=state
    )


def require_role(allowed_roles: List[str]):
    def role_checker(current_user: UserProfile = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker
