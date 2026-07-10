"""CRM Accounts view — customer-centric rollups over contracts/bid lines (read-only, RLS-scoped).

An "account" is a customer (customer_group_number) with >=1 bid line the user can see. Rollups are
computed at bid-line grain (won/pending/lost via SQL FILTER) and scoped to the user's office
subtree, exactly like the rest of the app. No Snowflake / bid_line_performance dependency.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.auth import ScopeContext, get_scope
from app.db import get_db
from app.deps import scoped_filter
from app.models import BidLine, Contract
from app.schemas import AccountContract, AccountDetail, AccountLine, AccountSummary
from app.services.accounts import summary_from_row

router = APIRouter(prefix="/accounts", tags=["accounts"])

# Worst (most attention-worthy) risk first, so a contract rolls up to its riskiest line.
_RISK_PRIORITY = {"AT_RISK": 0, "WATCH": 1, "ON_TRACK": 2, "AHEAD": 3, "COMPLETE": 4}


def _worst_risk(statuses: list[str]) -> str | None:
    present = [s for s in statuses if s in _RISK_PRIORITY]
    if not present:
        return None
    return min(present, key=lambda s: _RISK_PRIORITY[s])

# One rollup row per customer. {where} is the RLS office filter (+ optional search / customer pred).
_ROLLUP = """
    SELECT c.customer_group_number AS customer_group_number,
           MAX(c.customer_group_name) AS customer_group_name,
           COUNT(DISTINCT c.id) AS contract_count,
           COUNT(bl.id) AS line_count,
           COALESCE(SUM(bl.gross_profit)      FILTER (WHERE bl.bid_status = 'WON'), 0)     AS gp_won,
           COALESCE(SUM(bl.gross_profit)      FILTER (WHERE bl.bid_status = 'PENDING'), 0) AS gp_pending,
           COALESCE(SUM(bl.gross_profit)      FILTER (WHERE bl.bid_status = 'LOST'), 0)    AS gp_lost,
           COUNT(*) FILTER (WHERE bl.bid_status = 'WON')  AS won_lines,
           COUNT(*) FILTER (WHERE bl.bid_status = 'LOST') AS lost_lines,
           COALESCE(SUM(bl.contracted_volume) FILTER (WHERE bl.bid_status = 'WON'), 0)     AS volume_won,
           COALESCE(SUM(bl.contracted_volume) FILTER (WHERE bl.bid_status = 'PENDING'), 0) AS volume_pending
    FROM bid_line bl
    JOIN contract c ON c.id = bl.contract_id
    {where}
    GROUP BY c.customer_group_number
"""


def _where(scope: ScopeContext, params: dict, extra: str = "") -> str:
    """RLS office filter (+ optional extra predicate). Mirrors routers/dashboard.py."""
    conds: list[str] = []
    if not scope.sees_everything:
        # empty subtree -> impossible id so an unassigned user sees nothing
        params["ids"] = list(scope.visible_office_ids) or ["00000000-0000-0000-0000-000000000000"]
        conds.append("bl.office_id = ANY(:ids)")
    if extra:
        conds.append(extra)
    return ("WHERE " + " AND ".join(conds)) if conds else ""


@router.get("", response_model=list[AccountSummary])
def list_accounts(q: str | None = None, db: Session = Depends(get_db),
                  scope: ScopeContext = Depends(get_scope)):
    params: dict = {}
    extra = ""
    if q:
        extra = "(c.customer_group_name ILIKE :q OR c.customer_group_number ILIKE :q)"
        params["q"] = f"%{q}%"
    sql = text(_ROLLUP.format(where=_where(scope, params, extra))
               + " ORDER BY gp_won DESC LIMIT 500")
    rows = db.execute(sql, params).mappings().all()
    return [summary_from_row(r) for r in rows]


@router.get("/{customer_group_number}", response_model=AccountDetail)
def account_detail(customer_group_number: str, db: Session = Depends(get_db),
                   scope: ScopeContext = Depends(get_scope)):
    params: dict = {"cgn": customer_group_number}
    sql = text(_ROLLUP.format(where=_where(scope, params, "c.customer_group_number = :cgn")))
    row = db.execute(sql, params).mappings().first()
    if row is None:
        raise HTTPException(404, "Account not found or not in your scope")

    line_q = scoped_filter(
        select(BidLine)
        .join(Contract, Contract.id == BidLine.contract_id)
        .where(Contract.customer_group_number == customer_group_number)
        .options(joinedload(BidLine.contract)),
        BidLine.office_id, scope,
    ).order_by(BidLine.created_at)

    by_contract: dict = {}
    for ln in db.scalars(line_q).all():
        c = ln.contract
        ac = by_contract.get(c.id)
        if ac is None:
            ac = AccountContract(id=c.id, contract_source_id=c.contract_source_id,
                                 bid_year=c.bid_year, region=c.region,
                                 source_status=c.source_status, lines=[])
            by_contract[c.id] = ac
        ac.lines.append(AccountLine(
            id=ln.id, contract_id=ln.contract_id, port=ln.port, grade=ln.grade,
            supplier_name=ln.supplier_name, bid_status=ln.bid_status,
            contracted_volume=ln.contracted_volume, gross_profit=ln.gross_profit, margin=ln.margin))

    _attach_risk(db, by_contract)

    return AccountDetail(summary=AccountSummary(**summary_from_row(row)),
                         contracts=list(by_contract.values()))


def _attach_risk(db: Session, by_contract: dict) -> None:
    """Fill each line's risk_status from bid_line_performance and roll up the worst per contract.
    The view may be missing on a fresh DB, so failure just leaves risk_status as None."""
    line_ids = [str(ln.id) for ac in by_contract.values() for ln in ac.lines]
    if not line_ids:
        return
    try:
        rows = db.execute(
            text("SELECT bid_line_id, risk_status FROM bid_line_performance "
                 "WHERE bid_line_id = ANY(:ids)"),
            {"ids": line_ids},
        ).mappings().all()
    except SQLAlchemyError:
        db.rollback()
        return
    risk_by_line = {str(r["bid_line_id"]): r["risk_status"] for r in rows}
    for ac in by_contract.values():
        for ln in ac.lines:
            ln.risk_status = risk_by_line.get(str(ln.id))
        ac.risk_status = _worst_risk([ln.risk_status for ln in ac.lines if ln.risk_status])
