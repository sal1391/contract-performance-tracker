"""Org-tree maintenance: keep `org_closure` in sync with `org_unit`.

`org_closure` is the materialized transitive closure the RLS layer reads to resolve a user's
visible-office subtree (see `rls.visible_unit_ids` / `deps.scoped_filter`). Any change to the
org tree (add / re-parent / deactivate / delete a unit) must rebuild it. The tree is tiny
(company → segment → region → office, dozens of rows), so we recompute the whole thing — simple
and always correct — rather than maintaining it incrementally.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import OrgClosure, OrgUnit
from app.rls import compute_closure


def rebuild_closure(db: Session) -> int:
    """Recompute `org_closure` from the current `org_unit` rows. Returns the row count."""
    edges = db.execute(select(OrgUnit.id, OrgUnit.parent_id)).all()
    rows = compute_closure([(uid, pid) for uid, pid in edges])
    db.query(OrgClosure).delete()
    db.add_all([
        OrgClosure(ancestor_id=anc, descendant_id=desc, depth=depth)
        for anc, desc, depth in rows
    ])
    db.commit()
    return len(rows)
