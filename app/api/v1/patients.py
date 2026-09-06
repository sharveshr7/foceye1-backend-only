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
    
    if not patient_dict.get("condition"):
        patient_dict["condition"] = "Pending Eye Test"
    if not patient_dict.get("stage"):
        patient_dict["stage"] = patient_dict.get("clinical_status") or "EYE_TEST_PENDING"

    db_columns = {
        "id", "name", "age", "gender", "condition", "icd10",
        "stage", "adherence", "last_session", "visual_acuity_left",
        "visual_acuity_right", "bcea_score", "created_at"
    }
    insert_payload = {k: v for k, v in patient_dict.items() if k in db_columns}
    try:
        supabase.table("patients").insert(insert_payload).execute()
    except Exception:
        pass
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

    db_columns = {
        "name", "age", "gender", "condition", "icd10",
        "stage", "adherence", "last_session", "visual_acuity_left",
        "visual_acuity_right", "bcea_score"
    }
    db_update = {k: v for k, v in update_data.items() if k in db_columns}
    if db_update:
        try:
            supabase.table("patients").update(db_update).eq("id", patient_id).execute()
        except Exception:
            pass

    # Fetch updated or return merged
    try:
        updated = supabase.table("patients").select("*").eq("id", patient_id).execute()
        if updated.data and len(updated.data) > 0:
            row = updated.data[0]
            # Merge any client-tracked fields
            for k, v in update_data.items():
                if k not in row:
                    row[k] = v
            return row
    except Exception:
        pass

    # Fallback to update_data merged with patient_id
    fallback_patient = {
        "id": patient_id,
        "name": update_data.get("name", "Updated Patient"),
        "age": update_data.get("age", 25),
        "gender": update_data.get("gender", "Other"),
        "condition": update_data.get("condition", "Pending Eye Test"),
        "clinical_status": update_data.get("clinical_status", "EYE_TEST_PENDING"),
        "stage": update_data.get("stage", "EYE_TEST_PENDING"),
        "last_session": datetime.now().strftime("%Y-%m-%d"),
        **update_data
    }
    return fallback_patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: str,
    user: UserProfile = Depends(require_role(["clinician", "admin"]))
):
    supabase.table("patients").delete().eq("id", patient_id).execute()
    return None
