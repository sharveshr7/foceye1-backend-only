import json
import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = (
        os.getenv("ENVIRONMENT")
        or (
            "production"
            if (
                os.getenv("RENDER")
                or os.getenv("RENDER_SERVICE_ID")
                or os.getenv("RENDER_EXTERNAL_URL")
                or os.getenv("PORT") == "10000"
            )
            else "development"
        )
    )
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # Frontend Deployment URL (e.g. https://your-frontend.vercel.app)
    FRONTEND_URL: str = ""
    
    # CORS Production & Development Origins
    CORS_ORIGINS: List[str] = [
        "https://foceye.vercel.app",
        "https://foceye-frontend.vercel.app",
        "https://foceye1-backend-only.onrender.com",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000"
    ]
    
    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        origins: List[str] = []
        if isinstance(v, str):
            val = v.strip()
            if val.startswith("[") and val.endswith("]"):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, list):
                        origins = [str(item).strip() for item in parsed if item]
                except Exception:
                    origins = [i.strip().strip("'\"") for i in val.strip("[]").split(",") if i.strip()]
            else:
                origins = [i.strip() for i in val.split(",") if i.strip()]
        elif isinstance(v, list):
            origins = [str(i).strip() for i in v if i]

        # Filter out wildcard "*" if specific domains are present to avoid CORS credential rejection
        filtered = [o for o in origins if o and o != "*"]
        return filtered if filtered else origins

    def get_cors_origins(self) -> List[str]:
        origins = list(self.CORS_ORIGINS)
        if self.FRONTEND_URL and self.FRONTEND_URL.strip():
            clean_frontend = self.FRONTEND_URL.strip().rstrip("/")
            if clean_frontend not in origins:
                origins.append(clean_frontend)
        # Guarantee default production Vercel apps are always allowed
        default_apps = [
            "https://foceye.vercel.app",
            "https://foceye-frontend.vercel.app",
            "https://foceye1-backend-only.onrender.com",
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000"
        ]
        for app in default_apps:
            if app not in origins:
                origins.append(app)
        return origins

    # Supabase Configuration - Set via environment variables in production / .env
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_PUBLISHABLE_KEY: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_SECRET_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    def get_supabase_key(self) -> str:
        candidates = [
            self.SUPABASE_SECRET_KEY,
            self.SUPABASE_SERVICE_ROLE_KEY,
            self.SUPABASE_SERVICE_KEY,
            self.SUPABASE_PUBLISHABLE_KEY,
            self.SUPABASE_KEY,
            self.SUPABASE_ANON_KEY
        ]
        for k in candidates:
            if k and "mock" not in k and not k.startswith("your-"):
                return k
        return ""
    
    # AI (Gemini)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    
    # Auth & Security
    JWT_SECRET: str = "foceye-clinical-jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # Eye Tracking Calibration
    CALIBRATION_GRID_POINTS: int = 9
    SAMPLING_RATE_HZ: int = 60
    
    model_config = SettingsConfigDict(
        env_file=(
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), ".env"),
            ".env"
        ),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )


settings = Settings()
