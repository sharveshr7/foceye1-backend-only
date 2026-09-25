import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from app.core.supabase import supabase
from app.schemas.progress_schemas import (
    EyeTestTrendPoint,
    TherapyTrendPoint,
    MetricComparison,
    EyeTestsSummary,
    TherapySessionsSummary,
    SessionCompletionSummary,
    DataQualitySummary,
    PatientProgressOverview,
    AIProgressChangeItem,
    AIProgressSummaryOutput,
    AIProgressSummaryResponse,
    ClinicianProgressNoteResponse,
    TimelineItem,
)
from app.services.gemini_service import gemini_service

logger = logging.getLogger("foceye.patient_progress_service")


class PatientProgressService:
    @staticmethod
    def _verify_patient(patient_id: str) -> Dict[str, Any]:
        res = supabase.table("patients").select("*").eq("id", patient_id).execute()
        if not res.data or len(res.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient '{patient_id}' not found."
            )
        return res.data[0]

    @staticmethod
    def get_patient_progress(patient_id: str) -> PatientProgressOverview:
        PatientProgressService._verify_patient(patient_id)

        # 1. Fetch Eye Test Sessions and Results
        eye_sessions_res = supabase.table("eye_test_sessions").select("*").eq("patient_id", patient_id).execute()
        eye_sessions = eye_sessions_res.data or []
        eye_sessions.sort(key=lambda s: s.get("created_at") or s.get("test_date") or "", reverse=False)

        eye_results_res = supabase.table("eye_test_results").select("*").eq("patient_id", patient_id).execute()
        eye_results = eye_results_res.data or []

        # Map results by session_id
        results_by_session: Dict[str, List[Dict[str, Any]]] = {}
        for r in eye_results:
            sid = r.get("session_id")
            if sid:
                results_by_session.setdefault(sid, []).append(r)

        # 2. Fetch Therapy Sessions and Results
        therapy_sessions_res = supabase.table("therapy_sessions").select("*").eq("patient_id", patient_id).execute()
        therapy_sessions = therapy_sessions_res.data or []
        therapy_sessions.sort(key=lambda s: s.get("created_at") or "", reverse=False)

        therapy_results_res = supabase.table("therapy_session_results").select("*").eq("patient_id", patient_id).execute()
        therapy_results = therapy_results_res.data or []

        therapy_results_by_session: Dict[str, List[Dict[str, Any]]] = {}
        for tr in therapy_results:
            sid = tr.get("therapy_session_id")
            if sid:
                therapy_results_by_session.setdefault(sid, []).append(tr)

        # 3. Eye Tests Summary
        completed_eye_sessions = [s for s in eye_sessions if str(s.get("session_status", "")).upper() == "COMPLETED"]
        latest_eye_date = (
            (eye_sessions[-1].get("created_at") or eye_sessions[-1].get("test_date"))
            if eye_sessions else None
        )
        eye_summary = EyeTestsSummary(
            total_sessions=len(eye_sessions),
            completed_sessions=len(completed_eye_sessions),
            latest_session_date=latest_eye_date,
        )

        # 4. Therapy Sessions Summary
        completed_therapy = [s for s in therapy_sessions if s.get("session_status") == "completed"]
        stopped_therapy = [s for s in therapy_sessions if s.get("session_status") == "stopped"]
        abandoned_therapy = [s for s in therapy_sessions if s.get("session_status") == "abandoned"]
        latest_therapy_date = therapy_sessions[-1].get("created_at") if therapy_sessions else None

        therapy_summary = TherapySessionsSummary(
            total_sessions=len(therapy_sessions),
            completed_sessions=len(completed_therapy),
            stopped_sessions=len(stopped_therapy),
            abandoned_sessions=len(abandoned_therapy),
            latest_session_date=latest_therapy_date,
        )

        # 5. Session Completion (Rule: Do not invent adherence from incomplete data)
        recs_res = supabase.table("therapy_recommendations").select("*").eq("patient_id", patient_id).execute()
        recs = recs_res.data or []
        assigned_sessions_count: Optional[int] = None
        total_prescribed = 0
        for rec in recs:
            if str(rec.get("clinician_review_status", "")).lower() == "approved":
                val = rec.get("recommended_sessions") or rec.get("planned_sessions")
                if isinstance(val, (int, float)) and val > 0:
                    total_prescribed += int(val)

        if total_prescribed > 0:
            assigned_sessions_count = total_prescribed
            comp_pct = round((len(completed_therapy) / assigned_sessions_count) * 100, 1)
            completion_summary = SessionCompletionSummary(
                assigned_sessions=assigned_sessions_count,
                planned_sessions=assigned_sessions_count,
                completed_sessions=len(completed_therapy),
                stopped_sessions=len(stopped_therapy),
                completion_percentage=min(100.0, comp_pct),
                notice=f"{len(completed_therapy)} of {assigned_sessions_count} planned sessions completed.",
            )
        else:
            completion_summary = SessionCompletionSummary(
                assigned_sessions=None,
                planned_sessions=None,
                completed_sessions=len(completed_therapy),
                stopped_sessions=len(stopped_therapy),
                completion_percentage=None,
                notice="Planned session data unavailable. Session completion data is available; planned-session adherence is not yet configured.",
            )

        # 6. Data Quality Summary
        simulated_count = 0
        low_confidence_count = 0
        incomplete_count = (len(eye_sessions) - len(completed_eye_sessions)) + len(stopped_therapy) + len(abandoned_therapy)

        for s in eye_sessions:
            if s.get("is_simulated_data") or "simulated" in str(s.get("data_quality_status", "")).lower():
                simulated_count += 1

        for r in eye_results:
            conf = float(r.get("tracking_confidence") or 1.0)
            if conf < 0.80 or "low" in str(r.get("data_quality_status", "")).lower():
                low_confidence_count += 1
            if r.get("is_simulated_data"):
                simulated_count += 1

        for ts in therapy_sessions:
            if ts.get("is_simulated_data"):
                simulated_count += 1

        valid_count = max(0, (len(eye_results) + len(therapy_results)) - low_confidence_count)

        data_quality_summary = DataQualitySummary(
            valid_count=valid_count,
            low_confidence_count=low_confidence_count,
            incomplete_count=incomplete_count,
            simulated_count=simulated_count,
            notice="Data quality reflects recording reliability, not medical severity.",
        )

        # 7. Group Eye Test Trends by Test Type
        eye_test_trends: Dict[str, List[EyeTestTrendPoint]] = {
            "FIXATION_STABILITY": [],
            "SMOOTH_PURSUIT": [],
            "SACCADE": [],
            "GAZE_ACCURACY": [],
        }

        for s in eye_sessions:
            sid = s.get("id")
            s_date = s.get("created_at") or s.get("test_date") or ""
            s_res_list = results_by_session.get(sid, [])
            for r in s_res_list:
                raw_type = str(r.get("test_type", "")).upper()
                target_key = None
                if "FIXATION" in raw_type:
                    target_key = "FIXATION_STABILITY"
                elif "PURSUIT" in raw_type:
                    target_key = "SMOOTH_PURSUIT"
                elif "SACCADE" in raw_type:
                    target_key = "SACCADE"
                elif "GAZE" in raw_type or "ACCURACY" in raw_type:
                    target_key = "GAZE_ACCURACY"

                if target_key:
                    point = EyeTestTrendPoint(
                        session_id=sid,
                        test_date=s_date,
                        test_type=target_key,
                        score=float(r.get("score") or 0.0),
                        error_value=float(r["error_value"]) if r.get("error_value") is not None else None,
                        duration=float(r.get("duration") or 0.0),
                        reaction_time=float(r["reaction_time"]) if r.get("reaction_time") is not None else None,
                        tracking_confidence=float(r.get("tracking_confidence") or 0.85),
                        is_simulated_data=bool(r.get("is_simulated_data", False)),
                        data_quality_status=str(r.get("data_quality_status") or "Valid Data"),
                    )
                    eye_test_trends[target_key].append(point)

        # 8. Baseline vs. Latest Comparison
        baseline_comparisons: List[MetricComparison] = []

        # Fixation Stability Comparison
        fix_points = eye_test_trends["FIXATION_STABILITY"]
        if fix_points:
            baseline = fix_points[0]
            latest = fix_points[-1]
            diff = round(latest.score - baseline.score, 2)
            pct_chg = round((diff / baseline.score) * 100, 1) if baseline.score != 0 else None
            rel = "Sufficient Data" if len(fix_points) >= 2 and latest.tracking_confidence >= 0.80 else ("Single Session" if len(fix_points) == 1 else "Low Confidence")
            baseline_comparisons.append(MetricComparison(
                metric_name="Fixation Stability Score",
                test_type="Fixation Stability",
                unit="%",
                baseline_value=baseline.score,
                latest_value=latest.score,
                current_value=latest.score,
                trend_direction="improving" if diff > 0 else ("declining" if diff < 0 else "stable"),
                recorded_change=diff,
                percentage_change=pct_chg,
                sessions_between=max(0, len(fix_points) - 2),
                comparison_reliability=rel,
                higher_is_better=True,
            ))
        else:
            baseline_comparisons.append(MetricComparison(
                metric_name="Fixation Stability Score",
                test_type="Fixation Stability",
                unit="%",
                comparison_reliability="No Data",
                higher_is_better=True,
            ))

        # Smooth Pursuit Tracking Error Comparison
        pursuit_points = eye_test_trends["SMOOTH_PURSUIT"]
        if pursuit_points:
            baseline = pursuit_points[0]
            latest = pursuit_points[-1]
            base_err = baseline.error_value if baseline.error_value is not None else round(100.0 - baseline.score, 2)
            lat_err = latest.error_value if latest.error_value is not None else round(100.0 - latest.score, 2)
            diff = round(lat_err - base_err, 2)
            pct_chg = round((diff / base_err) * 100, 1) if base_err != 0 else None
            rel = "Sufficient Data" if len(pursuit_points) >= 2 and latest.tracking_confidence >= 0.80 else ("Single Session" if len(pursuit_points) == 1 else "Low Confidence")
            baseline_comparisons.append(MetricComparison(
                metric_name="Smooth Pursuit Error",
                test_type="Smooth Pursuit",
                unit="px",
                baseline_value=base_err,
                latest_value=lat_err,
                current_value=lat_err,
                trend_direction="improving" if diff < 0 else ("declining" if diff > 0 else "stable"),
                recorded_change=diff,
                percentage_change=pct_chg,
                sessions_between=max(0, len(pursuit_points) - 2),
                comparison_reliability=rel,
                higher_is_better=False,
            ))
        else:
            baseline_comparisons.append(MetricComparison(
                metric_name="Smooth Pursuit Error",
                test_type="Smooth Pursuit",
                unit="px",
                comparison_reliability="No Data",
                higher_is_better=False,
            ))

        # Saccadic Latency Comparison
        saccade_points = eye_test_trends["SACCADE"]
        if saccade_points:
            baseline = saccade_points[0]
            latest = saccade_points[-1]
            base_rt = baseline.reaction_time if baseline.reaction_time is not None else 250.0
            lat_rt = latest.reaction_time if latest.reaction_time is not None else 250.0
            diff = round(lat_rt - base_rt, 1)
            pct_chg = round((diff / base_rt) * 100, 1) if base_rt != 0 else None
            rel = "Sufficient Data" if len(saccade_points) >= 2 and latest.tracking_confidence >= 0.80 else ("Single Session" if len(saccade_points) == 1 else "Low Confidence")
            baseline_comparisons.append(MetricComparison(
                metric_name="Saccadic Response Time",
                test_type="Saccade Assessment",
                unit="ms",
                baseline_value=base_rt,
                latest_value=lat_rt,
                current_value=lat_rt,
                trend_direction="improving" if diff < 0 else ("declining" if diff > 0 else "stable"),
                recorded_change=diff,
                percentage_change=pct_chg,
                sessions_between=max(0, len(saccade_points) - 2),
                comparison_reliability=rel,
                higher_is_better=False,
            ))
        else:
            baseline_comparisons.append(MetricComparison(
                metric_name="Saccadic Response Time",
                test_type="Saccade Assessment",
                unit="ms",
                comparison_reliability="No Data",
                higher_is_better=False,
            ))

        # Gaze Accuracy Comparison
        gaze_points = eye_test_trends["GAZE_ACCURACY"]
        if gaze_points:
            baseline = gaze_points[0]
            latest = gaze_points[-1]
            diff = round(latest.score - baseline.score, 2)
            pct_chg = round((diff / baseline.score) * 100, 1) if baseline.score != 0 else None
            rel = "Sufficient Data" if len(gaze_points) >= 2 and latest.tracking_confidence >= 0.80 else ("Single Session" if len(gaze_points) == 1 else "Low Confidence")
            baseline_comparisons.append(MetricComparison(
                metric_name="Gaze Target Accuracy",
                test_type="Gaze Accuracy",
                unit="%",
                baseline_value=baseline.score,
                latest_value=latest.score,
                current_value=latest.score,
                trend_direction="improving" if diff > 0 else ("declining" if diff < 0 else "stable"),
                recorded_change=diff,
                percentage_change=pct_chg,
                sessions_between=max(0, len(gaze_points) - 2),
                comparison_reliability=rel,
                higher_is_better=True,
            ))
        else:
            baseline_comparisons.append(MetricComparison(
                metric_name="Gaze Target Accuracy",
                test_type="Gaze Accuracy",
                unit="%",
                comparison_reliability="No Data",
                higher_is_better=True,
            ))

        # 9. Therapy Performance Trends
        therapy_trends: List[TherapyTrendPoint] = []
        for ts in therapy_sessions:
            sid = ts.get("id")
            s_date = ts.get("created_at") or ""
            t_res_list = therapy_results_by_session.get(sid, [])
            if t_res_list:
                tr = t_res_list[0]
                therapy_trends.append(TherapyTrendPoint(
                    session_id=sid,
                    session_date=s_date,
                    exercise_type=ts.get("exercise_type") or tr.get("exercise_type") or "fixation_target",
                    score=float(tr.get("score") or tr.get("accuracy") or 0.0),
                    accuracy=float(tr.get("accuracy") or tr.get("score") or 0.0),
                    error_value=float(tr["error_value"]) if tr.get("error_value") is not None else None,
                    reaction_time=float(tr["reaction_time"]) if tr.get("reaction_time") is not None else None,
                    actual_duration_seconds=int(ts.get("actual_duration_seconds") or 0),
                    planned_duration_seconds=int(ts.get("planned_duration_seconds") or 300),
                    completion_percentage=float(tr.get("completion_percentage") or 0.0),
                    tracking_confidence=float(tr.get("tracking_confidence") or ts.get("tracking_confidence") or 0.85),
                    target_loss_events=int(tr.get("target_loss_events") or 0),
                    is_simulated_data=bool(ts.get("is_simulated_data", False)),
                    data_quality_status=str(tr.get("data_quality_status") or ts.get("data_quality_status") or "optimal"),
                    session_status=str(ts.get("session_status") or "completed"),
                ))
            else:
                therapy_trends.append(TherapyTrendPoint(
                    session_id=sid,
                    session_date=s_date,
                    exercise_type=ts.get("exercise_type") or "fixation_target",
                    score=0.0,
                    accuracy=0.0,
                    actual_duration_seconds=int(ts.get("actual_duration_seconds") or 0),
                    planned_duration_seconds=int(ts.get("planned_duration_seconds") or 300),
                    completion_percentage=0.0,
                    tracking_confidence=0.85,
                    is_simulated_data=bool(ts.get("is_simulated_data", False)),
                    data_quality_status=str(ts.get("data_quality_status") or "incomplete"),
                    session_status=str(ts.get("session_status") or "assigned"),
                ))

        is_simulated = simulated_count > 0 or (len(eye_sessions) == 0 and len(therapy_sessions) == 0)
        provenance = "Demo/Simulated Data" if is_simulated else "Optical Sensor Telemetry"

        return PatientProgressOverview(
            patient_id=patient_id,
            total_eye_tests=eye_summary.total_sessions,
            total_therapy_sessions=therapy_summary.total_sessions,
            eye_tests_summary=eye_summary,
            therapy_sessions_summary=therapy_summary,
            completion_summary=completion_summary,
            data_quality_summary=data_quality_summary,
            baseline_comparisons=baseline_comparisons,
            eye_test_trends=eye_test_trends,
            therapy_trends=therapy_trends,
            provenance_label=provenance,
            is_simulated_data=is_simulated,
            last_updated=datetime.now().isoformat(),
        )

    @staticmethod
    def get_eye_test_trends(patient_id: str) -> Dict[str, Any]:
        overview = PatientProgressService.get_patient_progress(patient_id)
        return {
            "patient_id": patient_id,
            "trends": overview.eye_test_trends,
            "summary": overview.eye_tests_summary,
            "is_simulated_data": overview.is_simulated_data,
        }

    @staticmethod
    def get_therapy_trends(patient_id: str) -> Dict[str, Any]:
        overview = PatientProgressService.get_patient_progress(patient_id)
        return {
            "patient_id": patient_id,
            "trends": overview.therapy_trends,
            "summary": overview.therapy_sessions_summary,
            "completion": overview.completion_summary,
            "is_simulated_data": overview.is_simulated_data,
        }

    @staticmethod
    def get_patient_timeline(patient_id: str) -> List[TimelineItem]:
        patient = PatientProgressService._verify_patient(patient_id)
        timeline: List[TimelineItem] = []

        # 1. Patient Registration
        reg_date = patient.get("created_at") or patient.get("dateOfBirth") or datetime.utcnow().isoformat()
        timeline.append(TimelineItem(
            id=f"evt-reg-{patient['id']}",
            event_type="PATIENT_REGISTERED",
            date_time=reg_date,
            title="Patient Registered",
            short_description=f"Patient {patient.get('first_name', '')} {patient.get('last_name', '')} registered at {patient.get('hospital_id', 'hospital')}.",
            related_id=patient["id"],
            related_type="patient",
            status="Active",
        ))

        # 2. Eye Test Sessions
        eye_res = supabase.table("eye_test_sessions").select("*").eq("patient_id", patient_id).execute()
        for s in eye_res.data or []:
            d = s.get("created_at") or s.get("test_date") or ""
            status_val = s.get("session_status") or "COMPLETED"
            timeline.append(TimelineItem(
                id=f"evt-eye-{s.get('id')}",
                event_type="EYE_TEST_COMPLETED" if status_val.upper() == "COMPLETED" else "EYE_TEST_SESSION",
                date_time=d,
                title=f"Eye Test {status_val.capitalize()}",
                short_description=f"Standardized eye assessment session ({s.get('id')}).",
                related_id=s.get("id"),
                related_type="eye_test_session",
                status=status_val,
                data_quality_status=s.get("data_quality_status", "Valid Data"),
                is_simulated_data=bool(s.get("is_simulated_data", False)),
            ))

        # 3. AI Analysis Events
        ai_res = supabase.table("ai_analyses").select("*").eq("patient_id", patient_id).execute()
        for a in ai_res.data or []:
            d = a.get("created_at") or ""
            timeline.append(TimelineItem(
                id=f"evt-ai-{a.get('id')}",
                event_type="AI_ANALYSIS_GENERATED",
                date_time=d,
                title="AI Analysis Generated",
                short_description="AI analysis synthesized oculomotor telemetry with non-diagnostic guardrails.",
                related_id=a.get("id"),
                related_type="ai_analysis",
                status="completed",
                is_simulated_data=bool(a.get("is_simulated_data", False)),
            ))

        # 4. Therapy Recommendations
        rec_res = supabase.table("therapy_recommendations").select("*").eq("patient_id", patient_id).execute()
        for r in rec_res.data or []:
            d = r.get("created_at") or ""
            cat = r.get("exercise_category") or "Visual Exercise"
            rev_status = str(r.get("clinician_review_status") or "pending").lower()
            timeline.append(TimelineItem(
                id=f"evt-rec-{r.get('id')}",
                event_type="THERAPY_RECOMMENDATION_APPROVED" if rev_status == "approved" else "THERAPY_RECOMMENDATION_GENERATED",
                date_time=d,
                title=f"Therapy Recommendation {rev_status.capitalize()}",
                short_description=f"Recommendation for {cat} ({rev_status}).",
                related_id=r.get("id"),
                related_type="therapy_recommendation",
                status=rev_status,
                is_simulated_data=bool(r.get("is_simulated_data", False)),
            ))

        # 5. Therapy Sessions
        ts_res = supabase.table("therapy_sessions").select("*").eq("patient_id", patient_id).execute()
        for ts in ts_res.data or []:
            d = ts.get("created_at") or ""
            s_status = ts.get("session_status") or "completed"
            timeline.append(TimelineItem(
                id=f"evt-ts-{ts.get('id')}",
                event_type="THERAPY_SESSION_COMPLETED" if s_status == "completed" else "THERAPY_SESSION_LOGGED",
                date_time=d,
                title=f"Therapy Session {s_status.capitalize()}",
                short_description=f"Exercise protocol {ts.get('exercise_type', '')} ({ts.get('actual_duration_seconds', 0)}s duration).",
                related_id=ts.get("id"),
                related_type="therapy_session",
                status=s_status,
                data_quality_status=ts.get("data_quality_status", "optimal"),
                is_simulated_data=bool(ts.get("is_simulated_data", False)),
            ))

        # 6. Clinician Progress Notes
        notes_res = supabase.table("clinician_progress_notes").select("*").eq("patient_id", patient_id).execute()
        for n in notes_res.data or []:
            d = n.get("created_at") or ""
            author = n.get("clinician_name") or "Clinician"
            timeline.append(TimelineItem(
                id=f"evt-note-{n.get('id')}",
                event_type="CLINICIAN_REVIEW_ADDED",
                date_time=d,
                title="Clinician Review Added",
                short_description=f"Observation note recorded by {author}: {n.get('notes', '')[:60]}...",
                related_id=n.get("id"),
                related_type="clinician_note",
                status="recorded",
            ))

        # 7. AI Progress Summaries
        ai_prog_res = supabase.table("ai_progress_summaries").select("*").eq("patient_id", patient_id).execute()
        for p in ai_prog_res.data or []:
            d = p.get("created_at") or ""
            rev = p.get("clinician_review_status", "pending")
            timeline.append(TimelineItem(
                id=f"evt-prog-{p.get('id')}",
                event_type="PROGRESS_SUMMARY_GENERATED",
                date_time=d,
                title=f"AI Progress Summary ({rev.capitalize()})",
                short_description=f"Longitudinal progress summary synthesized. Status: {rev}.",
                related_id=p.get("id"),
                related_type="ai_progress_summary",
                status=rev,
                is_simulated_data=bool(p.get("is_simulated_data", False)),
            ))

        # Sort chronologically (newest first)
        timeline.sort(key=lambda item: item.date_time, reverse=True)
        return timeline

    @staticmethod
    async def generate_ai_progress_summary(
        patient_id: str,
        clinician_notes: Optional[str] = None,
        clinician_id: Optional[str] = None
    ) -> AIProgressSummaryResponse:
        overview = PatientProgressService.get_patient_progress(patient_id)
        now_iso = datetime.now().isoformat()
        summary_id = f"pps-{uuid.uuid4().hex[:12]}"

        # Prepare telemetry input summary
        input_summary = {
            "patient_id": patient_id,
            "total_eye_tests": overview.eye_tests_summary.total_sessions,
            "total_therapy": overview.therapy_sessions_summary.total_sessions,
            "completed_therapy": overview.therapy_sessions_summary.completed_sessions,
            "data_quality": {
                "valid_count": overview.data_quality_summary.valid_count,
                "low_confidence_count": overview.data_quality_summary.low_confidence_count,
                "incomplete_count": overview.data_quality_summary.incomplete_count,
                "simulated_count": overview.data_quality_summary.simulated_count,
            },
            "comparisons": [
                {
                    "metric": c.metric_name,
                    "unit": c.unit,
                    "baseline": c.baseline_value,
                    "latest": c.latest_value,
                    "change": c.recorded_change,
                    "reliability": c.comparison_reliability,
                }
                for c in overview.baseline_comparisons
            ],
            "clinician_notes": clinician_notes or "",
        }

        # Build algorithmic structured output first (guaranteed fallback adhering strictly to Section 8)
        recorded_changes: List[AIProgressChangeItem] = []
        stable_areas: List[str] = []
        inconsistent_areas: List[str] = []
        missing_info: List[str] = []
        review_points: List[str] = []
        observed_trends: List[str] = []

        for cmp in overview.baseline_comparisons:
            if cmp.baseline_value is not None and cmp.latest_value is not None and cmp.recorded_change is not None:
                chg = cmp.recorded_change
                if abs(chg) > 0.05:
                    direction = "higher" if chg > 0 else "lower"
                    area_name = cmp.test_type.lower().replace(" ", "_")
                    desc = f"The latest recorded {cmp.metric_name.lower()} is {direction} than the baseline value ({chg:+} {cmp.unit})."
                    conf_level = "moderate" if cmp.comparison_reliability == "Sufficient Data" else "low"
                    recorded_changes.append(AIProgressChangeItem(
                        area=area_name,
                        metric=cmp.metric_name.lower().replace(" ", "_"),
                        baseline_value=cmp.baseline_value,
                        latest_value=cmp.latest_value,
                        change=chg,
                        description=desc,
                        confidence=conf_level,
                    ))
                    observed_trends.append(f"{cmp.metric_name}: Baseline {cmp.baseline_value}{cmp.unit} vs Latest {cmp.latest_value}{cmp.unit} ({desc})")
                else:
                    stable_areas.append(f"{cmp.metric_name} remained stable between baseline ({cmp.baseline_value}{cmp.unit}) and latest recording ({cmp.latest_value}{cmp.unit}).")
                    observed_trends.append(f"{cmp.metric_name}: Stable telemetry ({cmp.baseline_value}{cmp.unit}).")
            else:
                missing_info.append(f"Insufficient baseline or follow-up telemetry for {cmp.metric_name}.")

        if overview.data_quality_summary.low_confidence_count > 0:
            inconsistent_areas.append(
                f"{overview.data_quality_summary.low_confidence_count} session result(s) demonstrated tracking confidence below 80% or head motion artifacts."
            )

        if overview.data_quality_summary.simulated_count > 0:
            inconsistent_areas.append(
                f"{overview.data_quality_summary.simulated_count} session(s) utilized demo/simulated tracking."
            )

        if overview.completion_summary.assigned_sessions is None:
            missing_info.append("Planned therapy assignment quota is not yet configured.")

        review_points.append("Verify calibration stability and patient positioning during oculomotor assessments.")
        review_points.append("Review whether recorded performance changes correlate with functional reading or visual stamina.")
        if clinician_notes:
            review_points.append(f"Clinician observation to correlate: {clinician_notes}")

        limitations = [
            "The summary is based only on recorded sessions.",
            "Recorded changes do not establish treatment efficacy.",
            "Differences may be influenced by calibration, fatigue, or ambient lighting.",
            "This output is not a diagnosis or clinical cure determination.",
        ]

        overall_summary = (
            f"The available records show changes in selected performance measurements across "
            f"{overview.eye_tests_summary.total_sessions} eye test(s) and {overview.therapy_sessions_summary.total_sessions} therapy session(s). "
            f"Recorded telemetry reflects sensor measurements and requires clinician evaluation."
        )

        structured_output = AIProgressSummaryOutput(
            summary_status="completed",
            overall_summary=overall_summary,
            recorded_changes=recorded_changes,
            stable_areas=stable_areas,
            inconsistent_or_low_reliability_areas=inconsistent_areas,
            missing_information=missing_info,
            clinician_review_points=review_points,
            limitations=limitations,
        )

        model_used = "deterministic-clinical-rule-engine"

        # If live Gemini is configured, invoke Gemini with strict non-diagnostic instructions
        if gemini_service.is_configured:
            system_instruction = (
                "You are an AI clinical telemetry progress analyzer for eye care professionals. "
                "CRITICAL NON-DIAGNOSTIC SAFETY RULES:\n"
                "1. NEVER diagnose any disease or clinical condition.\n"
                "2. NEVER predict disease outcomes, clinical prognosis, or cure.\n"
                "3. NEVER claim treatment success or state that therapy is medically effective.\n"
                "4. NEVER say 'The patient has recovered', 'The patient is cured', 'The treatment worked', or 'The disease has improved'.\n"
                "5. Use cautious, neutral, objective phrasing: 'The recorded measurements show...', 'The available sessions indicate...', 'The data suggests a change in...'.\n"
                "6. Output strictly valid JSON matching the required schema."
            )
            prompt = (
                f"Analyze the following longitudinal eye tracking and therapy telemetry for Patient ID {patient_id}.\n\n"
                f"Input Telemetry:\n{input_summary}\n\n"
                "Output must follow this JSON schema:\n"
                "{\n"
                '  "summary_status": "completed",\n'
                '  "overall_summary": string,\n'
                '  "recorded_changes": [{"area": string, "metric": string, "baseline_value": number, "latest_value": number, "change": number, "description": string, "confidence": string}],\n'
                '  "stable_areas": [string],\n'
                '  "inconsistent_or_low_reliability_areas": [string],\n'
                '  "missing_information": [string],\n'
                '  "clinician_review_points": [string],\n'
                '  "limitations": [string]\n'
                "}"
            )
            try:
                gemini_data, model_name, err = await gemini_service.generate_json(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    temperature=0.1
                )
                if gemini_data and isinstance(gemini_data, dict) and "overall_summary" in gemini_data:
                    # Validate and parse
                    changes = [
                        AIProgressChangeItem(**item) for item in gemini_data.get("recorded_changes", [])
                        if isinstance(item, dict) and "area" in item and "metric" in item
                    ]
                    ret_limitations = list(gemini_data.get("limitations", limitations))
                    # Ensure mandatory Section 8 non-diagnostic limitations are always present
                    for mand_lim in limitations:
                        if not any(mand_lim.lower() in l.lower() for l in ret_limitations):
                            ret_limitations.append(mand_lim)

                    structured_output = AIProgressSummaryOutput(
                        summary_status="completed",
                        overall_summary=str(gemini_data.get("overall_summary", overall_summary)),
                        recorded_changes=changes if changes else recorded_changes,
                        stable_areas=list(gemini_data.get("stable_areas", stable_areas)),
                        inconsistent_or_low_reliability_areas=list(gemini_data.get("inconsistent_or_low_reliability_areas", inconsistent_areas)),
                        missing_information=list(gemini_data.get("missing_information", missing_info)),
                        clinician_review_points=list(gemini_data.get("clinician_review_points", review_points)),
                        limitations=ret_limitations,
                    )
                    model_used = model_name or "gemini-3.5-flash-lite"
            except Exception as e:
                logger.warning(f"Gemini AI progress summary fallback applied: {e}")

        # Summary text for text displays
        summary_text_lines = [
            f"Longitudinal Telemetry Review for Patient {patient_id}.",
            structured_output.overall_summary,
            "\nRecorded Changes:",
        ]
        for c in structured_output.recorded_changes:
            summary_text_lines.append(f"- {c.metric}: Baseline {c.baseline_value} -> Latest {c.latest_value} ({c.change:+}). {c.description}")
        if structured_output.stable_areas:
            summary_text_lines.append("\nStable Areas:")
            for s in structured_output.stable_areas:
                summary_text_lines.append(f"- {s}")
        if structured_output.limitations:
            summary_text_lines.append("\nLimitations:")
            for lim in structured_output.limitations:
                summary_text_lines.append(f"- {lim}")

        summary_text = "\n".join(summary_text_lines)
        remarks = f"Recording reliability status: {overview.data_quality_summary.valid_count} valid point(s), {overview.data_quality_summary.simulated_count} simulated data session(s)."

        record_dict = {
            "id": summary_id,
            "patient_id": patient_id,
            "source_session_ids_json": [s.session_id for s in overview.therapy_trends] + [p.session_id for series in overview.eye_test_trends.values() for p in series],
            "summary_status": "completed",
            "model_name": model_used,
            "input_summary_json": input_summary,
            "output_json": structured_output.model_dump(),
            "data_quality_status": "Simulated Data" if overview.is_simulated_data else "Valid Data",
            "is_simulated_data": overview.is_simulated_data,
            "clinician_review_status": "pending",
            "clinician_notes": clinician_notes,
            "created_by": clinician_id or "attending_clinician",
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        # Save to both tables for full persistence & backwards compatibility
        supabase.table("ai_progress_summaries").insert(record_dict).execute()
        supabase.table("patient_progress_summaries").insert({
            "id": summary_id,
            "patient_id": patient_id,
            "summary_text": summary_text,
            "observed_trends": observed_trends,
            "data_quality_remarks": remarks,
            "is_simulated_data": overview.is_simulated_data,
            "created_at": now_iso,
        }).execute()

        return AIProgressSummaryResponse(
            id=summary_id,
            patient_id=patient_id,
            summary_text=summary_text,
            observed_trends=observed_trends,
            structured_output=structured_output,
            data_quality_remarks=remarks,
            is_simulated_data=overview.is_simulated_data,
            model_name=model_used,
            clinician_review_status="pending",
            clinician_notes=clinician_notes,
            generated_at=now_iso,
        )

    @staticmethod
    def get_latest_ai_summary(patient_id: str) -> Optional[AIProgressSummaryResponse]:
        PatientProgressService._verify_patient(patient_id)
        res = supabase.table("ai_progress_summaries").select("*").eq("patient_id", patient_id).execute()
        records = res.data or []
        if not records:
            # Check fallback table
            fb_res = supabase.table("patient_progress_summaries").select("*").eq("patient_id", patient_id).execute()
            fb_records = fb_res.data or []
            if not fb_records:
                return None
            fb_records.sort(key=lambda r: r.get("created_at", ""), reverse=True)
            top = fb_records[0]
            return AIProgressSummaryResponse(
                id=top.get("id"),
                patient_id=patient_id,
                summary_text=top.get("summary_text", ""),
                observed_trends=top.get("observed_trends", []),
                data_quality_remarks=top.get("data_quality_remarks", ""),
                is_simulated_data=bool(top.get("is_simulated_data", False)),
                generated_at=top.get("created_at", datetime.now().isoformat()),
            )

        records.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        latest = records[0]

        out_data = latest.get("output_json") or {}
        structured = AIProgressSummaryOutput(**out_data) if out_data else None

        return AIProgressSummaryResponse(
            id=latest.get("id"),
            patient_id=patient_id,
            summary_text=latest.get("output_json", {}).get("overall_summary", "Longitudinal progress telemetry review."),
            observed_trends=[c.description for c in structured.recorded_changes] if structured else [],
            structured_output=structured,
            data_quality_remarks=f"Data status: {latest.get('data_quality_status', 'Valid Data')}",
            is_simulated_data=bool(latest.get("is_simulated_data", False)),
            model_name=latest.get("model_name", "gemini-3.5-flash-lite"),
            clinician_review_status=latest.get("clinician_review_status", "pending"),
            clinician_notes=latest.get("clinician_notes"),
            generated_at=latest.get("created_at", datetime.now().isoformat()),
        )

    @staticmethod
    def review_ai_summary(
        summary_id: str,
        clinician_id: str,
        review_status: str,
        clinician_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        valid_statuses = {"pending", "reviewed", "flagged", "dismissed"}
        if review_status.lower() not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid review status '{review_status}'. Must be one of: {', '.join(valid_statuses)}"
            )

        updates = {
            "clinician_review_status": review_status.lower(),
            "updated_at": datetime.now().isoformat(),
        }
        if clinician_notes is not None:
            updates["clinician_notes"] = clinician_notes

        res = supabase.table("ai_progress_summaries").update(updates).eq("id", summary_id).execute()
        return {
            "summary_id": summary_id,
            "clinician_review_status": review_status.lower(),
            "clinician_notes": clinician_notes,
            "reviewed_by": clinician_id,
            "updated_at": updates["updated_at"],
            "message": "AI Progress Summary review updated successfully."
        }

    @staticmethod
    def add_clinician_note(
        patient_id: str,
        clinician_id: str,
        clinician_name: str,
        notes: str,
        related_session_id: Optional[str] = None,
        follow_up_date: Optional[str] = None
    ) -> ClinicianProgressNoteResponse:
        PatientProgressService._verify_patient(patient_id)
        now_iso = datetime.now().isoformat()
        note_id = f"cpn-{uuid.uuid4().hex[:12]}"

        record = {
            "id": note_id,
            "patient_id": patient_id,
            "clinician_id": clinician_id,
            "clinician_name": clinician_name,
            "notes": notes,
            "related_session_id": related_session_id,
            "follow_up_date": follow_up_date,
            "created_at": now_iso,
        }

        supabase.table("clinician_progress_notes").insert(record).execute()
        return ClinicianProgressNoteResponse(**record)

    @staticmethod
    def get_clinician_notes(patient_id: str) -> List[ClinicianProgressNoteResponse]:
        PatientProgressService._verify_patient(patient_id)
        res = supabase.table("clinician_progress_notes").select("*").eq("patient_id", patient_id).execute()
        notes = res.data or []
        notes.sort(key=lambda n: n.get("created_at", ""), reverse=True)
        return [ClinicianProgressNoteResponse(**n) for n in notes]
