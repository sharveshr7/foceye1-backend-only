from fastapi import APIRouter, Depends
from app.core.auth import UserProfile, get_current_user
from app.schemas.ai_schemas import (
    AIInsightRequest,
    AIInsightResponse,
    GeminiHealthResponse,
    TherapyPrescriptionRequest,
    TherapyPrescriptionResponse,
)
from app.services.ai_analyzer import AIAnalyzerService
from app.services.gemini_service import gemini_service

router = APIRouter(prefix="/ai", tags=["AI Clinical Diagnostics"])


@router.get("/gemini-health", response_model=GeminiHealthResponse)
async def gemini_health():
    """
    Dedicated diagnostic endpoint verifying the Google Gemini API connection independently
    from the clinical application flow. Never exposes keys, credentials, or secrets.
    """
    result = await gemini_service.check_health()
    return GeminiHealthResponse(**result)


@router.post("/insights", response_model=AIInsightResponse)
async def generate_insights(
    req: AIInsightRequest,
    user: UserProfile = Depends(get_current_user)
):
    analysis = await AIAnalyzerService.analyze_patient_metrics(
        condition=req.condition,
        age=req.age,
        bcea_score=req.bcea_score,
        fixation_stability=req.fixation_stability,
        saccadic_latency_ms=req.saccadic_latency_ms,
        adherence_rate=req.adherence_rate,
        horizontal_gaze_range_deg=req.horizontal_gaze_range_deg,
        vertical_gaze_range_deg=req.vertical_gaze_range_deg,
        pursuit_gain=req.pursuit_gain,
        blink_rate_bpm=req.blink_rate_bpm,
        incomplete_blink_pct=req.incomplete_blink_pct,
        calibration_accuracy=req.calibration_accuracy,
        total_frames_sampled=req.total_frames_sampled,
        voms_scores=req.voms_scores,
    )
    return AIInsightResponse(**analysis)


@router.post("/therapy-prescription", response_model=TherapyPrescriptionResponse)
async def generate_therapy_prescription(
    req: TherapyPrescriptionRequest,
    user: UserProfile = Depends(get_current_user)
):
    """
    Generates an evidence-based 4-Week Visual Rehabilitation Prescription (VRP)
    and a multilingual Patient Discharge Handout tailored to post-therapy performance metrics.
    """
    prescription = await AIAnalyzerService.generate_therapy_prescription(
        patient_name=req.patient_name or "Patient",
        age=req.age or 30,
        condition=req.condition,
        exercise_name=req.exercise_name or "Target Tracking",
        session_accuracy=req.session_accuracy or 90.0,
        repetitions=req.repetitions or 5,
        pre_fatigue_vas=req.pre_fatigue_vas or 2,
        post_fatigue_vas=req.post_fatigue_vas or 3,
        working_distance_cm=req.working_distance_cm or 45,
        saccadic_latency_ms=req.saccadic_latency_ms or 220.0,
        fixation_stability_pct=req.fixation_stability_pct or 92.0,
        language=req.language or "en",
    )
    return TherapyPrescriptionResponse(**prescription)

