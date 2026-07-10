# Repo Brief & Domain Wiki — Fuel Contract Tracking

> **Purpose of this file:** Single source of truth so any agent (Claude, GitHub Copilot,
> Snowflake "Coco"/Cortex) can get oriented **without re-reading the whole repo**.
> Update this file whenever a design decision is made.
>
> **Last updated:** 2026-06-24

---

## 1. What this repo is today

This repo (`example-snowflake`) currently contains **"the legacy app"** — an earlier internal
**Streamlit** app for **fuel sales**. It reads fuel transaction data out of **Snowflake**, computes sales
metrics, and uses **Snowflake Cortex** (LLM) + **Perplexity** to generate customer
insights.

It is **not** the contract app yet. It is the reference implementation we are mining for
patterns: Snowflake connection handling, dual local/AWS deployment, Auth0 role-gating,
and the canonical metric/field dictionary.

### Key files
| File | What it is |
|------|-----------|
| `snowflake_client.py` | Snowpark data layer. Connection, metric SQL, Cortex `complete()` helper, token counting. Queries the view `SALES_ACTUALS_V`. |
| `config.py` | Dual-mode config: `DEPLOY_MODE` (`local`/`aws`) + `AUTH0_ENABLED`. Secrets come from env vars (local) or AWS Secrets Manager (prod). |
| `CONFIG_GUIDE.md` | Plain-English explanation of the two config switches. |
| `docs/REPO_BRIEF.md` | This file. |

---

## 2. Tech stack & conventions observed

- **Language:** Python 3.x.
- **Data access:** `snowflake-snowpark-python` (`Session.builder.configs(...).create()`).
- **LLM:** `snowflake.cortex.complete(model, prompt)` run as SQL; default model
  `claude-sonnet-4-5`. Token counting via `AI_COUNT_TOKENS`.
- **UI today:** Streamlit (`streamlit run app.py` — `app.py` not yet in repo).
- **Secrets:** never hardcoded in prod; AWS Secrets Manager key `app_secret_json`.
- **SQL style:** fully-qualified table names built from `database.schema.table`; single
  quotes escaped with a `_sql_escape()` helper (string-inlined, **not** parameterized).

---

## 3. Deployment model (inherited pattern)

`config.py` already encodes a multi-environment model we should reuse:

- **`DEPLOY_MODE = "local"`** → creds from env vars, `AUTH0_ENABLED=false` (no login).
- **`DEPLOY_MODE = "aws"`** → creds from Secrets Manager, `AUTH0_ENABLED=true`.
- **Environments:** `dev`, `test`, `qa`, `psup`, `prod` (from
  `BITBUCKET_DEPLOYMENT_ENVIRONMENT`), mapped to subdomains, e.g.
  `https://app.dev.aws.example.com/`, prod = `https://app.aws.example.com/`.
- **Auth0 today:** `clientId` + `domain` from env; required role **`App:Sales`**.

> Implication for the new app: we already have a working **dev/prod split + Auth0
> role-gating** pattern to copy. The open question is Auth0 vs Microsoft Entra (tenant).

---

## 4. Snowflake data layer (the transactional source)

- **Main view:** `SALES_ACTUALS_V` (FQN built from
  `SNOWFLAKE_DATABASE.SNOWFLAKE_SCHEMA.SNOWFLAKE_TABLE`; local default DB `SANDBOX`,
  schema `ANALYTICS`).
- **Grain:** one row per fuel transaction ("LIFT").
- **Primary date column:** `DELIVERY_DATE` (fuel delivery / expected delivery date).

### Canonical metrics (do not redefine — reuse these)
| Metric | SQL | Rule |
|--------|-----|------|
| `VOLUME` | `SUM(VOLUME_TONS)` | tons delivered |
| `GP` | `SUM(GROSS_PROFIT)` | gross profit USD |
| `MARGIN` | `SUM(GROSS_PROFIT)/NULLIF(SUM(VOLUME_TONS),0)` | **always a ratio of aggregates — never sum/avg a raw margin column** |
| `NUM_WON` | `SUM("WON_FLAG")` | transactions won |
| `NUM_INQUIRIES` | `SUM("INQUIRY_FLAG")` | inquiries (1/row) |
| `NUM_LOST` | `SUM("INQUIRY_FLAG") - SUM("WON_FLAG")` | non-converted |

### Useful dimensions on the view
`CUSTOMER_NAME` (customer), `SUPPLIER_NAME` (supplier), `PORT_NAME` (port), `SUPPLY_TEAM_NAME`,
broker fields (`ACCOUNT_BROKER*`, `CUSTOMER_BROKER`, `CUSTOMER_BROKER_REGION` …),
`DEAL_TYPE`, ship-type groups
(`VESSEL_SHIP_TYPE`, `CUSTOMER_SHIP_TYPE`).

---

## 5. The NEW app's domain — Cruise Contract data dictionary

The table below (from the original bid workbook) defines the fields of a **bid/contract line** as the cruise team
uses them today (in Excel) and how each maps back to Snowflake. **This is the seed schema
for the new app.** Columns in the source: *Field · Description · Examples · Entered by user
(U) · Pre-populated by Snowflake (S) · Calculated (C) · Snowflake source table · Mapping note.*

| Field | Src | Snowflake source / mapping |
|-------|:---:|----------------------------|
| BID YEAR | S | Calendar year of bid (4-digit). Validate it's a real year. |
| REGION | S | Group of `port_location` → {AFRICA, N.AMERICA, EUROPE, N EU, ASIA}. |
| CLIENT | U | Display = `customer_group_name`; **backend joins on `customer_group_number`**. e.g. OCL. |
| PORT | S | `port_location` (free text; may be multi-port `A/B`, `A + B`). |
| GRADE | S | `grade_name` or grouped grade. e.g. VLSFO, MGO, HSFO. |
| SUPPLIER | S | Display = supplier name; **backend joins on `supplier_number`**. |
| INDEX | S | `symbol` from `MARKET_PRICES_HISTORY_V` (Platts/ICE/OPIS ticker). |
| FORMULA | C | Concat of `symbol` + index full name. |
| PRICE UOM | S | Lookup `new_price_uom` table. {MT, USG, BBL, GAL}. |
| SELLING PREMIUM | U | Sell-side premium over index, per UOM (USD). |
| BUYING PREMIUM | U | Buy-side premium over index, per UOM (USD). |
| MARGIN | C | `SELLING PREMIUM − BUYING PREMIUM` (per UOM). |
| FREIGHT | S | Lookup `new_freight_type`. |
| PRICING DAYS | S | Lookup `new_pricing days` (pricing window for index avg). |
| SUPPLIER TERMS | S | `supplier_terms` (e.g. 30DDD). |
| CONTRACTED VOLUME | U | Total contracted volume in UOM. 0/blank = spot. |
| VOLUME TOLERANCE | U | % or text (e.g. "15% +/-", "Zero to"). |
| GROSS PROFIT | C | `CONTRACTED VOLUME × MARGIN`. |
| SUPPLY METHOD | S | Lookup `new_supply_method`. {BARGE, TRUCK, PIPELINE, …}. |
| SPEC | S | `spec` (ISO standard / dye notes). |
| CONTRACT START | U | Date. |
| CONTRACT END | U | Date; must be ≥ CONTRACT START. |
| FREIGHT FEE | U | Free text extra fees. |
| NOTES | U | Internal commercial notes. |
| BID NOTES | U | Client-facing / bid-process notes. |
| DATE OFFERED | U | Date bid offered to client. |
| BID STATUS | S | Lookup `new_bid status`. {WON, LOST, PENDING} (note dirty data: "PEDING"). |
| QB ID # | S | `record_id` from `quick_base` table. Integer; may be slash-joined ("742/743"). |
| QB STATUS | S | `won_or_lost` from `quick_base` table. e.g. EXECUTED, DRAFT DONE. |
| Bid sub note | U | Free text, esp. loss reasons / competitor pricing. |

### Field-source summary
- **User-entered (the editable contract-tracking fields):** SELLING/BUYING PREMIUM,
  CONTRACTED VOLUME, VOLUME TOLERANCE, CONTRACT START/END, DATE OFFERED, FREIGHT FEE,
  NOTES, BID NOTES, Bid sub note. → **these imply the app needs WRITE/storage.**
- **Snowflake pre-populated (joined in):** BID YEAR, REGION, PORT, GRADE, SUPPLIER, INDEX,
  PRICE UOM, FREIGHT, PRICING DAYS, SUPPLIER TERMS, SPEC, SUPPLY METHOD, BID STATUS,
  CLIENT, QB ID #, QB STATUS.
- **Calculated:** FORMULA, MARGIN, GROSS PROFIT.

---

## 6. Source-system map

| System | Object(s) | Role |
|--------|-----------|------|
| **Snowflake — sales planning** | `SALES_ACTUALS_V` | Transactional "actuals" the contract is tracked against. |
| **Snowflake — market prices** | `MARKET_PRICES_HISTORY_V` | Index `symbol` + names for FORMULA. |
| **QuickBase contract app** | `quick_base` table (`record_id`, `won_or_lost`) | High-level legal/commercial contract record (the approval system). |
| **User lookup tables** (built by user, to be created in Snowflake by Coco) | `new_price_uom`, `new_freight_type`, `new_pricing days`, `new_bid status`, `new_supply_method` | Controlled vocabularies / pick-lists. |

---

## 7. The vision for the new app (from the user)

- **Problem:** QuickBase captures *high-level* contract info (customer, port, fuel type,
  quantity) for **legal + commercial approval**. After approval, the team has **no system
  to track how the contract actually performed** against transactional data.
- **Goal:** New web app that (1) pulls high-level info from QuickBase, (2) maps it to
  transactional data in `SALES_ACTUALS_V`, (3) lets the team track outcomes.
- **Rollout:** Cruise team first → rest of the fuel team → entire fuel company.
- **Per-segment custom views** expected (each group wants its own features/filters).
- **Auth:** Auth0 **or** Microsoft tenant (Entra).
- **Deploy:** dev + prod.
- **Stack preference:** **Python backend, React frontend** (user is fluent in React).
- **Hard constraint:** the user's **current machine has NO Snowflake access**. All
  Snowflake table creation + data testing must be handed off (as instructions/memory)
  to **GitHub Copilot + Snowflake Coco** running where Snowflake IS reachable.
- **Open storage question:** plain Snowflake tables vs. "Snowflake Postgres" (user unsure;
  open to either).

---

## 8. Design decisions — RESOLVED 2026-06-24

Full design: [`docs/plans/2026-06-24-contract-tracking-app-design.md`](plans/2026-06-24-contract-tracking-app-design.md).
Build instructions: [`docs/snowflake/COCO_BUILD_SPEC.md`](snowflake/COCO_BUILD_SPEC.md).
**Current build status (done vs. pending):** [`docs/BUILD_STATUS.md`](BUILD_STATUS.md) — a working
local prototype exists (`backend/` + `frontend/`); Auth, real org/RLS, and Snowflake integration
are still pending. Local dev uses plain Postgres + a `lift_source` stand-in for Snowflake.

1. **App type:** full read-write **contract workbench** (replaces the Excel).
2. **Storage:** **Snowflake Postgres** for the app DB (local dev against plain Postgres);
   Snowflake views for actuals + `CONTRACT_INTAKE`.
3. **Backend:** **FastAPI** + SQLAlchemy/Alembic + **`sqladmin`** auto-admin.
4. **Frontend:** **React 19 + Vite + TanStack Query + MUI/MUI X Data Grid**.
5. **Auth:** **Auth0** (authN + coarse claims) + **app-layer org-subtree RLS**.
6. **Visibility:** hierarchical org tree Company→Segment→Region→Office→IC; IC sees whole
   office, scope widens up. Driven by deal owner's office + `org_closure`.
7. **Matching:** auto-match on customer+supplier+port+date (grade loose) + **editable
   `lift_contract_map`** (confirm/unmap/add). Port is the grain; no port groups.
8. **Grain:** `contract` (1 per QB/source ID, 1 customer) → many `bid_line` (grade×supplier×port).
9. **Intake:** source-agnostic `CONTRACT_INTAKE` Snowflake table, user-loaded (QB→DocuSign).
10. **Deploy:** AWS, reusing the the legacy app dev/prod + Secrets Manager pattern.
11. **Reference dimensions** synced Snowflake→Postgres (`dim_*`); **pick-from-list only (no
    free text)**; **refresh button for all users** (rate-limited).
12. **Export Postgres→Snowflake** via in-app APScheduler every few hours, with an **append-only
    snapshot-history backup** (+ Snowflake Postgres native backups).
13. **Leadership dashboard** with **at-risk detection** (pace vs committed volume; $ GP at risk).
14. **CRM-style** Accounts view + won/lost/pending pipeline.
15. **Search/filter** server-side, RLS-scoped, `pg_trgm` fuzzy.

> App = an operational store (Postgres) for bid-level data that **publishes performance to
> Snowflake** for leadership/BI. Three scheduled jobs: dimension sync (in), matcher (in),
> performance export (out).

### Still open (Snowflake side — see COCO_BUILD_SPEC.md §0)
- LIFT primary-key column; exact `SALES_ACTUALS_V` column names (customer/supplier/grade);
  grade-grouping source; Snowflake Postgres connection; Auth0 roles/claims + tenants.

---

## 9. Glossary

- **LIFT** — the per-transaction grain of `SALES_ACTUALS_V`.
- **Bid line** — one row of a contract bid (CLIENT × PORT × GRADE × SUPPLIER).
- **DDD** — "days from delivery date" payment terms (e.g. 30DDD).
- **Index / symbol** — Platts/ICE/OPIS price reference (e.g. FUEL01).
- **Coco** — Snowflake's coding/Cortex agent that will build tables on the Snowflake side.
- **QB** — QuickBase (sometimes written "QuickBooks" in the dictionary — it is QuickBase).
