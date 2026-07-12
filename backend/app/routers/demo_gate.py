"""Env-gated demo access gate (DEMO_MODE only), with anti-bot protection.

This endpoint exists purely to gate the public Railway demo behind a Start
action before the app is shown — it has nothing to do with Auth0, which stays
completely untouched. No email is collected; we record the requesting IP
address instead. Order of checks on submit:

1. Honeypot — an off-screen ``website`` field. Real visitors never fill it; a
   non-empty value gets a silent fake success (no rate-limit hit, no log line).
2. Cloudflare Turnstile (env-gated OFF until TURNSTILE_SITE_KEY/SECRET are set).
3. Per-IP rate limit (5/hour by default).

On success the ip + timestamp are printed to stdout so they show up in
Railway logs — there is no database table for this, it's a low-traffic demo.
"""
from __future__ import annotations

import json
import logging
import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.demo_abuse import get_client_ip, is_rate_limited, record_attempt, verify_turnstile

router = APIRouter(prefix="/demo", tags=["demo"])
log = logging.getLogger("contracts")


class DemoGateRequest(BaseModel):
    website: str = ""          # honeypot — must stay empty
    turnstile_token: str = ""


class DemoGateResponse(BaseModel):
    ok: bool


@router.post("/gate", response_model=DemoGateResponse)
def demo_gate(payload: DemoGateRequest, request: Request) -> DemoGateResponse:
    if payload.website.strip():
        # Honeypot tripped — silent fake success, nothing logged or recorded.
        return DemoGateResponse(ok=True)

    ip = get_client_ip(request)

    if not verify_turnstile(payload.turnstile_token, ip):
        raise HTTPException(400, "Verification failed")

    if is_rate_limited(ip):
        raise HTTPException(429, "Too many attempts, try again later")

    record_attempt(ip)
    print(
        f"[demo-gate] {json.dumps({'ip': ip, 'ts': time.time()})}",
        flush=True,
    )
    return DemoGateResponse(ok=True)
