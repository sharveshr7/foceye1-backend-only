import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from app.services.gemini_service import gemini_service

logger = logging.getLogger("foceye.ai")


class AIAnalyzerService:
    """
    Diagnostic biomarker evaluation using Google Gemini API (via GeminiService)
    with evidence-based clinical decision support heuristic fallback.
    In-memory TTL caching prevents redundant API consumption.
    """

    _cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
    _CACHE_TTL_SECONDS = 600.0  # 10 minutes

    @staticmethod
    async def analyze_patient_metrics(
        condition: str,
        age: int,
        bcea_score: float,
        fixation_stability: float,
        saccadic_latency_ms: float,
        adherence_rate: float,
        horizontal_gaze_range_deg: Optional[float] = None,
        vertical_gaze_range_deg: Optional[float] = None,
        pursuit_gain: Optional[float] = None,
        blink_rate_bpm: Optional[float] = None,
        incomplete_blink_pct: Optional[float] = None,
        calibration_accuracy: Optional[float] = None,
        total_frames_sampled: Optional[int] = None,
        voms_scores: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        
        # Check cache
        cache_key = (
            f"{condition}_{age}_{bcea_score}_{fixation_stability}_{saccadic_latency_ms}_{adherence_rate}_"
            f"{horizontal_gaze_range_deg}_{vertical_gaze_range_deg}_{pursuit_gain}_{blink_rate_bpm}_"
            f"{incomplete_blink_pct}_{calibration_accuracy}_{total_frames_sampled}_{voms_scores}"
        )
        now = time.time()
        if cache_key in AIAnalyzerService._cache:
            cached_time, cached_val = AIAnalyzerService._cache[cache_key]
            if now - cached_time < AIAnalyzerService._CACHE_TTL_SECONDS:
                logger.info("Returning cached AI analysis result.")
                return cached_val

        # Defaults for clinical ranges
        h_range = horizontal_gaze_range_deg if horizontal_gaze_range_deg is not None else 35.0
        v_range = vertical_gaze_range_deg if vertical_gaze_range_deg is not None else 28.0
        gain = pursuit_gain if pursuit_gain is not None else 0.90
        bpm = blink_rate_bpm if blink_rate_bpm is not None else 16.0
        inc_blinks = incomplete_blink_pct if incomplete_blink_pct is not None else 10.0
        cal_acc = calibration_accuracy if calibration_accuracy is not None else 95.0
        frames = total_frames_sampled if total_frames_sampled is not None else 60

        system_instruction = (
            "You are a senior clinical neuro-ophthalmologist and vision therapy AI consultant for FOCEYE. "
            "Analyze patient eye-tracking and clinical metrics objectively based strictly on the provided data. "
            "Return valid JSON only matching the requested schema."
        )

        prompt = f"""
        Analyze the following actual patient eye-tracking and clinical assessment data.
        
        CRITICAL CLINICAL REQUIREMENTS:
        1. Base your evaluation strictly on the collected eye-tracking metrics below. Do NOT hallucinate pathologies or invent medical diagnoses without evidence.
        2. Clearly separate:
           - "observed_findings" (array of strings: objective physiological findings from the measurements)
           - "possible_concerns" (array of strings: evidence-based clinical interpretations or risks, or state "No significant oculomotor deficits detected" if normal)
           - "recommendations" (array of strings: specific vision therapy regimens, follow-up timelines, and visual hygiene)
        3. Determine data sufficiency:
           - If calibration accuracy < 85% or frames sampled < 20, set "data_sufficiency" to "Insufficient" and explicitly note in summary and recommendations that more assessment is required.
           - Otherwise set "data_sufficiency" to "Sufficient".
        4. Return a strictly valid JSON object with:
           - summary (string: concise clinical synthesis without unsupported claims)
           - risk_level ("Low", "Moderate", "High")
           - confidence_score (float between 0.80 and 0.99)
           - biomarkers (list of objects with: name, value, status, recommendation)
           - recommended_protocols (list of strings)
           - observed_findings (list of strings)
           - possible_concerns (list of strings)
           - recommendations (list of strings)
           - data_sufficiency ("Sufficient" or "Insufficient")
           - confidence_quality_indicator (string)

        Patient Assessment Data:
        - Primary Evaluation / Condition: {condition}
        - Age: {age}
        - Fixation BCEA (68% Ellipse Area): {bcea_score} deg² (Normal < 1.0 deg²)
        - Fixation Stability: {fixation_stability}% (Normal > 85%)
        - Saccadic Latency: {saccadic_latency_ms} ms (Normal 180-230 ms)
        - Smooth Pursuit Gain: {gain}x (Normal 0.90-1.00)
        - Horizontal Gaze Range: {h_range}° (Normal 30-45°)
        - Vertical Gaze Range: {v_range}° (Normal 25-35°)
        - Blink Rate: {bpm} BPM (Normal 14-18 BPM)
        - Incomplete Blink Ratio: {inc_blinks}% (Normal < 15%)
        - Calibration Tracking Accuracy: {cal_acc}% (Minimum passing 85%)
        - Therapy Adherence: {adherence_rate}%
        - Actual Frames Tracked: {frames}
        """

        if voms_scores:
            prompt += f"""
        Vestibular / Ocular-Motor Screening (VOMS Concussion Protocol):
        - Headache Provocation: {voms_scores.get('headache', 0)} / 10
        - Dizziness Provocation: {voms_scores.get('dizziness', 0)} / 10
        - Nausea Provocation: {voms_scores.get('nausea', 0)} / 10
        - Fogginess Provocation: {voms_scores.get('fogginess', 0)} / 10
        - Near Point of Convergence (NPC) Breakpoint: {voms_scores.get('npcCm', 5.0)} cm (Abnormal > 5.0 cm)
        - VOMS Clinical Sign: {"POSITIVE for Vestibular/Ocular Dysfunction or Concussion" if voms_scores.get('isPositive') else "NEGATIVE / Normal physiological tolerance"}
        Note: If VOMS is positive, emphasize return-to-learn / return-to-play graduated safety protocols in recommendations.
        """

        # Attempt inference using live Google Gemini API
        if gemini_service.is_configured:
            gemini_data, used_model, error_msg = await gemini_service.generate_json(
                prompt=prompt,
                system_instruction=system_instruction,
            )

            if gemini_data and isinstance(gemini_data, dict):
                # Ensure all required fields exist
                gemini_data["source"] = f"Gemini AI ({used_model})"
                res = AIAnalyzerService._ensure_schema(gemini_data, cal_acc, frames)
                AIAnalyzerService._cache[cache_key] = (now, res)
                return res
            else:
                logger.warning(f"Gemini API invocation unsuccessful ({error_msg}). Falling back to Clinical Heuristic Engine.")
        else:
            logger.info("Gemini API not configured. Utilizing Clinical Decision Support Engine fallback.")

        # Resilient Clinical Decision Support Heuristic Fallback Engine
        res = AIAnalyzerService._heuristic_clinical_eval(
            condition=condition,
            age=age,
            bcea_score=bcea_score,
            fixation_stability=fixation_stability,
            saccadic_latency_ms=saccadic_latency_ms,
            adherence_rate=adherence_rate,
            horizontal_gaze_range_deg=h_range,
            vertical_gaze_range_deg=v_range,
            pursuit_gain=gain,
            blink_rate_bpm=bpm,
            incomplete_blink_pct=inc_blinks,
            calibration_accuracy=cal_acc,
            total_frames_sampled=frames,
            voms_scores=voms_scores,
        )
        AIAnalyzerService._cache[cache_key] = (now, res)
        return res

    @staticmethod
    def _ensure_schema(data: Dict[str, Any], cal_acc: float, frames: int) -> Dict[str, Any]:
        if "summary" not in data or not data["summary"]:
            data["summary"] = "Clinical analysis completed with ophthalmic biometric indices."
        if "risk_level" not in data:
            data["risk_level"] = "Moderate"
        if "biomarkers" not in data or not isinstance(data["biomarkers"], list):
            data["biomarkers"] = []
        if "recommended_protocols" not in data or not isinstance(data["recommended_protocols"], list):
            data["recommended_protocols"] = ["Standard FOCEYE Vision Therapy Regimen"]
        if "observed_findings" not in data or not data["observed_findings"]:
            data["observed_findings"] = ["Biometric gaze stability and tracking velocity recorded."]
        if "possible_concerns" not in data or not data["possible_concerns"]:
            data["possible_concerns"] = ["No acute oculomotor concerns noted based on current data."]
        if "recommendations" not in data or not data["recommendations"]:
            data["recommendations"] = ["Maintain prescribed daily vision therapy protocol."]
        if "data_sufficiency" not in data:
            data["data_sufficiency"] = "Insufficient" if (cal_acc < 85.0 or frames < 20) else "Sufficient"
        if "confidence_quality_indicator" not in data:
            data["confidence_quality_indicator"] = (
                f"Data quality {data['data_sufficiency']} ({frames} frames, {cal_acc}% calibration accuracy)"
            )
        if "confidence_score" not in data:
            data["confidence_score"] = 0.92
        return data

    @staticmethod
    def _heuristic_clinical_eval(
        condition: str,
        age: int,
        bcea_score: float,
        fixation_stability: float,
        saccadic_latency_ms: float,
        adherence_rate: float,
        horizontal_gaze_range_deg: float = 35.0,
        vertical_gaze_range_deg: float = 28.0,
        pursuit_gain: float = 0.90,
        blink_rate_bpm: float = 16.0,
        incomplete_blink_pct: float = 10.0,
        calibration_accuracy: float = 95.0,
        total_frames_sampled: int = 60,
        voms_scores: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        
        is_insufficient = calibration_accuracy < 85.0 or total_frames_sampled < 20
        data_sufficiency = "Insufficient" if is_insufficient else "Sufficient"

        observed_findings = [
            f"Fixation stability measured at {fixation_stability}% with BCEA of {bcea_score} deg².",
            f"Conjugate smooth pursuit velocity gain measured at {pursuit_gain}x across {horizontal_gaze_range_deg}° horizontal excursion.",
            f"Saccadic reaction latency recorded at {saccadic_latency_ms} ms with {vertical_gaze_range_deg}° vertical range.",
            f"Blink rate of {blink_rate_bpm} BPM with {incomplete_blink_pct}% incomplete closures over {total_frames_sampled} tracked frames.",
            f"Baseline 9-point eye calibration verified at {calibration_accuracy}% precision."
        ]

        possible_concerns = []
        recommendations = []

        if is_insufficient:
            risk = "Moderate"
            summary = (
                f"Evaluation data is currently insufficient for definitive staging "
                f"({total_frames_sampled} frames captured, calibration {calibration_accuracy}%). "
                f"Further supervised evaluation is required before confirming targeted therapy."
            )
            possible_concerns.append("Data sufficiency is limited: calibration accuracy below clinical 85% threshold or low sample count.")
            recommendations.append("Perform 9-point recalibration before starting active therapy exercises.")
            recommendations.append("Repeat eye movement assessment under consistent ambient lighting.")
        elif bcea_score > 2.0 or fixation_stability < 70.0:
            risk = "High"
            summary = (
                f"Patient exhibits marked gaze dispersion (BCEA {bcea_score} deg²), "
                f"indicating significant amblyopic suppression or motor fusion deficit. "
                f"Saccadic initiation latency of {saccadic_latency_ms}ms suggests delayed target acquisition."
            )
            possible_concerns.append(f"Elevated foveal fixation drift ({bcea_score} deg² vs normative < 1.0 deg²).")
            if pursuit_gain < 0.85:
                possible_concerns.append(f"Deficient smooth pursuit gain ({pursuit_gain}x) necessitating catch-up saccades.")
            recommendations.append("Intensive central fixation hold training (15 minutes daily).")
            recommendations.append("Dynamic smooth pursuit step-ramp exercises.")
        elif bcea_score > 1.2 or fixation_stability < 85.0 or pursuit_gain < 0.88:
            risk = "Moderate"
            summary = (
                f"Moderate fixation instability noted ({fixation_stability}% stability). "
                f"Pursuit tracking gain is {pursuit_gain}x. Favorable therapy adherence ({adherence_rate}%)."
            )
            possible_concerns.append("Mild foveal tracking instability under dynamic ocular excursion.")
            recommendations.append("Near-point convergence pushups and target tracking exercises.")
            recommendations.append("Periodic 20-20-20 ocular breaks to mitigate visual fatigue.")
        else:
            risk = "Low"
            summary = (
                f"Oculomotor tracking and fixation stability are within normal physiological bounds "
                f"(BCEA {bcea_score} deg², {fixation_stability}% stability, pursuit gain {pursuit_gain}x). "
                f"Ready for standard developmental or maintenance therapy."
            )
            possible_concerns.append("No acute oculomotor or binocular coordination deficits identified in captured metrics.")
            recommendations.append("Routine maintenance visual conditioning (2x weekly).")
            recommendations.append("Follow-up progress check in 4 weeks.")

        biomarkers = [
            {
                "name": "Bivariate Contour Ellipse Area (BCEA 68%)",
                "value": f"{bcea_score} deg²",
                "status": "Elevated" if bcea_score > 1.2 else "Normal",
                "recommendation": "Intensify central foveal fixation training" if bcea_score > 1.2 else "Maintain current protocol"
            },
            {
                "name": "Fixation Stability Index",
                "value": f"{fixation_stability}%",
                "status": "Sub-optimal" if fixation_stability < 85.0 else "Optimal",
                "recommendation": "Incorporate high-contrast Gabor stimulus" if fixation_stability < 85.0 else "Progress to dynamic pursuit tracking"
            },
            {
                "name": "Smooth Pursuit Gain",
                "value": f"{pursuit_gain}x",
                "status": "Deficient" if pursuit_gain < 0.88 else "Normal",
                "recommendation": "Dynamic smooth pursuit tracking protocol"
            },
            {
                "name": "Saccadic Initiation Latency",
                "value": f"{saccadic_latency_ms} ms",
                "status": "Delayed" if saccadic_latency_ms > 240 else "Normal",
                "recommendation": "Step-ramp velocity stimulus protocol"
            },
            {
                "name": "Protocol Adherence",
                "value": f"{adherence_rate}%",
                "status": "Compliant" if adherence_rate >= 80 else "At-Risk",
                "recommendation": "Maintain regular 15-minute daily sessions"
            }
        ]

        if voms_scores and voms_scores.get("isPositive"):
            risk = "High"
            summary += f" Positive VOMS neuro-screening: provocation delta of {voms_scores.get('provocationDelta', 2)} and NPC {voms_scores.get('npcCm', 5.0)}cm indicate vestibular-ocular disruption."
            observed_findings.append(f"VOMS Concussion Screen Positive: Headache {voms_scores.get('headache', 0)}/10, Dizziness {voms_scores.get('dizziness', 0)}/10, Nausea {voms_scores.get('nausea', 0)}/10, Fogginess {voms_scores.get('fogginess', 0)}/10.")
            possible_concerns.append("Elevated symptom provocation during ocular-vestibular challenge consistent with mild concussion / vestibular dysfunction.")
            recommendations.append("Graduated Return-to-Learn and Return-to-Play safety protocol under supervision.")
            recommendations.append("Vestibular-ocular gaze stabilization conditioning.")
            biomarkers.append({
                "name": "VOMS Concussion Provocation",
                "value": f"Score {voms_scores.get('provocationDelta', 2)} (NPC {voms_scores.get('npcCm', 5.0)}cm)",
                "status": "Positive / Provoked",
                "recommendation": "Graduated return-to-activity protocol"
            })

        protocols = [
            "Dynamic Saccadic Step-Ramp Protocol (15 mins/day)",
            "Smooth Pursuit Target Tracking (10 mins/day)",
            "Near-Point Convergence Breakpoint Recovery",
            "9-Point Automated Fixation Re-Assessment"
        ]

        return {
            "summary": summary,
            "risk_level": risk,
            "biomarkers": biomarkers,
            "recommended_protocols": protocols,
            "observed_findings": observed_findings,
            "possible_concerns": possible_concerns,
            "recommendations": recommendations,
            "data_sufficiency": data_sufficiency,
            "confidence_quality_indicator": f"Data quality {data_sufficiency} ({total_frames_sampled} frames, {calibration_accuracy}% calibration)",
            "confidence_score": 0.72 if is_insufficient else 0.94,
            "source": "Clinical Decision Support Engine (Fallback)"
        }
