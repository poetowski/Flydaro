from datetime import datetime, timedelta, timezone

from app.models.poller_heartbeat import PollerHeartbeat
from app.worker import heartbeat


def _naive(dt: datetime) -> datetime:
    # SQLite (unlike Postgres) doesn't preserve tzinfo across a flush-forced
    # refresh -- normalize both sides before comparing, a portability quirk
    # of the test DB, not something the model/heartbeat code needs to handle.
    return dt.replace(tzinfo=None)


async def test_record_tick_success_then_failure_then_success(db):
    t1 = datetime.now(timezone.utc)
    await heartbeat.record_tick(db, now=t1, success=True, credits_remaining=100)
    row = await db.get(PollerHeartbeat, 1)
    assert _naive(row.last_success_at) == _naive(t1)
    assert row.last_error is None
    assert row.credits_remaining == 100

    t2 = t1 + timedelta(seconds=60)
    await heartbeat.record_tick(db, now=t2, success=False, error="OpenSky timed out")
    row = await db.get(PollerHeartbeat, 1)
    assert _naive(row.last_tick_at) == _naive(t2)
    assert row.last_error == "OpenSky timed out"
    assert _naive(row.last_success_at) == _naive(t1)  # unchanged from the prior success
    assert row.credits_remaining == 100  # unchanged: failure path passed no value

    t3 = t2 + timedelta(seconds=60)
    await heartbeat.record_tick(db, now=t3, success=True, credits_remaining=90)
    row = await db.get(PollerHeartbeat, 1)
    assert row.last_error is None
    assert _naive(row.last_success_at) == _naive(t3)
    assert row.credits_remaining == 90


async def test_record_tick_stores_opensky_call_result(db):
    t1 = datetime.now(timezone.utc)
    await heartbeat.record_tick(
        db, now=t1, success=False, error="OpenSky 401", opensky_status=401, opensky_detail="Unauthorized"
    )
    row = await db.get(PollerHeartbeat, 1)
    assert row.last_opensky_status == 401
    assert row.last_opensky_detail == "Unauthorized"

    t2 = t1 + timedelta(seconds=60)
    await heartbeat.record_tick(db, now=t2, success=True, opensky_status=200, opensky_detail=None)
    row = await db.get(PollerHeartbeat, 1)
    assert row.last_opensky_status == 200
    assert row.last_opensky_detail is None
