import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import aircraft_types, airports, auth, flights, item_types, licenses, rentals, wallet
from app.worker.opensky_client import OpenSkyClient
from app.worker.poller import run_forever

logger = logging.getLogger(__name__)
settings = get_settings()

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _run_migrations() -> None:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.run_migrations_on_startup:
        logger.info("Running migrations on startup")
        await asyncio.to_thread(_run_migrations)

    poller_task = None
    client = None
    if settings.run_poller_in_api:
        if not settings.opensky_client_id or not settings.opensky_client_secret:
            logger.warning(
                "OPENSKY_CLIENT_ID/OPENSKY_CLIENT_SECRET are not set -- the "
                "in-process poller will run but every request to OpenSky will fail."
            )
        client = OpenSkyClient()
        poller_task = asyncio.create_task(run_forever(client, settings.poller_interval_seconds))

    yield

    if poller_task is not None:
        poller_task.cancel()
    if client is not None:
        await client.aclose()


app = FastAPI(title="Flydaro API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(wallet.router)
app.include_router(airports.router)
app.include_router(item_types.router)
app.include_router(aircraft_types.router)
app.include_router(licenses.router)
app.include_router(flights.router)
app.include_router(rentals.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
