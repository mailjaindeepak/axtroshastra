"""Regression guards for the storage layer.

These cover the class of bug that once reached production silently: /api/kundli
returned 200 with a report_id, but the row was not actually retrievable
afterwards (writes accepted, not durable). A plain "does the API respond"
test does NOT catch that — you have to write, then read it back, and assert the
data survived. We also exercise /api/order's non-Razorpay branches (free pass,
already-paid, missing report) so the checkout entry point has server-side
coverage without needing live Razorpay keys in CI.
"""

KUNDLI = {"name": "Persist Tester", "dob": "1993-03-21", "tob": "08:15",
          "time_quality": "T0", "place": "Delhi", "gender": "female"}


def _new_report(client, **overrides):
    r = client.post("/api/kundli", json={**KUNDLI, **overrides})
    assert r.status_code == 200, r.text
    return r.json()


# --------------------------------------------------------------- durability

def test_created_report_is_immediately_retrievable(client):
    """The exact prod failure: create returns a report_id, but the follow-up
    read 404s. This asserts the write is durable and readable right after."""
    rid = _new_report(client)["report_id"]
    r = client.get(f"/api/report/{rid}")
    assert r.status_code == 200, f"report {rid} vanished after write: {r.text}"
    body = r.json()
    assert body["paid"] is False
    assert "teaser" in body


def test_report_survives_multiple_reads(client):
    """A durable write is readable repeatedly, not just on a lucky first hit
    (guards against a write landing on only one of several backends)."""
    rid = _new_report(client)["report_id"]
    for _ in range(5):
        assert client.get(f"/api/report/{rid}").status_code == 200


def test_healthz_db_selfcheck_passes(client):
    """The deep write-durability probe returns 200 on a healthy DB."""
    r = client.get("/healthz/db")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ok"


# --------------------------------------------------- /api/order (no Razorpay)

def test_order_for_missing_report_404s(client):
    r = client.post("/api/order", json={"report_id": "does-not-exist"})
    assert r.status_code == 404


def test_order_with_free_pass_unlocks_without_razorpay(client):
    """The free-pass branch of /api/order marks the report paid server-side —
    no Razorpay call — so the whole unlock path is testable in CI."""
    # mint a one-time pass via the admin route (STATS_KEY set by conftest)
    passes = client.get("/api/make_pass?key=test-stats-key&n=1").json()["passes"]
    tok = passes[0]
    rid = _new_report(client)["report_id"]
    r = client.post("/api/order", json={"report_id": rid, "pass": tok})
    assert r.status_code == 200, r.text
    assert r.json().get("free") is True
    # report is now paid and fully retrievable
    paid = client.get(f"/api/report/{rid}").json()
    assert paid["paid"] is True
    assert "report" in paid


def test_used_pass_is_rejected_second_time(client):
    tok = client.get("/api/make_pass?key=test-stats-key&n=1").json()["passes"][0]
    rid1 = _new_report(client)["report_id"]
    assert client.post("/api/order", json={"report_id": rid1, "pass": tok}).json().get("free") is True
    # same token on a second report must be refused
    rid2 = _new_report(client)["report_id"]
    assert client.post("/api/order", json={"report_id": rid2, "pass": tok}).json().get("error") == "invalid_pass"


def test_order_on_already_paid_report_short_circuits(client):
    """Once paid (via demo pay), /api/order returns already_paid instead of
    trying to create a second Razorpay order."""
    rid = _new_report(client)["report_id"]
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    r = client.post("/api/order", json={"report_id": rid})
    assert r.status_code == 200
    assert r.json().get("already_paid") is True
