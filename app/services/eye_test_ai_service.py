import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from app.core.supabase import supabase
from app.schemas.eye_test_ai_schemas import (
    AIAnalysisOutput,
    AIAnalysisResponse,
    ClinicianReviewUpdate,
)
from app.services.eye_test_ai_prompts import (
    SYSTEM_INSTRUCTION,
    build_analysis_prompt,
    generate_clinical_heuristic_analysis,
)
from app.services.gemini_service import gemini_service

logger = logging.getLogger("foceye.eye_test_ai_service")


class EyeTestAIService:
    """
    Service coordinating AI-assisted analysis of completed eye-test sessions.
    Strictly observes clinical safety rules: non-diagnostic, non-prescriptive,
    objective telemetry interpretation only.
    """

    @staticmethod
    def _verify_session(session_id: str) -> Dict[str, Any]:
        res = supabase.table("eye_test_sessions").select("*").eq("id", session_id).execute()
        if not res.data or len(res.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Eye test session '{session_id}' not found."
            )
        return res.data[0]

    @staticmethod
    def _fetch_results(session_id: str) -> List[Dict[str, Any]]:
        res = supabase.table("eye_test_results").select("*").eq("session_id", session_id).execute()
        return res.data or []

    @staticmethod
    def _fetch_previous_session(patient_id: str, current_session_id: str, current_created_at: str) -> Optional[Dict[str, Any]]:
        res = supabase.table("eye_test_sessions").select("*").eq("patient_id", patient_id).execute()
        sessions = res.data or []
        # Filter completed sessions created prior to current session
        candidates = [
            s for s in sessions
            if s.get("id") != current_session_id
            and s.get("created_at", "") < current_created_at
            and s.get("session_status") in ("COMPLETED", "READY_FOR_REVIEW")
        ]
        if not candidates:
            return None
        # Sort descending by created_at
        candidates.sort(key=lambda s: s.get("created_at", ""), reverse=True)
        prev_session = candidates[0]
        prev_results = supabase.table("eye_test_results").select("*").eq("session_id", prev_session["id"]).execute()
        return {
            "session": prev_session,
            "results": prev_results.data or []
        }

    @staticmethod
    async def analyze_session(session_id: str, requesting_user_id: Optional[str] = None) -> Dict[str, Any]:
        # 1. Verify session exists
        session = EyeTestAIService._verify_session(session_id)
        patient_id = session.get("patient_id")

        # 2. Fetch results
        results = EyeTestAIService._fetch_results(session_id)
        if not results:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid test data is available for analysis."
            )

        # 3. Validate data and compute quality summary
        completed_tests = [r for r in results if r.get("status") == "COMPLETED" or r.get("score") is not None]
        if not completed_tests:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session has no completed test runs available for analysis."
            )

        is_simulated = any(
            r.get("data_quality_status") == "Demo/Simulated Data"
            or "simulated" in str(r.get("data_quality_status", "")).lower()
            for r in results
        )
        low_confidence_count = sum(1 for r in results if float(r.get("tracking_confidence") or 1.0) < 0.80)
        incomplete_count = len(results) - len(completed_tests)

        data_quality_summary = {
            "total_tests": len(results),
            "completed_tests": len(completed_tests),
            "incomplete_count": incomplete_count,
            "low_confidence_count": low_confidence_count,
            "is_simulated": is_simulated,
            "data_quality_status": "Demo/Simulated Data" if is_simulated else "Valid Data"
        }

        # 4. Fetch previous session for comparison
        prev_info = EyeTestAIService._fetch_previous_session(patient_id, session_id, session.get("created_at", ""))
        previous_session_data = {
            "available": prev_info is not None,
            "results": prev_info["results"] if prev_info else []
        }

        # 5. Prepare anonymized structured input
        structured_input = {
            "session_id": session_id,
            "tests": [
                {
                    "test_type": r.get("test_type"),
                    "status": r.get("status", "COMPLETED"),
                    "score": r.get("score"),
                    "error_value": r.get("error_value"),
                    "reaction_time": r.get("reaction_time"),
                    "valid_sample_count": r.get("valid_sample_count"),
                    "tracking_confidence": r.get("tracking_confidence"),
                    "data_quality_status": r.get("data_quality_status"),
                    "is_simulated": is_simulated
                }
                for r in completed_tests
            ],
            "data_quality_summary": data_quality_summary,
            "previous_session": previous_session_data
        }

        # 6. Request AI analysis from Gemini or fallback
        prompt = build_analysis_prompt(structured_input)
        raw_output = None
        used_model = "ClinicalHeuristicEngine-v1"

        if gemini_service.is_configured:
            try:
                parsed_json, model_name, err = await gemini_service.generate_json(
                    prompt=prompt,
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.1
                )
                if parsed_json and not err:
                    raw_output = parsed_json
                    used_model = model_name or gemini_service.default_model
                else:
                    logger.warning(f"Gemini API returned unparseable output or error: {err}. Using clinical heuristic.")
            except Exception as exc:
                logger.warning(f"Gemini call threw exception: {exc}. Falling back to clinical heuristic.")

        if not raw_output:
            raw_output = generate_clinical_heuristic_analysis(structured_input)

        # 7. Validate output against AIAnalysisOutput schema
        try:
            validated_output = AIAnalysisOutput(**raw_output)
        except Exception as ve:
            logger.error(f"AI response schema validation error: {ve}. Reverting to baseline heuristic.")
            validated_output = AIAnalysisOutput(**generate_clinical_heuristic_analysis(structured_input))

        # Enforce non-diagnostic disclaimer
        validated_output.disclaimer = "AI-assisted analysis. Requires clinician review. Not a diagnosis."

        now_iso = datetime.now().isoformat()
        analysis_id = f"aia-{uuid.uuid4().hex[:12]}"

        record = {
            "id": analysis_id,
            "patient_id": patient_id,
            "eye_test_session_id": session_id,
            "analysis_status": validated_output.analysis_status,
            "model_name": used_model,
            "input_summary_json": structured_input,
            "output_json": validated_output.model_dump(),
            "data_quality_status": data_quality_summary["data_quality_status"],
            "is_simulated_data": is_simulated,
            "clinician_review_status": "pending",
            "clinician_notes": None,
            "confidence_score": 0.95,
            "ai_observations": validated_output.overall_summary,
            "created_at": now_iso,
            "updated_at": now_iso
        }

        # 8. Store in database
        supabase.table("ai_analyses").insert(record).execute()
        return record

    @staticmethod
    def get_session_analysis(session_id: str) -> Optional[Dict[str, Any]]:
        EyeTestAIService._verify_session(session_id)
        res = supabase.table("ai_analyses").select("*").eq("eye_test_session_id", session_id).execute()
        records = res.data or []
        if not records:
            return None
        # Return latest analysis
        records.sort(key=lambda a: a.get("created_at", ""), reverse=True)
        return records[0]

    @staticmethod
    def get_patient_analyses(patient_id: str) -> List[Dict[str, Any]]:
        res = supabase.table("ai_analyses").select("*").eq("patient_id", patient_id).execute()
        records = res.data or []
        records.sort(key=lambda a: a.get("created_at", ""), reverse=True)
        return records

    @staticmethod
    def update_clinician_review(analysis_id: str, review_status_val: str, notes: Optional[str] = None) -> Dict[str, Any]:
        valid_statuses = {"pending", "reviewed", "flagged", "dismissed"}
        if review_status_val not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid review status '{review_status_val}'. Must be one of: {', '.join(sorted(valid_statuses))}"
            )

        res = supabase.table("ai_analyses").select("*").eq("id", analysis_id).execute()
        if not res.data or len(res.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"AI analysis with ID '{analysis_id}' not found."
            )

        now_iso = datetime.now().isoformat()
        updates = {
            "clinician_review_status": review_status_val,
            "updated_at": now_iso
        }
        if notes is not None:
            updates["clinician_notes"] = notes

        up_res = supabase.table("ai_analyses").update(updates).eq("id", analysis_id).execute()
        if up_res.data and len(up_res.data) > 0:
            return up_res.data[0]

        # In-memory fallback update
        existing = res.data[0]
        existing.update(updates)
        return existing
