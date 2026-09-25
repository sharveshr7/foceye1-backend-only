import sys
import os
import json
import urllib.request
import urllib.error

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.supabase import supabase

BASE_URL = "http://127.0.0.1:8000/api/v1"

def make_req(method, endpoint, payload=None, token=None):
    url = f"{BASE_URL}{endpoint}"
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

print("[1] Clinician Login...")
status, login_res = make_req("POST", "/auth/login", {
    "email": "dr.smith@foceye.clinic",
    "password": "Password123!"
})
assert status == 200, f"Login failed: {login_res}"
token = login_res["access_token"]
print(" -> Logged in successfully!")

print("\n[2] Creating patient via API...")
status, p_data = make_req("POST", "/patients", {
    "name": "PersistenceTest User",
    "age": 32,
    "gender": "Female",
    "condition": "Binocular Vision Dysfunction",
    "hospital_id": "HOS-999",
    "phone": "+1 555-999-1234",
    "email": "persistence@test.clinic",
    "address": "101 Persistence Way",
    "diagnosis": "Binocular Vision Dysfunction - Active Rehabilitation"
}, token=token)
assert status == 201, f"Creation failed: {p_data}"
p_id = p_data["id"]
print(f" -> Created patient: {p_id}, name: {p_data['name']}, phone: {p_data.get('phone')}")

print("\n[3] Updating patient via API...")
status, up_data = make_req("PUT", f"/patients/{p_id}", {
    "condition": "Updated Rehabilitation Status",
    "notes": "Telemetry verified"
}, token=token)
assert status == 200, f"Update failed: {up_data}"
print(f" -> Updated successfully: {up_data['condition']}")

print("\n[4] Creating Eye Test Session for patient in Supabase...")
status, ses_data = make_req("POST", "/eye-tests/sessions", {"patient_id": p_id}, token=token)
assert status == 201, f"Eye test session failed: {ses_data}"
ses_id = ses_data["id"]
print(f" -> Created session: {ses_id}")

print("\n[5] Creating Eye Test Result...")
status, res_data = make_req("POST", "/eye-tests/results", {
    "session_id": ses_id,
    "patient_id": p_id,
    "test_type": "FIXATION_STABILITY",
    "duration": 15.0,
    "score": 95.0,
    "valid_sample_count": 450,
    "tracking_confidence": 0.98,
    "data_quality_status": "Calibrated Optical Data"
}, token=token)
assert status == 201, f"Eye test result failed: {res_data}"
print(f" -> Created result: {res_data['id']}")

print("\n[6] Deleting patient via DELETE /patients/{id}...")
status, del_data = make_req("DELETE", f"/patients/{p_id}", token=token)
assert status == 204, f"Delete failed: {del_data}"
print(" -> Patient deletion API returned HTTP 204 No Content")

print("\n[7] Verifying persistence: patient must remain deleted across reload...")
status, get_data = make_req("GET", f"/patients/{p_id}", token=token)
assert status == 404, f"Patient still returned: {get_data}"
print(" -> Verified: Patient returns 404 Not Found")

# Check Supabase tables directly
sb_pat = supabase.table("patients").select("id").eq("id", p_id).execute()
assert len(sb_pat.data or []) == 0, "Patient still in Supabase!"

sb_ses = supabase.table("eye_test_sessions").select("id").eq("patient_id", p_id).execute()
assert len(sb_ses.data or []) == 0, "Eye test session still in Supabase!"

sb_res = supabase.table("eye_test_results").select("id").eq("patient_id", p_id).execute()
assert len(sb_res.data or []) == 0, "Eye test results still in Supabase!"

print("\n======================================================================")
print("SUCCESS: Full CRUD, cascade deletion, and persistence verified against Supabase!")
print("======================================================================")
