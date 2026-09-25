from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

VALID_EXERCISE_TYPES = {
    "fixation_target",
    "horizontal_moving_target",
    "gaze_target_selection",
    # Allow mapping from recommendation categories and common slugs
    "Fixation Exercise",
    "Smooth Pursuit Exercise",
    "Saccade Exercise",
    "Gaze Accuracy Exercise",
    "smooth_pursuit",
    "saccade",
    "fixation",
    "gaze_accuracy",
}

VALID_SESSION_STATUSES = {
    "assigned",
    "ready",
    "in_progress",
    "paused",
    "completed",
    "stopped",
    "abandoned",
    "error",
}

VALID_DIFFICULTIES = {
    "beginner",
    "medium",
    "moderate",
    "intermediate",
    "advanced",
    "not_applicable",
    "1", "2", "3", "4", "5",
    "Level 1", "Level 2", "Level 3", "Level 4", "Level 5",
}


class TherapySessionCreate(BaseModel):
    patient_id: str
    recommendation_id: Optional[str] = None
    exercise_type: str = "horizontal_moving_target"
    planned_duration_seconds: int = 300
    duration_seconds: Optional[int] = None
    difficulty: str = "beginner"
    assigned_by: Optional[str] = None
    is_simulated_data: bool = False
    data_quality_status: Optional[str] = "Valid Data"


class TherapySessionAction(BaseModel):
    action: Optional[str] = None
    actual_duration_seconds: Optional[int] = None
    stop_reason: Optional[str] = None
    clinician_notes: Optional[str] = None


class TherapySessionResultCreate(BaseModel):
    exercise_type: Optional[str] = None
    score: float = 0.0
    accuracy: Optional[float] = None
    accuracy_score: Optional[float] = None
    error_value: Optional[float] = None
    reaction_time: Optional[float] = None
    reaction_time_ms: Optional[float] = None
    completion_percentage: float = 0.0
    valid_sample_count: int = 0
    tracking_confidence: float = 0.9
    target_loss_events: int = 0
    pause_count: int = 0
    metrics_json: Dict[str, Any] = Field(default_factory=dict)
    data_quality_status: str = "Valid Data"
    is_simulated_data: bool = False
    clinician_notes: Optional[str] = None


class TherapySessionResultResponse(BaseModel):
    id: str
    therapy_session_id: str
    patient_id: str
    exercise_type: str
    score: float
    accuracy: float
    error_value: Optional[float] = None
    reaction_time: Optional[float] = None
    completion_percentage: float
    valid_sample_count: int
    tracking_confidence: float
    target_loss_events: int
    pause_count: int
    metrics_json: Dict[str, Any] = Field(default_factory=dict)
    data_quality_status: str
    is_simulated_data: bool
    clinician_notes: Optional[str] = None
    created_at: str
    notice: str = "Prototype rehabilitation session. Follow clinician instructions. Stop if discomfort occurs. Recorded results are not a diagnosis."


class TherapySessionResponse(BaseModel):
    id: str
    patient_id: str
    recommendation_id: Optional[str] = None
    assigned_by: Optional[str] = None
    exercise_type: str
    session_status: str
    planned_duration_seconds: int = 300
    actual_duration_seconds: int = 0
    duration_seconds: Optional[int] = None
    difficulty: str
    started_at: Optional[str] = None
    paused_at: Optional[str] = None
    completed_at: Optional[str] = None
    stopped_at: Optional[str] = None
    stop_reason: Optional[str] = None
    data_quality_status: str
    is_simulated_data: bool
    created_at: str
    updated_at: str
    notice: str = "Prototype rehabilitation session. Follow clinician instructions. Stop if discomfort occurs. Recorded results are not a diagnosis."
    results: List[TherapySessionResultResponse] = Field(default_factory=list)
