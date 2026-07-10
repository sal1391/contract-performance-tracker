"""Shared dependency helpers — the org-subtree RLS filter applied to queries."""
from __future__ import annotations

from app.auth import ScopeContext


def scoped_filter(query, office_col, scope: ScopeContext):
    """Restrict a Select to the user's visible offices (the row-level security rule).

    - Leadership/Admin: no restriction (sees everything).
    - Assigned user: office_id IN their org subtree.
    - Unassigned user: matches nothing.
    """
    if scope.sees_everything:
        return query
    if not scope.visible_office_ids:
        return query.where(office_col.in_([]))
    return query.where(office_col.in_(scope.visible_office_ids))
