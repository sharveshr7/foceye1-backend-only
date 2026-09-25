from app.core.config import Settings
import pytest


def test_cors_parser_accepts_json_and_removes_wildcard():
    settings = Settings(CORS_ORIGINS='["https://clinic.example", "*"]')

    assert "https://clinic.example" in settings.get_cors_origins()
    assert "*" not in settings.get_cors_origins()


def test_supabase_key_prefers_configured_service_key(monkeypatch):
    for name in (
        "SUPABASE_SECRET_KEY",
        "SUPABASE_SERVICE_KEY",
        "SUPABASE_PUBLISHABLE_KEY",
        "SUPABASE_ANON_KEY",
        "SUPABASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = Settings(
        _env_file=None,
        SUPABASE_KEY="your-anon-key",
        SUPABASE_SERVICE_ROLE_KEY="service-key",
    )

    assert settings.get_supabase_key() == "service-key"


def test_production_rejects_default_jwt_secret():
    with pytest.raises(ValueError, match="JWT_SECRET"):
        Settings(_env_file=None, ENVIRONMENT="production")


def test_production_cors_excludes_localhost():
    settings = Settings(
        _env_file=None,
        ENVIRONMENT="production",
        JWT_SECRET="x" * 48,
        CORS_ORIGINS=["https://clinic.example", "http://localhost:3000"],
    )

    origins = settings.get_cors_origins()
    assert "https://clinic.example" in origins
    assert "http://localhost:3000" not in origins
