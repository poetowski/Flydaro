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
) -> PollerHeartbeat:
    """Get-or-create + mutate the single heartbeat row (id=1).

    last_tick_at is set unconditionally (every attempt, success or not).
    last_success_at only advances on success. last_error is cleared to
    None on success, set on failure. credits_remaining is only overwritten
    when a value is supplied -- a failed tick that errored before any
    OpenSky call passes None here, and that must NOT blank out the last
    known real value.
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

    await db.flush()
    return heartbeat
