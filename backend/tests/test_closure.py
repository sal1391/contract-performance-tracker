from app.rls import compute_closure, visible_unit_ids

# Org tree:  COMPANY -> FUEL -> EU -> CRUISE (office)
#                                   \-> TANKER (office)
EDGES = [
    ("COMPANY", None),
    ("FUEL", "COMPANY"),
    ("EU", "FUEL"),
    ("CRUISE", "EU"),
    ("TANKER", "EU"),
]


def test_self_pairs_present_at_depth_zero():
    closure = compute_closure(EDGES)
    for node, _ in EDGES:
        assert (node, node, 0) in closure


def test_full_ancestry_with_depths():
    closure = set(compute_closure(EDGES))
    # CRUISE sits 3 levels below COMPANY
    assert ("EU", "CRUISE", 1) in closure
    assert ("FUEL", "CRUISE", 2) in closure
    assert ("COMPANY", "CRUISE", 3) in closure
    # ...but COMPANY never becomes a descendant of anyone
    assert not any(desc == "COMPANY" and anc != "COMPANY" for anc, desc, _ in closure)


def test_closure_feeds_rls_subtree_lookup():
    pairs = [(anc, desc) for anc, desc, _ in compute_closure(EDGES)]
    assert visible_unit_ids("EU", pairs) == {"EU", "CRUISE", "TANKER"}
    assert visible_unit_ids("CRUISE", pairs) == {"CRUISE"}
    assert visible_unit_ids("COMPANY", pairs) == {"COMPANY", "FUEL", "EU", "CRUISE", "TANKER"}


def test_reparent_changes_visibility():
    # move TANKER out of EU, directly under FUEL
    moved = [(u, ("FUEL" if u == "TANKER" else p)) for u, p in EDGES]
    pairs = [(anc, desc) for anc, desc, _ in compute_closure(moved)]
    assert visible_unit_ids("EU", pairs) == {"EU", "CRUISE"}        # TANKER no longer under EU
    assert "TANKER" in visible_unit_ids("FUEL", pairs)            # ...now under FUEL


def test_cycle_is_guarded():
    # a corrupt A<->B cycle must not hang
    rows = compute_closure([("A", "B"), ("B", "A")])
    assert ("A", "A", 0) in rows and ("B", "B", 0) in rows
