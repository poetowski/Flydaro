"""adsb.fi client: a free, unauthenticated community ADS-B feed used in place
of OpenSky Network, whose own docs say they may block traffic from AWS and
other hyperscalers -- exactly the class of egress Render (and, confirmed
separately, a Cloudflare Worker relay) falls into. This is the ONLY module
in the codebase that talks to adsb.fi -- the web API and SPA only ever
read/write Postgres.

All physical units are normalized to match this codebase's existing
conventions (meters, m/s) at the parsing boundary in StateVector.from_adsb_json,
so every downstream consumer (tracker.py, thresholds.py) is unaffected by
adsb.fi's native units (feet, knots, ft/min).
"""

import asyncio
import logging
import time
from dataclasses import dataclass

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

KNOTS_TO_MS = 0.514444
FEET_TO_M = 0.3048
FPM_TO_MS = FEET_TO_M / 60

# adsb.fi's documented public rate limit is 1 request/second for the whole
# API -- not per-endpoint or per-caller. A small safety margin over 1.0s
# avoids edge-of-window 429s from clock/latency jitter.
MIN_REQUEST_INTERVAL_SECONDS = 1.05


@dataclass
class StateVector:
    icao24: str
    callsign: str | None
    longitude: float | None
    latitude: float | None
    baro_altitude: float | None
    on_ground: bool
    velocity: float | None
    vertical_rate: float | None
    geo_altitude: float | None
    # ICAO type code (e.g. "A321"), read directly off the live response --
    # adsb.fi includes this inline, unlike OpenSky which required a separate
    # bulk-CSV registry lookup keyed by icao24.
    aircraft_type_code: str | None
    raw: dict

    @classmethod
    def from_adsb_json(cls, record: dict) -> "StateVector":
        alt_baro_raw = record.get("alt_baro")
        on_ground = alt_baro_raw == "ground"
        baro_altitude = (
            float(alt_baro_raw) * FEET_TO_M
            if isinstance(alt_baro_raw, (int, float))
            else None
        )
        alt_geom_raw = record.get("alt_geom")
        geo_altitude = float(alt_geom_raw) * FEET_TO_M if isinstance(alt_geom_raw, (int, float)) else None

        gs = record.get("gs")
        velocity = float(gs) * KNOTS_TO_MS if isinstance(gs, (int, float)) else None

        # baro_rate is preferred (matches OpenSky's barometric vertical_rate);
        # geom_rate is the fallback adsb.fi itself uses when baro_rate is absent.
        rate_raw = record.get("baro_rate", record.get("geom_rate"))
        vertical_rate = float(rate_raw) * FPM_TO_MS if isinstance(rate_raw, (int, float)) else None

        callsign = (record.get("flight") or "").strip() or None
        type_code = (record.get("t") or "").strip().upper() or None

        return cls(
            icao24=record["hex"].lower(),
            callsign=callsign,
            longitude=record.get("lon"),
            latitude=record.get("lat"),
            baro_altitude=baro_altitude,
            on_ground=on_ground,
            velocity=velocity,
            vertical_rate=vertical_rate,
            geo_altitude=geo_altitude,
            aircraft_type_code=type_code,
            raw=record,
        )


class AdsbClient:
    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=20.0)
        self._rate_limit_lock = asyncio.Lock()
        self._last_call_monotonic: float | None = None
        # Outcome of the most recent call attempt -- surfaced on /health/adsb
        # so "0 flights" can be told apart from "adsb.fi calls are actually
        # failing/erroring".
        self.last_status_code: int | None = None
        self.last_status_detail: str | None = None

    async def aclose(self) -> None:
        await self._http.aclose()

    def _record_call_result(self, status_code: int | None, detail: str | None) -> None:
        self.last_status_code = status_code
        self.last_status_detail = detail

    async def _throttled_get(self, path: str) -> httpx.Response | None:
        """Serializes every call (regardless of caller) through a single
        pacing lock, so concurrent callers (e.g. flight_discovery_service.py
        querying several airports via asyncio.gather) can't collectively
        burst past adsb.fi's 1 req/sec ceiling -- the guarantee lives here,
        once, rather than needing every call site to coordinate it.
        """
        async with self._rate_limit_lock:
            now = time.monotonic()
            if self._last_call_monotonic is not None:
                wait_for = MIN_REQUEST_INTERVAL_SECONDS - (now - self._last_call_monotonic)
                if wait_for > 0:
                    await asyncio.sleep(wait_for)
            self._last_call_monotonic = time.monotonic()

            url = f"{settings.adsb_api_base}{path}"
            try:
                response = await self._http.get(url)
            except httpx.HTTPError as exc:
                logger.exception("adsb.fi request failed")
                self._record_call_result(None, f"{exc.__class__.__name__}: {exc}")
                return None

            self._record_call_result(
                response.status_code, None if response.is_success else _response_detail(response)
            )
            return response

    async def get_states_near(self, lat: float, lon: float, dist_nm: float) -> list[StateVector]:
        response = await self._throttled_get(f"/v2/lat/{lat}/lon/{lon}/dist/{dist_nm}")
        if response is None:
            return []
        if response.status_code == 429:
            logger.warning("adsb.fi rate limit hit (429), skipping this call")
            return []
        response.raise_for_status()

        body = response.json()
        aircraft = body.get("aircraft") or []
        return [StateVector.from_adsb_json(a) for a in aircraft if a.get("hex")]

    async def get_state_for_icao24(self, icao24: str) -> StateVector | None:
        """Single-aircraft live lookup, used for an on-demand landing check
        (has this specific aircraft got a current live report, and if so is
        it on the ground) rather than scanning a whole airport's radius.
        """
        response = await self._throttled_get(f"/v2/hex/{icao24.lower()}")
        if response is None or response.status_code == 429:
            return None
        response.raise_for_status()

        body = response.json()
        # Unlike get_states_near's /v2/lat/lon/dist endpoint, /v2/hex/
        # wraps its result under "ac", not "aircraft" -- confirmed live
        # against the real API; using the wrong key here silently made
        # every on-demand landing check look like "aircraft not found",
        # regardless of whether it actually was.
        aircraft = body.get("ac") or []
        return StateVector.from_adsb_json(aircraft[0]) if aircraft else None


def _response_detail(response: httpx.Response) -> str:
    text = response.text.strip()
    return text[:300] if text else (response.reason_phrase or f"HTTP {response.status_code}")
