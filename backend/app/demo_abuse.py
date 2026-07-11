"""Abuse protection for the demo email gate (FastAPI variant).

Two layers apply to the ``POST /api/demo/gate`` endpoint:

1. Per-IP rate limiting — in-memory, per-process (resets on deploy, which is an
   acceptable tradeoff for a low-traffic demo, per the anti-bot handoff).
2. Cloudflare Turnstile — env-gated and OFF unless both TURNSTILE_SITE_KEY and
   TURNSTILE_SECRET_KEY are set. ``verify_turnstile`` returns True while disabled
   so the gate keeps working until keys are provisioned in Railway.

The honeypot check itself lives in the router (it's a one-line field check on
the request payload); this module only holds the reusable rate-limit/IP/
Turnstile helpers, mirroring the pattern in the agentic-sql-analyst demo gate.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.parse
import urllib.request

from fastapi import Request

# --- Rate limiting -----------------------------------------------------------
RATE_LIMIT_MAX = int(os.getenv("DEMO_RATE_LIMIT_MAX", "5"))
RATE_LIMIT_WINDOW_SEC = int(os.getenv("DEMO_RATE_LIMIT_WINDOW_SEC", str(60 * 60)))

_lock = threading.Lock()
_hits: dict[str, list[float]] = {}


def _now() -> float:
    return time.time()


def is_rate_limited(ip: str) -> bool:
    """True if this IP has used up its allowance in the window.

    Does not record the attempt — call ``record_attempt`` once a submission is
    accepted. An empty IP (caller unidentifiable) is never blocked.
    """
    if not ip:
        return False
    cutoff = _now() - RATE_LIMIT_WINDOW_SEC
    with _lock:
        recent = [t for t in _hits.get(ip, []) if t >= cutoff]
        _hits[ip] = recent
        return len(recent) >= RATE_LIMIT_MAX


def record_attempt(ip: str) -> None:
    """Record an accepted submission timestamp for this IP."""
    if not ip:
        return
    cutoff = _now() - RATE_LIMIT_WINDOW_SEC
    with _lock:
        recent = [t for t in _hits.get(ip, []) if t >= cutoff]
        recent.append(_now())
        _hits[ip] = recent


def reset() -> None:
    """Test hook — clear all recorded attempts."""
    with _lock:
        _hits.clear()


# --- Client IP (FastAPI) ------------------------------------------------------
def get_client_ip(request: Request) -> str:
    """Best-effort client IP: Railway's X-Forwarded-For header, else the socket peer."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else ""


# --- Cloudflare Turnstile (env-gated, OFF by default) ------------------------
_SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def turnstile_enabled() -> bool:
    return bool(os.getenv("TURNSTILE_SITE_KEY") and os.getenv("TURNSTILE_SECRET_KEY"))


def verify_turnstile(token: str, ip: str = "") -> bool:
    """Verify a Turnstile token. Returns True when Turnstile is disabled so the
    gate keeps working until keys are provisioned."""
    if not turnstile_enabled():
        return True
    data = urllib.parse.urlencode(
        {
            "secret": os.getenv("TURNSTILE_SECRET_KEY", ""),
            "response": token or "",
            "remoteip": ip or "",
        }
    ).encode()
    try:
        with urllib.request.urlopen(_SITEVERIFY_URL, data=data, timeout=5) as resp:
            payload = json.loads(resp.read().decode())
        return bool(payload.get("success"))
    except Exception:
        return False
