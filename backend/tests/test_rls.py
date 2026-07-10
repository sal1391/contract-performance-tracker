from app.rls import can_see_office, scope_node_for, visible_unit_ids

# Org tree:  COMPANY -> FUEL -> EU_REGION -> CRUISE (office) -> [N/A]
#                                          \-> TANKER (office)
# closure includes self-pairs + all ancestor/descendant pairs.
CLOSURE = [
    ("COMPANY", "COMPANY"), ("COMPANY", "FUEL"), ("COMPANY", "EU"),
    ("COMPANY", "CRUISE"), ("COMPANY", "TANKER"),
    ("FUEL", "FUEL"), ("FUEL", "EU"), ("FUEL", "CRUISE"), ("FUEL", "TANKER"),
    ("EU", "EU"), ("EU", "CRUISE"), ("EU", "TANKER"),
    ("CRUISE", "CRUISE"),
    ("TANKER", "TANKER"),
]


def test_ic_sees_only_their_office():
    visible = visible_unit_ids("CRUISE", CLOSURE)
    assert visible == {"CRUISE"}
    assert can_see_office("CRUISE", "CRUISE", CLOSURE) is True
    assert can_see_office("CRUISE", "TANKER", CLOSURE) is False


def test_regional_sees_all_offices_in_region():
    visible = visible_unit_ids("EU", CLOSURE)
    assert {"CRUISE", "TANKER"} <= visible


def test_segment_lead_sees_segment():
    assert can_see_office("FUEL", "CRUISE", CLOSURE) is True
    assert can_see_office("FUEL", "TANKER", CLOSURE) is True


def test_leadership_sees_everything():
    visible = visible_unit_ids("COMPANY", CLOSURE)
    assert {"FUEL", "EU", "CRUISE", "TANKER"} <= visible


def test_scope_node_resolution():
    assert scope_node_for("IC", "CRUISE", "EU", "FUEL", "COMPANY") == "CRUISE"
    assert scope_node_for("REGIONAL_DIRECTOR", "CRUISE", "EU", "FUEL", "COMPANY") == "EU"
    assert scope_node_for("SEGMENT_LEAD", "CRUISE", "EU", "FUEL", "COMPANY") == "FUEL"
    assert scope_node_for("LEADERSHIP", None, None, None, "COMPANY") == "COMPANY"
    assert scope_node_for("IC", None, None, None, "COMPANY") is None  # unassigned -> sees nothing
