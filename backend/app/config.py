from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Neon connection strings: pooled for the API's request-scoped sessions,
    # direct/unpooled for the worker's long-lived process and for Alembic.
    database_url: str = "postgresql+asyncpg://flydaro:flydaro@localhost:5432/flydaro"
    database_url_direct: str = "postgresql+asyncpg://flydaro:flydaro@localhost:5432/flydaro"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30

    cors_allowed_origins: list[str] = ["http://localhost:5173"]

    signup_bonus_credits: int = 2000

    opensky_client_id: str = ""
    opensky_client_secret: str = ""
    opensky_token_url: str = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
    opensky_api_base: str = "https://opensky-network.org/api"
    poller_interval_seconds: int = 45


@lru_cache
def get_settings() -> Settings:
    return Settings()
