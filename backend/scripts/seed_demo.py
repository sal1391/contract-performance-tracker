"""Deterministic demo-data seeder, anchored to date.today().

Generates 6 contracts / 12 bid lines / ~55 lifts engineered so the dashboard
shows every risk status (bid_line_performance view) no matter when it runs.
Pure math lives up top (unit-tested); DB writing (seed_demo) is added in a
follow-up task. Idempotent: skips if any contract exists.

Run (from backend/, Postgres up):  python -m scripts.seed_demo
"""
from __future__ import annotations

from datetime import date, timedelta

TOL = 0.10  # mirrors BidLine.tolerance_pct default
# Pace multiplier per target status; see PERF_VIEW_SQL in scripts/init_db.py.
# ON_TRACK needs pace >= 1.0; WATCH in [1-TOL, 1.0); AT_RISK below 1-TOL.
PACE = {"ON_TRACK": 1.10, "WATCH": 0.95, "AT_RISK": 0.55}


def elapsed_pct(start: date, end: date, today: date) -> float:
    """Mirror of the SQL view: (today-start)/(end-start) clamped to 0..1."""
    total = (end - start).days
    if total <= 0:
        return 1.0
    return max(0.0, min(1.0, (today - start).days / total))


def target_actual(contracted: float, status: str, start: date, end: date, today: date) -> float:
    """Total lifted tons that make a line show `status` on the dashboard today.

    ON_TRACK is capped at 98% of contracted volume: past ~91% elapsed the raw
    1.10x pace would exceed contracted and trip the AHEAD check instead. The
    cap keeps pace >= contracted (0.98/elapsed >= 1.0 while elapsed <= 0.98)
    yet stays under the AHEAD trigger, guaranteeing the status for any
    elapsed value."""
    if status == "FUTURE":
        return 0.0
    if status == "COMPLETE":
        return round(contracted * 0.97, 1)
    if status == "AHEAD":
        return round(contracted * 1.06, 1)
    computed = contracted * elapsed_pct(start, end, today) * PACE[status]
    if status == "ON_TRACK":
        return round(min(computed, contracted * 0.98), 1)
    return round(computed, 1)


def lift_schedule(start: date, end: date, today: date, total_tons: float) -> list[tuple[date, float]]:
    """Split total_tons over 2-6 lifts between start and min(today, end), ~45-day
    cadence, deterministic ±8% size variation, sum exactly total_tons."""
    if total_tons <= 0:
        return []
    last = min(today, end)
    days = max((last - start).days, 1)
    n = min(6, max(2, days // 45))
    step = days // n
    dates = [start + timedelta(days=step // 2 + i * step) for i in range(n)]
    weights = [1 + 0.08 * ((i % 3) - 1) for i in range(n)]  # 0.92, 1.00, 1.08, ...
    wsum = sum(weights)
    tons = [round(total_tons * w / wsum, 1) for w in weights]
    tons[-1] = round(tons[-1] + (total_tons - sum(tons)), 1)  # absorb rounding drift
    return list(zip(dates, tons))


def expected_status(contracted: float, actual: float, start: date, end: date,
                    today: date, tol: float = TOL) -> str:
    """Python mirror of the view's risk_status CASE — used by tests and the self-check."""
    if end < today:
        return "COMPLETE"
    if actual > contracted:
        return "AHEAD"
    if (today - start).days <= 0:
        return "ON_TRACK"
    pace = actual / elapsed_pct(start, end, today)
    if pace >= contracted:
        return "ON_TRACK"
    if pace >= contracted * (1 - tol):
        return "WATCH"
    return "AT_RISK"


from dataclasses import dataclass


@dataclass(frozen=True)
class LineSpec:
    port: str
    grade: str
    supplier: str            # supplier_number
    volume: float            # contracted MT
    sell: float              # selling premium USD/MT
    buy: float                # buying premium USD/MT
    status: str              # target risk status, or FUTURE
    back: int                # contract_start = today - back days (negative = future)
    ahead: int                # contract_end = today + ahead days (negative = past)
    bid_status: str = "WON"
    supply_method: str = "BARGE"


@dataclass(frozen=True)
class ContractSpec:
    source_id: str
    source_system: str       # QUICKBASE | MANUAL
    customer: str            # customer_group_number
    office: str              # org_unit OFFICE name (from init_db.seed_org)
    owner_email: str         # app_user email (from init_db.seed_org)
    bid_year_offset: int     # bid_year = today.year + offset
    region: str
    qb_status: str | None
    note: str
    lines: tuple[LineSpec, ...]


SUPPLIERS = {"NRD": "Nordfuel", "HBE": "Harbor Energy", "PMR": "Petromar", "SEA": "SeaBridge Fuels"}
INDEX_FOR_GRADE = {
    "VLSFO": ("FUEL01", "FUEL 0.5% FOB BARGE INDEX"),
    "HSFO": ("FUEL01", "FUEL 0.5% FOB BARGE INDEX"),
    "MGO": ("DSL01", "ULSD 10PPM FOB CARGO INDEX"),
}

CONTRACTS: tuple[ContractSpec, ...] = (
    ContractSpec("QB-2201", "QUICKBASE", "OCL01", "Cruise Team", "ic.cruise@local",
                 0, "EUROPE", "EXECUTED", "Renewal of 2025 Med program; priced off Platts.",
                 (LineSpec("NAPLES", "VLSFO", "NRD", 6000, 22.0, 18.0, "ON_TRACK", 200, 165),
                  LineSpec("BARCELONA", "MGO", "HBE", 4000, 34.0, 29.0, "WATCH", 180, 185))),
    ContractSpec("QB-2202", "QUICKBASE", "MER01", "Cruise Team", "ic.cruise@local",
                 0, "EUROPE", "EXECUTED", "New client 2026; volumes ramping slower than bid.",
                 (LineSpec("VENICE", "VLSFO", "NRD", 5000, 21.0, 17.5, "AT_RISK", 220, 145),
                  LineSpec("BARCELONA", "VLSFO", "SEA", 3500, 23.0, 19.0, "ON_TRACK", 160, 205))),
    ContractSpec("QB-2203", "QUICKBASE", "BWL01", "New Jersey Office", "mgr.nj@local",
                 0, "N.AMERICA", "EXECUTED", "Caribbean itineraries added mid-season.",
                 (LineSpec("MIAMI", "VLSFO", "PMR", 4500, 24.0, 19.0, "AHEAD", 240, 125,
                           supply_method="TRUCK"),
                  LineSpec("MIAMI", "MGO", "HBE", 2500, 36.0, 31.0, "WATCH", 190, 175,
                           supply_method="TRUCK"))),
    ContractSpec("QB-2204", "QUICKBASE", "ATB01", "Rotterdam Office", "mgr.nj@local",
                 0, "ASIA", "DRAFT DONE", "Bulk carrier fleet; Singapore bunkering hub.",
                 (LineSpec("SINGAPORE", "HSFO", "SEA", 8000, 18.0, 15.0, "AT_RISK", 210, 155),
                  LineSpec("SINGAPORE", "VLSFO", "NRD", 6000, 20.0, 16.5, "ON_TRACK", 170, 195,
                           supply_method="PIPELINE"))),
    ContractSpec("MAN-1001", "MANUAL", "OCL01", "Yacht Team", "lead.fuel@local",
                 -1, "N.AMERICA", None, "Prior-year yacht season; closed out.",
                 (LineSpec("MIAMI", "MGO", "PMR", 1500, 35.0, 30.0, "COMPLETE", 390, -25,
                           supply_method="TRUCK"),
                  LineSpec("NAPLES", "MGO", "HBE", 2000, 33.0, 28.5, "COMPLETE", 380, -30))),
    ContractSpec("QB-2205", "QUICKBASE", "MER01", "Cruise Team", "ic.cruise@local",
                 0, "ASIA", "EXECUTED", "Asia expansion; first line starts next quarter.",
                 (LineSpec("SINGAPORE", "MGO", "SEA", 3000, 37.0, 32.0, "FUTURE", -45, 410,
                           bid_status="PENDING"),
                  LineSpec("NAPLES", "HSFO", "NRD", 2200, 17.0, 14.0, "AHEAD", 230, 135))),
)

# Extra lift_source rows the auto-matcher CAN find (left unmapped for a live demo),
# and near-misses it must NOT find: (lift_id, customer, supplier, port, grade,
# days_ago, tons). GP is derived as tons * 4.0 for these.
EXTRA_MATCHABLE = (
    ("XL-0001", "OCL01", "NRD", "NAPLES", "VLSFO", 30, 180.0),
    ("XL-0002", "OCL01", "NRD", "NAPLES", "VLSFO", 12, 220.0),
    ("XL-0003", "BWL01", "PMR", "MIAMI", "VLSFO", 9, 250.0),
    ("XL-0004", "ATB01", "NRD", "SINGAPORE", "VLSFO", 20, 200.0),
    ("XL-0005", "ATB01", "NRD", "SINGAPORE", "VLSFO", 6, 240.0),
)
NEAR_MISSES = (
    ("NM-0001", "MER01", "NRD", "VENICE", "HSFO", 40, 400.0),    # grade mismatch vs QB-2202/VENICE
    ("NM-0002", "BWL01", "PMR", "MIAMI", "VLSFO", 400, 350.0),   # outside every BWL window
    ("NM-0003", "OCL01", "HBE", "NAPLES", "VLSFO", 15, 300.0),   # supplier mismatch vs QB-2201/NAPLES
)


def seed_demo(db) -> dict[str, int]:
    """Layer the demo dataset on top of reference data. Idempotent: no-op when any
    contract exists. Returns risk-status counts from bid_line_performance."""
    from datetime import datetime, timezone

    from sqlalchemy import text

    from app import models as m

    if db.query(m.Contract).first():
        print("Contracts already present — skipping demo seed.")
        return {}

    today = date.today()
    offices = {o.name: o for o in db.query(m.OrgUnit).filter_by(unit_type="OFFICE")}
    users = {u.email: u for u in db.query(m.AppUser)}

    # Extend dimensions (new fictional customers/ports/supplier for variety).
    db.add_all([
        m.DimCustomer(customer_group_number="MER01", customer_group_name="Meridian Cruises"),
        m.DimCustomer(customer_group_number="ATB01", customer_group_name="Atlas Bulk Carriers"),
        m.DimPort(port="BARCELONA", region="EUROPE"),
        m.DimPort(port="SINGAPORE", region="ASIA"),
        m.DimSupplier(supplier_number="SEA", supplier_name="SeaBridge Fuels"),
    ])
    customer_names = {c.customer_group_number: c.customer_group_name
                      for c in db.query(m.DimCustomer)}
    customer_names.setdefault("MER01", "Meridian Cruises")
    customer_names.setdefault("ATB01", "Atlas Bulk Carriers")

    lift_no = 0
    for cs in CONTRACTS:
        office = offices[cs.office]
        owner = users[cs.owner_email]
        contract = m.Contract(
            contract_source_id=cs.source_id, source_system=cs.source_system,
            customer_group_number=cs.customer, customer_group_name=customer_names[cs.customer],
            bid_year=today.year + cs.bid_year_offset, region=cs.region,
            source_status=cs.qb_status, bid_sub_note=cs.note,
            owner_user_id=owner.id, office_id=office.id)
        db.add(contract)
        db.flush()
        for ls in cs.lines:
            start = today - timedelta(days=ls.back)
            end = today + timedelta(days=ls.ahead)
            symbol, index_name = INDEX_FOR_GRADE[ls.grade]
            line = m.BidLine(
                contract_id=contract.id, port=ls.port, grade=ls.grade,
                supplier_number=ls.supplier, supplier_name=SUPPLIERS[ls.supplier],
                index_symbol=symbol, formula=f"{symbol} {index_name}",
                price_uom="MT", selling_premium=ls.sell, buying_premium=ls.buy,
                freight_type="MTD", pricing_days="PMA", supplier_terms="30DDD",
                contracted_volume=ls.volume, volume_tolerance="10% +/-",
                supply_method=ls.supply_method, spec="ISO 8217:2017",
                contract_start=start, contract_end=end,
                date_offered=start - timedelta(days=60),
                bid_status=ls.bid_status,
                qb_id=cs.source_id.split("-")[1] if cs.source_system == "QUICKBASE" else None,
                owner_user_id=owner.id, office_id=office.id)
            db.add(line)
            db.flush()
            total = target_actual(ls.volume, ls.status, start, end, today)
            for d, tons in lift_schedule(start, end, today, total):
                lift_no += 1
                lid = f"DL-{lift_no:04d}"
                gp = round(tons * (ls.sell - ls.buy) * (1 + 0.05 * ((lift_no % 3) - 1)), 2)
                db.add(m.LiftSource(lift_id=lid, customer_group_number=cs.customer,
                                    supplier_number=ls.supplier, port=ls.port, grade=ls.grade,
                                    lift_date=d, volume_tons=tons, gp=gp))
                db.add(m.LiftContractMap(bid_line_id=line.id, lift_id=lid, status="CONFIRMED",
                                         match_score=100, lift_lift_date=d,
                                         lift_volume_tons=tons, lift_gp=gp,
                                         mapped_at=datetime.now(timezone.utc)))

    for lid, cust, sup, port, grade, days_ago, tons in EXTRA_MATCHABLE + NEAR_MISSES:
        db.add(m.LiftSource(lift_id=lid, customer_group_number=cust, supplier_number=sup,
                            port=port, grade=grade, lift_date=today - timedelta(days=days_ago),
                            volume_tons=tons, gp=round(tons * 4.0, 2)))

    db.commit()
    counts = {row.risk_status: row.n for row in db.execute(text(
        "SELECT risk_status, COUNT(*) AS n FROM bid_line_performance GROUP BY risk_status"))}
    print(f"Demo seed complete: {lift_no} mapped lifts, "
          f"{len(EXTRA_MATCHABLE)} matchable + {len(NEAR_MISSES)} near-miss extras. "
          f"Risk statuses: {counts}")
    return counts


def run_full_seed(strict: bool = False) -> None:
    """Schema + reference + demo data. strict=True fails loudly on a bad self-check
    (CLI); the startup hook uses strict=False and just logs the counts."""
    from app.db import SessionLocal
    from scripts.init_db import create_schema, seed_reference

    create_schema()
    db = SessionLocal()
    try:
        seed_reference(db)
        counts = seed_demo(db)
    finally:
        db.close()
    if strict and counts:
        missing = {"ON_TRACK", "WATCH", "AT_RISK", "AHEAD", "COMPLETE"} - set(counts)
        if missing:
            raise SystemExit(f"Seed self-check FAILED — missing statuses: {missing}")


if __name__ == "__main__":
    run_full_seed(strict=True)
