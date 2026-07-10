"""LIFT -> bid_line mapping grid actions: confirm / exclude (unmap) / add manual.
The auto-matcher only writes AUTO_SUGGESTED; humans drive the rest here."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import ScopeContext, get_scope
from app.db import get_db
from app.models import LiftContractMap, LiftSource
from app.schemas import MappingCreate, LiftMapRead

router = APIRouter(prefix="/mappings", tags=["mapping"])


def _get(db: Session, map_id: str) -> LiftContractMap:
    m = db.get(LiftContractMap, map_id)
    if m is None:
        raise HTTPException(404, "Mapping not found")
    return m


@router.get("/by-line/{bid_line_id}", response_model=list[LiftMapRead])
def list_for_line(bid_line_id: str, db: Session = Depends(get_db),
                  scope: ScopeContext = Depends(get_scope)):
    return db.scalars(
        select(LiftContractMap).where(LiftContractMap.bid_line_id == bid_line_id)
    ).all()


@router.post("/{map_id}/confirm", response_model=LiftMapRead)
def confirm(map_id: str, db: Session = Depends(get_db),
            scope: ScopeContext = Depends(get_scope)):
    m = _get(db, map_id)
    m.status = "CONFIRMED"
    m.mapped_by = scope.app_user_id
    m.mapped_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(m)
    return m


@router.post("/{map_id}/exclude", response_model=LiftMapRead)
def exclude(map_id: str, reason: str | None = None, db: Session = Depends(get_db),
            scope: ScopeContext = Depends(get_scope)):
    m = _get(db, map_id)
    m.status = "EXCLUDED"
    m.override_reason = reason
    m.mapped_by = scope.app_user_id
    m.mapped_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(m)
    return m


@router.post("", response_model=LiftMapRead, status_code=201)
def add_manual(payload: MappingCreate, db: Session = Depends(get_db),
               scope: ScopeContext = Depends(get_scope)):
    # copy the LIFT's facts so performance/risk counts this manual mapping
    lift = db.get(LiftSource, payload.lift_id)
    m = LiftContractMap(
        bid_line_id=payload.bid_line_id, lift_id=payload.lift_id,
        status="USER_ADDED", override_reason=payload.override_reason,
        lift_lift_date=lift.lift_date if lift else None,
        lift_volume_tons=lift.volume_tons if lift else None,
        lift_gp=lift.gp if lift else None,
        mapped_by=scope.app_user_id, mapped_at=datetime.now(timezone.utc),
    )
    db.add(m); db.commit(); db.refresh(m)
    return m
