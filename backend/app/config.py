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

    # Optional workaround for a deployment whose outbound network is
    # blocked/throttled by OpenSky specifically (seen on Render): route
    # every OpenSky call through an external relay (e.g. a Cloudflare
    # Worker) instead of calling opensky-network.org directly. Leave both
    # blank to call OpenSky directly, which is the default and what local
    # dev uses.
    opensky_relay_url: str = ""
    opensky_relay_secret: str = ""

    # Bulk, irregularly-updated, unversioned "as-is" CSV -- not a live API.
    # Verify this URL still resolves before relying on it; OpenSky gives no
    # stability guarantee on it.
    aircraft_registry_csv_url: str = "https://opensky-network.org/datasets/metadata/aircraftDatabase.csv"

    run_migrations_on_startup: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
