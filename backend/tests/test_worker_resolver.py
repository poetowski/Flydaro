from datetime import datetime, timedelta, timezone

from app.models.flight import TrackedFlightStatus
from app.worker import resolver
from app.worker import thresholds


async def test_sweep_resolves_flight_past_max_duration_ceiling(db, open_flight):
    open_flight.first_seen_at = datetime.now(timezone.utc) - timedelta(
        minutes=thresholds.MAX_FLIGHT_DURATION_CEILING_MINUTES + 1
    )
    await db.flush()

    await resolver.sweep_timeouts_and_lost_signal(db)

    assert open_flight.status == TrackedFlightStatus.RESOLVED_TIMEOUT
    assert open_flight.resolved_at is not None


async def test_sweep_resolves_flight_with_no_recent_updates_as_lost_signal(db, open_flight):
    open_flight.last_seen_at = datetime.now(timezone.utc) - timedelta(
        minutes=thresholds.LOST_SIGNAL_CEILING_MINUTES + 1
    )
    await db.flush()

    await resolver.sweep_timeouts_and_lost_signal(db)

    assert open_flight.status == TrackedFlightStatus.RESOLVED_LOST_SIGNAL


async def test_sweep_leaves_healthy_flight_untouched(db, open_flight):
    await resolver.sweep_timeouts_and_lost_signal(db)
    assert open_flight.status == TrackedFlightStatus.AIRBORNE_OPEN


async def test_resolve_pending_landings_confirms_after_grace_period(db, open_flight):
    open_flight.status = TrackedFlightStatus.LANDING_SUSPECTED
    open_flight.landing_suspected_at = datetime.now(timezone.utc) - timedelta(
        minutes=thresholds.LANDING_GRACE_PERIOD_MINUTES + 1
    )
    await db.flush()

    await resolver.resolve_pending_landings(db)

    assert open_flight.status == TrackedFlightStatus.RESOLVED_LANDED


async def test_resolve_pending_landings_waits_out_grace_period(db, open_flight):
    open_flight.status = TrackedFlightStatus.LANDING_SUSPECTED
    open_flight.landing_suspected_at = datetime.now(timezone.utc)
    await db.flush()

    await resolver.resolve_pending_landings(db)

    assert open_flight.status == TrackedFlightStatus.LANDING_SUSPECTED
