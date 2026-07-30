from app.routers.flights import get_flight_board


async def test_board_excludes_flights_with_locked_aircraft_type(
    db, user, open_flight, locked_aircraft_type
):
    open_flight.aircraft_type_id = locked_aircraft_type.id
    await db.flush()

    result = await get_flight_board(current_user=user, db=db)
    assert open_flight.id not in [f.id for f in result]


async def test_board_aircraft_type_id_param_on_locked_type_returns_empty(
    db, user, open_flight, locked_aircraft_type
):
    open_flight.aircraft_type_id = locked_aircraft_type.id
    await db.flush()

    # Proves the param composes on top of the unlocked-types floor rather
    # than bypassing it -- before this change, this call returned the flight.
    result = await get_flight_board(
        aircraft_type_id=locked_aircraft_type.id, current_user=user, db=db
    )
    assert result == []


async def test_board_excludes_flights_at_locked_airport(db, user, open_flight, locked_airport):
    open_flight.origin_airport_id = locked_airport.id
    await db.flush()

    result = await get_flight_board(current_user=user, db=db)
    assert open_flight.id not in [f.id for f in result]


async def test_board_includes_flight_with_unlocked_airport_and_aircraft_type(
    db, user, open_flight
):
    result = await get_flight_board(current_user=user, db=db)
    assert open_flight.id in [f.id for f in result]
