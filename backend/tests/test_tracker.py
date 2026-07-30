from datetime import datetime, timedelta, timezone

from app.models.aircraft import AircraftRegistry
from app.models.airport import Airport
from app.models.flight import TrackedFlight, TrackedFlightStatus
from app.worker import thresholds
from app.worker.opensky_client import StateVector
from app.worker.tracker import (
    build_resolution_summary,
    create_tracked_flight,
    duration_ceiling_breached,
    landing_grace_period_elapsed,
    looks_like_landing,
    looks_like_recent_takeoff,
    lost_signal_ceiling_breached,
    resolve_aircraft_type_id,
)

EHAM = Airport(
    id=1,
    icao4="EHAM",
    iata="AMS",
    name="Amsterdam Schiphol",
    city="Amsterdam",
    country="Netherlands",
    lat=52.3086,
    lon=4.7639,
    bbox_lamin=51.9586,
    bbox_lomin=4.4139,
    bbox_lamax=52.6586,
    bbox_lomax=5.1139,
)


def _state(lat, lon, alt, on_ground, velocity=100.0, vertical_rate=5.0):
    raw = ["abc123", "TST123 ", "NL", None, None, lon, lat, alt, on_ground, velocity, 0, vertical_rate, None, alt]
    return StateVector.from_raw(raw)


def test_takeoff_detected_close_to_airport_low_and_climbing():
    state = _state(52.32, 4.78, 300.0, False, vertical_rate=6.0)
    assert looks_like_recent_takeoff(state, EHAM) is True


def test_takeoff_not_detected_when_on_ground():
    state = _state(52.31, 4.77, 0.0, True, velocity=0.0, vertical_rate=0.0)
    assert looks_like_recent_takeoff(state, EHAM) is False


def test_takeoff_not_detected_too_far_from_airport():
    # Roughly 100+ km away
    state = _state(53.5, 4.78, 300.0, False, vertical_rate=6.0)
    assert looks_like_recent_takeoff(state, EHAM) is False


def test_takeoff_not_detected_already_cruising():
    state = _state(52.32, 4.78, 10000.0, False, vertical_rate=0.0)
    assert looks_like_recent_takeoff(state, EHAM) is False


def test_takeoff_not_detected_descending():
    state = _state(52.32, 4.78, 300.0, False, vertical_rate=-6.0)
    assert looks_like_recent_takeoff(state, EHAM) is False


def test_takeoff_not_detected_descending_near_zero():
    # Pins the exact reject cutoff (< 0.0), distinct from the far-negative case above.
    state = _state(52.32, 4.78, 300.0, False, vertical_rate=-0.1)
    assert looks_like_recent_takeoff(state, EHAM) is False


def test_takeoff_detected_with_null_vertical_rate():
    # OpenSky frequently omits vertical_rate during climb-out -- must not
    # reject on missing data, only on data that clearly shows not climbing.
    state = _state(52.32, 4.78, 300.0, False, vertical_rate=None)
    assert looks_like_recent_takeoff(state, EHAM) is True


def test_takeoff_detected_with_zero_vertical_rate():
    # Exactly-level doesn't reject -- only a negative reading does.
    state = _state(52.32, 4.78, 300.0, False, vertical_rate=0.0)
    assert looks_like_recent_takeoff(state, EHAM) is True


def test_takeoff_detected_via_geo_altitude_fallback():
    # baro_altitude (index 7) missing, geo_altitude (index 13) present.
    raw = ["abc123", "TST123 ", "NL", None, None, 4.78, 52.32, None, False, 100.0, 0, 6.0, None, 300.0]
    state = StateVector.from_raw(raw)
    assert looks_like_recent_takeoff(state, EHAM) is True


def test_takeoff_not_detected_when_both_altitudes_missing():
    raw = ["abc123", "TST123 ", "NL", None, None, 4.78, 52.32, None, False, 100.0, 0, 6.0, None, None]
    state = StateVector.from_raw(raw)
    assert looks_like_recent_takeoff(state, EHAM) is False


def test_landing_detected_via_on_ground_flag():
    state = _state(52.31, 4.77, 500.0, True, velocity=5.0, vertical_rate=0.0)
    assert looks_like_landing(state) is True


def test_landing_detected_via_low_alt_low_speed_fallback():
    state = _state(52.31, 4.77, 100.0, False, velocity=30.0, vertical_rate=1.0)
    assert looks_like_landing(state) is True


def test_landing_not_detected_while_cruising():
    state = _state(48.0, 8.0, 10000.0, False, velocity=250.0, vertical_rate=0.0)
    assert looks_like_landing(state) is False


def test_landing_not_detected_still_descending_fast():
    state = _state(52.31, 4.77, 100.0, False, velocity=30.0, vertical_rate=-8.0)
    assert looks_like_landing(state) is False


async def test_resolve_aircraft_type_id_matches_registry_entry(db, aircraft_type):
    db.add(AircraftRegistry(icao24="abc123", aircraft_type_id=aircraft_type.id))
    await db.flush()

    resolved = await resolve_aircraft_type_id(db, "ABC123")  # case-insensitive lookup
    assert resolved == aircraft_type.id


async def test_resolve_aircraft_type_id_unknown_icao24_returns_none(db):
    assert await resolve_aircraft_type_id(db, "ffffff") is None


async def test_create_tracked_flight_resolves_known_aircraft_type(db, airport, aircraft_type):
    db.add(AircraftRegistry(icao24="abc123", aircraft_type_id=aircraft_type.id))
    await db.flush()

    state = _state(52.32, 4.78, 300.0, False, vertical_rate=6.0)
    flight = await create_tracked_flight(db, state, airport, datetime.now(timezone.utc))
    assert flight.aircraft_type_id == aircraft_type.id


async def test_create_tracked_flight_leaves_unknown_aircraft_type_null(db, airport):
    state = _state(52.32, 4.78, 300.0, False, vertical_rate=6.0)
    flight = await create_tracked_flight(db, state, airport, datetime.now(timezone.utc))
    assert flight.aircraft_type_id is None


def _flight(**overrides) -> TrackedFlight:
    now = datetime.now(timezone.utc)
    defaults = dict(
        icao24="abc123",
        origin_airport_id=1,
        first_seen_at=now,
        first_seen_lat=52.32,
        first_seen_lon=4.78,
        last_seen_at=now,
        last_seen_lat=52.32,
        last_seen_lon=4.78,
        last_seen_alt=300.0,
        status=TrackedFlightStatus.AIRBORNE_OPEN,
        landing_suspected_at=None,
    )
    defaults.update(overrides)
    return TrackedFlight(**defaults)


def test_build_resolution_summary_shape():
    flight = _flight(last_seen_lat=1.0, last_seen_lon=2.0, last_seen_alt=300.0, origin_airport_id=42)
    summary = build_resolution_summary(flight, 12.345)
    assert summary == {
        "duration_minutes": 12.3,
        "last_lat": 1.0,
        "last_lon": 2.0,
        "last_alt": 300.0,
        "origin_airport_id": 42,
    }


def test_duration_ceiling_not_breached_just_under():
    now = datetime.now(timezone.utc)
    flight = _flight(first_seen_at=now - timedelta(minutes=thresholds.MAX_FLIGHT_DURATION_CEILING_MINUTES - 1))
    assert duration_ceiling_breached(flight, now) is False


def test_duration_ceiling_breached_just_over():
    now = datetime.now(timezone.utc)
    flight = _flight(first_seen_at=now - timedelta(minutes=thresholds.MAX_FLIGHT_DURATION_CEILING_MINUTES + 1))
    assert duration_ceiling_breached(flight, now) is True


def test_lost_signal_ceiling_not_breached_just_under():
    now = datetime.now(timezone.utc)
    flight = _flight(last_seen_at=now - timedelta(minutes=thresholds.LOST_SIGNAL_CEILING_MINUTES - 1))
    assert lost_signal_ceiling_breached(flight, now) is False


def test_lost_signal_ceiling_breached_just_over():
    now = datetime.now(timezone.utc)
    flight = _flight(last_seen_at=now - timedelta(minutes=thresholds.LOST_SIGNAL_CEILING_MINUTES + 1))
    assert lost_signal_ceiling_breached(flight, now) is True


def test_landing_grace_period_not_elapsed_without_landing_suspected_at():
    now = datetime.now(timezone.utc)
    flight = _flight(landing_suspected_at=None)
    assert landing_grace_period_elapsed(flight, now) is False


def test_landing_grace_period_not_elapsed_just_under():
    now = datetime.now(timezone.utc)
    flight = _flight(
        landing_suspected_at=now - timedelta(minutes=thresholds.LANDING_GRACE_PERIOD_MINUTES - 1)
    )
    assert landing_grace_period_elapsed(flight, now) is False


def test_landing_grace_period_elapsed_at_boundary():
    now = datetime.now(timezone.utc)
    flight = _flight(
        landing_suspected_at=now - timedelta(minutes=thresholds.LANDING_GRACE_PERIOD_MINUTES)
    )
    assert landing_grace_period_elapsed(flight, now) is True
