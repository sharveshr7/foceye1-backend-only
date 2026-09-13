from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

VALID_EXERCISE_CATEGORIES = {
    "Fixation Exercise",
    "Smooth Pursuit Exercise",
    "Saccade Exercise",
    "Gaze Accuracy Exercise",
    "General Visual Attention Exercise",
    "Repeat Assessment / Calibration Review",
}

VALID_PRIORITIES = {"low", "moderate", "high", "review_required"}
VALID_DIFFICULTIES = {"beginner", "moderate", "advanced", "not_applicable"}
VALID_REVIEW_STATUSES = {"pending", "approved", "edited", "rejected"}


class SupportingMetric(BaseModel):
    metric: str
    value: float


class DurationRange(BaseModel):
    min: int = 5
    max: int = 10


class TherapyRecommendationItem(BaseModel):
    exercise_category: str
    reason: str
    supporting_metrics: List[SupportingMetric] = Field(default_factory=list)
    suggested_difficulty: str = "beginner"
    suggested_duration_minutes: DurationRange = Field(default_factory=DurationRange)
    priority: str = "moderate"
    confidence: str = "moderate"
    data_quality_note: str = "Based on available session data."
    clinician_review_required: bool = True


class AIRecommendationOutput(BaseModel):
    recommendation_status: str = "completed"
    recommendations: List[TherapyRecommendationItem] = Field(default_factory=list)
    overall_note: str = "The recommendations are suggestions for clinician review and are not automatic prescriptions."
    limitations: List[str] = Field(
        default_factory=lambda: [
            "The recommendation is based strictly on recorded eye-test performance telemetry.",
            "Clinical judgment and clinician approval are required before assigning therapy.",
            "Not a diagnosis or medical treatment prescription."
        ]
    )
    disclaimer: str = "AI-assisted recommendation. Requires clinician review. Not a diagnosis or automatic prescription."


class ClinicianReviewAction(BaseModel):
    action: str  # "approved", "rejected", "pending"
    clinician_notes: Optional[str] = None


class ClinicianEditAction(BaseModel):
    exercise_category: str
    suggested_difficulty: str
    suggested_duration_min: int
    suggested_duration_max: int
    priority: str
    clinician_notes: Optional[str] = None


class TherapyRecommendationResponse(BaseModel):
    id: str
    patient_id: str
    eye_test_session_id: str
    ai_analysis_id: str
    recommendation_status: str
    exercise_category: str
    reason: str
    supporting_metrics_json: List[Dict[str, Any]]
    suggested_difficulty: str
    suggested_duration_min: int
    suggested_duration_max: int
    priority: str
    confidence: str
    data_quality_note: str
    is_simulated_data: bool
    clinician_review_status: str
    clinician_notes: Optional[str] = None
    original_recommendation_json: Optional[Dict[str, Any]] = None
    created_by: Optional[str] = None
    created_at: str
    updated_at: str
    disclaimer: str = "AI-assisted recommendation. Requires clinician review. Not a diagnosis or automatic prescription."
