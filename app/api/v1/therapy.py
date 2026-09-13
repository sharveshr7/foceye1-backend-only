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

    # Format language and repetitions into clinical notes for persistent clinical documentation
    lang_code = (session_in.language or "en").upper()
    reps_val = session_in.repetitions or 0
    tag = f"[Lang: {lang_code} | Reps: {reps_val}]"
    if session_data.get("clinical_notes"):
        if tag not in session_data["clinical_notes"]:
            session_data["clinical_notes"] = f"{tag} {session_data['clinical_notes']}".strip()
    else:
        session_data["clinical_notes"] = tag

    # DB columns supported in therapy_sessions
    db_columns = {
        "id", "patient_id", "exercise_type", "duration_seconds",
        "fixation_score", "saccadic_score", "convergence_score",
        "overall_score", "bcea_68", "bcea_95", "language", "repetitions",
        "clinical_notes", "created_at"
    }
    insert_payload = {k: v for k, v in session_data.items() if k in db_columns}
    supabase.table("therapy_sessions").insert(insert_payload).execute()
    
    # Update patient last_session date
    try:
        patient_update = {
            "last_session": datetime.now().strftime("%Y-%m-%d")
        }
        if "bcea_68" in session_data and session_data["bcea_68"] is not None:
            patient_update["bcea_score"] = session_data["bcea_68"]
        supabase.table("patients").update(patient_update).eq("id", session_in.patient_id).execute()
    except Exception:
        pass

    return session_data


# Feature 5: VR Therapy Session Tracking & Performance Recording
from app.schemas.therapy_session_schemas import (
    TherapySessionCreate as VRTherapySessionCreate,
    TherapySessionResponse as VRTherapySessionResponse,
    TherapySessionAction,
    TherapySessionResultCreate,
    TherapySessionResultResponse,
)
from app.services.therapy_session_service import TherapySessionService

therapy_sessions_router = APIRouter(tags=["VR Therapy Sessions"])


@therapy_sessions_router.post("/therapy-sessions", response_model=VRTherapySessionResponse, status_code=status.HTTP_201_CREATED)
async def create_therapy_session(
    payload: VRTherapySessionCreate,
    user: UserProfile = Depends(get_current_user)
):
    return TherapySessionService.create_session(payload, clinician_id=user.full_name or user.id)


@therapy_sessions_router.get("/therapy-sessions/{session_id}", response_model=VRTherapySessionResponse)
async def get_therapy_session(
    session_id: str,
    user: UserProfile = Depends(get_current_user)
):
    return TherapySessionService.get_session(session_id)


@therapy_sessions_router.post("/therapy-sessions/{session_id}/start", response_model=VRTherapySessionResponse)
async def start_therapy_session(
    session_id: str,
    payload: Optional[TherapySessionAction] = None,
    user: UserProfile = Depends(get_current_user)
):
    return TherapySessionService.transition_state(
        session_id=session_id,
        target_status="in_progress",
        actual_duration_seconds=payload.actual_duration_seconds if payload else None
    )


@therapy_sessions_router.post("/therapy-sessions/{session_id}/pause", response_model=VRTherapySessionResponse)
async def pause_therapy_session(
    session_id: str,
    payload: Optional[TherapySessionAction] = None,
    user: UserProfile = Depends(get_current_user)
):
    return TherapySessionService.transition_state(
        session_id=session_id,
        target_status="paused",
        actual_duration_seconds=payload.actual_duration_seconds if payload else None
    )


@therapy_sessions_router.post("/therapy-sessions/{session_id}/resume", response_model=VRTherapySessionResponse)
async def resume_therapy_session(
    session_id: str,
    payload: Optional[TherapySessionAction] = None,
    user: UserProfile = Depends(get_current_user)
):
    return TherapySessionService.transition_state(
        session_id=session_id,
        target_status="in_progress",
        actual_duration_seconds=payload.actual_duration_seconds if payload else None
    )


@therapy_sessions_router.post("/therapy-sessions/{session_id}/complete", response_model=VRTherapySessionResponse)
async def complete_therapy_session(
    session_id: str,
    payload: Optional[TherapySessionAction] = None,
    user: UserProfile = Depends(get_current_user)
):
    return TherapySessionService.transition_state(
        session_id=session_id,
        target_status="completed",
        actual_duration_seconds=payload.actual_duration_seconds if payload else None
    )


@therapy_sessions_router.post("/therapy-sessions/{session_id}/stop", response_model=VRTherapySessionResponse)
async def stop_therapy_session(
    session_id: str,
    payload: Optional[TherapySessionAction] = None,
    user: UserProfile = Depends(get_current_user)
):
    stop_reason = payload.stop_reason if payload else "Session stopped early"
    duration = payload.actual_duration_seconds if payload else None
    return TherapySessionService.transition_state(
        session_id=session_id,
        target_status="stopped",
        actual_duration_seconds=duration,
        stop_reason=stop_reason
    )


@therapy_sessions_router.post("/therapy-sessions/{session_id}/results", response_model=TherapySessionResultResponse, status_code=status.HTTP_201_CREATED)
async def save_therapy_session_result(
    session_id: str,
    payload: TherapySessionResultCreate,
    user: UserProfile = Depends(get_current_user)
):
    return TherapySessionService.save_session_result(session_id, payload)


@therapy_sessions_router.get("/patients/{patient_id}/therapy-sessions", response_model=List[VRTherapySessionResponse])
async def get_patient_therapy_sessions(
    patient_id: str,
    user: UserProfile = Depends(get_current_user)
):
    return TherapySessionService.get_patient_sessions(patient_id)

