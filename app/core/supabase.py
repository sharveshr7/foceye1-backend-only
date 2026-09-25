"""Strict Supabase client setup for the FOCEYE API.

The API must never report fake in-memory data as persisted clinical data. When
server credentials are missing or invalid, queries fail clearly and readiness
reports the dependency as unavailable.
"""

import logging
import time
from typing import Any, Dict

from app.core.config import settings

logger = logging.getLogger("foceye.supabase")


class SupabaseUnavailableError(RuntimeError):
    """Raised when a database operation cannot reach the configured project."""


class _UnavailableQuery:
    def __init__(self, reason: str):
        self.reason = reason

    def __getattr__(self, _name: str):
        # Preserve the fluent PostgREST query shape; fail only when executed.
        def chain(*_args, **_kwargs):
            return self
        return chain

    def execute(self):
        raise SupabaseUnavailableError(self.reason)


class _UnavailableSupabaseClient:
    def __init__(self, reason: str):
        self.reason = reason

    def table(self, _table_name: str):
        return _UnavailableQuery(self.reason)


def _get_server_key() -> str:
    """Return a server-side key; public browser keys are not enough for this API."""
    for key in (
        settings.SUPABASE_SECRET_KEY,
        settings.SUPABASE_SERVICE_ROLE_KEY,
        settings.SUPABASE_SERVICE_KEY,
    ):
        if key and "mock" not in key.lower() and not key.lower().startswith("your-"):
            return key
    return ""


def get_supabase_client():
    url = (settings.SUPABASE_URL or "").strip()
    key = _get_server_key()
    if not url or not key or "mock" in url.lower():
        reason = (
            "Supabase is unavailable. Configure SUPABASE_URL and a server-side "
            "SUPABASE_SERVICE_ROLE_KEY or SUPABASE_SECRET_KEY in the backend environment."
        )
        logger.error(reason)
        return _UnavailableSupabaseClient(reason)

    try:
        from supabase import ClientOptions, create_client

        options = ClientOptions(
            postgrest_client_timeout=60.0,
            storage_client_timeout=30.0,
            auto_refresh_token=False,
            persist_session=False,
            headers={"X-Client-Info": "foceye-clinical-backend/1.0.0"},
        )
        return create_client(url, key, options=options)
    except Exception as exc:
        # Do not log credentials or return a fake client after initialization fails.
        logger.error("Could not initialize Supabase client (%s).", type(exc).__name__)
        reason = "Supabase client initialization failed. Check the backend URL and server key."
        return _UnavailableSupabaseClient(reason)


supabase = get_supabase_client()


def execute_with_retry(query_builder, max_retries: int = 2, delay_seconds: float = 0.3):
    """Retry only transient Supabase gateway and timeout errors."""
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return query_builder.execute()
        except SupabaseUnavailableError:
            raise
        except Exception as exc:
            last_exc = exc
            error_text = str(exc)
            transient = any(
                marker in error_text
                for marker in ("504", "502", "503", "Gateway Timeout", "timed out", "Timeout")
            )
            if transient and attempt < max_retries:
                logger.warning(
                    "Transient Supabase error (attempt %s/%s); retrying.",
                    attempt + 1,
                    max_retries + 1,
                )
                time.sleep(delay_seconds * (attempt + 1))
                continue
            raise
    raise last_exc


def check_supabase_connection() -> Dict[str, Any]:
    """Check the configured Supabase project without returning patient data."""
    start = time.perf_counter()
    if isinstance(supabase, _UnavailableSupabaseClient):
        return {
            "status": "unhealthy",
            "connected": False,
            "mode": "unavailable",
            "project_url": None,
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            "error": supabase.reason,
        }

    try:
        supabase.table("patients").select("id").limit(1).execute()
        return {
            "status": "healthy",
            "connected": True,
            "mode": "live_cloud",
            "project_url": settings.SUPABASE_URL,
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            "error": None,
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.error("Supabase connectivity check failed after %sms (%s).", latency_ms, type(exc).__name__)
        return {
            "status": "unhealthy",
            "connected": False,
            "mode": "live_cloud",
            "project_url": settings.SUPABASE_URL,
            "latency_ms": latency_ms,
            "error": "Supabase query failed. Check the server key, table access, and project availability.",
        }
