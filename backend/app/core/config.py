from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Webhook Inspector"
    api_v1_prefix: str = "/api/v1"
    debug: bool = False
    # Public base URL used to build the ingest URL shown to users.
    public_base_url: str = "http://localhost:8000"

    database_url: str = Field(
        default="postgresql+asyncpg://webhook:webhook@db:5432/webhook"
    )
    redis_url: str = "redis://redis:6379/0"

    # Bins / requests
    bin_ttl_days: int = 7
    bin_id_length: int = 10
    max_body_bytes: int = 262_144  # 256 KB
    max_requests_per_bin: int = 500

    # Replay
    replay_timeout_seconds: float = 5.0
    replay_max_response_bytes: int = 65_536

    # Rate limits (Redis; fail-open). "count/window_seconds"
    rate_limit_ingest_per_min: int = 120
    rate_limit_create_bin_per_min: int = 20

    # TTL cleanup loop interval
    cleanup_interval_seconds: int = 3600


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
