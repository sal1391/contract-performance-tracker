from datetime import date

from app.services.matcher import (
    BidLine, Lift, grade_matches, is_auto_match, match_score, suggest_matches,
)

LINE = BidLine(
    id="L1", customer_group_number="C100", supplier_number="S9",
    port="NAPLES", grade="VLSFO",
    contract_start=date(2026, 1, 1), contract_end=date(2026, 12, 31),
)


def _lift(**kw):
    base = dict(lift_id="P1", customer_group_number="C100", supplier_number="S9",
                port="NAPLES", grade="VLSFO", lift_date=date(2026, 6, 1),
                volume_tons=500.0, gp=6000.0)
    base.update(kw)
    return Lift(**base)


def test_happy_path_auto_match():
    assert is_auto_match(_lift(), LINE) is True


def test_wrong_customer_blocks():
    assert is_auto_match(_lift(customer_group_number="C999"), LINE) is False


def test_wrong_port_blocks():            # port is the grain — exact
    assert is_auto_match(_lift(port="VENICE"), LINE) is False


def test_outside_window_blocks():
    assert is_auto_match(_lift(lift_date=date(2027, 1, 5)), LINE) is False


def test_grade_mismatch_blocks_auto_but_allows_manual():
    # HSFO LIFT vs VLSFO line: NOT auto (design example 2 -> manual USER_ADDED)
    assert is_auto_match(_lift(grade="HSFO"), LINE) is False


def test_loose_grade_via_group():
    groups = {"VLSFO": "VLSFO_FAMILY", "ULSFO": "VLSFO_FAMILY"}
    assert grade_matches("ULSFO", "VLSFO", groups) is True
    assert is_auto_match(_lift(grade="ULSFO"), LINE, grade_groups=groups) is True


def test_blank_line_supplier_does_not_block():
    line = BidLine(id="L2", customer_group_number="C100", supplier_number=None,
                   port="NAPLES", grade="VLSFO",
                   contract_start=date(2026, 1, 1), contract_end=date(2026, 12, 31))
    assert is_auto_match(_lift(supplier_number="ANYTHING"), line) is True


def test_score_exact_beats_loose():
    groups = {"VLSFO": "F", "ULSFO": "F"}
    exact = match_score(_lift(), LINE)
    loose = match_score(_lift(grade="ULSFO"), LINE, grade_groups=groups)
    assert exact == 100.0
    assert loose < exact


def test_suggest_matches_returns_pairs():
    lifts = [_lift(lift_id="P1"), _lift(lift_id="P2", port="VENICE")]
    out = suggest_matches(lifts, [LINE])
    assert {s.lift_id for s in out} == {"P1"}
