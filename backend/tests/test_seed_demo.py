"""Pure-logic tests for the demo seeder: the generated actuals must land each
bid line on its target bid_line_performance risk status, for any 'today'."""
from datetime import date, timedelta

from scripts.seed_demo import (
    elapsed_pct, expected_status, lift_schedule, target_actual,
)

TODAY = date(2026, 7, 10)  # tests pin 'today'; production code uses date.today()


def test_elapsed_pct_clamps_and_divides():
    s, e = TODAY - timedelta(days=100), TODAY + timedelta(days=100)
    assert elapsed_pct(s, e, TODAY) == 0.5
    assert elapsed_pct(TODAY + timedelta(days=5), e, TODAY) == 0.0
    assert elapsed_pct(s, TODAY - timedelta(days=1), TODAY) == 1.0


def test_lift_schedule_sums_exactly_and_stays_in_window():
    s, e = TODAY - timedelta(days=200), TODAY + timedelta(days=165)
    sched = lift_schedule(s, e, TODAY, 3617.0)
    assert round(sum(t for _, t in sched), 1) == 3617.0
    assert all(s <= d <= min(TODAY, e) for d, _ in sched)
    assert 2 <= len(sched) <= 6


def test_lift_schedule_empty_for_zero_tons():
    assert lift_schedule(TODAY + timedelta(days=45), TODAY + timedelta(days=410), TODAY, 0.0) == []


def test_target_actual_hits_every_status():
    cases = [
        ("ON_TRACK", 200, 165), ("WATCH", 180, 185), ("AT_RISK", 220, 145),
        ("AHEAD", 240, 125), ("COMPLETE", 390, -25),
    ]
    for status, back, ahead in cases:
        s, e = TODAY - timedelta(days=back), TODAY + timedelta(days=ahead)
        actual = target_actual(5000.0, status, s, e, TODAY)
        assert expected_status(5000.0, actual, s, e, TODAY) == status, status


def test_on_track_near_contract_end_stays_on_track():
    # elapsed 0.95 > 1/1.10 — without the cap this would read AHEAD.
    s, e = TODAY - timedelta(days=342), TODAY + timedelta(days=18)
    actual = target_actual(5000.0, "ON_TRACK", s, e, TODAY)
    assert actual <= 5000.0
    assert expected_status(5000.0, actual, s, e, TODAY) == "ON_TRACK"


def test_future_line_reads_on_track_with_no_lifts():
    s, e = TODAY + timedelta(days=45), TODAY + timedelta(days=410)
    assert target_actual(3000.0, "FUTURE", s, e, TODAY) == 0.0
    assert expected_status(3000.0, 0.0, s, e, TODAY) == "ON_TRACK"


def test_schedule_total_preserves_status_after_split():
    # Splitting into lifts must not shift the status (rounding drift check).
    for status, back, ahead in [("WATCH", 180, 185), ("AT_RISK", 220, 145)]:
        s, e = TODAY - timedelta(days=back), TODAY + timedelta(days=ahead)
        total = target_actual(4000.0, status, s, e, TODAY)
        summed = sum(t for _, t in lift_schedule(s, e, TODAY, total))
        assert expected_status(4000.0, summed, s, e, TODAY) == status, status
