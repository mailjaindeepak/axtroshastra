"""API tests: trust boundary (teaser-only before payment), webhook signature,
health check, and XSS escaping of user-supplied names."""

KUNDLI = {"name": "Test User", "dob": "1995-08-15", "tob": "10:30",
          "time_quality": "T0", "place": "Delhi", "gender": "male"}


def _new_report(client, **overrides):
    body = {**KUNDLI, **overrides}
    r = client.post("/api/kundli", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_healthz_ok(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_kundli_returns_teaser_not_full_report(client):
    body = _new_report(client)
    assert "report_id" in body
    assert "teaser" in body
    assert "report" not in body  # full report must never be returned pre-payment


def test_report_is_gated_before_payment(client):
    rid = _new_report(client)["report_id"]
    r = client.get(f"/api/report/{rid}")
    assert r.status_code == 200
    body = r.json()
    assert body["paid"] is False
    assert "report" not in body


def test_webhook_rejects_bad_signature(client):
    r = client.post("/api/webhook", content=b"{}",
                    headers={"X-Razorpay-Signature": "deadbeef"})
    assert r.status_code == 400


def test_admin_routes_require_key(client):
    assert client.get("/api/stats").status_code == 403
    assert client.get("/api/stats?key=wrong").status_code == 403
    assert client.get("/api/stats?key=test-stats-key").status_code == 200


def test_name_is_html_escaped_in_rendered_report(client):
    rid = _new_report(client, name="<script>alert(1)</script>")["report_id"]
    # DEMO_MODE unlock so the paid report page renders
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    html = client.get(f"/report/{rid}").text
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
