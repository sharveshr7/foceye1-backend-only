"""
Dashboard & Notification Models for Clinician Dashboard & Hospital Administration.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class NotificationRecord(BaseModel):
    id: str
    user_id: Optional[str] = None
    hospital_name: Optional[str] = None
    title: str
    description: str
    category: str = Field(
        ...,
        description="Category: pending_eye_test_review, pending_therapy_recommendation, pending_adaptation_review, discomfort_reported, data_quality_warning, session_abandoned"
    )
    related_patient_id: Optional[str] = None
    related_patient_name: Optional[str] = None
    related_resource_id: Optional[str] = None
    priority: str = Field("medium", description="Priority: low, medium, high, urgent")
    is_read: bool = False
    target_url: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ActivityLogRecord(BaseModel):
    id: str
    hospital_name: Optional[str] = None
    activity_type: str = Field(
        ...,
        description="Activity type: patient_registered, eye_test_completed, ai_analysis_generated, recommendation_created, recommendation_approved, recommendation_rejected, session_completed, session_abandoned, adaptation_recommended, difficulty_updated, clinician_note_added"
    )
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    actor_role: Optional[str] = None
    details: Optional[str] = None
    target_url: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
