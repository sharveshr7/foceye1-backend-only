from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

VALID_EXERCISE_TYPES = {
    "fixation_target",
    "horizontal_moving_target",
    "gaze_target_selection",
    # Allow mapping from recommendation categories
    "Fixation Exercise",
    "Smooth Pursuit Exercise",
    "Saccade Exercise",
    "Gaze Accuracy Exercise",
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
    difficulty: str = "beginner"
    assigned_by: Optional[str] = None


class TherapySessionAction(BaseModel):
    action: Optional[str] = None
    actual_duration_seconds: Optional[int] = None
    stop_reason: Optional[str] = None
    clinician_notes: Optional[str] = None


class TherapySessionResultCreate(BaseModel):
    exercise_type: str
    score: float = 0.0
    accuracy: float = 0.0
    error_value: Optional[float] = None
    reaction_time: Optional[float] = None
    completion_percentage: float = 0.0
    valid_sample_count: int = 0
    tracking_confidence: float = 0.9
    target_loss_events: int = 0
    pause_count: int = 0
    metrics_json: Dict[str, Any] = Field(default_factory=dict)
    data_quality_status: str = "Demo/Simulated Tracking Data"
    is_simulated_data: bool = True
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
    planned_duration_seconds: int
    actual_duration_seconds: int
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
