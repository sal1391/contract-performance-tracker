# Fuel Contract Tracker — Backend (FastAPI)

Python API for the contract-performance app. Develop locally against plain Postgres; deploy to
Snowflake Postgres. See `../docs/` for the full design and the Snowflake/Coco build spec.

## Run locally (no Snowflake needed)

Prereq: **Docker Desktop running** (for Postgres). Commands below are PowerShell.

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt   # core deps only; no Snowflake
Copy-Item .env.example .env                                    # AUTH0_ENABLED=false -> dev ADMIN user

docker compose up -d db                                        # local Postgres on :5432

# Fast path: create tables + view + demo data in one shot
.venv\Scripts\python.exe -m scripts.init_db

.venv\Scripts\python.exe -m uvicorn app.main:app --reload      # http://localhost:8000
#   docs: /docs   admin: /admin   health: /healthz
```

Using `.venv\Scripts\python.exe -m ...` avoids PowerShell execution-policy prompts (no need to
activate the venv). To activate instead: `.venv\Scripts\Activate.ps1`.

### Proper migrations (instead of init_db)
Once Postgres is up you can use Alembic for real schema management:
```powershell
.venv\Scripts\python.exe -m alembic revision --autogenerate -m "init schema"
.venv\Scripts\python.exe -m alembic upgrade head
```
(init_db is just a convenience that also seeds demo data and the bid_line_performance view.)

## Tests
```bash
pytest            # pure-logic tests (matcher, RLS, at-risk) — no DB required
```

## Layout
```
app/
  config.py          settings (dual local/prod)
  db.py              engine + session + Base
  models.py          all tables (mirrors COCO_BUILD_SPEC.md Part B)
  auth.py            Auth0 JWT + scope resolution (org-subtree RLS)
  rls.py             pure visibility logic (unit-tested)
  deps.py            scoped_filter() applied to every query
  schemas.py         Pydantic read models
  admin.py           sqladmin auto-admin (/admin)
  routers/           contracts, bid_lines, mapping, dimensions, dashboard
  services/
    matcher.py       pure LIFT->bid_line match logic (unit-tested)
    matcher_runner.py  DB+Snowflake matcher job (stub — needs Snowflake)
    performance.py   pure at-risk computation (unit-tested)
    dimensions.py    Snowflake->Postgres dim sync (stub — needs Snowflake)
    intake.py        CONTRACT_INTAKE -> contract/bid_line (stub — needs Snowflake)
    export.py        Postgres -> Snowflake reporting (stub — needs Snowflake)
alembic/             migrations
tests/               matcher / rls / performance
```

## What needs the Snowflake-connected machine
The `*_runner` / `dimensions` / `intake` / `export` services are stubs that raise without a
Snowflake connection. Implement them per `../docs/snowflake/COCO_BUILD_SPEC.md` (Parts C, D, F, H).
The scheduler (`SCHEDULER_ENABLED=true`) wires them to run every few hours.
