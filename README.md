# Triton — Fuel Contract Performance Tracker

A web app for the fuel supply team to track how approved fuel contracts **actually perform**
against real lift transactions. Contracts are approved in an external system (QuickBase today,
DocuSign later) that captures only high-level terms; after approval there has been no system to
measure contracted-vs-actual volume, margin, and gross profit. Triton fills that gap: it ingests
approved contract headers, lets the team maintain detailed bid lines, auto-maps each line to its
actual fuel-lift transactions (Lifts), and reports performance — with per-segment, row-level
visibility driven by the org hierarchy.

> Status: **working local prototype**. Core flow (Bids, LIFT mapping, dashboard, org tree + RLS,
> access model) is built and runs locally on plain Postgres. Snowflake integration and Auth0 login
> are the remaining phases. See [`docs/BUILD_STATUS.md`](docs/BUILD_STATUS.md) for the honest
> done/pending list.

## Architecture

```
Snowflake (read-only sources)                 Snowflake Postgres (app DB, read-write)
  SALES_ACTUALS_V  ── LIFT actuals        org_unit / org_closure / app_user
  LIFTS_FOR_MATCHING_V       ── matcher input      contract / bid_line / lift_contract_map
  CONTRACT_INTAKE          ── approved headers    lkp_* / dim_* / audit_log
  MARKET_PRICES_HISTORY_V── index/formula                │
            │  (scheduled jobs pull → push)                │  read/write
            └───────────────► FastAPI API ◄───────────────┘
                                  │  JSON + Auth0 JWT
                                  ▼
                            React SPA (Vite)
                    Bids · Mapping · Dashboard · Accounts · Admin
```

- **Operational store is Postgres** (Snowflake Postgres in prod, plain Postgres locally). The app
  reads/writes it via SQLAlchemy.
- **Snowflake is the read-only source of "actuals"** and the BI sink. Five scheduled jobs move data:
  dimension sync, contract intake, the LIFT matcher, org provisioning (Snowflake → Postgres), and a
  performance export (Postgres → Snowflake). See [`docs/snowflake/COCO_BUILD_SPEC.md`](docs/snowflake/COCO_BUILD_SPEC.md).
- **Visibility** is an org-subtree rule enforced server-side on every query (`app/rls.py` +
  `deps.scoped_filter`): you see a deal if its owning office is within your scope node's subtree.

## Tech stack

- **Backend:** FastAPI · SQLAlchemy 2.0 · Alembic · `sqladmin` · APScheduler · Postgres
- **Frontend:** React 19 · Vite · TanStack Query · MUI / MUI X Data Grid
- **Auth (planned):** Auth0 (PKCE) + app-layer org-subtree RLS
- **Data:** Snowflake (sources + BI) · Snowflake Postgres (app DB)

## Repo layout

```
backend/    FastAPI service (app/), Alembic migrations, tests, scripts/init_db.py
frontend/   React + Vite SPA
docs/       REPO_BRIEF, design + build docs, and docs/snowflake/ (Coco/Cortex build spec + prompt)
snowflake_client.py   legacy reference client (confirmed source columns + metric rules)
```

## Local development

Requires Docker (for Postgres), Python 3.12+, and Node 20+.

```bash
# Backend (from backend/)
docker compose up -d db
python -m scripts.init_db            # seeds reference data, org tree, sample Lifts (no hardcoded contracts)
uvicorn app.main:app --reload        # http://localhost:8000  (/docs for OpenAPI, /admin for sqladmin)

# Frontend (from frontend/)
npm install
npm run dev                          # http://localhost:5173 (proxies /api → :8000)
```

Auth is off locally (`AUTH0_ENABLED=false`); a dev **"Act as"** switch (top-right) impersonates any
seeded user so you can verify org-subtree visibility (IC → office, regional → region, segment, and
leadership → all) without Auth0.

Run the backend tests: `python -m pytest -q` (from `backend/`).

## Snowflake integration

The Snowflake objects, Snowflake Postgres provisioning, and the five sync jobs are built on a
Snowflake-connected machine. Everything needed is in:

- [`docs/snowflake/COCO_BUILD_SPEC.md`](docs/snowflake/COCO_BUILD_SPEC.md) — DDL, provisioning (§B.0),
  matcher/intake/dimension/export logic, and the blocking data questions (§0).
  Snowflake-connected coding agent.

## Demo mode & Railway

The app auto-seeds a deterministic demo dataset (6 contracts, 12 bid lines, ~55 lifts —
every dashboard risk status represented, dates anchored to "today") on first boot when
`DEMO_SEED=true` (the default). A single-service Docker image (React build served by
FastAPI) deploys to Railway in ~5 minutes — see [`DEPLOY.md`](DEPLOY.md).

## Documentation

- [`docs/REPO_BRIEF.md`](docs/REPO_BRIEF.md) — domain + data dictionary
- [`docs/plans/2026-06-24-contract-tracking-app-design.md`](docs/plans/2026-06-24-contract-tracking-app-design.md) — design + decision log
- [`docs/BUILD_STATUS.md`](docs/BUILD_STATUS.md) — what's built vs. pending
