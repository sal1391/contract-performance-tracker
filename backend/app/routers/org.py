"""Org-tree + user administration (ADMIN only).

Manage the org hierarchy (Company → Segment → Region → Office) and app users, including each
user's `scope_unit_id` (what they can see) and `home_office_id` (where their bids land). Every
mutation to the tree rebuilds `org_closure` so the RLS subtree lookups stay correct.

In prod these are gated to the ADMIN role. In local dev the default identity is ADMIN, so the
React Admin page works as-is; while you're impersonating a non-admin via the act-as switch these
endpoints correctly return 403.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import ScopeContext, get_current_user, get_scope
from app.db import get_db
from app.models import AppUser, BidLine, Contract, OrgUnit
from app.schemas import (
    ROLE_LEVELS, UNIT_TYPES, AppUserCreate, AppUserRead, AppUserUpdate,
    BrokerOption, OrgUnitCreate, OrgUnitMerge, OrgUnitRead, OrgUnitUpdate, SyncResult,
)
from app.services.org import rebuild_closure
from app.services.org_sync import sync_org_from_sales_planning

router = APIRouter(prefix="/org", tags=["org"])


def require_admin(scope: ScopeContext = Depends(get_scope)) -> ScopeContext:
    if not scope.is_admin:
        raise HTTPException(403, "Admin only")
    return scope


# ----------------------------------------------------------------------------- org units
@router.get("/units", response_model=list[OrgUnitRead])
def list_units(db: Session = Depends(get_db), _: ScopeContext = Depends(require_admin)):
    return db.scalars(select(OrgUnit).order_by(OrgUnit.unit_type, OrgUnit.name)).all()


@router.get("/offices", response_model=list[OrgUnitRead])
def list_offices(db: Session = Depends(get_db), _: ScopeContext = Depends(require_admin)):
    """Active offices — what a new bid can be assigned to."""
    return db.scalars(
        select(OrgUnit).where(OrgUnit.unit_type == "OFFICE", OrgUnit.is_active.is_(True))
        .order_by(OrgUnit.name)
    ).all()


@router.post("/units", response_model=OrgUnitRead, status_code=201)
def create_unit(payload: OrgUnitCreate, db: Session = Depends(get_db),
                _: ScopeContext = Depends(require_admin)):
    if payload.unit_type not in UNIT_TYPES:
        raise HTTPException(422, f"unit_type must be one of {UNIT_TYPES}")
    unit = OrgUnit(**payload.model_dump())
    db.add(unit)
    db.commit()
    db.refresh(unit)
    rebuild_closure(db)
    return unit


@router.patch("/units/{unit_id}", response_model=OrgUnitRead)
def update_unit(unit_id: str, payload: OrgUnitUpdate, db: Session = Depends(get_db),
                _: ScopeContext = Depends(require_admin)):
    unit = db.get(OrgUnit, unit_id)
    if unit is None:
        raise HTTPException(404, "Org unit not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("unit_type") and data["unit_type"] not in UNIT_TYPES:
        raise HTTPException(422, f"unit_type must be one of {UNIT_TYPES}")
    if str(data.get("parent_id")) == unit_id:
        raise HTTPException(422, "A unit cannot be its own parent")
    for k, v in data.items():
        setattr(unit, k, v)
    db.commit()
    db.refresh(unit)
    rebuild_closure(db)   # parent change re-shapes the subtree
    return unit


@router.delete("/units/{unit_id}", status_code=204)
def delete_unit(unit_id: str, db: Session = Depends(get_db),
                _: ScopeContext = Depends(require_admin)):
    unit = db.get(OrgUnit, unit_id)
    if unit is None:
        raise HTTPException(404, "Org unit not found")
    if db.scalar(select(OrgUnit.id).where(OrgUnit.parent_id == unit_id)):
        raise HTTPException(409, "Remove or re-parent child units first")
    db.delete(unit)
    db.commit()
    rebuild_closure(db)


@router.post("/closure/rebuild")
def rebuild(db: Session = Depends(get_db), _: ScopeContext = Depends(require_admin)):
    """Force a closure rebuild (e.g. after editing org units via /admin)."""
    return {"rows": rebuild_closure(db)}


# ----------------------------------------------------------------------------- users
@router.get("/users", response_model=list[AppUserRead])
def list_users(db: Session = Depends(get_db), _: ScopeContext = Depends(require_admin)):
    return db.scalars(select(AppUser).order_by(AppUser.email)).all()


@router.post("/users", response_model=AppUserRead, status_code=201)
def create_user(payload: AppUserCreate, db: Session = Depends(get_db),
                _: ScopeContext = Depends(require_admin)):
    if payload.role_level not in ROLE_LEVELS:
        raise HTTPException(422, f"role_level must be one of {ROLE_LEVELS}")
    data = payload.model_dump()
    data["auth0_sub"] = data.get("auth0_sub") or f"dev|{payload.email}"
    user = AppUser(**data)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"A user with email '{payload.email}' already exists")
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=AppUserRead)
def update_user(user_id: str, payload: AppUserUpdate, db: Session = Depends(get_db),
                _: ScopeContext = Depends(require_admin)):
    user = db.get(AppUser, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("role_level") and data["role_level"] not in ROLE_LEVELS:
        raise HTTPException(422, f"role_level must be one of {ROLE_LEVELS}")
    for k, v in data.items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return user


@router.post("/sync", response_model=SyncResult)
def run_sync(db: Session = Depends(get_db), _: ScopeContext = Depends(require_admin)):
    """Provision org/users from sales planning. Stub-skips without Snowflake (dev)."""
    try:
        return SyncResult(status="ok", **sync_org_from_sales_planning(db, sf_conn=None))
    except (RuntimeError, NotImplementedError) as exc:
        return SyncResult(status="skipped", reason=str(exc))


@router.post("/units/{unit_id}/verify", response_model=OrgUnitRead)
def verify_unit(unit_id: str, db: Session = Depends(get_db),
                _: ScopeContext = Depends(require_admin)):
    unit = db.get(OrgUnit, unit_id)
    if unit is None:
        raise HTTPException(404, "Org unit not found")
    unit.is_verified = True
    db.commit()
    db.refresh(unit)
    return unit


@router.post("/units/{unit_id}/merge", status_code=204)
def merge_unit(unit_id: str, payload: OrgUnitMerge, db: Session = Depends(get_db),
               _: ScopeContext = Depends(require_admin)):
    """Repoint everything from `unit_id` onto `into_id`, delete the source, rebuild closure."""
    src = db.get(OrgUnit, unit_id)
    dst = db.get(OrgUnit, str(payload.into_id))
    if src is None or dst is None:
        raise HTTPException(404, "Org unit not found")
    if str(src.id) == str(dst.id):
        raise HTTPException(422, "Cannot merge a unit into itself")
    db.execute(update(OrgUnit).where(OrgUnit.parent_id == src.id).values(parent_id=dst.id))
    db.execute(update(AppUser).where(AppUser.home_office_id == src.id).values(home_office_id=dst.id))
    db.execute(update(AppUser).where(AppUser.scope_unit_id == src.id).values(scope_unit_id=dst.id))
    db.execute(update(Contract).where(Contract.office_id == src.id).values(office_id=dst.id))
    db.execute(update(BidLine).where(BidLine.office_id == src.id).values(office_id=dst.id))
    db.delete(src)
    db.commit()
    rebuild_closure(db)


@router.get("/brokers", response_model=list[BrokerOption])
def list_brokers(db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Active users for the bid-line Customer broker dropdown (available to any authed user)."""
    return db.scalars(select(AppUser).where(AppUser.is_active.is_(True))
                      .order_by(AppUser.display_name)).all()
