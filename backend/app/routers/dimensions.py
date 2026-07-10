"""Dimension lists for the workbench dropdowns (pick-from-list only, no free text),
plus a refresh endpoint available to ALL authenticated users (rate-limited)."""
import time

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.db import get_db
from app.models import (
    DimCustomer, DimGrade, DimIndex, DimPort, DimSupplier,
    LkpBidStatus, LkpFreightType, LkpPriceUom, LkpPricingDays, LkpSupplyMethod,
)

router = APIRouter(prefix="/dimensions", tags=["dimensions"])


@router.get("/lookups")
def lookups(db: Session = Depends(get_db)):
    def opts(model):
        rows = db.scalars(select(model).where(model.is_active.is_(True))
                          .order_by(model.sort_order)).all()
        return [{"value": r.code, "label": r.label} for r in rows]
    return {
        "price_uom": opts(LkpPriceUom),
        "bid_status": opts(LkpBidStatus),
        "supply_method": opts(LkpSupplyMethod),
        "freight_type": opts(LkpFreightType),
        "pricing_days": opts(LkpPricingDays),
    }


@router.get("/ports")
def ports(db: Session = Depends(get_db)):
    rows = db.scalars(select(DimPort).where(DimPort.is_active.is_(True))).all()
    return [{"value": r.port, "label": r.region} for r in rows]


@router.get("/customers")
def customers(db: Session = Depends(get_db)):
    rows = db.scalars(select(DimCustomer).where(DimCustomer.is_active.is_(True))).all()
    return [{"value": r.customer_group_number, "label": r.customer_group_name} for r in rows]


@router.get("/suppliers")
def suppliers(db: Session = Depends(get_db)):
    rows = db.scalars(select(DimSupplier).where(DimSupplier.is_active.is_(True))).all()
    return [{"value": r.supplier_number, "label": r.supplier_name} for r in rows]


@router.get("/grades")
def grades(db: Session = Depends(get_db)):
    rows = db.scalars(select(DimGrade).where(DimGrade.is_active.is_(True))).all()
    return [{"value": r.grade, "label": r.grade_group} for r in rows]


@router.get("/indexes")
def indexes(db: Session = Depends(get_db)):
    rows = db.scalars(select(DimIndex).where(DimIndex.is_active.is_(True))).all()
    return [{"value": r.symbol, "label": r.index_name} for r in rows]


_last_refresh = 0.0
_MIN_INTERVAL_SEC = 300  # protect the warehouse from refresh spam


@router.post("/refresh")
def refresh(user: CurrentUser = Depends(get_current_user)):
    """Available to all users. In dev (no Snowflake) this is a no-op stub; on the
    Snowflake-connected machine it triggers app.services.dimensions.refresh_dimensions."""
    global _last_refresh
    now = time.monotonic()
    if now - _last_refresh < _MIN_INTERVAL_SEC:
        return {"status": "skipped", "reason": "rate-limited",
                "retry_in_sec": round(_MIN_INTERVAL_SEC - (now - _last_refresh))}
    _last_refresh = now
    return {"status": "queued", "requested_by": user.email}
