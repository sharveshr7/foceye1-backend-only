"""
Pydantic Schemas for Clinician Dashboard & Hospital Administration.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DashboardSummaryMetrics(BaseModel):
    total_patients: int = Field(..., description="Total count of authorized registered patients")
    active_therapy_plans: int = Field(..., description="Count of patients currently undergoing therapy")
    pending_eye_test_reviews: int = Field(..., description="Eye tests completed and awaiting clinician review")
    pending_therapy_recommendations: int = Field(..., description="Therapy recommendations awaiting clinician approval")
    sessions_completed: int = Field(..., description="Cumulative therapy sessions successfully finished")
    patients_requiring_attention: int = Field(..., description="Count of patients with one or more attention flags")
    hospital_name: str = Field(..., description="Authorized clinical institution or department scope")
    user_role: str = Field(..., description="Authenticated user role")
    notice: Optional[str] = "Clinical decision-support metrics. Non-diagnostic. Reflects real hospital operational data."


class PendingActionItem(BaseModel):
    id: str
    patient_id: str
    patient_name: str
    action_type: str = Field(
        ...,
        description="Type: eye_test_review, therapy_recommendation_approval, adaptation_review, discomfort_reported, poor_data_quality, abandoned_session, therapy_plan_review"
    )
    title: str
    reason: str
    priority: str = Field(..., description="Priority: low, medium, high, urgent")
    created_at: str
    target_route: str
    can_act: bool = Field(..., description="Whether current user's role grants approval/execution permission")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PendingActionsResponse(BaseModel):
    items: List[PendingActionItem]
    total: int
    urgent_count: int


class PatientOverviewItem(BaseModel):
    id: str
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    registration_date: str
    last_eye_test_date: Optional[str] = None
    last_therapy_session_date: Optional[str] = None
    therapy_status: str = Field(..., description="Status: not_assigned, prescribed, active, completed")
    latest_review_status: str = Field(..., description="Status: pending, reviewed, approved, none")
    data_quality_status: str = Field(..., description="Status: good, warning, poor, no_data")
    attention_indicators: List[str] = Field(default_factory=list)
    attention_reasons: List[str] = Field(default_factory=list)


class PatientOverviewPaginationResponse(BaseModel):
    items: List[PatientOverviewItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class ActivityFeedItem(BaseModel):
    id: str
    activity_type: str
    description: str
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    actor_name: Optional[str] = None
    actor_role: Optional[str] = None
    created_at: str
    target_url: Optional[str] = None


class ActivityFeedResponse(BaseModel):
    items: List[ActivityFeedItem]
    total: int


class NotificationResponse(BaseModel):
    id: str
    title: str
    description: str
    category: str
    related_patient_id: Optional[str] = None
    related_patient_name: Optional[str] = None
    priority: str = "medium"
    is_read: bool = False
    created_at: str
    target_url: Optional[str] = None


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    unread_count: int


class NotificationMarkReadRequest(BaseModel):
    notification_ids: Optional[List[str]] = None
