"""Typed settings loaded from .env. No secrets default here — missing values fail fast at boot."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    env: Literal["dev", "staging", "prod"] = "dev"
    log_level: str = "INFO"
    cors_origins: str = ""  # comma-separated; empty in prod is intentional — fail-closed
    template_example: bool = True

    # Database
    database_url: str  # postgresql+asyncpg://...
    app_db_role: str = "authenticated"

    # Supabase / JWT
    supabase_url: AnyHttpUrl
    supabase_anon_key: str
    jwt_aud: str = "authenticated"
    jwt_leeway_seconds: int = 30

    # Rate limiting
    rate_limit_default: str = "60/minute"

    # Observability
    structlog_json: bool = True
    log_request_bodies: bool = False

    @property
    def database_url_sync(self) -> str:
        """Same DSN but sync-driver (psycopg3), for Alembic and pg_dump helpers."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")

    @property
    def jwt_issuer(self) -> str:
        """Supabase JWT `iss` claim — derived, never configured separately."""
        return f"{str(self.supabase_url).rstrip('/')}/auth/v1"

    @property
    def jwks_url(self) -> str:
        return f"{self.jwt_issuer}/.well-known/jwks.json"

    @field_validator("database_url")
    @classmethod
    def _no_service_role(cls, v: str) -> str:
        # Refuse to start if the DATABASE_URL looks like a service-role DSN.
        # Heuristic: Supabase service-role DSNs contain `service_role` in the password
        # segment; in practice the password itself is the tell. We check for common names.
        banned = ("service_role", "postgres:postgres@")
        if any(b in v for b in banned):
            raise ValueError(
                "DATABASE_URL looks like a service-role or superuser DSN. "
                "RLS will silently bypass. Use the `authenticated` role DSN."
            )
        return v

    @field_validator("cors_origins")
    @classmethod
    def _no_wildcard_in_prod(cls, v: str, info) -> str:  # type: ignore[no-untyped-def]
        env = info.data.get("env", "dev")
        if env == "prod" and "*" in v:
            raise ValueError("CORS_ORIGINS cannot contain '*' in prod.")
        return v

    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
