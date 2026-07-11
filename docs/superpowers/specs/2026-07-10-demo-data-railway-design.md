# Demo Data + Railway Deployment — Design

> **Goal:** a fully running app locally with rich fake demo data, and a repo that deploys to
> Railway in ~5 minutes — with **zero changes to the UI code**.
>
> Approved by Carlos on 2026-07-10 (brainstorming session). Implementation code is to be
> written by **Sonnet subagents**; the orchestrating agent plans and reviews.

## Context

Triton (this repo) is a working local prototype: FastAPI + SQLAlchemy + Postgres backend,
React 19 + Vite + MUI frontend, auth off locally with a dev "Act as" impersonation switch.
`scripts/init_db.py` seeds only reference data (lookups, dims, 6 lifts, org tree + 5 users) —
no contracts or bid lines, so every page starts empty. There is no Dockerfile and no
deployment config; the frontend runs as a separate Vite dev server proxying `/api`.

## Decisions (from brainstorming)

| Decision | Choice |
|---|---|
| Data scale | **Medium**: ~6 contracts, ~12 bid lines, ~50 lifts |
| Railway shape | **Single service**: FastAPI serves the built SPA + `/api`; Railway Postgres plugin |
| Seeding trigger | **Auto-seed on startup** (idempotent), gated by `DEMO_SEED` env var (default `true`) |
| Data generation | **Today-anchored deterministic generator** — dates computed relative to `date.today()` so every dashboard risk status is guaranteed regardless of deploy date; no new dependencies |
| Deploy scope | **Deploy-ready + guide** (`DEPLOY.md`); no live deployment in this project |
| Code authorship | **Sonnet subagents** write implementation code |
| Git hygiene | All work on local branch `feat/demo-data-railway`; nothing pushed without approval |

## Component 1 — `backend/scripts/seed_demo.py`

Pure-Python deterministic demo seeder. No new dependencies.

- **Interface:** `python -m scripts.seed_demo` (manual) and `seed_demo(db)` callable from the
  startup hook. Calls the existing `init_db` bootstrap logic first (tables, view, reference
  data, org tree), then layers demo data on top.
- **Idempotency:** if any `Contract` row exists, exit without writing. Restarts never duplicate.
- **Dimensions extended modestly:** ~4 customers (add "Meridian Cruises", "Atlas Bulk
  Carriers"), ~5 ports (add BARCELONA, SINGAPORE), 4 suppliers (add one), grades/indexes as-is.
- **6 contracts** spread across the 4 seeded offices (Cruise Team, New Jersey, Rotterdam,
  Yacht Team) so the "Act as" switch demonstrates org-subtree RLS: the Cruise IC sees ~2,
  the NJ office manager ~1–2, the NA regional director sees NJ's, segment lead and
  leadership see all. Mixed `source` (QUICKBASE / MANUAL), mixed QB statuses, realistic QB
  IDs, notes, and bid sub notes.
- **12 bid lines** (~2 per contract), each *engineered backwards* from a target risk status
  in the `bid_line_performance` view: 3 ON_TRACK, 2 WATCH, 2 AT_RISK, 2 AHEAD, 2 COMPLETE,
  1 not-yet-started/spot. All contract start/end dates are offsets from `date.today()`.
- **~50 `lift_source` rows** generated from each line's target pace (monthly/biweekly
  cadence, 300–2,500 MT, GP ≈ margin × tons with small deterministic variation):
  - ~42 with **CONFIRMED** `lift_contract_map` rows (dashboard + mapping page populated);
  - ~5 matchable but unmapped (live "Run auto-match" demo);
  - ~3 near-miss rows (wrong grade/port) to demonstrate exclusion.
- `init_db.py` behavior is unchanged for anyone using it directly.

## Component 2 — Auto-seed on startup

In `main.py`'s existing `lifespan` hook: when `settings.demo_seed` is true, run
`create_all` + the pg_trgm/view bootstrap + reference seed + demo seed inside a
try/except that logs a warning and continues (a seed failure must not prevent boot).
New setting in `config.py`: `demo_seed: bool = True`.

## Component 3 — Packaging (Dockerfile + SPA serving)

- **Root `Dockerfile`, multi-stage:**
  1. `node:20-alpine`: `npm ci && npm run build` in `frontend/` → `dist/`.
  2. `python:3.12-slim`: install `backend/requirements.txt`, copy `backend/`, copy the
     built `dist/`, `CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`.
- **`main.py` additive change:** new setting `static_dir: str = ""` (empty = SPA serving
  disabled, which is the local-dev default; the Dockerfile sets `STATIC_DIR=/app/static`).
  When set and the directory exists, mount static assets and add an SPA fallback route —
  any path not under `/api`, `/admin`, `/docs`, or `/healthz` returns `index.html`.
  Local dev (Vite proxy) is completely unaffected; no frontend code changes.
- **Config normalization in `config.py`:** rewrite `postgres://` or `postgresql://`
  `DATABASE_URL` values to `postgresql+psycopg://` so Railway's injected URL works as-is.

## Component 4 — Railway config + docs

- **`railway.json`:** Dockerfile builder, healthcheck path `/healthz`, restart on failure.
- **`DEPLOY.md`:** step-by-step — create Railway project → add Postgres plugin → set env
  vars (`DATABASE_URL` reference, `DEMO_SEED=true`) → deploy via `railway up` or GitHub
  connect → open the URL. Includes an env-var table and a "reset the demo data" note
  (delete Postgres volume / re-provision).
- **`.dockerignore`** to keep images small (node_modules, .git, tests, docs).

## Error handling

- Seed failures log and continue; the API still boots (empty pages beat a crash loop).
- Seeder is transactional per phase (reference, org, demo) so partial writes roll back.
- SPA fallback returns 404 JSON for unknown `/api/*` paths (unchanged behavior).

## Testing & verification

1. Existing 24 backend tests pass unchanged (`python -m pytest -q`).
2. New unit test for the risk-status engineering: seed into a fresh DB, query
   `bid_line_performance`, assert every one of the 5 risk statuses is present.
3. Local end-to-end: compose Postgres → auto-seed boot → `/api/dashboard/summary` shows all
   statuses → Vite UI walk-through (Dashboard, Bids, Mapping, Accounts, Admin, Act-as).
4. Production-image rehearsal: `docker build` + run the image locally against compose
   Postgres; verify the SPA serves from FastAPI and all pages work on one origin.

## Out of scope

Auth0, Snowflake integration, AWS deployment, UI changes, pushing to GitHub, live Railway
deployment (covered by `DEPLOY.md` instead).
