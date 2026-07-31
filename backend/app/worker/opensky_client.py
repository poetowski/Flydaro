"""OpenSky Network client: OAuth2 client-credentials token management plus
bounding-box state-vector queries. This is the ONLY module in the codebase
that talks to OpenSky -- the web API and SPA only ever read/write Postgres.
"""

import logging
import time
from dataclasses import dataclass
from urllib.parse import quote

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Refresh the bearer token this many seconds before it actually expires, so a
# request never blocks mid-tick on a token fetch.
TOKEN_REFRESH_SAFETY_MARGIN_SECONDS = 60


def _relay_wrap(url: str) -> str:
    """Routes through the configured external relay if set (see
    opensky_relay_url's docstring in config.py); otherwise returns the
    OpenSky URL unchanged."""
    if not settings.opensky_relay_url:
        return url
    return f"{settings.opensky_relay_url}?target={quote(url, safe='')}"


def _relay_headers(headers: dict) -> dict:
    if settings.opensky_relay_url and settings.opensky_relay_secret:
        return {**headers, "X-Relay-Secret": settings.opensky_relay_secret}
    return headers


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
    raw: list

    @classmethod
    def from_raw(cls, row: list) -> "StateVector":
        def at(index: int):
            return row[index] if index < len(row) else None

        return cls(
            icao24=at(0),
            callsign=(at(1) or "").strip() or None,
            longitude=at(5),
            latitude=at(6),
            baro_altitude=at(7),
            on_ground=bool(at(8)),
            velocity=at(9),
            vertical_rate=at(11),
            geo_altitude=at(13),
            raw=row,
        )


class OpenSkyClient:
    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=20.0)
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0
        self.credits_remaining: int | None = None
        # Outcome of the most recent states/all (or token) call attempt --
        # surfaced on the admin heartbeat so "0 flights" can be told apart
        # from "OpenSky calls are actually failing/401ing/whatever".
        self.last_status_code: int | None = None
        self.last_status_detail: str | None = None

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _fetch_token(self) -> None:
        response = await self._http.post(
            _relay_wrap(settings.opensky_token_url),
            data={
                "grant_type": "client_credentials",
                "client_id": settings.opensky_client_id,
                "client_secret": settings.opensky_client_secret,
            },
            headers=_relay_headers({}),
        )
        response.raise_for_status()
        body = response.json()
        self._access_token = body["access_token"]
        self._token_expires_at = time.monotonic() + float(body.get("expires_in", 1800))

    async def _get_valid_token(self) -> str:
        if (
            self._access_token is None
            or time.monotonic() >= self._token_expires_at - TOKEN_REFRESH_SAFETY_MARGIN_SECONDS
        ):
            await self._fetch_token()
        return self._access_token

    def _update_credit_budget(self, response: httpx.Response) -> None:
        remaining = response.headers.get("X-Rate-Limit-Remaining")
        if remaining is not None:
            try:
                self.credits_remaining = int(remaining)
            except ValueError:
                pass
            if self.credits_remaining is not None and self.credits_remaining < 50:
                logger.warning(
                    "OpenSky credit budget low: %s remaining", self.credits_remaining
                )

    def _record_call_result(self, status_code: int | None, detail: str | None) -> None:
        self.last_status_code = status_code
        self.last_status_detail = detail

    async def _get(self, path: str, params: dict) -> httpx.Response | None:
        """Shared GET path: token fetch, request, one 401-triggered token
        retry, credit/call-result bookkeeping. Returns None (having already
        recorded why) on anything that never produced a response; otherwise
        returns the response as-is -- callers still need to check status
        (e.g. 429) themselves since "no exception" isn't "treat as success"
        for every endpoint the same way.
        """
        try:
            token = await self._get_valid_token()
        except httpx.HTTPStatusError as exc:
            self._record_call_result(exc.response.status_code, _response_detail(exc.response))
            return None
        except httpx.HTTPError as exc:
            self._record_call_result(None, f"Token request failed: {exc.__class__.__name__}: {exc}")
            return None

        # Query params are baked into the URL string itself (rather than
        # passed separately to httpx) so the *whole* target -- path and
        # params together -- is what gets url-encoded as the relay's
        # ?target= value when a relay is configured; harmless/equivalent to
        # passing params separately when it isn't.
        target_url = str(httpx.URL(f"{settings.opensky_api_base}{path}", params=params))
        url = _relay_wrap(target_url)
        headers = _relay_headers({"Authorization": f"Bearer {token}"})
        try:
            response = await self._http.get(url, headers=headers)
        except httpx.HTTPError as exc:
            logger.exception("OpenSky request failed")
            self._record_call_result(None, f"{exc.__class__.__name__}: {exc}")
            return None

        if response.status_code == 401:
            # Token may have been invalidated server-side; force one retry.
            self._access_token = None
            try:
                token = await self._get_valid_token()
            except httpx.HTTPError as exc:
                self._record_call_result(None, f"Token refresh failed: {exc.__class__.__name__}: {exc}")
                return None
            headers = _relay_headers({"Authorization": f"Bearer {token}"})
            response = await self._http.get(url, headers=headers)

        self._update_credit_budget(response)
        self._record_call_result(
            response.status_code, None if response.is_success else _response_detail(response)
        )
        return response

    async def get_states_in_bbox(
        self, lamin: float, lomin: float, lamax: float, lomax: float
    ) -> list[StateVector]:
        response = await self._get(
            "/states/all", {"lamin": lamin, "lomin": lomin, "lamax": lamax, "lomax": lomax}
        )
        if response is None:
            return []
        if response.status_code == 429:
            logger.warning("OpenSky rate limit hit (429), skipping this tick for this box")
            return []
        response.raise_for_status()

        body = response.json()
        states = body.get("states") or []
        return [StateVector.from_raw(row) for row in states]

    async def get_state_for_icao24(self, icao24: str) -> StateVector | None:
        """Single-aircraft live lookup, used for an on-demand landing check
        (has this specific aircraft got a current live report, and if so is
        it on the ground) rather than scanning a whole airport's bbox.
        """
        response = await self._get("/states/all", {"icao24": icao24.lower()})
        if response is None or response.status_code == 429:
            return None
        response.raise_for_status()

        body = response.json()
        states = body.get("states") or []
        return StateVector.from_raw(states[0]) if states else None

    async def get_aircraft_flights(self, icao24: str, begin: int, end: int) -> list[dict]:
        """Historical flight legs for one aircraft over [begin, end] (unix
        seconds, OpenSky caps the window at 7 days) via /flights/aircraft --
        the only way to confirm what happened to a flight after the fact,
        e.g. once the tracking window itself has gone quiet/the app was
        asleep through the actual landing. Distinct from live state
        vectors: this comes from OpenSky's own arrival-estimation, keyed by
        estDepartureAirport/estArrivalAirport, not on_ground/altitude.
        """
        response = await self._get("/flights/aircraft", {"icao24": icao24.lower(), "begin": begin, "end": end})
        if response is None or response.status_code == 429:
            return []
        response.raise_for_status()
        return response.json() or []


def _response_detail(response: httpx.Response) -> str:
    text = response.text.strip()
    return text[:300] if text else (response.reason_phrase or f"HTTP {response.status_code}")
