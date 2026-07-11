"""FastAPI entrypoint: routers + sqladmin + the three scheduled data jobs (APScheduler)."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.admin import setup_admin
from app.config import get_settings
from app.db import SessionLocal, engine
from app.routers import accounts, bid_lines, contracts, dashboard, dev, dimensions, mapping, org, lifts
from app.services.dimensions import refresh_dimensions
from app.services.export import export_performance
from app.services.matcher_runner import run_matcher
from app.services.org_sync import sync_org_from_sales_planning

log = logging.getLogger("contracts")
settings = get_settings()
scheduler = BackgroundScheduler()


def _run(job_name: str, fn) -> None:
    """Run a data job with its own session; Snowflake-less envs log and skip."""
    db = SessionLocal()
    try:
        fn(db, sf_conn=None)  # TODO: pass a real Snowflake connection in prod
    except (RuntimeError, NotImplementedError) as exc:
        log.warning("job %s skipped: %s", job_name, exc)
    except Exception:  # noqa: BLE001
        log.exception("job %s failed", job_name)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.demo_seed:
        try:
            from scripts.seed_demo import run_full_seed
            run_full_seed()
        except Exception:  # noqa: BLE001 — a seed failure must never block boot
            log.exception("demo seed failed — continuing without demo data")
    if settings.scheduler_enabled:
        scheduler.add_job(lambda: _run("dimension_sync", refresh_dimensions),
                          "interval", seconds=settings.dimension_sync_interval, id="dimension_sync")
        scheduler.add_job(lambda: _run("matcher", run_matcher),
                          "interval", seconds=settings.matcher_interval, id="matcher")
        scheduler.add_job(lambda: _run("export", export_performance),
                          "interval", seconds=settings.export_interval, id="export")
        scheduler.add_job(lambda: _run("org_sync", sync_org_from_sales_planning),
                          "interval", seconds=settings.org_sync_interval, id="org_sync")
        scheduler.start()
        log.info("scheduler started")
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Fuel Contract Tracker API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def read_only_guard(request: Request, call_next):
    """Public-demo safety: when READ_ONLY is set, block data-changing requests so visitors
    can browse everything but not alter the seeded data. Reads (GET) stay fully open — no
    login. The auto-match action is exempt so the mapping demo still works."""
    if (settings.read_only and request.method in _WRITE_METHODS
            and not request.url.path.endswith("/auto-match")):
        return JSONResponse(status_code=403,
                            content={"detail": "This is a read-only demo — changes are disabled."})
    return await call_next(request)


for r in (contracts.router, bid_lines.router, mapping.router, dimensions.router,
          dashboard.router, lifts.router, org.router, dev.router, accounts.router):
    app.include_router(r, prefix="/api")

setup_admin(app, engine)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "env": settings.app_env}


# --- Built-SPA serving (single-service deploys; off locally where Vite serves the UI) ---
_static = Path(settings.static_dir) if settings.static_dir else None
if _static and _static.is_dir():
    app.mount("/assets", StaticFiles(directory=_static / "assets"), name="spa-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        if full_path in ("api", "admin") or full_path.startswith(("api/", "admin/")):
            raise HTTPException(status_code=404)  # unknown API/admin path stays a JSON 404
        if full_path:
            candidate = (_static / full_path).resolve()
            root = _static.resolve()
            if candidate.is_file() and candidate.is_relative_to(root):
                return FileResponse(candidate)
        return FileResponse(_static / "index.html")
