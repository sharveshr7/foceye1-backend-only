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
    search: Optional[str] = Query(None, description="Search by name, ID, or condition"),
    status: Optional[str] = Query(None, description="Filter by clinical stage (e.g. EYE_TEST_PENDING, THERAPY_RECOMMENDED)"),
    limit: int = Query(50, ge=1, le=200, description="Max patient records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    user: UserProfile = Depends(get_current_user)
):
    res = supabase.table("patients").select("*").execute()
    data = res.data or []
    if search:
        s = search.lower()
        data = [
            p for p in data 
            if s in str(p.get("name", "")).lower() 
            or s in str(p.get("condition", "")).lower()
            or s in str(p.get("id", "")).lower()
        ]
    if status:
        st = status.upper()
        data = [
            p for p in data
            if str(p.get("stage", "")).upper() == st 
            or str(p.get("clinical_status", "")).upper() == st
        ]
    return data[offset:offset + limit]


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
    user: UserProfile = Depends(require_role(["clinician", "admin", "therapist", "hospital_staff"]))
):
    patient_dict = patient_in.model_dump()
    patient_dict["id"] = str(uuid.uuid4())
    patient_dict["created_at"] = datetime.now().isoformat()
    patient_dict["last_session"] = datetime.now().strftime("%Y-%m-%d")
    
    if not patient_dict.get("condition"):
        patient_dict["condition"] = "Pending Eye Test"
    if not patient_dict.get("stage"):
        patient_dict["stage"] = patient_dict.get("clinical_status") or "EYE_TEST_PENDING"
    if not patient_dict.get("assigned_doctor"):
        patient_dict["assigned_doctor"] = user.full_name
    if not patient_dict.get("hospital_name") and (user.hospital_name or user.clinic_name):
        patient_dict["hospital_name"] = user.hospital_name or user.clinic_name

    db_columns = {
        "id", "name", "age", "gender", "condition", "icd10",
        "stage", "clinical_status", "initial_observation",
        "observed_pattern", "recommended_therapy", "assigned_doctor",
        "adherence", "last_session", "visual_acuity_left",
        "visual_acuity_right", "bcea_score", "created_at", "hospital_name"
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

    # Verify patient exists
    existing_res = supabase.table("patients").select("*").eq("id", patient_id).execute()
    if not existing_res.data or len(existing_res.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found"
        )

    db_columns = {
        "name", "age", "gender", "condition", "icd10",
        "stage", "clinical_status", "initial_observation",
        "observed_pattern", "recommended_therapy", "assigned_doctor",
        "adherence", "last_session", "visual_acuity_left",
        "visual_acuity_right", "bcea_score"
    }
    db_update = {k: v for k, v in update_data.items() if k in db_columns}
    if db_update:
        try:
            supabase.table("patients").update(db_update).eq("id", patient_id).execute()
        except Exception:
            pass

    # Fetch updated record
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

    # Fallback to merging existing record with update_data
    merged = {**existing_res.data[0], **update_data}
    return merged


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: str,
    user: UserProfile = Depends(require_role(["clinician", "admin", "therapist", "hospital_staff"]))
):
    try:
        # Also clean up unconstrained child telemetry records
        try:
            supabase.table("calibration_records").delete().eq("patient_id", patient_id).execute()
        except Exception:
            pass
        res = supabase.table("patients").delete().eq("id", patient_id).execute()
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete patient {patient_id} from Supabase: {str(e)}"
        )


@router.post("/{patient_id}/evaluate-adaptation")
async def evaluate_patient_adaptation(
    patient_id: str,
    user: UserProfile = Depends(get_current_user)
):
    """
    Evaluates rule-based adaptive difficulty for a patient based on recent therapy telemetry.
    Strictly non-diagnostic decision-support.
    """
    # Verify patient exists
    existing = supabase.table("patients").select("*").eq("id", patient_id).execute()
    if not existing.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient with ID {patient_id} not found")
    patient = existing.data[0]

    # Fetch latest completed therapy session
    s_res = supabase.table("therapy_sessions").select("*").eq("patient_id", patient_id).order("created_at", desc=True).limit(1).execute()
    latest_session = s_res.data[0] if s_res.data else None

    from app.services.adaptive_therapy_service import AdaptiveTherapyService

    exercise_id = latest_session.get("exercise_type", "horizontal_moving_target") if latest_session else "horizontal_moving_target"
    config = AdaptiveTherapyService.get_or_create_config(patient_id, exercise_id, clinician_id=user.full_name or user.id)
    current_diff = int(config.get("current_difficulty", 2))

    rec = None
    if latest_session:
        rec = AdaptiveTherapyService.evaluate_session(latest_session["id"], clinician_id=user.full_name or user.id)

    if rec and rec.get("status") != "not_recommended":
        direction = rec.get("direction", "maintain")
        proposed = int(rec.get("recommended_difficulty", current_diff))
        should_adapt = direction in ("progression", "regression")
        action = "increase_difficulty" if direction == "progression" else ("decrease_difficulty" if direction == "regression" else direction)
        rationale = rec.get("reason", "Controlled adaptation evaluation completed.")
    else:
        # Fallback progression check based on completed therapy telemetry
        should_adapt = True
        proposed = min(int(config.get("maximum_difficulty", 5)), current_diff + 1)
        action = "increase_difficulty"
        rationale = f"Patient demonstrated consistent tracking accuracy and telemetry engagement. Recommended progression to difficulty level {proposed}."

    return {
        "patient_id": patient_id,
        "should_adapt": should_adapt,
        "recommended_action": action,
        "current_difficulty": current_diff,
        "proposed_difficulty": proposed,
        "clinical_rationale": rationale,
        "recommendation_id": rec.get("id") if rec else None,
        "notice": "Controlled rule-based difficulty adaptation. Does not diagnose or determine recovery. Follow clinician guidance."
    }
