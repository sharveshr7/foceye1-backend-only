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

    @staticmethod
    async def generate_therapy_prescription(
        patient_name: str = "Patient",
        age: int = 30,
        condition: str = "Convergence Insufficiency",
        exercise_name: str = "Target Tracking",
        session_accuracy: float = 90.0,
        repetitions: int = 5,
        pre_fatigue_vas: int = 2,
        post_fatigue_vas: int = 3,
        working_distance_cm: int = 45,
        saccadic_latency_ms: float = 220.0,
        fixation_stability_pct: float = 92.0,
        language: str = "en",
    ) -> Dict[str, Any]:
        """
        Generates an automated 4-week Visual Rehabilitation Prescription (VRP)
        and a multilingual Patient Discharge Handout using Google Gemini.
        """
        lang_names = {
            "en": "English",
            "ta": "Tamil (தமிழ்)",
            "ml": "Malayalam (മലയാളം)",
            "te": "Telugu (తెలుగు)",
            "hi": "Hindi (हिन्दी)",
        }
        target_lang_label = lang_names.get(language, "English")

        prompt = f"""
        Generate an evidence-based 4-Week Visual Rehabilitation Prescription (VRP) and a multilingual Patient Discharge Handout.

        PATIENT & CLINICAL REHABILITATION DATA:
        - Patient Name: {patient_name}
        - Age: {age}
        - Eye Condition / Diagnosis: {condition}
        - Completed Exercise: {exercise_name}
        - Session Tracking Accuracy: {session_accuracy}%
        - Executed Repetitions: {repetitions}
        - Visual Fatigue (1-10 VAS): Baseline {pre_fatigue_vas}/10 -> Post-Session {post_fatigue_vas}/10
        - Working Distance: {working_distance_cm} cm
        - Saccadic Latency: {saccadic_latency_ms} ms
        - Fixation Stability: {fixation_stability_pct}%
        - Target Language for Patient Handout: {target_lang_label} (Language code: '{language}')

        CLINICAL REQUIREMENTS:
        1. Clinical Rationale: Concise 2-3 sentence explanation for the ophthalmologist on why this regimen stimulates oculomotor neuroplasticity.
        2. Weekly Regimen: Exactly 4 weeks (weeks 1 to 4) with progressive difficulty (Week 1 foundation, Week 2 ramp, Week 3 challenge, Week 4 stabilization).
        3. Home Discharge Handout:
           - MUST be written in the patient's requested language ({target_lang_label}).
           - Include patient greeting, clear daily home exercise instructions, ergonomic tips (20-20-20 rule, screen distance), red flag warning signs (sudden diplopia, severe pain), and follow-up timeline.
        
        Return STRICTLY a JSON object with this structure:
        {{
            "clinical_rationale": "...",
            "weekly_regimen": [
                {{
                    "week": 1,
                    "focus_goal": "...",
                    "daily_frequency": "...",
                    "target_duration_mins": 10,
                    "target_velocity": "1.0x",
                    "instructions": "..."
                }},
                ... (up to week 4)
            ],
            "home_discharge_handout": {{
                "title": "...",
                "greeting": "...",
                "instructions": ["...", "..."],
                "ergonomic_and_hygiene_tips": ["...", "..."],
                "red_flag_symptoms": ["...", "..."],
                "follow_up_schedule": "..."
            }}
        }}
        """

        system_instruction = (
            "You are a clinical neuro-ophthalmologist and certified vision therapist. "
            "Formulate an exact 4-week visual rehabilitation progression and patient-friendly discharge instructions. "
            f"Write the home_discharge_handout sections in fluent, warm, and natural {target_lang_label}. "
            "Output valid JSON only."
        )

        # 1. Attempt Gemini Generation
        if gemini_service.is_configured:
            parsed, used_model, err = await gemini_service.generate_json(
                prompt=prompt,
                system_instruction=system_instruction,
            )
            if parsed and "weekly_regimen" in parsed and "home_discharge_handout" in parsed:
                return {
                    "success": True,
                    "patient_name": patient_name,
                    "condition": condition,
                    "language": language,
                    "clinical_rationale": parsed.get("clinical_rationale", "Targeted oculomotor conditioning to reinforce binocular fusion and saccadic precision."),
                    "weekly_regimen": parsed["weekly_regimen"],
                    "home_discharge_handout": parsed["home_discharge_handout"],
                    "source": "Google Gemini Clinical Vision Engine",
                    "model": used_model or gemini_service.default_model,
                }
            logger.warning(f"Gemini prescription generation fell back: {err}")

        # 2. Evidence-Based Clinical Fallback
        return AIAnalyzerService._get_fallback_prescription(
            patient_name=patient_name,
            condition=condition,
            exercise_name=exercise_name,
            language=language,
            working_distance_cm=working_distance_cm,
        )

    @staticmethod
    def _get_fallback_prescription(
        patient_name: str,
        condition: str,
        exercise_name: str,
        language: str,
        working_distance_cm: int = 45,
    ) -> Dict[str, Any]:
        """Provides evidence-based optometric fallback protocols when offline."""
        regimen = [
            {
                "week": 1,
                "focus_goal": "Establish Baseline Neuro-Motor Coordination",
                "daily_frequency": "1 session / day",
                "target_duration_mins": 5,
                "target_velocity": "1.0x Pace",
                "instructions": f"Perform {exercise_name} at standard pace at {working_distance_cm} cm distance with head stabilized.",
            },
            {
                "week": 2,
                "focus_goal": "Saccadic Latency Reduction & Gaze Hold",
                "daily_frequency": "2 sessions / day",
                "target_duration_mins": 8,
                "target_velocity": "1.2x Pace",
                "instructions": "Maintain fixations on peripheral target jumps. Incorporate 20-second gaze breaks at midpoint.",
            },
            {
                "week": 3,
                "focus_goal": "Binocular Fusion & Smooth Pursuit Velocity",
                "daily_frequency": "2 sessions / day",
                "target_duration_mins": 10,
                "target_velocity": "1.4x Pace",
                "instructions": "Increase tracking velocity. Ensure consistent binocular engagement without head tilt.",
            },
            {
                "week": 4,
                "focus_goal": "Ocular Motility Consolidation & Visual Stamina",
                "daily_frequency": "1 session / day",
                "target_duration_mins": 10,
                "target_velocity": "1.5x Pace",
                "instructions": "Consolidate endurance. Perform post-session visual rest and record fatigue score.",
            },
        ]

        handouts: Dict[str, Dict[str, Any]] = {
            "en": {
                "title": "Home Visual Rehabilitation & Eye Hygiene Guide",
                "greeting": f"Dear {patient_name}, congratulations on completing your visual therapy session today.",
                "instructions": [
                    f"Perform prescribed {exercise_name} once to twice daily as outlined in your 4-week chart.",
                    f"Maintain your screen distance strictly at {working_distance_cm} cm (approx. an arm's length).",
                    "Keep your head completely steady during eye movements and blink naturally.",
                ],
                "ergonomic_and_hygiene_tips": [
                    "Follow the 20-20-20 Rule: Every 20 minutes of screen use, look 20 feet away for 20 seconds.",
                    "Ensure overhead room lighting is balanced to prevent glare and screen reflections.",
                    "Stay hydrated and remember to take scheduled visual rest breaks.",
                ],
                "red_flag_symptoms": [
                    "Sudden onset of double vision (diplopia) lasting > 5 minutes.",
                    "Severe sharp ocular pain or flashes of light.",
                ],
                "follow_up_schedule": "Schedule a follow-up review with your attending optometrist in 3 to 4 weeks.",
            },
            "ta": {
                "title": "வீட்டு பார்வை மறுவாழ்வு மற்றும் கண் பாதுகாப்பு வழிகாட்டி",
                "greeting": f"அன்புள்ள {patient_name}, உங்கள் கண் பயிற்சி அமர்வை வெற்றிகரமாக முடித்ததற்கு வாழ்த்துகள்.",
                "instructions": [
                    f"உங்கள் 4 வார அட்டவணையின்படி {exercise_name} பயிற்சியை தினமும் 1 முதல் 2 முறை செய்யவும்.",
                    f"திரையிலிருந்து கண் தூரத்தை சரியாக {working_distance_cm} செ.மீ அளவில் பராமரிக்கவும்.",
                    "கண் அசைவுகளின் போது தலையை அசைக்காமல் நேராக வைத்துக்கொள்ளவும்.",
                ],
                "ergonomic_and_hygiene_tips": [
                    "20-20-20 விதி: ஒவ்வொரு 20 நிமிடங்களுக்கும் 20 அடி தூரமுள்ள பொருளை 20 நொடிகள் பார்க்கவும்.",
                    "கண்களில் நீர்ச்சத்து குறையாமல் இருக்க போதுமான தண்ணீர் குடிக்கவும்.",
                    "அறை வெளிச்சம் திரைப் பிரதிபலிப்பு இல்லாமல் சீராக இருப்பதை உறுதிசெய்யவும்.",
                ],
                "red_flag_symptoms": [
                    "திடீரென இரட்டை பார்வை (Double vision) ஏற்படுதல்.",
                    "கடும் கண் வலி அல்லது ஒளிரும் புள்ளிகள் தோன்றுதல்.",
                ],
                "follow_up_schedule": "3 முதல் 4 வாரங்களில் உங்கள் கண் மருத்துவரிடம் மறுபரிசோதனைக்கு வரவும்.",
            },
            "hi": {
                "title": "घरेलू दृष्टि पुनर्वास एवं नेत्र सुरक्षा दिशानिर्देश",
                "greeting": f"प्रिय {patient_name}, आज अपना दृष्टि थेरेपी सत्र सफलतापूर्वक पूरा करने पर बधाई।",
                "instructions": [
                    f"अपने 4-सप्ताह के चार्ट के अनुसार {exercise_name} दिन में 1 से 2 बार करें।",
                    f"स्क्रीन से अपनी दूरी लगभग {working_distance_cm} सेमी (हाथ की दूरी) बनाए रखें।",
                    "व्यायाम करते समय सिर को स्थिर रखें और केवल आंखों को घुमाएं।",
                ],
                "ergonomic_and_hygiene_tips": [
                    "20-20-20 नियम: हर 20 मिनट के स्क्रीन समय के बाद 20 फीट दूर 20 सेकंड के लिए देखें।",
                    "पर्याप्त पानी पिएं और कमरे में रोशनी संतुलित रखें।",
                    "थकान महसूस होने पर 20 सेकंड का विश्राम अवश्य लें।",
                ],
                "red_flag_symptoms": [
                    "अचानक दोहरी दृष्टि (Double vision) दिखाई देना।",
                    "आंखों में तेज दर्द या चमकती रोशनी दिखाई देना।",
                ],
                "follow_up_schedule": "3 से 4 सप्ताह में अपने नेत्र रोग विशेषज्ञ से पुनः जांच कराएं।",
            },
            "te": {
                "title": "ఇంటి వద్ద కంటి వ్యాయామాలు మరియు భద్రతా సూచనలు",
                "greeting": f"ప్రియమైన {patient_name}, మీ విజన్ థెరపీ సెషన్‌ను విజయవంతంగా పూర్తి చేసినందుకు అభినందనలు.",
                "instructions": [
                    f"మీ 4 వారాల పట్టిక ప్రకారం {exercise_name} రోజుకు 1-2 సార్లు సాధన చేయండి.",
                    f"స్క్రీన్ నుండి దూరం ఖచ్చితంగా {working_distance_cm} సెం.మీ ఉండేలా చూసుకోండి.",
                    "వ్యాయామ సమయంలో తల తిప్పకుండా కేవలం కళ్ళను మాత్రమే కదపండి.",
                ],
                "ergonomic_and_hygiene_tips": [
                    "20-20-20 నియమం: ప్రతి 20 నిమిషాలకు 20 అడుగుల దూరాన్ని 20 సెకన్ల పాటు చూడండి.",
                    "కంటి అలసటను నివారించడానికి తగినంత నీరు త్రాగండి.",
                ],
                "red_flag_symptoms": [
                    "అకస్మాత్తుగా రెండుగా కనిపించడం (Double vision).",
                    "తీవ్రమైన కంటి నొప్పి లేదా మెరుపులు రావడం.",
                ],
                "follow_up_schedule": "3 నుండి 4 వారాలలో మీ కంటి వైద్యుడిని సంప్రదించండి.",
            },
            "ml": {
                "title": "ഗൃഹ നേത്ര പുനരധിവാസവും സംരക്ഷണ മാർഗ്ഗനിർദ്ദേശങ്ങളും",
                "greeting": f"പ്രിയപ്പെട്ട {patient_name}, നിങ്ങളുടെ ഇന്നത്തെ തെറാപ്പി വിജയകരമായി പൂർത്തിയാക്കിയതിന് അഭിനന്ദനങ്ങൾ.",
                "instructions": [
                    f"നിങ്ങളുടെ 4 ആഴ്ചത്തെ പട്ടിക അനുസരിച്ച് {exercise_name} വ്യായാമം ദിവസവും 1-2 തവണ ചെയ്യുക.",
                    f"സ്‌ക്രീനിൽ നിന്ന് {working_distance_cm} സെ.മീ അകലം കൃത്യമായി പാലിക്കുക.",
                    "തല അനക്കാതെ കൃഷ്ണമണികൾ മാത്രം ചലിപ്പിക്കുക.",
                ],
                "ergonomic_and_hygiene_tips": [
                    "20-20-20 നിയമം: ഓരോ 20 മിനിറ്റിലും 20 അടി അകലെയുള്ള വസ്തുവിലേക്ക് 20 സെക്കൻഡ് നോക്കുക.",
                    "ആവശ്യത്തിന് വെള്ളം കുടിക്കുകയും നേത്ര വിശ്രമം ഉറപ്പാക്കുകയും ചെയ്യുക.",
                ],
                "red_flag_symptoms": [
                    "പെട്ടെന്ന് വസ്തുക്കൾ രണ്ടായി കാണുക (Double vision).",
                    "തീവ്രമായ നേത്രവേദന അനുഭവപ്പെടുക.",
                ],
                "follow_up_schedule": "3-4 ആഴ്ചകൾക്കുള്ളിൽ ഡോക്ടറെ വീണ്ടും കാണുക.",
            },
        }

        chosen_handout = handouts.get(language, handouts["en"])

        return {
            "success": True,
            "patient_name": patient_name,
            "condition": condition,
            "language": language,
            "clinical_rationale": f"Structured progressive oculomotor exercise plan targeting {condition} to re-establish binocular coordination.",
            "weekly_regimen": regimen,
            "home_discharge_handout": chosen_handout,
            "source": "Clinical Decision Support Engine (Fallback Protocol)",
            "model": "rule-based-clinical-optometry",
        }

