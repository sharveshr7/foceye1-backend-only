from typing import List, Optional
from pydantic import BaseModel


class AIInsightRequest(BaseModel):
    patient_id: Optional[str] = None
    condition: str
    age: int
    bcea_score: float
    fixation_stability: float
    saccadic_latency_ms: float
    adherence_rate: float
    recent_session_scores: Optional[List[float]] = []


class AIInsightResponse(BaseModel):
    summary: str
    risk_level: str # Low, Moderate, High
    biomarkers: List[dict]
    recommended_protocols: List[str]
    confidence_score: float
    source: str # "gemini-1.5-flash" or "clinical-heuristic-engine"
