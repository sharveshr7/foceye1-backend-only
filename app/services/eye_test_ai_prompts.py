import json
from typing import Any, Dict, List, Optional


SYSTEM_INSTRUCTION = """You are an AI-assisted clinical ophthalmic data analysis engine.
Your sole role is to analyze objective eye-tracking and gaze telemetry measurements recorded during standard eye tests.

STRICT CLINICAL SAFETY RULES:
1. You MUST NOT diagnose any eye disease or medical condition (e.g., Amblyopia, Strabismus, Glaucoma, Convergence Insufficiency, Nystagmus).
2. You MUST NOT confirm or rule out any medical condition.
3. You MUST NOT prescribe or recommend therapy or medical treatments.
4. You MUST NOT claim that a patient is cured, clinically recovered, or has a specific medical pathology.
5. You MUST NOT replace a qualified clinician.
6. You MUST NOT invent or impute missing values.
7. If data is incomplete, low confidence (< 0.80), or simulated, you MUST clearly state that interpretation is limited.
8. Use cautious, objective language such as:
   - "The recorded data indicates..."
   - "The session measurements show..."
   - "This variation may warrant further clinical review..."
   - "The available telemetry is insufficient to evaluate..."
9. Never use wording like:
   - "The patient has [condition]"
   - "The patient is diagnosed with..."
   - "This proves..."
   - "This confirms disease..."

You must output STRICT valid JSON only matching the requested schema.
Every response MUST contain the disclaimer:
"AI-assisted analysis. Requires clinician review. Not a diagnosis."
"""


def build_analysis_prompt(structured_input: Dict[str, Any]) -> str:
    input_json = json.dumps(structured_input, indent=2)
    return f"""Please perform an objective AI-assisted analysis of the following eye-test session telemetry:

{input_json}

Return a valid JSON object strictly matching this schema:
{{
  "analysis_status": "completed",
  "overall_summary": "Objective telemetry summary based strictly on the available recorded tests.",
  "performance_summary": [
    {{
      "test_type": "FIXATION_STABILITY",
      "observation": "Objective observation of fixation stability and spatial variance.",
      "supporting_metrics": [
        {{"metric": "score", "value": 85.0}},
        {{"metric": "error_value", "value": 0.05}}
      ],
      "interpretation_confidence": "moderate"
    }}
  ],
  "performance_patterns": [
    {{
      "pattern": "stable",
      "area": "Fixation",
      "description": "Observed fixation drift remained within expected boundaries.",
      "supporting_metrics": ["score: 85.0"],
      "confidence": "moderate"
    }}
  ],
  "session_comparison": {{
    "available": false,
    "summary": "No previous session is available for comparison.",
    "changes": []
  }},
  "data_quality_warnings": [],
  "areas_for_clinician_review": [],
  "limitations": [
    "This analysis is based only on recorded eye-tracking measurements.",
    "The output is an assistive observation and not a medical diagnosis."
  ],
  "disclaimer": "AI-assisted analysis. Requires clinician review. Not a diagnosis."
}}
"""


def generate_clinical_heuristic_analysis(structured_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic clinical heuristic analysis fallback when Gemini API is unconfigured or offline.
    Adheres strictly to the same non-diagnostic clinical safety constraints.
    """
    tests: List[Dict[str, Any]] = structured_input.get("tests", [])
    data_quality = structured_input.get("data_quality_summary", {})
    prev_session = structured_input.get("previous_session", {})

    warnings: List[str] = []
    if data_quality.get("is_simulated", False):
        warnings.append("Session data was captured via simulation provider (Demo/Simulated Data).")
    if data_quality.get("low_confidence_count", 0) > 0:
        warnings.append(f"{data_quality['low_confidence_count']} test(s) exhibited tracking confidence below 0.80.")
    if data_quality.get("incomplete_count", 0) > 0:
        warnings.append(f"{data_quality['incomplete_count']} test(s) were flagged as incomplete or had missing samples.")

    perf_summary: List[Dict[str, Any]] = []
    patterns: List[Dict[str, Any]] = []
    areas_for_review: List[str] = []

    for t in tests:
        t_type = t.get("test_type", "UNKNOWN")
        score = t.get("score")
        error_val = t.get("error_value")
        reaction_time = t.get("reaction_time")
        confidence = t.get("tracking_confidence", 1.0)
        samples = t.get("valid_sample_count", 0)
        is_sim = t.get("is_simulated", False)

        supporting = []
        if score is not None:
            supporting.append({"metric": "score", "value": float(score)})
        if error_val is not None:
            supporting.append({"metric": "error_value", "value": float(error_val)})
        if reaction_time is not None:
            supporting.append({"metric": "reaction_time", "value": float(reaction_time)})

        conf_level = "high" if confidence >= 0.90 else "moderate" if confidence >= 0.75 else "low"

        if t_type == "FIXATION_STABILITY":
            obs = f"Fixation stability score recorded at {score:.1f}% with average spatial deviation of {error_val:.3f} units across {samples} frames."
            pat = "stable" if (score or 0) >= 80 else "variable" if (score or 0) >= 60 else "low_reliability"
            pat_desc = f"Fixation telemetry demonstrates {pat} central holding over the test duration."
            perf_summary.append({
                "test_type": t_type,
                "observation": obs,
                "supporting_metrics": supporting,
                "interpretation_confidence": conf_level
            })
            patterns.append({
                "pattern": pat,
                "area": "Fixation Stability",
                "description": pat_desc,
                "supporting_metrics": [f"Stability Score: {score:.1f}%", f"Deviation: {error_val:.3f}"],
                "confidence": conf_level
            })
            if (score or 0) < 70:
                areas_for_review.append("Fixation stability score lower than expected baseline; verify patient attention and working distance.")

        elif t_type == "SMOOTH_PURSUIT":
            obs = f"Horizontal smooth pursuit tracking recorded an accuracy score of {score:.1f}% with tracking error of {error_val:.3f} units across {samples} frames."
            pat = "stable" if (score or 0) >= 80 else "variable"
            pat_desc = f"Horizontal gaze following demonstrates {pat} pursuit trajectory alignment."
            perf_summary.append({
                "test_type": t_type,
                "observation": obs,
                "supporting_metrics": supporting,
                "interpretation_confidence": conf_level
            })
            patterns.append({
                "pattern": pat,
                "area": "Horizontal Smooth Pursuit",
                "description": pat_desc,
                "supporting_metrics": [f"Tracking Accuracy: {score:.1f}%", f"Pursuit Error: {error_val:.3f}"],
                "confidence": conf_level
            })

        elif t_type == "SACCADE_RESPONSE":
            obs = f"Saccadic jump stimulus response recorded average response latency of {reaction_time:.0f} ms with position error of {error_val:.3f} units."
            pat = "stable" if (reaction_time or 999) <= 280 else "variable"
            pat_desc = f"Rapid saccade redirection measured an average latency of {reaction_time:.0f} ms."
            perf_summary.append({
                "test_type": t_type,
                "observation": obs,
                "supporting_metrics": supporting,
                "interpretation_confidence": conf_level
            })
            patterns.append({
                "pattern": pat,
                "area": "Saccade Response",
                "description": pat_desc,
                "supporting_metrics": [f"Latency: {reaction_time:.0f} ms", f"Position Error: {error_val:.3f}"],
                "confidence": conf_level
            })

        elif t_type == "GAZE_ACCURACY":
            obs = f"Multi-point cardinal gaze alignment achieved {score:.1f}% accuracy with mean target offset of {error_val:.3f} units across {samples} frames."
            pat = "stable" if (score or 0) >= 80 else "variable"
            pat_desc = f"Cardinal fixation targeting demonstrates {pat} eccentric gaze alignment."
            perf_summary.append({
                "test_type": t_type,
                "observation": obs,
                "supporting_metrics": supporting,
                "interpretation_confidence": conf_level
            })
            patterns.append({
                "pattern": pat,
                "area": "Gaze Accuracy",
                "description": pat_desc,
                "supporting_metrics": [f"Gaze Accuracy: {score:.1f}%", f"Mean Offset: {error_val:.3f}"],
                "confidence": conf_level
            })

    # Comparison logic
    comparison_changes = []
    comp_available = prev_session.get("available", False)
    prev_results = prev_session.get("results", [])

    if comp_available and prev_results:
        prev_map = {r.get("test_type"): r for r in prev_results}
        for t in tests:
            tt = t.get("test_type")
            if tt in prev_map:
                p = prev_map[tt]
                curr_score = t.get("score")
                prev_score = p.get("score")
                if curr_score is not None and prev_score is not None:
                    diff = round(curr_score - prev_score, 2)
                    direction = "higher_score" if diff > 1.0 else "lower_score" if diff < -1.0 else "similar"
                    comparison_changes.append({
                        "metric": f"{tt} Score",
                        "previous_value": float(prev_score),
                        "current_value": float(curr_score),
                        "change": diff,
                        "direction": direction,
                        "comparison_confidence": "moderate"
                    })

    session_comp = {
        "available": comp_available and len(comparison_changes) > 0,
        "summary": (
            f"Comparison with previous session shows {len(comparison_changes)} matching test metric(s)."
            if comp_available and len(comparison_changes) > 0
            else "No previous session is available for comparison."
        ),
        "changes": comparison_changes
    }

    if not areas_for_review:
        areas_for_review.append("Verify overall test environment lighting and patient distance during review.")

    analysis_status = "completed" if len(tests) >= 1 and len(warnings) == 0 else "partial" if len(tests) >= 1 else "limited"

    overall_summary = (
        f"Session recorded {len(tests)} standard eye test(s). "
        f"Telemetry displays {patterns[0]['pattern'] if patterns else 'insufficient'} general performance across evaluated oculomotor metrics. "
        f"Measurements are presented for clinical review."
    )

    return {
        "analysis_status": analysis_status,
        "overall_summary": overall_summary,
        "performance_summary": perf_summary,
        "performance_patterns": patterns,
        "session_comparison": session_comp,
        "data_quality_warnings": warnings,
        "areas_for_clinician_review": areas_for_review,
        "limitations": [
            "This analysis is based strictly on recorded eye-tracking measurements.",
            "The output is an assistive observation and not a medical diagnosis."
        ],
        "disclaimer": "AI-assisted analysis. Requires clinician review. Not a diagnosis."
    }
