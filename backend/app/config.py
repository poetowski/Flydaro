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

    # Free, unauthenticated community ADS-B feed (see app/worker/adsb_client.py)
    # -- adsb.lol mirrors the same schema/endpoints, so switching is just this
    # one URL if adsb.fi ever becomes unreliable.
    adsb_api_base: str = "https://opendata.adsb.fi/api"

    run_migrations_on_startup: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
