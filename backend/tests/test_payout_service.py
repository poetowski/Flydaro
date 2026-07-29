from app.services.payout_service import (
    LANDED_REASON,
    LOST_SIGNAL_REASON,
    TIMEOUT_REASON,
    compute_payout,
)


def test_short_hop_bucket_multiplier():
    payout, breakdown = compute_payout(100, duration_minutes=30, cargo_payout_multiplier=1.0, resolution_reason=LANDED_REASON)
    assert breakdown["base_multiplier"] == 1.2
    assert payout == 120


def test_standard_bucket_multiplier():
    payout, breakdown = compute_payout(100, duration_minutes=120, cargo_payout_multiplier=1.0, resolution_reason=LANDED_REASON)
    assert breakdown["base_multiplier"] == 1.5
    assert payout == 150


def test_long_haul_bucket_multiplier():
    payout, breakdown = compute_payout(100, duration_minutes=400, cargo_payout_multiplier=1.0, resolution_reason=LANDED_REASON)
    assert breakdown["base_multiplier"] == 2.0
    assert payout == 200


def test_bucket_boundaries_are_exclusive_upper_bound():
    # exactly 60 minutes should fall into the 60-180 bucket, not the <60 one
    _, breakdown_at_60 = compute_payout(100, duration_minutes=60, cargo_payout_multiplier=1.0, resolution_reason=LANDED_REASON)
    assert breakdown_at_60["base_multiplier"] == 1.5

    _, breakdown_just_under = compute_payout(100, duration_minutes=59.9, cargo_payout_multiplier=1.0, resolution_reason=LANDED_REASON)
    assert breakdown_just_under["base_multiplier"] == 1.2


def test_cargo_multiplier_applied_on_clean_landing():
    payout, breakdown = compute_payout(100, duration_minutes=30, cargo_payout_multiplier=1.75, resolution_reason=LANDED_REASON)
    assert payout == round(100 * 1.2 * 1.75)
    assert breakdown["cargo_multiplier"] == 1.75


def test_fallback_ignores_cargo_multiplier_and_duration():
    payout_timeout, breakdown_timeout = compute_payout(
        100, duration_minutes=999, cargo_payout_multiplier=1.75, resolution_reason=TIMEOUT_REASON
    )
    payout_lost_signal, breakdown_lost_signal = compute_payout(
        100, duration_minutes=5, cargo_payout_multiplier=1.75, resolution_reason=LOST_SIGNAL_REASON
    )
    assert payout_timeout == payout_lost_signal == 105
    assert breakdown_timeout["cargo_multiplier"] is None
    assert breakdown_lost_signal["cargo_multiplier"] is None


def test_fallback_payout_always_worse_than_any_clean_landing_bucket():
    fallback_payout, _ = compute_payout(100, duration_minutes=1, cargo_payout_multiplier=1.0, resolution_reason=TIMEOUT_REASON)
    cheapest_clean_landing_payout, _ = compute_payout(
        100, duration_minutes=1, cargo_payout_multiplier=1.0, resolution_reason=LANDED_REASON
    )
    assert fallback_payout < cheapest_clean_landing_payout


def test_payout_never_zero_or_negative():
    payout, _ = compute_payout(1, duration_minutes=0, cargo_payout_multiplier=0.01, resolution_reason=LANDED_REASON)
    assert payout >= 1
