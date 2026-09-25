from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MetricValue(BaseModel):
    metric: str
    value: float


class PerformanceSummaryItem(BaseModel):
    test_type: str
    observation: str
    supporting_metrics: List[MetricValue] = Field(default_factory=list)
    interpretation_confidence: str = "moderate"  # low, moderate, high


class PerformancePatternItem(BaseModel):
    pattern: str  # improving, declining, stable, variable, incomplete, low_reliability, insufficient_data
    area: str
    description: str
    supporting_metrics: List[str] = Field(default_factory=list)
    confidence: str = "moderate"


class SessionComparisonItem(BaseModel):
    metric: Optional[str] = "Metric"
    previous_value: Optional[float] = None
    current_value: Optional[float] = None
    change: Optional[float] = None
    direction: Optional[str] = "stable"
    comparison_confidence: str = "moderate"
    test_type: Optional[str] = None
    notes: Optional[str] = None

    model_config = {"extra": "ignore"}


class SessionComparison(BaseModel):
    available: bool = False
    summary: str = "No previous session is available for comparison."
    changes: List[SessionComparisonItem] = Field(default_factory=list)


class AIAnalysisOutput(BaseModel):
    analysis_status: str = "completed"  # completed, partial, limited
    overall_summary: str
    performance_summary: List[PerformanceSummaryItem] = Field(default_factory=list)
    performance_patterns: List[PerformancePatternItem] = Field(default_factory=list)
    session_comparison: SessionComparison = Field(default_factory=SessionComparison)
    data_quality_warnings: List[str] = Field(default_factory=list)
    areas_for_clinician_review: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(
        default_factory=lambda: [
            "This analysis is based strictly on recorded eye-tracking measurements.",
            "The output is an assistive observation and not a medical diagnosis."
        ]
    )
    disclaimer: str = "AI-assisted analysis. Requires clinician review. Not a diagnosis."


class ClinicianReviewUpdate(BaseModel):
    clinician_review_status: str = "reviewed"  # pending, reviewed, flagged, dismissed
    clinician_notes: Optional[str] = None


class AIAnalysisResponse(BaseModel):
    id: str
    patient_id: str
    eye_test_session_id: str
    analysis_status: str
    model_name: str
    input_summary_json: Dict[str, Any]
    output_json: AIAnalysisOutput
    data_quality_status: str
    is_simulated_data: bool
    clinician_review_status: str = "pending"
    clinician_notes: Optional[str] = None
    confidence_score: Optional[float] = 0.95
    ai_observations: Optional[str] = "Objective telemetry consistent with clinical normative ranges."
    created_at: str
    updated_at: str
