import json
import urllib.request
import urllib.error
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://127.0.0.1:8000/api/v1"

client = None

def get_client():
    global client
    if client is None:
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
    return client

def make_req(method, endpoint, payload=None, token=None):
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = body
        return e.code, parsed
    except urllib.error.URLError:
        # Fallback to TestClient for in-process verification
        c = get_client()
        h = {}
        if token:
            h["Authorization"] = f"Bearer {token}"
        full_path = f"/api/v1{endpoint}"
        if method == "GET":
            r = c.get(full_path, headers=h)
        elif method == "POST":
            r = c.post(full_path, json=payload, headers=h)
        elif method == "PUT":
            r = c.put(full_path, json=payload, headers=h)
        elif method == "PATCH":
            r = c.patch(full_path, json=payload, headers=h)
        elif method == "DELETE":
            r = c.delete(full_path, headers=h)
        else:
            raise ValueError(f"Unsupported method {method}")
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text

def run_e2e_flow():
    print("=" * 70)
    print("FOCEYE E2E CLINICAL WORKFLOW VERIFICATION TEST")
    print("=" * 70)

    # 1. Clinician Authentication
    print("\n[Step 1] Clinician Authentication...")
    status, res = make_req("POST", "/auth/login", {
        "email": "dr.smith@foceye.clinic",
        "password": "Password123!"
    })
    assert status == 200, f"Login failed: {res}"
    token = res["access_token"]
    user = res.get("user", {})
    print(f" -> Logged in as: {user.get('full_name')} ({user.get('role')})")
    assert token, "Token missing from login response"

    # 2. Clinician Dashboard Operational Summary
    print("\n[Step 2] Clinician Dashboard Operational Summary...")
    status, summary = make_req("GET", "/dashboard/summary", token=token)
    assert status == 200, f"Failed summary: {summary}"
    print(f" -> Total Patients: {summary.get('total_patients')}")
    print(f" -> Active Therapy Plans: {summary.get('active_therapy_plans')}")
    print(f" -> Pending Eye Tests: {summary.get('pending_eye_test_reviews')}")
    print(f" -> Pending Recommendations: {summary.get('pending_therapy_recommendations')}")
    print(f" -> Attention Flags: {summary.get('patients_requiring_attention')}")

    # 3. Pending Clinical Actions Triage
    print("\n[Step 3] Pending Clinical Actions...")
    status, actions_data = make_req("GET", "/dashboard/pending-actions", token=token)
    assert status == 200, f"Failed pending actions: {actions_data}"
    actions = actions_data.get("items", [])
    print(f" -> Retrieved {len(actions)} pending clinical actions")
    for a in actions[:3]:
        print(f"    - [{a.get('priority').upper()}] {a.get('title')} (Patient: {a.get('patient_name')})")

    # 4. Patient Roster
    print("\n[Step 4] Patient Roster Overview...")
    status, roster = make_req("GET", "/dashboard/patient-overview?page=1&page_size=5", token=token)
    assert status == 200, f"Failed roster: {roster}"
    patient_items = roster.get("items", [])
    print(f" -> Total patients in roster: {roster.get('total')}")
    assert len(patient_items) > 0, "Roster is empty!"
    target_patient = patient_items[0]
    patient_id = target_patient["id"]
    print(f" -> Selected Patient: {target_patient.get('name')} (ID: {patient_id})")
    print(f"    Therapy Status: {target_patient.get('therapy_status')}, Review Status: {target_patient.get('latest_review_status')}")

    # 5. Initialize Objective Eye Test Session
    print(f"\n[Step 5] Initialize Objective Eye Test Session for {patient_id}...")
    status, session = make_req("POST", "/eye-tests/sessions", {
        "patient_id": patient_id,
        "clinician_id": user.get("id", "dr-smith-01")
    }, token=token)
    assert status in (200, 201), f"Failed to create session: {session}"
    session_id = session["id"]
    print(f" -> Eye Test Session created: {session_id}")

    # 6. Record 4 Precision Eye Tests
    print("\n[Step 6] Recording 4 Precision Eye Tests...")
    tests_to_run = [
        ("FIXATION_STABILITY", 92.5, 0.45, None, 600, 0.96, "Foveal fixation held with 0.45 deg BCEA"),
        ("SMOOTH_PURSUIT", 88.0, 1.8, 210, 580, 0.94, "Sinusoidal horizontal tracking with 0.82 gain"),
        ("SACCADE_RESPONSE", 91.0, 0.6, 185, 590, 0.95, "Prosaccadic latency 185ms, peak velocity 395 deg/s"),
        ("GAZE_ACCURACY", 94.0, 0.35, 160, 600, 0.98, "9-point grid target accuracy within 0.35 deg")
    ]
    for t_type, score, err_val, rt, valid_cnt, conf, notes in tests_to_run:
        status, t_res = make_req("POST", "/eye-tests/results", {
            "session_id": session_id,
            "patient_id": patient_id,
            "test_type": t_type,
            "status": "COMPLETED",
            "duration": 10.0,
            "score": score,
            "error_value": err_val,
            "reaction_time": rt,
            "valid_sample_count": valid_cnt,
            "tracking_confidence": conf,
            "data_quality_status": "Valid Data",
            "notes": notes
        }, token=token)
        assert status in (200, 201), f"Failed test {t_type}: {t_res}"
        print(f" -> Saved {t_type}: Score {score}%, Error {err_val}, Conf {conf}")

    # Finalize Eye Test Session
    status, fin = make_req("POST", f"/eye-tests/sessions/{session_id}/complete", token=token)
    assert status == 200, f"Failed to finalize session: {fin}"
    print(f" -> Eye Test Session {session_id} marked as COMPLETED")

    # 7. AI Analysis of Eye Test
    print(f"\n[Step 7] Running AI-Assisted Eye Test Analysis for session {session_id}...")
    status, ai_analysis = make_req("POST", f"/eye-tests/sessions/{session_id}/analyze", token=token)
    assert status in (200, 201), f"Failed AI analysis: {ai_analysis}"
    analysis_id = ai_analysis["id"]
    print(f" -> AI Analysis generated: ID {analysis_id}")
    print(f"    Confidence: {ai_analysis.get('confidence_score')}")
    print(f"    Observations: {ai_analysis.get('ai_observations')[:80]}...")

    # Clinician Reviews AI Analysis
    status, rev_res = make_req("PATCH", f"/eye-tests/ai-analyses/{analysis_id}/review", {
        "status": "reviewed",
        "clinician_notes": "Verified objective telemetry. BCEA and saccadic latencies consistent with clinical assessment."
    }, token=token)
    assert status == 200, f"Failed clinician review: {rev_res}"
    print(f" -> Clinician verified AI analysis (Status: {rev_res.get('clinician_review_status')})")

    # 8. AI Therapy Recommendation & Clinician Approval
    print(f"\n[Step 8] Generating AI Therapy Recommendation for session {session_id}...")
    status, rec = make_req("POST", f"/eye-tests/sessions/{session_id}/recommend-therapy", token=token)
    assert status in (200, 201), f"Failed recommendation: {rec}"
    rec_id = rec["id"]
    print(f" -> Recommendation generated: ID {rec_id}")
    print(f"    Exercise: {rec.get('primary_exercise_category')}")
    print(f"    Difficulty: {rec.get('recommended_difficulty_level')}, Duration: {rec.get('recommended_duration_minutes')} min")

    # Clinician Approves Recommendation
    status, appr_res = make_req("POST", f"/therapy-recommendations/{rec_id}/review", {
        "action": "approved",
        "notes": "Protocol approved for 5-minute visual pursuit and fixation rehabilitation."
    }, token=token)
    assert status == 200, f"Failed recommendation approval: {appr_res}"
    print(f" -> Clinician Approved Recommendation (Status: {appr_res.get('clinician_review_status')})")

    # 9. Execute VR Therapy Session
    print("\n[Step 9] Launching Prescribed VR Therapy Session...")
    status, th_session = make_req("POST", "/therapy-sessions", {
        "patient_id": patient_id,
        "recommendation_id": rec_id,
        "exercise_type": rec.get("primary_exercise_category", "smooth_pursuit"),
        "planned_duration_seconds": 300,
        "difficulty": rec.get("recommended_difficulty_level", "medium"),
        "is_simulated_data": False
    }, token=token)
    assert status in (200, 201), f"Failed to create therapy session: {th_session}"
    th_session_id = th_session["id"]
    print(f" -> Therapy Session created: {th_session_id}")

    # Start and Complete Session
    make_req("POST", f"/therapy-sessions/{th_session_id}/start", token=token)
    status, comp_th = make_req("POST", f"/therapy-sessions/{th_session_id}/complete", {
        "actual_duration_seconds": 300
    }, token=token)
    assert status == 200, f"Failed to complete therapy session: {comp_th}"

    # Record Session Telemetry Results
    status, th_result = make_req("POST", f"/therapy-sessions/{th_session_id}/results", {
        "score": 93.4,
        "accuracy_score": 93.4,
        "reaction_time_ms": 215.0,
        "valid_sample_count": 1800,
        "tracking_confidence": 0.96,
        "data_quality_status": "Valid Data",
        "clinician_notes": "Patient sustained high foveal engagement throughout 5-minute pursuit protocol."
    }, token=token)
    assert status in (200, 201), f"Failed to record therapy session results: {th_result}"
    print(f" -> Therapy Session {th_session_id} telemetry recorded: Accuracy 93.4%, Confidence 0.96")

    # 10. Adaptive Difficulty Engine Evaluation
    print("\n[Step 10] Evaluating Adaptive Difficulty Engine...")
    status, eval_res = make_req("POST", f"/patients/{patient_id}/evaluate-adaptation", token=token)
    assert status == 200, f"Failed adaptive evaluation: {eval_res}"
    print(f" -> Adaptation Evaluated: Should Adapt = {eval_res.get('should_adapt')}")
    print(f"    Action: {eval_res.get('recommended_action')}")
    print(f"    Current Level: {eval_res.get('current_difficulty')}, Proposed: {eval_res.get('proposed_difficulty')}")
    print(f"    Clinical Rationale: {eval_res.get('clinical_rationale')}")

    # 11. Longitudinal Progress Overview
    print("\n[Step 11] Verifying Longitudinal Progress Overview...")
    status, progress = make_req("GET", f"/patients/{patient_id}/progress/overview", token=token)
    assert status == 200, f"Failed progress overview: {progress}"
    print(f" -> Total Eye Tests: {progress.get('total_eye_tests')}")
    print(f" -> Total Therapy Sessions: {progress.get('total_therapy_sessions')}")
    print(f" -> Baseline Comparisons: {len(progress.get('baseline_comparisons', []))}")
    for comp in progress.get("baseline_comparisons", [])[:2]:
        print(f"    - {comp.get('metric_name')}: Baseline {comp.get('baseline_value')} -> Current {comp.get('current_value')} ({comp.get('trend_direction')})")

    # 12. Notification Center Check
    print("\n[Step 12] Notification Center Verification...")
    status, notifs = make_req("GET", "/dashboard/notifications", token=token)
    assert status == 200, f"Failed notifications: {notifs}"
    items = notifs.get("items", [])
    print(f" -> Total notifications: {len(items)}, Unread: {notifs.get('unread_count')}")

    print("\n" + "=" * 70)
    print("SUCCESS: ALL 12 CLINICAL PIPELINE STAGES VERIFIED!")
    print("=" * 70)

if __name__ == "__main__":
    run_e2e_flow()
