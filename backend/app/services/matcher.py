"""
LIFT -> bid_line auto-matcher (pure logic, DB-free so it is unit-testable).

A LIFT auto-matches a bid line when ALL hard keys agree and the lift date falls inside
the contract window. Grade is matched "loosely" (exact OR same grade-group); a grade
mismatch is NOT auto-mapped but a user may still map it manually (USER_ADDED).

See docs/snowflake/COCO_BUILD_SPEC.md Part C and the design decision log (#7, #10).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Lift:
    lift_id: str
    customer_group_number: str
    supplier_number: str | None
    port: str
    grade: str | None
    lift_date: date
    volume_tons: float = 0.0
    gp: float = 0.0


@dataclass(frozen=True)
class BidLine:
    id: str
    customer_group_number: str
    supplier_number: str | None
    port: str
    grade: str | None
    contract_start: date
    contract_end: date


@dataclass(frozen=True)
class MatchSuggestion:
    lift_id: str
    bid_line_id: str
    score: float  # 0..100 confidence


def grade_matches(lift_grade: str | None, line_grade: str | None,
                  grade_groups: dict[str, str] | None = None) -> bool:
    """Loose grade equality: exact, or same grade-group when a grouping is provided."""
    if lift_grade is None or line_grade is None:
        return False
    if lift_grade == line_grade:
        return True
    if grade_groups:
        g_lift = grade_groups.get(lift_grade)
        g_line = grade_groups.get(line_grade)
        return g_lift is not None and g_lift == g_line
    return False


def is_auto_match(lift: Lift, line: BidLine,
                  grade_groups: dict[str, str] | None = None) -> bool:
    """True when the LIFT should be AUTO_SUGGESTED for this bid line."""
    if lift.customer_group_number != line.customer_group_number:
        return False
    # Supplier is only enforced when the line names a supplier.
    if line.supplier_number and lift.supplier_number != line.supplier_number:
        return False
    if lift.port != line.port:                       # port is the grain — exact
        return False
    if not (line.contract_start <= lift.lift_date <= line.contract_end):
        return False
    if not grade_matches(lift.grade, line.grade, grade_groups):
        return False
    return True


def match_score(lift: Lift, line: BidLine,
                grade_groups: dict[str, str] | None = None) -> float:
    """Confidence 0..100: exact grade + supplier raises it; loose grade lowers it."""
    score = 60.0
    if line.supplier_number and lift.supplier_number == line.supplier_number:
        score += 20.0
    if lift.grade is not None and lift.grade == line.grade:
        score += 20.0
    elif grade_matches(lift.grade, line.grade, grade_groups):
        score += 10.0
    return min(score, 100.0)


def suggest_matches(lifts: list[Lift], lines: list[BidLine],
                    grade_groups: dict[str, str] | None = None) -> list[MatchSuggestion]:
    """
    Return AUTO_SUGGESTED (lift -> bid_line) pairs. A LIFT may match more than one line
    (e.g. overlapping windows); the caller / human resolves ambiguity in the mapping grid.
    """
    out: list[MatchSuggestion] = []
    for lift in lifts:
        for line in lines:
            if is_auto_match(lift, line, grade_groups):
                out.append(MatchSuggestion(lift.lift_id, line.id,
                                           match_score(lift, line, grade_groups)))
    return out
