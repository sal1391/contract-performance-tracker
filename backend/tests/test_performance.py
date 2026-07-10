from datetime import date

from app.services.performance import compute_risk

START = date(2026, 1, 1)
END = date(2026, 12, 31)


def test_on_track_when_pace_meets_commitment():
    # ~50% elapsed, ~50% of volume lifted -> projects to full
    r = compute_risk(1000, 500, START, END, date(2026, 7, 2))
    assert r.status == "ON_TRACK"


def test_at_risk_when_well_behind_pace():
    # ~50% elapsed but only 200/1000 lifted -> projects ~400, below 900 floor
    r = compute_risk(1000, 200, START, END, date(2026, 7, 2))
    assert r.status == "AT_RISK"


def test_watch_just_below_commitment():
    # ~50% elapsed, 460 lifted -> projects ~920, between lower bound (900) and 1000
    r = compute_risk(1000, 460, START, END, date(2026, 7, 2))
    assert r.status == "WATCH"


def test_ahead_when_over_committed():
    r = compute_risk(1000, 1100, START, END, date(2026, 7, 2))
    assert r.status == "AHEAD"


def test_complete_after_end():
    r = compute_risk(1000, 800, START, END, date(2027, 1, 5))
    assert r.status == "COMPLETE"
