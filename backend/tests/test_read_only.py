"""READ_ONLY guard: when on, writes are blocked (403) EXCEPT /auto-match; reads stay open."""
import asyncio
import json as _json

from app import main


class _Response:
    def __init__(self, status_code, headers, body):
        self.status_code = status_code
        self.headers = headers
        self._body = body

    def json(self):
        return _json.loads(self._body.decode() or "null")


class _Client:
    """Drives the real ASGI app (real middleware stack) via stdlib asyncio — no httpx."""

    def __init__(self, app):
        self.app = app

    def request(self, method: str, path: str) -> _Response:
        scope = {
            "type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1", "method": method, "path": path,
            "raw_path": path.encode(), "query_string": b"", "root_path": "",
            "scheme": "http", "server": ("testserver", 80), "client": ("testclient", 50000),
            "headers": [], "state": {},
        }
        sent = False

        async def receive():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": b"", "more_body": False}
            return {"type": "http.disconnect"}

        messages = []

        async def send(message):
            messages.append(message)

        asyncio.run(self.app(scope, receive, send))
        status, headers, body = None, {}, b""
        for m in messages:
            if m["type"] == "http.response.start":
                status = m["status"]
                headers = {k.decode().lower(): v.decode() for k, v in m.get("headers", [])}
            elif m["type"] == "http.response.body":
                body += m.get("body", b"")
        return _Response(status, headers, body)


def test_reads_open_when_read_only(monkeypatch):
    monkeypatch.setattr(main.settings, "read_only", True)
    monkeypatch.setattr(main.settings, "demo_seed", False)
    c = _Client(main.app)
    assert c.request("GET", "/openapi.json").status_code == 200


def test_write_blocked_when_read_only(monkeypatch):
    monkeypatch.setattr(main.settings, "read_only", True)
    monkeypatch.setattr(main.settings, "demo_seed", False)
    c = _Client(main.app)
    r = c.request("POST", "/api/contracts")
    assert r.status_code == 403
    assert "read-only" in r.json()["detail"].lower()


def test_delete_blocked_when_read_only(monkeypatch):
    monkeypatch.setattr(main.settings, "read_only", True)
    monkeypatch.setattr(main.settings, "demo_seed", False)
    c = _Client(main.app)
    assert c.request("DELETE", "/api/contracts/some-id").status_code == 403


def test_auto_match_allowed_when_read_only(monkeypatch):
    # The guard must let /auto-match through (it 404s at routing here since the path is
    # unregistered — the point is it is NOT 403-blocked by the guard).
    monkeypatch.setattr(main.settings, "read_only", True)
    monkeypatch.setattr(main.settings, "demo_seed", False)
    c = _Client(main.app)
    assert c.request("POST", "/api/does-not-exist/auto-match").status_code == 404


def test_writes_allowed_when_not_read_only(monkeypatch):
    monkeypatch.setattr(main.settings, "read_only", False)
    monkeypatch.setattr(main.settings, "demo_seed", False)
    c = _Client(main.app)
    # Guard off => unregistered write path routes normally to 404, not 403.
    assert c.request("POST", "/nope").status_code == 404
