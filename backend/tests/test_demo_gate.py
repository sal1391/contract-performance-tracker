"""The DEMO_PASSWORD gate: when set, every path except /healthz needs HTTP Basic auth.

Note: fastapi.testclient.TestClient requires the (uninstalled) httpx/httpx2 package in this
environment's starlette version. Adding it would be a new dependency, which is off-limits
per the task constraints, so this module drives the real ASGI app directly over stdlib
asyncio instead -- the exact same production code path (CORS middleware -> demo-password
middleware -> routing), just without an HTTP client library in between.
"""
import asyncio
import base64

from app import main


def _basic(password: str) -> dict:
    token = base64.b64encode(f"demo:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


class _Response:
    def __init__(self, status_code: int | None, headers: dict[str, str]):
        self.status_code = status_code
        self.headers = headers


class _Client:
    """Minimal stand-in for fastapi.testclient.TestClient's .get(), driving the ASGI
    app directly via stdlib asyncio (no httpx dependency)."""

    def __init__(self, app):
        self.app = app

    def get(self, path: str, headers: dict | None = None) -> _Response:
        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "GET",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "root_path": "",
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
            "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
            "state": {},
        }

        sent = False

        async def receive():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": b"", "more_body": False}
            return {"type": "http.disconnect"}

        messages: list[dict] = []

        async def send(message):
            messages.append(message)

        asyncio.run(self.app(scope, receive, send))

        status = None
        resp_headers: dict[str, str] = {}
        for m in messages:
            if m["type"] == "http.response.start":
                status = m["status"]
                resp_headers = {k.decode().lower(): v.decode() for k, v in m.get("headers", [])}
        return _Response(status, resp_headers)


def test_healthz_exempt_even_when_gated(monkeypatch):
    monkeypatch.setattr(main.settings, "demo_password", "s3cret")
    monkeypatch.setattr(main.settings, "demo_seed", False)
    c = _Client(main.app)
    assert c.get("/healthz").status_code == 200


def test_gated_path_blocked_without_credentials(monkeypatch):
    monkeypatch.setattr(main.settings, "demo_password", "s3cret")
    monkeypatch.setattr(main.settings, "demo_seed", False)
    c = _Client(main.app)
    r = c.get("/openapi.json")
    assert r.status_code == 401
    assert r.headers["www-authenticate"].lower().startswith("basic")


def test_gated_path_blocked_with_wrong_password(monkeypatch):
    monkeypatch.setattr(main.settings, "demo_password", "s3cret")
    monkeypatch.setattr(main.settings, "demo_seed", False)
    c = _Client(main.app)
    assert c.get("/openapi.json", headers=_basic("wrong")).status_code == 401


def test_gated_path_allowed_with_correct_password(monkeypatch):
    monkeypatch.setattr(main.settings, "demo_password", "s3cret")
    monkeypatch.setattr(main.settings, "demo_seed", False)
    c = _Client(main.app)
    assert c.get("/openapi.json", headers=_basic("s3cret")).status_code == 200


def test_gate_off_when_password_empty(monkeypatch):
    monkeypatch.setattr(main.settings, "demo_password", "")
    monkeypatch.setattr(main.settings, "demo_seed", False)
    c = _Client(main.app)
    assert c.get("/openapi.json").status_code == 200
