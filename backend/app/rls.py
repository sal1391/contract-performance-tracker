"""
Row-level authorization (pure logic, DB-free so it is unit-testable).

The visibility rule (design decision #6): a user sees a deal when the deal's office is
within the subtree of the user's scope node. We resolve the set of visible office ids from
the org closure table, then the data layer filters every query with:

    WHERE office_id IN (visible office ids)

Levels and their scope node:
    IC / OFFICE_MANAGER -> their Office
    REGIONAL_DIRECTOR   -> their Region
    SEGMENT_LEAD        -> their Segment
    LEADERSHIP / ADMIN  -> Company root (everything)
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import TypeVar

# closure rows are (ancestor_id, descendant_id) pairs, incl. self-pairs (depth 0)
ClosureRow = tuple[str, str]

_Id = TypeVar("_Id")


def compute_closure(units: Iterable[tuple[_Id, _Id | None]]) -> list[tuple[_Id, _Id, int]]:
    """Transitive closure of an org tree, as ``(ancestor, descendant, depth)`` rows.

    Input is the set of ``(id, parent_id)`` edges. For every node we walk up its parent
    chain, emitting a row for itself (depth 0) and one per ancestor. This is the canonical
    way to (re)build ``org_closure`` after any unit is added, re-parented, or removed, so
    the RLS subtree lookups in :func:`visible_unit_ids` stay correct. Pure logic (no DB) so
    it is unit-testable; cycles are guarded against defensively.
    """
    parent: dict[_Id, _Id | None] = {uid: pid for uid, pid in units}
    rows: list[tuple[_Id, _Id, int]] = []
    for node in parent:
        ancestor: _Id | None = node
        depth = 0
        seen: set[_Id] = set()
        while ancestor is not None and ancestor not in seen:
            seen.add(ancestor)
            rows.append((ancestor, node, depth))
            ancestor = parent.get(ancestor)
            depth += 1
    return rows


def visible_unit_ids(scope_unit_id: str, closure: Iterable[ClosureRow]) -> set[str]:
    """All org units (incl. self) at or below the user's scope node."""
    return {desc for (anc, desc) in closure if anc == scope_unit_id}


def can_see_office(scope_unit_id: str, office_id: str,
                   closure: Iterable[ClosureRow]) -> bool:
    """True if `office_id` is within the user's scope subtree."""
    return office_id in visible_unit_ids(scope_unit_id, closure)


def scope_node_for(role_level: str, home_office_id: str | None,
                   region_id: str | None, segment_id: str | None,
                   company_root_id: str) -> str | None:
    """
    Map a user's role + position to the org node that defines their visibility.
    Returns None when the user has no assignment yet (=> sees nothing until an admin
    assigns them).
    """
    role = role_level.upper()
    if role in ("LEADERSHIP", "ADMIN"):
        return company_root_id
    if role == "SEGMENT_LEAD":
        return segment_id
    if role == "REGIONAL_DIRECTOR":
        return region_id
    if role in ("IC", "OFFICE_MANAGER"):
        return home_office_id
    return None
