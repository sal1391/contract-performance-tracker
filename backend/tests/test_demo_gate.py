"""Tests for the demo access gate (app/routers/demo_gate.py) and its
rate-limiter / honeypot / Turnstile layers (app/demo_abuse.py). No email is
collected — the gate records the requesting IP address instead.

DEMO_MODE only changes what the frontend shows; the endpoint itself is always
importable/callable (see app/routers/demo_gate.py docstring), so no env
gating is needed here.
"""
from __future__ import annotations

from starlette.testclient import TestClient

from app import demo_abuse
from app import main as main_module
from app.main import app

client = TestClient(app)


def setup_function(_fn):
    demo_abuse.reset()


def _post(website="", turnstile_token="", ip="203.0.113.5"):
    return client.post(
        "/api/demo/gate",
        json={"website": website, "turnstile_token": turnstile_token},
        headers={"X-Forwarded-For": ip},
    )


def test_turnstile_disabled_passes():
    assert demo_abuse.turnstile_enabled() is False
    resp = _post()
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_no_email_required_and_ip_is_logged(capsys):
    resp = _post(ip="203.0.113.9")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    captured = capsys.readouterr()
    assert "[demo-gate]" in captured.out
    assert "203.0.113.9" in captured.out
    assert "email" not in captured.out


def test_honeypot_tripped_returns_fake_success_and_does_not_log(capsys):
    resp = _post(website="http://spam.example")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    captured = capsys.readouterr()
    assert "[demo-gate]" not in captured.out


def test_rate_limit_allows_five_then_blocks_sixth():
    ip = "198.51.100.9"
    for _ in range(demo_abuse.RATE_LIMIT_MAX):
        resp = _post(ip=ip)
        assert resp.status_code == 200, resp.text

    resp = _post(ip=ip)
    assert resp.status_code == 429


def test_rate_limit_is_scoped_per_ip():
    for _ in range(demo_abuse.RATE_LIMIT_MAX):
        assert _post(ip="192.0.2.1").status_code == 200

    # A different IP still has its own allowance.
    assert _post(ip="192.0.2.2").status_code == 200


def test_gate_still_works_when_read_only_locks_down_the_rest_of_the_api(monkeypatch):
    """READ_ONLY blocks other writes (e.g. contracts POST) but must not block the gate itself —
    otherwise the gate would be unusable on exactly the deployment it exists to protect."""
    monkeypatch.setattr(main_module.settings, "read_only", True)

    blocked = client.post("/api/contracts", json={})
    assert blocked.status_code == 403

    resp = _post(ip="203.0.113.42")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
