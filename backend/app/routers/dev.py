"""Dev-only endpoints backing the 'act as user' switch.

These exist ONLY when Auth0 is disabled (local dev). They are intentionally ungated so the
switcher can list users and switch back to ADMIN even while you are impersonating a non-admin
user (whom the /org admin endpoints would 403). Returns 404 when auth is enabled.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import AppUser
from app.schemas import DevUser

router = APIRouter(prefix="/dev", tags=["dev"])
settings = get_settings()


@router.get("/users", response_model=list[DevUser])
def dev_users(db: Session = Depends(get_db)):
    if settings.auth0_enabled:
        raise HTTPException(404, "Not available when Auth0 is enabled")
    return db.scalars(select(AppUser).where(AppUser.is_active.is_(True))
                      .order_by(AppUser.role_level, AppUser.email)).all()
