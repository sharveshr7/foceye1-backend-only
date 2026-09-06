from fastapi import APIRouter, Depends
from app.core.auth import UserProfile, get_current_user
from app.schemas.ai_schemas import AIInsightRequest, AIInsightResponse
from app.services.ai_analyzer import AIAnalyzerService

router = APIRouter(prefix="/ai", tags=["AI Clinical Diagnostics"])


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
        adherence_rate=req.adherence_rate
    )
    return AIInsightResponse(**analysis)
