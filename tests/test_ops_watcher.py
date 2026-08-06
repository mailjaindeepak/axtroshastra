"""Tests for ops.watcher — the HTTP health heartbeat.

The network is fully mocked: we monkeypatch urllib.request.urlopen to return
canned responses keyed by URL, and monkeypatch alerts.send_alert to record
calls. No real HTTP is ever made.
"""
import io
import json
import urllib.error
import urllib.request

import pytest

from ops import config, watcher


class FakeResponse(io.BytesIO):
    """Minimal stand-in for the object urlopen returns / a context manager."""

    def __init__(self, status, body):
        super().__init__(body.encode("utf-8"))
        self.status = status

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()
        return False


def _routes_all_green():
    """URL-suffix -> (status, json-body) for a fully healthy site."""
    return {
        "/healthz": (200, {"status": "ok"}),
        "/healthz/db": (200, {"status": "ok", "db": "write-read-verified"}),
        "/api/pdf_health": (200, {"render_ok": True}),
        "/api/otp/health": (200, {"ok": True}),
    }


def _make_urlopen(routes):
    """Build a fake urlopen that dispatches on the request URL path."""
    def fake_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else req
        for suffix, (status, body) in routes.items():
            # match ignoring query string
            path = url.split("?", 1)[0]
            if path.endswith(suffix):
                text = json.dumps(body)
                if status >= 400:
                    raise urllib.error.HTTPError(url, status, "err", {},
                                                 io.BytesIO(text.encode()))
                return FakeResponse(status, text)
        raise AssertionError("unexpected URL in test: %s" % url)
    return fake_urlopen


@pytest.fixture
def record_alert(monkeypatch):
    calls = []
    monkeypatch.setattr(watcher.alerts, "send_alert",
                        lambda *a, **k: calls.append((a, k)) or {"email": True})
    return calls


def test_all_green(monkeypatch, record_alert):
    monkeypatch.setattr(urllib.request, "urlopen",
                        _make_urlopen(_routes_all_green()))

    report = watcher.run_checks()

    assert report["overall"] == "green"
    assert report["failures"] == []
    assert {c["name"] for c in report["checks"]} == {
        "healthz", "healthz_db", "pdf_health", "otp_health"}
    for c in report["checks"]:
        assert c["ok"] is True
        assert "latency_ms" in c and isinstance(c["latency_ms"], int)

    # main() exits 0 and fires NO alert when green.
    rc = watcher.main()
    assert rc == 0
    assert record_alert == []


def test_healthz_503_is_red_and_alerts(monkeypatch, record_alert):
    routes = _routes_all_green()
    routes["/healthz"] = (503, {"detail": "db unavailable"})
    monkeypatch.setattr(urllib.request, "urlopen", _make_urlopen(routes))

    report = watcher.run_checks()

    assert report["overall"] == "red"
    assert "healthz" in report["failures"]

    rc = watcher.main()
    assert rc == 1
    # send_alert called exactly once, with critical severity.
    assert len(record_alert) == 1
    args, kwargs = record_alert[0]
    severity = kwargs.get("severity", args[2] if len(args) > 2 else None)
    assert severity == "critical"


def test_otp_non200_is_warn_only(monkeypatch, record_alert):
    routes = _routes_all_green()
    routes["/api/otp/health"] = (503, {"ok": False})
    monkeypatch.setattr(urllib.request, "urlopen", _make_urlopen(routes))

    report = watcher.run_checks()

    # otp failure is warn-only: it shows in failures but does NOT turn red.
    assert report["overall"] == "green"
    assert "otp_health" in report["failures"]
    assert watcher.main() == 0
    assert record_alert == []


def test_run_checks_never_raises_when_urlopen_throws(monkeypatch, record_alert):
    def boom(req, timeout=None):
        raise ConnectionError("network down")
    monkeypatch.setattr(urllib.request, "urlopen", boom)

    # Must not raise despite every request throwing.
    report = watcher.run_checks()

    assert report["overall"] == "red"
    assert "healthz" in report["failures"]
    # every hard check recorded ok:False with the error captured in detail.
    for c in report["checks"]:
        assert c["ok"] is False
        assert "ConnectionError" in c["detail"]
    assert watcher.main() == 1
    assert len(record_alert) == 1
