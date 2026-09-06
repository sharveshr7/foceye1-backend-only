"""
FOCEYE Production Database Seeder
Seeds initial clinical patients, hardware tracking devices, calibration benchmarks,
and therapy sessions into Supabase PostgreSQL.
"""
import os
import sys
from datetime import datetime, timedelta
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = (
    os.environ.get("SUPABASE_SECRET_KEY")
    or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    or os.environ.get("SUPABASE_KEY")
    or ""
)

def seed():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_SECRET_KEY (or SUPABASE_SERVICE_ROLE_KEY) must be provided in environment variables.")
        print("Example: SUPABASE_URL=... SUPABASE_SECRET_KEY=... python scripts/seed_supabase.py")
        sys.exit(1)

    print(f"Connecting to Supabase at: {SUPABASE_URL}")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # 1. Seed Production Clinicians & Staff Profiles
    profiles = [
        {
            "id": "user-dr.smith",
            "email": "dr.smith@foceye.clinic",
            "full_name": "Dr. Sarah Smith, OD",
            "role": "clinician",
            "clinic_name": "FOCEYE Ophthalmic Center"
        },
        {
            "id": "user-dr.evans",
            "email": "dr.evans@foceye.clinic",
            "full_name": "Dr. Rachel Evans, MD",
            "role": "clinician",
            "clinic_name": "FOCEYE Vision Rehabilitation Hospital"
        },
        {
            "id": "user-therapist-marcus",
            "email": "marcus.v@foceye.clinic",
            "full_name": "Marcus Vance, COVT",
            "role": "therapist",
            "clinic_name": "FOCEYE Ophthalmic Center"
        }
    ]

    for p in profiles:
        res = supabase.table("profiles").select("id").eq("email", p["email"]).execute()
        if not res.data:
            supabase.table("profiles").insert(p).execute()
            print(f"  [+] Profile seeded: {p['full_name']} ({p['email']})")
        else:
            print(f"  [*] Profile exists: {p['full_name']}")

    # 2. Seed Baseline Clinical Patients
    clinical_patients = [
        {
            "id": "c1a00001-0000-0000-0000-000000000001",
            "name": "Elena Rostova",
            "age": 11,
            "gender": "Female",
            "condition": "Refractive Amblyopia (Left Eye)",
            "icd10": "H53.022",
            "stage": "Active Therapy",
            "adherence": 94,
            "last_session": datetime.now().strftime("%Y-%m-%d"),
            "visual_acuity_left": "20/60",
            "visual_acuity_right": "20/20",
            "bcea_score": 1.45,
        },
        {
            "id": "c1a00002-0000-0000-0000-000000000002",
            "name": "Marcus Vance",
            "age": 28,
            "gender": "Male",
            "condition": "Convergence Insufficiency",
            "icd10": "H51.11",
            "stage": "Active Therapy",
            "adherence": 91,
            "last_session": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            "visual_acuity_left": "20/20",
            "visual_acuity_right": "20/20",
            "bcea_score": 0.88,
        },
        {
            "id": "c1a00003-0000-0000-0000-000000000003",
            "name": "Liam Chen",
            "age": 8,
            "gender": "Male",
            "condition": "Strabismic Amblyopia (Esotropia)",
            "icd10": "H53.011",
            "stage": "Active Therapy",
            "adherence": 88,
            "last_session": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
            "visual_acuity_left": "20/80",
            "visual_acuity_right": "20/25",
            "bcea_score": 2.15,
        },
        {
            "id": "c1a00004-0000-0000-0000-000000000004",
            "name": "Maya Patel",
            "age": 19,
            "gender": "Female",
            "condition": "Oculomotor Saccadic Dysfunction",
            "icd10": "H55.81",
            "stage": "Maintenance",
            "adherence": 96,
            "last_session": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
            "visual_acuity_left": "20/20",
            "visual_acuity_right": "20/20",
            "bcea_score": 0.72,
        }
    ]

    for pat in clinical_patients:
        res = supabase.table("patients").select("id").eq("name", pat["name"]).execute()
        if not res.data:
            supabase.table("patients").insert(pat).execute()
            print(f"  [+] Patient seeded: {pat['name']} ({pat['condition']})")
        else:
            print(f"  [*] Patient exists: {pat['name']}")

    # 3. Seed Production Hardware Eye-Tracking Devices
    devices = [
        {
            "id": "FOC-PI5-001",
            "name": "FOCEYE Pi-Tracker v2 (RPi 5 + Sony IMX500)",
            "status": "online",
            "fps": 60.0,
            "latency_ms": 11.4
        },
        {
            "id": "FOC-CAM-002",
            "name": "FOCEYE Dual-IR Ophthalmic Gaze Station",
            "status": "online",
            "fps": 120.0,
            "latency_ms": 8.2
        }
    ]

    for d in devices:
        res = supabase.table("devices").select("id").eq("id", d["id"]).execute()
        if not res.data:
            supabase.table("devices").insert(d).execute()
            print(f"  [+] Device seeded: {d['name']} ({d['id']})")
        else:
            supabase.table("devices").update(d).eq("id", d["id"]).execute()
            print(f"  [*] Device updated: {d['name']}")

    # 4. Seed Clinical Therapy Sessions
    elena = supabase.table("patients").select("id").eq("name", "Elena Rostova").execute()
    if elena.data:
        p_id = elena.data[0]["id"]
        sess_check = supabase.table("therapy_sessions").select("id").eq("patient_id", p_id).execute()
        if not sess_check.data:
            sessions = [
                {
                    "patient_id": p_id,
                    "exercise_type": "saccade-trainer",
                    "duration_seconds": 600,
                    "fixation_score": 89.2,
                    "saccadic_score": 92.5,
                    "convergence_score": 85.0,
                    "overall_score": 89.1,
                    "bcea_68": 1.15,
                    "bcea_95": 2.30,
                    "clinical_notes": "Significant gain in saccadic velocity. Suppression scotoma reducing."
                },
                {
                    "patient_id": p_id,
                    "exercise_type": "pursuit-tracker",
                    "duration_seconds": 450,
                    "fixation_score": 86.0,
                    "saccadic_score": 88.0,
                    "convergence_score": 82.5,
                    "overall_score": 85.8,
                    "bcea_68": 1.25,
                    "bcea_95": 2.50,
                    "clinical_notes": "Smooth pursuit gain improved from 0.65 to 0.81."
                }
            ]
            for s in sessions:
                supabase.table("therapy_sessions").insert(s).execute()
                print(f"  [+] Therapy session seeded for patient {p_id}")

    # 5. Seed Calibration Benchmark Records
    calib_check = supabase.table("calibration_records").select("id").execute()
    if not calib_check.data:
        calibs = [
            {
                "rmse_pixels": 7.4,
                "accuracy_percentage": 97.2,
                "coefficients": [1.01, 0.02, -1.8, 0.98, -0.01, 1.2],
                "points_count": 9
            },
            {
                "rmse_pixels": 8.1,
                "accuracy_percentage": 96.5,
                "coefficients": [1.03, 0.01, -2.1, 0.99, -0.02, 1.5],
                "points_count": 9
            }
        ]
        for c in calibs:
            supabase.table("calibration_records").insert(c).execute()
            print(f"  [+] Calibration record seeded with {c['accuracy_percentage']}% accuracy")

    print("Supabase Production Seeding Complete!")

if __name__ == "__main__":
    seed()
