"""Candidate Lifts for the mapping screen. In dev these come from the local lift_source table;
in prod they come from Snowflake LIFTS_FOR_MATCHING_V."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import ScopeContext, get_scope
from app.db import get_db
from app.models import LiftSource
from app.schemas import LiftRead

router = APIRouter(prefix="/lifts", tags=["lifts"])


@router.get("", response_model=list[LiftRead])
def list_lifts(db: Session = Depends(get_db), scope: ScopeContext = Depends(get_scope),
              q: str | None = None):
    stmt = select(LiftSource)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(LiftSource.port.ilike(like) | LiftSource.customer_group_number.ilike(like))
    return db.scalars(stmt.order_by(LiftSource.lift_date.desc()).limit(500)).all()
