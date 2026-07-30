from datetime import datetime, timezone

from app.models.aircraft import AircraftType
from app.models.flight import TrackedFlight, TrackedFlightStatus
from app.routers.flights import get_flight_board


class FakeOpenSkyClient:
    """No-op stub: these tests exercise the board's DB-level filtering, not
    ad-hoc discovery itself (see test_flight_discovery_service.py for that)."""

    async def get_states_in_bbox(self, lamin, lomin, lamax, lomax):
        return []


async def test_board_excludes_flights_with_locked_aircraft_type(
    db, user, open_flight, locked_aircraft_type
):
    open_flight.aircraft_type_id = locked_aircraft_type.id
    await db.flush()

    result = await get_flight_board(current_user=user, db=db, client=FakeOpenSkyClient())
    assert open_flight.id not in [f.id for f in result]


async def test_board_aircraft_family_id_param_on_locked_family_returns_empty(
    db, user, open_flight, locked_aircraft_type, locked_aircraft_family
):
    open_flight.aircraft_type_id = locked_aircraft_type.id
    await db.flush()

    # Proves the param composes on top of the unlocked-families floor rather
    # than bypassing it -- before this change, this call returned the flight.
    result = await get_flight_board(
        aircraft_family_id=locked_aircraft_family.id,
        current_user=user,
        db=db,
        client=FakeOpenSkyClient(),
    )
    assert result == []


async def test_board_excludes_flights_at_locked_airport(db, user, open_flight, locked_airport):
    open_flight.origin_airport_id = locked_airport.id
    await db.flush()

    result = await get_flight_board(current_user=user, db=db, client=FakeOpenSkyClient())
    assert open_flight.id not in [f.id for f in result]


async def test_board_includes_flight_with_unlocked_airport_and_aircraft_type(
    db, user, open_flight
):
    result = await get_flight_board(current_user=user, db=db, client=FakeOpenSkyClient())
    assert open_flight.id in [f.id for f in result]


async def test_board_family_filter_expands_across_member_types(
    db, user, airport, aircraft_family, aircraft_type, open_flight
):
    # A second type in the SAME family as open_flight's aircraft_type, on a
    # second flight -- proves selecting the family surfaces both, not just
    # an exact type match.
    other_type = AircraftType(
        icao_type_code="A321",
        name="Airbus A321",
        manufacturer="Airbus",
        family_id=aircraft_family.id,
        is_active=True,
    )
    db.add(other_type)
    await db.flush()

    now = datetime.now(timezone.utc)
    other_flight = TrackedFlight(
        icao24="def456",
        callsign="TST456",
        origin_airport_id=airport.id,
        aircraft_type_id=other_type.id,
        first_seen_at=now,
        first_seen_lat=airport.lat,
        first_seen_lon=airport.lon,
        last_seen_at=now,
        last_seen_lat=airport.lat,
        last_seen_lon=airport.lon,
        last_seen_on_ground=False,
        status=TrackedFlightStatus.AIRBORNE_OPEN,
        capacity_open=True,
    )
    db.add(other_flight)
    await db.flush()

    result = await get_flight_board(
        aircraft_family_id=aircraft_family.id, current_user=user, db=db, client=FakeOpenSkyClient()
    )
    result_ids = {f.id for f in result}
    assert open_flight.id in result_ids
    assert other_flight.id in result_ids
