import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.routers import (
    aircraft_families,
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

logger = logging.getLogger(__name__)
settings = get_settings()

BACKEND_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BACKEND_ROOT.parent / "frontend" / "dist"

# Uvicorn doesn't bind/listen on the port until this lifespan's startup
# finishes -- a migration step that hangs (e.g. a DB that's unreachable
# rather than cleanly refusing) would otherwise sit silently until
# Render's own ~15-minute port-scan timeout kills the deploy, with zero
# diagnostic signal about why. This ceiling turns that into a fast, loud
# failure instead.
STARTUP_MIGRATION_TIMEOUT_SECONDS = 60


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
            await asyncio.wait_for(
                asyncio.to_thread(_run_migrations), timeout=STARTUP_MIGRATION_TIMEOUT_SECONDS
            )
        except TimeoutError:
            logger.error(
                "Migrations did not complete within %ss -- likely a DB "
                "connectivity issue reaching DATABASE_URL_DIRECT, not a "
                "migration bug",
                STARTUP_MIGRATION_TIMEOUT_SECONDS,
            )
            raise
        except Exception:
            logger.exception("Migrations failed on startup")
            raise

    if not settings.opensky_client_id or not settings.opensky_client_secret:
        logger.warning(
            "OPENSKY_CLIENT_ID/OPENSKY_CLIENT_SECRET are not set -- OpenSky "
            "calls (flight-board discovery and on-demand rental status "
            "checks) will fail."
        )

    # No background task: OpenSky is only ever called ad hoc, from within a
    # request (see flight_discovery_service.py / flight_status_service.py).
    client = OpenSkyClient()
    app.state.opensky_client = client

    yield

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
app.include_router(aircraft_families.router)
app.include_router(licenses.router)
app.include_router(flights.router)
app.include_router(rentals.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/opensky")
async def opensky_health() -> dict[str, int | str | bool | None]:
    """The only visibility into whether ad-hoc OpenSky calls (flight-board
    discovery, on-demand rental status checks) are actually succeeding in
    this deployment -- there's no background poller left to attach a
    heartbeat to, but the shared OpenSkyClient still tracks its own last
    call's outcome, which this just reads back. Unauthenticated like
    /health since it exposes no player data, only call diagnostics.

    Also does a live check against a well-known, unrelated host (GitHub's
    API) to tell apart "OpenSky specifically is unreachable/blocking us"
    from "this deployment's outbound networking is broken generally" --
    two very different problems with very different fixes.
    """
    client: OpenSkyClient = app.state.opensky_client

    general_egress_ok: bool | None
    general_egress_detail: str | None
    try:
        async with httpx.AsyncClient(timeout=10.0) as probe:
            response = await probe.get("https://api.github.com")
        general_egress_ok = response.status_code < 500
        general_egress_detail = f"HTTP {response.status_code}"
    except httpx.HTTPError as exc:
        general_egress_ok = False
        general_egress_detail = f"{exc.__class__.__name__}: {exc}"

    return {
        "last_opensky_status": client.last_status_code,
        "last_opensky_detail": client.last_status_detail,
        "credits_remaining": client.credits_remaining,
        "general_egress_ok": general_egress_ok,
        "general_egress_detail": general_egress_detail,
    }


# KJFK's coordinates (see alembic/versions/0004_seed_aircraft_types_and_locked_airports.py)
# -- an arbitrary but real, high-traffic seeded airport, used only to prove
# reachability, not to fetch anything the app actually needs yet.
_ADSB_PROBE_URL = "https://opendata.adsb.fi/api/v2/lat/40.6413/lon/-73.7781/dist/25"


@app.get("/health/adsb")
async def adsb_health() -> dict[str, int | str | None]:
    """One-shot reachability check for adsb.fi (a free, unauthenticated
    community ADS-B feed being evaluated as an OpenSky replacement, since
    OpenSky's own docs say they may block hyperscaler/cloud IP ranges --
    exactly the class of network Render's egress falls into). This is the
    same "prove it before building on it" check /health/opensky already
    demonstrated the value of -- don't assume reachability from a sandbox
    test alone.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as probe:
            response = await probe.get(_ADSB_PROBE_URL)
        return {
            "status_code": response.status_code,
            "detail": None if response.is_success else response.text[:300],
        }
    except httpx.HTTPError as exc:
        return {"status_code": None, "detail": f"{exc.__class__.__name__}: {exc}"}


# Registered last so it only catches requests no API route above matched.
# Absent in local dev unless you've run `npm run build` -- the frontend
# normally runs separately via `npm run dev` there (see README).
if FRONTEND_DIST.is_dir():
    app.mount("/", SPAStaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
