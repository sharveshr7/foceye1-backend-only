-- ==========================================================
-- FOCEYE Production PostgreSQL Schema for Supabase
-- Medical EHR, Eye-Tracking Telemetry & Therapy Management
-- Idempotent script: safe to run multiple times without data loss
-- ==========================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Profiles Table (Clinicians, Optometrists, Therapists, Staff)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'clinician' CHECK (role IN ('clinician', 'therapist', 'admin', 'patient', 'doctor')),
    clinic_name TEXT DEFAULT 'FOCEYE Ophthalmic Center',
    hospital_name TEXT,
    hospital_registration_number TEXT,
    hospital_type TEXT,
    mobile_number TEXT,
    city TEXT,
    state TEXT,
    password_hash TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Idempotent column migrations for existing profiles table
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS hospital_name TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS hospital_registration_number TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS hospital_type TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS mobile_number TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS city TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS state TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS password_hash TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- 2. Patients Table (EMR Records & Clinical State)
CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    age INTEGER NOT NULL CHECK (age >= 0 AND age <= 120),
    gender TEXT NOT NULL CHECK (gender IN ('Male', 'Female', 'Other')),
    condition TEXT NOT NULL DEFAULT 'Pending Eye Test',
    icd10 TEXT DEFAULT 'H53.00',
    hospital_id TEXT,
    date_of_birth DATE,
    phone TEXT,
    email TEXT,
    address TEXT,
    emergency_contact TEXT,
    medical_history TEXT,
    diagnosis TEXT,
    notes TEXT,
    stage TEXT DEFAULT 'EYE_TEST_PENDING',
    clinical_status TEXT DEFAULT 'EYE_TEST_PENDING',
    initial_observation TEXT,
    observed_pattern TEXT,
    recommended_therapy TEXT,
    assigned_doctor TEXT DEFAULT 'Dr. Sarah Smith, OD',
    adherence INTEGER DEFAULT 100 CHECK (adherence >= 0 AND adherence <= 100),
    last_session DATE DEFAULT CURRENT_DATE,
    visual_acuity_left TEXT DEFAULT '20/20',
    visual_acuity_right TEXT DEFAULT '20/20',
    bcea_score REAL DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Idempotent column migrations for existing patients table
ALTER TABLE patients ADD COLUMN IF NOT EXISTS clinical_status TEXT DEFAULT 'EYE_TEST_PENDING';
ALTER TABLE patients ADD COLUMN IF NOT EXISTS initial_observation TEXT;
ALTER TABLE patients ADD COLUMN IF NOT EXISTS observed_pattern TEXT;
ALTER TABLE patients ADD COLUMN IF NOT EXISTS recommended_therapy TEXT;
ALTER TABLE patients ADD COLUMN IF NOT EXISTS assigned_doctor TEXT DEFAULT 'Dr. Sarah Smith, OD';
ALTER TABLE patients ADD COLUMN IF NOT EXISTS hospital_id TEXT;
ALTER TABLE patients ADD COLUMN IF NOT EXISTS date_of_birth DATE;
ALTER TABLE patients ADD COLUMN IF NOT EXISTS phone TEXT;
ALTER TABLE patients ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE patients ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE patients ADD COLUMN IF NOT EXISTS emergency_contact TEXT;
ALTER TABLE patients ADD COLUMN IF NOT EXISTS medical_history TEXT;
ALTER TABLE patients ADD COLUMN IF NOT EXISTS diagnosis TEXT;
ALTER TABLE patients ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE patients ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- 3. Therapy Sessions Table (Biometric Telemetry & Performance Logs)
CREATE TABLE IF NOT EXISTS therapy_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    exercise_type TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL,
    fixation_score REAL NOT NULL,
    saccadic_score REAL NOT NULL,
    convergence_score REAL NOT NULL,
    overall_score REAL NOT NULL,
    bcea_68 REAL DEFAULT 1.2,
    bcea_95 REAL DEFAULT 2.4,
    language TEXT DEFAULT 'en',
    repetitions INTEGER DEFAULT 0,
    clinical_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Idempotent column migrations for existing therapy_sessions table
ALTER TABLE therapy_sessions ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'en';
ALTER TABLE therapy_sessions ADD COLUMN IF NOT EXISTS repetitions INTEGER DEFAULT 0;

-- 4. Calibration Records Table (9-Point Polynomial Surface Transform)
CREATE TABLE IF NOT EXISTS calibration_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rmse_pixels REAL NOT NULL,
    accuracy_percentage REAL NOT NULL,
    coefficients REAL[] NOT NULL,
    points_count INTEGER NOT NULL,
    patient_id UUID REFERENCES patients(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Idempotent column migrations for existing calibration_records table
ALTER TABLE calibration_records ADD COLUMN IF NOT EXISTS patient_id UUID REFERENCES patients(id) ON DELETE SET NULL;

-- 5. Hardware Devices Table (Raspberry Pi 5 / Eye-Tracking Stations)
CREATE TABLE IF NOT EXISTS devices (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT DEFAULT 'online' CHECK (status IN ('online', 'offline', 'calibrating')),
    fps REAL DEFAULT 60.0,
    latency_ms REAL DEFAULT 12.0,
    battery INTEGER DEFAULT 95,
    cpu_usage REAL,
    temperature_c REAL,
    last_heartbeat TIMESTAMPTZ DEFAULT NOW()
);

-- Idempotent column migrations for existing devices table
ALTER TABLE devices ADD COLUMN IF NOT EXISTS battery INTEGER DEFAULT 95;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS cpu_usage REAL;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS temperature_c REAL;

-- Enable Row Level Security (RLS)
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
ALTER TABLE therapy_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE calibration_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;

-- Idempotent Policies (Drops existing policy if present before creating)
DROP POLICY IF EXISTS "Allow authenticated read on profiles" ON profiles;
CREATE POLICY "Allow authenticated read on profiles" ON profiles FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "Allow authenticated full access on profiles" ON profiles;
CREATE POLICY "Allow authenticated full access on profiles" ON profiles FOR ALL TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow authenticated full access on patients" ON patients;
CREATE POLICY "Allow authenticated full access on patients" ON patients FOR ALL TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow authenticated full access on therapy_sessions" ON therapy_sessions;
CREATE POLICY "Allow authenticated full access on therapy_sessions" ON therapy_sessions FOR ALL TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow authenticated full access on calibration_records" ON calibration_records;
CREATE POLICY "Allow authenticated full access on calibration_records" ON calibration_records FOR ALL TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow authenticated full access on devices" ON devices;
CREATE POLICY "Allow authenticated full access on devices" ON devices FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- Performance Indexes for Fast Querying
CREATE INDEX IF NOT EXISTS idx_patients_condition ON patients(condition);
CREATE INDEX IF NOT EXISTS idx_patients_clinical_status ON patients(clinical_status);
CREATE INDEX IF NOT EXISTS idx_patients_stage ON patients(stage);
CREATE INDEX IF NOT EXISTS idx_sessions_patient_id ON therapy_sessions(patient_id);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON therapy_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_profiles_email ON profiles(email);

-- 6. Eye Test Sessions Table (Feature 1)
CREATE TABLE IF NOT EXISTS eye_test_sessions (
    id TEXT PRIMARY KEY,
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    clinician_id TEXT,
    session_status TEXT DEFAULT 'IN_PROGRESS' CHECK (session_status IN ('IN_PROGRESS', 'COMPLETED', 'ABANDONED')),
    active_test_type TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Eye Test Results Table (Feature 1)
CREATE TABLE IF NOT EXISTS eye_test_results (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES eye_test_sessions(id) ON DELETE CASCADE,
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    test_type TEXT NOT NULL CHECK (test_type IN ('FIXATION_STABILITY', 'SMOOTH_PURSUIT', 'SACCADE_RESPONSE', 'GAZE_ACCURACY')),
    duration REAL DEFAULT 10.0,
    score REAL,
    error_value REAL,
    reaction_time REAL,
    valid_sample_count INTEGER,
    tracking_confidence REAL,
    data_quality_status TEXT DEFAULT 'Valid Data',
    status TEXT DEFAULT 'COMPLETED',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. AI Analyses Table (Feature 2)
CREATE TABLE IF NOT EXISTS ai_analyses (
    id TEXT PRIMARY KEY,
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    eye_test_session_id TEXT REFERENCES eye_test_sessions(id) ON DELETE CASCADE,
    requesting_user_id TEXT,
    analysis_type TEXT DEFAULT 'SESSION_COMPREHENSIVE',
    output_json JSONB NOT NULL,
    clinician_review_status TEXT DEFAULT 'pending' CHECK (clinician_review_status IN ('pending', 'reviewed', 'flagged', 'dismissed')),
    clinician_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. Therapy Recommendations Table (Feature 3 - Decision Support Only)
CREATE TABLE IF NOT EXISTS therapy_recommendations (
    id TEXT PRIMARY KEY,
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    eye_test_session_id TEXT REFERENCES eye_test_sessions(id) ON DELETE CASCADE,
    ai_analysis_id TEXT REFERENCES ai_analyses(id) ON DELETE CASCADE,
    recommendation_status TEXT DEFAULT 'pending_review' CHECK (recommendation_status IN ('generated', 'pending_review', 'approved', 'edited', 'rejected', 'archived')),
    exercise_category TEXT NOT NULL CHECK (exercise_category IN (
        'Fixation Exercise',
        'Smooth Pursuit Exercise',
        'Saccade Exercise',
        'Gaze Accuracy Exercise',
        'General Visual Attention Exercise',
        'Repeat Assessment / Calibration Review'
    )),
    reason TEXT NOT NULL,
    supporting_metrics_json JSONB DEFAULT '[]'::jsonb,
    suggested_difficulty TEXT DEFAULT 'beginner' CHECK (suggested_difficulty IN ('beginner', 'moderate', 'advanced', 'not_applicable')),
    suggested_duration_min INTEGER DEFAULT 5,
    suggested_duration_max INTEGER DEFAULT 10,
    priority TEXT DEFAULT 'moderate' CHECK (priority IN ('low', 'moderate', 'high', 'review_required')),
    confidence TEXT DEFAULT 'moderate' CHECK (confidence IN ('low', 'moderate', 'high')),
    data_quality_note TEXT DEFAULT 'Based on available session data.',
    is_simulated_data BOOLEAN DEFAULT FALSE,
    clinician_review_status TEXT DEFAULT 'pending' CHECK (clinician_review_status IN ('pending', 'approved', 'edited', 'rejected')),
    clinician_notes TEXT,
    original_recommendation_json JSONB,
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS on New Tables
ALTER TABLE eye_test_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE eye_test_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE therapy_recommendations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow authenticated full access on eye_test_sessions" ON eye_test_sessions;
CREATE POLICY "Allow authenticated full access on eye_test_sessions" ON eye_test_sessions FOR ALL TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow authenticated full access on eye_test_results" ON eye_test_results;
CREATE POLICY "Allow authenticated full access on eye_test_results" ON eye_test_results FOR ALL TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow authenticated full access on ai_analyses" ON ai_analyses;
CREATE POLICY "Allow authenticated full access on ai_analyses" ON ai_analyses FOR ALL TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow authenticated full access on therapy_recommendations" ON therapy_recommendations;
CREATE POLICY "Allow authenticated full access on therapy_recommendations" ON therapy_recommendations FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_eye_test_sessions_patient ON eye_test_sessions(patient_id);
CREATE INDEX IF NOT EXISTS idx_eye_test_results_session ON eye_test_results(session_id);
CREATE INDEX IF NOT EXISTS idx_ai_analyses_session ON ai_analyses(eye_test_session_id);
CREATE INDEX IF NOT EXISTS idx_therapy_recs_session ON therapy_recommendations(eye_test_session_id);
CREATE INDEX IF NOT EXISTS idx_therapy_recs_patient ON therapy_recommendations(patient_id);

-- 10. Therapy Session Results Table (Feature 5 - Performance Recording)
CREATE TABLE IF NOT EXISTS therapy_session_results (
    id TEXT PRIMARY KEY,
    therapy_session_id TEXT REFERENCES therapy_sessions(id) ON DELETE CASCADE,
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    exercise_type TEXT NOT NULL,
    score REAL DEFAULT 0.0,
    accuracy REAL DEFAULT 0.0,
    error_value REAL,
    reaction_time REAL,
    completion_percentage REAL DEFAULT 0.0,
    valid_sample_count INTEGER DEFAULT 0,
    tracking_confidence REAL DEFAULT 0.9,
    target_loss_events INTEGER DEFAULT 0,
    pause_count INTEGER DEFAULT 0,
    metrics_json JSONB DEFAULT '{}'::jsonb,
    data_quality_status TEXT DEFAULT 'Demo/Simulated Tracking Data',
    is_simulated_data BOOLEAN DEFAULT TRUE,
    clinician_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Idempotent column migrations for therapy_sessions
ALTER TABLE therapy_sessions ADD COLUMN IF NOT EXISTS recommendation_id TEXT;
ALTER TABLE therapy_sessions ADD COLUMN IF NOT EXISTS assigned_by TEXT;
ALTER TABLE therapy_sessions ADD COLUMN IF NOT EXISTS session_status TEXT DEFAULT 'ready';
ALTER TABLE therapy_sessions ADD COLUMN IF NOT EXISTS planned_duration_seconds INTEGER DEFAULT 300;
ALTER TABLE therapy_sessions ADD COLUMN IF NOT EXISTS actual_duration_seconds INTEGER DEFAULT 0;
ALTER TABLE therapy_sessions ADD COLUMN IF NOT EXISTS difficulty TEXT DEFAULT 'beginner';
ALTER TABLE therapy_sessions ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
ALTER TABLE therapy_sessions ADD COLUMN IF NOT EXISTS paused_at TIMESTAMPTZ;
ALTER TABLE therapy_sessions ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
ALTER TABLE therapy_sessions ADD COLUMN IF NOT EXISTS stopped_at TIMESTAMPTZ;
ALTER TABLE therapy_sessions ADD COLUMN IF NOT EXISTS stop_reason TEXT;
ALTER TABLE therapy_sessions ADD COLUMN IF NOT EXISTS data_quality_status TEXT DEFAULT 'Demo/Simulated Tracking Data';
ALTER TABLE therapy_sessions ADD COLUMN IF NOT EXISTS is_simulated_data BOOLEAN DEFAULT TRUE;
ALTER TABLE therapy_sessions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Enable RLS on therapy_session_results
ALTER TABLE therapy_session_results ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow authenticated full access on therapy_session_results" ON therapy_session_results;
CREATE POLICY "Allow authenticated full access on therapy_session_results" ON therapy_session_results FOR ALL TO authenticated USING (true) WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_therapy_session_results_session ON therapy_session_results(therapy_session_id);
CREATE INDEX IF NOT EXISTS idx_therapy_session_results_patient ON therapy_session_results(patient_id);

-- 11. Adaptive Therapy Configs Table
CREATE TABLE IF NOT EXISTS adaptive_therapy_configs (
    id TEXT PRIMARY KEY,
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    therapy_assignment_id TEXT,
    exercise_id TEXT NOT NULL DEFAULT 'horizontal_moving_target',
    enabled BOOLEAN DEFAULT TRUE,
    adaptive_mode TEXT DEFAULT 'controlled_automatic',
    minimum_difficulty INTEGER DEFAULT 1,
    maximum_difficulty INTEGER DEFAULT 5,
    starting_difficulty INTEGER DEFAULT 2,
    current_difficulty INTEGER DEFAULT 2,
    progression_threshold REAL DEFAULT 85.0,
    regression_threshold REAL DEFAULT 65.0,
    step_size INTEGER DEFAULT 1,
    minimum_sessions_before_adaptation INTEGER DEFAULT 2,
    max_daily_difficulty_increase INTEGER DEFAULT 1,
    clinician_approval_required BOOLEAN DEFAULT TRUE,
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE adaptive_therapy_configs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow authenticated full access on adaptive_therapy_configs" ON adaptive_therapy_configs;
CREATE POLICY "Allow authenticated full access on adaptive_therapy_configs" ON adaptive_therapy_configs FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE INDEX IF NOT EXISTS idx_adaptive_therapy_configs_patient ON adaptive_therapy_configs(patient_id);

-- 12. Therapy Adaptation Recommendations Table
CREATE TABLE IF NOT EXISTS therapy_adaptation_recommendations (
    id TEXT PRIMARY KEY,
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    config_id TEXT REFERENCES adaptive_therapy_configs(id) ON DELETE SET NULL,
    therapy_assignment_id TEXT,
    exercise_id TEXT NOT NULL DEFAULT 'horizontal_moving_target',
    source_session_id TEXT,
    current_difficulty INTEGER NOT NULL DEFAULT 2,
    recommended_difficulty INTEGER NOT NULL DEFAULT 3,
    direction TEXT NOT NULL DEFAULT 'progression',
    reason TEXT NOT NULL,
    supporting_metrics JSONB DEFAULT '{}'::jsonb,
    confidence REAL DEFAULT 0.9,
    data_quality_note TEXT,
    is_simulated_data BOOLEAN DEFAULT FALSE,
    approval_status TEXT DEFAULT 'pending_review',
    status TEXT DEFAULT 'pending_review',
    reviewed_by TEXT,
    clinician_note TEXT,
    reviewed_at TIMESTAMPTZ,
    applied_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE therapy_adaptation_recommendations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow authenticated full access on therapy_adaptation_recommendations" ON therapy_adaptation_recommendations;
CREATE POLICY "Allow authenticated full access on therapy_adaptation_recommendations" ON therapy_adaptation_recommendations FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE INDEX IF NOT EXISTS idx_therapy_adaptation_recs_patient ON therapy_adaptation_recommendations(patient_id);

-- 13. Therapy Adaptation Audits Table
CREATE TABLE IF NOT EXISTS therapy_adaptation_audits (
    id TEXT PRIMARY KEY,
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    config_id TEXT,
    exercise_id TEXT,
    action_type TEXT DEFAULT 'difficulty_adjusted',
    previous_difficulty INTEGER NOT NULL,
    new_difficulty INTEGER NOT NULL,
    change_type TEXT,
    trigger TEXT,
    source_recommendation_id TEXT,
    applied_by TEXT,
    clinician_id TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE therapy_adaptation_audits ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow authenticated full access on therapy_adaptation_audits" ON therapy_adaptation_audits;
CREATE POLICY "Allow authenticated full access on therapy_adaptation_audits" ON therapy_adaptation_audits FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE INDEX IF NOT EXISTS idx_therapy_adaptation_audits_patient ON therapy_adaptation_audits(patient_id);

-- 14. Clinician Progress Notes Table
CREATE TABLE IF NOT EXISTS clinician_progress_notes (
    id TEXT PRIMARY KEY,
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    clinician_name TEXT NOT NULL,
    author_name TEXT,
    title TEXT,
    note TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE clinician_progress_notes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow authenticated full access on clinician_progress_notes" ON clinician_progress_notes;
CREATE POLICY "Allow authenticated full access on clinician_progress_notes" ON clinician_progress_notes FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE INDEX IF NOT EXISTS idx_clinician_progress_notes_patient ON clinician_progress_notes(patient_id);

-- 15. In-App Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT DEFAULT 'info',
    category TEXT,
    priority TEXT DEFAULT 'medium',
    related_patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    patient_name TEXT,
    hospital_name TEXT,
    target_route TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow authenticated full access on notifications" ON notifications;
CREATE POLICY "Allow authenticated full access on notifications" ON notifications FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE INDEX IF NOT EXISTS idx_notifications_patient ON notifications(related_patient_id);
