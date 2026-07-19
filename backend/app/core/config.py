from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import json

class Settings(BaseSettings):
    # App
    environment: str = "development"
    backend_cors_origins: str | List[str] = ["http://localhost:3000", "https://*.vercel.app"]
    backend_host: str = "0.0.0.0"
    backend_port: int = 8001
    max_room_participants: int = 10

    # Upstash Redis
    upstash_redis_url: str = ""
    upstash_redis_token: str = ""

    # Auth
    clerk_secret_key: str = ""
    next_public_clerk_publishable_key: str = ""
    clerk_audience: str = ""

    # External APIs
    tmdb_api_key: str = ""
    
    # Gemini LLM
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        case_sensitive=False,
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        if isinstance(self.backend_cors_origins, str):
            try:
                return json.loads(self.backend_cors_origins)
            except json.JSONDecodeError:
                return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]
        return self.backend_cors_origins

settings = Settings()
