"""Phase 1 payout formula: duration-bucket multipliers, always pays >0.

A clean confirmed landing (`landed_normally`) uses the full formula:
    payout = stake * duration_bucket_multiplier * cargo_type.payout_multiplier

A fallback resolution (`timeout` / `lost_signal` -- our own tracking gave up,
not a real negative outcome for the flight) pays a small flat profit instead,
deliberately worse than any real landing outcome and ignoring the cargo
multiplier, so players are never indifferent between a real resolution and a
coverage-gap fallback. Exact multipliers are starting guesses to tune from
real play (see plan's "Open risks").
"""

# (upper_bound_minutes_exclusive, multiplier) checked in order.
DURATION_BUCKETS: list[tuple[float, float]] = [
    (60.0, 1.2),
    (180.0, 1.5),
    (float("inf"), 2.0),
]

FALLBACK_MULTIPLIER = 1.05

LANDED_REASON = "landed_normally"
TIMEOUT_REASON = "timeout_fallback"
LOST_SIGNAL_REASON = "lost_signal_fallback"


def _duration_bucket_multiplier(duration_minutes: float) -> float:
    for upper_bound, multiplier in DURATION_BUCKETS:
        if duration_minutes < upper_bound:
            return multiplier
    return DURATION_BUCKETS[-1][1]


def compute_payout(
    stake_credits: int,
    duration_minutes: float,
    cargo_payout_multiplier: float,
    resolution_reason: str,
) -> tuple[int, dict]:
    if resolution_reason == LANDED_REASON:
        base_multiplier = _duration_bucket_multiplier(duration_minutes)
        total_multiplier = base_multiplier * cargo_payout_multiplier
    else:
        base_multiplier = FALLBACK_MULTIPLIER
        total_multiplier = base_multiplier

    payout_credits = max(1, round(stake_credits * total_multiplier))
    breakdown = {
        "stake_credits": stake_credits,
        "duration_minutes": round(duration_minutes, 1),
        "base_multiplier": base_multiplier,
        "cargo_multiplier": cargo_payout_multiplier if resolution_reason == LANDED_REASON else None,
        "total_multiplier": total_multiplier,
        "payout_credits": payout_credits,
        "resolution_reason": resolution_reason,
    }
    return payout_credits, breakdown
