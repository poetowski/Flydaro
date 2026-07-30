from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.flight import TrackedFlight, TrackedFlightStatus
from app.services import flight_discovery_service
from app.worker import thresholds
from app.worker.opensky_client import StateVector


def _state(icao24, lat, lon, on_ground=False, alt=300.0, velocity=100.0, vertical_rate=5.0):
    return StateVector(
        icao24=icao24,
        callsign="TST123",
        longitude=lon,
        latitude=lat,
        baro_altitude=alt,
        on_ground=on_ground,
        velocity=velocity,
        vertical_rate=vertical_rate,
        geo_altitude=alt,
        raw=[],
    )


class FakeOpenSkyClient:
    def __init__(self, states_by_bbox=None):
        self._states_by_bbox = states_by_bbox or {}
        self.calls = []

    async def get_states_in_bbox(self, lamin, lomin, lamax, lomax):
        self.calls.append((lamin, lomin, lamax, lomax))
        return self._states_by_bbox.get((lamin, lomin, lamax, lomax), [])


def _bbox_key(airport):
    return (airport.bbox_lamin, airport.bbox_lomin, airport.bbox_lamax, airport.bbox_lomax)


async def test_new_takeoff_creates_tracked_flight(db, airport):
    state = _state("newicao", airport.lat, airport.lon)
    client = FakeOpenSkyClient({_bbox_key(airport): [state]})

    await flight_discovery_service.refresh_board_for_airports(db, client, [airport])

    flight = await db.scalar(select(TrackedFlight).where(TrackedFlight.icao24 == "newicao"))
    assert flight is not None
    assert flight.status == TrackedFlightStatus.AIRBORNE_OPEN


async def test_capacity_window_closes_after_elapsed_minutes(db, open_flight, airport):
    open_flight.first_seen_at = datetime.now(timezone.utc) - timedelta(
        minutes=thresholds.CAPACITY_WINDOW_MINUTES + 1
    )
    await db.flush()
    state = _state(open_flight.icao24, airport.lat, airport.lon)
    client = FakeOpenSkyClient({_bbox_key(airport): [state]})

    await flight_discovery_service.refresh_board_for_airports(db, client, [airport])

    assert open_flight.status == TrackedFlightStatus.AIRBORNE_LOCKED
    assert open_flight.capacity_open is False


async def test_locked_flight_transitions_to_landing_suspected(db, open_flight, airport):
    open_flight.status = TrackedFlightStatus.AIRBORNE_LOCKED
    await db.flush()
    landing_state = _state(
        open_flight.icao24, airport.lat, airport.lon, alt=50.0, velocity=20.0, vertical_rate=0.5
    )
    client = FakeOpenSkyClient({_bbox_key(airport): [landing_state]})

    await flight_discovery_service.refresh_board_for_airports(db, client, [airport])

    assert open_flight.status == TrackedFlightStatus.LANDING_SUSPECTED
    assert open_flight.landing_suspected_at is not None


async def test_landing_suspected_rolls_back_on_touch_and_go(db, open_flight, airport):
    open_flight.status = TrackedFlightStatus.LANDING_SUSPECTED
    open_flight.landing_suspected_at = datetime.now(timezone.utc)
    await db.flush()
    climbing_state = _state(open_flight.icao24, airport.lat, airport.lon, alt=500.0, velocity=120.0, vertical_rate=8.0)
    client = FakeOpenSkyClient({_bbox_key(airport): [climbing_state]})

    await flight_discovery_service.refresh_board_for_airports(db, client, [airport])

    assert open_flight.status == TrackedFlightStatus.AIRBORNE_LOCKED
    assert open_flight.landing_suspected_at is None


async def test_landing_suspected_resolves_after_grace_period_with_no_fresh_state(
    db, open_flight, airport
):
    open_flight.status = TrackedFlightStatus.LANDING_SUSPECTED
    open_flight.landing_suspected_at = datetime.now(timezone.utc) - timedelta(
        minutes=thresholds.LANDING_GRACE_PERIOD_MINUTES + 1
    )
    await db.flush()
    client = FakeOpenSkyClient({_bbox_key(airport): []})

    await flight_discovery_service.refresh_board_for_airports(db, client, [airport])

    assert open_flight.status == TrackedFlightStatus.RESOLVED_LANDED


async def test_sweep_resolves_timeout_past_duration_ceiling_with_no_rental(db, open_flight, airport):
    open_flight.first_seen_at = datetime.now(timezone.utc) - timedelta(
        minutes=thresholds.MAX_FLIGHT_DURATION_CEILING_MINUTES + 1
    )
    await db.flush()
    client = FakeOpenSkyClient({_bbox_key(airport): []})

    await flight_discovery_service.refresh_board_for_airports(db, client, [airport])

    assert open_flight.status == TrackedFlightStatus.RESOLVED_TIMEOUT


async def test_sweep_resolves_lost_signal_past_ceiling(db, open_flight, airport):
    open_flight.last_seen_at = datetime.now(timezone.utc) - timedelta(
        minutes=thresholds.LOST_SIGNAL_CEILING_MINUTES + 1
    )
    await db.flush()
    client = FakeOpenSkyClient({_bbox_key(airport): []})

    await flight_discovery_service.refresh_board_for_airports(db, client, [airport])

    assert open_flight.status == TrackedFlightStatus.RESOLVED_LOST_SIGNAL


async def test_per_airport_throttle_skips_second_call_within_window(db, airport):
    client = FakeOpenSkyClient({_bbox_key(airport): []})

    await flight_discovery_service.refresh_board_for_airports(db, client, [airport])
    assert len(client.calls) == 1

    await flight_discovery_service.refresh_board_for_airports(db, client, [airport])
    assert len(client.calls) == 1  # still throttled, no second call


async def test_two_due_airports_both_get_queried(db, airport, locked_airport):
    client = FakeOpenSkyClient({_bbox_key(airport): [], _bbox_key(locked_airport): []})

    await flight_discovery_service.refresh_board_for_airports(db, client, [airport, locked_airport])

    assert len(client.calls) == 2
    assert _bbox_key(airport) in client.calls
    assert _bbox_key(locked_airport) in client.calls
