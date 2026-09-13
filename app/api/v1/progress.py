from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.auth import UserProfile, get_current_user
from app.schemas.progress_schemas import (
    PatientProgressOverview,
    AIProgressSummaryRequest,
    AIProgressSummaryResponse,
    AIProgressSummaryReviewRequest,
    ClinicianProgressNoteCreate,
    ClinicianProgressNoteResponse,
    TimelineItem,
)
from app.services.patient_progress_service import PatientProgressService

router = APIRouter(tags=["Patient Progress & Longitudinal Analytics"])


# 1. Progress Overview Endpoints (Both /overview and root /progress)
@router.get("/patients/{patient_id}/progress", response_model=PatientProgressOverview)
@router.get("/patients/{patient_id}/progress/overview", response_model=PatientProgressOverview)
async def get_patient_progress_overview(
    patient_id: str,
    user: UserProfile = Depends(get_current_user)
):
    """
    Retrieves aggregated longitudinal eye test and therapy session telemetry,
    baseline vs latest comparisons, and data recording reliability for the patient.
    """
    return PatientProgressService.get_patient_progress(patient_id)


# 2. Eye-Test Longitudinal Trends
@router.get("/patients/{patient_id}/progress/eye-tests")
async def get_eye_test_trends(
    patient_id: str,
    user: UserProfile = Depends(get_current_user)
):
    """
    Retrieves longitudinal telemetry curves grouped by eye test type:
    Fixation stability, Smooth pursuit, Saccade assessment, and Gaze accuracy.
    """
    return PatientProgressService.get_eye_test_trends(patient_id)


# 3. Therapy Performance Trends
@router.get("/patients/{patient_id}/progress/therapy-sessions")
async def get_therapy_trends(
    patient_id: str,
    user: UserProfile = Depends(get_current_user)
):
    """
    Retrieves quantitative motor telemetry and exercise logs from completed
    clinical therapy sessions.
    """
    return PatientProgressService.get_therapy_trends(patient_id)


# 4. Patient Progress Timeline
@router.get("/patients/{patient_id}/progress/timeline", response_model=List[TimelineItem])
async def get_patient_timeline(
    patient_id: str,
    user: UserProfile = Depends(get_current_user)
):
    """
    Chronological multi-modality timeline aggregating patient registration,
    eye-test sessions, AI analyses, therapy recommendations and approvals,
    therapy session completion, clinician notes, and progress summaries.
    """
    return PatientProgressService.get_patient_timeline(patient_id)


# 5. Generate AI Progress Summary (Deliberate clinician action)
@router.post("/patients/{patient_id}/progress/ai-summary", response_model=AIProgressSummaryResponse)
async def generate_ai_progress_summary(
    patient_id: str,
    req: AIProgressSummaryRequest = AIProgressSummaryRequest(),
    user: UserProfile = Depends(get_current_user)
):
    """
    Deliberate clinician action: synthesizes recorded longitudinal performance changes
    with strict non-diagnostic and clinical safety guardrails.
    """
    clinician_id = user.id or user.email or "attending_clinician"
    return await PatientProgressService.generate_ai_progress_summary(
        patient_id=patient_id,
        clinician_notes=req.clinician_notes,
        clinician_id=clinician_id
    )


# 6. Get Latest AI Progress Summary
@router.get("/patients/{patient_id}/progress/ai-summary", response_model=Optional[AIProgressSummaryResponse])
async def get_latest_ai_progress_summary(
    patient_id: str,
    user: UserProfile = Depends(get_current_user)
):
    """
    Retrieves the most recent AI progress summary generated for the patient,
    including clinician review status.
    """
    summary = PatientProgressService.get_latest_ai_summary(patient_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No AI progress summary generated yet for patient '{patient_id}'."
        )
    return summary


# 7. Clinician Review of AI Progress Summary
@router.patch("/progress/ai-summaries/{summary_id}/review")
@router.patch("/patients/{patient_id}/progress/ai-summary/{summary_id}/review")
async def review_ai_progress_summary(
    summary_id: str,
    payload: AIProgressSummaryReviewRequest,
    patient_id: Optional[str] = None,
    user: UserProfile = Depends(get_current_user)
):
    """
    Allows authorized clinician to record a review decision on an AI summary:
    'pending', 'reviewed', 'flagged', or 'dismissed', along with audit notes.
    """
    clinician_id = user.id or user.email or "attending_clinician"
    return PatientProgressService.review_ai_summary(
        summary_id=summary_id,
        clinician_id=clinician_id,
        review_status=payload.clinician_review_status,
        clinician_notes=payload.clinician_notes,
    )


# 8. Clinician Progress Notes
@router.get("/patients/{patient_id}/progress/notes", response_model=List[ClinicianProgressNoteResponse])
async def get_clinician_progress_notes(
    patient_id: str,
    user: UserProfile = Depends(get_current_user)
):
    """
    Retrieves longitudinal clinician observation notes for the patient.
    """
    return PatientProgressService.get_clinician_notes(patient_id)


@router.post(
    "/patients/{patient_id}/progress/notes",
    response_model=ClinicianProgressNoteResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_clinician_progress_note(
    patient_id: str,
    payload: ClinicianProgressNoteCreate,
    user: UserProfile = Depends(get_current_user)
):
    """
    Records a longitudinal progress observation or evaluation note from an attending clinician.
    """
    clinician_id = user.id or user.email or "clinician-001"
    clinician_name = user.full_name or "Attending Clinician"
    return PatientProgressService.add_clinician_note(
        patient_id=patient_id,
        clinician_id=clinician_id,
        clinician_name=clinician_name,
        notes=payload.notes,
        related_session_id=payload.related_session_id,
        follow_up_date=payload.follow_up_date,
    )
