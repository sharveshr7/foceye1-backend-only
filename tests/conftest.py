import os
import pytest

# Ensure tests always run against in-memory mock client and never touch the live Supabase project
os.environ["ENVIRONMENT"] = "test"
os.environ["SUPABASE_URL"] = "https://mock-test.supabase.co"
os.environ["SUPABASE_KEY"] = "mock-test-anon-key"
os.environ["SUPABASE_SECRET_KEY"] = "mock-test-secret-key"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "mock-test-service-role-key"

import app.core.supabase as supabase_mod
import app.api.v1.patients as patients_mod
import app.api.v1.therapy as therapy_mod
import app.api.v1.devices as devices_mod
import app.api.v1.reports as reports_mod
import app.api.v1.calibration as calibration_mod
import app.api.v1.auth as auth_mod


@pytest.fixture(autouse=True)
def isolate_supabase_for_tests(monkeypatch):
    """Guarantees every pytest run operates strictly in-memory without polluting live database."""
    isolated_client = supabase_mod.MockSupabaseClient()
    # Reset in-memory test database for clean isolated run
    isolated_client.db = {
        "profiles": [],
        "patients": [],
        "therapy_sessions": [],
        "calibration_records": [],
        "devices": []
    }

    monkeypatch.setattr(supabase_mod, "supabase", isolated_client)
    monkeypatch.setattr(patients_mod, "supabase", isolated_client)
    monkeypatch.setattr(therapy_mod, "supabase", isolated_client)
    monkeypatch.setattr(devices_mod, "supabase", isolated_client)
    monkeypatch.setattr(reports_mod, "supabase", isolated_client)
    monkeypatch.setattr(calibration_mod, "supabase", isolated_client)
    monkeypatch.setattr(auth_mod, "supabase", isolated_client)
    yield
