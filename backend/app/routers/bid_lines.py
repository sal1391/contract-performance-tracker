from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import ScopeContext, get_scope
from app.db import get_db
from app.deps import scoped_filter
from app.models import BidLine, Contract
from app.schemas import BidLineCreate, BidLineRow, BidLineUpdate
from app.services.matcher_runner import run_matcher_local

router = APIRouter(prefix="/bid-lines", tags=["bid_lines"])

# lookup-backed columns: a blank dropdown must become NULL, not '' (FK violation)
_FK_FIELDS = ("price_uom", "freight_type", "pricing_days", "supply_method", "bid_status")


def _clean(data: dict) -> dict:
    """Blank FK dropdowns -> NULL; drop a null tolerance_pct so its NOT-NULL default stands."""
    for fk in _FK_FIELDS:
        if data.get(fk) == "":
            data[fk] = None
    if data.get("tolerance_pct") is None:
        data.pop("tolerance_pct", None)
    if data.get("owner_user_id") is None:
        data.pop("owner_user_id", None)
    return data


def _row(bl: BidLine, c: Contract) -> BidLineRow:
    row = BidLineRow.model_validate(bl)
    row.contract_source_id = c.contract_source_id
    row.customer_group_name = c.customer_group_name
    return row


@router.get("", response_model=list[BidLineRow])
def list_bid_lines(
    db: Session = Depends(get_db),
    scope: ScopeContext = Depends(get_scope),
    contract_id: str | None = None,
    q: str | None = Query(default=None, description="search port/supplier"),
):
    stmt = scoped_filter(select(BidLine, Contract).join(Contract, Contract.id == BidLine.contract_id),
                         BidLine.office_id, scope)
    if contract_id:
        stmt = stmt.where(BidLine.contract_id == contract_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(BidLine.port.ilike(like) | BidLine.supplier_name.ilike(like))
    rows = db.execute(stmt.order_by(BidLine.created_at.desc()).limit(500)).all()
    return [_row(bl, c) for bl, c in rows]


@router.post("", response_model=BidLineRow, status_code=201)
def create_bid_line(payload: BidLineCreate, db: Session = Depends(get_db),
                    scope: ScopeContext = Depends(get_scope)):
    """Add a bid line (port x grade x supplier) under an existing contract."""
    contract = db.get(Contract, payload.contract_id)
    if contract is None:
        raise HTTPException(404, "Contract not found")
    data = _clean(payload.model_dump())
    broker_id = data.pop("owner_user_id", None) or scope.app_user_id
    bl = BidLine(**data, office_id=contract.office_id, owner_user_id=broker_id)
    db.add(bl)
    db.commit()
    db.refresh(bl)
    return _row(bl, contract)


@router.patch("/{bid_line_id}", response_model=BidLineRow)
def update_bid_line(bid_line_id: str, payload: BidLineUpdate, db: Session = Depends(get_db),
                    scope: ScopeContext = Depends(get_scope)):
    q = scoped_filter(select(BidLine).where(BidLine.id == bid_line_id), BidLine.office_id, scope)
    bl = db.scalars(q).first()
    if bl is None:
        raise HTTPException(404, "Bid line not found or not in your scope")
    data = _clean(payload.model_dump(exclude_unset=True))
    for k, v in data.items():
        setattr(bl, k, v)
    db.commit()
    db.refresh(bl)
    return _row(bl, db.get(Contract, bl.contract_id))


@router.delete("/{bid_line_id}", status_code=204)
def delete_bid_line(bid_line_id: str, db: Session = Depends(get_db),
                    scope: ScopeContext = Depends(get_scope)):
    """Delete a bid line and (cascade) its LIFT mappings."""
    q = scoped_filter(select(BidLine).where(BidLine.id == bid_line_id), BidLine.office_id, scope)
    bl = db.scalars(q).first()
    if bl is None:
        raise HTTPException(404, "Bid line not found or not in your scope")
    db.delete(bl)
    db.commit()


@router.post("/{bid_line_id}/auto-match")
def auto_match(bid_line_id: str, db: Session = Depends(get_db),
               scope: ScopeContext = Depends(get_scope)):
    """Run the matcher for this bid line against the local LIFT source (Snowflake in prod)."""
    if db.get(BidLine, bid_line_id) is None:
        raise HTTPException(404, "Bid line not found")
    n = run_matcher_local(db, bid_line_id=bid_line_id)
    return {"suggested": n}
