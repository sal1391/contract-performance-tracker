# Snowflake / Coco Build Spec — Fuel Contract Tracking App

> **Audience:** Snowflake Coco + GitHub Copilot running on a **Snowflake-connected machine**.
> The originating dev machine has **no Snowflake access**, so all object creation and
> data-dependent testing happen here. Build exactly these objects with these names.
>
> **Read first:** [`docs/REPO_BRIEF.md`](../REPO_BRIEF.md) (domain + data dictionary) and
> [`docs/plans/2026-06-24-contract-tracking-app-design.md`](../plans/2026-06-24-contract-tracking-app-design.md) (decisions).
> **Last updated:** 2026-06-30

---

## 0. RESOLVE THESE FIRST (blocking data questions)

These cannot be answered without Snowflake access. Answer them, then fill the `‹…›`
placeholders below and report the answers back into this file.

1. **LIFT primary key** — What column uniquely identifies one LIFT (one transaction row) in
   `SALES_ACTUALS_V`? (e.g. a transaction id / fixture id.) If none exists, build a
   deterministic surrogate `LIFT_ID = MD5(concat_ws('|', <natural key cols>))` and document it.
2. **Join column names on `SALES_ACTUALS_V`:**
   - customer key → expected `CUSTOMER_GROUP_NUMBER` (confirm exact name)
   - supplier key → expected `SUPPLIER_NUMBER` (confirm exact name; note it may be null/blank)
   - port (lowest grain) → `PORT_NAME` (confirmed in `snowflake_client.py`)
   - grade → expected `GRADE_NAME` (confirm; may be a grouped grade column)
   - date → `DELIVERY_DATE` (confirmed) · volume → `VOLUME_TONS` · GP → `GROSS_PROFIT` (confirmed)
3. **Grade grouping** — Is there a grade-group mapping (e.g. all `VLSFO`-family codes → `VLSFO`)?
   If yes, expose it; the matcher uses it for "loose" grade matching.
4. **Snowflake Postgres** — Provision an instance and capture the connection string
   (exact commands in **Part B.0**). The API connects to it as standard Postgres via `DATABASE_URL`.
5. **Contract office classification** — exact QuickBase column that yields a contract's **office**
   (classification grain is office; lines/Lifts inherit it via intake).
6. **Broker↔email join** — confirm `CUSTOMER_BROKER_NUMBER` (SALES_ACTUALS_V) ==
   `SALES_REP_NUMBER` (email-mapping table) as the broker key; the mapping provides `EMAIL`.
   `CUSTOMER_BROKER_NAME` is the display name. Segment defaults to 'Fuel Contracts' (implied by the source table).

---

## PART A — Snowflake objects (Snowflake SQL)

Create in the app's Snowflake database/schema (mirror the existing `SANDBOX.ANALYTICS` convention or
a dedicated `CONTRACTS_APP` schema — confirm with the team).

### A.1 `CONTRACT_INTAKE` — source-agnostic contract feed (USER-LOADED)
Fixed schema. The user loads it from a QuickBase export today and a DocuSign export later.
One row per **bid line** as it exists in the source; the app groups rows into contracts by
`CONTRACT_SOURCE_ID`.

```sql
CREATE TABLE IF NOT EXISTS CONTRACT_INTAKE (
    CONTRACT_SOURCE_ID      VARCHAR        NOT NULL,  -- QB ID now / DocuSign id later; the contract grain
    SOURCE_SYSTEM           VARCHAR        DEFAULT 'QUICKBASE',  -- QUICKBASE | DOCUSIGN | MANUAL
    CUSTOMER_GROUP_NUMBER   VARCHAR        NOT NULL,  -- backend join key
    CUSTOMER_GROUP_NAME     VARCHAR,                  -- display (e.g. OCL)
    BID_YEAR                NUMBER(4,0),
    REGION                  VARCHAR,                  -- AFRICA | N.AMERICA | EUROPE | N EU | ASIA
    OFFICE                  VARCHAR,                  -- §0.5: QB office/classification -> contract.office_id (lines + Lifts inherit)
    PORT                    VARCHAR        NOT NULL,  -- lowest grain; matches SALES_ACTUALS_V.PORT_NAME
    GRADE                   VARCHAR,                  -- VLSFO | MGO | HSFO | ...
    SUPPLIER_NUMBER         VARCHAR,                  -- backend join key (may be blank if no supplier yet)
    SUPPLIER_NAME           VARCHAR,
    CONTRACTED_VOLUME       NUMBER(18,3),
    FUEL_TYPE               VARCHAR,                  -- high-level fuel type if distinct from GRADE
    SPEC                    VARCHAR,                  -- ISO spec / dye notes
    CONTRACT_START          DATE,
    CONTRACT_END            DATE,
    DATE_OFFERED            DATE,
    BID_STATUS              VARCHAR,                  -- WON | LOST | PENDING (clean 'PEDING' typo on load)
    SOURCE_STATUS           VARCHAR,                  -- QB STATUS / won_or_lost (EXECUTED, DRAFT DONE, ...)
    LOADED_AT               TIMESTAMP_NTZ  DEFAULT CURRENT_TIMESTAMP()
);
```
> Premiums, tolerances, freight fees, and notes are **NOT** in intake — the team enters those
> in the app. Intake carries only what the approval system knows.

### A.2 `LIFTS_FOR_MATCHING_V` — projection the matcher reads
Build over `SALES_ACTUALS_V` once §0 columns are confirmed. Replace `‹…›`.

```sql
CREATE OR REPLACE VIEW LIFTS_FOR_MATCHING_V AS
SELECT
    ‹LIFT_ID_EXPR›              AS LIFT_ID,             -- stable key or MD5 surrogate (see §0.1)
    ‹CUSTOMER_GROUP_NUMBER›    AS CUSTOMER_GROUP_NUMBER,
    ‹SUPPLIER_NUMBER›          AS SUPPLIER_NUMBER,
    PORT_NAME                     AS PORT,               -- lowest grain
    ‹GRADE_NAME›               AS GRADE,
    DELIVERY_DATE              AS LIFT_DATE,
    VOLUME_TONS                 AS VOLUME_TONS,
    GROSS_PROFIT               AS GP
FROM SALES_ACTUALS_V
WHERE DELIVERY_DATE IS NOT NULL
  AND PORT_NAME IS NOT NULL;
```

---

## PART B — Snowflake Postgres app schema

> **Authoritative source = `backend/app/models.py`, applied via Alembic — NOT the DDL below.**
> Alembic is already scaffolded (`backend/alembic/env.py` targets `Base.metadata`, `versions/`
> empty). Build the schema with `alembic revision --autogenerate -m "initial schema"` then
> `alembic upgrade head`; this captures every column (including the org-access-v2 ones) with zero
> drift. The DDL in B.1–B.7 is a human-readable reference kept in sync with the models. Three
> objects are NOT in the models and must be created with raw SQL after `upgrade head`: the
> `bid_line_performance` view (Part G), `pg_trgm` + its indexes (Part I), and confirm
> `gen_random_uuid()` exists (PG13+, built-in).

### B.0 Provision the Snowflake Postgres instance (run on this connected machine)

Snowflake Postgres is fully-managed standard Postgres; provision it, then point `DATABASE_URL`
at it — no app code changes.

```sql
-- Needs the CREATE POSTGRES INSTANCE privilege (ACCOUNTADMIN by default):
--   GRANT CREATE POSTGRES INSTANCE ON ACCOUNT TO <role>;
CREATE POSTGRES INSTANCE contracts_app
  COMPUTE_FAMILY           = '<size>'    -- see Snowflake "Instance Sizes"
  STORAGE_SIZE_GB          = 50          -- 10 .. 65535
  AUTHENTICATION_AUTHORITY = POSTGRES
  POSTGRES_VERSION         = 16          -- 16 | 17 | 18
  HIGH_AVAILABILITY        = TRUE;
```
The command (or Snowsight: **Create → Postgres Instance**) returns the **hostname**
(e.g. `abcefg.snowflake.app`, port `5432`) plus credentials for the `snowflake_admin` and
`application` roles in `access_roles`. **They are shown once — save them.** SSL is required.

Set in `backend/.env` (note `+psycopg` driver and `?sslmode=require`):
```
DATABASE_URL=postgresql+psycopg://snowflake_admin:<password>@<host>.snowflake.app:5432/postgres?sslmode=require
```
Build the schema (from `backend/`):
```
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
# then run the raw-SQL objects: Part G (bid_line_performance view), Part I (pg_trgm + indexes)
```

### B.1 Enums
```sql
CREATE TYPE unit_type    AS ENUM ('COMPANY','SEGMENT','REGION','OFFICE');
CREATE TYPE role_level   AS ENUM ('IC','OFFICE_MANAGER','REGIONAL_DIRECTOR','SEGMENT_LEAD','LEADERSHIP','ADMIN');
CREATE TYPE source_system AS ENUM ('QUICKBASE','DOCUSIGN','MANUAL');
CREATE TYPE map_status   AS ENUM ('AUTO_SUGGESTED','CONFIRMED','USER_ADDED','EXCLUDED');
CREATE TYPE user_source  AS ENUM ('SYNCED','MANUAL');   -- app_user.source (org-access-v2)
```

### B.2 Org hierarchy + fast subtree lookups
```sql
CREATE TABLE org_unit (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    unit_type   unit_type NOT NULL,
    parent_id   UUID REFERENCES org_unit(id),
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT TRUE,   -- org-access-v2: sales-planning sync creates units FALSE for admin review
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Closure table: one row per (ancestor, descendant) incl. self (depth 0).
CREATE TABLE org_closure (
    ancestor_id   UUID NOT NULL REFERENCES org_unit(id) ON DELETE CASCADE,
    descendant_id UUID NOT NULL REFERENCES org_unit(id) ON DELETE CASCADE,
    depth         INT  NOT NULL,
    PRIMARY KEY (ancestor_id, descendant_id)
);
CREATE INDEX idx_org_closure_desc ON org_closure(descendant_id);

-- Rebuild closure from org_unit (run after any tree change):
-- WITH RECURSIVE tree AS (
--   SELECT id AS ancestor_id, id AS descendant_id, 0 AS depth FROM org_unit
--   UNION ALL
--   SELECT t.ancestor_id, c.id, t.depth+1
--   FROM tree t JOIN org_unit c ON c.parent_id = t.descendant_id)
-- INSERT INTO org_closure SELECT * FROM tree
-- ON CONFLICT (ancestor_id, descendant_id) DO UPDATE SET depth = EXCLUDED.depth;
```

### B.3 App users
```sql
CREATE TABLE app_user (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth0_sub      TEXT UNIQUE NOT NULL,            -- Auth0 'sub' claim
    email          TEXT UNIQUE NOT NULL,
    display_name   TEXT,
    role_level     role_level NOT NULL DEFAULT 'IC',
    home_office_id UUID REFERENCES org_unit(id),    -- the office the user belongs to
    scope_unit_id  UUID REFERENCES org_unit(id),    -- node defining visibility (office/region/segment/root)
    source           user_source NOT NULL DEFAULT 'MANUAL', -- org-access-v2: SYNCED (sales-planning) | MANUAL (admin)
    source_broker_id TEXT,                                  -- sales-planning customer_broker_number (sync match key)
    role_locked      BOOLEAN NOT NULL DEFAULT FALSE,        -- admin override; sync won't reset role/scope
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### B.4 Contracts (header) and bid lines (the matchable grain)
```sql
CREATE TABLE contract (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_source_id    TEXT NOT NULL,              -- QB ID / DocuSign id (the contract grain)
    source_system         source_system NOT NULL DEFAULT 'QUICKBASE',
    customer_group_number TEXT NOT NULL,
    customer_group_name   TEXT,
    bid_year              INT,
    region                TEXT,
    source_status         TEXT,                       -- EXECUTED / DRAFT DONE / ...
    owner_user_id         UUID REFERENCES app_user(id),  -- who entered the deal
    office_id             UUID REFERENCES org_unit(id),  -- denormalized = owner's office (RLS)
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_system, contract_source_id)
);
CREATE INDEX idx_contract_office  ON contract(office_id);
CREATE INDEX idx_contract_cust    ON contract(customer_group_number);

CREATE TABLE bid_line (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id       UUID NOT NULL REFERENCES contract(id) ON DELETE CASCADE,
    -- line identity (grade x supplier x port):
    port              TEXT NOT NULL,                  -- matches LIFT.PORT (PORT_NAME)
    grade             TEXT,                           -- loose match
    supplier_number   TEXT,
    supplier_name     TEXT,
    -- pricing (user-entered):
    index_symbol      TEXT,                           -- MARKET_PRICES_HISTORY_V.symbol
    formula           TEXT,                           -- symbol + index name
    price_uom         TEXT REFERENCES lkp_price_uom(code),
    selling_premium   NUMERIC(18,4),
    buying_premium    NUMERIC(18,4),
    margin            NUMERIC(18,4) GENERATED ALWAYS AS (selling_premium - buying_premium) STORED,
    freight_type      TEXT REFERENCES lkp_freight_type(code),
    pricing_days      TEXT REFERENCES lkp_pricing_days(code),
    supplier_terms    TEXT,
    contracted_volume NUMERIC(18,3),
    volume_tolerance  TEXT,                           -- '15% +/-', 'Zero to', etc. (free text)
    gross_profit      NUMERIC(20,2)
        GENERATED ALWAYS AS (contracted_volume * (selling_premium - buying_premium)) STORED,
    supply_method     TEXT REFERENCES lkp_supply_method(code),
    spec              TEXT,
    contract_start    DATE,
    contract_end      DATE,
    date_offered      DATE,
    freight_fee       TEXT,
    notes             TEXT,
    bid_notes         TEXT,
    bid_sub_note      TEXT,
    bid_status        TEXT REFERENCES lkp_bid_status(code),
    qb_id             TEXT,                           -- line-level QB id (usually = contract_source_id)
    owner_user_id     UUID REFERENCES app_user(id),
    office_id         UUID REFERENCES org_unit(id),   -- denormalized for RLS
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_dates CHECK (contract_end IS NULL OR contract_start IS NULL OR contract_end >= contract_start),
    UNIQUE (contract_id, port, grade, supplier_number)
);
CREATE INDEX idx_bidline_contract ON bid_line(contract_id);
CREATE INDEX idx_bidline_office   ON bid_line(office_id);
CREATE INDEX idx_bidline_match    ON bid_line(supplier_number, port, grade, contract_start, contract_end);
```

### B.5 LIFT → contract mapping (editable)
```sql
CREATE TABLE lift_contract_map (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bid_line_id     UUID NOT NULL REFERENCES bid_line(id) ON DELETE CASCADE,
    lift_id          TEXT NOT NULL,                    -- from LIFTS_FOR_MATCHING_V.LIFT_ID
    status          map_status NOT NULL DEFAULT 'AUTO_SUGGESTED',
    match_score     NUMERIC(5,2),                     -- optional confidence 0..100
    override_reason TEXT,                             -- 'supplier won''t honor pricing', 'grade override', ...
    mapped_by       UUID REFERENCES app_user(id),
    mapped_at       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (bid_line_id, lift_id)
);
CREATE INDEX idx_map_lift  ON lift_contract_map(lift_id);
CREATE INDEX idx_map_line ON lift_contract_map(bid_line_id);
```

### B.6 Lookups (the `new_*` pick-lists) — create BEFORE bid_line (it references them)
```sql
CREATE TABLE lkp_price_uom    (code TEXT PRIMARY KEY, label TEXT, sort_order INT, is_active BOOLEAN DEFAULT TRUE);
CREATE TABLE lkp_freight_type (code TEXT PRIMARY KEY, label TEXT, sort_order INT, is_active BOOLEAN DEFAULT TRUE);
CREATE TABLE lkp_pricing_days (code TEXT PRIMARY KEY, label TEXT, sort_order INT, is_active BOOLEAN DEFAULT TRUE);
CREATE TABLE lkp_bid_status   (code TEXT PRIMARY KEY, label TEXT, sort_order INT, is_active BOOLEAN DEFAULT TRUE);
CREATE TABLE lkp_supply_method(code TEXT PRIMARY KEY, label TEXT, sort_order INT, is_active BOOLEAN DEFAULT TRUE);

INSERT INTO lkp_price_uom(code,label,sort_order) VALUES
  ('MT','Metric Ton',1),('USG','US Gallon',2),('BBL','Barrel',3),('GAL','Gallon',4);
INSERT INTO lkp_bid_status(code,label,sort_order) VALUES
  ('WON','Won',1),('LOST','Lost',2),('PENDING','Pending',3);
INSERT INTO lkp_supply_method(code,label,sort_order) VALUES
  ('BARGE','Barge',1),('TRUCK','Truck',2),('PIPELINE','Pipeline',3),
  ('BARGE OR TRUCK','Barge or Truck',4),('BARGE / TRUCK','Barge / Truck',5);
-- lkp_freight_type / lkp_pricing_days: seed from the real `new_freight_type` / `new_pricing days`
-- source tables referenced in the data dictionary (confirm canonical values before seeding).
```

### B.7 Audit + per-segment view config
```sql
CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id   UUID,
    action      TEXT NOT NULL,                        -- INSERT | UPDATE | DELETE
    changed_by  UUID REFERENCES app_user(id),
    changed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    before      JSONB,
    after       JSONB
);
CREATE TABLE segment_view_config (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    segment_unit_id UUID REFERENCES org_unit(id),
    config          JSONB NOT NULL DEFAULT '{}',      -- columns/dashboards/filters per segment
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## PART C — Matcher logic (runs in the API; reads Snowflake, writes Postgres)

For each active bid_line, find candidate Lifts from `LIFTS_FOR_MATCHING_V`:

```
AUTO_SUGGESTED when ALL of:
  lift.CUSTOMER_GROUP_NUMBER = contract.customer_group_number        (exact)
  lift.SUPPLIER_NUMBER       = bid_line.supplier_number              (exact; skip if line supplier blank)
  lift.PORT                  = bid_line.port                         (exact — port is the grain)
  grade_matches(lift.GRADE, bid_line.grade)                          (loose: equal OR same grade-group)
  lift.LIFT_DATE BETWEEN bid_line.contract_start AND bid_line.contract_end
```
- Upsert results into `lift_contract_map` as `AUTO_SUGGESTED`.
- **Never** modify rows already `CONFIRMED`, `USER_ADDED`, or `EXCLUDED` (human edits win).
- Manual actions bypass grade/supplier checks (e.g. HSFO LIFT → VLSFO line) → `USER_ADDED`.
- A bid_line's **actuals** = Lifts in `lift_contract_map` where `status <> 'EXCLUDED'`.
- Reporting per line: `SUM(VOLUME_TONS)`, `SUM(GP)`, `SUM(GP)/NULLIF(SUM(VOLUME_TONS),0)` AS
  actual margin — compare to `contracted_volume`, `margin`, `gross_profit`. (Reuse the metric
  rules in `snowflake_client.py`: margin is always a ratio of aggregates, never averaged.)

---

## PART D — Intake sync (CONTRACT_INTAKE → contract/bid_line)

1. Read `CONTRACT_INTAKE` (Snowflake).
2. Group rows by `CONTRACT_SOURCE_ID` → upsert `contract` (on `(source_system, contract_source_id)`).
   Fallback group key `customer_group_number + bid_year` when `CONTRACT_SOURCE_ID` is null.
3. For each row → upsert `bid_line` on `(contract_id, port, grade, supplier_number)`.
4. **Preserve user-entered fields** (premiums, tolerance, notes, freight_fee, bid_sub_note) — only
   set them from intake if currently null; never overwrite a user value.
5. Set `owner_user_id` / `office_id` on first creation (default to the loader/admin; reassign in app).
6. Log rows that fail validation to an intake-exceptions view.

---

## PART E — Testing on the Snowflake-connected machine
- Verify `LIFTS_FOR_MATCHING_V` returns rows and `LIFT_ID` is unique.
- Load a small `CONTRACT_INTAKE` sample (real QB export) → run intake sync → confirm
  contract/bid_line counts and grouping.
- Run the matcher → spot-check `AUTO_SUGGESTED` rows against known contracts.
- Re-run the matcher after a manual `EXCLUDED`/`USER_ADDED` edit → confirm edits are preserved.
- Validate RLS: seed 4–5 users at different levels, confirm each query returns only their subtree.

---

# SESSION-2 ADDITIONS (dimensions, performance/risk, export, search)

## B.5+ Denormalize LIFT facts onto the mapping (so performance is pure-Postgres)
The matcher captures each mapped LIFT's volume/GP/date into `lift_contract_map`, so the dashboard
and export never need a cross-store join at read time.
```sql
ALTER TABLE lift_contract_map
  ADD COLUMN lift_lift_date   DATE,
  ADD COLUMN lift_volume_tons NUMERIC(18,3),
  ADD COLUMN lift_gp          NUMERIC(20,2);
```
Also add a numeric tolerance to `bid_line` (parsed from the free-text `volume_tolerance` on entry):
```sql
ALTER TABLE bid_line ADD COLUMN tolerance_pct NUMERIC(6,4) DEFAULT 0.10;  -- 0.10 = 10%
```

## PART F — Dimension tables (Postgres) + Snowflake source queries

### F.1 Postgres `dim_*` (workbench is PICK-FROM-LIST ONLY — no free text)
```sql
CREATE TABLE dim_port     (port TEXT PRIMARY KEY, region TEXT, is_active BOOLEAN DEFAULT TRUE, synced_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE dim_customer (customer_group_number TEXT PRIMARY KEY, customer_group_name TEXT, is_active BOOLEAN DEFAULT TRUE, synced_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE dim_supplier (supplier_number TEXT PRIMARY KEY, supplier_name TEXT, is_active BOOLEAN DEFAULT TRUE, synced_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE dim_grade    (grade TEXT PRIMARY KEY, grade_group TEXT, is_active BOOLEAN DEFAULT TRUE, synced_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE dim_index    (symbol TEXT PRIMARY KEY, index_name TEXT, is_active BOOLEAN DEFAULT TRUE, synced_at TIMESTAMPTZ DEFAULT now());
```

### F.2 Snowflake source queries the sync job runs (then upserts into the `dim_*` above)
```sql
-- ports (region grouping per REPO_BRIEF: REGION = grouping of LOC_COUNTRY)
SELECT DISTINCT PORT_NAME AS PORT, ‹REGION_EXPR› AS REGION
FROM SALES_ACTUALS_V WHERE PORT_NAME IS NOT NULL;
-- customers
SELECT DISTINCT ‹CUSTOMER_GROUP_NUMBER› AS CUSTOMER_GROUP_NUMBER, CUSTOMER_NAME AS CUSTOMER_GROUP_NAME
FROM SALES_ACTUALS_V WHERE ‹CUSTOMER_GROUP_NUMBER› IS NOT NULL;
-- suppliers
SELECT DISTINCT ‹SUPPLIER_NUMBER› AS SUPPLIER_NUMBER, SUPPLIER_NAME AS SUPPLIER_NAME
FROM SALES_ACTUALS_V WHERE ‹SUPPLIER_NUMBER› IS NOT NULL;
-- grades (+ optional grade group for loose matching)
SELECT DISTINCT ‹GRADE_NAME› AS GRADE, ‹GRADE_GROUP_EXPR› AS GRADE_GROUP
FROM SALES_ACTUALS_V WHERE ‹GRADE_NAME› IS NOT NULL;
-- index symbols
SELECT DISTINCT SYMBOL, ‹INDEX_NAME_EXPR› AS INDEX_NAME
FROM MARKET_PRICES_HISTORY_V WHERE SYMBOL IS NOT NULL;
```
**Sync semantics:** `INSERT ... ON CONFLICT (pk) DO UPDATE SET ... , synced_at = now()`; values no
longer present are soft-deactivated (`is_active = FALSE`), never hard-deleted (they may be
referenced by existing bid lines). The **"refresh" endpoint is available to all users** and is
rate-limited (e.g. min 5-minute interval, shared lock) so concurrent clicks don't hammer the warehouse.

## PART G — `bid_line_performance` (Postgres view; powers dashboard + export)
```sql
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
```
$ GP at risk = `SUM(contracted_gp)` where `risk_status IN ('AT_RISK','WATCH')`, RLS-scoped.

## PART H — Snowflake export/reporting tables (in-app APScheduler upserts these)
```sql
-- CURRENT state (idempotent upsert each run; one row per bid line)
CREATE TABLE IF NOT EXISTS CONTRACTS_APP.CONTRACT_PERFORMANCE (
    BID_LINE_ID         VARCHAR, CONTRACT_ID VARCHAR, CONTRACT_SOURCE_ID VARCHAR,
    CUSTOMER_GROUP_NUMBER VARCHAR, CUSTOMER_GROUP_NAME VARCHAR,
    PORT VARCHAR, GRADE VARCHAR, SUPPLIER_NUMBER VARCHAR,
    CONTRACTED_VOLUME NUMBER(18,3), ACTUAL_VOLUME NUMBER(18,3),
    CONTRACTED_GP NUMBER(20,2), ACTUAL_GP NUMBER(20,2),
    CONTRACTED_MARGIN NUMBER(18,4), ACTUAL_MARGIN NUMBER(18,4),
    RISK_STATUS VARCHAR, BID_STATUS VARCHAR,
    OWNER_EMAIL VARCHAR, OFFICE VARCHAR, REGION VARCHAR, SEGMENT VARCHAR,
    SNAPSHOT_AT TIMESTAMP_NTZ
);
-- APPEND-ONLY history = the backup copy (point-in-time recoverable)
CREATE TABLE IF NOT EXISTS CONTRACTS_APP.CONTRACT_PERFORMANCE_HISTORY
    LIKE CONTRACTS_APP.CONTRACT_PERFORMANCE;
```
Each run: `MERGE` into `CONTRACT_PERFORMANCE` on `BID_LINE_ID`; `INSERT` the same rows into
`CONTRACT_PERFORMANCE_HISTORY` with the run's `SNAPSHOT_AT`. DR also covered by Snowflake Postgres
native continuous backups.

## PART I — Search indexes (Postgres `pg_trgm` for fuzzy)
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_contract_custname_trgm ON contract USING gin (customer_group_name gin_trgm_ops);
CREATE INDEX idx_bidline_port_trgm      ON bid_line USING gin (port gin_trgm_ops);
CREATE INDEX idx_bidline_supplier_trgm  ON bid_line USING gin (supplier_name gin_trgm_ops);
CREATE INDEX idx_bidline_notes_trgm     ON bid_line USING gin (notes gin_trgm_ops);
```
All search/filter endpoints apply the **org-subtree RLS filter** before returning results.
