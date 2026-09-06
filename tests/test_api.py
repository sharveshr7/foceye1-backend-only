import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import create_access_token
from app.services.eye_processor import EyeProcessor
from app.services.calibration_engine import CalibrationEngine

client = TestClient(app)

# Default authenticated clinician token for API test suite
test_token = create_access_token({
    "sub": "mock-clinician-1",
    "email": "dr.smith@foceye.clinic",
    "full_name": "Dr. Sarah Smith, OD",
    "role": "clinician",
    "clinic_name": "FOCEYE Ophthalmic Center"
})
client.headers.update({"Authorization": f"Bearer {test_token}"})


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "FOCEYE Clinical Backend"


def test_list_patients():
    # Verify initial list is a valid list
    initial_res = client.get("/api/v1/patients")
    assert initial_res.status_code == 200
    assert isinstance(initial_res.json(), list)

    # Create patient and verify listing
    client.post("/api/v1/patients", json={
        "name": "Listing Test Patient",
        "age": 28,
        "gender": "Female",
        "condition": "Strabismus",
        "icd10": "H50.0",
        "stage": "Active",
        "adherence": 100,
        "visual_acuity_left": "20/20",
        "visual_acuity_right": "20/20",
        "bcea_score": 1.0
    })

    response = client.get("/api/v1/patients")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(p["name"] == "Listing Test Patient" for p in data)


def test_create_and_get_patient():
    new_patient = {
        "name": "Alex Mercer",
        "age": 14,
        "gender": "Male",
        "condition": "Strabismus",
        "icd10": "H50.0",
        "stage": "Active Therapy",
        "adherence": 95,
        "visual_acuity_left": "20/25",
        "visual_acuity_right": "20/20",
        "bcea_score": 1.15
    }
    create_res = client.post("/api/v1/patients", json=new_patient)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["name"] == "Alex Mercer"
    assert "id" in created_data

    # Fetch patient
    p_id = created_data["id"]
    get_res = client.get(f"/api/v1/patients/{p_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Alex Mercer"


def test_therapy_session_logging():
    # First create a patient to get a valid patient UUID
    p_res = client.post("/api/v1/patients", json={
        "name": "Test Session Patient",
        "age": 10,
        "gender": "Female",
        "condition": "Amblyopia",
        "icd10": "H53.00",
        "stage": "Active Therapy",
        "adherence": 100,
        "visual_acuity_left": "20/30",
        "visual_acuity_right": "20/20",
        "bcea_score": 1.2
    })
    patient_id = p_res.json()["id"]

    session_payload = {
        "patient_id": patient_id,
        "exercise_type": "target-tracking",
        "duration_seconds": 300,
        "fixation_score": 92.0,
        "saccadic_score": 88.5,
        "convergence_score": 90.0,
        "gaze_points": [
            {"x": 100.0, "y": 200.0, "timestamp": 1000.0},
            {"x": 101.0, "y": 201.0, "timestamp": 1016.0},
            {"x": 99.5, "y": 199.5, "timestamp": 1032.0},
            {"x": 100.5, "y": 200.5, "timestamp": 1048.0},
            {"x": 100.0, "y": 200.0, "timestamp": 1064.0},
            {"x": 100.2, "y": 200.1, "timestamp": 1080.0}
        ],
        "clinical_notes": "Patient achieved excellent fixation stability"
    }
    res = client.post("/api/v1/therapy/sessions", json=session_payload)
    assert res.status_code == 201
    data = res.json()
    assert "overall_score" in data
    assert data["overall_score"] > 80.0
    assert "bcea_68" in data


def test_device_heartbeat():
    heartbeat_payload = {
        "device_id": "dev-01",
        "fps": 60.0,
        "latency_ms": 11.8,
        "status": "online"
    }
    res = client.post("/api/v1/devices/heartbeat", json=heartbeat_payload)
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_scientific_bcea_calculation():
    gx = [100.0, 101.2, 99.8, 100.5, 100.1, 99.9, 100.3, 100.0]
    gy = [200.0, 199.5, 200.4, 200.1, 199.8, 200.2, 200.0, 200.3]
    result = EyeProcessor.calculate_bcea(gx, gy, p=0.68)
    assert "bcea_deg2" in result
    assert result["bcea_deg2"] >= 0.0
    assert "sigma_x" in result
    assert "sigma_y" in result


def test_calibration_engine():
    targets = [(0, 0), (960, 0), (1920, 0), (0, 540), (960, 540), (1920, 540), (0, 1080), (960, 1080), (1920, 1080)]
    recorded = [(2, 1), (958, 2), (1923, -1), (-1, 541), (961, 539), (1918, 542), (1, 1082), (959, 1078), (1921, 1081)]
    res = CalibrationEngine.solve_calibration(targets, recorded)
    assert res["success"] is True
    assert res["rmse_pixels"] < 10.0
    assert res["accuracy_percentage"] > 90.0


def test_ai_insights_endpoint():
    payload = {
        "condition": "Amblyopia (Lazy Eye)",
        "age": 12,
        "bcea_score": 1.45,
        "fixation_stability": 82.0,
        "saccadic_latency_ms": 230.0,
        "adherence_rate": 90.0
    }
    response = client.post("/api/v1/ai/insights", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "risk_level" in data
    assert "recommended_protocols" in data
    assert len(data["recommended_protocols"]) > 0


def test_pdf_report_endpoint():
    # First create a patient
    p_res = client.post("/api/v1/patients", json={
        "name": "PDF Report Patient",
        "age": 16,
        "gender": "Male",
        "condition": "Convergence Insufficiency",
        "icd10": "H51.11",
        "stage": "Active Therapy",
        "adherence": 90,
        "visual_acuity_left": "20/20",
        "visual_acuity_right": "20/20",
        "bcea_score": 0.95
    })
    patient_id = p_res.json()["id"]

    payload = {
        "patient_id": patient_id,
        "include_ai_insights": True,
        "therapist_signature": "Dr. Sarah Smith, OD"
    }
    response = client.post("/api/v1/reports/pdf", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 1000 # Valid PDF bytes


def test_websocket_gaze_streaming():
    with client.websocket_connect("/ws/gaze/sess-test-100") as ws1:
        with client.websocket_connect("/ws/gaze/sess-test-100") as ws2:
            # Test JSON broadcast from ws1 to ws2
            ws1.send_text('{"gaze_x": 0.5, "gaze_y": 0.5, "pupil_mm": 3.4}')
            received_json = ws2.receive_json()
            assert received_json["gaze_x"] == 0.5
            assert received_json["pupil_mm"] == 3.4

            # Test Binary broadcast from ws2 to ws1
            sample_bytes = b"\x00" * 32
            ws2.send_bytes(sample_bytes)
            received_bytes = ws1.receive_bytes()
            assert len(received_bytes) == 32


def test_unauthenticated_request_rejected():
    # Fresh unauthenticated client without auth headers
    unauth_client = TestClient(app)
    res = unauth_client.get("/api/v1/patients")
    assert res.status_code == 401
    assert "detail" in res.json()

    # Invalid token rejected
    bad_client = TestClient(app)
    bad_client.headers["Authorization"] = "Bearer invalid-expired-or-malformed-token"
    res2 = bad_client.get("/api/v1/patients")
    assert res2.status_code == 401


def test_auth_signup_and_login():
    unauth_client = TestClient(app)

    # 1. Test Signup
    signup_payload = {
        "email": "dr.smith.test@foceye.clinic",
        "password": "Password123!",
        "full_name": "Dr. Sarah Smith",
        "role": "clinician",
        "clinic_name": "FOCEYE Vision Clinic"
    }
    signup_res = unauth_client.post("/api/v1/auth/signup", json=signup_payload)
    assert signup_res.status_code == 200
    signup_data = signup_res.json()
    assert "access_token" in signup_data
    assert signup_data["token_type"] == "bearer"
    assert "password_hash" not in signup_data["user"]

    # Duplicate signup should fail
    dup_res = unauth_client.post("/api/v1/auth/signup", json=signup_payload)
    assert dup_res.status_code == 400

    # 2. Test Login with correct password
    login_payload = {
        "email": "dr.smith.test@foceye.clinic",
        "password": "Password123!"
    }
    login_res = unauth_client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    assert token

    # 3. Test Login with wrong password
    bad_login = unauth_client.post("/api/v1/auth/login", json={
        "email": "dr.smith.test@foceye.clinic",
        "password": "WrongPassword!"
    })
    assert bad_login.status_code == 401

    # 4. Test /auth/me with the issued token
    authed_client = TestClient(app)
    authed_client.headers["Authorization"] = f"Bearer {token}"
    me_res = authed_client.get("/api/v1/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "dr.smith.test@foceye.clinic"


def test_calibration_compute_endpoint():
    payload = {
        "points": [
            {"target_x": 0.0, "target_y": 0.0, "recorded_x": 1.0, "recorded_y": 2.0},
            {"target_x": 960.0, "target_y": 0.0, "recorded_x": 958.0, "recorded_y": 1.0},
            {"target_x": 1920.0, "target_y": 0.0, "recorded_x": 1921.0, "recorded_y": 0.0},
            {"target_x": 0.0, "target_y": 540.0, "recorded_x": 2.0, "recorded_y": 539.0},
            {"target_x": 960.0, "target_y": 540.0, "recorded_x": 960.0, "recorded_y": 541.0},
            {"target_x": 1920.0, "target_y": 540.0, "recorded_x": 1919.0, "recorded_y": 538.0},
            {"target_x": 0.0, "target_y": 1080.0, "recorded_x": 1.0, "recorded_y": 1082.0},
            {"target_x": 960.0, "target_y": 1080.0, "recorded_x": 961.0, "recorded_y": 1079.0},
            {"target_x": 1920.0, "target_y": 1080.0, "recorded_x": 1920.0, "recorded_y": 1081.0}
        ]
    }
    res = client.post("/api/v1/calibration/compute", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["accuracy_percentage"] > 80.0
    assert len(data["polynomial_coefficients"]) == 12


def test_therapy_session_canonical_and_singular_removed():
    # Verify singular endpoint is removed and returns 404
    res_singular_post = client.post("/api/v1/therapy/session", json={
        "patient_id": "test-patient-id",
        "exercise_type": "saccade-jumps",
        "duration_seconds": 120,
        "fixation_score": 90.0,
        "saccadic_score": 92.0,
        "convergence_score": 88.0,
        "clinical_notes": "Saccade latency test"
    })
    assert res_singular_post.status_code == 404

    res_singular_get = client.get("/api/v1/therapy/session")
    assert res_singular_get.status_code == 404

    # Verify canonical plural endpoint works
    res_canonical = client.post("/api/v1/therapy/sessions", json={
        "patient_id": "test-patient-id",
        "exercise_type": "saccade-jumps",
        "duration_seconds": 120,
        "fixation_score": 90.0,
        "saccadic_score": 92.0,
        "convergence_score": 88.0,
        "clinical_notes": "Saccade latency test completed"
    })
    assert res_canonical.status_code == 201
    assert res_canonical.json()["exercise_type"] == "saccade-jumps"


def test_expanded_clinical_endpoints():
    # 1. Devices status
    res_dev = client.get("/api/v1/devices/status")
    assert res_dev.status_code == 200
    assert "status" in res_dev.json()

    # 2. Calibration status
    res_cal = client.get("/api/v1/calibration/status")
    assert res_cal.status_code == 200
    assert "accuracy_percentage" in res_cal.json()

    # 3. Therapy categories & exercises
    res_cat = client.get("/api/v1/therapy/categories")
    assert res_cat.status_code == 200
    assert len(res_cat.json()) >= 4

    res_ex = client.get("/api/v1/therapy/exercises")
    assert res_ex.status_code == 200
    assert len(res_ex.json()) >= 4

    # 4. Auth staff endpoints
    res_staff = client.get("/api/v1/auth/staff")
    assert res_staff.status_code == 200
    assert isinstance(res_staff.json(), list)

    res_add_staff = client.post("/api/v1/auth/staff", json={
        "name": "Dr. Testing Specialist",
        "email": "testing.specialist@foceye.clinic",
        "role": "doctor",
        "department": "Vision Rehabilitation"
    })
    assert res_add_staff.status_code == 200
    assert res_add_staff.json()["email"] == "testing.specialist@foceye.clinic"



