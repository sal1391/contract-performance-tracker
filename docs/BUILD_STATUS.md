# Build Status — Fuel Contract Tracking App

> Honest snapshot of what is **built and verified** vs. **still pending**.
> Branch: `feat/contract-tracker` (not pushed). **Last updated:** 2026-06-24.
>
> Short answer: a **working local prototype of the core flow is done**; **the build is NOT
> complete** — Auth, the real org/RLS, and all Snowflake integration are still pending.

---

## ✅ Built & verified (local — API + browser)

**Backend (FastAPI + SQLAlchemy + Postgres)**
- Contracts: `GET /contracts` (with `?q=` search on QB ID + customer), `POST`, `PATCH`, `GET /{id}`.
- Bid lines: `GET /bid-lines` (full Excel field set + contract context), `POST`, `PATCH`,
  `POST /{id}/auto-match`.
- Mapping: `GET /mappings/by-line/{id}`, `POST /{id}/confirm`, `POST /{id}/exclude`, `POST` (manual add).
- Lifts: `GET /lifts`. Dimensions: lists + `/lookups` + `/refresh` (stub). Dashboard: `/summary` (at-risk).
- Org-subtree **RLS scaffold** (`rls.py` + `deps.scoped_filter`) applied to every query — now
  **live & testable**: org tree CRUD (`/org/*`) auto-maintains `org_closure`; `X-Dev-User`
  act-as header resolves a chosen user; new bids stamp the acting user's office.
- Pure, unit-tested logic: matcher, RLS resolver, at-risk, **org closure** — **24 tests pass**.
- `sqladmin` mounted at `/admin` (open in dev).

**Frontend (React 19 + Vite + MUI)**
- **Dashboard** — at-risk tiles + $ GP at risk.
- **Bids** — search; create/edit/**delete** (with confirm) contracts (QB header: QB ID, client,
  year, region, QB status, **bid sub note + owning office**) and bid lines (full Excel dictionary);
  master/detail; computed margin + GP; Sell/Buy/Margin shown to 2dp; **Tol. +/- as a percent**;
  **Index auto-fills Formula**. `+ New Bid` saves as source **MANUAL** (intake rows = QUICKBASE).
- **Mapping** — pick a line, Run auto-match, confirm/unmap, map available Lifts.
- **Admin** — manage the org tree (Company→Segment→Region→Office, closure auto-rebuilt) + users
  (role, scope unit, home office). **Act-as switch** (top-right, dev only) impersonates any user.

**Local dev substitutes (so it runs without Snowflake)**
- App DB = **plain Postgres in Docker** (stand-in for Snowflake Postgres — same SQL).
- `lift_source` table = **local stand-in for Snowflake `LIFTS_FOR_MATCHING_V`**; `run_matcher_local`
  matches against it.
- `scripts/init_db.py` seeds reference data (lookups, dimensions) + 6 sample Lifts. **No hardcoded
  contracts/org** — you create bids in the app.

---

## 🧭 Planned sequence (decided 2026-06-24)

1. **Local app features FIRST** — everything in the next section that needs no Snowflake/Auth.
   This **includes the org tree + RLS**, which are testable now via a dev "act as user" switch
   (Auth0 is NOT required to build/validate authorization — see first item below).
2. **Snowflake integration SECOND-TO-LAST** — handed to Coco/Copilot on the connected machine.
3. **Auth0 LOGIN only — LAST** — **GitHub Copilot will do this**. It just swaps the identity
   resolver for real Auth0 tokens; the org tree + `rls.py`/`scoped_filter` built in step 1 are reused as-is.

## ⏳ Pending — local app (no Snowflake needed) — DO THESE FIRST

- [x] **Org tree + RLS — built WITHOUT Auth0** (verified 2026-06-24). (a) `org_unit` CRUD via the
      **Admin** page / `/org/*` API auto-rebuilds `org_closure` (sqladmin path covered too);
      (b) `app_user` create + `scope_unit_id`/`home_office_id` assignment; (c) **dev "act as user"
      switch** — `X-Dev-User` header (set from the top-right dropdown) makes `get_current_user`/
      `get_scope` resolve a chosen user instead of the see-all dev ADMIN. Confirmed IC→office,
      regional→region, segment→segment, leadership→all on the Bids list. Auth0 (last) only swaps
      the identity resolver; `rls.py` + `deps.scoped_filter` unchanged. Demo tree + 5 users seeded
      by `init_db` (idempotent).
- [x] **Access v2 — classification-driven** (2026-06-25): contract office comes from QuickBase
      (inherited by lines/Lifts); bid lines carry a **Customer broker** (`owner_user_id`, attribution,
      not RLS); sales-planning **provisioning sync** (`services/org_sync.py`, stub) auto-creates org
      units + broker users with manual-protection + `is_verified` review. RLS engine unchanged.
- [x] **Delete** for contracts and bid lines (with confirm) — scoped DELETE endpoints + UI dialog.
- [ ] **CRM Accounts view** + **per-segment custom views** (designed, not built).
- [ ] **Alembic migrations** (currently bootstrap via `create_all` in `init_db`).
- [ ] **API/integration tests** (only pure-logic is tested today).
- [ ] `sqladmin` **auth gating** (restrict `/admin` to ADMIN role).
- [x] Niceties: **INDEX→FORMULA autofill** (done). Still open: wire the dimension **refresh**
      button in the UI, broader `pg_trgm` search, code-split the JS bundle.

## ⏳ Pending — Snowflake-connected machine (Coco/Copilot, per `docs/snowflake/COCO_BUILD_SPEC.md`)

- [ ] Resolve **§0 data questions** (LIFT primary key, exact `SALES_ACTUALS_V` column
      names, grade grouping).
- [ ] Build `CONTRACT_INTAKE` table + `LIFTS_FOR_MATCHING_V` view.
- [ ] Implement the real jobs — currently **stubs that raise without a Snowflake connection**:
      `services/matcher_runner.run_matcher`, `services/dimensions.refresh_dimensions`,
      `services/intake.sync_contract_intake`, `services/export.export_performance`.
- [ ] Snowflake reporting/export tables (`CONTRACT_PERFORMANCE` + `_HISTORY`); enable the
      APScheduler jobs with a real Snowflake connection.
- [ ] Provision **Snowflake Postgres**; point `DATABASE_URL` at it (app code is unchanged).

## ⏳ Pending — Auth0 + real org/RLS (LAST — GitHub Copilot will do this)

Today auth is bypassed (`AUTH0_ENABLED=false`, dev ADMIN = sees everything). When tackled last:
- [ ] Wire Auth0 login (SPA `@auth0/auth0-react`; API validates JWT — already stubbed in `auth.py`).
- [ ] Populate the **org tree + users** (via `/admin`) and set each `app_user.scope_unit_id`.
- [ ] Flip `AUTH0_ENABLED=true` so the org-subtree RLS is actually enforced (cruise/region/
      segment/leadership). The enforcement code already exists (`rls.py`, `deps.scoped_filter`).

## ⏳ Pending — deployment

- [ ] AWS dev/prod, Secrets Manager, `*.aws.example.com` domains, CI.

---

## How to run locally
See `backend/README.md` and `frontend/README.md`. TL;DR (PowerShell, Docker running):
```
cd backend; docker compose up -d db; .venv\Scripts\python.exe -m scripts.init_db; .venv\Scripts\python.exe -m uvicorn app.main:app
cd frontend; npm run dev    # http://localhost:5173 (or next free port)
```
