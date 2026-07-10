"""Deterministic demo-data seeder, anchored to date.today().

Generates 6 contracts / 12 bid lines / ~55 lifts engineered so the dashboard
shows every risk status (bid_line_performance view) no matter when it runs.
Pure math lives up top (unit-tested); DB writing (seed_demo) is added in a
follow-up task. Idempotent: skips if any contract exists.

Run (from backend/, Postgres up):  python -m scripts.seed_demo
"""
from __future__ import annotations

from datetime import date, timedelta

TOL = 0.10  # mirrors BidLine.tolerance_pct default
# Pace multiplier per target status; see PERF_VIEW_SQL in scripts/init_db.py.
# ON_TRACK needs pace >= 1.0; WATCH in [1-TOL, 1.0); AT_RISK below 1-TOL.
PACE = {"ON_TRACK": 1.10, "WATCH": 0.95, "AT_RISK": 0.55}


def elapsed_pct(start: date, end: date, today: date) -> float:
    """Mirror of the SQL view: (today-start)/(end-start) clamped to 0..1."""
    total = (end - start).days
    if total <= 0:
        return 1.0
    return max(0.0, min(1.0, (today - start).days / total))


def target_actual(contracted: float, status: str, start: date, end: date, today: date) -> float:
    """Total lifted tons that make a line show `status` on the dashboard today."""
    if status == "FUTURE":
        return 0.0
    if status == "COMPLETE":
        return round(contracted * 0.97, 1)
    if status == "AHEAD":
        return round(contracted * 1.06, 1)
    return round(contracted * elapsed_pct(start, end, today) * PACE[status], 1)


def lift_schedule(start: date, end: date, today: date, total_tons: float) -> list[tuple[date, float]]:
    """Split total_tons over 2-6 lifts between start and min(today, end), ~45-day
    cadence, deterministic ±8% size variation, sum exactly total_tons."""
    if total_tons <= 0:
        return []
    last = min(today, end)
    days = max((last - start).days, 1)
    n = min(6, max(2, days // 45))
    step = days // n
    dates = [start + timedelta(days=step // 2 + i * step) for i in range(n)]
    weights = [1 + 0.08 * ((i % 3) - 1) for i in range(n)]  # 0.92, 1.00, 1.08, ...
    wsum = sum(weights)
    tons = [round(total_tons * w / wsum, 1) for w in weights]
    tons[-1] = round(tons[-1] + (total_tons - sum(tons)), 1)  # absorb rounding drift
    return list(zip(dates, tons))


def expected_status(contracted: float, actual: float, start: date, end: date,
                    today: date, tol: float = TOL) -> str:
    """Python mirror of the view's risk_status CASE — used by tests and the self-check."""
    if end < today:
        return "COMPLETE"
    if actual > contracted:
        return "AHEAD"
    if (today - start).days <= 0:
        return "ON_TRACK"
    pace = actual / elapsed_pct(start, end, today)
    if pace >= contracted:
        return "ON_TRACK"
    if pace >= contracted * (1 - tol):
        return "WATCH"
    return "AT_RISK"
