from datetime import datetime

from sqlalchemy import Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PollerHeartbeat(Base):
    """Single persisted row (fixed id=1) recording poller liveness.

    This is the only thing that can distinguish "poller crashed/stopped
    hours ago" from "poller is fine, there just haven't been any real
    takeoffs recently" -- TrackedFlight/FlightStateSample activity alone
    can't tell those apart. Written every tick attempt (success AND
    failure) from worker/poller.py's run_forever, using its own independent
    session/transaction -- see that module for why.

    Single-row-contention note: fine for the current single-poller
    architecture (one worker process OR one in-process API task, never
    both intentionally). If ever scaled to multiple concurrent poller
    instances, last-writer-wins on this row would mask one instance being
    down -- not a concern today, flagging for future readers.
    """

    __tablename__ = "poller_heartbeats"

    id: Mapped[int] = mapped_column(primary_key=True)
    last_tick_at: Mapped[datetime] = mapped_column(nullable=False)
    last_success_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # Text, not String(N): tracebacks/exception messages can exceed any
    # reasonable fixed cap and we'd rather store the whole thing than choose
    # a truncation length.
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    credits_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
