from datetime import datetime, timezone

from app.models.aircraft import AircraftRegistry
from app.models.airport import Airport
from app.worker.opensky_client import StateVector
from app.worker.tracker import (
    create_tracked_flight,
    looks_like_landing,
    looks_like_recent_takeoff,
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
