"""Bootstrap a LOCAL dev database.

Creates all tables + the bid_line_performance view, and seeds ONLY reference data:
  - lookups (price UOM, bid status, supply method)
  - dimensions (ports, customers, suppliers, grades) -> the workbench dropdowns
  - lift_source: sample LIFT transactions (a local stand-in for Snowflake LIFTS_FOR_MATCHING_V)
    so the matcher + mapping work without Snowflake.

It does NOT create any contracts, bid lines, or org units — you enter those in the app.
For real schema management use Alembic; this is a local convenience.

Run (from backend/, with Postgres up):  python -m scripts.init_db
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import text

from app import models as m
from app.db import Base, SessionLocal, engine
from app.services.org import rebuild_closure

PERF_VIEW_SQL = """
CREATE OR REPLACE VIEW bid_line_performance AS
WITH actuals AS (
  SELECT bid_line_id,
         SUM(lift_volume_tons) AS actual_volume,
         SUM(lift_gp)          AS actual_gp
  FROM lift_contract_map
  WHERE status <> 'EXCLUDED' AND lift_lift_date <= CURRENT_DATE
  GROUP BY bid_line_id
)
SELECT
  bl.id AS bid_line_id, bl.contract_id, bl.contracted_volume,
  bl.gross_profit AS contracted_gp, bl.margin AS contracted_margin,
  bl.contract_start, bl.contract_end, bl.tolerance_pct,
  COALESCE(a.actual_volume,0) AS actual_volume,
  COALESCE(a.actual_gp,0)     AS actual_gp,
  a.actual_gp / NULLIF(a.actual_volume,0) AS actual_margin,
  GREATEST(0, LEAST(1,
    (CURRENT_DATE - bl.contract_start)::numeric
    / NULLIF((bl.contract_end - bl.contract_start),0))) AS elapsed_pct,
  CASE
    WHEN bl.contract_end < CURRENT_DATE THEN 'COMPLETE'
    WHEN COALESCE(a.actual_volume,0) > bl.contracted_volume THEN 'AHEAD'
    WHEN (CURRENT_DATE - bl.contract_start) <= 0 THEN 'ON_TRACK'
    ELSE
      CASE
        WHEN COALESCE(a.actual_volume,0)
             / NULLIF((CURRENT_DATE - bl.contract_start)::numeric
                      / NULLIF((bl.contract_end - bl.contract_start),0),0)
             >= bl.contracted_volume THEN 'ON_TRACK'
        WHEN COALESCE(a.actual_volume,0)
             / NULLIF((CURRENT_DATE - bl.contract_start)::numeric
                      / NULLIF((bl.contract_end - bl.contract_start),0),0)
             >= bl.contracted_volume * (1 - bl.tolerance_pct) THEN 'WATCH'
        ELSE 'AT_RISK'
      END
  END AS risk_status
FROM bid_line bl
LEFT JOIN actuals a ON a.bid_line_id = bl.id;
"""

LIFTS = [
    # lift_id,    customer, supplier, port,     grade,  lift_date,           tons,  gp
    ("LIFT-1001", "OCL01", "NRD", "NAPLES", "VLSFO", date(2026, 3, 10), 500, 6000),
    ("LIFT-1002", "OCL01", "NRD", "NAPLES", "VLSFO", date(2026, 5, 12), 450, 5400),
    ("LIFT-1003", "OCL01", "HBE", "VENICE", "MGO",   date(2026, 2, 20), 2000, 24000),
    ("LIFT-1004", "BWL01", "PMR", "MIAMI",  "VLSFO", date(2026, 4, 1), 800, 9600),
    ("LIFT-1005", "OCL01", "NRD", "NAPLES", "HSFO",  date(2026, 6, 1), 300, 3000),  # grade mismatch demo
    ("LIFT-1006", "BWL01", "HBE", "MIAMI",  "MGO",   date(2026, 1, 15), 1200, 14400),
]


def seed_org(db) -> None:
    """Idempotent demo tree matching the v2 design + 5 MANUAL users for the act-as switch.

        TridentFuel (COMPANY)
          └ Fuel Contracts (SEGMENT)
              ├ North America (REGION) ─ New Jersey Office (OFFICE)
              ├ EMEA (REGION) ─ Rotterdam Office (OFFICE)
              ├ Cruise (REGION, global) ─ Cruise Team (OFFICE)
              └ Yacht (REGION, global) ─ Yacht Team (OFFICE)
    """
    if db.query(m.OrgUnit).first():
        print("Org tree already present - skipping org seed.")
        return

    company = m.OrgUnit(name="TridentFuel", unit_type="COMPANY")
    db.add(company); db.flush()
    fuel = m.OrgUnit(name="Fuel Contracts", unit_type="SEGMENT", parent_id=company.id)
    db.add(fuel); db.flush()
    na = m.OrgUnit(name="North America", unit_type="REGION", parent_id=fuel.id)
    emea = m.OrgUnit(name="EMEA", unit_type="REGION", parent_id=fuel.id)
    cruise = m.OrgUnit(name="Cruise", unit_type="REGION", parent_id=fuel.id)
    yacht = m.OrgUnit(name="Yacht", unit_type="REGION", parent_id=fuel.id)
    db.add_all([na, emea, cruise, yacht]); db.flush()
    nj = m.OrgUnit(name="New Jersey Office", unit_type="OFFICE", parent_id=na.id)
    rot = m.OrgUnit(name="Rotterdam Office", unit_type="OFFICE", parent_id=emea.id)
    src = m.OrgUnit(name="Cruise Team", unit_type="OFFICE", parent_id=cruise.id)
    yt = m.OrgUnit(name="Yacht Team", unit_type="OFFICE", parent_id=yacht.id)
    db.add_all([nj, rot, src, yt]); db.flush()

    db.add_all([
        m.AppUser(email="ic.cruise@local", display_name="Ivy - Cruise (IC)",
                  role_level="IC", home_office_id=src.id, scope_unit_id=src.id,
                  auth0_sub="dev|ic.cruise@local", source="MANUAL"),
        m.AppUser(email="mgr.nj@local", display_name="Theo - New Jersey (Office Mgr)",
                  role_level="OFFICE_MANAGER", home_office_id=nj.id, scope_unit_id=nj.id,
                  auth0_sub="dev|mgr.nj@local", source="MANUAL"),
        m.AppUser(email="dir.na@local", display_name="Rosa - North America (Regional Dir)",
                  role_level="REGIONAL_DIRECTOR", home_office_id=nj.id, scope_unit_id=na.id,
                  auth0_sub="dev|dir.na@local", source="MANUAL"),
        m.AppUser(email="lead.fuel@local", display_name="Sam - Fuel Contracts (Segment Lead)",
                  role_level="SEGMENT_LEAD", home_office_id=src.id, scope_unit_id=fuel.id,
                  auth0_sub="dev|lead.fuel@local", source="MANUAL"),
        m.AppUser(email="leadership@local", display_name="Lee - Leadership (sees all)",
                  role_level="LEADERSHIP", scope_unit_id=company.id,
                  auth0_sub="dev|leadership@local", source="MANUAL"),
    ])
    db.commit()
    rebuild_closure(db)
    print("Seeded demo org tree (TridentFuel > Fuel Contracts > NA/EMEA/Cruise/Yacht > offices) + 5 MANUAL users.")


def main() -> None:
    Base.metadata.create_all(engine)
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    except Exception as exc:  # noqa: BLE001
        print(f"(pg_trgm extension skipped: {exc})")
    with engine.begin() as conn:
        conn.execute(text(PERF_VIEW_SQL))

    db = SessionLocal()
    try:
        seed_org(db)
        if db.query(m.LiftSource).first():
            print("Reference data already present — skipping seed.")
            return

        db.add_all([
            m.LkpPriceUom(code="MT", label="Metric Ton", sort_order=1),
            m.LkpPriceUom(code="USG", label="US Gallon", sort_order=2),
            m.LkpBidStatus(code="WON", label="Won", sort_order=1),
            m.LkpBidStatus(code="LOST", label="Lost", sort_order=2),
            m.LkpBidStatus(code="PENDING", label="Pending", sort_order=3),
            m.LkpSupplyMethod(code="BARGE", label="Barge", sort_order=1),
            m.LkpSupplyMethod(code="TRUCK", label="Truck", sort_order=2),
            m.LkpSupplyMethod(code="PIPELINE", label="Pipeline", sort_order=3),
            m.LkpFreightType(code="MTD", label="Month to date", sort_order=1),
            m.LkpFreightType(code="MTW", label="Month to week", sort_order=2),
            m.LkpPricingDays(code="PMA", label="Previous Month Average", sort_order=1),
            m.LkpPricingDays(code="PWA", label="Prior Week Average", sort_order=2),
            m.LkpPricingDays(code="DOD", label="Date of Delivery", sort_order=3),
            m.DimIndex(symbol="FUEL01", index_name="FUEL 0.5% FOB BARGE INDEX"),
            m.DimIndex(symbol="DSL01", index_name="ULSD 10PPM FOB CARGO INDEX"),
            m.DimPort(port="NAPLES", region="EUROPE"),
            m.DimPort(port="VENICE", region="EUROPE"),
            m.DimPort(port="MIAMI", region="N.AMERICA"),
            m.DimCustomer(customer_group_number="OCL01", customer_group_name="OCL"),
            m.DimCustomer(customer_group_number="BWL01", customer_group_name="Bluewave Lines"),
            m.DimSupplier(supplier_number="NRD", supplier_name="Nordfuel"),
            m.DimSupplier(supplier_number="HBE", supplier_name="Harbor Energy"),
            m.DimSupplier(supplier_number="PMR", supplier_name="Petromar"),
            m.DimGrade(grade="VLSFO", grade_group="VLSFO"),
            m.DimGrade(grade="MGO", grade_group="MGO"),
            m.DimGrade(grade="HSFO", grade_group="HSFO"),
        ])
        for lift_id, cust, sup, port, grade, lift, tons, gp in LIFTS:
            db.add(m.LiftSource(lift_id=lift_id, customer_group_number=cust, supplier_number=sup,
                               port=port, grade=grade, lift_date=lift, volume_tons=tons, gp=gp))
        db.commit()
        print("Seeded reference data: lookups, dimensions, and 6 sample Lifts (lift_source).")
        print("Now create a bid in the app: e.g. customer OCL01, line NAPLES / VLSFO / Nordfuel,")
        print("contract 2026-01-01..2026-12-31, then Run auto-match to pull LIFT-1001 / LIFT-1002.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
