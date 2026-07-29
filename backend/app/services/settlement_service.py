"""Phase 1 settlement formula: duration-bucket multipliers, always pays >0.

A clean confirmed landing (`landed_normally`) uses the full formula:
    settlement = rental_fee * duration_bucket_multiplier * item_type.settlement_multiplier

A fallback resolution (`timeout` / `lost_signal` -- our own tracking gave up,
not a real negative outcome for the flight) pays a small flat profit instead,
deliberately worse than any real landing outcome and ignoring the item
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


def compute_settlement(
    rental_fee_credits: int,
    duration_minutes: float,
    item_settlement_multiplier: float,
    resolution_reason: str,
) -> tuple[int, dict]:
    if resolution_reason == LANDED_REASON:
        base_multiplier = _duration_bucket_multiplier(duration_minutes)
        total_multiplier = base_multiplier * item_settlement_multiplier
    else:
        base_multiplier = FALLBACK_MULTIPLIER
        total_multiplier = base_multiplier

    settlement_credits = max(1, round(rental_fee_credits * total_multiplier))
    breakdown = {
        "rental_fee_credits": rental_fee_credits,
        "duration_minutes": round(duration_minutes, 1),
        "base_multiplier": base_multiplier,
        "item_multiplier": item_settlement_multiplier if resolution_reason == LANDED_REASON else None,
        "total_multiplier": total_multiplier,
        "settlement_credits": settlement_credits,
        "resolution_reason": resolution_reason,
    }
    return settlement_credits, breakdown
