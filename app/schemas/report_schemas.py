from typing import Optional
from pydantic import BaseModel


class ReportRequest(BaseModel):
    patient_id: str
    include_raw_telemetry: bool = False
    include_ai_insights: bool = True
    therapist_signature: Optional[str] = "Dr. Sarah Smith, OD"
