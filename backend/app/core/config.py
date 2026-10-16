import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "QueryPilot - AI Data Analyst Workspace"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite:///./querypilot.db"
    SUPABASE_DB_URL: str = ""
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 300
    DB_SSL_REQUIRE: bool = False

    @property
    def effective_database_url(self) -> str:
        if self.SUPABASE_DB_URL and self.SUPABASE_DB_URL.strip():
            return self.SUPABASE_DB_URL.strip()
        return self.DATABASE_URL.strip()

    # Security
    SECRET_KEY: str = "dev-secret-key-querypilot-production-standard-at-least-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # File storage
    STORAGE_DIR: str = "./storage"
    MAX_UPLOAD_SIZE_MB: int = 25
    STORAGE_BACKEND: str = "local"  # 'local' or 'supabase'
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "querypilot-data"

    # AI Configuration
    AI_PROVIDER: str = "heuristic"  # 'heuristic', 'openai', 'gemini', 'anthropic', 'ollama'
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_BASE_URL: str = ""

    # CORS - allow string or list
    ALLOWED_ORIGINS: Union[str, List[str]] = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000"

    @property
    def cors_origins(self) -> List[str]:
        if isinstance(self.ALLOWED_ORIGINS, list):
            return self.ALLOWED_ORIGINS
        if isinstance(self.ALLOWED_ORIGINS, str):
            # check if JSON list
            if self.ALLOWED_ORIGINS.startswith("[") and self.ALLOWED_ORIGINS.endswith("]"):
                import json
                try:
                    return json.loads(self.ALLOWED_ORIGINS)
                except Exception:
                    pass
            return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]
        return ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

# Ensure storage directories exist
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_DIR, "uploads"), exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_DIR, "reports"), exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_DIR, "cache"), exist_ok=True)
