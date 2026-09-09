from datetime import datetime
from typing import List, Optional
import uuid
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
from app.schemas.auth_schemas import (
    AuthResponse,
    PasswordChangeRequest,
    TokenRefreshResponse,
    UserLoginRequest,
    UserSignupRequest
)

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

    user_id = f"user-{uuid.uuid4().hex[:12]}"
    hashed_pwd = hash_password(request.password)
    hosp_name = request.hospital_name or request.clinic_name or "FOCEYE Vision Center"
    
    user_record = {
        "id": user_id,
        "email": email_clean,
        "full_name": request.full_name.strip(),
        "role": request.role,
        "clinic_name": hosp_name,
        "hospital_name": hosp_name,
        "hospital_registration_number": request.hospital_registration_number,
        "hospital_type": request.hospital_type or "Eye Care Center",
        "mobile_number": request.mobile_number,
        "city": request.city,
        "state": request.state,
        "password_hash": hashed_pwd,
        "created_at": datetime.now().isoformat()
    }
    supabase.table("profiles").insert(user_record).execute()

    token = create_access_token({
        "sub": user_id,
        "email": email_clean,
        "role": request.role,
        "full_name": request.full_name.strip(),
        "clinic_name": hosp_name,
        "hospital_name": hosp_name,
        "hospital_registration_number": request.hospital_registration_number,
        "hospital_type": request.hospital_type,
        "mobile_number": request.mobile_number,
        "city": request.city,
        "state": request.state
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
                "id": f"user-{uuid.uuid4().hex[:12]}",
                "email": email_clean,
                "full_name": "Dr. Sarah Smith, OD",
                "role": "clinician",
                "clinic_name": "FOCEYE Ophthalmic Center",
                "hospital_name": "FOCEYE Vision Hospital",
                "hospital_registration_number": "HOSP-REG-2026-001",
                "hospital_type": "Eye Care Center",
                "mobile_number": "+1 (555) 019-2831",
                "city": "Boston",
                "state": "MA",
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
        "clinic_name": user_record.get("clinic_name", "FOCEYE Ophthalmic Center"),
        "hospital_name": user_record.get("hospital_name") or user_record.get("clinic_name", "FOCEYE Vision Hospital"),
        "hospital_registration_number": user_record.get("hospital_registration_number"),
        "hospital_type": user_record.get("hospital_type"),
        "mobile_number": user_record.get("mobile_number"),
        "city": user_record.get("city"),
        "state": user_record.get("state")
    })

    safe_user = {k: v for k, v in user_record.items() if k != "password_hash"}
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=safe_user
    )


@router.post("/change-password")
async def change_password(
    req: PasswordChangeRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    res = supabase.table("profiles").select("*").eq("id", current_user.id).execute()
    if not res.data or len(res.data) == 0:
        # Try matching by email
        res = supabase.table("profiles").select("*").eq("email", current_user.email).execute()

    if not res.data or len(res.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found."
        )

    user_data = res.data[0]
    stored_hash = user_data.get("password_hash")
    if stored_hash and not verify_password(req.current_password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect."
        )

    new_hash = hash_password(req.new_password)
    supabase.table("profiles").update({"password_hash": new_hash}).eq("id", user_data["id"]).execute()
    return {"message": "Password updated successfully."}


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(current_user: UserProfile = Depends(get_current_user)):
    new_token = create_access_token({
        "sub": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "full_name": current_user.full_name,
        "clinic_name": current_user.clinic_name,
        "hospital_name": current_user.hospital_name,
        "hospital_registration_number": current_user.hospital_registration_number,
        "hospital_type": current_user.hospital_type,
        "mobile_number": current_user.mobile_number,
        "city": current_user.city,
        "state": current_user.state
    })
    return TokenRefreshResponse(access_token=new_token, token_type="bearer")


@router.post("/logout")
async def logout(current_user: UserProfile = Depends(get_current_user)):
    return {"message": "Logged out successfully."}



@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(user: UserProfile = Depends(get_current_user)):
    res = supabase.table("profiles").select("*").eq("id", user.id).execute()
    if not res.data or len(res.data) == 0:
        res = supabase.table("profiles").select("*").eq("email", user.email).execute()
    if res.data and len(res.data) > 0:
        p = res.data[0]
        return UserProfile(
            id=p.get("id", user.id),
            email=p.get("email", user.email),
            full_name=p.get("full_name", user.full_name),
            role=p.get("role", user.role),
            clinic_name=p.get("clinic_name", user.clinic_name),
            hospital_name=p.get("hospital_name") or p.get("clinic_name", user.hospital_name),
            hospital_registration_number=p.get("hospital_registration_number", user.hospital_registration_number),
            hospital_type=p.get("hospital_type", user.hospital_type),
            mobile_number=p.get("mobile_number", user.mobile_number),
            city=p.get("city", user.city),
            state=p.get("state", user.state)
        )
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
