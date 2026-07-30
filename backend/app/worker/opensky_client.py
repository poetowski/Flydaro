"""OpenSky Network client: OAuth2 client-credentials token management plus
bounding-box state-vector queries. This is the ONLY module in the codebase
that talks to OpenSky -- the web API and SPA only ever read/write Postgres.
"""

import logging
import time
from dataclasses import dataclass

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Refresh the bearer token this many seconds before it actually expires, so a
# request never blocks mid-tick on a token fetch.
TOKEN_REFRESH_SAFETY_MARGIN_SECONDS = 60


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
            settings.opensky_token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.opensky_client_id,
                "client_secret": settings.opensky_client_secret,
            },
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

    async def get_states_in_bbox(
        self, lamin: float, lomin: float, lamax: float, lomax: float
    ) -> list[StateVector]:
        try:
            token = await self._get_valid_token()
        except httpx.HTTPStatusError as exc:
            self._record_call_result(exc.response.status_code, _response_detail(exc.response))
            return []
        except httpx.HTTPError as exc:
            self._record_call_result(None, f"Token request failed: {exc.__class__.__name__}: {exc}")
            return []

        try:
            response = await self._http.get(
                f"{settings.opensky_api_base}/states/all",
                params={"lamin": lamin, "lomin": lomin, "lamax": lamax, "lomax": lomax},
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.HTTPError as exc:
            logger.exception("OpenSky request failed")
            self._record_call_result(None, f"{exc.__class__.__name__}: {exc}")
            return []

        if response.status_code == 401:
            # Token may have been invalidated server-side; force one retry.
            self._access_token = None
            try:
                token = await self._get_valid_token()
            except httpx.HTTPError as exc:
                self._record_call_result(None, f"Token refresh failed: {exc.__class__.__name__}: {exc}")
                return []
            response = await self._http.get(
                f"{settings.opensky_api_base}/states/all",
                params={"lamin": lamin, "lomin": lomin, "lamax": lamax, "lomax": lomax},
                headers={"Authorization": f"Bearer {token}"},
            )

        self._update_credit_budget(response)
        self._record_call_result(
            response.status_code, None if response.is_success else _response_detail(response)
        )

        if response.status_code == 429:
            logger.warning("OpenSky rate limit hit (429), skipping this tick for this box")
            return []
        response.raise_for_status()

        body = response.json()
        states = body.get("states") or []
        return [StateVector.from_raw(row) for row in states]


def _response_detail(response: httpx.Response) -> str:
    text = response.text.strip()
    return text[:300] if text else (response.reason_phrase or f"HTTP {response.status_code}")
