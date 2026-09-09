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
    voms_scores: Optional[Dict[str, Any]] = None


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


class GeminiHealthResponse(BaseModel):
    success: bool
    gemini_configured: bool
    gemini_working: bool
    message: str
    model: Optional[str] = None
    error_type: Optional[str] = None


class WeeklyRegimenItem(BaseModel):
    week: int
    focus_goal: str
    daily_frequency: str
    target_duration_mins: int
    target_velocity: str
    instructions: str


class HomeDischargeHandout(BaseModel):
    title: str
    greeting: str
    instructions: List[str]
    ergonomic_and_hygiene_tips: List[str]
    red_flag_symptoms: List[str]
    follow_up_schedule: str


class TherapyPrescriptionRequest(BaseModel):
    patient_id: Optional[str] = None
    patient_name: Optional[str] = "Patient"
    age: Optional[int] = 30
    condition: str = "Convergence Insufficiency"
    exercise_id: Optional[str] = "target-tracking"
    exercise_name: Optional[str] = "Target Tracking"
    session_accuracy: Optional[float] = 90.0
    repetitions: Optional[int] = 5
    pre_fatigue_vas: Optional[int] = 2
    post_fatigue_vas: Optional[int] = 3
    working_distance_cm: Optional[int] = 45
    saccadic_latency_ms: Optional[float] = 220.0
    fixation_stability_pct: Optional[float] = 92.0
    language: Optional[str] = "en"  # "en", "ta", "ml", "te", "hi"


class TherapyPrescriptionResponse(BaseModel):
    success: bool
    patient_name: str
    condition: str
    language: str
    clinical_rationale: str
    weekly_regimen: List[WeeklyRegimenItem]
    home_discharge_handout: HomeDischargeHandout
    source: str = "Google Gemini Clinical Vision Engine"
    model: Optional[str] = None

