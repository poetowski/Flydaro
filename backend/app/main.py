import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.routers import (
    admin,
    aircraft_types,
    airports,
    auth,
    flights,
    item_types,
    licenses,
    rentals,
    wallet,
)
from app.worker.opensky_client import OpenSkyClient
from app.worker.poller import run_forever

logger = logging.getLogger(__name__)
settings = get_settings()

BACKEND_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BACKEND_ROOT.parent / "frontend" / "dist"


class SPAStaticFiles(StaticFiles):
    """Serves the built SPA, falling back to index.html for any path that
    isn't a real file -- e.g. /dashboard -- so client-side routing works on
    a hard refresh or direct link."""

    async def get_response(self, path: str, scope):
        # StaticFiles raises HTTPException(404) rather than returning a
        # 404 response, so the fallback has to be a catch, not a status check.
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


def _run_migrations() -> None:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.run_migrations_on_startup:
        logger.info("Running migrations on startup")
        try:
            await asyncio.to_thread(_run_migrations)
        except Exception:
            logger.exception("Migrations failed on startup")
            raise

    if not settings.opensky_client_id or not settings.opensky_client_secret:
        logger.warning(
            "OPENSKY_CLIENT_ID/OPENSKY_CLIENT_SECRET are not set -- OpenSky "
            "calls (poller and on-demand rental status checks) will fail."
        )

    # Shared regardless of run_poller_in_api: the on-demand landing check
    # in /rentals (app/services/flight_status_service.py) needs a client
    # even on deployments where the background poller loop is disabled.
    client = OpenSkyClient()
    app.state.opensky_client = client

    poller_task = None
    if settings.run_poller_in_api:
        poller_task = asyncio.create_task(run_forever(client, settings.poller_interval_seconds))

    yield

    if poller_task is not None:
        poller_task.cancel()
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
app.include_router(admin.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# Registered last so it only catches requests no API route above matched.
# Absent in local dev unless you've run `npm run build` -- the frontend
# normally runs separately via `npm run dev` there (see README).
if FRONTEND_DIST.is_dir():
    app.mount("/", SPAStaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
