"""Leadership dashboard — at-risk tiles + $ GP at risk, scoped to the user's org subtree.
Reads the bid_line_performance view (COCO_BUILD_SPEC.md Part G)."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import ScopeContext, get_scope
from app.db import get_db
from app.schemas import DashboardSummary, RiskLine

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
log = logging.getLogger("contracts")

RISK_STATUSES = ("AT_RISK", "WATCH", "ON_TRACK", "AHEAD", "COMPLETE")


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db), scope: ScopeContext = Depends(get_scope)):
    where, params = "", {}
    if not scope.sees_everything:
        # empty subtree -> impossible id so an unassigned user sees nothing
        ids = list(scope.visible_office_ids) or ["00000000-0000-0000-0000-000000000000"]
        where = "WHERE bl.office_id = ANY(:ids)"
        params["ids"] = ids

    sql = text(f"""
        SELECT p.risk_status AS risk_status,
               COUNT(*)      AS n,
               COALESCE(SUM(p.contracted_gp), 0) AS gp
        FROM bid_line_performance p
        JOIN bid_line bl ON bl.id = p.bid_line_id
        {where}
        GROUP BY p.risk_status
    """)

    by_status: dict[str, int] = {}
    gp_at_risk = 0.0
    try:
        for row in db.execute(sql, params):
            by_status[row.risk_status] = row.n
            if row.risk_status in ("AT_RISK", "WATCH"):
                gp_at_risk += float(row.gp or 0)
    except SQLAlchemyError as exc:
        # bid_line_performance view not created yet (fresh DB) -> empty dashboard, not a 500
        db.rollback()
        log.warning("dashboard summary unavailable: %s", exc)
    return DashboardSummary(by_status=by_status, gp_at_risk=gp_at_risk)


@router.get("/risk-lines", response_model=list[RiskLine])
def risk_lines(status: list[str] = Query(...), db: Session = Depends(get_db),
               scope: ScopeContext = Depends(get_scope)):
    """Drill-down for a dashboard KPI: the bid lines currently at one or more risk statuses,
    with their contract context. RLS-scoped to the user's office subtree."""
    bad = [s for s in status if s not in RISK_STATUSES]
    if bad:
        raise HTTPException(400, f"status must be one of {', '.join(RISK_STATUSES)}")

    conds = ["p.risk_status = ANY(:statuses)"]
    params: dict = {"statuses": status}
    if not scope.sees_everything:
        # empty subtree -> impossible id so an unassigned user sees nothing
        params["ids"] = list(scope.visible_office_ids) or ["00000000-0000-0000-0000-000000000000"]
        conds.append("bl.office_id = ANY(:ids)")

    sql = text(f"""
        SELECT p.bid_line_id, p.contract_id, p.risk_status,
               p.contracted_volume, p.actual_volume, p.contracted_gp, p.actual_gp, p.elapsed_pct,
               bl.port, bl.grade, bl.supplier_name, bl.contract_end,
               c.contract_source_id, c.customer_group_number, c.customer_group_name
        FROM bid_line_performance p
        JOIN bid_line bl ON bl.id = p.bid_line_id
        JOIN contract c  ON c.id = bl.contract_id
        WHERE {' AND '.join(conds)}
        ORDER BY p.contracted_gp DESC NULLS LAST
        LIMIT 500
    """)
    try:
        rows = db.execute(sql, params).mappings().all()
    except SQLAlchemyError as exc:
        # bid_line_performance view not created yet (fresh DB) -> empty list, not a 500
        db.rollback()
        log.warning("dashboard risk-lines unavailable: %s", exc)
        return []
    return [RiskLine(**row) for row in rows]
