import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.ai import router as ai_router
from app.api.v1.auth import router as auth_router
from app.api.v1.calibration import router as calibration_router
from app.api.v1.devices import router as devices_router
from app.api.v1.patients import router as patients_router
from app.api.v1.reports import router as reports_router
from app.api.v1.therapy import router as therapy_router
from app.api.v1.websocket_gaze import router as ws_router
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("foceye.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting FOCEYE Clinical Backend & Vision Telemetry Engine...")
    logger.info(f"Environment: {settings.ENVIRONMENT} | Port: {settings.PORT}")
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
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API v1 Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(patients_router, prefix="/api/v1")
app.include_router(therapy_router, prefix="/api/v1")
app.include_router(calibration_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(devices_router, prefix="/api/v1")
app.include_router(ws_router)


@app.get("/health", tags=["System Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "FOCEYE Clinical Backend",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }
