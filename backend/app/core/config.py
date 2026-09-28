import os
import re
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Startup Operating System"
    API_V1_STR: str = "/api/v1"

    # A comma-separated list of origins, e.g: "http://localhost:3000,https://your-app.vercel.app"
    # Kept as a plain string (not List[AnyHttpUrl]): pydantic-settings 2.2.1 tries to
    # JSON-decode any env var bound to a list-typed field before any validator runs,
    # which raises SettingsError for a plain comma/URL string and crashes the app at
    # import time. Parsing it ourselves in cors_origins sidesteps that entirely.
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip().rstrip("/") for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]

    # Auth (Clerk)
    CLERK_ISSUER: str | None = None
    CLERK_JWKS_URL: str | None = None
    CLERK_AUDIENCE: str | None = None
    AUTH_REQUIRED: bool = True
    DEV_MOCK_USER_ENABLED: bool = False

    # Database
    USE_SQLITE: bool = False
    # Single connection string as provided by managed Postgres hosts (e.g. Render).
    # When set, this takes precedence over the discrete POSTGRES_* fields below.
    DATABASE_URL: str | None = None
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "ai_ceo_panel"
    POSTGRES_PORT: str = "5432"

    @staticmethod
    def _with_driver(url: str, driver: str) -> str:
        return re.sub(r"^postgres(?:ql)?://", f"postgresql+{driver}://", url, count=1)

    @property
    def sync_database_uri(self) -> str:
        if self.USE_SQLITE:
            return "sqlite:///ai_ceo_panel.db"
        if self.DATABASE_URL:
            return self._with_driver(self.DATABASE_URL, "psycopg")
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def async_database_uri(self) -> str:
        if self.USE_SQLITE:
            return "sqlite+aiosqlite:///ai_ceo_panel.db"
        if self.DATABASE_URL:
            return self._with_driver(self.DATABASE_URL, "asyncpg")
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # LLM
    GEMINI_API_KEY: str | None = None
    NVIDIA_API_KEY: str | None = None
    NVIDIA_MODEL: str = "nvidia/nemotron-3-super-120b-a12b"
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
