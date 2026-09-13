"""
Adaptive Therapy Service
Rule-based, deterministic difficulty evaluation engine for VR visual therapy exercises.
Strictly non-diagnostic and clinical decision-support only.
"""

from datetime import datetime, date
import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import HTTPException, status

from app.core.supabase import supabase
from app.models.adaptive_therapy import (
    AdaptiveTherapyConfig,
    TherapyAdaptationRecommendation,
    TherapyAdaptationAudit,
)
from app.schemas.adaptive_therapy_schemas import (
    AdaptiveTherapyConfigCreate,
    AdaptiveTherapyConfigUpdate,
    TherapyAdaptationReviewRequest,
)

logger = logging.getLogger("foceye.adaptive_therapy")

DEFAULT_MIN_DIFFICULTY = 1
DEFAULT_MAX_DIFFICULTY = 5
DEFAULT_STARTING_DIFFICULTY = 2
DEFAULT_PROGRESSION_THRESHOLD = 85.0
DEFAULT_REGRESSION_THRESHOLD = 50.0
DEFAULT_STEP_SIZE = 1
DEFAULT_MIN_SESSIONS = 2
DEFAULT_MAX_DAILY_INCREASE = 1


class AdaptiveTherapyService:
    @staticmethod
    def _verify_patient(patient_id: str) -> Dict[str, Any]:
        res = supabase.table("patients").select("*").eq("id", patient_id).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient '{patient_id}' not found."
            )
        return res.data[0]

    @staticmethod
    def get_or_create_config(
        patient_id: str,
        exercise_id: str = "horizontal_moving_target",
        clinician_id: Optional[str] = None
    ) -> Dict[str, Any]:
        AdaptiveTherapyService._verify_patient(patient_id)

        res = supabase.table("adaptive_therapy_configs").select("*").eq("patient_id", patient_id).execute()
        configs = res.data or []
        for c in configs:
            if c.get("exercise_id") == exercise_id:
                c["notice"] = "Controlled rule-based difficulty adaptation. Does not diagnose or determine recovery. Follow clinician guidance."
                return c

        # Create safe default configuration
        now_iso = datetime.now().isoformat()
        config_id = f"atc-{uuid.uuid4().hex[:12]}"
        record = {
            "id": config_id,
            "patient_id": patient_id,
            "therapy_assignment_id": None,
            "exercise_id": exercise_id,
            "enabled": True,
            "adaptive_mode": "controlled_automatic",
            "minimum_difficulty": DEFAULT_MIN_DIFFICULTY,
            "maximum_difficulty": DEFAULT_MAX_DIFFICULTY,
            "starting_difficulty": DEFAULT_STARTING_DIFFICULTY,
            "current_difficulty": DEFAULT_STARTING_DIFFICULTY,
            "progression_threshold": DEFAULT_PROGRESSION_THRESHOLD,
            "regression_threshold": DEFAULT_REGRESSION_THRESHOLD,
            "step_size": DEFAULT_STEP_SIZE,
            "minimum_sessions_before_adaptation": DEFAULT_MIN_SESSIONS,
            "max_daily_difficulty_increase": DEFAULT_MAX_DAILY_INCREASE,
            "clinician_approval_required": True,
            "created_by": clinician_id or "clinician",
            "created_at": now_iso,
            "updated_at": now_iso,
            "notice": "Controlled rule-based difficulty adaptation. Does not diagnose or determine recovery. Follow clinician guidance."
        }
        supabase.table("adaptive_therapy_configs").insert(record).execute()

        # Audit initial configuration
        audit_id = f"taa-{uuid.uuid4().hex[:12]}"
        audit_record = {
            "id": audit_id,
            "patient_id": patient_id,
            "exercise_id": exercise_id,
            "previous_difficulty": DEFAULT_STARTING_DIFFICULTY,
            "new_difficulty": DEFAULT_STARTING_DIFFICULTY,
            "change_type": "initial_setup",
            "trigger": "initial_setup",
            "source_recommendation_id": None,
            "applied_by": clinician_id or "system",
            "applied_at": now_iso,
            "notes": "Initial adaptive difficulty configuration established with safe defaults."
        }
        supabase.table("therapy_adaptation_audits").insert(audit_record).execute()

        return record

    @staticmethod
    def get_patient_configs(patient_id: str) -> List[Dict[str, Any]]:
        AdaptiveTherapyService._verify_patient(patient_id)
        res = supabase.table("adaptive_therapy_configs").select("*").eq("patient_id", patient_id).execute()
        configs = res.data or []
        for c in configs:
            c["notice"] = "Controlled rule-based difficulty adaptation. Does not diagnose or determine recovery. Follow clinician guidance."
        return configs

    @staticmethod
    def create_config(payload: AdaptiveTherapyConfigCreate, clinician_id: Optional[str] = None) -> Dict[str, Any]:
        AdaptiveTherapyService._verify_patient(payload.patient_id)

        # Check existing config for same patient & exercise
        res = supabase.table("adaptive_therapy_configs").select("*").eq("patient_id", payload.patient_id).execute()
        for existing in (res.data or []):
            if existing.get("exercise_id") == payload.exercise_id:
                # Update existing rather than creating duplicate
                update_payload = AdaptiveTherapyConfigUpdate(**payload.model_dump(exclude={"patient_id", "exercise_id"}))
                return AdaptiveTherapyService.update_config(existing["id"], update_payload, clinician_id)

        now_iso = datetime.now().isoformat()
        config_id = f"atc-{uuid.uuid4().hex[:12]}"
        curr_diff = payload.current_difficulty if payload.current_difficulty is not None else payload.starting_difficulty

        record = {
            "id": config_id,
            "patient_id": payload.patient_id,
            "therapy_assignment_id": payload.therapy_assignment_id,
            "exercise_id": payload.exercise_id,
            "enabled": payload.enabled,
            "adaptive_mode": payload.adaptive_mode,
            "minimum_difficulty": payload.minimum_difficulty,
            "maximum_difficulty": payload.maximum_difficulty,
            "starting_difficulty": payload.starting_difficulty,
            "current_difficulty": curr_diff,
            "progression_threshold": payload.progression_threshold,
            "regression_threshold": payload.regression_threshold,
            "step_size": payload.step_size,
            "minimum_sessions_before_adaptation": payload.minimum_sessions_before_adaptation,
            "max_daily_difficulty_increase": payload.max_daily_difficulty_increase,
            "clinician_approval_required": payload.clinician_approval_required,
            "created_by": clinician_id or "clinician",
            "created_at": now_iso,
            "updated_at": now_iso,
            "notice": "Controlled rule-based difficulty adaptation. Does not diagnose or determine recovery. Follow clinician guidance."
        }
        supabase.table("adaptive_therapy_configs").insert(record).execute()
        return record

    @staticmethod
    def update_config(config_id: str, payload: AdaptiveTherapyConfigUpdate, clinician_id: Optional[str] = None) -> Dict[str, Any]:
        res = supabase.table("adaptive_therapy_configs").select("*").eq("id", config_id).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Adaptive config '{config_id}' not found."
            )
        config = res.data[0]

        updates = payload.model_dump(exclude_unset=True)

        # Merge for validation
        min_diff = updates.get("minimum_difficulty", config["minimum_difficulty"])
        max_diff = updates.get("maximum_difficulty", config["maximum_difficulty"])
        start_diff = updates.get("starting_difficulty", config["starting_difficulty"])
        curr_diff = updates.get("current_difficulty", config["current_difficulty"])
        prog_thresh = updates.get("progression_threshold", config["progression_threshold"])
        reg_thresh = updates.get("regression_threshold", config["regression_threshold"])

        if min_diff > max_diff:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Minimum difficulty ({min_diff}) cannot exceed maximum difficulty ({max_diff})."
            )
        if not (min_diff <= start_diff <= max_diff):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Starting difficulty ({start_diff}) must be between minimum ({min_diff}) and maximum ({max_diff})."
            )
        if curr_diff is not None and not (min_diff <= curr_diff <= max_diff):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Current difficulty ({curr_diff}) must be between minimum ({min_diff}) and maximum ({max_diff})."
            )
        if reg_thresh >= prog_thresh:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Regression threshold ({reg_thresh}%) must be lower than progression threshold ({prog_thresh}%)."
            )

        now_iso = datetime.now().isoformat()
        updates["updated_at"] = now_iso

        supabase.table("adaptive_therapy_configs").update(updates).eq("id", config_id).execute()
        config.update(updates)
        config["notice"] = "Controlled rule-based difficulty adaptation. Does not diagnose or determine recovery. Follow clinician guidance."
        return config

    @staticmethod
    def evaluate_session(session_id: str, clinician_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Deterministic, rule-based adaptation engine evaluating a completed therapy session.
        Calculates progression, regression, maintenance, or safety pause based on telemetry.
        """
        # Fetch session
        s_res = supabase.table("therapy_sessions").select("*").eq("id", session_id).execute()
        if not s_res.data:
            logger.warning(f"Therapy session '{session_id}' not found for adaptation evaluation.")
            return None
        session = s_res.data[0]

        patient_id = session.get("patient_id")
        exercise_id = session.get("exercise_type", "horizontal_moving_target")

        # Fetch result
        r_res = supabase.table("therapy_session_results").select("*").eq("therapy_session_id", session_id).execute()
        results = r_res.data or []
        result = results[0] if results else {}

        # Fetch or initialize config
        config = AdaptiveTherapyService.get_or_create_config(patient_id, exercise_id, clinician_id)
        if not config.get("enabled") or config.get("adaptive_mode") == "disabled":
            logger.info(f"Adaptive therapy disabled for patient '{patient_id}', exercise '{exercise_id}'. Skipping.")
            return None

        current_diff = int(config.get("current_difficulty", DEFAULT_STARTING_DIFFICULTY))
        min_diff = int(config.get("minimum_difficulty", DEFAULT_MIN_DIFFICULTY))
        max_diff = int(config.get("maximum_difficulty", DEFAULT_MAX_DIFFICULTY))
        step = int(config.get("step_size", DEFAULT_STEP_SIZE))
        min_sessions = int(config.get("minimum_sessions_before_adaptation", DEFAULT_MIN_SESSIONS))
        prog_thresh = float(config.get("progression_threshold", DEFAULT_PROGRESSION_THRESHOLD))
        reg_thresh = float(config.get("regression_threshold", DEFAULT_REGRESSION_THRESHOLD))
        approval_required = bool(config.get("clinician_approval_required", True))
        is_simulated = bool(result.get("is_simulated_data", session.get("is_simulated_data", False)))

        now_iso = datetime.now().isoformat()
        rec_id = f"tar-{uuid.uuid4().hex[:12]}"

        # RULE 1: SAFETY / DISCOMFORT CHECK (HIGHEST PRIORITY)
        stop_reason = str(session.get("stop_reason") or "").lower()
        clinician_notes = str(result.get("clinician_notes") or "").lower()
        metrics = result.get("metrics_json") or {}
        has_discomfort = (
            session.get("session_status") == "stopped"
            and any(term in stop_reason for term in ["discomfort", "strain", "fatigue", "dizziness", "headache", "pain"])
        ) or (
            any(term in clinician_notes for term in ["discomfort", "eye strain", "fatigue", "dizziness"])
        ) or bool(metrics.get("discomfort_reported"))

        if has_discomfort:
            recommended_diff = max(min_diff, current_diff - step)
            rec_record = {
                "id": rec_id,
                "patient_id": patient_id,
                "therapy_assignment_id": config.get("therapy_assignment_id"),
                "exercise_id": exercise_id,
                "source_session_id": session_id,
                "current_difficulty": current_diff,
                "recommended_difficulty": recommended_diff,
                "direction": "pause_discomfort",
                "reason": "Adaptation paused. The patient reported discomfort during this session. Clinical review is required before changing difficulty.",
                "supporting_metrics": {
                    "reported_discomfort": True,
                    "stop_reason": session.get("stop_reason"),
                    "session_status": session.get("session_status"),
                    "actual_duration_seconds": session.get("actual_duration_seconds", 0)
                },
                "confidence": "high",
                "data_quality_note": "Immediate patient-safety alert. Adaptation suspended.",
                "is_simulated_data": is_simulated,
                "status": "pending",
                "reviewed_by": None,
                "clinician_note": None,
                "reviewed_at": None,
                "applied_at": None,
                "created_at": now_iso,
                "notice": "Suggested difficulty adjustment based on performance rules. Requires clinician review before application when configured."
            }
            supabase.table("therapy_adaptation_recommendations").insert(rec_record).execute()
            return rec_record

        # RULE 2: DATA QUALITY & INCOMPLETE SESSIONS CHECK
        tracking_confidence = float(result.get("tracking_confidence") or 1.0)
        session_status = session.get("session_status", "completed")
        data_quality_status = result.get("data_quality_status") or session.get("data_quality_status") or "Valid Data"

        if session_status in ["abandoned", "error"] or tracking_confidence < 0.70 or "low" in data_quality_status.lower() or "invalid" in data_quality_status.lower():
            rec_record = {
                "id": rec_id,
                "patient_id": patient_id,
                "therapy_assignment_id": config.get("therapy_assignment_id"),
                "exercise_id": exercise_id,
                "source_session_id": session_id,
                "current_difficulty": current_diff,
                "recommended_difficulty": current_diff,
                "direction": "maintain",
                "reason": "Session was abandoned or recorded telemetry tracking confidence is low (<0.70). Data quality is insufficient for adaptation evaluation.",
                "supporting_metrics": {
                    "tracking_confidence": tracking_confidence,
                    "session_status": session_status,
                    "data_quality_status": data_quality_status
                },
                "confidence": "low",
                "data_quality_note": "Unreliable session data excluded from difficulty calculation.",
                "is_simulated_data": is_simulated,
                "status": "not_recommended",
                "reviewed_by": None,
                "clinician_note": None,
                "reviewed_at": None,
                "applied_at": None,
                "created_at": now_iso,
                "notice": "Suggested difficulty adjustment based on performance rules. Requires clinician review before application when configured."
            }
            supabase.table("therapy_adaptation_recommendations").insert(rec_record).execute()
            return rec_record

        # RULE 3: RETRIEVE HISTORICAL COMPLETED SESSIONS FOR EVALUATION
        all_sessions_res = supabase.table("therapy_sessions").select("*").eq("patient_id", patient_id).execute()
        all_sessions = all_sessions_res.data or []

        # Filter valid completed sessions for matching exercise
        valid_sessions: List[Dict[str, Any]] = []
        for s in all_sessions:
            if s.get("exercise_type") != exercise_id:
                continue
            if s.get("session_status") != "completed":
                continue
            # Check results
            r_check = supabase.table("therapy_session_results").select("*").eq("therapy_session_id", s["id"]).execute()
            if r_check.data:
                r_item = r_check.data[0]
                if float(r_item.get("tracking_confidence") or 1.0) >= 0.70:
                    s["result"] = r_item
                    valid_sessions.append(s)

        # Sort chronologically by completion or creation
        valid_sessions.sort(key=lambda x: x.get("completed_at") or x.get("created_at", ""), reverse=True)

        # Check minimum session requirement
        if len(valid_sessions) < min_sessions:
            rec_record = {
                "id": rec_id,
                "patient_id": patient_id,
                "therapy_assignment_id": config.get("therapy_assignment_id"),
                "exercise_id": exercise_id,
                "source_session_id": session_id,
                "current_difficulty": current_diff,
                "recommended_difficulty": current_diff,
                "direction": "maintain",
                "reason": f"Insufficient session history ({len(valid_sessions)}/{min_sessions} valid sessions completed). Additional sessions required before evaluating adaptation.",
                "supporting_metrics": {
                    "completed_valid_sessions": len(valid_sessions),
                    "required_sessions": min_sessions,
                    "latest_score": result.get("score") or result.get("accuracy", 0.0)
                },
                "confidence": "moderate",
                "data_quality_note": "Awaiting minimum session threshold.",
                "is_simulated_data": is_simulated,
                "status": "not_recommended",
                "reviewed_by": None,
                "clinician_note": None,
                "reviewed_at": None,
                "applied_at": None,
                "created_at": now_iso,
                "notice": "Suggested difficulty adjustment based on performance rules. Requires clinician review before application when configured."
            }
            supabase.table("therapy_adaptation_recommendations").insert(rec_record).execute()
            return rec_record

        # RULE 4: PERFORMANCE AGGREGATION ACROSS LAST N SESSIONS
        evaluated_sessions = valid_sessions[:min_sessions]
        scores = []
        accuracies = []
        target_losses = []
        error_values = []

        for s in evaluated_sessions:
            res_obj = s.get("result", {})
            sc = res_obj.get("score")
            ac = res_obj.get("accuracy")
            if sc is not None:
                scores.append(float(sc))
            if ac is not None:
                accuracies.append(float(ac))
            if res_obj.get("target_loss_events") is not None:
                target_losses.append(int(res_obj.get("target_loss_events", 0)))
            if res_obj.get("error_value") is not None:
                error_values.append(float(res_obj.get("error_value", 0)))

        # Composite performance score
        avg_score = sum(scores) / len(scores) if scores else (sum(accuracies) / len(accuracies) if accuracies else 0.0)
        avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else avg_score
        avg_loss = sum(target_losses) / len(target_losses) if target_losses else 0.0
        avg_error = sum(error_values) / len(error_values) if error_values else None

        supporting = {
            "evaluated_sessions_count": len(evaluated_sessions),
            "average_performance_score": round(avg_score, 1),
            "average_accuracy": round(avg_accuracy, 1),
            "average_target_loss": round(avg_loss, 1),
            "average_error_value": round(avg_error, 3) if avg_error is not None else None,
            "progression_threshold": prog_thresh,
            "regression_threshold": reg_thresh
        }

        # PROGRESSION BRANCH
        if avg_score >= prog_thresh:
            if current_diff >= max_diff:
                direction = "maintain"
                recommended_diff = current_diff
                status_val = "not_recommended"
                reason_str = (
                    f"Performance ({avg_score:.1f}%) remained consistently above the progression threshold ({prog_thresh}%), "
                    f"but difficulty is already at the clinician-configured maximum limit (Level {max_diff})."
                )
            else:
                # Check daily increase limits
                today_str = date.today().isoformat()
                audits_res = supabase.table("therapy_adaptation_audits").select("*").eq("patient_id", patient_id).execute()
                daily_increases = sum(
                    1 for a in (audits_res.data or [])
                    if a.get("exercise_id") == exercise_id
                    and str(a.get("applied_at", "")).startswith(today_str)
                    and int(a.get("new_difficulty", 0)) > int(a.get("previous_difficulty", 0))
                )

                if daily_increases >= int(config.get("max_daily_difficulty_increase", 1)):
                    direction = "maintain"
                    recommended_diff = current_diff
                    status_val = "not_recommended"
                    reason_str = (
                        f"Performance qualified for progression, but the maximum daily difficulty increase cap "
                        f"({config.get('max_daily_difficulty_increase', 1)}) has been reached for today."
                    )
                else:
                    direction = "progression"
                    recommended_diff = min(max_diff, current_diff + step)
                    status_val = "pending" if approval_required else "applied"
                    reason_str = (
                        f"Performance remained consistently above the progression threshold ({prog_thresh}%) "
                        f"across {len(evaluated_sessions)} valid sessions (average score: {avg_score:.1f}%)."
                    )

        # REGRESSION BRANCH
        elif avg_score <= reg_thresh or avg_loss >= 6.0:
            if current_diff <= min_diff:
                direction = "maintain"
                recommended_diff = current_diff
                status_val = "not_recommended"
                reason_str = (
                    f"Performance ({avg_score:.1f}%) was below the regression threshold ({reg_thresh}%), "
                    f"but difficulty is already at the clinician-configured minimum limit (Level {min_diff})."
                )
            else:
                direction = "regression"
                recommended_diff = max(min_diff, current_diff - step)
                status_val = "pending" if approval_required else "applied"
                reason_str = (
                    f"Performance dropped below the regression threshold ({reg_thresh}%) "
                    f"across evaluated sessions (average score: {avg_score:.1f}%). "
                    f"A step reduction is recommended to support patient engagement."
                )

        # MAINTAIN BRANCH
        else:
            direction = "maintain"
            recommended_diff = current_diff
            status_val = "not_recommended"
            reason_str = (
                f"Performance ({avg_score:.1f}%) is within the target therapeutic challenge range "
                f"({reg_thresh}% - {prog_thresh}%). Maintaining current difficulty."
            )

        # AUTOMATIC DIFFICULTY APPLICATION
        applied_at_val = None
        if status_val == "applied":
            applied_at_val = now_iso
            # Update config current difficulty
            prev_diff = current_diff
            config["current_difficulty"] = recommended_diff
            config["updated_at"] = now_iso
            supabase.table("adaptive_therapy_configs").update({
                "current_difficulty": recommended_diff,
                "updated_at": now_iso
            }).eq("id", config["id"]).execute()

            # Create audit record
            audit_id = f"taa-{uuid.uuid4().hex[:12]}"
            audit_rec = {
                "id": audit_id,
                "patient_id": patient_id,
                "exercise_id": exercise_id,
                "previous_difficulty": prev_diff,
                "new_difficulty": recommended_diff,
                "change_type": "automatic",
                "trigger": "session_completion",
                "source_recommendation_id": rec_id,
                "applied_by": "system (controlled_automatic)",
                "applied_at": now_iso,
                "notes": f"Automatic {direction} applied per clinician configuration."
            }
            supabase.table("therapy_adaptation_audits").insert(audit_rec).execute()

        rec_record = {
            "id": rec_id,
            "patient_id": patient_id,
            "therapy_assignment_id": config.get("therapy_assignment_id"),
            "exercise_id": exercise_id,
            "source_session_id": session_id,
            "current_difficulty": current_diff,
            "recommended_difficulty": recommended_diff,
            "direction": direction,
            "reason": reason_str,
            "supporting_metrics": supporting,
            "confidence": "high" if tracking_confidence >= 0.85 else "moderate",
            "data_quality_note": "Evaluated from verified hardware telemetry" if not is_simulated else "Evaluated from demo/simulated tracking telemetry",
            "is_simulated_data": is_simulated,
            "status": status_val,
            "reviewed_by": None,
            "clinician_note": None,
            "reviewed_at": None,
            "applied_at": applied_at_val,
            "created_at": now_iso,
            "notice": "Suggested difficulty adjustment based on performance rules. Requires clinician review before application when configured."
        }
        supabase.table("therapy_adaptation_recommendations").insert(rec_record).execute()
        return rec_record

    @staticmethod
    def review_recommendation(
        recommendation_id: str,
        payload: TherapyAdaptationReviewRequest,
        clinician_id: str
    ) -> Dict[str, Any]:
        """
        Clinician workflow to approve, reject, or override a difficulty recommendation.
        """
        res = supabase.table("therapy_adaptation_recommendations").select("*").eq("id", recommendation_id).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Adaptation recommendation '{recommendation_id}' not found."
            )
        rec = res.data[0]

        patient_id = rec["patient_id"]
        exercise_id = rec["exercise_id"]

        cfg_res = supabase.table("adaptive_therapy_configs").select("*").eq("patient_id", patient_id).execute()
        config = None
        for c in (cfg_res.data or []):
            if c.get("exercise_id") == exercise_id:
                config = c
                break

        if not config:
            config = AdaptiveTherapyService.get_or_create_config(patient_id, exercise_id, clinician_id)

        now_iso = datetime.now().isoformat()
        prev_diff = int(config.get("current_difficulty", DEFAULT_STARTING_DIFFICULTY))

        if payload.action == "approve":
            new_diff = int(rec["recommended_difficulty"])
            # Update recommendation
            rec["status"] = "applied"
            rec["reviewed_by"] = clinician_id
            rec["clinician_note"] = payload.clinician_notes
            rec["reviewed_at"] = now_iso
            rec["applied_at"] = now_iso

            # Update config
            config["current_difficulty"] = new_diff
            config["updated_at"] = now_iso
            supabase.table("adaptive_therapy_configs").update({
                "current_difficulty": new_diff,
                "updated_at": now_iso
            }).eq("id", config["id"]).execute()

            # Audit
            audit_id = f"taa-{uuid.uuid4().hex[:12]}"
            audit_rec = {
                "id": audit_id,
                "patient_id": patient_id,
                "exercise_id": exercise_id,
                "previous_difficulty": prev_diff,
                "new_difficulty": new_diff,
                "change_type": "clinician_approved",
                "trigger": "clinician_action",
                "source_recommendation_id": recommendation_id,
                "applied_by": clinician_id,
                "applied_at": now_iso,
                "notes": payload.clinician_notes or "Clinician approved recommended difficulty."
            }
            supabase.table("therapy_adaptation_audits").insert(audit_rec).execute()

        elif payload.action == "reject":
            rec["status"] = "rejected"
            rec["reviewed_by"] = clinician_id
            rec["clinician_note"] = payload.clinician_notes
            rec["reviewed_at"] = now_iso

        elif payload.action == "override":
            override_val = payload.override_difficulty
            if override_val is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="override_difficulty is required for override action."
                )
            min_d = int(config.get("minimum_difficulty", 1))
            max_d = int(config.get("maximum_difficulty", 5))
            if not (min_d <= override_val <= max_d):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Override difficulty ({override_val}) must be between {min_d} and {max_d}."
                )

            rec["status"] = "overridden"
            rec["reviewed_by"] = clinician_id
            rec["clinician_note"] = payload.clinician_notes
            rec["reviewed_at"] = now_iso
            rec["applied_at"] = now_iso

            # Update config
            config["current_difficulty"] = override_val
            config["updated_at"] = now_iso
            supabase.table("adaptive_therapy_configs").update({
                "current_difficulty": override_val,
                "updated_at": now_iso
            }).eq("id", config["id"]).execute()

            # Audit
            audit_id = f"taa-{uuid.uuid4().hex[:12]}"
            audit_rec = {
                "id": audit_id,
                "patient_id": patient_id,
                "exercise_id": exercise_id,
                "previous_difficulty": prev_diff,
                "new_difficulty": override_val,
                "change_type": "clinician_override",
                "trigger": "clinician_action",
                "source_recommendation_id": recommendation_id,
                "applied_by": clinician_id,
                "applied_at": now_iso,
                "notes": payload.clinician_notes or f"Clinician manually adjusted difficulty to Level {override_val}."
            }
            supabase.table("therapy_adaptation_audits").insert(audit_rec).execute()

        supabase.table("therapy_adaptation_recommendations").update({
            "status": rec["status"],
            "reviewed_by": rec.get("reviewed_by"),
            "clinician_note": rec.get("clinician_note"),
            "reviewed_at": rec.get("reviewed_at"),
            "applied_at": rec.get("applied_at")
        }).eq("id", recommendation_id).execute()

        rec["notice"] = "Suggested difficulty adjustment based on performance rules. Requires clinician review before application when configured."
        return rec

    @staticmethod
    def reset_difficulty(config_id: str, clinician_id: str, notes: Optional[str] = None) -> Dict[str, Any]:
        res = supabase.table("adaptive_therapy_configs").select("*").eq("id", config_id).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Adaptive config '{config_id}' not found."
            )
        config = res.data[0]

        prev_diff = int(config.get("current_difficulty", DEFAULT_STARTING_DIFFICULTY))
        starting_diff = int(config.get("starting_difficulty", DEFAULT_STARTING_DIFFICULTY))
        now_iso = datetime.now().isoformat()

        config["current_difficulty"] = starting_diff
        config["updated_at"] = now_iso

        supabase.table("adaptive_therapy_configs").update({
            "current_difficulty": starting_diff,
            "updated_at": now_iso
        }).eq("id", config_id).execute()

        # Audit
        audit_id = f"taa-{uuid.uuid4().hex[:12]}"
        audit_rec = {
            "id": audit_id,
            "patient_id": config["patient_id"],
            "exercise_id": config["exercise_id"],
            "previous_difficulty": prev_diff,
            "new_difficulty": starting_diff,
            "change_type": "reset",
            "trigger": "clinician_action",
            "source_recommendation_id": None,
            "applied_by": clinician_id,
            "applied_at": now_iso,
            "notes": notes or f"Difficulty reset to starting baseline (Level {starting_diff})."
        }
        supabase.table("therapy_adaptation_audits").insert(audit_rec).execute()

        config["notice"] = "Controlled rule-based difficulty adaptation. Does not diagnose or determine recovery. Follow clinician guidance."
        return config

    @staticmethod
    def get_patient_recommendations(patient_id: str, exercise_id: Optional[str] = None) -> List[Dict[str, Any]]:
        AdaptiveTherapyService._verify_patient(patient_id)
        res = supabase.table("therapy_adaptation_recommendations").select("*").eq("patient_id", patient_id).execute()
        recs = res.data or []
        if exercise_id:
            recs = [r for r in recs if r.get("exercise_id") == exercise_id]
        recs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        for r in recs:
            r["notice"] = "Suggested difficulty adjustment based on performance rules. Requires clinician review before application when configured."
        return recs

    @staticmethod
    def get_patient_audits(patient_id: str, exercise_id: Optional[str] = None) -> List[Dict[str, Any]]:
        AdaptiveTherapyService._verify_patient(patient_id)
        res = supabase.table("therapy_adaptation_audits").select("*").eq("patient_id", patient_id).execute()
        audits = res.data or []
        if exercise_id:
            audits = [a for a in audits if a.get("exercise_id") == exercise_id]
        audits.sort(key=lambda x: x.get("applied_at", ""), reverse=True)
        return audits
