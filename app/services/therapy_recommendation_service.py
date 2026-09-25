import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from app.core.supabase import supabase
from app.schemas.therapy_recommendation_schemas import (
    VALID_EXERCISE_CATEGORIES,
    VALID_PRIORITIES,
    VALID_DIFFICULTIES,
    AIRecommendationOutput,
    TherapyRecommendationResponse,
)
from app.services.therapy_recommendation_prompts import (
    RECOMMENDATION_SYSTEM_INSTRUCTION,
    build_recommendation_prompt,
    generate_clinical_heuristic_recommendation,
)
from app.services.gemini_service import gemini_service

logger = logging.getLogger("foceye.therapy_recommendation_service")


class TherapyRecommendationService:
    """
    Coordinates AI-assisted decision-support therapy exercise recommendations.
    Strictly clinical decision-support only:
    - Never prescribes therapy independently
    - Never automatically assigns therapy
    - Strictly clinician approved, edited, or rejected
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
    def _fetch_ai_analysis(session_id: str) -> Optional[Dict[str, Any]]:
        res = supabase.table("ai_analyses").select("*").eq("eye_test_session_id", session_id).execute()
        records = res.data or []
        if not records:
            return None
        records.sort(key=lambda a: a.get("created_at", ""), reverse=True)
        return records[0]

    @staticmethod
    async def generate_recommendation(
        session_id: str,
        clinician_id: Optional[str] = None
    ) -> Dict[str, Any]:
        # 1. Verify session exists
        session = TherapyRecommendationService._verify_session(session_id)
        patient_id = session.get("patient_id")

        # 2. Verify results exist
        results = TherapyRecommendationService._fetch_results(session_id)
        if not results:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid test data is available for generating a recommendation."
            )

        # 3. Verify AI Analysis exists
        ai_analysis = TherapyRecommendationService._fetch_ai_analysis(session_id)
        if not ai_analysis:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Complete AI analysis before generating a therapy recommendation."
            )

        is_simulated = any(
            r.get("data_quality_status") == "Demo/Simulated Data"
            or "simulated" in str(r.get("data_quality_status", "")).lower()
            for r in results
        )
        low_confidence_count = sum(1 for r in results if float(r.get("tracking_confidence") or 1.0) < 0.80)
        incomplete_count = sum(1 for r in results if r.get("status") != "COMPLETED" and r.get("score") is None)
        insufficient_sample_count = sum(
            1 for r in results
            if r.get("valid_sample_count") is not None and int(r.get("valid_sample_count") or 0) < 200
        )

        data_quality_summary = {
            "is_simulated": is_simulated,
            "low_confidence_count": low_confidence_count,
            "incomplete_count": incomplete_count,
            "insufficient_sample_count": insufficient_sample_count,
        }

        # 4. Prepare structured input
        structured_input = {
            "eye_test_session_id": session_id,
            "eye_test_results": [
                {
                    "test_type": r.get("test_type"),
                    "score": r.get("score"),
                    "error_value": r.get("error_value"),
                    "reaction_time": r.get("reaction_time"),
                    "valid_sample_count": r.get("valid_sample_count"),
                    "tracking_confidence": r.get("tracking_confidence"),
                    "data_quality_status": r.get("data_quality_status"),
                    "is_simulated": is_simulated
                }
                for r in results
            ],
            "data_quality_summary": data_quality_summary,
            "ai_analysis": {
                "overall_summary": ai_analysis.get("output_json", {}).get("overall_summary", ""),
                "performance_patterns": ai_analysis.get("output_json", {}).get("performance_patterns", []),
                "data_quality_warnings": ai_analysis.get("output_json", {}).get("data_quality_warnings", []),
                "areas_for_clinician_review": ai_analysis.get("output_json", {}).get("areas_for_clinician_review", [])
            }
        }

        prompt = build_recommendation_prompt(structured_input)
        raw_output = None

        if gemini_service.is_configured:
            try:
                parsed_json, _, err = await gemini_service.generate_json(
                    prompt=prompt,
                    system_instruction=RECOMMENDATION_SYSTEM_INSTRUCTION,
                    temperature=0.1
                )
                if parsed_json and not err and "recommendations" in parsed_json:
                    raw_output = parsed_json
            except Exception as e:
                logger.warning(f"Gemini therapy recommendation call failed: {e}. Falling back to clinical heuristic.")

        if not raw_output:
            raw_output = generate_clinical_heuristic_recommendation(structured_input)

        try:
            validated = AIRecommendationOutput(**raw_output)
        except Exception as ve:
            logger.error(f"Failed to validate recommendation output: {ve}. Using baseline fallback.")
            validated = AIRecommendationOutput(**generate_clinical_heuristic_recommendation(structured_input))

        # Select primary item
        primary_rec = validated.recommendations[0]

        # Clinical safety guardrail: If data is incomplete, low confidence, or has insufficient sample count (<200),
        # safety requires Repeat Assessment / Calibration Review
        if insufficient_sample_count > 0 or low_confidence_count > 0 or incomplete_count > 0:
            validated = AIRecommendationOutput(**generate_clinical_heuristic_recommendation(structured_input))
            primary_rec = validated.recommendations[0]

        # Validate category in allowed categories
        category = primary_rec.exercise_category
        if category not in VALID_EXERCISE_CATEGORIES:
            category = "General Visual Attention Exercise"

        now_iso = datetime.now().isoformat()
        rec_id = f"tr-{uuid.uuid4().hex[:12]}"

        record = {
            "id": rec_id,
            "patient_id": patient_id,
            "eye_test_session_id": session_id,
            "ai_analysis_id": ai_analysis["id"],
            "recommendation_status": "pending_review",
            "exercise_category": category,
            "primary_exercise_category": category,
            "recommended_difficulty_level": primary_rec.suggested_difficulty,
            "recommended_duration_minutes": primary_rec.suggested_duration_minutes.min,
            "reason": primary_rec.reason,
            "supporting_metrics_json": [m.model_dump() for m in primary_rec.supporting_metrics],
            "suggested_difficulty": primary_rec.suggested_difficulty,
            "suggested_duration_min": primary_rec.suggested_duration_minutes.min,
            "suggested_duration_max": primary_rec.suggested_duration_minutes.max,
            "priority": primary_rec.priority,
            "confidence": primary_rec.confidence,
            "data_quality_note": primary_rec.data_quality_note,
            "is_simulated_data": is_simulated,
            "clinician_review_status": "pending",  # strictly pending initially
            "clinician_notes": None,
            "original_recommendation_json": primary_rec.model_dump(),
            "created_by": clinician_id or "AI Clinical Engine",
            "created_at": now_iso,
            "updated_at": now_iso,
            "disclaimer": "AI-assisted recommendation. Requires clinician review. Not a diagnosis or automatic prescription."
        }

        supabase.table("therapy_recommendations").insert(record).execute()
        return record

    @staticmethod
    def get_session_recommendations(session_id: str) -> List[Dict[str, Any]]:
        TherapyRecommendationService._verify_session(session_id)
        res = supabase.table("therapy_recommendations").select("*").eq("eye_test_session_id", session_id).execute()
        records = res.data or []
        records.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return records

    @staticmethod
    def get_patient_recommendations(patient_id: str) -> List[Dict[str, Any]]:
        res = supabase.table("therapy_recommendations").select("*").eq("patient_id", patient_id).execute()
        records = res.data or []
        records.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return records

    @staticmethod
    def review_recommendation(
        recommendation_id: str,
        action: str,
        notes: Optional[str] = None,
        clinician_name: Optional[str] = None
    ) -> Dict[str, Any]:
        norm_action = action.lower()
        if norm_action not in {"approved", "rejected", "pending"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid review action '{action}'. Must be 'approved', 'rejected', or 'pending'."
            )

        res = supabase.table("therapy_recommendations").select("*").eq("id", recommendation_id).execute()
        if not res.data or len(res.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Therapy recommendation '{recommendation_id}' not found."
            )

        now_iso = datetime.now().isoformat()
        status_map = {
            "approved": ("approved", "approved"),
            "rejected": ("rejected", "rejected"),
            "pending": ("pending_review", "pending")
        }
        rec_status, review_status = status_map[norm_action]

        updates = {
            "recommendation_status": rec_status,
            "clinician_review_status": review_status,
            "updated_at": now_iso
        }
        if notes is not None:
            updates["clinician_notes"] = notes

        up_res = supabase.table("therapy_recommendations").update(updates).eq("id", recommendation_id).execute()
        if up_res.data and len(up_res.data) > 0:
            return up_res.data[0]

        existing = res.data[0]
        existing.update(updates)
        return existing

    @staticmethod
    def edit_recommendation(
        recommendation_id: str,
        edits: Dict[str, Any],
        clinician_name: Optional[str] = None
    ) -> Dict[str, Any]:
        res = supabase.table("therapy_recommendations").select("*").eq("id", recommendation_id).execute()
        if not res.data or len(res.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Therapy recommendation '{recommendation_id}' not found."
            )

        category = edits.get("exercise_category")
        if category and category not in VALID_EXERCISE_CATEGORIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid exercise category '{category}'. Must be one of: {', '.join(sorted(VALID_EXERCISE_CATEGORIES))}"
            )

        d_min = edits.get("suggested_duration_min")
        d_max = edits.get("suggested_duration_max")
        if d_min is not None and d_min <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Minimum duration must be positive."
            )
        if d_min is not None and d_max is not None and d_min > d_max:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Minimum duration cannot exceed maximum duration."
            )

        now_iso = datetime.now().isoformat()
        updates: Dict[str, Any] = {
            "recommendation_status": "edited",
            "clinician_review_status": "edited",
            "updated_at": now_iso
        }
        if category:
            updates["exercise_category"] = category
        if edits.get("suggested_difficulty"):
            updates["suggested_difficulty"] = edits["suggested_difficulty"]
        if d_min is not None:
            updates["suggested_duration_min"] = d_min
        if d_max is not None:
            updates["suggested_duration_max"] = d_max
        if edits.get("priority"):
            updates["priority"] = edits["priority"]
        if edits.get("clinician_notes") is not None:
            updates["clinician_notes"] = edits["clinician_notes"]

        up_res = supabase.table("therapy_recommendations").update(updates).eq("id", recommendation_id).execute()
        if up_res.data and len(up_res.data) > 0:
            return up_res.data[0]

        existing = res.data[0]
        existing.update(updates)
        return existing
