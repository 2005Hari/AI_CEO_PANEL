import os
import re
from typing import List, Union
from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Startup Operating System"
    API_V1_STR: str = "/api/v1"
    
    # BACKEND_CORS_ORIGINS is a JSON-formatted list of origins
    # e.g: '["http://localhost", "http://localhost:3000"]'
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = ["http://localhost:3000"]

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

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
    NVIDIA_MODEL: str = "meta/llama-3.1-8b-instruct"
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
