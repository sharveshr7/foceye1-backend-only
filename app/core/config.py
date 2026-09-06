import os
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = (
        os.getenv("ENVIRONMENT")
        or ("production" if os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID") else "development")
    )
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # CORS Production Origins
    CORS_ORIGINS: List[str] = [
        "*",
        "https://foceye.vercel.app",
        "https://foceye-frontend.vercel.app",
        "https://foceye1-backend-only.onrender.com"
    ]
    
    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.strip() == "*":
                return ["*"]
            if not v.startswith("["):
                return [i.strip() for i in v.split(",") if i.strip()]
        return v
    
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
    GEMINI_MODEL: str = "gemini-1.5-flash"
    
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
