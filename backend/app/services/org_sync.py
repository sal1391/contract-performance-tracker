"""Org provisioning from sales planning (pure planners + DB apply + Snowflake stub).

The planners are DB-free so they are unit-testable (mirrors app/rls.py). The DB apply and the
Snowflake read are thin wrappers; the read is a stub that raises without a connection, like
services/intake.py and services/matcher_runner.py.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from app.models import AppUser, OrgUnit
from app.services.org import rebuild_closure


@dataclass(frozen=True)
class BrokerRow:
    customer_broker_number: str
    customer_broker_name: str
    region: str | None
    office: str
    email: str | None


@dataclass(frozen=True)
class UnitCreate:
    name: str
    unit_type: str       # "REGION" | "OFFICE"
    parent_name: str


def plan_unit_creates(rows, existing_unit_names, segment_name="Fuel Contracts"):
    """Org units missing from the tree, regions first so offices can reference them.
    An office with no region parks directly under the segment (Cruise/Yacht style)."""
    seen = set(existing_unit_names)
    creates: list[UnitCreate] = []
    for r in rows:
        if r.region and r.region not in seen:
            creates.append(UnitCreate(r.region, "REGION", segment_name))
            seen.add(r.region)
    for r in rows:
        if r.office and r.office not in seen:
            parent = r.region if r.region else segment_name
            creates.append(UnitCreate(r.office, "OFFICE", parent))
            seen.add(r.office)
    return creates


def plan_user_upserts(rows, existing, office_id_by_name):
    """Per-broker create/update actions. Match on source_broker_id, so MANUAL users (which have
    none) are never touched. role_locked users keep their role/scope (no scope_unit_id emitted)."""
    by_broker = {u["source_broker_id"]: u for u in existing if u.get("source_broker_id")}
    actions: list[dict] = []
    for r in rows:
        office_id = office_id_by_name.get(r.office)
        cur = by_broker.get(r.customer_broker_number)
        if cur is None:
            actions.append({
                "action": "create", "source_broker_id": r.customer_broker_number,
                "display_name": r.customer_broker_name, "email": r.email,
                "home_office_id": office_id, "role_level": "IC", "scope_unit_id": office_id,
            })
        else:
            a = {
                "action": "update", "id": cur["id"],
                "source_broker_id": r.customer_broker_number,
                "display_name": r.customer_broker_name, "email": r.email,
                "home_office_id": office_id,
            }
            if not cur.get("role_locked"):
                a["scope_unit_id"] = office_id
            actions.append(a)
    return actions


def resolve_office_id(quickbase_office, office_id_by_name):
    """Map a QuickBase office label to an org_unit office id (the contract's classification)."""
    if not quickbase_office:
        return None
    return office_id_by_name.get(quickbase_office.strip())


def apply_org_sync(db, rows):
    """Provision org units + broker users from BrokerRows against the live DB. The Fuel Contracts segment must exist."""
    units = {u.name: u for u in db.scalars(select(OrgUnit))}
    if "Fuel Contracts" not in units:
        raise RuntimeError("Seed the Fuel Contracts segment before syncing (run scripts.init_db).")
    creates = plan_unit_creates(rows, set(units))
    for c in creates:
        unit = OrgUnit(name=c.name, unit_type=c.unit_type,
                       parent_id=units[c.parent_name].id, is_verified=False)
        db.add(unit)
        db.flush()
        units[c.name] = unit
    rebuild_closure(db)  # commits

    office_ids = {u.name: str(u.id)
                  for u in db.scalars(select(OrgUnit).where(OrgUnit.unit_type == "OFFICE"))}
    existing = [{"id": str(u.id), "source_broker_id": u.source_broker_id,
                 "source": u.source, "role_locked": u.role_locked}
                for u in db.scalars(select(AppUser))]
    created = updated = 0
    for a in plan_user_upserts(rows, existing, office_ids):
        if a["action"] == "create":
            db.add(AppUser(
                email=a["email"] or f"broker-{a['source_broker_id']}@no-email.local",
                display_name=a["display_name"], role_level=a["role_level"],
                home_office_id=a["home_office_id"], scope_unit_id=a["scope_unit_id"],
                source_broker_id=a["source_broker_id"], source="SYNCED",
                auth0_sub=f"sync|{a['source_broker_id']}"))
            created += 1
        else:
            u = db.get(AppUser, a["id"])
            u.display_name = a["display_name"]
            if a.get("email"):
                u.email = a["email"]
            u.home_office_id = a["home_office_id"]
            if "scope_unit_id" in a:
                u.scope_unit_id = a["scope_unit_id"]
            updated += 1
    db.commit()
    return {"units_created": len(creates), "users_created": created, "users_updated": updated}


def sync_org_from_sales_planning(db, sf_conn=None):
    """Read SALES_ACTUALS_V (+ email mapping) -> BrokerRows -> apply_org_sync.
    Stub until Snowflake; raises like services/intake.py."""
    if sf_conn is None:
        raise RuntimeError(
            "org sync needs a Snowflake connection; run on the Snowflake-connected machine.")
    # TODO(coco): rows = SELECT customer_broker_number, customer_broker_name, region, office
    #   FROM SALES_ACTUALS_V  (segment defaults to 'Fuel Contracts' — implied by the source table)
    #   LEFT JOIN <email_mapping> ON sales_rep_number = customer_broker_number  -> email
    #   build [BrokerRow(...)] and call apply_org_sync(db, rows)
    raise NotImplementedError("Implement the sales-planning read on the connected machine.")
