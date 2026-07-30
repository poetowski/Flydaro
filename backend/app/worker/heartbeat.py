from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.poller_heartbeat import PollerHeartbeat

HEARTBEAT_ID = 1


async def record_tick(
    db: AsyncSession,
    *,
    now: datetime,
    success: bool,
    error: str | None = None,
    credits_remaining: int | None = None,
    opensky_status: int | None = None,
    opensky_detail: str | None = None,
) -> PollerHeartbeat:
    """Get-or-create + mutate the single heartbeat row (id=1).

    last_tick_at is set unconditionally (every attempt, success or not).
    last_success_at only advances on success. last_error is cleared to
    None on success, set on failure. credits_remaining is only overwritten
    when a value is supplied -- a failed tick that errored before any
    OpenSky call passes None here, and that must NOT blank out the last
    known real value.

    opensky_status/opensky_detail always overwrite (no None-guard): they
    come straight from OpenSkyClient's own last-call-result attributes,
    which already only change when a real HTTP call happens -- a tick with
    zero active airports just re-writes whatever the client already had,
    which is correct (nothing changed).
    """
    heartbeat = await db.get(PollerHeartbeat, HEARTBEAT_ID)
    if heartbeat is None:
        heartbeat = PollerHeartbeat(id=HEARTBEAT_ID, last_tick_at=now)
        db.add(heartbeat)

    heartbeat.last_tick_at = now
    if success:
        heartbeat.last_success_at = now
        heartbeat.last_error = None
    else:
        heartbeat.last_error = error
    if credits_remaining is not None:
        heartbeat.credits_remaining = credits_remaining
    heartbeat.last_opensky_status = opensky_status
    heartbeat.last_opensky_detail = opensky_detail

    await db.flush()
    return heartbeat
