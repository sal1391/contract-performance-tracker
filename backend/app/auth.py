"""Authentication (Auth0 JWT) + scope resolution.

Local dev (AUTH0_ENABLED=false): auth is bypassed with a dev ADMIN user so you can build the
UI without an IdP. Prod: validate the RS256 JWT against the Auth0 JWKS and read custom claims
(`segment`, `role_level`) from the configured namespace.

Scope resolution turns the authenticated user into the set of visible office ids (the RLS rule).
"""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from functools import lru_cache

from fastapi import Depends, Header, HTTPException, status
from jose import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import AppUser, OrgClosure

settings = get_settings()


@dataclass
class CurrentUser:
    sub: str
    email: str
    role_level: str = "IC"
    segment: str | None = None


@dataclass
class ScopeContext:
    user: CurrentUser
    app_user_id: str | None
    scope_unit_id: str | None
    visible_office_ids: set[str] = field(default_factory=set)
    home_office_id: str | None = None   # where this user's new bids land (for office stamping)

    @property
    def sees_everything(self) -> bool:
        return self.user.role_level.upper() in ("LEADERSHIP", "ADMIN")

    @property
    def is_admin(self) -> bool:
        return self.user.role_level.upper() == "ADMIN"


@lru_cache
def _jwks() -> dict:
    url = f"https://{settings.auth0_domain}/.well-known/jwks.json"
    with urllib.request.urlopen(url, timeout=5) as r:   # noqa: S310 (trusted Auth0 URL)
        return json.load(r)


def _verify_jwt(token: str) -> CurrentUser:
    try:
        header = jwt.get_unverified_header(token)
        key = next(k for k in _jwks()["keys"] if k["kid"] == header["kid"])
        claims = jwt.decode(
            token, key, algorithms=settings.algorithms_list,
            audience=settings.auth0_audience,
            issuer=f"https://{settings.auth0_domain}/",
        )
    except Exception as exc:                              # noqa: BLE001
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc
    ns = settings.auth0_claims_namespace
    return CurrentUser(
        sub=claims["sub"],
        email=claims.get(f"{ns}email", claims.get("email", "")),
        role_level=claims.get(f"{ns}role_level", "IC"),
        segment=claims.get(f"{ns}segment"),
    )


def _resolve_dev_user(db: Session, ident: str) -> AppUser | None:
    """Look up an app_user by id (uuid) or email — backs the dev 'act as user' switch."""
    user = None
    try:
        user = db.get(AppUser, ident)
    except Exception:  # noqa: BLE001 — not a uuid; fall through to email lookup
        db.rollback()
    return user or db.scalar(select(AppUser).where(AppUser.email == ident))


def get_current_user(
    authorization: str | None = Header(default=None),
    x_dev_user: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if not settings.auth0_enabled:
        # Dev "act as user": impersonate a seeded user so cruise/region/segment/leadership
        # visibility can be tested without Auth0. No header => the see-all dev ADMIN.
        if x_dev_user:
            u = _resolve_dev_user(db, x_dev_user)
            if u is not None:
                return CurrentUser(sub=u.auth0_sub, email=u.email, role_level=u.role_level)
        return CurrentUser(sub="dev|local", email="dev@local", role_level="ADMIN")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    return _verify_jwt(authorization.split(" ", 1)[1])


def get_scope(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScopeContext:
    """Resolve the authenticated user to their visible office ids (the org-subtree RLS set)."""
    app_user = db.scalar(select(AppUser).where(AppUser.auth0_sub == user.sub))
    home_office_id = str(app_user.home_office_id) if app_user and app_user.home_office_id else None

    # Leadership/Admin (or the dev user) see everything.
    if user.role_level.upper() in ("LEADERSHIP", "ADMIN"):
        return ScopeContext(user, str(app_user.id) if app_user else None, None,
                            visible_office_ids=set(),  # empty set => caller treats as "all"
                            home_office_id=home_office_id)

    if app_user is None or app_user.scope_unit_id is None:
        # Authenticated but unassigned -> sees nothing until an admin assigns them.
        return ScopeContext(user, str(app_user.id) if app_user else None, None, set(),
                            home_office_id=home_office_id)

    rows = db.execute(
        select(OrgClosure.descendant_id).where(OrgClosure.ancestor_id == app_user.scope_unit_id)
    ).all()
    visible = {str(r[0]) for r in rows}
    return ScopeContext(user, str(app_user.id), str(app_user.scope_unit_id), visible,
                        home_office_id=home_office_id)
