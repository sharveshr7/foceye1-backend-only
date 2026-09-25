import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from app.core.supabase import supabase

logger = logging.getLogger("foceye.eye_test_service")

VALID_TEST_TYPES = {
    "FIXATION_STABILITY",
    "SMOOTH_PURSUIT",
    "SACCADE_RESPONSE",
    "GAZE_ACCURACY"
}


class EyeTestService:
    """
    Manages eye test sessions, individual subtest execution lifecycles,
    and objective clinical ocular biomarker result persistence.
    """

    @staticmethod
    def _verify_patient(patient_id: str) -> Dict[str, Any]:
        res = supabase.table("patients").select("*").eq("id", patient_id).execute()
        if not res.data or len(res.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with ID '{patient_id}' does not exist in clinical records."
            )
        return res.data[0]

    @staticmethod
    def create_session(patient_id: str, clinician_id: Optional[str] = None) -> Dict[str, Any]:
        EyeTestService._verify_patient(patient_id)
        now_iso = datetime.now().isoformat()
        session_id = f"ets-{uuid.uuid4().hex[:12]}"
        
        record = {
            "id": session_id,
            "patient_id": patient_id,
            "clinician_id": clinician_id,
            "session_status": "IN_PROGRESS",
            "started_at": now_iso,
            "completed_at": None,
            "created_at": now_iso,
            "updated_at": now_iso
        }
        supabase.table("eye_test_sessions").insert(record).execute()
        return record

    @staticmethod
    def get_session(session_id: str) -> Dict[str, Any]:
        res = supabase.table("eye_test_sessions").select("*").eq("id", session_id).execute()
        if not res.data or len(res.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Eye test session '{session_id}' not found."
            )
        return res.data[0]

    @staticmethod
    def start_test(session_id: str, test_type: str) -> Dict[str, Any]:
        norm_type = test_type.upper()
        if norm_type not in VALID_TEST_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid test type '{test_type}'. Must be one of: {', '.join(sorted(VALID_TEST_TYPES))}"
            )
        session = EyeTestService.get_session(session_id)
        
        # Update session status if not already completed
        if session.get("session_status") != "COMPLETED":
            supabase.table("eye_test_sessions").update({
                "session_status": "IN_PROGRESS",
                "updated_at": datetime.now().isoformat()
            }).eq("id", session_id).execute()

        return {
            "session_id": session_id,
            "test_type": norm_type,
            "status": "STARTED",
            "started_at": datetime.now().isoformat()
        }

    @staticmethod
    def save_result(data: Dict[str, Any]) -> Dict[str, Any]:
        patient_id = data.get("patient_id")
        session_id = data.get("session_id")
        test_type = str(data.get("test_type", "")).upper()

        if not patient_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="patient_id is required.")
        if not session_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="session_id is required.")
        if test_type not in VALID_TEST_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid test type '{test_type}'. Must be one of: {', '.join(sorted(VALID_TEST_TYPES))}"
            )

        # Validate existence
        EyeTestService._verify_patient(patient_id)
        EyeTestService.get_session(session_id)

        now_iso = datetime.now().isoformat()
        result_id = f"etr-{uuid.uuid4().hex[:12]}"
        
        record = {
            "id": result_id,
            "session_id": session_id,
            "patient_id": patient_id,
            "test_type": test_type,
            "status": data.get("status", "COMPLETED"),
            "duration": float(data.get("duration", 0.0)),
            "score": float(data.get("score", 0.0)),
            "error_value": data.get("error_value"),
            "reaction_time": data.get("reaction_time"),
            "valid_sample_count": int(data.get("valid_sample_count", 0)),
            "tracking_confidence": float(data.get("tracking_confidence", 0.0)),
            "data_quality_status": data.get("data_quality_status", "Demo/Simulated Data"),
            "raw_result_json": data.get("raw_result_json") or {},
            "notes": data.get("notes"),
            "created_at": now_iso
        }
        supabase.table("eye_test_results").insert(record).execute()
        return record

    @staticmethod
    def update_result(result_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        res = supabase.table("eye_test_results").select("*").eq("id", result_id).execute()
        if not res.data or len(res.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test result '{result_id}' not found."
            )
        
        allowed_fields = {
            "status", "score", "error_value", "reaction_time",
            "valid_sample_count", "tracking_confidence",
            "data_quality_status", "raw_result_json", "notes"
        }
        clean_updates = {k: v for k, v in updates.items() if k in allowed_fields and v is not None}
        if clean_updates:
            supabase.table("eye_test_results").update(clean_updates).eq("id", result_id).execute()
        
        updated_res = supabase.table("eye_test_results").select("*").eq("id", result_id).execute()
        return updated_res.data[0]

    @staticmethod
    def complete_session(session_id: str) -> Dict[str, Any]:
        session = EyeTestService.get_session(session_id)
        now_iso = datetime.now().isoformat()

        supabase.table("eye_test_sessions").update({
            "session_status": "COMPLETED",
            "completed_at": now_iso,
            "updated_at": now_iso
        }).eq("id", session_id).execute()

        # Update patient stage if currently pending eye test
        try:
            supabase.table("patients").update({
                "clinical_status": "EYE_TEST_COMPLETED",
                "stage": "EYE_TEST_COMPLETED",
                "last_session": datetime.now().strftime("%Y-%m-%d")
            }).eq("id", session["patient_id"]).execute()
        except Exception as e:
            logger.warning(f"Could not update patient stage on session completion: {e}")

        session["session_status"] = "COMPLETED"
        session["completed_at"] = now_iso
        session["updated_at"] = now_iso
        return session

    @staticmethod
    def get_sessions_for_patient(patient_id: str) -> List[Dict[str, Any]]:
        EyeTestService._verify_patient(patient_id)
        res = supabase.table("eye_test_sessions").select("*").eq("patient_id", patient_id).execute()
        sessions = res.data or []
        # Sort newest first
        sessions.sort(key=lambda s: s.get("started_at", ""), reverse=True)
        return sessions

    @staticmethod
    def get_results_for_session(session_id: str) -> List[Dict[str, Any]]:
        EyeTestService.get_session(session_id)
        res = supabase.table("eye_test_results").select("*").eq("session_id", session_id).execute()
        results = res.data or []
        results.sort(key=lambda r: r.get("created_at", ""))
        return results

    @staticmethod
    def get_latest_result_for_patient(patient_id: str) -> Optional[Dict[str, Any]]:
        EyeTestService._verify_patient(patient_id)
        res = supabase.table("eye_test_results").select("*").eq("patient_id", patient_id).execute()
        results = res.data or []
        if not results:
            return None
        # Sort newest first
        results.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return results[0]

    @staticmethod
    def get_results_for_patient(patient_id: str) -> List[Dict[str, Any]]:
        EyeTestService._verify_patient(patient_id)
        res = supabase.table("eye_test_results").select("*").eq("patient_id", patient_id).execute()
        results = res.data or []
        results.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return results

