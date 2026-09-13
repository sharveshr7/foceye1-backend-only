from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EyeTestTrendPoint(BaseModel):
    session_id: str
    test_date: str
    test_type: str
    score: float
    error_value: Optional[float] = None
    duration: float = 0.0
    reaction_time: Optional[float] = None
    tracking_confidence: float = 0.85
    is_simulated_data: bool = False
    data_quality_status: str = "Valid Data"


class TherapyTrendPoint(BaseModel):
    session_id: str
    session_date: str
    exercise_type: str
    score: float
    accuracy: float
    error_value: Optional[float] = None
    reaction_time: Optional[float] = None
    actual_duration_seconds: int = 0
    planned_duration_seconds: int = 300
    completion_percentage: float = 100.0
    tracking_confidence: float = 0.85
    target_loss_events: int = 0
    is_simulated_data: bool = False
    data_quality_status: str = "optimal"
    session_status: str = "completed"


class MetricComparison(BaseModel):
    metric_name: str
    test_type: str
    unit: str
    baseline_value: Optional[float] = None
    latest_value: Optional[float] = None
    recorded_change: Optional[float] = None
    percentage_change: Optional[float] = None
    sessions_between: int = 0
    comparison_reliability: str = "No Data"
    higher_is_better: bool = True
    notice: Optional[str] = None


class EyeTestsSummary(BaseModel):
    total_sessions: int = 0
    completed_sessions: int = 0
    latest_session_date: Optional[str] = None


class TherapySessionsSummary(BaseModel):
    total_sessions: int = 0
    completed_sessions: int = 0
    stopped_sessions: int = 0
    abandoned_sessions: int = 0
    latest_session_date: Optional[str] = None


class SessionCompletionSummary(BaseModel):
    assigned_sessions: Optional[int] = None
    planned_sessions: Optional[int] = None
    completed_sessions: int = 0
    stopped_sessions: Optional[int] = None
    completion_percentage: Optional[float] = None
    notice: str = "Session completion data is available; planned-session adherence is not yet configured."


class DataQualitySummary(BaseModel):
    valid_count: int = 0
    low_confidence_count: int = 0
    incomplete_count: int = 0
    simulated_count: int = 0
    notice: str = "Data quality reflects recording reliability, not medical severity."


class PatientProgressOverview(BaseModel):
    patient_id: str
    eye_tests_summary: EyeTestsSummary
    therapy_sessions_summary: TherapySessionsSummary
    completion_summary: SessionCompletionSummary
    data_quality_summary: DataQualitySummary
    baseline_comparisons: List[MetricComparison] = Field(default_factory=list)
    eye_test_trends: Dict[str, List[EyeTestTrendPoint]] = Field(default_factory=dict)
    therapy_trends: List[TherapyTrendPoint] = Field(default_factory=list)
    provenance_label: str = "Optical Sensor Telemetry"
    is_simulated_data: bool = False
    last_updated: str
    safety_disclaimer: str = (
        "Recorded changes should be interpreted by a qualified clinician. "
        "Differences may be affected by test conditions, calibration, device performance, and data quality. "
        "Recorded results are not a diagnosis."
    )


# Section 8 & 9: Structured AI Progress Summary Data Schemas
class AIProgressChangeItem(BaseModel):
    area: str
    metric: str
    baseline_value: Optional[float] = None
    latest_value: Optional[float] = None
    change: Optional[float] = None
    description: str
    confidence: str = "moderate"


class AIProgressSummaryOutput(BaseModel):
    summary_status: str = "completed"
    overall_summary: str
    recorded_changes: List[AIProgressChangeItem] = Field(default_factory=list)
    stable_areas: List[str] = Field(default_factory=list)
    inconsistent_or_low_reliability_areas: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    clinician_review_points: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class AIProgressSummaryRequest(BaseModel):
    clinician_notes: Optional[str] = None


class AIProgressSummaryResponse(BaseModel):
    """Backwards-compatible wrapper plus structured output."""
    id: Optional[str] = None
    patient_id: str
    summary_text: str
    observed_trends: List[str] = Field(default_factory=list)
    structured_output: Optional[AIProgressSummaryOutput] = None
    data_quality_remarks: str = ""
    is_simulated_data: bool = False
    model_name: str = "gemini-2.5-flash"
    clinician_review_status: str = "pending"
    clinician_notes: Optional[str] = None
    generated_at: str
    disclaimer: str = (
        "AI-assisted progress summary. Requires clinician review. "
        "Does not represent a clinical diagnosis or treatment-outcome determination. "
        "Not a diagnosis or treatment-outcome determination."
    )


class AIProgressSummaryReviewRequest(BaseModel):
    clinician_review_status: str = "reviewed"
    clinician_notes: Optional[str] = None


# Section 11: Patient Progress Timeline Schema
class TimelineItem(BaseModel):
    id: str
    event_type: str
    date_time: str
    title: str
    short_description: str
    related_id: Optional[str] = None
    related_type: Optional[str] = None
    status: Optional[str] = None
    data_quality_status: Optional[str] = None
    is_simulated_data: bool = False


# Section 12: Clinician Notes Schemas
class ClinicianProgressNoteCreate(BaseModel):
    notes: str
    related_session_id: Optional[str] = None
    follow_up_date: Optional[str] = None


class ClinicianProgressNoteResponse(BaseModel):
    id: str
    patient_id: str
    clinician_id: str
    clinician_name: str
    notes: str
    related_session_id: Optional[str] = None
    follow_up_date: Optional[str] = None
    created_at: str
