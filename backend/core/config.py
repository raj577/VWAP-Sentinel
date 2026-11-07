"""Backend settings loaded from environment variables and an optional .env file.

Only the backend reads these values. FYERS provider credentials stay in the
worker/ingestion configuration and are never returned by any API.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Immutable-ish runtime configuration for the API process."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "VWAP Sentinel API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    database_url: str = Field(
        default="postgresql+psycopg://avwap:avwap@127.0.0.1:5432/avwap",
        description="SQLAlchemy URL. PostgreSQL is required outside tests.",
    )
    database_echo: bool = False

    redis_url: str = "redis://localhost:6379/0"
    timezone: str = "Asia/Kolkata"

    cors_origins: str = "http://localhost:3000,http://localhost:8501"

    scheduler_interval_minutes: int = 56
    scheduler_enabled: bool = True
    scheduler_lock_key: int = 730_003
    worker_poll_seconds: int = 2
    scheduler_tick_seconds: int = 15
    job_heartbeat_timeout_seconds: int = 900
    scan_stale_warning_hours: int = 24
    market_holidays: str = ""


    # Authentication (Phase 5)
    auth_secret_key: str = "dev-insecure-secret-change-me-please-rotate-32"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    jwt_issuer: str = "vwap-sentinel"
    jwt_audience: str = "vwap-sentinel-clients"
    cookie_secure: bool = False
    auth_dev_expose_tokens: bool = True
    app_base_url: str = "http://localhost:3000"

    email_provider: str = "console"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = "no-reply@vwap-sentinel.local"

    super_admin_email: str = ""
    super_admin_password: str = ""

    auth_rate_limit_per_minute: int = 20
    login_rate_limit_per_minute: int = 10


    # Interim admin gate until Phase 5 introduces JWT roles. Empty disables the
    # admin market-data diagnostics entirely.
    admin_api_key: str = ""
    market_data_timeframe: str = "60"
    candle_upsert_batch_size: int = 500
    ingestion_lock_key: int = 730_001
    scan_lock_key: int = 730_002
    pipeline_lock_key: int = 730_004
    fyers_status_cache_seconds: int = 30

    # Owner-level FYERS OAuth performed from the admin panel. This redirect URI
    # must also be registered in the FYERS API dashboard.
    fyers_backend_redirect_uri: str = "http://localhost:8000/api/v1/fyers/callback"
    frontend_base_url: str = "http://localhost:3000"
    fyers_login_state_ttl_seconds: int = 600

    @field_validator("scheduler_interval_minutes")
    @classmethod
    def _positive_interval(cls, value: int) -> int:
        if value < 1:
            raise ValueError("scheduler_interval_minutes must be >= 1")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    def safe_summary(self) -> dict[str, Any]:
        """Non-secret settings suitable for logs and diagnostics."""

        return {
            "app_name": self.app_name,
            "environment": self.environment,
            "api_v1_prefix": self.api_v1_prefix,
            "timezone": self.timezone,
            "cors_origins": self.cors_origin_list,
            "scheduler_interval_minutes": self.scheduler_interval_minutes,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
