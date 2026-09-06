from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from app.core.auth import (
    UserProfile,
    create_access_token,
    get_current_user,
    hash_password,
    require_role,
    verify_password
)
from app.core.supabase import supabase
from app.schemas.auth_schemas import AuthResponse, UserLoginRequest, UserSignupRequest

router = APIRouter(prefix="/auth", tags=["Authentication & Clinical Staff"])


class StaffCreateRequest(BaseModel):
    name: str
    email: EmailStr
    role: str = "therapist"
    department: Optional[str] = "Vision Therapy"
    phone: Optional[str] = None


@router.post("/signup", response_model=AuthResponse)
async def signup(request: UserSignupRequest):
    email_clean = str(request.email).strip().lower()
    
    # Check if user exists in profiles
    existing = supabase.table("profiles").select("*").eq("email", email_clean).execute()
    if existing.data and len(existing.data) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists. Please log in instead."
        )

    user_id = f"user-{email_clean.split('@')[0]}"
    hashed_pwd = hash_password(request.password)
    clinic = request.clinic_name or "FOCEYE Vision Center"
    
    user_record = {
        "id": user_id,
        "email": email_clean,
        "full_name": request.full_name.strip(),
        "role": request.role,
        "clinic_name": clinic,
        "password_hash": hashed_pwd,
        "created_at": datetime.now().isoformat()
    }
    supabase.table("profiles").insert(user_record).execute()

    token = create_access_token({
        "sub": user_id,
        "email": email_clean,
        "role": request.role,
        "full_name": request.full_name.strip(),
        "clinic_name": clinic
    })

    safe_user = {k: v for k, v in user_record.items() if k != "password_hash"}
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=safe_user
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: UserLoginRequest):
    email_clean = str(request.email).strip().lower()
    res = supabase.table("profiles").select("*").eq("email", email_clean).execute()
    
    user_record = None
    if res.data and len(res.data) > 0:
        user_record = res.data[0]
        # Verify password if hash exists
        stored_hash = user_record.get("password_hash")
        if stored_hash:
            if not verify_password(request.password, stored_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password. Please verify your credentials."
                )
        else:
            # Upgrade legacy record with hashed password
            new_hash = hash_password(request.password)
            supabase.table("profiles").update({"password_hash": new_hash}).eq("id", user_record["id"]).execute()
    else:
        # Default clinic accounts provisioned for initial station login
        if email_clean in ["dr.smith@foceye.clinic", "admin@foceye.clinic", "clinician@foceye.clinic"]:
            hashed_pwd = hash_password(request.password)
            user_record = {
                "id": f"user-{email_clean.split('@')[0]}",
                "email": email_clean,
                "full_name": "Dr. Sarah Smith, OD",
                "role": "clinician",
                "clinic_name": "FOCEYE Ophthalmic Center",
                "password_hash": hashed_pwd,
                "created_at": datetime.now().isoformat()
            }
            supabase.table("profiles").insert(user_record).execute()
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid clinician credentials. No account registered with this email."
            )

    token = create_access_token({
        "sub": user_record["id"],
        "email": user_record["email"],
        "role": user_record.get("role", "clinician"),
        "full_name": user_record.get("full_name", "Clinical Specialist"),
        "clinic_name": user_record.get("clinic_name", "FOCEYE Ophthalmic Center")
    })

    safe_user = {k: v for k, v in user_record.items() if k != "password_hash"}
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=safe_user
    )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(user: UserProfile = Depends(get_current_user)):
    return user


@router.get("/staff")
async def list_staff_members(user: UserProfile = Depends(get_current_user)):
    res = supabase.table("profiles").select("*").execute()
    profiles = res.data or []
    staff_list = []
    for p in profiles:
        staff_list.append({
            "id": p.get("id"),
            "hospitalId": "hosp-foceye-main",
            "name": p.get("full_name", "Staff Member"),
            "email": p.get("email"),
            "role": "DOCTOR" if p.get("role") == "clinician" else "THERAPIST",
            "department": p.get("clinic_name", "Vision Therapy"),
            "phone": "+1 (555) 012-3456",
            "status": "ACTIVE",
            "assignedPatientsCount": 4,
            "joinDate": p.get("created_at", "2026-01-01").split("T")[0]
        })
    return staff_list


@router.post("/staff")
async def create_staff_member(
    staff_in: StaffCreateRequest,
    user: UserProfile = Depends(require_role(["clinician", "admin"]))
):
    email_clean = str(staff_in.email).strip().lower()
    user_id = f"user-{email_clean.split('@')[0]}"
    record = {
        "id": user_id,
        "email": email_clean,
        "full_name": staff_in.name,
        "role": "clinician" if staff_in.role.lower() in ["doctor", "clinician"] else "therapist",
        "clinic_name": staff_in.department or "Vision Therapy",
        "created_at": datetime.now().isoformat()
    }
    supabase.table("profiles").upsert(record).execute()
    return {
        "id": user_id,
        "name": staff_in.name,
        "email": email_clean,
        "role": "DOCTOR" if record["role"] == "clinician" else "THERAPIST",
        "department": record["clinic_name"],
        "status": "ACTIVE"
    }


@router.delete("/staff/{staff_id}")
async def remove_staff_member(
    staff_id: str,
    user: UserProfile = Depends(require_role(["clinician", "admin"]))
):
    supabase.table("profiles").delete().eq("id", staff_id).execute()
    return {"status": "deleted", "id": staff_id}
