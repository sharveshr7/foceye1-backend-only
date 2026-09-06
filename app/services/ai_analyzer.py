import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger("foceye.ai")


class AIAnalyzerService:
    """
    Diagnostic biomarker evaluation using Gemini Flash (via Google Generative AI SDK
    or direct REST API) with evidence-based clinical heuristic fallback.
    """

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
    ) -> Dict[str, Any]:
        
        # Resolve Gemini API Key from settings or environment
        api_key = (
            settings.GEMINI_API_KEY 
            or os.environ.get("GEMINI_API_KEY") 
            or os.environ.get("GOOGLE_API_KEY") 
            or ""
        ).strip()

        # Defaults for clinical ranges
        h_range = horizontal_gaze_range_deg if horizontal_gaze_range_deg is not None else 35.0
        v_range = vertical_gaze_range_deg if vertical_gaze_range_deg is not None else 28.0
        gain = pursuit_gain if pursuit_gain is not None else 0.90
        bpm = blink_rate_bpm if blink_rate_bpm is not None else 16.0
        inc_blinks = incomplete_blink_pct if incomplete_blink_pct is not None else 10.0
        cal_acc = calibration_accuracy if calibration_accuracy is not None else 95.0
        frames = total_frames_sampled if total_frames_sampled is not None else 60

        prompt = f"""
        You are a senior clinical neuro-ophthalmologist consulting for FOCEYE Vision Therapy.
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

        if api_key and "mock" not in api_key.lower() and not api_key.startswith("your-"):
            # Method 1: Google Generative AI SDK
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(settings.GEMINI_MODEL)

                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                
                cleaned_text = response.text.strip()
                match = re.search(r"\{.*\}", cleaned_text, re.DOTALL)
                if match:
                    cleaned_text = match.group(0)
                data = json.loads(cleaned_text)
                data["source"] = f"Gemini AI ({settings.GEMINI_MODEL})"
                return AIAnalyzerService._ensure_schema(data, cal_acc, frames)

            except Exception as sdk_err:
                logger.warning(f"Google Generative AI SDK call failed, trying direct REST API: {sdk_err}")

            # Method 2: Direct Gemini REST API via httpx
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={api_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "responseMimeType": "application/json"
                    }
                }
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        res_json = resp.json()
                        raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
                        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                        if match:
                            raw_text = match.group(0)
                        data = json.loads(raw_text)
                        data["source"] = f"Gemini REST ({settings.GEMINI_MODEL})"
                        return AIAnalyzerService._ensure_schema(data, cal_acc, frames)
                    else:
                        logger.warning(f"Gemini REST API returned status {resp.status_code}: {resp.text}")
            except Exception as rest_err:
                logger.warning(f"Gemini REST API invocation failed: {rest_err}")

        # Method 3: Resilient clinical heuristic fallback engine
        return AIAnalyzerService._heuristic_clinical_eval(
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
        )

    @staticmethod
    def _ensure_schema(data: Dict[str, Any], cal_acc: float, frames: int) -> Dict[str, Any]:
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
            possible_concerns.append(f"Mild foveal tracking instability under dynamic ocular excursion.")
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
            "source": "Clinical Decision Support Engine"
        }
