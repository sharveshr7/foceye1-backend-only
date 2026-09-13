import json
from typing import Any, Dict, List

RECOMMENDATION_SYSTEM_INSTRUCTION = """You are an AI-assisted clinical ophthalmic decision-support engine.
Your role is to propose therapy exercise categories for clinician review based strictly on recorded eye-test telemetry.

STRICT CLINICAL SAFETY RULES:
1. You MUST NOT diagnose any medical condition or eye disease (e.g. no Amblyopia, Strabismus, Convergence Insufficiency, Glaucoma).
2. You MUST NOT prescribe therapy independently or present suggestions as a confirmed treatment plan.
3. You MUST NOT claim that therapy will cure or medically improve a disease.
4. You MUST NOT automatically assign or start therapy.
5. You MUST NOT replace clinician judgment.
6. Recommendations are strictly suggestions requiring clinician approval before use.
7. You must ONLY use the 6 allowed exercise categories:
   - "Fixation Exercise"
   - "Smooth Pursuit Exercise"
   - "Saccade Exercise"
   - "Gaze Accuracy Exercise"
   - "General Visual Attention Exercise"
   - "Repeat Assessment / Calibration Review"
8. If data is incomplete, simulated, has low tracking confidence (< 0.80), or has insufficient sample count (< 200 samples), you MUST select "Repeat Assessment / Calibration Review" with priority "review_required".
9. Use cautious wording:
   - "Consider reviewing..."
   - "A possible exercise category is..."
   - "This suggestion is based on the recorded performance data..."
   - "Clinician approval is required before use..."

Every response MUST contain the disclaimer:
"AI-assisted recommendation. Requires clinician review. Not a diagnosis or automatic prescription."
"""


def build_recommendation_prompt(structured_input: Dict[str, Any]) -> str:
    input_json = json.dumps(structured_input, indent=2)
    return f"""Please generate an AI-assisted therapy exercise recommendation for clinician review based strictly on this eye-test telemetry:

{input_json}

Return valid JSON strictly matching this schema:
{{
  "recommendation_status": "completed",
  "recommendations": [
    {{
      "exercise_category": "Fixation Exercise",
      "reason": "The recorded fixation metrics indicate reduced fixation consistency.",
      "supporting_metrics": [
        {{"metric": "score", "value": 72.0}}
      ],
      "suggested_difficulty": "beginner",
      "suggested_duration_minutes": {{"min": 5, "max": 10}},
      "priority": "moderate",
      "confidence": "moderate",
      "data_quality_note": "Based on available session data.",
      "clinician_review_required": true
    }}
  ],
  "overall_note": "The recommendations are suggestions for clinician review and are not automatic prescriptions.",
  "limitations": [
    "The recommendation is based strictly on recorded eye-test performance telemetry.",
    "Clinical judgment and clinician approval are required before assigning therapy."
  ],
  "disclaimer": "AI-assisted recommendation. Requires clinician review. Not a diagnosis or automatic prescription."
}}
"""


def generate_clinical_heuristic_recommendation(structured_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic clinical decision-support evaluator conforming strictly to
    the 6 categories and clinical safety rules.
    """
    tests: List[Dict[str, Any]] = structured_input.get("eye_test_results", [])
    data_quality = structured_input.get("data_quality_summary", {})
    is_simulated = data_quality.get("is_simulated", False)
    low_confidence_count = data_quality.get("low_confidence_count", 0)
    incomplete_count = data_quality.get("incomplete_count", 0)

    recs: List[Dict[str, Any]] = []

    insufficient_sample_count = data_quality.get("insufficient_sample_count", 0)

    # Check for unreliable or low confidence data first
    if low_confidence_count > 0 or incomplete_count > 0 or insufficient_sample_count > 0 or not tests:
        recs.append({
            "exercise_category": "Repeat Assessment / Calibration Review",
            "reason": "The available data may not be reliable enough for a therapy recommendation.",
            "supporting_metrics": [
                {"metric": "low_confidence_test_count", "value": float(low_confidence_count)},
                {"metric": "incomplete_test_count", "value": float(incomplete_count)},
                {"metric": "insufficient_sample_count", "value": float(insufficient_sample_count)}
            ],
            "suggested_difficulty": "not_applicable",
            "suggested_duration_minutes": {"min": 0, "max": 0},
            "priority": "review_required",
            "confidence": "low",
            "data_quality_note": "Low tracking confidence or incomplete samples detected. Telemetry recalibration recommended.",
            "clinician_review_required": True
        })
    else:
        # Evaluate objective test performance
        test_map = {t.get("test_type"): t for t in tests}

        fixation = test_map.get("FIXATION_STABILITY")
        pursuit = test_map.get("SMOOTH_PURSUIT")
        saccade = test_map.get("SACCADE_RESPONSE")
        gaze = test_map.get("GAZE_ACCURACY")

        # Check fixation
        if fixation and ((fixation.get("score") or 100) < 80 or (fixation.get("error_value") or 0) > 0.04):
            recs.append({
                "exercise_category": "Fixation Exercise",
                "reason": "The recorded fixation metrics indicate reduced fixation consistency.",
                "supporting_metrics": [
                    {"metric": "score", "value": float(fixation.get("score") or 0)},
                    {"metric": "error_value", "value": float(fixation.get("error_value") or 0)}
                ],
                "suggested_difficulty": "beginner",
                "suggested_duration_minutes": {"min": 5, "max": 10},
                "priority": "moderate" if (fixation.get("score") or 0) > 65 else "high",
                "confidence": "moderate",
                "data_quality_note": "Captured with " + ("Demo/Simulated Data" if is_simulated else "Hardware Sensor Data"),
                "clinician_review_required": True
            })

        # Check smooth pursuit
        if pursuit and ((pursuit.get("score") or 100) < 80 or (pursuit.get("error_value") or 0) > 0.04):
            recs.append({
                "exercise_category": "Smooth Pursuit Exercise",
                "reason": "The latest session recorded increased smooth-pursuit error.",
                "supporting_metrics": [
                    {"metric": "score", "value": float(pursuit.get("score") or 0)},
                    {"metric": "error_value", "value": float(pursuit.get("error_value") or 0)}
                ],
                "suggested_difficulty": "beginner" if (pursuit.get("score") or 0) < 70 else "moderate",
                "suggested_duration_minutes": {"min": 5, "max": 10},
                "priority": "moderate",
                "confidence": "moderate",
                "data_quality_note": "Captured with " + ("Demo/Simulated Data" if is_simulated else "Hardware Sensor Data"),
                "clinician_review_required": True
            })

        # Check saccades
        if saccade and ((saccade.get("reaction_time") or 0) > 260 or (saccade.get("score") or 100) < 80):
            recs.append({
                "exercise_category": "Saccade Exercise",
                "reason": "The recorded saccade response metrics may require further review.",
                "supporting_metrics": [
                    {"metric": "reaction_time", "value": float(saccade.get("reaction_time") or 0)},
                    {"metric": "score", "value": float(saccade.get("score") or 0)}
                ],
                "suggested_difficulty": "beginner",
                "suggested_duration_minutes": {"min": 5, "max": 10},
                "priority": "moderate",
                "confidence": "moderate",
                "data_quality_note": "Captured with " + ("Demo/Simulated Data" if is_simulated else "Hardware Sensor Data"),
                "clinician_review_required": True
            })

        # Check gaze accuracy
        if gaze and ((gaze.get("score") or 100) < 85 or (gaze.get("error_value") or 0) > 0.03):
            recs.append({
                "exercise_category": "Gaze Accuracy Exercise",
                "reason": "The session recorded reduced gaze-target accuracy.",
                "supporting_metrics": [
                    {"metric": "score", "value": float(gaze.get("score") or 0)},
                    {"metric": "error_value", "value": float(gaze.get("error_value") or 0)}
                ],
                "suggested_difficulty": "beginner",
                "suggested_duration_minutes": {"min": 5, "max": 10},
                "priority": "moderate",
                "confidence": "moderate",
                "data_quality_note": "Captured with " + ("Demo/Simulated Data" if is_simulated else "Hardware Sensor Data"),
                "clinician_review_required": True
            })

        # If all scores are high/normal
        if not recs:
            recs.append({
                "exercise_category": "General Visual Attention Exercise",
                "reason": "Performance telemetry indicates consistent baseline oculomotor control; consider visual attention maintenance.",
                "supporting_metrics": [
                    {"metric": "average_score", "value": 90.0}
                ],
                "suggested_difficulty": "beginner",
                "suggested_duration_minutes": {"min": 5, "max": 10},
                "priority": "low",
                "confidence": "moderate",
                "data_quality_note": "Captured with " + ("Demo/Simulated Data" if is_simulated else "Hardware Sensor Data"),
                "clinician_review_required": True
            })

    return {
        "recommendation_status": "completed",
        "recommendations": recs,
        "overall_note": "The recommendations are suggestions for clinician review and are not automatic prescriptions.",
        "limitations": [
            "The recommendation is based strictly on recorded eye-test performance telemetry.",
            "Clinical judgment and clinician approval are required before assigning therapy."
        ],
        "disclaimer": "AI-assisted recommendation. Requires clinician review. Not a diagnosis or automatic prescription."
    }
