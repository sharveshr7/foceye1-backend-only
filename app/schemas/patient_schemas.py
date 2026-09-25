from datetime import date
from typing import Optional
from pydantic import BaseModel


class PatientCreate(BaseModel):
    name: str
    age: int
    gender: str
    hospital_id: Optional[str] = None
    date_of_birth: Optional[date] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    medical_history: Optional[str] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    condition: Optional[str] = "Pending Eye Test"
    initial_observation: Optional[str] = None
    clinical_status: Optional[str] = "EYE_TEST_PENDING"
    observed_pattern: Optional[str] = None
    recommended_therapy: Optional[str] = None
    assigned_doctor: Optional[str] = None
    icd10: Optional[str] = "H53.00"
    stage: Optional[str] = "EYE_TEST_PENDING"
    adherence: Optional[int] = 100
    visual_acuity_left: Optional[str] = "20/20"
    visual_acuity_right: Optional[str] = "20/20"
    bcea_score: Optional[float] = 1.0


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    hospital_id: Optional[str] = None
    date_of_birth: Optional[date] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    medical_history: Optional[str] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    condition: Optional[str] = None
    initial_observation: Optional[str] = None
    clinical_status: Optional[str] = None
    observed_pattern: Optional[str] = None
    recommended_therapy: Optional[str] = None
    assigned_doctor: Optional[str] = None
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
