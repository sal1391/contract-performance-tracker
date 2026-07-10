"""App settings (pydantic-settings). Mirrors the dual local/prod pattern in the legacy
root-level config.py: locally, auth is off and creds come from env; in prod, AUTH0_ENABLED
and real Snowflake/Secrets are used.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"

    # Database
    database_url: str = "postgresql+psycopg://app:app@localhost:5432/contracts"

    # Auth0
    auth0_enabled: bool = False
    auth0_domain: str = ""
    auth0_audience: str = ""
    auth0_algorithms: str = "RS256"
    auth0_claims_namespace: str = "https://example.com/"

    # CORS
    cors_origins: str = "http://localhost:5173"

    # Snowflake
    snowflake_account: str = ""
    snowflake_user: str = ""
    snowflake_password: str = ""
    snowflake_warehouse: str = ""
    snowflake_database: str = "SANDBOX"
    snowflake_schema: str = "ANALYTICS"
    snowflake_role: str = ""

    # Scheduled jobs
    scheduler_enabled: bool = False
    dimension_sync_interval: int = 86_400   # daily
    matcher_interval: int = 10_800          # 3h
    export_interval: int = 10_800           # 3h
    org_sync_interval: int = 86_400   # daily

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def algorithms_list(self) -> list[str]:
        return [a.strip() for a in self.auth0_algorithms.split(",") if a.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
