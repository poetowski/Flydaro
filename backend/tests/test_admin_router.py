from app.routers.admin import get_poller_health


async def test_poller_health_returns_defaults_with_no_heartbeat_row(db, user):
    user.is_admin = True
    await db.flush()

    result = await get_poller_health(current_user=user, db=db)
    assert result.heartbeat.last_tick_at is None
    assert result.heartbeat.seconds_since_last_tick is None


async def test_poller_health_aggregates_status_counts_and_recent_flights(
    db, user, open_flight, airport
):
    user.is_admin = True
    await db.flush()

    result = await get_poller_health(current_user=user, db=db)

    assert any(c.status == open_flight.status.value and c.count == 1 for c in result.status_counts)
    assert any(f.id == open_flight.id for f in result.recent_flights)
    recent = next(f for f in result.recent_flights if f.id == open_flight.id)
    assert recent.origin_airport_name == airport.name


async def test_poller_health_lists_only_active_airports(db, user, airport, locked_airport):
    user.is_admin = True
    await db.flush()
    # airport fixture is_active=True, locked_airport fixture is_active=False

    result = await get_poller_health(current_user=user, db=db)
    active_ids = {a.id for a in result.active_airports}
    assert airport.id in active_ids
    assert locked_airport.id not in active_ids
