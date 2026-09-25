import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.adaptive_therapy import router as adaptive_therapy_router
from app.api.v1.ai import router as ai_router
from app.api.v1.auth import router as auth_router
from app.api.v1.calibration import router as calibration_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.devices import router as devices_router
from app.api.v1.eye_test_routes import router as eye_test_router, ai_alias_router
from app.api.v1.patients import router as patients_router
from app.api.v1.progress import router as progress_router
from app.api.v1.reports import router as reports_router
from app.api.v1.therapy import router as therapy_router, therapy_sessions_router
from app.api.v1.websocket_gaze import router as ws_router
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("foceye.main")


from app.core.supabase import check_supabase_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting FOCEYE Clinical Backend & Vision Telemetry Engine...")
    logger.info(f"Environment: {settings.ENVIRONMENT} | Port: {settings.PORT}")
    
    # Startup database connection verification
    db_health = check_supabase_connection()
    if db_health.get("connected"):
        logger.info(f"Supabase database connection verified: {db_health.get('mode')} ({db_health.get('latency_ms')}ms roundtrip)")
    else:
        logger.warning(f"Supabase database check failed on startup: {db_health.get('error')}")
        
    yield
    logger.info("Shutting down FOCEYE Backend...")


app = FastAPI(
    title="FOCEYE Clinical & Vision Therapy Backend",
    description="Production-grade Ophthalmic Biomarker, Eye-Tracking Telemetry & Therapy Management API.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_and_timing_headers(request, call_next):
    try:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
    except Exception as exc:
        logger.exception(f"Unhandled server error on path {request.url.path}: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred in the FOCEYE clinical engine.",
                "detail": str(exc) if settings.ENVIRONMENT != "production" else None
            }
        )


# API v1 Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(patients_router, prefix="/api/v1")
app.include_router(therapy_router, prefix="/api/v1")
app.include_router(therapy_sessions_router, prefix="/api/v1")
app.include_router(adaptive_therapy_router, prefix="/api/v1")
app.include_router(progress_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(calibration_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(devices_router, prefix="/api/v1")
app.include_router(eye_test_router, prefix="/api/v1")
app.include_router(ai_alias_router, prefix="/api/v1")
app.include_router(ws_router)


@app.get("/health", tags=["System Health"])
@app.get("/api/v1/health", tags=["System Health"])
async def health_check():
    db_health = check_supabase_connection()
    is_healthy = db_health.get("connected", False)
    
    return {
        "status": "healthy" if is_healthy else "degraded",
        "service": "FOCEYE Clinical Backend",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "database": db_health,
        "ai_engine": {
            "model": settings.GEMINI_MODEL,
            "configured": bool(settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your-"))
        }
    }


@app.get("/health/live", tags=["System Health"])
async def liveness_check():
    """Process-only health check for load balancers and container restarts."""
    return {"status": "alive", "service": "FOCEYE Clinical Backend"}


@app.get("/health/ready", tags=["System Health"])
async def readiness_check():
    """Dependency-aware health check for deployment readiness diagnostics."""
    db_health = check_supabase_connection()
    if not db_health.get("connected"):
        return JSONResponse(status_code=503, content={"status": "not_ready", "database": db_health})
    return {"status": "ready", "database": db_health}


@app.get("/health/db", tags=["System Health"])
async def database_health_check():
    return check_supabase_connection()
