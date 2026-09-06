from typing import Optional
from pydantic import BaseModel


class PatientCreate(BaseModel):
    name: str
    age: int
    gender: str
    condition: str
    icd10: Optional[str] = "H53.00"
    stage: Optional[str] = "Active Therapy"
    adherence: Optional[int] = 100
    visual_acuity_left: Optional[str] = "20/20"
    visual_acuity_right: Optional[str] = "20/20"
    bcea_score: Optional[float] = 1.0


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    condition: Optional[str] = None
    icd10: Optional[str] = None
    stage: Optional[str] = None
    adherence: Optional[int] = None
    last_session: Optional[str] = None
    visual_acuity_left: Optional[str] = None
    visual_acuity_right: Optional[str] = None
    bcea_score: Optional[float] = None


class PatientResponse(PatientCreate):
    id: str
    last_session: Optional[str] = None
    created_at: Optional[str] = None
