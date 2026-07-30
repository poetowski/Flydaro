from datetime import datetime, timedelta, timezone

from app.models.flight import TrackedFlightStatus
from app.models.rental import RentalStatus
from app.services import flight_status_service, rental_service
from app.services.wallet_service import apply_ledger_entry
from app.models.wallet import LedgerReason
from app.worker.opensky_client import StateVector


async def _fund(db, user, amount=2000):
    await apply_ledger_entry(db, user.id, amount, LedgerReason.SIGNUP_BONUS)


def _airborne_state(icao24="abc123", on_ground=False):
    return StateVector(
        icao24=icao24,
        callsign="TST123",
        longitude=4.7639,
        latitude=52.3086,
        baro_altitude=300.0,
        on_ground=on_ground,
        velocity=100.0,
        vertical_rate=5.0,
        geo_altitude=300.0,
        raw=[],
    )


class FakeOpenSkyClient:
    def __init__(self, live_state=None, historical_legs=None):
        self._live_state = live_state
        self._historical_legs = historical_legs or []
        self.live_state_calls = 0
        self.historical_calls = 0

    async def get_state_for_icao24(self, icao24):
        self.live_state_calls += 1
        return self._live_state

    async def get_aircraft_flights(self, icao24, begin, end):
        self.historical_calls += 1
        return self._historical_legs


async def test_refresh_confirms_landing_via_live_state(db, user, open_flight, item_type, airport):
    await _fund(db, user)
    rental = await rental_service.create_rental(db, user.id, open_flight.id, item_type.id, 300)
    open_flight.status = TrackedFlightStatus.AIRBORNE_LOCKED
    await db.flush()

    client = FakeOpenSkyClient(live_state=_airborne_state(on_ground=True))
    await flight_status_service.refresh_flight_status(db, client, open_flight, airport)

    assert open_flight.status == TrackedFlightStatus.RESOLVED_LANDED
    assert open_flight.resolved_at is not None
    await db.refresh(rental)
    assert rental.status == RentalStatus.RESOLVED
    assert rental.settlement_credits is not None


async def test_refresh_still_airborne_updates_sample_without_resolving(db, open_flight, airport):
    client = FakeOpenSkyClient(live_state=_airborne_state(on_ground=False))
    original_last_seen = open_flight.last_seen_at

    await flight_status_service.refresh_flight_status(db, client, open_flight, airport)

    assert open_flight.status == TrackedFlightStatus.AIRBORNE_OPEN
    assert open_flight.last_seen_at >= original_last_seen


async def test_refresh_throttles_repeat_checks(db, open_flight, airport):
    open_flight.last_status_check_at = datetime.now(timezone.utc)
    await db.flush()

    client = FakeOpenSkyClient(live_state=_airborne_state(on_ground=True))
    await flight_status_service.refresh_flight_status(db, client, open_flight, airport)

    assert client.live_state_calls == 0
    assert open_flight.status == TrackedFlightStatus.AIRBORNE_OPEN


async def test_refresh_falls_back_to_historical_record_when_no_live_state(
    db, user, open_flight, item_type, airport
):
    await _fund(db, user)
    rental = await rental_service.create_rental(db, user.id, open_flight.id, item_type.id, 300)
    open_flight.status = TrackedFlightStatus.AIRBORNE_LOCKED
    await db.flush()

    first_seen_ts = open_flight.first_seen_at.timestamp()
    last_seen_ts = first_seen_ts + 45 * 60
    legs = [
        {
            "icao24": open_flight.icao24,
            "firstSeen": first_seen_ts,
            "estDepartureAirport": airport.icao4,
            "lastSeen": last_seen_ts,
            "estArrivalAirport": "EDDF",
        }
    ]
    client = FakeOpenSkyClient(live_state=None, historical_legs=legs)

    await flight_status_service.refresh_flight_status(db, client, open_flight, airport)

    assert open_flight.status == TrackedFlightStatus.RESOLVED_LANDED
    assert open_flight.resolved_at == datetime.fromtimestamp(last_seen_ts, tz=timezone.utc)
    await db.refresh(rental)
    assert rental.status == RentalStatus.RESOLVED


async def test_refresh_leaves_flight_open_when_nothing_confirms_landing(db, open_flight, airport):
    client = FakeOpenSkyClient(live_state=None, historical_legs=[])
    await flight_status_service.refresh_flight_status(db, client, open_flight, airport)

    assert open_flight.status == TrackedFlightStatus.AIRBORNE_OPEN
    assert open_flight.resolved_at is None


async def test_refresh_ignores_unrelated_historical_leg(db, open_flight, airport):
    # firstSeen far outside the match tolerance -- must not be treated as this flight.
    unrelated_first_seen = open_flight.first_seen_at.timestamp() - 5 * 3600
    legs = [
        {
            "icao24": open_flight.icao24,
            "firstSeen": unrelated_first_seen,
            "estDepartureAirport": airport.icao4,
            "lastSeen": unrelated_first_seen + 3600,
            "estArrivalAirport": "EDDF",
        }
    ]
    client = FakeOpenSkyClient(live_state=None, historical_legs=legs)

    await flight_status_service.refresh_flight_status(db, client, open_flight, airport)

    assert open_flight.status == TrackedFlightStatus.AIRBORNE_OPEN


async def test_refresh_noop_on_already_resolved_flight(db, open_flight, airport):
    open_flight.status = TrackedFlightStatus.RESOLVED_LANDED
    open_flight.resolved_at = datetime.now(timezone.utc)
    await db.flush()

    client = FakeOpenSkyClient(live_state=_airborne_state(on_ground=True))
    await flight_status_service.refresh_flight_status(db, client, open_flight, airport)

    assert client.live_state_calls == 0
