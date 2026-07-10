def test_models_have_v2_columns():
    from app.models import AppUser, OrgUnit
    assert "is_verified" in OrgUnit.__table__.columns
    assert {"source", "source_broker_id", "role_locked"} <= set(AppUser.__table__.columns.keys())


from app.services.org_sync import (
    BrokerRow, UnitCreate, plan_unit_creates,
)

ROWS = [
    BrokerRow("B100", "Alice", "EMEA", "Rotterdam Office", "alice@example.com"),
    BrokerRow("B200", "Bob", None, "Cruise Team", "bob@example.com"),
]

def test_plan_unit_creates_region_then_office():
    creates = plan_unit_creates(ROWS, existing_unit_names={"Fuel Contracts"})
    assert creates == [
        UnitCreate("EMEA", "REGION", "Fuel Contracts"),
        UnitCreate("Rotterdam Office", "OFFICE", "EMEA"),
        UnitCreate("Cruise Team", "OFFICE", "Fuel Contracts"),  # no region -> under segment
    ]

def test_plan_unit_creates_skips_existing():
    creates = plan_unit_creates(ROWS, existing_unit_names={"Fuel Contracts", "EMEA", "Rotterdam Office"})
    assert creates == [UnitCreate("Cruise Team", "OFFICE", "Fuel Contracts")]


from app.services.org_sync import plan_user_upserts

OFFICE_IDS = {"Rotterdam Office": "o-emea", "Cruise Team": "o-cruise"}

def test_user_upserts_creates_new_brokers_as_ic():
    actions = plan_user_upserts(ROWS, existing=[], office_id_by_name=OFFICE_IDS)
    assert actions == [
        {"action": "create", "source_broker_id": "B100", "display_name": "Alice",
         "email": "alice@example.com", "home_office_id": "o-emea",
         "role_level": "IC", "scope_unit_id": "o-emea"},
        {"action": "create", "source_broker_id": "B200", "display_name": "Bob",
         "email": "bob@example.com", "home_office_id": "o-cruise",
         "role_level": "IC", "scope_unit_id": "o-cruise"},
    ]

def test_user_upserts_updates_synced_unlocked():
    existing = [{"id": "u1", "source_broker_id": "B100", "source": "SYNCED", "role_locked": False}]
    actions = plan_user_upserts([ROWS[0]], existing, OFFICE_IDS)
    assert actions == [{"action": "update", "id": "u1", "source_broker_id": "B100",
                        "display_name": "Alice", "email": "alice@example.com",
                        "home_office_id": "o-emea", "scope_unit_id": "o-emea"}]

def test_user_upserts_respects_role_lock():
    existing = [{"id": "u1", "source_broker_id": "B100", "source": "SYNCED", "role_locked": True}]
    actions = plan_user_upserts([ROWS[0]], existing, OFFICE_IDS)
    assert actions == [{"action": "update", "id": "u1", "source_broker_id": "B100",
                        "display_name": "Alice", "email": "alice@example.com",
                        "home_office_id": "o-emea"}]  # no scope_unit_id -> role/scope locked

def test_user_upserts_never_touches_manual_users():
    existing = [{"id": "ceo", "source_broker_id": None, "source": "MANUAL", "role_locked": True}]
    actions = plan_user_upserts([ROWS[0]], existing, OFFICE_IDS)
    assert [a["action"] for a in actions] == ["create"]  # B100 created; CEO never appears


from app.services.org_sync import resolve_office_id

def test_resolve_office_id():
    m = {"Rotterdam Office": "o1"}
    assert resolve_office_id("Rotterdam Office", m) == "o1"
    assert resolve_office_id("  Rotterdam Office ", m) == "o1"  # trims
    assert resolve_office_id("Unknown", m) is None
    assert resolve_office_id(None, m) is None
