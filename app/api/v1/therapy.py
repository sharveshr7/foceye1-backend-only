import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.auth import UserProfile, get_current_user
from app.core.supabase import supabase
from app.schemas.session_schemas import TherapySessionCreate, TherapySessionResponse
from app.services.eye_processor import EyeProcessor

router = APIRouter(prefix="/therapy", tags=["Therapy Sessions"])

CLINICAL_CATEGORIES = [
    {
        "id": "refractive_errors",
        "name": "Refractive & Amblyopia Recovery",
        "description": "Evidence-based exercises targeting contrast sensitivity and neuro-adaptation for amblyopic eyes."
    },
    {
        "id": "binocular_vision",
        "name": "Binocular Coordination & Anti-Suppression",
        "description": "Dichoptic stimulation and stereopsis training to break cortical suppression."
    },
    {
        "id": "oculomotor_training",
        "name": "Oculomotor Saccadic & Pursuit",
        "description": "High-frequency saccadic jumps and smooth pursuit tracking across visual quadrants."
    },
    {
        "id": "vergence_therapy",
        "name": "Convergence Insufficiency (NPC Recovery)",
        "description": "Near point of convergence stepped ramp exercises to restore binocular alignment."
    }
]

CLINICAL_EXERCISES = [
    {
        "id": "saccade-trainer",
        "category_id": "oculomotor_training",
        "title": "Saccadic Speed & Precision Trainer",
        "duration_minutes": 8,
        "difficulty": "Adaptive"
    },
    {
        "id": "pursuit-tracker",
        "category_id": "oculomotor_training",
        "title": "Smooth Pursuit Dynamic Vector",
        "duration_minutes": 6,
        "difficulty": "Adaptive"
    },
    {
        "id": "anti-suppression",
        "category_id": "binocular_vision",
        "title": "Dichoptic Anti-Suppression Flashing",
        "duration_minutes": 10,
        "difficulty": "Moderate"
    },
    {
        "id": "convergence-jump",
        "category_id": "vergence_therapy",
        "title": "Stepped Vergence & NPC Recovery",
        "duration_minutes": 8,
        "difficulty": "Advanced"
    }
]


@router.get("/categories")
async def get_therapy_categories():
    return CLINICAL_CATEGORIES


@router.get("/exercises")
async def get_therapy_exercises():
    return CLINICAL_EXERCISES


@router.get("/sessions", response_model=List[TherapySessionResponse])
async def list_sessions(
    patient_id: Optional[str] = Query(None),
    user: UserProfile = Depends(get_current_user)
):
    res = supabase.table("therapy_sessions").select("*").execute()
    data = res.data or []
    if patient_id:
        data = [s for s in data if s.get("patient_id") == patient_id]
    return data


@router.post("/sessions", response_model=TherapySessionResponse, status_code=status.HTTP_201_CREATED)
async def log_therapy_session(
    session_in: TherapySessionCreate,
    user: UserProfile = Depends(get_current_user)
):
    session_data = session_in.model_dump()
    session_data["id"] = str(uuid.uuid4())
    session_data["created_at"] = datetime.now().isoformat()
    
    # Calculate overall clinical composite score
    overall = (
        session_in.fixation_score * 0.4 +
        session_in.saccadic_score * 0.3 +
        session_in.convergence_score * 0.3
    )
    session_data["overall_score"] = round(overall, 1)

    # Compute BCEA 68% and 95% if gaze points are provided
    if session_in.gaze_points and len(session_in.gaze_points) >= 5:
        gx = [p.x for p in session_in.gaze_points]
        gy = [p.y for p in session_in.gaze_points]
        bcea_68 = EyeProcessor.calculate_bcea(gx, gy, p=0.68)
        bcea_95 = EyeProcessor.calculate_bcea(gx, gy, p=0.95)
        session_data["bcea_68"] = bcea_68["bcea_deg2"]
        session_data["bcea_95"] = bcea_95["bcea_deg2"]

    # Exclude non-database column gaze_points from insertion payload
    insert_payload = {k: v for k, v in session_data.items() if k != "gaze_points"}
    supabase.table("therapy_sessions").insert(insert_payload).execute()
    
    # Update patient last_session date
    try:
        supabase.table("patients").update({
            "last_session": datetime.now().strftime("%Y-%m-%d"),
            "bcea_score": session_data.get("bcea_68", 1.2)
        }).eq("id", session_in.patient_id).execute()
    except Exception:
        pass

    return session_data
