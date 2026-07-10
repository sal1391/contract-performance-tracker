"""CRM Accounts rollups — pure, DB-free derived math (mirrors services/performance.py).

The SQL in routers/accounts.py does the bucketing (won/pending/lost via FILTER). This module
holds only the derived fields so they are unit-testable in isolation: the win rate and the
assembly of an AccountSummary dict from one aggregated row.
"""
from __future__ import annotations


def win_rate(won_lines: int, lost_lines: int) -> float | None:
    """Won / (Won + Lost) at bid-line grain; PENDING is excluded by the caller's bucketing.
    None when no lines are decided yet (avoids a divide-by-zero and reads as '—' in the UI)."""
    decided = won_lines + lost_lines
    return won_lines / decided if decided else None


def summary_from_row(row) -> dict:
    """Assemble an AccountSummary-shaped dict from an aggregated rollup row, computing win_rate.
    `row` may be a plain dict (tests) or a SQLAlchemy RowMapping (router) — both index by key."""
    return {
        "customer_group_number": row["customer_group_number"],
        "customer_group_name": row["customer_group_name"],
        "contract_count": int(row["contract_count"]),
        "line_count": int(row["line_count"]),
        "gp_won": float(row["gp_won"]),
        "gp_pending": float(row["gp_pending"]),
        "gp_lost": float(row["gp_lost"]),
        "win_rate": win_rate(int(row["won_lines"]), int(row["lost_lines"])),
        "volume_won": float(row["volume_won"]),
        "volume_pending": float(row["volume_pending"]),
    }
