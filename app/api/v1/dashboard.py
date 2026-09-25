"""
Clinician Dashboard & Hospital Administration API Router.
Provides operational metrics, pending clinical action triage, rule-based attention indicators,
searchable/filterable patient rosters, multi-event audit activity feeds, and in-app notifications.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import UserProfile, get_current_user, require_role
from app.schemas.dashboard_schemas import (
    ActivityFeedResponse,
    DashboardSummaryMetrics,
    NotificationListResponse,
    PatientOverviewPaginationResponse,
    PendingActionsResponse,
)
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Clinician Dashboard & Hospital Administration"])

ALLOWED_DASHBOARD_ROLES = ["clinician", "hospital_staff", "admin", "therapist"]


@router.get("/summary", response_model=DashboardSummaryMetrics)
async def get_dashboard_summary(
    user: UserProfile = Depends(require_role(ALLOWED_DASHBOARD_ROLES))
):
    """
    Retrieve hospital-isolated operational statistics for the logged-in user.
    Accessible to clinicians, hospital staff, and administrators.
    """
    try:
        return DashboardService.get_summary_metrics(user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate dashboard summary: {str(e)}"
        )


@router.get("/pending-actions", response_model=PendingActionsResponse)
async def get_pending_actions(
    category: Optional[str] = Query(
        None,
        description="Optional filter by action type (e.g. eye_test_review, therapy_recommendation_approval, adaptation_review, discomfort_reported)"
    ),
    user: UserProfile = Depends(require_role(ALLOWED_DASHBOARD_ROLES))
):
    """
    Retrieve clinical actions awaiting attention (unreviewed tests, unapproved recommendations, discomfort alerts).
    Enforces role permissions via can_act flag.
    """
    try:
        return DashboardService.get_pending_actions(user, category=category)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve pending actions: {str(e)}"
        )


@router.get("/patient-overview", response_model=PatientOverviewPaginationResponse)
@router.get("/patients", response_model=PatientOverviewPaginationResponse)
async def get_patient_overview(
    search: Optional[str] = Query(None, description="Search by patient name or ID"),
    therapy_status: Optional[str] = Query(None, description="Filter: all, not_assigned, prescribed, active, completed"),
    review_status: Optional[str] = Query(None, description="Filter: all, pending, reviewed, approved, none"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    user: UserProfile = Depends(require_role(ALLOWED_DASHBOARD_ROLES))
):
    """
    Retrieve searchable, filterable, paginated patient records with rule-based attention indicators and telemetry quality tags.
    """
    try:
        return DashboardService.get_patient_overview(
            user=user,
            search=search,
            therapy_status=therapy_status,
            review_status=review_status,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch patient overview: {str(e)}"
        )


@router.get("/recent-activity", response_model=ActivityFeedResponse)
@router.get("/activity-feed", response_model=ActivityFeedResponse)
async def get_recent_activity(
    limit: int = Query(20, ge=1, le=100, description="Max activities to return"),
    user: UserProfile = Depends(require_role(ALLOWED_DASHBOARD_ROLES))
):
    """
    Retrieve recent chronological hospital activity events (registrations, tests, reviews, therapy sessions, adaptations).
    """
    try:
        return DashboardService.get_recent_activity(user=user, limit=limit)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve activity feed: {str(e)}"
        )


@router.get("/notifications", response_model=NotificationListResponse)
async def get_notifications(
    user: UserProfile = Depends(require_role(ALLOWED_DASHBOARD_ROLES))
):
    """
    Retrieve in-app notifications for pending clinical actions, discomfort reports, and data quality warnings.
    """
    try:
        return DashboardService.get_notifications(user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve notifications: {str(e)}"
        )


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user: UserProfile = Depends(require_role(ALLOWED_DASHBOARD_ROLES))
):
    """
    Mark an in-app notification as read.
    """
    try:
        return DashboardService.mark_notification_read(notification_id, user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark notification as read: {str(e)}"
        )


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    user: UserProfile = Depends(require_role(ALLOWED_DASHBOARD_ROLES))
):
    """
    Mark all in-app notifications as read.
    """
    try:
        return DashboardService.mark_all_notifications_read(user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark all notifications as read: {str(e)}"
        )
