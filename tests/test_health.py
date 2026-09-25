from fastapi.testclient import TestClient

from app import main


def test_liveness_does_not_require_external_services():
    client = TestClient(main.app)
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_reports_dependency_failure(monkeypatch):
    monkeypatch.setattr(
        main,
        "check_supabase_connection",
        lambda: {"connected": False, "status": "unhealthy", "mode": "test"},
    )
    client = TestClient(main.app)
    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


def test_readiness_reports_dependency_success(monkeypatch):
    monkeypatch.setattr(
        main,
        "check_supabase_connection",
        lambda: {"connected": True, "status": "healthy", "mode": "test"},
    )
    client = TestClient(main.app)
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
