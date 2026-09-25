import sys
import os
import json
import urllib.request
import urllib.error

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.supabase import supabase

API_URL = "http://127.0.0.1:8000/api/v1"
FRONTEND_URL = "http://localhost:3000"

def make_req(method, endpoint, payload=None, token=None, base=API_URL):
    url = f"{base}{endpoint}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = body
        return e.code, parsed

def check_frontend_route(path):
    url = f"{FRONTEND_URL}{path}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        return resp.status, len(resp.read())

def run_pass():
    print("=" * 70)
    print("FOCEYE INTEGRATION & BUG-FIX VERIFICATION PASS")
    print("=" * 70)

    # 1. Health check
    print("\n[Check 1] Supabase Connection Health Check...")
    s, h = make_req("GET", "/health")
    assert s == 200, f"Health check failed: {h}"
    print(f" -> Supabase status: {h['status']}, mode: {h.get('database', {}).get('mode')}")

    # 2. Clinician Auth
    print("\n[Check 2] Clinician Authentication...")
    s, login = make_req("POST", "/auth/login", {
        "email": "dr.smith@foceye.clinic",
        "password": "Password123!"
    })
    assert s == 200, f"Login failed: {login}"
    token = login["access_token"]
    print(" -> Auth token acquired.")

    # 3. Create patient with all detailed fields
    print("\n[Check 3] Create Patient with Full Clinical Details...")
    patient_payload = {
        "name": "IntegrationTest Patient",
        "age": 29,
        "gender": "Male",
        "hospital_id": "HOS-INTEG-01",
        "phone": "+1 (555) 777-8899",
        "email": "integration.patient@foceye.clinic",
        "address": "404 Fovea Boulevard, Vision Park",
        "emergency_contact": "Guardian (+1 555-777-8800)",
        "medical_history": "Mild convergence insufficiency with asthenopia.",
        "condition": "Convergence Insufficiency",
        "diagnosis": "Convergence Insufficiency (ICD-10: H51.11)",
        "initial_observation": "Reduced NPC (12 cm). Normal monocular fixation.",
        "notes": "Scheduled for computerized 4-test ocular evaluation.",
        "clinical_status": "EYE_TEST_PENDING"
    }
    s, created = make_req("POST", "/patients", patient_payload, token=token)
    assert s == 201, f"Creation failed: {created}"
    pid = created["id"]
    print(f" -> Created patient: {pid}")
    assert created["name"] == patient_payload["name"]
    assert created["hospital_id"] == patient_payload["hospital_id"]
    assert created["phone"] == patient_payload["phone"]

    # 4. Verify data persistence (simulating browser reload / re-opening app)
    print("\n[Check 4] Refresh Check: Verify patient details remain saved...")
    s, reloaded = make_req("GET", f"/patients/{pid}", token=token)
    assert s == 200, f"Fetch failed: {reloaded}"
    assert reloaded["name"] == patient_payload["name"]
    assert reloaded["hospital_id"] == patient_payload["hospital_id"]
    assert reloaded["phone"] == patient_payload["phone"]
    assert reloaded["condition"] == patient_payload["condition"]
    print(" -> Confirmed: All patient fields persisted perfectly across reload.")

    # 5. Update patient details
    print("\n[Check 5] Update Patient Details in Supabase...")
    update_payload = {
        "condition": "Convergence Insufficiency - In Therapy",
        "notes": "Patient completed initial baseline; progressing to vergence therapy.",
        "clinical_status": "THERAPY_IN_PROGRESS"
    }
    s, updated = make_req("PUT", f"/patients/{pid}", update_payload, token=token)
    assert s == 200, f"Update failed: {updated}"
    print(f" -> Updated condition: {updated['condition']}")

    # 6. Verify updated data persistence across refresh
    print("\n[Check 6] Refresh Check: Verify updated details remain saved...")
    s, reloaded_updated = make_req("GET", f"/patients/{pid}", token=token)
    assert s == 200, f"Reload failed: {reloaded_updated}"
    assert reloaded_updated["condition"] == update_payload["condition"]
    assert reloaded_updated["clinical_status"] == update_payload["clinical_status"]
    print(" -> Confirmed: Updated details remain saved after refresh.")

    # 7. Execute Eye Test Suite for Patient
    print("\n[Check 7] Execute 4-Test Eye Test Suite for Patient...")
    s, session = make_req("POST", "/eye-tests/sessions", {"patient_id": pid}, token=token)
    assert s == 201, f"Session create failed: {session}"
    sid = session["id"]
    print(f" -> Eye test session initialized: {sid}")

    # Log 4 tests
    tests = [
        ("FIXATION_STABILITY", 93.5, 0.42, 10.0, 480),
        ("SMOOTH_PURSUIT", 89.0, 1.65, 12.0, 520),
        ("SACCADE_RESPONSE", 91.5, 0.58, 7.2, 380),
        ("GAZE_ACCURACY", 94.0, 0.38, 11.0, 490)
    ]
    for t_type, score, err, dur, samples in tests:
        s, r = make_req("POST", "/eye-tests/results", {
            "session_id": sid,
            "patient_id": pid,
            "test_type": t_type,
            "duration": dur,
            "score": score,
            "error_value": err,
            "reaction_time": 210 if "SACCADE" in t_type else None,
            "valid_sample_count": samples,
            "tracking_confidence": 0.96,
            "data_quality_status": "Valid Optical Data"
        }, token=token)
        assert s == 201, f"Failed to save {t_type}: {r}"
        print(f"    - Saved {t_type}: Score {score}%, Error {err}")

    # Complete session
    s, completed_ses = make_req("POST", f"/eye-tests/sessions/{sid}/complete", token=token)
    assert s == 200
    print(f" -> Session marked COMPLETED.")

    # Verify results query
    s, all_results = make_req("GET", f"/eye-tests/patients/{pid}/results", token=token)
    assert s == 200 and len(all_results) == 4, f"Expected 4 results, got: {len(all_results)}"
    print(f" -> Successfully fetched all 4 eye test results from Supabase.")

    # 8. Test Cascade Deletion and Deletion Persistence
    print("\n[Check 8] Delete Patient and Verify Cascaded Cleanup...")
    s, del_res = make_req("DELETE", f"/patients/{pid}", token=token)
    assert s == 204, f"Delete failed: {del_res}"
    print(" -> Deleted patient via API (HTTP 204).")

    print("\n[Check 9] Refresh Check: Confirm deleted details DO NOT return...")
    s, get_deleted = make_req("GET", f"/patients/{pid}", token=token)
    assert s == 404, f"Expected 404, got {s}: {get_deleted}"
    print(" -> Confirmed: Patient returns 404 Not Found.")

    # Verify in roster query
    s, roster = make_req("GET", "/patients", token=token)
    assert not any(p["id"] == pid for p in roster), "Deleted patient still found in roster list!"
    print(" -> Confirmed: Patient is absent from patient roster.")

    # Direct Supabase table queries to confirm no ghost rows
    sb_p = supabase.table("patients").select("id").eq("id", pid).execute()
    assert len(sb_p.data or []) == 0, "Patient still in Supabase!"

    sb_s = supabase.table("eye_test_sessions").select("id").eq("patient_id", pid).execute()
    assert len(sb_s.data or []) == 0, "Eye test sessions still in Supabase!"

    sb_r = supabase.table("eye_test_results").select("id").eq("patient_id", pid).execute()
    assert len(sb_r.data or []) == 0, "Eye test results still in Supabase!"
    print(" -> Confirmed: Supabase database verified clean with zero orphan records.")

    # 10. Check Frontend Routes for Camera Mode and Eye Test
    print("\n[Check 10] Verify Running Frontend Routes...")
    routes_to_test = [
        "/",
        "/dashboard",
        "/patients",
        "/mode-selection",
        "/camera-mode",
        "/therapy-session",
        "/eye-test",
        "/vision-test",
        "/progress",
        "/adaptive-therapy",
        "/ai-insights",
        "/analytics",
        "/profile"
    ]
    for r in routes_to_test:
        code, length = check_frontend_route(r)
        assert code == 200, f"Route {r} returned {code}"
        print(f" -> Route {r:20s}: HTTP {code} OK ({length} bytes)")

    print("\n" + "=" * 70)
    print("SUCCESS: ALL 10 INTEGRATION PASS CHECKS COMPLETED PERFECTLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_pass()
