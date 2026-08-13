"""Tests for ops.watcher — the deep HTTP health check.

The network is fully mocked: we monkeypatch urllib.request.urlopen to return
canned responses keyed by URL, and monkeypatch alerts.send_alert to record
calls. No real HTTP is ever made.

The watcher runs the DEEP checks UptimeRobot can't (DB write-durability, the PDF
renderer, the OTP provider, LLM reachability, Razorpay creds). All five are hard
checks: any failure is red and fires a 'critical' alert.
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
        "/healthz/db": (200, {"status": "ok", "db": "write-read-verified"}),
        "/api/pdf_health": (200, {"render_ok": True}),
        "/api/otp/health": (200, {"ok": True}),
        "/api/admin/llm_health": (200, {"ok": True, "model": "claude-haiku-4-5-20251001", "note": "API responded: OK"}),
        "/api/admin/razorpay_health": (200, {"ok": True, "note": "credentials accepted (1 payment(s) returned)"}),
    }


def _make_urlopen(routes):
    """Build a fake urlopen that dispatches on the request URL path."""
    def fake_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else req
        # Longest suffix first so /healthz/db can't be shadowed by /healthz.
        path = url.split("?", 1)[0]
        for suffix in sorted(routes, key=len, reverse=True):
            status, body = routes[suffix]
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
        "healthz_db", "pdf_health", "otp_health", "llm_health", "razorpay_health"}
    for c in report["checks"]:
        assert c["ok"] is True
        assert "latency_ms" in c and isinstance(c["latency_ms"], int)

    # main() exits 0 and fires NO alert when green.
    rc = watcher.main()
    assert rc == 0
    assert record_alert == []


def test_db_503_is_red_and_alerts_critical(monkeypatch, record_alert):
    routes = _routes_all_green()
    routes["/healthz/db"] = (503, {"detail": "sentinel missing on re-read"})
    monkeypatch.setattr(urllib.request, "urlopen", _make_urlopen(routes))

    report = watcher.run_checks()

    assert report["overall"] == "red"
    assert "healthz_db" in report["failures"]

    rc = watcher.main()
    assert rc == 1
    # send_alert called exactly once, with critical severity.
    assert len(record_alert) == 1
    args, kwargs = record_alert[0]
    severity = kwargs.get("severity", args[2] if len(args) > 2 else None)
    assert severity == "critical"


def test_pdf_render_not_ok_is_red(monkeypatch, record_alert):
    routes = _routes_all_green()
    routes["/api/pdf_health"] = (200, {"render_ok": False})
    monkeypatch.setattr(urllib.request, "urlopen", _make_urlopen(routes))

    report = watcher.run_checks()

    assert report["overall"] == "red"
    assert "pdf_health" in report["failures"]
    assert watcher.main() == 1
    assert len(record_alert) == 1


def test_otp_non200_is_red_and_alerts(monkeypatch, record_alert):
    routes = _routes_all_green()
    routes["/api/otp/health"] = (503, {"ok": False})
    monkeypatch.setattr(urllib.request, "urlopen", _make_urlopen(routes))

    report = watcher.run_checks()

    # OTP is now a hard check: its failure turns the site red and alerts.
    assert report["overall"] == "red"
    assert "otp_health" in report["failures"]
    assert watcher.main() == 1
    assert len(record_alert) == 1


def test_otp_health_url_includes_stats_key(monkeypatch, record_alert):
    """The otp_health endpoint is admin-gated: it requires ?key=<STATS_KEY>.
    Without it the real server returns 403 and the check silently fails."""
    monkeypatch.setattr(config, "STATS_KEY", "my-secret-key")

    captured_urls = []

    def spy_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else req
        captured_urls.append(url)
        return FakeResponse(200, json.dumps({"ok": True}))

    monkeypatch.setattr(urllib.request, "urlopen", spy_urlopen)
    watcher.run_checks()

    otp_urls = [u for u in captured_urls if "/api/otp/health" in u]
    assert otp_urls, "otp_health was never called"
    assert "key=my-secret-key" in otp_urls[0]


def test_pdf_health_url_includes_stats_key(monkeypatch, record_alert):
    """Same admin-key gate applies to pdf_health."""
    monkeypatch.setattr(config, "STATS_KEY", "admin-key-42")

    captured_urls = []

    def spy_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else req
        captured_urls.append(url)
        return FakeResponse(200, json.dumps({"render_ok": True}))

    monkeypatch.setattr(urllib.request, "urlopen", spy_urlopen)
    watcher.run_checks()

    pdf_urls = [u for u in captured_urls if "/api/pdf_health" in u]
    assert pdf_urls, "pdf_health was never called"
    assert "key=admin-key-42" in pdf_urls[0]


def test_stats_key_is_url_encoded(monkeypatch, record_alert):
    """Special characters in the STATS_KEY must be percent-encoded so the
    query string doesn't break."""
    monkeypatch.setattr(config, "STATS_KEY", "a key&with=specials")

    captured_urls = []

    def spy_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else req
        captured_urls.append(url)
        return FakeResponse(200, json.dumps({"render_ok": True, "ok": True}))

    monkeypatch.setattr(urllib.request, "urlopen", spy_urlopen)
    watcher.run_checks()

    for url in captured_urls:
        if "key=" in url:
            raw_key = url.split("key=", 1)[1]
            assert "&" not in raw_key
            assert "=" not in raw_key
            assert " " not in raw_key


def test_llm_health_failure_is_red(monkeypatch, record_alert):
    routes = _routes_all_green()
    routes["/api/admin/llm_health"] = (200, {"ok": False, "error": "ANTHROPIC_API_KEY not set"})
    monkeypatch.setattr(urllib.request, "urlopen", _make_urlopen(routes))

    report = watcher.run_checks()

    assert report["overall"] == "red"
    assert "llm_health" in report["failures"]
    assert watcher.main() == 1
    assert len(record_alert) == 1


def test_razorpay_health_failure_is_red(monkeypatch, record_alert):
    routes = _routes_all_green()
    routes["/api/admin/razorpay_health"] = (200, {"ok": False, "error": "RAZORPAY_KEY_ID not set"})
    monkeypatch.setattr(urllib.request, "urlopen", _make_urlopen(routes))

    report = watcher.run_checks()

    assert report["overall"] == "red"
    assert "razorpay_health" in report["failures"]
    assert watcher.main() == 1
    assert len(record_alert) == 1


def test_run_checks_never_raises_when_urlopen_throws(monkeypatch, record_alert):
    def boom(req, timeout=None):
        raise ConnectionError("network down")
    monkeypatch.setattr(urllib.request, "urlopen", boom)

    # Must not raise despite every request throwing.
    report = watcher.run_checks()

    assert report["overall"] == "red"
    assert "healthz_db" in report["failures"]
    # every hard check recorded ok:False with the error captured in detail.
    for c in report["checks"]:
        assert c["ok"] is False
        assert "ConnectionError" in c["detail"]
    assert watcher.main() == 1
    assert len(record_alert) == 1
