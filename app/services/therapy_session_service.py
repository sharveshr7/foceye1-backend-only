import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from app.core.supabase import supabase
from app.schemas.therapy_session_schemas import (
    VALID_EXERCISE_TYPES,
    VALID_SESSION_STATUSES,
    VALID_DIFFICULTIES,
    TherapySessionCreate,
    TherapySessionResultCreate,
)

logger = logging.getLogger("foceye.therapy_session_service")

# Map recommendation category names to standardized exercise type slugs
CATEGORY_TO_EXERCISE_TYPE = {
    "Fixation Exercise": "fixation_target",
    "Smooth Pursuit Exercise": "horizontal_moving_target",
    "Saccade Exercise": "gaze_target_selection",
    "Gaze Accuracy Exercise": "gaze_target_selection",
    "General Visual Attention Exercise": "horizontal_moving_target",
    "fixation_target": "fixation_target",
    "horizontal_moving_target": "horizontal_moving_target",
    "gaze_target_selection": "gaze_target_selection",
    "smooth_pursuit": "horizontal_moving_target",
    "saccade": "gaze_target_selection",
    "fixation": "fixation_target",
    "gaze_accuracy": "gaze_target_selection",
}

# State machine transition rules
ALLOWED_TRANSITIONS = {
    "assigned": {"ready", "abandoned"},
    "ready": {"in_progress", "abandoned"},
    "in_progress": {"paused", "completed", "stopped", "abandoned"},
    "paused": {"in_progress", "stopped", "abandoned"},
    "completed": set(),  # Terminal state
    "stopped": set(),    # Terminal state
    "abandoned": set(),  # Terminal state
    "error": set(),
}


class TherapySessionService:
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
    def _verify_recommendation(recommendation_id: str) -> Dict[str, Any]:
        res = supabase.table("therapy_recommendations").select("*").eq("id", recommendation_id).execute()
        if not res.data or len(res.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Therapy recommendation '{recommendation_id}' not found."
            )
        rec = res.data[0]
        # Clinical Rule: Only approved recommendations can start a session
        review_status = (rec.get("clinician_review_status") or "").lower()
        if review_status != "approved":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This recommendation requires clinician approval before a session can be started."
            )
        return rec

    @staticmethod
    def create_session(payload: TherapySessionCreate, clinician_id: Optional[str] = None) -> Dict[str, Any]:
        # 1. Verify patient
        TherapySessionService._verify_patient(payload.patient_id)

        # 2. Check recommendation if provided
        exercise_type = payload.exercise_type
        difficulty = payload.difficulty
        duration = payload.planned_duration_seconds

        if payload.recommendation_id:
            rec = TherapySessionService._verify_recommendation(payload.recommendation_id)
            # Adapt exercise type from recommendation if not provided
            if not exercise_type or exercise_type in CATEGORY_TO_EXERCISE_TYPE:
                exercise_type = CATEGORY_TO_EXERCISE_TYPE.get(rec.get("exercise_category"), exercise_type)
            difficulty = rec.get("suggested_difficulty") or difficulty
            if duration == 300 and rec.get("suggested_duration_min"):
                duration = int(rec.get("suggested_duration_min", 5)) * 60

        # Validate exercise type
        normalized_type = CATEGORY_TO_EXERCISE_TYPE.get(exercise_type, exercise_type)
        if normalized_type not in {"fixation_target", "horizontal_moving_target", "gaze_target_selection"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid exercise type '{exercise_type}'. Must be one of: fixation_target, horizontal_moving_target, gaze_target_selection."
            )

        # Validate duration
        if duration <= 0 or duration > 3600:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Planned duration must be positive and not exceed 3600 seconds (60 minutes)."
            )

        # Check active adaptive difficulty config
        try:
            cfg_res = supabase.table("adaptive_therapy_configs").select("*").eq("patient_id", payload.patient_id).execute()
            for cfg in (cfg_res.data or []):
                if cfg.get("exercise_id") == normalized_type and cfg.get("enabled") and cfg.get("current_difficulty"):
                    if difficulty == "beginner" or not payload.difficulty:
                        difficulty = str(cfg.get("current_difficulty"))
                    break
        except Exception:
            pass

        # Validate difficulty
        if difficulty not in VALID_DIFFICULTIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid difficulty '{difficulty}'. Must be one of: {', '.join(sorted(VALID_DIFFICULTIES))}."
            )

        session_id = str(uuid.uuid4())
        now_iso = datetime.now().isoformat()
        is_simulated = bool(getattr(payload, "is_simulated_data", False))
        data_quality = getattr(payload, "data_quality_status", "Valid Data") or ("Demo/Simulated Tracking Data" if is_simulated else "Valid Data")

        record = {
            "id": session_id,
            "patient_id": payload.patient_id,
            "recommendation_id": payload.recommendation_id,
            "assigned_by": payload.assigned_by or clinician_id or "Attending Clinician",
            "exercise_type": normalized_type,
            "session_status": "ready",
            "planned_duration_seconds": duration,
            "duration_seconds": duration,
            "actual_duration_seconds": 0,
            "difficulty": difficulty,
            "fixation_score": 0.0,
            "saccadic_score": 0.0,
            "convergence_score": 0.0,
            "overall_score": 0.0,
            "bcea_68": 0.0,
            "bcea_95": 0.0,
            "clinical_notes": "Prescribed rehabilitation session initialized.",
            "started_at": None,
            "paused_at": None,
            "completed_at": None,
            "stopped_at": None,
            "stop_reason": None,
            "data_quality_status": data_quality,
            "is_simulated_data": is_simulated,
            "created_at": now_iso,
            "updated_at": now_iso,
            "notice": "Prototype rehabilitation session. Follow clinician instructions. Stop if discomfort occurs. Recorded results are not a diagnosis."
        }

        supabase.table("therapy_sessions").insert(record).execute()
        record["results"] = []
        return record

    @staticmethod
    def get_session(session_id: str) -> Dict[str, Any]:
        res = supabase.table("therapy_sessions").select("*").eq("id", session_id).execute()
        if not res.data or len(res.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Therapy session '{session_id}' not found."
            )
        session = res.data[0]
        # Attach results
        r_res = supabase.table("therapy_session_results").select("*").eq("therapy_session_id", session_id).execute()
        session["results"] = r_res.data or []
        session["notice"] = "Prototype rehabilitation session. Follow clinician instructions. Stop if discomfort occurs. Recorded results are not a diagnosis."
        return session

    @staticmethod
    def transition_state(
        session_id: str,
        target_status: str,
        actual_duration_seconds: Optional[int] = None,
        stop_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        session = TherapySessionService.get_session(session_id)
        current_status = session.get("session_status", "ready")

        # Check state transition validity
        allowed = ALLOWED_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid session state transition from '{current_status}' to '{target_status}'."
            )

        now_iso = datetime.now().isoformat()
        updates: Dict[str, Any] = {
            "session_status": target_status,
            "updated_at": now_iso,
        }

        if actual_duration_seconds is not None:
            val = max(0, actual_duration_seconds)
            updates["actual_duration_seconds"] = val
            updates["duration_seconds"] = val

        if target_status == "in_progress":
            if not session.get("started_at"):
                updates["started_at"] = now_iso
            updates["paused_at"] = None
        elif target_status == "paused":
            updates["paused_at"] = now_iso
        elif target_status == "completed":
            updates["completed_at"] = now_iso
        elif target_status == "stopped":
            updates["stopped_at"] = now_iso
            updates["stop_reason"] = stop_reason or "Session stopped by clinician or patient"

        supabase.table("therapy_sessions").update(updates).eq("id", session_id).execute()
        session.update(updates)

        # Trigger adaptive evaluation immediately if stopped due to discomfort
        if target_status == "stopped" and any(k in str(stop_reason).lower() for k in ["discomfort", "strain", "fatigue", "dizziness"]):
            try:
                from app.services.adaptive_therapy_service import AdaptiveTherapyService
                AdaptiveTherapyService.evaluate_session(session_id)
            except Exception as e:
                logger.warning(f"Failed to evaluate discomfort adaptation: {e}")

        return session

    @staticmethod
    def save_session_result(session_id: str, payload: TherapySessionResultCreate) -> Dict[str, Any]:
        session = TherapySessionService.get_session(session_id)
        patient_id = session.get("patient_id")

        result_id = f"tsr-{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now().isoformat()

        # Flexible resolution of field aliases
        exercise_type = payload.exercise_type or session.get("exercise_type", "horizontal_moving_target")
        accuracy = payload.accuracy if payload.accuracy is not None else (payload.accuracy_score if payload.accuracy_score is not None else payload.score)
        reaction_time = payload.reaction_time if payload.reaction_time is not None else payload.reaction_time_ms

        record = {
            "id": result_id,
            "therapy_session_id": session_id,
            "patient_id": patient_id,
            "exercise_type": exercise_type,
            "score": payload.score,
            "accuracy": accuracy,
            "error_value": payload.error_value,
            "reaction_time": reaction_time,
            "completion_percentage": payload.completion_percentage,
            "valid_sample_count": payload.valid_sample_count,
            "tracking_confidence": payload.tracking_confidence,
            "target_loss_events": payload.target_loss_events,
            "pause_count": payload.pause_count,
            "metrics_json": payload.metrics_json or {},
            "data_quality_status": payload.data_quality_status,
            "is_simulated_data": payload.is_simulated_data,
            "clinician_notes": payload.clinician_notes,
            "created_at": now_iso,
            "notice": "Prototype rehabilitation session. Follow clinician instructions. Stop if discomfort occurs. Recorded results are not a diagnosis."
        }

        supabase.table("therapy_session_results").insert(record).execute()

        # Update therapy_sessions row with overall score and clinician notes
        try:
            session_updates: Dict[str, Any] = {
                "overall_score": payload.score,
                "updated_at": now_iso
            }
            if payload.clinician_notes:
                session_updates["clinical_notes"] = payload.clinician_notes
            if exercise_type in ["fixation_target", "fixation"]:
                session_updates["fixation_score"] = payload.score
            elif exercise_type in ["horizontal_moving_target", "smooth_pursuit"]:
                session_updates["saccadic_score"] = payload.score
            supabase.table("therapy_sessions").update(session_updates).eq("id", session_id).execute()
        except Exception as e:
            logger.warning(f"Could not update therapy_sessions score: {e}")

        # Trigger adaptive difficulty engine evaluation
        try:
            from app.services.adaptive_therapy_service import AdaptiveTherapyService
            AdaptiveTherapyService.evaluate_session(session_id)
        except Exception as e:
            logger.warning(f"Failed to evaluate session '{session_id}' for adaptive difficulty: {e}")

        return record

    @staticmethod
    def get_patient_sessions(patient_id: str) -> List[Dict[str, Any]]:
        res = supabase.table("therapy_sessions").select("*").eq("patient_id", patient_id).execute()
        sessions = res.data or []
        sessions.sort(key=lambda s: s.get("created_at", ""), reverse=True)
        for s in sessions:
            r_res = supabase.table("therapy_session_results").select("*").eq("therapy_session_id", s["id"]).execute()
            s["results"] = r_res.data or []
            s["notice"] = "Prototype rehabilitation session. Follow clinician instructions. Stop if discomfort occurs. Recorded results are not a diagnosis."
        return sessions
