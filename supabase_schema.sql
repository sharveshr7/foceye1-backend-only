-- ==========================================================
-- FOCEYE Production PostgreSQL Schema for Supabase
-- Medical EHR, Eye-Tracking Telemetry & Therapy Management
-- Idempotent script: can be run safely multiple times
-- ==========================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Profiles Table (Clinicians, Optometrists, Therapists)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'clinician' CHECK (role IN ('clinician', 'therapist', 'admin', 'patient')),
    clinic_name TEXT DEFAULT 'FOCEYE Ophthalmic Center',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Patients Table (EMR Records)
CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    age INTEGER NOT NULL CHECK (age >= 0 AND age <= 120),
    gender TEXT NOT NULL CHECK (gender IN ('Male', 'Female', 'Other')),
    condition TEXT NOT NULL,
    icd10 TEXT DEFAULT 'H53.00',
    stage TEXT DEFAULT 'Active Therapy',
    adherence INTEGER DEFAULT 100 CHECK (adherence >= 0 AND adherence <= 100),
    last_session DATE DEFAULT CURRENT_DATE,
    visual_acuity_left TEXT DEFAULT '20/20',
    visual_acuity_right TEXT DEFAULT '20/20',
    bcea_score REAL DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Therapy Sessions Table
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
    clinical_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Calibration Records Table
CREATE TABLE IF NOT EXISTS calibration_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rmse_pixels REAL NOT NULL,
    accuracy_percentage REAL NOT NULL,
    coefficients REAL[] NOT NULL,
    points_count INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Hardware Devices Table
CREATE TABLE IF NOT EXISTS devices (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT DEFAULT 'online' CHECK (status IN ('online', 'offline', 'calibrating')),
    fps REAL DEFAULT 60.0,
    latency_ms REAL DEFAULT 12.0,
    last_heartbeat TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security (RLS)
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
ALTER TABLE therapy_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE calibration_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;

-- Idempotent Policies (Drops existing policy if present before creating)
DROP POLICY IF EXISTS "Allow authenticated read on profiles" ON profiles;
CREATE POLICY "Allow authenticated read on profiles" ON profiles FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow authenticated full access on patients" ON patients;
CREATE POLICY "Allow authenticated full access on patients" ON patients FOR ALL USING (true);

DROP POLICY IF EXISTS "Allow authenticated full access on therapy_sessions" ON therapy_sessions;
CREATE POLICY "Allow authenticated full access on therapy_sessions" ON therapy_sessions FOR ALL USING (true);

DROP POLICY IF EXISTS "Allow authenticated full access on calibration_records" ON calibration_records;
CREATE POLICY "Allow authenticated full access on calibration_records" ON calibration_records FOR ALL USING (true);

DROP POLICY IF EXISTS "Allow authenticated full access on devices" ON devices;
CREATE POLICY "Allow authenticated full access on devices" ON devices FOR ALL USING (true);

-- Indexes for Fast Querying
CREATE INDEX IF NOT EXISTS idx_patients_condition ON patients(condition);
CREATE INDEX IF NOT EXISTS idx_sessions_patient_id ON therapy_sessions(patient_id);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON therapy_sessions(created_at);
