"""
Adaptive Therapy Pydantic Schemas
Strictly validates clinician-controlled configuration, adaptation recommendations,
and review/audit requests.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator


VALID_ADAPTIVE_MODES = ["disabled", "manual_only", "controlled_automatic"]
VALID_RECOMMENDATION_STATUSES = [
    "pending",
    "approved",
    "rejected",
    "applied",
    "overridden",
    "cancelled",
    "not_recommended",
]
VALID_DIRECTIONS = ["progression", "regression", "maintain", "pause_discomfort"]


class AdaptiveTherapyConfigBase(BaseModel):
    exercise_id: str = Field(..., description="Exercise ID e.g. fixation_target, horizontal_moving_target")
    therapy_assignment_id: Optional[str] = None
    enabled: bool = True
    adaptive_mode: str = Field("controlled_automatic", description="disabled | manual_only | controlled_automatic")

    minimum_difficulty: int = Field(1, ge=1, le=10)
    maximum_difficulty: int = Field(5, ge=1, le=10)
    starting_difficulty: int = Field(2, ge=1, le=10)
    current_difficulty: Optional[int] = Field(None, ge=1, le=10)

    progression_threshold: float = Field(85.0, ge=0.0, le=100.0)
    regression_threshold: float = Field(50.0, ge=0.0, le=100.0)
    step_size: int = Field(1, ge=1, le=5)
    minimum_sessions_before_adaptation: int = Field(2, ge=1, le=20)
    max_daily_difficulty_increase: int = Field(1, ge=1, le=5)
    clinician_approval_required: bool = True

    @model_validator(mode="after")
    def validate_bounds_and_thresholds(self):
        if self.minimum_difficulty > self.maximum_difficulty:
            raise ValueError(
                f"Minimum difficulty ({self.minimum_difficulty}) cannot exceed maximum difficulty ({self.maximum_difficulty})."
            )
        if not (self.minimum_difficulty <= self.starting_difficulty <= self.maximum_difficulty):
            raise ValueError(
                f"Starting difficulty ({self.starting_difficulty}) must be between minimum ({self.minimum_difficulty}) and maximum ({self.maximum_difficulty})."
            )
        if self.current_difficulty is not None and not (self.minimum_difficulty <= self.current_difficulty <= self.maximum_difficulty):
            raise ValueError(
                f"Current difficulty ({self.current_difficulty}) must be between minimum ({self.minimum_difficulty}) and maximum ({self.maximum_difficulty})."
            )
        if self.regression_threshold >= self.progression_threshold:
            raise ValueError(
                f"Regression threshold ({self.regression_threshold}%) must be strictly lower than progression threshold ({self.progression_threshold}%)."
            )
        if self.adaptive_mode not in VALID_ADAPTIVE_MODES:
            raise ValueError(
                f"Invalid adaptive mode '{self.adaptive_mode}'. Must be one of {VALID_ADAPTIVE_MODES}."
            )
        return self


class AdaptiveTherapyConfigCreate(AdaptiveTherapyConfigBase):
    patient_id: str


class AdaptiveTherapyConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    adaptive_mode: Optional[str] = None
    minimum_difficulty: Optional[int] = Field(None, ge=1, le=10)
    maximum_difficulty: Optional[int] = Field(None, ge=1, le=10)
    starting_difficulty: Optional[int] = Field(None, ge=1, le=10)
    current_difficulty: Optional[int] = Field(None, ge=1, le=10)
    progression_threshold: Optional[float] = Field(None, ge=0.0, le=100.0)
    regression_threshold: Optional[float] = Field(None, ge=0.0, le=100.0)
    step_size: Optional[int] = Field(None, ge=1, le=5)
    minimum_sessions_before_adaptation: Optional[int] = Field(None, ge=1, le=20)
    max_daily_difficulty_increase: Optional[int] = Field(None, ge=1, le=5)
    clinician_approval_required: Optional[bool] = None


class AdaptiveTherapyConfigResponse(BaseModel):
    id: str
    patient_id: str
    therapy_assignment_id: Optional[str] = None
    exercise_id: str
    enabled: bool
    adaptive_mode: str
    minimum_difficulty: int
    maximum_difficulty: int
    starting_difficulty: int
    current_difficulty: int
    progression_threshold: float
    regression_threshold: float
    step_size: int
    minimum_sessions_before_adaptation: int
    max_daily_difficulty_increase: int
    clinician_approval_required: bool
    created_by: Optional[str] = None
    created_at: str
    updated_at: str
    notice: str = "Controlled rule-based difficulty adaptation. Does not diagnose or determine recovery. Follow clinician guidance."


class TherapyAdaptationRecommendationResponse(BaseModel):
    id: str
    patient_id: str
    therapy_assignment_id: Optional[str] = None
    exercise_id: str
    source_session_id: Optional[str] = None
    current_difficulty: int
    recommended_difficulty: int
    direction: str
    reason: str
    supporting_metrics: Dict[str, Any] = Field(default_factory=dict)
    confidence: str
    data_quality_note: str
    is_simulated_data: bool
    status: str
    reviewed_by: Optional[str] = None
    clinician_note: Optional[str] = None
    reviewed_at: Optional[str] = None
    applied_at: Optional[str] = None
    created_at: str
    notice: str = "Suggested difficulty adjustment based on performance rules. Requires clinician review before application when configured."


class TherapyAdaptationReviewRequest(BaseModel):
    action: Literal["approve", "reject", "override"]
    override_difficulty: Optional[int] = Field(None, ge=1, le=10)
    clinician_notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_override(self):
        if self.action == "override" and self.override_difficulty is None:
            raise ValueError("override_difficulty is required when action is 'override'.")
        return self


class TherapyAdaptationAuditResponse(BaseModel):
    id: str
    patient_id: str
    exercise_id: str
    previous_difficulty: int
    new_difficulty: int
    change_type: str
    trigger: str
    source_recommendation_id: Optional[str] = None
    applied_by: str
    applied_at: str
    notes: Optional[str] = None


class SessionEvaluationRequest(BaseModel):
    therapy_session_id: str
    exercise_id: Optional[str] = None
