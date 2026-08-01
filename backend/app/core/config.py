from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import json
import os


class Settings(BaseSettings):
    # App
    environment: str = "development"
    frontend_url: str = "http://localhost:3000"
    backend_cors_origins: str | List[str] = []
    backend_host: str = "0.0.0.0"
    backend_port: int = 8001
    max_room_participants: int = 10

    # Database — defaults to SQLite for zero-config local development.
    # Override with a PostgreSQL URL in production via .env:
    #   DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/cineiq
    database_url: str = ""

    # Upstash Redis
    upstash_redis_url: str = ""
    upstash_redis_token: str = ""

    # Auth
    clerk_secret_key: str = ""
    next_public_clerk_publishable_key: str = ""
    clerk_jwt_audience: str = ""
    clerk_audience: str = ""

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_global: str = "100/minute"
    rate_limit_semantic_search: str = "10/minute"

    # External APIs
    tmdb_api_key: str = ""

    # Gemini LLM
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # Qdrant Vector DB
    qdrant_url: str = ""
    qdrant_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    @property
    def resolved_database_url(self) -> str:
        """Return the database URL, falling back to a local SQLite file."""
        if self.database_url and "postgresql" in self.database_url:
            return self.database_url
        # Default: SQLite stored in the backend directory
        db_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return f"sqlite+aiosqlite:///{os.path.join(db_dir, 'cineiq.db')}"

    @property
    def cors_origins_list(self) -> List[str]:
        origins = [self.frontend_url]
        if self.environment == "development" and "http://localhost:3000" not in origins:
            origins.append("http://localhost:3000")
            
        if isinstance(self.backend_cors_origins, str):
            try:
                parsed = json.loads(self.backend_cors_origins)
                if isinstance(parsed, list):
                    origins.extend(parsed)
            except json.JSONDecodeError:
                origins.extend([
                    origin.strip()
                    for origin in self.backend_cors_origins.split(",")
                    if origin.strip()
                ])
        elif isinstance(self.backend_cors_origins, list):
            origins.extend(self.backend_cors_origins)
            
        return list(set(origins))


settings = Settings()
