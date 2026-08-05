"""GET /api/pdf_health — a from-a-URL check of the headless-Chrome PDF-maker on
whichever instance serves the request.

The report PDF is what Twilio downloads for the WhatsApp attachment; when the
PDF-maker is missing or broken on a prod instance, the attachment fetch fails
(Twilio 63019) and delivery falls back to the link. This endpoint makes that
failure *visible* without SSH. Chrome is mocked so the test is deterministic on
CI (which has no browser).
"""
import api


def test_pdf_health_requires_admin_key(client):
    assert client.get("/api/pdf_health").status_code == 403
    assert client.get("/api/pdf_health?key=wrong").status_code == 403


def test_pdf_health_reports_missing_chrome(client, monkeypatch):
    """No browser on this instance → render_ok False, an explanatory error, and
    generate() is never even attempted."""
    monkeypatch.setattr(api.pdfgen, "chrome_bin", lambda: "")

    def _boom(*a, **k):
        raise AssertionError("generate() must not run when there is no chrome binary")

    monkeypatch.setattr(api.pdfgen, "generate", _boom)

    r = client.get("/api/pdf_health?key=test-stats-key")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["render_ok"] is False
    assert body["chrome_bin"] == ""
    assert "not installed" in body["error"]


def test_pdf_health_ok_when_render_succeeds(client, monkeypatch):
    monkeypatch.setattr(api.pdfgen, "chrome_bin", lambda: "/opt/pw-browsers/chrome-headless-shell")
    monkeypatch.setattr(api.pdfgen, "generate", lambda html: b"%PDF-1.4 fake pdf bytes")

    r = client.get("/api/pdf_health?key=test-stats-key")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["render_ok"] is True
    assert body["pdf_bytes"] > 0
    assert body["chrome_bin"].endswith("chrome-headless-shell")
    assert "render_ms" in body


def test_pdf_health_flags_broken_render(client, monkeypatch):
    """Chrome present but the render returns nothing (crash/timeout) → not ok."""
    monkeypatch.setattr(api.pdfgen, "chrome_bin", lambda: "/opt/pw-browsers/chrome-headless-shell")
    monkeypatch.setattr(api.pdfgen, "generate", lambda html: None)

    r = client.get("/api/pdf_health?key=test-stats-key")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["render_ok"] is False
    assert body["pdf_bytes"] == 0
    assert body.get("error")
