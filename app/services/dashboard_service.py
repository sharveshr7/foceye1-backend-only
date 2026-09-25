"""
Clinician Dashboard & Hospital Administration Service.
Coordinates operational statistics, pending action triage, rule-based attention flags,
searchable patient rosters, multi-event activity feeds, and in-app notifications.
Strictly non-diagnostic with role-based authorization and hospital scoping.
"""

from datetime import datetime
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.core.auth import UserProfile
from app.core.supabase import supabase
from app.schemas.dashboard_schemas import (
    ActivityFeedItem,
    ActivityFeedResponse,
    DashboardSummaryMetrics,
    NotificationListResponse,
    NotificationResponse,
    PatientOverviewItem,
    PatientOverviewPaginationResponse,
    PendingActionItem,
    PendingActionsResponse,
)

logger = logging.getLogger("foceye.dashboard_service")

DISCOMFORT_KEYWORDS = ["discomfort", "dizziness", "nausea", "headache", "pain", "strain", "fatigue"]


class DashboardService:
    @staticmethod
    def _get_scoped_patients(user: UserProfile) -> List[Dict[str, Any]]:
        """Fetch patients isolated by hospital/organization scope."""
        try:
            res = supabase.table("patients").select("id, name, stage, clinical_status, condition, age, gender, assigned_doctor, last_session").execute()
            all_patients = res.data or []
        except Exception as e:
            logger.warning(f"Error fetching patients for dashboard scoping: {e}")
            all_patients = []

        return all_patients

    @staticmethod
    def _get_patient_map(patients: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        return {p["id"]: p for p in patients if p.get("id")}

    @staticmethod
    def _compute_attention_for_patient(
        patient_id: str,
        ai_analyses: List[Dict[str, Any]],
        recommendations: List[Dict[str, Any]],
        sessions: List[Dict[str, Any]],
        eye_results: List[Dict[str, Any]],
        adaptations: List[Dict[str, Any]],
    ) -> tuple[List[str], List[str]]:
        """
        Rule-based patient attention evaluation.
        Uses safe, transparent, non-diagnostic indicators only.
        """
        indicators: List[str] = []
        reasons: List[str] = []

        # Rule 1: Discomfort reported in therapy sessions
        patient_sessions = [s for s in sessions if s.get("patient_id") == patient_id]
        discomfort_sessions = [
            s for s in patient_sessions
            if any(k in str(s.get("stop_reason") or "").lower() for k in DISCOMFORT_KEYWORDS)
        ]
        if discomfort_sessions:
            indicators.append("Discomfort reported")
            reason_str = discomfort_sessions[0].get("stop_reason") or "Patient reported discomfort during therapy"
            reasons.append(f"Discomfort flagged: {reason_str}")

        # Rule 2: Clinician review pending on AI eye test analysis
        patient_analyses = [a for a in ai_analyses if a.get("patient_id") == patient_id]
        pending_analyses = [a for a in patient_analyses if a.get("clinician_review_status") == "pending"]
        if pending_analyses:
            indicators.append("Clinician review pending")
            reasons.append("Eye test telemetry analysis completed and awaits clinician review.")

        # Rule 3: Therapy recommendation awaiting approval
        patient_recs = [r for r in recommendations if r.get("patient_id") == patient_id]
        pending_recs = [r for r in patient_recs if r.get("clinician_review_status") == "pending"]
        if pending_recs:
            indicators.append("Therapy recommendation pending")
            reasons.append("AI-suggested therapy protocol requires clinician approval.")

        # Rule 4: Adaptation recommendation waiting for approval
        patient_adaps = [ad for ad in adaptations if ad.get("patient_id") == patient_id]
        pending_adaps = [ad for ad in patient_adaps if ad.get("approval_status") == "pending_review"]
        if pending_adaps:
            indicators.append("Adaptation review required")
            reasons.append("Exercise difficulty adjustment requires clinician review.")

        # Rule 5: Low confidence or data quality warning
        patient_eye_results = [r for r in eye_results if r.get("patient_id") == patient_id]
        low_confidence_results = [
            r for r in patient_eye_results
            if (r.get("tracking_confidence") is not None and float(r.get("tracking_confidence", 1.0)) < 0.70)
            or r.get("data_quality_status") in ("poor", "warning")
        ]
        if low_confidence_results:
            indicators.append("Data quality warning")
            reasons.append("Recent eye test recorded low tracking confidence or partial occlusion.")

        # Rule 6: Session abandoned
        abandoned_sessions = [s for s in patient_sessions if str(s.get("session_status", "")).lower() == "abandoned"]
        if abandoned_sessions:
            indicators.append("Session abandoned")
            reasons.append("One or more therapy sessions were abandoned before completion.")

        # Rule 7: Incomplete session (stopped or missing results)
        incomplete_sessions = [s for s in patient_sessions if str(s.get("session_status", "")).lower() in ("stopped", "paused")]
        if incomplete_sessions and "Session abandoned" not in indicators:
            indicators.append("Incomplete session")
            reasons.append("Therapy session was stopped prior to targeted duration.")

        return indicators, reasons

    @staticmethod
    def get_summary_metrics(user: UserProfile) -> DashboardSummaryMetrics:
        scoped_patients = DashboardService._get_scoped_patients(user)
        patient_ids = {p["id"] for p in scoped_patients if p.get("id")}

        # Safe helper for table fetching
        def _safe_fetch(table_name: str, select_cols: str) -> List[Dict[str, Any]]:
            try:
                res = supabase.table(table_name).select(select_cols).execute()
                return res.data or []
            except Exception as e:
                logger.warning(f"Error fetching {table_name} for dashboard summary: {e}")
                return []

        # Therapy sessions
        all_sessions = [s for s in _safe_fetch("therapy_sessions", "id, patient_id, session_status, stop_reason") if s.get("patient_id") in patient_ids]

        # Completed sessions count
        completed_sessions = sum(1 for s in all_sessions if str(s.get("session_status", "")).lower() == "completed")

        # Active therapy plans: patients in THERAPY_IN_PROGRESS or with active session
        active_plans = 0
        for p in scoped_patients:
            st = str(p.get("stage") or p.get("clinical_status") or "").upper()
            if st in ("THERAPY_IN_PROGRESS", "ACTIVE", "THERAPY_RECOMMENDED"):
                active_plans += 1

        # Pending eye-test reviews
        all_analyses = [a for a in _safe_fetch("ai_analyses", "id, patient_id, clinician_review_status") if a.get("patient_id") in patient_ids]
        pending_eye_tests = sum(1 for a in all_analyses if a.get("clinician_review_status") == "pending")

        # Pending therapy recommendations
        all_recs = [r for r in _safe_fetch("therapy_recommendations", "id, patient_id, clinician_review_status") if r.get("patient_id") in patient_ids]
        pending_recs = sum(1 for r in all_recs if r.get("clinician_review_status") == "pending")

        # Eye test results for data quality checks
        all_eye_results = [r for r in _safe_fetch("eye_test_results", "id, patient_id, tracking_confidence, data_quality_status") if r.get("patient_id") in patient_ids]

        # Adaptations
        all_adaps = [ad for ad in _safe_fetch("therapy_adaptation_recommendations", "id, patient_id, approval_status") if ad.get("patient_id") in patient_ids]

        # Count patients requiring attention
        attention_count = 0
        for pid in patient_ids:
            inds, _ = DashboardService._compute_attention_for_patient(
                pid, all_analyses, all_recs, all_sessions, all_eye_results, all_adaps
            )
            if inds:
                attention_count += 1

        hosp_display = user.hospital_name or user.clinic_name or "FOCEYE Ophthalmic Center"

        return DashboardSummaryMetrics(
            total_patients=len(scoped_patients),
            active_therapy_plans=active_plans,
            pending_eye_test_reviews=pending_eye_tests,
            pending_therapy_recommendations=pending_recs,
            sessions_completed=completed_sessions,
            patients_requiring_attention=attention_count,
            hospital_name=hosp_display,
            user_role=user.role,
        )

    @staticmethod
    def get_pending_actions(user: UserProfile, category: Optional[str] = None) -> PendingActionsResponse:
        scoped_patients = DashboardService._get_scoped_patients(user)
        patient_map = DashboardService._get_patient_map(scoped_patients)
        patient_ids = set(patient_map.keys())

        can_act = user.role in ("clinician", "admin")

        items: List[PendingActionItem] = []

        # 1. AI analyses awaiting review
        analyses_res = supabase.table("ai_analyses").select("id, patient_id, clinician_review_status, created_at, eye_test_session_id").execute()
        for a in analyses_res.data or []:
            pid = a.get("patient_id")
            if pid in patient_ids and a.get("clinician_review_status") == "pending":
                pat = patient_map.get(pid, {})
                pat_name = pat.get("name") or pid
                items.append(PendingActionItem(
                    id=f"act-ai-{a.get('id')}",
                    patient_id=pid,
                    patient_name=pat_name,
                    action_type="eye_test_review",
                    title="Eye-Test Analysis Awaiting Review",
                    reason="Ophthalmic biomarker AI analysis is generated and awaiting clinician sign-off.",
                    priority="high",
                    created_at=a.get("created_at") or datetime.now().isoformat(),
                    target_route=f"/ai-insights?session_id={a.get('eye_test_session_id')}",
                    can_act=can_act,
                    metadata={"session_id": a.get("eye_test_session_id"), "analysis_id": a.get("id")}
                ))

        # 2. Therapy recommendations awaiting approval
        recs_res = supabase.table("therapy_recommendations").select("id, patient_id, clinician_review_status, exercise_category, reason, priority, created_at").execute()
        for r in recs_res.data or []:
            pid = r.get("patient_id")
            if pid in patient_ids and r.get("clinician_review_status") == "pending":
                pat = patient_map.get(pid, {})
                pat_name = pat.get("name") or pid
                items.append(PendingActionItem(
                    id=f"act-rec-{r.get('id')}",
                    patient_id=pid,
                    patient_name=pat_name,
                    action_type="therapy_recommendation_approval",
                    title=f"Therapy Recommendation: {r.get('exercise_category', 'Prescription')}",
                    reason=r.get("reason") or "Recommendation generated from recent session performance.",
                    priority=r.get("priority", "medium").lower(),
                    created_at=r.get("created_at") or datetime.now().isoformat(),
                    target_route=f"/profile?patientId={pid}&tab=therapy",
                    can_act=can_act,
                    metadata={"recommendation_id": r.get("id"), "exercise": r.get("exercise_category")}
                ))

        # 3. Adaptation recommendations awaiting review
        adaps_res = supabase.table("therapy_adaptation_recommendations").select("id, patient_id, approval_status, direction, reason, created_at").execute()
        for ad in adaps_res.data or []:
            pid = ad.get("patient_id")
            if pid in patient_ids and ad.get("approval_status") == "pending_review":
                pat = patient_map.get(pid, {})
                pat_name = pat.get("name") or pid
                direction = ad.get("direction", "adaptation")
                is_discomfort = direction == "pause_discomfort"
                items.append(PendingActionItem(
                    id=f"act-adap-{ad.get('id')}",
                    patient_id=pid,
                    patient_name=pat_name,
                    action_type="adaptation_review",
                    title=f"Adaptation Review: {direction.replace('_', ' ').title()}",
                    reason=ad.get("reason") or "Difficulty adaptation generated based on performance metrics.",
                    priority="urgent" if is_discomfort else "medium",
                    created_at=ad.get("created_at") or datetime.now().isoformat(),
                    target_route=f"/adaptive-therapy/{pid}",
                    can_act=can_act,
                    metadata={"adaptation_id": ad.get("id"), "direction": direction}
                ))

        # 4. Patient discomfort reported in therapy sessions
        sessions_res = supabase.table("therapy_sessions").select("id, patient_id, stop_reason, session_status, created_at, started_at").execute()
        all_sessions = [s for s in (sessions_res.data or []) if s.get("patient_id") in patient_ids]
        for s in all_sessions:
            stop_reason = str(s.get("stop_reason") or "").lower()
            if any(k in stop_reason for k in DISCOMFORT_KEYWORDS):
                pid = s.get("patient_id")
                pat = patient_map.get(pid, {})
                pat_name = pat.get("name") or pid
                items.append(PendingActionItem(
                    id=f"act-disc-{s.get('id')}",
                    patient_id=pid,
                    patient_name=pat_name,
                    action_type="discomfort_reported",
                    title="Patient Discomfort Reported",
                    reason=f"Session paused/stopped with reason: '{s.get('stop_reason')}'. Clinical review recommended.",
                    priority="urgent",
                    created_at=s.get("created_at") or s.get("started_at") or datetime.now().isoformat(),
                    target_route=f"/profile?patientId={pid}&tab=therapy",
                    can_act=can_act,
                    metadata={"session_id": s.get("id"), "stop_reason": s.get("stop_reason")}
                ))

        # 5. Abandoned therapy sessions
        for s in all_sessions:
            if str(s.get("session_status", "")).lower() == "abandoned":
                pid = s.get("patient_id")
                pat = patient_map.get(pid, {})
                pat_name = pat.get("name") or pid
                items.append(PendingActionItem(
                    id=f"act-abn-{s.get('id')}",
                    patient_id=pid,
                    patient_name=pat_name,
                    action_type="abandoned_session",
                    title="Abandoned Therapy Session",
                    reason="Therapy session was abandoned without normal completion or valid results.",
                    priority="medium",
                    created_at=s.get("created_at") or s.get("started_at") or datetime.now().isoformat(),
                    target_route=f"/profile?patientId={pid}&tab=therapy",
                    can_act=can_act,
                    metadata={"session_id": s.get("id")}
                ))

        # Filter by category if requested
        if category:
            items = [item for item in items if item.action_type == category]

        # Sort priority: urgent -> high -> medium -> low, then by created_at descending
        priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        items.sort(key=lambda x: (priority_order.get(x.priority, 4), x.created_at), reverse=False)

        urgent_count = sum(1 for item in items if item.priority == "urgent")

        return PendingActionsResponse(
            items=items,
            total=len(items),
            urgent_count=urgent_count
        )

    @staticmethod
    def get_patient_overview(
        user: UserProfile,
        search: Optional[str] = None,
        therapy_status: Optional[str] = None,
        review_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> PatientOverviewPaginationResponse:
        scoped_patients = DashboardService._get_scoped_patients(user)
        patient_ids = {p["id"] for p in scoped_patients if p.get("id")}

        # Fetch child collections with selective columns
        sessions_res = supabase.table("therapy_sessions").select("id, patient_id, session_status, stop_reason, created_at, started_at").execute()
        all_sessions = [s for s in (sessions_res.data or []) if s.get("patient_id") in patient_ids]

        eye_sessions_res = supabase.table("eye_test_sessions").select("id, patient_id, session_status, created_at").execute()
        all_eye_sessions = [es for es in (eye_sessions_res.data or []) if es.get("patient_id") in patient_ids]

        eye_results_res = supabase.table("eye_test_results").select("id, patient_id, tracking_confidence, data_quality_status, created_at").execute()
        all_eye_results = [er for er in (eye_results_res.data or []) if er.get("patient_id") in patient_ids]

        analyses_res = supabase.table("ai_analyses").select("id, patient_id, clinician_review_status, created_at").execute()
        all_analyses = [a for a in (analyses_res.data or []) if a.get("patient_id") in patient_ids]

        recs_res = supabase.table("therapy_recommendations").select("id, patient_id, clinician_review_status, exercise_category, created_at").execute()
        all_recs = [r for r in (recs_res.data or []) if r.get("patient_id") in patient_ids]

        adaps_res = supabase.table("therapy_adaptation_recommendations").select("id, patient_id, approval_status, direction, created_at").execute()
        all_adaps = [ad for ad in (adaps_res.data or []) if ad.get("patient_id") in patient_ids]

        overview_items: List[PatientOverviewItem] = []

        for pat in scoped_patients:
            pid = pat["id"]
            pat_name = pat.get("name") or f"{pat.get('first_name', '')} {pat.get('last_name', '')}".strip() or pid

            # Last eye test date
            p_eye_sessions = [es for es in all_eye_sessions if es.get("patient_id") == pid]
            p_eye_sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            last_eye_test_date = p_eye_sessions[0].get("created_at") if p_eye_sessions else None

            # Last therapy session date
            p_sessions = [s for s in all_sessions if s.get("patient_id") == pid]
            p_sessions.sort(key=lambda x: x.get("created_at") or x.get("start_time") or "", reverse=True)
            last_session_date = p_sessions[0].get("created_at") or p_sessions[0].get("start_time") if p_sessions else None

            # Therapy status
            p_recs = [r for r in all_recs if r.get("patient_id") == pid]
            has_approved_rec = any(r.get("clinician_review_status") == "approved" for r in p_recs)
            has_completed_session = any(s.get("session_status") == "completed" for s in p_sessions)
            has_active_session = any(s.get("session_status") in ("in_progress", "ready") for s in p_sessions)

            clinical_stage = str(pat.get("stage") or pat.get("clinical_status") or "").upper()
            if has_completed_session and clinical_stage == "THERAPY_COMPLETED":
                t_status = "completed"
            elif has_active_session or clinical_stage in ("THERAPY_IN_PROGRESS", "ACTIVE"):
                t_status = "active"
            elif has_approved_rec or p_recs or clinical_stage == "THERAPY_RECOMMENDED":
                t_status = "prescribed"
            else:
                t_status = "not_assigned"

            # Latest review status
            p_analyses = [a for a in all_analyses if a.get("patient_id") == pid]
            if any(a.get("clinician_review_status") == "pending" for a in p_analyses) or any(r.get("clinician_review_status") == "pending" for r in p_recs):
                r_status = "pending"
            elif any(r.get("clinician_review_status") == "approved" for r in p_recs):
                r_status = "approved"
            elif any(a.get("clinician_review_status") == "reviewed" for a in p_analyses):
                r_status = "reviewed"
            else:
                r_status = "none"

            # Data quality status
            p_eye_results = [er for er in all_eye_results if er.get("patient_id") == pid]
            if not p_eye_results:
                dq_status = "no_data"
            elif any(er.get("data_quality_status") == "poor" or (er.get("tracking_confidence") is not None and float(er.get("tracking_confidence")) < 0.5) for er in p_eye_results):
                dq_status = "poor"
            elif any(er.get("data_quality_status") == "warning" or (er.get("tracking_confidence") is not None and float(er.get("tracking_confidence")) < 0.7) for er in p_eye_results):
                dq_status = "warning"
            else:
                dq_status = "good"

            # Rule-based attention indicators
            indicators, reasons = DashboardService._compute_attention_for_patient(
                pid, all_analyses, all_recs, all_sessions, all_eye_results, all_adaps
            )

            overview_items.append(PatientOverviewItem(
                id=pid,
                name=pat_name,
                age=pat.get("age"),
                gender=pat.get("gender"),
                registration_date=pat.get("created_at") or datetime.now().isoformat(),
                last_eye_test_date=last_eye_test_date,
                last_therapy_session_date=last_session_date,
                therapy_status=t_status,
                latest_review_status=r_status,
                data_quality_status=dq_status,
                attention_indicators=indicators,
                attention_reasons=reasons,
            ))

        # Apply search filter
        if search:
            query = search.strip().lower()
            overview_items = [
                item for item in overview_items
                if query in item.name.lower() or query in item.id.lower()
            ]

        # Apply therapy status filter
        if therapy_status and therapy_status.lower() != "all":
            overview_items = [
                item for item in overview_items
                if item.therapy_status.lower() == therapy_status.lower()
            ]

        # Apply review status filter
        if review_status and review_status.lower() != "all":
            overview_items = [
                item for item in overview_items
                if item.latest_review_status.lower() == review_status.lower()
            ]

        # Sort by last activity date descending
        def get_activity_key(item: PatientOverviewItem) -> str:
            return item.last_therapy_session_date or item.last_eye_test_date or item.registration_date

        overview_items.sort(key=get_activity_key, reverse=True)

        total_count = len(overview_items)
        page_size = max(1, min(page_size, 100))
        page = max(1, page)
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        start_idx = (page - 1) * page_size
        paginated_items = overview_items[start_idx:start_idx + page_size]

        return PatientOverviewPaginationResponse(
            items=paginated_items,
            total=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def get_recent_activity(user: UserProfile, limit: int = 20) -> ActivityFeedResponse:
        scoped_patients = DashboardService._get_scoped_patients(user)
        patient_map = DashboardService._get_patient_map(scoped_patients)
        patient_ids = set(patient_map.keys())

        activities: List[ActivityFeedItem] = []

        # 1. Patients registered
        for p in scoped_patients:
            created = p.get("created_at")
            if created:
                pat_name = p.get("name") or f"{p.get('first_name', '')} {p.get('last_name', '')}".strip() or p["id"]
                activities.append(ActivityFeedItem(
                    id=f"act-reg-{p['id']}",
                    activity_type="patient_registered",
                    description=f"Patient {pat_name} registered into hospital database.",
                    patient_id=p["id"],
                    patient_name=pat_name,
                    actor_name=p.get("assigned_doctor") or "Intake Specialist",
                    actor_role="staff",
                    created_at=created,
                    target_url=f"/profile?patientId={p['id']}"
                ))

        # 2. Eye tests completed
        eye_res = supabase.table("eye_test_sessions").select("id, patient_id, session_status, clinician_id, completed_at, created_at").order("created_at", desc=True).limit(50).execute()
        for es in eye_res.data or []:
            pid = es.get("patient_id")
            if pid in patient_ids and es.get("session_status") in ("COMPLETED", "READY_FOR_REVIEW"):
                pat = patient_map.get(pid, {})
                pat_name = pat.get("name") or pid
                activities.append(ActivityFeedItem(
                    id=f"act-et-{es.get('id')}",
                    activity_type="eye_test_completed",
                    description=f"Objective Eye Test completed for {pat_name}.",
                    patient_id=pid,
                    patient_name=pat_name,
                    actor_name=es.get("clinician_id") or "Telemetry Station",
                    actor_role="station",
                    created_at=es.get("completed_at") or es.get("created_at") or datetime.now().isoformat(),
                    target_url=f"/profile?patientId={pid}&tab=eye-tests"
                ))

        # 3. AI analyses generated
        analyses_res = supabase.table("ai_analyses").select("id, patient_id, created_at, eye_test_session_id").order("created_at", desc=True).limit(50).execute()
        for a in analyses_res.data or []:
            pid = a.get("patient_id")
            if pid in patient_ids:
                pat = patient_map.get(pid, {})
                pat_name = pat.get("name") or pid
                activities.append(ActivityFeedItem(
                    id=f"act-ana-{a.get('id')}",
                    activity_type="ai_analysis_generated",
                    description=f"AI-assisted telemetry biomarker analysis synthesized for {pat_name}.",
                    patient_id=pid,
                    patient_name=pat_name,
                    actor_name="Clinical AI Engine",
                    actor_role="ai",
                    created_at=a.get("created_at") or datetime.now().isoformat(),
                    target_url=f"/ai-insights?session_id={a.get('eye_test_session_id')}"
                ))

        # 4. Therapy recommendations created & reviewed
        recs_res = supabase.table("therapy_recommendations").select("id, patient_id, exercise_category, clinician_review_status, created_by, updated_at, created_at").order("created_at", desc=True).limit(50).execute()
        for r in recs_res.data or []:
            pid = r.get("patient_id")
            if pid in patient_ids:
                pat = patient_map.get(pid, {})
                pat_name = pat.get("name") or pid
                category = r.get("exercise_category", "Therapy Protocol")
                review_status = r.get("clinician_review_status", "pending")
                if review_status == "approved":
                    desc = f"Therapy recommendation '{category}' approved for {pat_name}."
                    act_type = "recommendation_approved"
                elif review_status == "rejected":
                    desc = f"Therapy recommendation '{category}' rejected for {pat_name}."
                    act_type = "recommendation_rejected"
                else:
                    desc = f"Therapy recommendation '{category}' generated for {pat_name}."
                    act_type = "recommendation_created"

                activities.append(ActivityFeedItem(
                    id=f"act-rec-{r.get('id')}",
                    activity_type=act_type,
                    description=desc,
                    patient_id=pid,
                    patient_name=pat_name,
                    actor_name=r.get("created_by") or "Clinical Specialist",
                    actor_role="clinician",
                    created_at=r.get("updated_at") or r.get("created_at") or datetime.now().isoformat(),
                    target_url=f"/profile?patientId={pid}&tab=therapy"
                ))

        # 5. Therapy sessions completed or abandoned
        sessions_res = supabase.table("therapy_sessions").select("id, patient_id, session_status, exercise_type, assigned_by, created_at").order("created_at", desc=True).limit(50).execute()
        for s in sessions_res.data or []:
            pid = s.get("patient_id")
            if pid in patient_ids:
                pat = patient_map.get(pid, {})
                pat_name = pat.get("name") or pid
                st = str(s.get("session_status", "")).lower()
                exercise = str(s.get("exercise_type") or "Exercise").replace("_", " ").title()
                if st == "completed":
                    desc = f"Completed {exercise} session for {pat_name}."
                    act_type = "session_completed"
                elif st == "abandoned":
                    desc = f"{exercise} session was abandoned for {pat_name}."
                    act_type = "session_abandoned"
                else:
                    continue

                activities.append(ActivityFeedItem(
                    id=f"act-sess-{s.get('id')}",
                    activity_type=act_type,
                    description=desc,
                    patient_id=pid,
                    patient_name=pat_name,
                    actor_name=s.get("assigned_by") or s.get("clinician_id") or "VR Headset",
                    actor_role="vr_station",
                    created_at=s.get("created_at") or datetime.now().isoformat(),
                    target_url=f"/profile?patientId={pid}&tab=therapy"
                ))

        # 6. Adaptive therapy difficulty updates from audit log
        audits_res = supabase.table("therapy_adaptation_audits").select("id, patient_id, previous_difficulty, new_difficulty, created_at, notes, action_type").order("created_at", desc=True).limit(50).execute()
        for au in audits_res.data or []:
            pid = au.get("patient_id")
            if pid in patient_ids:
                pat = patient_map.get(pid, {})
                pat_name = pat.get("name") or pid
                p_diff = au.get("previous_difficulty")
                n_diff = au.get("new_difficulty")
                action_type = au.get("action_type") or "difficulty_adjusted"
                desc = f"Difficulty updated for {pat_name}: Level {p_diff} -> Level {n_diff} ({action_type})."
                activities.append(ActivityFeedItem(
                    id=f"act-aud-{au.get('id')}",
                    activity_type="difficulty_updated",
                    description=desc,
                    patient_id=pid,
                    patient_name=pat_name,
                    actor_name=au.get("clinician_id") or au.get("applied_by") or "Adaptive Engine",
                    actor_role="adaptive_system",
                    created_at=au.get("created_at") or datetime.now().isoformat(),
                    target_url=f"/profile?patientId={pid}&tab=therapy"
                ))

        # 7. Clinician progress notes added
        notes_res = supabase.table("clinician_progress_notes").select("id, patient_id, clinician_name, note, created_at").order("created_at", desc=True).limit(50).execute()
        for no in notes_res.data or []:
            pid = no.get("patient_id")
            if pid in patient_ids:
                pat = patient_map.get(pid, {})
                pat_name = pat.get("name") or pid
                note_text = no.get("note") or no.get("title") or "Observation"
                activities.append(ActivityFeedItem(
                    id=f"act-note-{no.get('id')}",
                    activity_type="clinician_note_added",
                    description=f"Clinical note recorded for {pat_name}: '{note_text[:60]}'.",
                    patient_id=pid,
                    patient_name=pat_name,
                    actor_name=no.get("clinician_name") or no.get("author_name") or "Clinician",
                    actor_role="clinician",
                    created_at=no.get("created_at") or datetime.now().isoformat(),
                    target_url=f"/profile?patientId={pid}&tab=progress"
                ))

        # Sort descending by created_at
        activities.sort(key=lambda x: x.created_at, reverse=True)
        clipped = activities[:limit]

        return ActivityFeedResponse(
            items=clipped,
            total=len(activities)
        )

    @staticmethod
    def get_notifications(user: UserProfile) -> NotificationListResponse:
        scoped_patients = DashboardService._get_scoped_patients(user)
        patient_map = DashboardService._get_patient_map(scoped_patients)
        patient_ids = set(patient_map.keys())

        # Check existing notifications in table
        notif_res = supabase.table("notifications").select("*").execute()
        records = notif_res.data or []

        # Filter by patient scope or user hospital
        user_hosp = (user.hospital_name or user.clinic_name or "").strip().lower()
        filtered = []
        for n in records:
            pid = n.get("related_patient_id")
            hosp = (n.get("hospital_name") or "").strip().lower()
            if pid in patient_ids or (hosp and hosp == user_hosp) or not hosp:
                filtered.append(n)

        # If table is empty, generate active notifications dynamically from pending items
        if not filtered:
            pending_actions = DashboardService.get_pending_actions(user).items
            now_iso = datetime.now().isoformat()
            for pa in pending_actions[:10]:
                new_notif = {
                    "id": f"notif-{uuid.uuid4().hex[:10]}",
                    "user_id": user.id,
                    "hospital_name": user.hospital_name,
                    "title": pa.title,
                    "description": pa.reason,
                    "category": pa.action_type,
                    "related_patient_id": pa.patient_id,
                    "related_patient_name": pa.patient_name,
                    "priority": pa.priority,
                    "is_read": False,
                    "created_at": pa.created_at or now_iso,
                    "target_url": pa.target_route
                }
                supabase.table("notifications").insert(new_notif).execute()
                filtered.append(new_notif)

        # Map to NotificationResponse
        responses = [
            NotificationResponse(
                id=n.get("id"),
                title=n.get("title", "Clinical Notice"),
                description=n.get("description", ""),
                category=n.get("category", "general"),
                related_patient_id=n.get("related_patient_id"),
                related_patient_name=n.get("related_patient_name"),
                priority=n.get("priority", "medium"),
                is_read=bool(n.get("is_read", False)),
                created_at=n.get("created_at", datetime.now().isoformat()),
                target_url=n.get("target_url")
            )
            for n in filtered
        ]

        responses.sort(key=lambda x: x.created_at, reverse=True)
        unread_count = sum(1 for n in responses if not n.is_read)

        return NotificationListResponse(
            items=responses,
            unread_count=unread_count
        )

    @staticmethod
    def mark_notification_read(notification_id: str, user: UserProfile) -> Dict[str, Any]:
        supabase.table("notifications").update({"is_read": True}).eq("id", notification_id).execute()
        return {"status": "success", "id": notification_id, "is_read": True}

    @staticmethod
    def mark_all_notifications_read(user: UserProfile) -> Dict[str, Any]:
        notif_res = supabase.table("notifications").select("*").execute()
        for n in notif_res.data or []:
            supabase.table("notifications").update({"is_read": True}).eq("id", n["id"]).execute()
        return {"status": "success", "message": "All notifications marked as read."}
