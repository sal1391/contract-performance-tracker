# Demo Data + Railway Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Seed a deterministic, today-anchored demo dataset (6 contracts / 12 bid lines / ~55 lifts) and package the app as a single Railway-deployable Docker service — with zero changes to frontend code.

**Architecture:** A new `backend/scripts/seed_demo.py` generates demo data *backwards* from target dashboard risk statuses using pure, unit-testable functions; `main.py`'s lifespan auto-runs it behind a `DEMO_SEED` flag. A multi-stage Dockerfile builds the React SPA and has FastAPI serve it (via a `STATIC_DIR` setting, off in local dev). Spec: `docs/superpowers/specs/2026-07-10-demo-data-railway-design.md`.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Postgres 16 (Docker), React 19 + Vite (build only — no source changes), Railway.

## Global Constraints

- **No changes to any file under `frontend/src/` or to `frontend/index.html`** — the UI is untouched. (`vite.config.ts`, `package.json` also stay untouched.)
- **No new Python or npm dependencies.** `requirements.txt` changes are forbidden.
- **All demo dates are computed relative to `date.today()`** — never hardcode calendar dates in seed data.
- **No randomness** (`random`, `uuid` for lift ids, etc.) in the seeder — deterministic index-based variation only. (Model PKs use their existing `uuid4` defaults; that's fine.)
- **Idempotent seeding:** re-running any seed function against a populated DB must be a no-op.
- **Work on branch `feat/demo-data-railway`** in `C:\Users\carlo\github\github_demo_apps\contract-performance-tracker`. Never push to any remote.
- **All backend commands run from `backend/`** using the venv interpreter `.venv\Scripts\python.exe` (created in Task 1, Step 0). Postgres must be up: `docker compose up -d db`.
- Existing tests (24) must keep passing after every task.
- Implementation code is written by **Sonnet subagents** (orchestrator passes `model: "sonnet"`).

### Key domain facts (read once, needed by several tasks)

The dashboard reads the Postgres view `bid_line_performance` (defined in `backend/scripts/init_db.py` `PERF_VIEW_SQL`). Per bid line, with `elapsed = clamp((today-start)/(end-start), 0, 1)`, `actual = SUM(volume of non-EXCLUDED mapped lifts dated <= today)`, `tol = tolerance_pct` (default 0.10):

| risk_status | Rule (evaluated in this order) |
|---|---|
| COMPLETE | `contract_end < today` |
| AHEAD | `actual > contracted_volume` |
| ON_TRACK | `start >= today` (not started), OR `actual/elapsed >= contracted` |
| WATCH | `actual/elapsed >= contracted*(1-tol)` |
| AT_RISK | otherwise |

The auto-matcher (`app/services/matcher.py`) suggests a lift for a line when: same `customer_group_number`, same `port`, supplier matches **if the line names one**, lift date inside the contract window, and grade matches loosely (exact or same `grade_group`; seeded grade groups equal the grade, so effectively exact).

`BidLine.margin` and `BidLine.gross_profit` are **computed DB columns** — never pass them to the constructor.

---

### Task 1: Config hardening — `DATABASE_URL` normalization, `demo_seed`, `static_dir`

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example`
- Test: `backend/tests/test_config.py` (create)

**Interfaces:**
- Produces: `Settings.demo_seed: bool` (default `True`), `Settings.static_dir: str` (default `""`), and a validator that rewrites `postgres://` / `postgresql://` URLs to `postgresql+psycopg://`. Tasks 5 and 6 consume these settings.

- [ ] **Step 0: One-time environment setup** (skip any part already done)

```powershell
cd C:\Users\carlo\github\github_demo_apps\contract-performance-tracker\backend
docker compose up -d db
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest -q
```
Expected: final command prints `24 passed`.

- [ ] **Step 1: Write the failing tests** — create `backend/tests/test_config.py`:

```python
"""Settings: Railway-style DATABASE_URL normalization + demo/static flags."""
from app.config import Settings


def test_database_url_postgresql_scheme_normalized():
    s = Settings(database_url="postgresql://u:p@host:5432/db")
    assert s.database_url == "postgresql+psycopg://u:p@host:5432/db"


def test_database_url_postgres_scheme_normalized():
    s = Settings(database_url="postgres://u:p@host:5432/db")
    assert s.database_url == "postgresql+psycopg://u:p@host:5432/db"


def test_database_url_with_driver_unchanged():
    s = Settings(database_url="postgresql+psycopg://u:p@host:5432/db")
    assert s.database_url == "postgresql+psycopg://u:p@host:5432/db"


def test_demo_and_static_defaults():
    s = Settings()
    assert s.demo_seed is True
    assert s.static_dir == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest tests/test_config.py -v`
Expected: FAIL — `ValidationError`/`AttributeError` (no `demo_seed`, URL not rewritten).

- [ ] **Step 3: Implement** — in `backend/app/config.py`:

Add to the imports:
```python
from pydantic import field_validator
```

Inside `class Settings`, directly under `database_url`:
```python
    # Demo / static serving
    demo_seed: bool = True     # auto-seed demo data at startup when the DB is empty
    static_dir: str = ""       # built SPA dir; empty = disabled (local dev). Docker sets /app/static.

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, v: object) -> object:
        """Railway/Heroku provide postgres:// or postgresql:// — rewrite for the psycopg driver."""
        if isinstance(v, str):
            for prefix in ("postgres://", "postgresql://"):
                if v.startswith(prefix):
                    return "postgresql+psycopg://" + v[len(prefix):]
        return v
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_config.py -v`
Expected: 4 PASSED. Then the full suite: `.venv\Scripts\python.exe -m pytest -q` → `28 passed`.

- [ ] **Step 5: Update `backend/.env.example`** — append after the `APP_ENV=local` block:

```
# ---- Demo mode ----
# Auto-seed reference + demo data at startup when the DB has no contracts.
DEMO_SEED=true
# Built-SPA directory served by FastAPI. Leave empty in local dev (Vite serves the UI);
# the Dockerfile sets STATIC_DIR=/app/static.
STATIC_DIR=
```

- [ ] **Step 6: Commit**

```powershell
git add app/config.py tests/test_config.py .env.example
git commit -m "feat: DATABASE_URL normalization + demo_seed/static_dir settings"
```

---

### Task 2: Refactor `init_db.py` into reusable pieces (behavior unchanged)

**Files:**
- Modify: `backend/scripts/init_db.py`

**Interfaces:**
- Produces: `create_schema() -> None` (create_all + pg_trgm + `bid_line_performance` view) and `seed_reference(db) -> None` (org tree + lookups/dims/6 sample lifts, both idempotent). `main()` behavior is byte-for-byte equivalent to today. Tasks 4 and 5 import these.

- [ ] **Step 1: Refactor `main()`** — in `backend/scripts/init_db.py`, replace the current `main()` (keep `PERF_VIEW_SQL`, `LIFTS`, `seed_org` exactly as they are) with:

```python
def create_schema() -> None:
    """Create all tables, the pg_trgm extension (best effort), and the perf view."""
    Base.metadata.create_all(engine)
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    except Exception as exc:  # noqa: BLE001
        print(f"(pg_trgm extension skipped: {exc})")
    with engine.begin() as conn:
        conn.execute(text(PERF_VIEW_SQL))


def seed_reference(db) -> None:
    """Idempotent: org tree + lookups + dimensions + the 6 sample lifts."""
    seed_org(db)
    if db.query(m.LiftSource).first():
        print("Reference data already present — skipping seed.")
        return
    db.add_all([
        ...  # the existing add_all block, UNCHANGED — copy it verbatim
    ])
    for lift_id, cust, sup, port, grade, lift, tons, gp in LIFTS:
        db.add(m.LiftSource(lift_id=lift_id, customer_group_number=cust, supplier_number=sup,
                           port=port, grade=grade, lift_date=lift, volume_tons=tons, gp=gp))
    db.commit()
    print("Seeded reference data: lookups, dimensions, and 6 sample Lifts (lift_source).")
    print("Now create a bid in the app: e.g. customer OCL01, line NAPLES / VLSFO / Nordfuel,")
    print("contract 2026-01-01..2026-12-31, then Run auto-match to pull LIFT-1001 / LIFT-1002.")


def main() -> None:
    create_schema()
    db = SessionLocal()
    try:
        seed_reference(db)
    finally:
        db.close()
```

The `...` marker above means: move the existing `db.add_all([...])` contents (all `m.Lkp*`, `m.Dim*` rows) verbatim — do not retype them. Nothing else in the file changes.

- [ ] **Step 2: Verify on a fresh DB (behavior identical)**

```powershell
docker compose down -v
docker compose up -d db
Start-Sleep -Seconds 5
.venv\Scripts\python.exe -m scripts.init_db
.venv\Scripts\python.exe -m scripts.init_db
```
Expected: first run prints the org-seed line + "Seeded reference data...". Second run prints both "already present — skipping" lines (idempotent).

- [ ] **Step 3: Run the full test suite**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: `28 passed`.

- [ ] **Step 4: Commit**

```powershell
git add scripts/init_db.py
git commit -m "refactor: split init_db into create_schema + seed_reference (no behavior change)"
```

---

### Task 3: Demo generator — pure functions (TDD)

**Files:**
- Create: `backend/scripts/seed_demo.py` (pure-function half only)
- Test: `backend/tests/test_seed_demo.py` (create)

**Interfaces:**
- Produces (Task 4 and tests consume — exact signatures):
  - `elapsed_pct(start: date, end: date, today: date) -> float`
  - `target_actual(contracted: float, status: str, start: date, end: date, today: date) -> float`
  - `lift_schedule(start: date, end: date, today: date, total_tons: float) -> list[tuple[date, float]]`
  - `expected_status(contracted: float, actual: float, start: date, end: date, today: date, tol: float = TOL) -> str`
  - Constants `TOL = 0.10`, `PACE = {"ON_TRACK": 1.10, "WATCH": 0.95, "AT_RISK": 0.55}`

- [ ] **Step 1: Write the failing tests** — create `backend/tests/test_seed_demo.py`:

```python
"""Pure-logic tests for the demo seeder: the generated actuals must land each
bid line on its target bid_line_performance risk status, for any 'today'."""
from datetime import date, timedelta

from scripts.seed_demo import (
    TOL, elapsed_pct, expected_status, lift_schedule, target_actual,
)

TODAY = date(2026, 7, 10)  # tests pin 'today'; production code uses date.today()


def test_elapsed_pct_clamps_and_divides():
    s, e = TODAY - timedelta(days=100), TODAY + timedelta(days=100)
    assert elapsed_pct(s, e, TODAY) == 0.5
    assert elapsed_pct(TODAY + timedelta(days=5), e, TODAY) == 0.0
    assert elapsed_pct(s, TODAY - timedelta(days=1), TODAY) == 1.0


def test_lift_schedule_sums_exactly_and_stays_in_window():
    s, e = TODAY - timedelta(days=200), TODAY + timedelta(days=165)
    sched = lift_schedule(s, e, TODAY, 3617.0)
    assert round(sum(t for _, t in sched), 1) == 3617.0
    assert all(s <= d <= min(TODAY, e) for d, _ in sched)
    assert 2 <= len(sched) <= 6


def test_lift_schedule_empty_for_zero_tons():
    assert lift_schedule(TODAY + timedelta(days=45), TODAY + timedelta(days=410), TODAY, 0.0) == []


def test_target_actual_hits_every_status():
    cases = [
        ("ON_TRACK", 200, 165), ("WATCH", 180, 185), ("AT_RISK", 220, 145),
        ("AHEAD", 240, 125), ("COMPLETE", 390, -25),
    ]
    for status, back, ahead in cases:
        s, e = TODAY - timedelta(days=back), TODAY + timedelta(days=ahead)
        actual = target_actual(5000.0, status, s, e, TODAY)
        assert expected_status(5000.0, actual, s, e, TODAY) == status, status


def test_future_line_reads_on_track_with_no_lifts():
    s, e = TODAY + timedelta(days=45), TODAY + timedelta(days=410)
    assert target_actual(3000.0, "FUTURE", s, e, TODAY) == 0.0
    assert expected_status(3000.0, 0.0, s, e, TODAY) == "ON_TRACK"


def test_schedule_total_preserves_status_after_split():
    # Splitting into lifts must not shift the status (rounding drift check).
    for status, back, ahead in [("WATCH", 180, 185), ("AT_RISK", 220, 145)]:
        s, e = TODAY - timedelta(days=back), TODAY + timedelta(days=ahead)
        total = target_actual(4000.0, status, s, e, TODAY)
        summed = sum(t for _, t in lift_schedule(s, e, TODAY, total))
        assert expected_status(4000.0, summed, s, e, TODAY) == status, status
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_seed_demo.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.seed_demo'`.

- [ ] **Step 3: Implement** — create `backend/scripts/seed_demo.py`:

```python
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
    """Total lifted tons that make a line show `status` on the dashboard today."""
    if status == "FUTURE":
        return 0.0
    if status == "COMPLETE":
        return round(contracted * 0.97, 1)
    if status == "AHEAD":
        return round(contracted * 1.06, 1)
    return round(contracted * elapsed_pct(start, end, today) * PACE[status], 1)


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_seed_demo.py -v`
Expected: 6 PASSED. Full suite: `.venv\Scripts\python.exe -m pytest -q` → `34 passed`.

- [ ] **Step 5: Commit**

```powershell
git add scripts/seed_demo.py tests/test_seed_demo.py
git commit -m "feat: pure demo-data generator functions (status-engineered pacing)"
```

---

### Task 4: Demo dataset + DB seeding

**Files:**
- Modify: `backend/scripts/seed_demo.py` (add dataset spec + DB half)
- Modify: `backend/tests/test_seed_demo.py` (add dataset-spec tests)

**Interfaces:**
- Consumes: Task 2's `create_schema` / `seed_reference`; Task 3's pure functions.
- Produces: `CONTRACTS: tuple[ContractSpec, ...]`, `seed_demo(db) -> dict[str, int]` (risk-status counts; `{}` when skipped), `run_full_seed(strict: bool = False) -> None`. Task 5 imports `run_full_seed`.

- [ ] **Step 1: Write the failing tests** — append to `backend/tests/test_seed_demo.py`:

```python
from scripts.seed_demo import CONTRACTS


def test_dataset_shape():
    lines = [ls for cs in CONTRACTS for ls in cs.lines]
    assert len(CONTRACTS) == 6
    assert len(lines) == 12
    by_status: dict[str, int] = {}
    for ls in lines:
        by_status[ls.status] = by_status.get(ls.status, 0) + 1
    assert by_status == {"ON_TRACK": 3, "WATCH": 2, "AT_RISK": 2,
                         "AHEAD": 2, "COMPLETE": 2, "FUTURE": 1}


def test_every_line_spec_hits_its_target_status():
    """The money test: generated lift totals land every line on its declared status."""
    for cs in CONTRACTS:
        for ls in cs.lines:
            start = TODAY - timedelta(days=ls.back)
            end = TODAY + timedelta(days=ls.ahead)
            total = target_actual(ls.volume, ls.status, start, end, TODAY)
            summed = sum(t for _, t in lift_schedule(start, end, TODAY, total))
            want = "ON_TRACK" if ls.status == "FUTURE" else ls.status
            assert expected_status(ls.volume, summed, start, end, TODAY) == want, (cs.source_id, ls.port)


def test_line_uniqueness_per_contract():
    for cs in CONTRACTS:
        keys = [(ls.port, ls.grade, ls.supplier) for ls in cs.lines]
        assert len(keys) == len(set(keys)), cs.source_id
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_seed_demo.py -v`
Expected: FAIL — `ImportError: cannot import name 'CONTRACTS'`.

- [ ] **Step 3: Implement the dataset spec** — in `backend/scripts/seed_demo.py`, add below the pure functions:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class LineSpec:
    port: str
    grade: str
    supplier: str            # supplier_number
    volume: float            # contracted MT
    sell: float              # selling premium USD/MT
    buy: float               # buying premium USD/MT
    status: str              # target risk status, or FUTURE
    back: int                # contract_start = today - back days (negative = future)
    ahead: int               # contract_end = today + ahead days (negative = past)
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_seed_demo.py -v`
Expected: 9 PASSED.

- [ ] **Step 5: Implement the DB half** — append to `backend/scripts/seed_demo.py`:

```python
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
```

- [ ] **Step 6: Verify against a live fresh DB**

```powershell
docker compose down -v
docker compose up -d db
Start-Sleep -Seconds 5
.venv\Scripts\python.exe -m scripts.seed_demo
.venv\Scripts\python.exe -m scripts.seed_demo
```
Expected: first run ends with `Risk statuses: {...}` containing **all five** of AT_RISK, WATCH, ON_TRACK, AHEAD, COMPLETE (ON_TRACK count 4 = 3 paced + 1 future) and exit code 0. Second run prints all three "already present — skipping" messages.

- [ ] **Step 7: Run the full test suite**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: `37 passed`.

- [ ] **Step 8: Commit**

```powershell
git add scripts/seed_demo.py tests/test_seed_demo.py
git commit -m "feat: demo dataset (6 contracts / 12 lines / ~55 lifts) + idempotent DB seeder"
```

---

### Task 5: Auto-seed on startup

**Files:**
- Modify: `backend/app/main.py` (lifespan only)

**Interfaces:**
- Consumes: `run_full_seed` (Task 4), `settings.demo_seed` (Task 1).

- [ ] **Step 1: Implement** — in `backend/app/main.py`, at the very top of the `lifespan` function body (before the `if settings.scheduler_enabled:` block), insert:

```python
    if settings.demo_seed:
        try:
            from scripts.seed_demo import run_full_seed
            run_full_seed()
        except Exception:  # noqa: BLE001 — a seed failure must never block boot
            log.exception("demo seed failed — continuing without demo data")
```

- [ ] **Step 2: Verify on a fresh DB via boot alone**

```powershell
docker compose down -v
docker compose up -d db
Start-Sleep -Seconds 5
Start-Process -NoNewWindow .venv\Scripts\python.exe -ArgumentList "-m","uvicorn","app.main:app","--port","8000"
Start-Sleep -Seconds 12
curl.exe -s http://localhost:8000/healthz
curl.exe -s http://localhost:8000/api/dashboard/summary
curl.exe -s "http://localhost:8000/api/contracts" | ConvertFrom-Json | Measure-Object
```
Expected: healthz `{"status":"ok",...}`; summary JSON `by_status` contains all five statuses; contracts count = 6. Restart uvicorn once more and re-curl — data unchanged (idempotent). Stop the uvicorn process afterwards (`Get-Process python | Stop-Process` is too broad — use `Stop-Process -Name uvicorn -ErrorAction SilentlyContinue` or close via Ctrl+C in its window; if in doubt find the PID with `Get-NetTCPConnection -LocalPort 8000`).

- [ ] **Step 3: Run the full test suite**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: `37 passed`.

- [ ] **Step 4: Commit**

```powershell
git add app/main.py
git commit -m "feat: auto-seed demo data at startup behind DEMO_SEED flag"
```

---

### Task 6: FastAPI serves the built SPA (`STATIC_DIR`)

**Files:**
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `settings.static_dir` (Task 1).
- Produces: when `STATIC_DIR` points at a Vite build, `/` serves the SPA, unknown non-API paths fall back to `index.html`, unknown `/api/*` paths still 404. Task 7's image relies on this.

- [ ] **Step 1: Implement** — in `backend/app/main.py`:

Add imports:
```python
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
```

After the `setup_admin(app, engine)` line and the `healthz` route (very end of file), add:

```python
# --- Built-SPA serving (single-service deploys; off locally where Vite serves the UI) ---
_static = Path(settings.static_dir) if settings.static_dir else None
if _static and _static.is_dir():
    app.mount("/assets", StaticFiles(directory=_static / "assets"), name="spa-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        if full_path == "api" or full_path.startswith(("api/", "admin")):
            raise HTTPException(status_code=404)  # unknown API path stays a JSON 404
        candidate = _static / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_static / "index.html")
```

(Registration order matters: this catch-all is added last, so all real routes — `/api/*` routers, `/admin` mount, `/docs`, `/healthz` — win. The startswith guard is defense-in-depth.)

- [ ] **Step 2: Build the frontend once and verify serving**

```powershell
cd ..\frontend
npm install
npm run build
cd ..\backend
$env:STATIC_DIR = (Resolve-Path ..\frontend\dist).Path
Start-Process -NoNewWindow .venv\Scripts\python.exe -ArgumentList "-m","uvicorn","app.main:app","--port","8000"
Start-Sleep -Seconds 12
curl.exe -s -o NUL -w "%{content_type} %{http_code}`n" http://localhost:8000/
curl.exe -s -o NUL -w "%{http_code}`n" http://localhost:8000/bids
curl.exe -s -o NUL -w "%{http_code}`n" http://localhost:8000/api/nonexistent
curl.exe -s http://localhost:8000/api/dashboard/summary
Remove-Item Env:\STATIC_DIR
```
Expected: `/` → `text/html 200`; `/bids` → `200` (SPA fallback); `/api/nonexistent` → `404`; summary still returns JSON. Stop uvicorn.

- [ ] **Step 3: Verify local dev is unaffected**

Run: `.venv\Scripts\python.exe -m pytest -q` → `37 passed`. Boot uvicorn **without** `STATIC_DIR`; `curl.exe -s -o NUL -w "%{http_code}" http://localhost:8000/` → `404` (no SPA mounted, unchanged local behavior). Stop uvicorn.

- [ ] **Step 4: Commit**

```powershell
git add app/main.py
git commit -m "feat: serve built SPA from FastAPI when STATIC_DIR is set"
```

---

### Task 7: Dockerfile + .dockerignore + local image rehearsal

**Files:**
- Create: `Dockerfile` (repo root)
- Create: `.dockerignore` (repo root)

**Interfaces:**
- Consumes: Tasks 5-6 (auto-seed + `STATIC_DIR` serving).
- Produces: image `triton-demo` that Railway builds as-is; listens on `$PORT` (default 8000).

- [ ] **Step 1: Create `.dockerignore`** (repo root):

```
.git
docs
**/node_modules
frontend/dist
backend/.venv
backend/tests
**/__pycache__
**/*.pyc
backend/.env
.github
```

- [ ] **Step 2: Create `Dockerfile`** (repo root):

```dockerfile
# ---- Stage 1: build the React SPA ----
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python runtime serving API + SPA ----
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY backend/scripts ./scripts
COPY --from=frontend /build/dist ./static
ENV STATIC_DIR=/app/static
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

- [ ] **Step 3: Build and rehearse locally against the compose Postgres**

```powershell
cd C:\Users\carlo\github\github_demo_apps\contract-performance-tracker
docker build -t triton-demo .
docker run --rm -d --name triton-demo -p 8080:8080 -e PORT=8080 `
  -e DATABASE_URL="postgresql://app:app@host.docker.internal:5432/contracts" triton-demo
Start-Sleep -Seconds 15
curl.exe -s http://localhost:8080/healthz
curl.exe -s -o NUL -w "%{content_type} %{http_code}`n" http://localhost:8080/
curl.exe -s http://localhost:8080/api/dashboard/summary
docker logs triton-demo --tail 5
docker stop triton-demo
```
Expected: healthz ok; `/` serves `text/html 200`; summary has all five statuses; logs show either the seed-complete line or the "already present — skipping" lines (the compose DB was seeded in Task 5). Note: the raw `postgresql://` URL proves the Task 1 normalization works.

- [ ] **Step 4: Commit**

```powershell
git add Dockerfile .dockerignore
git commit -m "feat: single-service Dockerfile (SPA build + FastAPI runtime)"
```

---

### Task 8: Railway config + deploy guide + README note

**Files:**
- Create: `railway.json` (repo root)
- Create: `DEPLOY.md` (repo root)
- Modify: `README.md` (add a short demo/deploy section)

**Interfaces:**
- Consumes: the Task 7 image contract (`$PORT`, `DATABASE_URL`, `DEMO_SEED`).

- [ ] **Step 1: Create `railway.json`**:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "healthcheckPath": "/healthz",
    "healthcheckTimeout": 120,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

- [ ] **Step 2: Create `DEPLOY.md`**:

```markdown
# Deploying the Triton demo to Railway

One Railway service (API + UI in a single Docker image) + the Railway Postgres plugin.
On first boot the app creates its schema and seeds a full demo dataset automatically
(`DEMO_SEED=true`), so the deployed URL lands on a populated dashboard.

## Steps (~5 minutes)

1. **Create the project** — [railway.app](https://railway.app) → New Project.
2. **Add Postgres** — "Create" → Database → **PostgreSQL**.
3. **Add the app service** — either:
   - **GitHub:** "Create" → GitHub Repo → pick this repo (Railway detects `railway.json`
     and builds the Dockerfile), or
   - **CLI:** `npm i -g @railway/cli`, then from the repo root:
     `railway login`, `railway init`, `railway up`.
4. **Set the app service variables** (service → Variables):

   | Variable | Value | Notes |
   |---|---|---|
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Reference to the plugin. The app rewrites the URL for its psycopg driver automatically. |
   | `DEMO_SEED` | `true` | Auto-seed schema + demo data on first boot. Optional (defaults to true). |

   `PORT` is injected by Railway; `STATIC_DIR` is baked into the image. Nothing else is needed —
   auth stays off (`AUTH0_ENABLED` defaults to false), which is what enables the demo
   "Act as" user switch.
5. **Expose it** — service → Settings → Networking → **Generate Domain**. Open the URL:
   the Dashboard should show populated risk tiles.

## Demo walkthrough

- **Dashboard** — at-risk tiles ($ GP at risk) across every status.
- **Bids** — 6 contracts / 12 bid lines; open one to see computed margin + GP.
- **Mapping** — pick QB-2201 · NAPLES/VLSFO and "Run auto-match" to live-match the
  unmapped `XL-…` lifts; `NM-…` lifts demonstrate near-misses you can map manually.
- **Act as** (top-right) — switch between Ivy (IC, sees Cruise Team only), Theo (NJ office),
  Rosa (NA region), Sam (segment), Lee (leadership, sees all) to demo org-subtree RLS.

## Resetting the demo data

The seeder is idempotent and never overwrites. To reset to a pristine demo:

```
railway connect postgres        # opens psql on the plugin
DROP SCHEMA public CASCADE; CREATE SCHEMA public;
\q
```

then redeploy (or restart) the app service — it reseeds on boot.

## Running the production image locally

```
docker build -t triton-demo .
docker run --rm -p 8080:8080 -e PORT=8080 \
  -e DATABASE_URL="postgresql://app:app@host.docker.internal:5432/contracts" triton-demo
```

Requires the local compose Postgres: `cd backend && docker compose up -d db`.
```

- [ ] **Step 3: Add a README section** — in `README.md`, insert directly before the `## Documentation` heading:

```markdown
## Demo mode & Railway

The app auto-seeds a deterministic demo dataset (6 contracts, 12 bid lines, ~55 lifts —
every dashboard risk status represented, dates anchored to "today") on first boot when
`DEMO_SEED=true` (the default). A single-service Docker image (React build served by
FastAPI) deploys to Railway in ~5 minutes — see [`DEPLOY.md`](DEPLOY.md).
```

- [ ] **Step 4: Commit**

```powershell
git add railway.json DEPLOY.md README.md
git commit -m "docs: Railway config + deploy guide + README demo section"
```

---

### Task 9: Full end-to-end verification

**Files:** none created — this task gates completion. Use the superpowers:verification-before-completion skill.

- [ ] **Step 1: Full test suite**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest -q`
Expected: `37 passed` (24 original + 4 config + 9 seed).

- [ ] **Step 2: Pristine local stack**

```powershell
cd backend
docker compose down -v
docker compose up -d db
Start-Sleep -Seconds 5
Start-Process -NoNewWindow .venv\Scripts\python.exe -ArgumentList "-m","uvicorn","app.main:app","--port","8000"
Start-Sleep -Seconds 12
curl.exe -s http://localhost:8000/api/dashboard/summary
```
Expected: `by_status` contains AT_RISK, WATCH, ON_TRACK, AHEAD, COMPLETE; `gp_at_risk` > 0.

- [ ] **Step 3: UI walkthrough (Vite dev, UI untouched)**

```powershell
cd ..\frontend
npm run dev
```
In the browser at `http://localhost:5173`, verify each page renders with data: **Dashboard** (populated risk tiles, non-zero $ GP at risk), **Bids** (6 contracts; open QB-2201 → 2 lines with computed margin/GP), **Mapping** (select QB-2201 NAPLES/VLSFO → confirmed lifts listed; Run auto-match surfaces XL-0001/XL-0002), **Accounts** (customers listed), **Admin** (org tree + 5 users). Top-right **Act as**: Ivy sees only Cruise Team contracts (QB-2201, QB-2202, QB-2205); Lee sees all 6.

- [ ] **Step 4: Git hygiene check**

```powershell
git status --short
git log --oneline origin/main..HEAD
```
Expected: clean tree; only this plan's commits on `feat/demo-data-railway`; `frontend/src` and `frontend/index.html` absent from every diff (`git diff origin/main..HEAD --stat -- frontend/src frontend/index.html` → empty).

- [ ] **Step 5: Report** — summarize verified evidence (test count, status list from the summary endpoint, pages checked) before claiming completion.
