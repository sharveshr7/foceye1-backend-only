import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.auth import UserProfile, get_current_user, require_role
from app.core.supabase import supabase
from app.schemas.patient_schemas import PatientCreate, PatientResponse, PatientUpdate

router = APIRouter(prefix="/patients", tags=["Patients EMR"])


@router.get("", response_model=List[PatientResponse])
async def list_patients(
    search: Optional[str] = Query(None, description="Search by name or condition"),
    user: UserProfile = Depends(get_current_user)
):
    res = supabase.table("patients").select("*").execute()
    data = res.data or []
    if search:
        s = search.lower()
        data = [
            p for p in data 
            if s in p.get("name", "").lower() or s in p.get("condition", "").lower()
        ]
    return data


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: str, user: UserProfile = Depends(get_current_user)):
    res = supabase.table("patients").select("*").eq("id", patient_id).execute()
    if not res.data or len(res.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found"
        )
    return res.data[0]


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient_in: PatientCreate,
    user: UserProfile = Depends(require_role(["clinician", "admin", "therapist"]))
):
    patient_dict = patient_in.model_dump()
    patient_dict["id"] = str(uuid.uuid4())
    patient_dict["created_at"] = datetime.now().isoformat()
    patient_dict["last_session"] = datetime.now().strftime("%Y-%m-%d")

    res = supabase.table("patients").insert(patient_dict).execute()
    return patient_dict


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str,
    patient_update: PatientUpdate,
    user: UserProfile = Depends(require_role(["clinician", "admin", "therapist"]))
):
    update_data = {k: v for k, v in patient_update.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    supabase.table("patients").update(update_data).eq("id", patient_id).execute()
    # Fetch updated
    updated = supabase.table("patients").select("*").eq("id", patient_id).execute()
    if not updated.data:
        raise HTTPException(status_code=404, detail="Patient not found")
    return updated.data[0]


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: str,
    user: UserProfile = Depends(require_role(["clinician", "admin"]))
):
    supabase.table("patients").delete().eq("id", patient_id).execute()
    return None
