from typing import List, Optional, Dict, Any
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
    horizontal_gaze_range_deg: Optional[float] = None
    vertical_gaze_range_deg: Optional[float] = None
    pursuit_gain: Optional[float] = None
    blink_rate_bpm: Optional[float] = None
    incomplete_blink_pct: Optional[float] = None
    calibration_accuracy: Optional[float] = None
    total_frames_sampled: Optional[int] = None


class AIInsightResponse(BaseModel):
    summary: str
    risk_level: str  # Low, Moderate, High
    biomarkers: List[Dict[str, Any]]
    recommended_protocols: List[str]
    confidence_score: float
    source: str
    observed_findings: Optional[List[str]] = []
    possible_concerns: Optional[List[str]] = []
    recommendations: Optional[List[str]] = []
    data_sufficiency: Optional[str] = "Sufficient"
    confidence_quality_indicator: Optional[str] = "High Data Confidence"
