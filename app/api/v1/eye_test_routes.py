from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, status
from app.core.auth import UserProfile, get_current_user
from app.schemas.eye_test_schemas import (
    EyeTestResultCreate,
    EyeTestResultResponse,
    EyeTestResultUpdate,
    EyeTestSessionCreate,
    EyeTestSessionResponse,
    StartTestRequest,
)
from app.services.eye_test_service import EyeTestService

from app.schemas.eye_test_ai_schemas import (
    AIAnalysisResponse,
    ClinicianReviewUpdate,
)
from app.services.eye_test_ai_service import EyeTestAIService

from app.schemas.therapy_recommendation_schemas import (
    ClinicianEditAction,
    ClinicianReviewAction,
    TherapyRecommendationResponse,
)
from app.services.therapy_recommendation_service import TherapyRecommendationService

router = APIRouter(prefix="/eye-tests", tags=["Clinical Eye Testing"])
ai_alias_router = APIRouter(tags=["Clinical Eye Testing AI Aliases"])


@router.post("/sessions", response_model=EyeTestSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: EyeTestSessionCreate,
    user: UserProfile = Depends(get_current_user)
):
    clinician = payload.clinician_id or user.full_name
    return EyeTestService.create_session(payload.patient_id, clinician)


@router.get("/sessions/{session_id}", response_model=EyeTestSessionResponse)
async def get_session(
    session_id: str,
    user: UserProfile = Depends(get_current_user)
):
    return EyeTestService.get_session(session_id)


@router.post("/sessions/{session_id}/start-test")
async def start_selected_test(
    session_id: str,
    payload: StartTestRequest,
    user: UserProfile = Depends(get_current_user)
):
    return EyeTestService.start_test(session_id, payload.test_type)


@router.post("/results", response_model=EyeTestResultResponse, status_code=status.HTTP_201_CREATED)
async def save_test_result(
    payload: EyeTestResultCreate,
    user: UserProfile = Depends(get_current_user)
):
    return EyeTestService.save_result(payload.model_dump())


@router.put("/results/{result_id}", response_model=EyeTestResultResponse)
async def update_test_result(
    result_id: str,
    payload: EyeTestResultUpdate,
    user: UserProfile = Depends(get_current_user)
):
    return EyeTestService.update_result(result_id, payload.model_dump())


@router.post("/sessions/{session_id}/complete", response_model=EyeTestSessionResponse)
async def complete_session(
    session_id: str,
    user: UserProfile = Depends(get_current_user)
):
    return EyeTestService.complete_session(session_id)


@router.get("/patients/{patient_id}/sessions", response_model=List[EyeTestSessionResponse])
async def get_patient_sessions(
    patient_id: str,
    user: UserProfile = Depends(get_current_user)
):
    return EyeTestService.get_sessions_for_patient(patient_id)


@router.get("/sessions/{session_id}/results", response_model=List[EyeTestResultResponse])
async def get_session_results(
    session_id: str,
    user: UserProfile = Depends(get_current_user)
):
    return EyeTestService.get_results_for_session(session_id)


@router.get("/patients/{patient_id}/latest-result", response_model=Optional[EyeTestResultResponse])
async def get_patient_latest_result(
    patient_id: str,
    user: UserProfile = Depends(get_current_user)
):
    return EyeTestService.get_latest_result_for_patient(patient_id)


# AI-Assisted Eye Test Analysis Endpoints
@router.post("/sessions/{session_id}/ai-analysis", response_model=AIAnalysisResponse, status_code=status.HTTP_201_CREATED)
@router.post("/sessions/{session_id}/analyze", response_model=AIAnalysisResponse, status_code=status.HTTP_201_CREATED)
@ai_alias_router.post("/eye-test-sessions/{session_id}/ai-analysis", response_model=AIAnalysisResponse, status_code=status.HTTP_201_CREATED)
@ai_alias_router.post("/eye-test-sessions/{session_id}/analyze", response_model=AIAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def analyze_session(
    session_id: str,
    user: UserProfile = Depends(get_current_user)
):
    return await EyeTestAIService.analyze_session(session_id, requesting_user_id=user.id)


@router.get("/sessions/{session_id}/ai-analysis", response_model=Optional[AIAnalysisResponse])
@ai_alias_router.get("/eye-test-sessions/{session_id}/ai-analysis", response_model=Optional[AIAnalysisResponse])
async def get_session_ai_analysis(
    session_id: str,
    user: UserProfile = Depends(get_current_user)
):
    return EyeTestAIService.get_session_analysis(session_id)


@router.get("/patients/{patient_id}/ai-analyses", response_model=List[AIAnalysisResponse])
@ai_alias_router.get("/patients/{patient_id}/ai-analyses", response_model=List[AIAnalysisResponse])
async def get_patient_ai_analyses(
    patient_id: str,
    user: UserProfile = Depends(get_current_user)
):
    return EyeTestAIService.get_patient_analyses(patient_id)


@router.patch("/ai-analyses/{analysis_id}/review", response_model=AIAnalysisResponse)
@ai_alias_router.patch("/ai-analyses/{analysis_id}/review", response_model=AIAnalysisResponse)
async def update_clinician_review(
    analysis_id: str,
    payload: ClinicianReviewUpdate,
    user: UserProfile = Depends(get_current_user)
):
    return EyeTestAIService.update_clinician_review(
        analysis_id,
        payload.clinician_review_status,
        payload.clinician_notes
    )


# AI-Assisted Therapy Recommendation Endpoints
@router.post(
    "/sessions/{session_id}/therapy-recommendations",
    response_model=TherapyRecommendationResponse,
    status_code=status.HTTP_201_CREATED
)
@router.post(
    "/sessions/{session_id}/recommend-therapy",
    response_model=TherapyRecommendationResponse,
    status_code=status.HTTP_201_CREATED
)
@ai_alias_router.post(
    "/eye-test-sessions/{session_id}/therapy-recommendations",
    response_model=TherapyRecommendationResponse,
    status_code=status.HTTP_201_CREATED
)
@ai_alias_router.post(
    "/eye-test-sessions/{session_id}/recommend-therapy",
    response_model=TherapyRecommendationResponse,
    status_code=status.HTTP_201_CREATED
)
async def generate_therapy_recommendation(
    session_id: str,
    user: UserProfile = Depends(get_current_user)
):
    return await TherapyRecommendationService.generate_recommendation(
        session_id=session_id,
        clinician_id=user.full_name or user.id
    )


@router.get(
    "/sessions/{session_id}/therapy-recommendations",
    response_model=List[TherapyRecommendationResponse]
)
@ai_alias_router.get(
    "/eye-test-sessions/{session_id}/therapy-recommendations",
    response_model=List[TherapyRecommendationResponse]
)
async def get_session_therapy_recommendations(
    session_id: str,
    user: UserProfile = Depends(get_current_user)
):
    return TherapyRecommendationService.get_session_recommendations(session_id)


@router.get(
    "/patients/{patient_id}/therapy-recommendations",
    response_model=List[TherapyRecommendationResponse]
)
@ai_alias_router.get(
    "/patients/{patient_id}/therapy-recommendations",
    response_model=List[TherapyRecommendationResponse]
)
async def get_patient_therapy_recommendations(
    patient_id: str,
    user: UserProfile = Depends(get_current_user)
):
    return TherapyRecommendationService.get_patient_recommendations(patient_id)


@router.post(
    "/therapy-recommendations/{recommendation_id}/review",
    response_model=TherapyRecommendationResponse
)
@router.patch(
    "/therapy-recommendations/{recommendation_id}/review",
    response_model=TherapyRecommendationResponse
)
@ai_alias_router.post(
    "/therapy-recommendations/{recommendation_id}/review",
    response_model=TherapyRecommendationResponse
)
@ai_alias_router.patch(
    "/therapy-recommendations/{recommendation_id}/review",
    response_model=TherapyRecommendationResponse
)
async def review_therapy_recommendation(
    recommendation_id: str,
    payload: ClinicianReviewAction,
    user: UserProfile = Depends(get_current_user)
):
    notes = payload.clinician_notes or payload.notes
    return TherapyRecommendationService.review_recommendation(
        recommendation_id=recommendation_id,
        action=payload.action,
        notes=notes,
        clinician_name=user.full_name or user.id
    )


@router.patch(
    "/therapy-recommendations/{recommendation_id}",
    response_model=TherapyRecommendationResponse
)
@ai_alias_router.patch(
    "/therapy-recommendations/{recommendation_id}",
    response_model=TherapyRecommendationResponse
)
async def edit_therapy_recommendation(
    recommendation_id: str,
    payload: ClinicianEditAction,
    user: UserProfile = Depends(get_current_user)
):
    return TherapyRecommendationService.edit_recommendation(
        recommendation_id=recommendation_id,
        edits=payload.model_dump(),
        clinician_name=user.full_name or user.id
    )

