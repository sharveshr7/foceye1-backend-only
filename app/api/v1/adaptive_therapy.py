"""
Adaptive Therapy Difficulty Engine REST Endpoints
Strictly non-diagnostic and rule-based decision-support only.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import UserProfile, get_current_user
from app.schemas.adaptive_therapy_schemas import (
    AdaptiveTherapyConfigBase,
    AdaptiveTherapyConfigCreate,
    AdaptiveTherapyConfigUpdate,
    AdaptiveTherapyConfigResponse,
    TherapyAdaptationRecommendationResponse,
    TherapyAdaptationReviewRequest,
    TherapyAdaptationAuditResponse,
    SessionEvaluationRequest,
)
from app.services.adaptive_therapy_service import AdaptiveTherapyService

router = APIRouter(tags=["Adaptive Therapy Difficulty Engine"])


# ---------------------------------------------------------------------------
# CONFIGURATION ENDPOINTS
# ---------------------------------------------------------------------------

@router.get(
    "/patients/{patient_id}/adaptive-therapy/config",
    response_model=List[AdaptiveTherapyConfigResponse]
)
def get_patient_adaptive_configs(
    patient_id: str,
    exercise_id: Optional[str] = Query(None, description="Filter by exercise ID"),
    user: UserProfile = Depends(get_current_user)
):
    """Retrieve all adaptive therapy difficulty configurations for a patient."""
    configs = AdaptiveTherapyService.get_patient_configs(patient_id)
    if exercise_id:
        configs = [c for c in configs if c.get("exercise_id") == exercise_id]
        if not configs:
            # Auto-initialize default for requested exercise
            default_cfg = AdaptiveTherapyService.get_or_create_config(patient_id, exercise_id, user.full_name or user.id)
            configs = [default_cfg]
    return configs


@router.post(
    "/patients/{patient_id}/adaptive-therapy/config",
    response_model=AdaptiveTherapyConfigResponse,
    status_code=status.HTTP_201_CREATED
)
def create_or_update_adaptive_config(
    patient_id: str,
    payload: AdaptiveTherapyConfigBase,
    user: UserProfile = Depends(get_current_user)
):
    """Create or update clinician-controlled adaptive difficulty parameters."""
    full_payload = AdaptiveTherapyConfigCreate(
        patient_id=patient_id,
        **payload.model_dump()
    )
    return AdaptiveTherapyService.create_config(full_payload, clinician_id=user.full_name or user.id)


@router.patch(
    "/patients/{patient_id}/adaptive-therapy/config/{config_id}",
    response_model=AdaptiveTherapyConfigResponse
)
def update_adaptive_config(
    patient_id: str,
    config_id: str,
    payload: AdaptiveTherapyConfigUpdate,
    user: UserProfile = Depends(get_current_user)
):
    """Update difficulty thresholds, step size, or toggle adaptive mode."""
    return AdaptiveTherapyService.update_config(config_id, payload, clinician_id=user.full_name or user.id)


# ---------------------------------------------------------------------------
# EVALUATION & RECOMMENDATION ENDPOINTS
# ---------------------------------------------------------------------------

@router.post(
    "/patients/{patient_id}/adaptive-therapy/evaluate",
    response_model=Optional[TherapyAdaptationRecommendationResponse]
)
def evaluate_therapy_session(
    patient_id: str,
    payload: SessionEvaluationRequest,
    user: UserProfile = Depends(get_current_user)
):
    """Evaluate a completed session using deterministic rules to generate difficulty recommendation."""
    rec = AdaptiveTherapyService.evaluate_session(payload.therapy_session_id, clinician_id=user.full_name or user.id)
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session evaluation did not produce a recommendation (session may not exist or adaptation is disabled)."
        )
    return rec


@router.get(
    "/patients/{patient_id}/adaptive-therapy/recommendations",
    response_model=List[TherapyAdaptationRecommendationResponse]
)
def get_patient_adaptation_recommendations(
    patient_id: str,
    exercise_id: Optional[str] = Query(None, description="Filter by exercise ID"),
    user: UserProfile = Depends(get_current_user)
):
    """Retrieve history of difficulty adaptation recommendations for a patient."""
    return AdaptiveTherapyService.get_patient_recommendations(patient_id, exercise_id)


@router.get(
    "/patients/{patient_id}/adaptive-therapy/recommendations/latest",
    response_model=Optional[TherapyAdaptationRecommendationResponse]
)
def get_latest_adaptation_recommendation(
    patient_id: str,
    exercise_id: Optional[str] = Query(None, description="Filter by exercise ID"),
    user: UserProfile = Depends(get_current_user)
):
    """Retrieve latest adaptation recommendation for a patient."""
    recs = AdaptiveTherapyService.get_patient_recommendations(patient_id, exercise_id)
    return recs[0] if recs else None


# ---------------------------------------------------------------------------
# CLINICIAN REVIEW & OVERRIDE WORKFLOW
# ---------------------------------------------------------------------------

@router.post(
    "/adaptive-therapy/recommendations/{recommendation_id}/review",
    response_model=TherapyAdaptationRecommendationResponse
)
def review_adaptation_recommendation(
    recommendation_id: str,
    payload: TherapyAdaptationReviewRequest,
    user: UserProfile = Depends(get_current_user)
):
    """Clinician action to approve, reject, or manually override a difficulty recommendation."""
    return AdaptiveTherapyService.review_recommendation(
        recommendation_id=recommendation_id,
        payload=payload,
        clinician_id=user.full_name or user.id
    )


@router.post(
    "/adaptive-therapy/configs/{config_id}/reset",
    response_model=AdaptiveTherapyConfigResponse
)
def reset_difficulty_to_baseline(
    config_id: str,
    notes: Optional[str] = Query(None, description="Optional clinical note for reset"),
    user: UserProfile = Depends(get_current_user)
):
    """Reset difficulty to the clinician-configured starting baseline level."""
    return AdaptiveTherapyService.reset_difficulty(
        config_id=config_id,
        clinician_id=user.full_name or user.id,
        notes=notes
    )


# ---------------------------------------------------------------------------
# AUDIT LOG ENDPOINTS
# ---------------------------------------------------------------------------

@router.get(
    "/patients/{patient_id}/adaptive-therapy/audit",
    response_model=List[TherapyAdaptationAuditResponse]
)
def get_patient_adaptation_audit(
    patient_id: str,
    exercise_id: Optional[str] = Query(None, description="Filter by exercise ID"),
    user: UserProfile = Depends(get_current_user)
):
    """Retrieve full chronological audit trail of all difficulty adaptations and clinician actions."""
    return AdaptiveTherapyService.get_patient_audits(patient_id, exercise_id)
