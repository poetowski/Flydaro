from app.services.settlement_service import (
    LANDED_REASON,
    LOST_SIGNAL_REASON,
    TIMEOUT_REASON,
    compute_settlement,
)


def test_short_hop_bucket_multiplier():
    settlement, breakdown = compute_settlement(100, duration_minutes=30, item_settlement_multiplier=1.0, resolution_reason=LANDED_REASON)
    assert breakdown["base_multiplier"] == 1.2
    assert settlement == 120


def test_standard_bucket_multiplier():
    settlement, breakdown = compute_settlement(100, duration_minutes=120, item_settlement_multiplier=1.0, resolution_reason=LANDED_REASON)
    assert breakdown["base_multiplier"] == 1.5
    assert settlement == 150


def test_long_haul_bucket_multiplier():
    settlement, breakdown = compute_settlement(100, duration_minutes=400, item_settlement_multiplier=1.0, resolution_reason=LANDED_REASON)
    assert breakdown["base_multiplier"] == 2.0
    assert settlement == 200


def test_bucket_boundaries_are_exclusive_upper_bound():
    # exactly 60 minutes should fall into the 60-180 bucket, not the <60 one
    _, breakdown_at_60 = compute_settlement(100, duration_minutes=60, item_settlement_multiplier=1.0, resolution_reason=LANDED_REASON)
    assert breakdown_at_60["base_multiplier"] == 1.5

    _, breakdown_just_under = compute_settlement(100, duration_minutes=59.9, item_settlement_multiplier=1.0, resolution_reason=LANDED_REASON)
    assert breakdown_just_under["base_multiplier"] == 1.2


def test_item_multiplier_applied_on_clean_landing():
    settlement, breakdown = compute_settlement(100, duration_minutes=30, item_settlement_multiplier=1.75, resolution_reason=LANDED_REASON)
    assert settlement == round(100 * 1.2 * 1.75)
    assert breakdown["item_multiplier"] == 1.75


def test_fallback_ignores_item_multiplier_and_duration():
    settlement_timeout, breakdown_timeout = compute_settlement(
        100, duration_minutes=999, item_settlement_multiplier=1.75, resolution_reason=TIMEOUT_REASON
    )
    settlement_lost_signal, breakdown_lost_signal = compute_settlement(
        100, duration_minutes=5, item_settlement_multiplier=1.75, resolution_reason=LOST_SIGNAL_REASON
    )
    assert settlement_timeout == settlement_lost_signal == 105
    assert breakdown_timeout["item_multiplier"] is None
    assert breakdown_lost_signal["item_multiplier"] is None


def test_fallback_settlement_always_worse_than_any_clean_landing_bucket():
    fallback_settlement, _ = compute_settlement(100, duration_minutes=1, item_settlement_multiplier=1.0, resolution_reason=TIMEOUT_REASON)
    cheapest_clean_landing_settlement, _ = compute_settlement(
        100, duration_minutes=1, item_settlement_multiplier=1.0, resolution_reason=LANDED_REASON
    )
    assert fallback_settlement < cheapest_clean_landing_settlement


def test_settlement_never_zero_or_negative():
    settlement, _ = compute_settlement(1, duration_minutes=0, item_settlement_multiplier=0.01, resolution_reason=LANDED_REASON)
    assert settlement >= 1
