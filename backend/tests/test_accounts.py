from app.services.accounts import summary_from_row, win_rate


def test_win_rate_no_decided_lines_is_none():
    assert win_rate(0, 0) is None


def test_win_rate_all_won():
    assert win_rate(3, 0) == 1.0


def test_win_rate_half():
    assert win_rate(1, 1) == 0.5


def test_win_rate_quarter_pending_excluded():
    # 2 won, 6 lost -> 2/8; PENDING never enters the helper
    assert win_rate(2, 6) == 0.25


ROW = {
    "customer_group_number": "C100",
    "customer_group_name": "Carnival",
    "contract_count": 4,
    "line_count": 18,
    "gp_won": 1200000,
    "gp_pending": 220000,
    "gp_lost": 80000,
    "won_lines": 6,
    "lost_lines": 2,
    "volume_won": 50000,
    "volume_pending": 12000,
}


def test_summary_from_row_shapes_and_win_rate():
    out = summary_from_row(ROW)
    assert out == {
        "customer_group_number": "C100",
        "customer_group_name": "Carnival",
        "contract_count": 4,
        "line_count": 18,
        "gp_won": 1200000.0,
        "gp_pending": 220000.0,
        "gp_lost": 80000.0,
        "win_rate": 0.75,
        "volume_won": 50000.0,
        "volume_pending": 12000.0,
    }
    assert isinstance(out["gp_won"], float)
    assert "won_lines" not in out  # intermediate fields dropped


def test_summary_from_row_win_rate_none_when_undecided():
    row = {**ROW, "won_lines": 0, "lost_lines": 0}
    assert summary_from_row(row)["win_rate"] is None
