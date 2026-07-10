"""At-risk / performance computation (pure logic, mirrors the bid_line_performance SQL view).

Kept DB-free so the risk rule is unit-testable and documented in one place. The SQL view in
COCO_BUILD_SPEC.md Part G is the production path; this function is the canonical definition the
dashboard and tests agree on.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class Risk:
    status: str            # COMPLETE | AHEAD | ON_TRACK | WATCH | AT_RISK
    elapsed_pct: float
    projected_final: float | None


def compute_risk(contracted_volume: float, actual_to_date: float,
                 start: date, end: date, today: date,
                 tolerance_pct: float = 0.10) -> Risk:
    if end < start:
        return Risk("AT_RISK", 0.0, None)
    span = (end - start).days
    elapsed_days = (today - start).days
    elapsed_pct = max(0.0, min(1.0, elapsed_days / span if span else 1.0))

    if today > end:
        return Risk("COMPLETE", elapsed_pct, actual_to_date)
    if actual_to_date > contracted_volume:
        return Risk("AHEAD", elapsed_pct, actual_to_date)
    if elapsed_pct <= 0:
        return Risk("ON_TRACK", elapsed_pct, None)

    projected_final = actual_to_date / elapsed_pct
    lower_bound = contracted_volume * (1 - tolerance_pct)
    if projected_final >= contracted_volume:
        status = "ON_TRACK"
    elif projected_final >= lower_bound:
        status = "WATCH"
    else:
        status = "AT_RISK"
    return Risk(status, elapsed_pct, projected_final)
