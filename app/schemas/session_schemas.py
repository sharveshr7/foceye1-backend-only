from typing import List, Optional
from pydantic import BaseModel


class GazePoint(BaseModel):
    x: float
    y: float
    timestamp: float
    pupil_left_mm: Optional[float] = 3.5
    pupil_right_mm: Optional[float] = 3.5
    confidence: Optional[float] = 1.0


class TherapySessionCreate(BaseModel):
    patient_id: str
    exercise_type: str
    duration_seconds: int
    fixation_score: float
    saccadic_score: float
    convergence_score: float
    bcea_68: Optional[float] = 1.2
    bcea_95: Optional[float] = 2.4
    gaze_points: Optional[List[GazePoint]] = []
    clinical_notes: Optional[str] = ""


class TherapySessionResponse(TherapySessionCreate):
    id: str
    created_at: str
    overall_score: float
