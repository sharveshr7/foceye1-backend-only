from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EyeTestSessionCreate(BaseModel):
    patient_id: str
    clinician_id: Optional[str] = None


class EyeTestSessionUpdate(BaseModel):
    session_status: Optional[str] = None
    completed_at: Optional[str] = None


class EyeTestSessionResponse(BaseModel):
    id: str
    patient_id: str
    clinician_id: Optional[str] = None
    session_status: str = "IN_PROGRESS"
    started_at: str
    completed_at: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


class StartTestRequest(BaseModel):
    test_type: str = Field(
        ...,
        description="Type of eye test: FIXATION_STABILITY, SMOOTH_PURSUIT, SACCADE_RESPONSE, or GAZE_ACCURACY"
    )


class EyeTestResultCreate(BaseModel):
    session_id: str
    patient_id: str
    test_type: str
    status: str = "COMPLETED"
    duration: float = 0.0
    score: float = 0.0
    error_value: Optional[float] = None
    reaction_time: Optional[float] = None
    valid_sample_count: int = 0
    tracking_confidence: float = 0.0
    data_quality_status: str = "Demo/Simulated Data"
    raw_result_json: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class EyeTestResultUpdate(BaseModel):
    status: Optional[str] = None
    score: Optional[float] = None
    error_value: Optional[float] = None
    reaction_time: Optional[float] = None
    valid_sample_count: Optional[int] = None
    tracking_confidence: Optional[float] = None
    data_quality_status: Optional[str] = None
    raw_result_json: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class EyeTestResultResponse(BaseModel):
    id: str
    session_id: str
    patient_id: str
    test_type: str
    status: str
    duration: float
    score: float
    error_value: Optional[float] = None
    reaction_time: Optional[float] = None
    valid_sample_count: int
    tracking_confidence: float
    data_quality_status: str
    raw_result_json: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    created_at: str
