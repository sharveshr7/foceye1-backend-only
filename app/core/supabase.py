import logging
from typing import Any, Dict, List, Optional, Union
from app.core.config import settings

logger = logging.getLogger("foceye.supabase")

# Rich pre-seeded clinical dataset for in-memory resilient testing and instant local operation
_mock_db: Dict[str, List[Dict[str, Any]]] = {
    "profiles": [
        {
            "id": "clinician-001",
            "email": "dr.smith@foceye.clinic",
            "role": "clinician",
            "full_name": "Dr. Sarah Smith, OD",
            "clinic_name": "FOCEYE Ophthalmic Center",
            "hospital_name": "FOCEYE Ophthalmic Center",
            "license_number": "OD-98234-NY",
        },
        {
            "id": "admin-001",
            "email": "admin@foceye.clinic",
            "role": "admin",
            "full_name": "Dr. Marcus Vance, MD",
            "clinic_name": "FOCEYE Ophthalmic Center",
            "hospital_name": "FOCEYE Ophthalmic Center",
            "license_number": "MD-44512-NY",
        }
    ],
    "patients": [
        {
            "id": "PAT-001",
            "name": "Elena Rostova",
            "age": 11,
            "gender": "Female",
            "condition": "Refractive Amblyopia (Left Eye)",
            "icd10": "H53.00",
            "stage": "IN_PROGRESS",
            "clinical_status": "IN_PROGRESS",
            "initial_observation": "Bilateral tracking asymmetry, mild left head turn when viewing moving targets.",
            "observed_pattern": "Eccentric fixation, reduced left pursuit gain (0.74), suppression under binocular stimulus",
            "recommended_therapy": "target-tracking",
            "assigned_doctor": "Dr. Sarah Smith, OD",
            "adherence": 94,
            "last_session": "2026-09-10",
            "visual_acuity_left": "20/40",
            "visual_acuity_right": "20/20",
            "bcea_score": 0.85,
            "hospital_name": "FOCEYE Ophthalmic Center",
            "created_at": "2026-08-10T10:00:00Z",
        },
        {
            "id": "PAT-002",
            "name": "Marcus Brody",
            "age": 28,
            "gender": "Male",
            "condition": "Convergence Insufficiency",
            "icd10": "H51.11",
            "stage": "THERAPY_RECOMMENDED",
            "clinical_status": "THERAPY_RECOMMENDED",
            "initial_observation": "High exophoria at near (10 prism diopters), breaks into diplopia at 14cm.",
            "observed_pattern": "Binocular coordination deficit, elevated BCEA dispersal (1.82 deg²)",
            "recommended_therapy": "convergence-jump",
            "assigned_doctor": "Dr. Rachel Evans, MD",
            "adherence": 88,
            "last_session": "2026-08-16",
            "visual_acuity_left": "20/20",
            "visual_acuity_right": "20/25",
            "bcea_score": 1.82,
            "hospital_name": "FOCEYE Ophthalmic Center",
            "created_at": "2026-08-15T11:00:00Z",
        },
        {
            "id": "PAT-003",
            "name": "Liam Chen",
            "age": 8,
            "gender": "Male",
            "condition": "Intermittent Strabismus",
            "icd10": "H50.31",
            "stage": "EYE_TEST_COMPLETED",
            "clinical_status": "EYE_TEST_COMPLETED",
            "initial_observation": "Occasional outward deviation OD when fatigued. Rapid recovery on cover-uncover.",
            "observed_pattern": "Suppression scotoma under dichoptic stimulus, stable monocular fixation",
            "recommended_therapy": "anti-suppression",
            "assigned_doctor": "Dr. Sarah Smith, OD",
            "adherence": 100,
            "last_session": "2026-08-21",
            "visual_acuity_left": "20/25",
            "visual_acuity_right": "20/20",
            "bcea_score": 1.15,
            "hospital_name": "FOCEYE Ophthalmic Center",
            "created_at": "2026-08-20T14:30:00Z",
        },
        {
            "id": "PAT-004",
            "name": "Maya Patel",
            "age": 19,
            "gender": "Female",
            "condition": "Oculomotor Saccadic Dysfunction",
            "icd10": "H55.81",
            "stage": "EYE_TEST_PENDING",
            "clinical_status": "EYE_TEST_PENDING",
            "initial_observation": "Blink rate 24 bpm with 28% incomplete blinks. Tear film breakup time shortened.",
            "observed_pattern": "Baseline eye test pending calibration",
            "recommended_therapy": "saccadic-pacer",
            "assigned_doctor": "Dr. Rachel Evans, MD",
            "adherence": 100,
            "last_session": "2026-08-28",
            "visual_acuity_left": "20/20",
            "visual_acuity_right": "20/20",
            "bcea_score": 0.95,
            "hospital_name": "FOCEYE Ophthalmic Center",
            "created_at": "2026-08-28T09:00:00Z",
        },
        {
            "id": "PAT-005",
            "name": "David Kim",
            "age": 45,
            "gender": "Male",
            "condition": "Post-Concussion Ocular Dysmetria",
            "icd10": "S06.0X1A",
            "stage": "ADAPTIVE_STAGE",
            "clinical_status": "ADAPTIVE_STAGE",
            "initial_observation": "Dizziness and fogginess provoked during horizontal and vertical saccades (VAS 4/10).",
            "observed_pattern": "Saccadic dysmetria, reduced horizontal pursuit gain (0.68), symptom provocation at 1.5 Hz",
            "recommended_therapy": "pursuit-tracker",
            "assigned_doctor": "Dr. Sarah Smith, OD",
            "adherence": 92,
            "last_session": "2026-08-25",
            "visual_acuity_left": "20/30",
            "visual_acuity_right": "20/25",
            "bcea_score": 1.45,
            "hospital_name": "FOCEYE Ophthalmic Center",
            "created_at": "2026-07-22T16:00:00Z",
        },
    ],
    "eye_test_sessions": [
        {
            "id": "ETS-001",
            "session_id": "ETS-001",
            "patient_id": "PAT-001",
            "clinician_id": "Dr. Sarah Smith, OD",
            "session_status": "COMPLETED",
            "status": "COMPLETED",
            "tests_conducted": ["fixation_stability", "smooth_pursuit", "saccades"],
            "notes": "Baseline clinical ocular gaze evaluation",
            "created_at": "2026-08-11T09:30:00Z",
            "test_date": "2026-08-11",
            "completed_at": "2026-08-11T09:45:00Z",
        },
        {
            "id": "ETS-002",
            "session_id": "ETS-002",
            "patient_id": "PAT-001",
            "clinician_id": "Dr. Sarah Smith, OD",
            "session_status": "COMPLETED",
            "status": "COMPLETED",
            "tests_conducted": ["fixation_stability", "smooth_pursuit", "saccades"],
            "notes": "4-week follow up eye test after prescribed VR therapy",
            "created_at": "2026-09-02T14:15:00Z",
            "test_date": "2026-09-02",
            "completed_at": "2026-09-02T14:30:00Z",
        },
        {
            "id": "ETS-003",
            "session_id": "ETS-003",
            "patient_id": "PAT-002",
            "clinician_id": "Dr. Rachel Evans, MD",
            "session_status": "COMPLETED",
            "status": "COMPLETED",
            "tests_conducted": ["fixation_stability", "smooth_pursuit"],
            "notes": "Initial vergence and gaze evaluation",
            "created_at": "2026-08-16T11:00:00Z",
            "test_date": "2026-08-16",
            "completed_at": "2026-08-16T11:15:00Z",
        },
        {
            "id": "ETS-004",
            "session_id": "ETS-004",
            "patient_id": "PAT-003",
            "clinician_id": "Dr. Sarah Smith, OD",
            "session_status": "COMPLETED",
            "status": "COMPLETED",
            "tests_conducted": ["fixation_stability", "gaze_accuracy"],
            "notes": "Pediatric strabismus fixation check",
            "created_at": "2026-08-21T10:30:00Z",
            "test_date": "2026-08-21",
            "completed_at": "2026-08-21T10:45:00Z",
        },
        {
            "id": "ETS-005",
            "session_id": "ETS-005",
            "patient_id": "PAT-005",
            "clinician_id": "Dr. Sarah Smith, OD",
            "session_status": "COMPLETED",
            "status": "COMPLETED",
            "tests_conducted": ["fixation_stability", "saccades"],
            "notes": "Post-concussion baseline oculomotor telemetry",
            "created_at": "2026-07-23T15:00:00Z",
            "test_date": "2026-07-23",
            "completed_at": "2026-07-23T15:15:00Z",
        },
    ],
    "eye_test_results": [
        {
            "id": "ETR-001",
            "session_id": "ETS-001",
            "patient_id": "PAT-001",
            "test_type": "fixation_stability",
            "bcea_value": 1.32,
            "fixation_drift_deg": 0.65,
            "microsaccade_rate": 1.6,
            "gaze_accuracy_pct": 84.5,
            "tracking_confidence": 0.94,
            "data_quality_status": "good",
            "created_at": "2026-08-11T09:35:00Z",
        },
        {
            "id": "ETR-002",
            "session_id": "ETS-001",
            "patient_id": "PAT-001",
            "test_type": "smooth_pursuit",
            "pursuit_gain": 0.74,
            "phase_lag_deg": 18.2,
            "smooth_pursuit_ratio": 0.72,
            "tracking_confidence": 0.92,
            "data_quality_status": "good",
            "created_at": "2026-08-11T09:40:00Z",
        },
        {
            "id": "ETR-003",
            "session_id": "ETS-001",
            "patient_id": "PAT-001",
            "test_type": "saccades",
            "saccadic_latency_ms": 285.0,
            "peak_velocity_deg_s": 340.0,
            "accuracy_pct": 82.0,
            "tracking_confidence": 0.95,
            "data_quality_status": "good",
            "created_at": "2026-08-11T09:43:00Z",
        },
        {
            "id": "ETR-004",
            "session_id": "ETS-002",
            "patient_id": "PAT-001",
            "test_type": "fixation_stability",
            "bcea_value": 0.85,
            "fixation_drift_deg": 0.42,
            "microsaccade_rate": 1.1,
            "gaze_accuracy_pct": 91.5,
            "tracking_confidence": 0.96,
            "data_quality_status": "good",
            "created_at": "2026-09-02T14:20:00Z",
        },
        {
            "id": "ETR-005",
            "session_id": "ETS-002",
            "patient_id": "PAT-001",
            "test_type": "smooth_pursuit",
            "pursuit_gain": 0.88,
            "phase_lag_deg": 12.1,
            "smooth_pursuit_ratio": 0.86,
            "tracking_confidence": 0.95,
            "data_quality_status": "good",
            "created_at": "2026-09-02T14:24:00Z",
        },
        {
            "id": "ETR-006",
            "session_id": "ETS-002",
            "patient_id": "PAT-001",
            "test_type": "saccades",
            "saccadic_latency_ms": 232.0,
            "peak_velocity_deg_s": 395.0,
            "accuracy_pct": 92.5,
            "tracking_confidence": 0.97,
            "data_quality_status": "good",
            "created_at": "2026-09-02T14:28:00Z",
        },
        {
            "id": "ETR-007",
            "session_id": "ETS-003",
            "patient_id": "PAT-002",
            "test_type": "fixation_stability",
            "bcea_value": 1.82,
            "fixation_drift_deg": 0.78,
            "microsaccade_rate": 1.9,
            "gaze_accuracy_pct": 79.0,
            "tracking_confidence": 0.91,
            "data_quality_status": "good",
            "created_at": "2026-08-16T11:05:00Z",
        },
        {
            "id": "ETR-008",
            "session_id": "ETS-004",
            "patient_id": "PAT-003",
            "test_type": "fixation_stability",
            "bcea_value": 1.15,
            "fixation_drift_deg": 0.52,
            "microsaccade_rate": 1.4,
            "gaze_accuracy_pct": 88.0,
            "tracking_confidence": 0.93,
            "data_quality_status": "good",
            "created_at": "2026-08-21T10:35:00Z",
        },
        {
            "id": "ETR-009",
            "session_id": "ETS-005",
            "patient_id": "PAT-005",
            "test_type": "fixation_stability",
            "bcea_value": 1.45,
            "fixation_drift_deg": 0.68,
            "microsaccade_rate": 1.7,
            "gaze_accuracy_pct": 83.0,
            "tracking_confidence": 0.89,
            "data_quality_status": "good",
            "created_at": "2026-07-23T15:05:00Z",
        },
    ],
    "ai_analyses": [
        {
            "id": "AIA-001",
            "eye_test_session_id": "ETS-001",
            "session_id": "ETS-001",
            "patient_id": "PAT-001",
            "observed_pattern": "Reduced left horizontal pursuit gain (0.74) and elevated BCEA dispersal consistent with eccentric amblyopic fixation.",
            "clinical_correlation_notes": "Telemetry aligns with anisometropic amblyopia presentation.",
            "confidence_score": 0.93,
            "risk_indicators": [],
            "clinician_review_status": "approved",
            "clinician_notes": "Approved for VR pursuit and anti-suppression rehabilitation protocol.",
            "created_at": "2026-08-11T09:46:00Z",
        },
        {
            "id": "AIA-002",
            "eye_test_session_id": "ETS-002",
            "session_id": "ETS-002",
            "patient_id": "PAT-001",
            "observed_pattern": "BCEA contracted to 0.85 deg² with pursuit gain recovered to 0.88 (+18.9% longitudinal improvement).",
            "clinical_correlation_notes": "Significant oculomotor consolidation observed over 6 therapy sessions.",
            "confidence_score": 0.96,
            "risk_indicators": [],
            "clinician_review_status": "approved",
            "clinician_notes": "Marked improvement noted. Continue current protocol.",
            "created_at": "2026-09-02T14:30:00Z",
        },
        {
            "id": "AIA-003",
            "eye_test_session_id": "ETS-003",
            "session_id": "ETS-003",
            "patient_id": "PAT-002",
            "observed_pattern": "Elevated BCEA dispersal (1.82 deg²) with binocular coordination deficit at near target distances.",
            "clinical_correlation_notes": "Correlates with symptomatic near-point convergence insufficiency.",
            "confidence_score": 0.91,
            "risk_indicators": [],
            "clinician_review_status": "approved",
            "clinician_notes": "Recommending convergence jump and stepped depth therapy.",
            "created_at": "2026-08-16T11:15:00Z",
        },
        {
            "id": "AIA-004",
            "eye_test_session_id": "ETS-004",
            "session_id": "ETS-004",
            "patient_id": "PAT-003",
            "observed_pattern": "Suppression scotoma under dichoptic stimulus, stable monocular fixation with mild outward drift OD.",
            "clinical_correlation_notes": "Intermittent exotropia with suppression requires clinician review.",
            "confidence_score": 0.89,
            "risk_indicators": [],
            "clinician_review_status": "pending",
            "clinician_notes": None,
            "created_at": "2026-08-21T10:45:00Z",
        },
        {
            "id": "AIA-005",
            "eye_test_session_id": "ETS-005",
            "session_id": "ETS-005",
            "patient_id": "PAT-005",
            "observed_pattern": "Post-concussion saccadic dysmetria, reduced horizontal pursuit gain (0.68), symptom provocation at 1.5 Hz.",
            "clinical_correlation_notes": "Vestibular-ocular motor disruption following mild TBI.",
            "confidence_score": 0.92,
            "risk_indicators": [],
            "clinician_review_status": "approved",
            "clinician_notes": "Careful progression with adaptive pacing enabled.",
            "created_at": "2026-07-23T15:20:00Z",
        },
    ],
    "therapy_recommendations": [
        {
            "id": "REC-001",
            "eye_test_session_id": "ETS-001",
            "session_id": "ETS-001",
            "patient_id": "PAT-001",
            "exercise_category": "Smooth Pursuit Exercise",
            "suggested_difficulty": "moderate",
            "suggested_duration_min": 10,
            "suggested_duration_max": 15,
            "frequency_per_week": 3,
            "clinician_review_status": "approved",
            "recommendation_status": "approved",
            "clinician_name": "Dr. Sarah Smith, OD",
            "recommendation_rationale": "Horizontal smooth pursuit with dichoptic contrast modulation to engage amblyopic left eye.",
            "created_at": "2026-08-11T09:50:00Z",
        },
        {
            "id": "REC-002",
            "eye_test_session_id": "ETS-003",
            "session_id": "ETS-003",
            "patient_id": "PAT-002",
            "exercise_category": "Gaze Accuracy Exercise",
            "suggested_difficulty": "beginner",
            "suggested_duration_min": 10,
            "suggested_duration_max": 15,
            "frequency_per_week": 4,
            "clinician_review_status": "pending",
            "recommendation_status": "pending_review",
            "clinician_name": None,
            "recommendation_rationale": "Stepped vergence ramp exercises to restore near-point convergence amplitude.",
            "created_at": "2026-08-16T11:20:00Z",
        },
        {
            "id": "REC-003",
            "eye_test_session_id": "ETS-005",
            "session_id": "ETS-005",
            "patient_id": "PAT-005",
            "exercise_category": "Smooth Pursuit Exercise",
            "suggested_difficulty": "moderate",
            "suggested_duration_min": 8,
            "suggested_duration_max": 12,
            "frequency_per_week": 3,
            "clinician_review_status": "approved",
            "recommendation_status": "approved",
            "clinician_name": "Dr. Sarah Smith, OD",
            "recommendation_rationale": "Low-frequency target pursuit with automatic speed throttling upon saccadic fatigue.",
            "created_at": "2026-07-23T15:25:00Z",
        },
    ],
    "therapy_sessions": [
        {
            "id": "THS-001",
            "patient_id": "PAT-001",
            "recommendation_id": "REC-001",
            "exercise_type": "horizontal_moving_target",
            "session_status": "completed",
            "planned_duration_seconds": 600,
            "actual_duration_seconds": 600,
            "difficulty": "beginner",
            "assigned_by": "Dr. Sarah Smith, OD",
            "created_at": "2026-08-13T10:00:00Z",
        },
        {
            "id": "THS-002",
            "patient_id": "PAT-001",
            "recommendation_id": "REC-001",
            "exercise_type": "horizontal_moving_target",
            "session_status": "completed",
            "planned_duration_seconds": 600,
            "actual_duration_seconds": 600,
            "difficulty": "beginner",
            "assigned_by": "Dr. Sarah Smith, OD",
            "created_at": "2026-08-17T10:00:00Z",
        },
        {
            "id": "THS-003",
            "patient_id": "PAT-001",
            "recommendation_id": "REC-001",
            "exercise_type": "horizontal_moving_target",
            "session_status": "completed",
            "planned_duration_seconds": 720,
            "actual_duration_seconds": 720,
            "difficulty": "moderate",
            "assigned_by": "Dr. Sarah Smith, OD",
            "created_at": "2026-08-22T10:00:00Z",
        },
        {
            "id": "THS-004",
            "patient_id": "PAT-001",
            "recommendation_id": "REC-001",
            "exercise_type": "horizontal_moving_target",
            "session_status": "completed",
            "planned_duration_seconds": 720,
            "actual_duration_seconds": 720,
            "difficulty": "moderate",
            "assigned_by": "Dr. Sarah Smith, OD",
            "created_at": "2026-08-26T10:00:00Z",
        },
        {
            "id": "THS-005",
            "patient_id": "PAT-001",
            "recommendation_id": "REC-001",
            "exercise_type": "horizontal_moving_target",
            "session_status": "completed",
            "planned_duration_seconds": 900,
            "actual_duration_seconds": 900,
            "difficulty": "moderate",
            "assigned_by": "Dr. Sarah Smith, OD",
            "created_at": "2026-09-03T10:00:00Z",
        },
        {
            "id": "THS-006",
            "patient_id": "PAT-001",
            "recommendation_id": "REC-001",
            "exercise_type": "horizontal_moving_target",
            "session_status": "completed",
            "planned_duration_seconds": 900,
            "actual_duration_seconds": 900,
            "difficulty": "intermediate",
            "assigned_by": "Dr. Sarah Smith, OD",
            "created_at": "2026-09-10T10:00:00Z",
        },
        {
            "id": "THS-007",
            "patient_id": "PAT-005",
            "recommendation_id": "REC-003",
            "exercise_type": "horizontal_moving_target",
            "session_status": "completed",
            "planned_duration_seconds": 600,
            "actual_duration_seconds": 600,
            "difficulty": "beginner",
            "assigned_by": "Dr. Sarah Smith, OD",
            "created_at": "2026-07-28T14:00:00Z",
        },
        {
            "id": "THS-008",
            "patient_id": "PAT-005",
            "recommendation_id": "REC-003",
            "exercise_type": "horizontal_moving_target",
            "session_status": "stopped",
            "stop_reason": "Patient reported dizziness during 1.5Hz fast target pursuit phase",
            "planned_duration_seconds": 600,
            "actual_duration_seconds": 240,
            "difficulty": "moderate",
            "assigned_by": "Dr. Sarah Smith, OD",
            "created_at": "2026-08-04T14:00:00Z",
        },
        {
            "id": "THS-009",
            "patient_id": "PAT-005",
            "recommendation_id": "REC-003",
            "exercise_type": "horizontal_moving_target",
            "session_status": "completed",
            "planned_duration_seconds": 480,
            "actual_duration_seconds": 480,
            "difficulty": "beginner",
            "assigned_by": "Dr. Sarah Smith, OD",
            "created_at": "2026-08-12T14:00:00Z",
        },
        {
            "id": "THS-010",
            "patient_id": "PAT-005",
            "recommendation_id": "REC-003",
            "exercise_type": "horizontal_moving_target",
            "session_status": "completed",
            "planned_duration_seconds": 600,
            "actual_duration_seconds": 600,
            "difficulty": "moderate",
            "assigned_by": "Dr. Sarah Smith, OD",
            "created_at": "2026-08-25T14:00:00Z",
        },
    ],
    "therapy_session_results": [
        {
            "id": "TSR-001",
            "therapy_session_id": "THS-001",
            "patient_id": "PAT-001",
            "exercise_type": "horizontal_moving_target",
            "score": 78.0,
            "accuracy": 78.5,
            "reaction_time": 265.0,
            "completion_percentage": 100.0,
            "valid_sample_count": 34500,
            "tracking_confidence": 0.94,
            "target_loss_events": 4,
            "created_at": "2026-08-13T10:10:00Z",
        },
        {
            "id": "TSR-002",
            "therapy_session_id": "THS-002",
            "patient_id": "PAT-001",
            "exercise_type": "horizontal_moving_target",
            "score": 82.0,
            "accuracy": 82.0,
            "reaction_time": 250.0,
            "completion_percentage": 100.0,
            "valid_sample_count": 34800,
            "tracking_confidence": 0.95,
            "target_loss_events": 3,
            "created_at": "2026-08-17T10:10:00Z",
        },
        {
            "id": "TSR-003",
            "therapy_session_id": "THS-003",
            "patient_id": "PAT-001",
            "exercise_type": "horizontal_moving_target",
            "score": 86.0,
            "accuracy": 85.5,
            "reaction_time": 242.0,
            "completion_percentage": 100.0,
            "valid_sample_count": 41200,
            "tracking_confidence": 0.95,
            "target_loss_events": 2,
            "created_at": "2026-08-22T10:12:00Z",
        },
        {
            "id": "TSR-004",
            "therapy_session_id": "THS-004",
            "patient_id": "PAT-001",
            "exercise_type": "horizontal_moving_target",
            "score": 89.0,
            "accuracy": 88.0,
            "reaction_time": 235.0,
            "completion_percentage": 100.0,
            "valid_sample_count": 41500,
            "tracking_confidence": 0.96,
            "target_loss_events": 2,
            "created_at": "2026-08-26T10:12:00Z",
        },
        {
            "id": "TSR-005",
            "therapy_session_id": "THS-005",
            "patient_id": "PAT-001",
            "exercise_type": "horizontal_moving_target",
            "score": 91.0,
            "accuracy": 91.5,
            "reaction_time": 228.0,
            "completion_percentage": 100.0,
            "valid_sample_count": 52000,
            "tracking_confidence": 0.96,
            "target_loss_events": 1,
            "created_at": "2026-09-03T10:15:00Z",
        },
        {
            "id": "TSR-006",
            "therapy_session_id": "THS-006",
            "patient_id": "PAT-001",
            "exercise_type": "horizontal_moving_target",
            "score": 94.0,
            "accuracy": 94.0,
            "reaction_time": 218.0,
            "completion_percentage": 100.0,
            "valid_sample_count": 52400,
            "tracking_confidence": 0.97,
            "target_loss_events": 1,
            "created_at": "2026-09-10T10:15:00Z",
        },
        {
            "id": "TSR-007",
            "therapy_session_id": "THS-007",
            "patient_id": "PAT-005",
            "exercise_type": "horizontal_moving_target",
            "score": 79.0,
            "accuracy": 79.0,
            "reaction_time": 290.0,
            "completion_percentage": 100.0,
            "valid_sample_count": 34000,
            "tracking_confidence": 0.91,
            "target_loss_events": 5,
            "created_at": "2026-07-28T14:10:00Z",
        },
        {
            "id": "TSR-008",
            "therapy_session_id": "THS-008",
            "patient_id": "PAT-005",
            "exercise_type": "horizontal_moving_target",
            "score": 52.0,
            "accuracy": 54.0,
            "reaction_time": 340.0,
            "completion_percentage": 40.0,
            "valid_sample_count": 13600,
            "tracking_confidence": 0.88,
            "target_loss_events": 6,
            "created_at": "2026-08-04T14:04:00Z",
        },
        {
            "id": "TSR-009",
            "therapy_session_id": "THS-009",
            "patient_id": "PAT-005",
            "exercise_type": "horizontal_moving_target",
            "score": 84.0,
            "accuracy": 83.5,
            "reaction_time": 275.0,
            "completion_percentage": 100.0,
            "valid_sample_count": 27200,
            "tracking_confidence": 0.93,
            "target_loss_events": 3,
            "created_at": "2026-08-12T14:08:00Z",
        },
        {
            "id": "TSR-010",
            "therapy_session_id": "THS-010",
            "patient_id": "PAT-005",
            "exercise_type": "horizontal_moving_target",
            "score": 88.0,
            "accuracy": 88.5,
            "reaction_time": 255.0,
            "completion_percentage": 100.0,
            "valid_sample_count": 34200,
            "tracking_confidence": 0.95,
            "target_loss_events": 2,
            "created_at": "2026-08-25T14:10:00Z",
        },
    ],
    "adaptive_therapy_configs": [
        {
            "id": "ATC-001",
            "patient_id": "PAT-001",
            "exercise_id": "horizontal_moving_target",
            "enabled": True,
            "adaptive_mode": "controlled_automatic",
            "minimum_difficulty": 1,
            "maximum_difficulty": 5,
            "starting_difficulty": 2,
            "current_difficulty": 3,
            "progression_threshold": 85.0,
            "regression_threshold": 50.0,
            "step_size": 1,
            "minimum_sessions_before_adaptation": 2,
            "max_daily_difficulty_increase": 1,
            "clinician_approval_required": True,
            "created_at": "2026-08-11T10:00:00Z",
        },
        {
            "id": "ATC-002",
            "patient_id": "PAT-005",
            "exercise_id": "horizontal_moving_target",
            "enabled": True,
            "adaptive_mode": "controlled_automatic",
            "minimum_difficulty": 1,
            "maximum_difficulty": 4,
            "starting_difficulty": 1,
            "current_difficulty": 2,
            "progression_threshold": 85.0,
            "regression_threshold": 50.0,
            "step_size": 1,
            "minimum_sessions_before_adaptation": 2,
            "max_daily_difficulty_increase": 1,
            "clinician_approval_required": True,
            "created_at": "2026-07-23T15:30:00Z",
        },
    ],
    "therapy_adaptation_recommendations": [
        {
            "id": "TAR-001",
            "patient_id": "PAT-005",
            "config_id": "ATC-002",
            "exercise_id": "horizontal_moving_target",
            "direction": "progression",
            "current_difficulty": 2,
            "recommended_difficulty": 3,
            "approval_status": "pending_review",
            "reason": "Patient scored 88.5% accuracy in session THS-010 exceeding 85% threshold with steady tracking confidence.",
            "created_at": "2026-08-26T10:00:00Z",
        },
    ],
    "therapy_adaptation_audits": [
        {
            "id": "AD-001",
            "patient_id": "PAT-001",
            "config_id": "ATC-001",
            "action_type": "progression_approved",
            "previous_difficulty": 2,
            "new_difficulty": 3,
            "clinician_id": "Dr. Sarah Smith, OD",
            "notes": "Approved step up to Level 3 after consecutive >85% sessions.",
            "created_at": "2026-08-26T11:00:00Z",
        }
    ],
    "clinician_progress_notes": [
        {
            "id": "CPN-001",
            "patient_id": "PAT-001",
            "clinician_name": "Dr. Sarah Smith, OD",
            "note": "Patient demonstrates steady fixation consolidation. Visual acuity in amblyopic left eye improved from 20/60 to 20/40. BCEA reduced from 1.32 to 0.85 deg².",
            "created_at": "2026-09-10T11:00:00Z",
        },
        {
            "id": "CPN-002",
            "patient_id": "PAT-005",
            "clinician_name": "Dr. Sarah Smith, OD",
            "note": "Post-concussion symptoms provoked during fast movement on 08/04. Pacing reduced; patient fully recovered and stabilized at Level 2.",
            "created_at": "2026-08-25T15:00:00Z",
        },
    ],
    "notifications": [
        {
            "id": "NOTIF-001",
            "title": "Discomfort Alert: Session Stopped",
            "message": "David Kim (PAT-005) reported dizziness during 1.5Hz target pursuit. Session stopped early.",
            "category": "discomfort",
            "patient_id": "PAT-005",
            "is_read": False,
            "created_at": "2026-08-04T14:05:00Z",
        },
        {
            "id": "NOTIF-002",
            "title": "Eye Test Analysis Pending Review",
            "message": "Computerized eye test analysis for Liam Chen (PAT-003) completed and awaits clinical sign-off.",
            "category": "eye_test_review",
            "patient_id": "PAT-003",
            "is_read": False,
            "created_at": "2026-08-21T10:46:00Z",
        },
        {
            "id": "NOTIF-003",
            "title": "Therapy Protocol Approval Required",
            "message": "AI-suggested vergence therapy protocol generated for Marcus Brody (PAT-002).",
            "category": "therapy_recommendation_approval",
            "patient_id": "PAT-002",
            "is_read": False,
            "created_at": "2026-08-16T11:21:00Z",
        },
        {
            "id": "NOTIF-004",
            "title": "Adaptive Difficulty Progression",
            "message": "Adaptive engine recommends advancing David Kim (PAT-005) from Level 2 to Level 3.",
            "category": "adaptation_review",
            "patient_id": "PAT-005",
            "is_read": False,
            "created_at": "2026-08-26T10:02:00Z",
        },
    ],
    "system_activity_logs": [
        {
            "id": "ACT-001",
            "patient_id": "PAT-001",
            "patient_name": "Elena Rostova",
            "event_type": "therapy_session_completed",
            "title": "VR Therapy Completed",
            "description": "Completed 15 min Horizontal Smooth Pursuit at 94% accuracy.",
            "timestamp": "2026-09-10T10:15:00Z",
            "actor_name": "Elena Rostova",
        },
        {
            "id": "ACT-002",
            "patient_id": "PAT-001",
            "patient_name": "Elena Rostova",
            "event_type": "eye_test_completed",
            "title": "Follow-Up Eye Test Recorded",
            "description": "BCEA improved to 0.85 deg²; pursuit gain reached 0.88.",
            "timestamp": "2026-09-02T14:30:00Z",
            "actor_name": "Dr. Sarah Smith, OD",
        },
        {
            "id": "ACT-003",
            "patient_id": "PAT-005",
            "patient_name": "David Kim",
            "event_type": "adaptation_recommended",
            "title": "Difficulty Level Up Recommended",
            "description": "Performance exceeded 85% safety boundary. Level 3 progression proposed.",
            "timestamp": "2026-08-26T10:00:00Z",
            "actor_name": "Adaptive Engine",
        },
        {
            "id": "ACT-004",
            "patient_id": "PAT-003",
            "patient_name": "Liam Chen",
            "event_type": "eye_test_completed",
            "title": "Baseline Eye Test Completed",
            "description": "Suppression scotoma observed under dichoptic stimulus.",
            "timestamp": "2026-08-21T10:45:00Z",
            "actor_name": "Dr. Sarah Smith, OD",
        },
        {
            "id": "ACT-005",
            "patient_id": "PAT-002",
            "patient_name": "Marcus Brody",
            "event_type": "therapy_recommendation_generated",
            "title": "Therapy Plan Formulated",
            "description": "Stepped convergence jump therapy formulated, awaiting approval.",
            "timestamp": "2026-08-16T11:20:00Z",
            "actor_name": "AI Diagnostic Engine",
        },
    ],
    "calibration_records": [],
    "devices": [],
    "patient_progress_summaries": [],
    "ai_progress_summaries": [],
}


class MockSupabaseClient:
    """Resilient in-memory mock client when live Supabase credentials are not connected."""
    
    def __init__(self):
        self.db = _mock_db

    def table(self, table_name: str):
        return MockTableQuery(table_name, self.db)


class MockTableQuery:
    def __init__(self, table_name: str, db: Dict[str, List[Dict[str, Any]]]):
        self.table_name = table_name
        self.db = db
        if self.table_name not in self.db:
            self.db[self.table_name] = []
        self._filters: Dict[str, Any] = {}
        self._order_col: Optional[str] = None
        self._order_desc: bool = False
        self._limit_val: Optional[int] = None

    def select(self, *args, **kwargs):
        return self

    def eq(self, column: str, value: Any):
        self._filters[column] = value
        return self

    def order(self, column: str, desc: bool = False, **kwargs):
        self._order_col = column
        self._order_desc = desc
        return self

    def limit(self, count: int):
        self._limit_val = count
        return self

    def upsert(self, record: Union[Dict[str, Any], List[Dict[str, Any]]]):
        items = record if isinstance(record, list) else [record]
        self._pending_upsert = items
        return self

    def insert(self, record: Union[Dict[str, Any], List[Dict[str, Any]]]):
        items = record if isinstance(record, list) else [record]
        self._pending_insert = items
        return self

    def update(self, updates: Dict[str, Any]):
        self._pending_update = updates
        return self

    def delete(self):
        self._pending_delete = True
        return self

    def execute(self):
        if hasattr(self, "_pending_upsert") and self._pending_upsert:
            res = []
            for item in self._pending_upsert:
                item_id = item.get("id")
                found = False
                if item_id:
                    for existing in self.db[self.table_name]:
                        if existing.get("id") == item_id:
                            existing.update(item)
                            res.append(existing)
                            found = True
                            break
                if not found:
                    self.db[self.table_name].append(item)
                    res.append(item)
            self._pending_upsert = []
            return MockResponse(res)

        if hasattr(self, "_pending_insert") and self._pending_insert:
            for item in self._pending_insert:
                self.db[self.table_name].append(item)
            res = list(self._pending_insert)
            self._pending_insert = []
            return MockResponse(res)

        if hasattr(self, "_pending_update") and self._pending_update:
            updated = []
            for item in self.db[self.table_name]:
                if not self._filters or all(item.get(k) == v for k, v in self._filters.items()):
                    item.update(self._pending_update)
                    updated.append(item)
            self._pending_update = None
            return MockResponse(updated)

        if hasattr(self, "_pending_delete") and self._pending_delete:
            initial_len = len(self.db[self.table_name])
            if self._filters:
                self.db[self.table_name] = [
                    x for x in self.db[self.table_name]
                    if not all(x.get(k) == v for k, v in self._filters.items())
                ]
            deleted_count = initial_len - len(self.db[self.table_name])
            self._pending_delete = False
            return MockResponse([{"deleted": deleted_count}])

        records = list(self.db[self.table_name])
        if self._filters:
            records = [
                r for r in records
                if all(r.get(k) == v for k, v in self._filters.items())
            ]
        if self._order_col:
            records.sort(
                key=lambda x: str(x.get(self._order_col, "")),
                reverse=self._order_desc
            )
        if self._limit_val is not None:
            records = records[:self._limit_val]
        return MockResponse(records)


class MockResponse:
    def __init__(self, data: Any):
        self.data = data


def get_supabase_client():
    """Initializes the real Supabase client with optimized timeouts or falls back to in-memory mock."""
    key = settings.get_supabase_key()
    if (
        settings.SUPABASE_URL 
        and "mock" not in settings.SUPABASE_URL 
        and key 
        and "mock" not in key
    ):
        try:
            from supabase import create_client, Client, ClientOptions
            options = ClientOptions(
                postgrest_client_timeout=60.0,
                storage_client_timeout=30.0,
                auto_refresh_token=True,
                persist_session=True,
                headers={"X-Client-Info": "foceye-clinical-backend/1.0.0"}
            )
            client: Client = create_client(settings.SUPABASE_URL, key, options=options)
            logger.info(f"Connected to live Supabase project: {settings.SUPABASE_URL}")
            return client
        except Exception as e:
            logger.warning(f"Could not connect to live Supabase, using mock fallback: {e}")
            return MockSupabaseClient()
    return MockSupabaseClient()


supabase = get_supabase_client()


def execute_with_retry(query_builder, max_retries: int = 2, delay_seconds: float = 0.3):
    """
    Executes a Supabase PostgREST query with automatic retry on transient gateway/timeout errors.
    """
    import time
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return query_builder.execute()
        except Exception as exc:
            last_exc = exc
            err_str = str(exc)
            is_transient = any(code in err_str for code in ["504", "502", "503", "Gateway Timeout", "timed out", "Timeout"])
            if is_transient and attempt < max_retries:
                logger.warning(f"Transient Supabase error on query (attempt {attempt + 1}/{max_retries + 1}): {exc}. Retrying in {delay_seconds}s...")
                time.sleep(delay_seconds * (attempt + 1))
                continue
            raise exc
    raise last_exc


def check_supabase_connection() -> Dict[str, Any]:
    """
    Performs a real-time connectivity and latency ping against the configured database.
    Returns diagnostic telemetry: status, roundtrip latency (ms), mode, and error if any.
    """
    import time
    is_live = not isinstance(supabase, MockSupabaseClient)
    project_url = settings.SUPABASE_URL if is_live else "in_memory_mock"
    t0 = time.time()
    try:
        # Perform a minimal, lightweight ping query on the patients table
        res = supabase.table("patients").select("id").limit(1).execute()
        latency_ms = round((time.time() - t0) * 1000, 2)
        return {
            "status": "healthy",
            "connected": True,
            "mode": "live_cloud" if is_live else "in_memory_mock",
            "project_url": project_url,
            "latency_ms": latency_ms,
            "error": None
        }
    except Exception as e:
        latency_ms = round((time.time() - t0) * 1000, 2)
        logger.error(f"Supabase connection health check failed after {latency_ms}ms: {e}")
        return {
            "status": "unhealthy",
            "connected": False,
            "mode": "live_cloud" if is_live else "in_memory_mock",
            "project_url": project_url,
            "latency_ms": latency_ms,
            "error": str(e)
        }
