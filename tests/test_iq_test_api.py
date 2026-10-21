"""Integration tests for the IQ test API endpoint (POST /api/iq-test).

Tests the real route through FastAPI's TestClient → scoring → DB save → teaser
response, plus the paid report view and the landing page route.
"""
import pytest
import api
from iq_test_questions import QUESTIONS


class _StubOrders:
    def create(self, payload):
        return {"id": "order_stub_iq", "amount": payload["amount"]}


class _StubRzp:
    order = _StubOrders()

# unique phone numbers per §12 (9876590xxx range, not used elsewhere)
PHONE_IQ_1 = "9876590001"
PHONE_IQ_2 = "9876590002"


def _correct_answers():
    return [q["correct"] for q in QUESTIONS]


def _wrong_answers():
    return [(q["correct"] + 1) % 4 for q in QUESTIONS]


def _base_body(**overrides):
    body = {
        "name": "IQ Tester",
        "age": 25,
        "gender": "male",
        "answers": _correct_answers(),
        "time_taken_seconds": 600,
        "consent_ts": "2026-10-01T00:00:00Z",
        "consent_v": "2026-10",
    }
    body.update(overrides)
    return body


# ── happy path ───────────────────────────────────────────────────────────

def test_create_iq_test_returns_teaser(client):
    r = client.post("/api/iq-test", json=_base_body())
    assert r.status_code == 200
    data = r.json()
    assert "report_id" in data
    assert "teaser" in data
    t = data["teaser"]
    assert "iq_score" in t
    assert "classification" in t
    assert "percentile" in t


def test_iq_report_viewable_after_payment(client):
    r = client.post("/api/iq-test", json=_base_body())
    rid = r.json()["report_id"]
    # not paid yet — report endpoint returns teaser only
    unpaid = client.get(f"/api/report/{rid}")
    assert unpaid.status_code == 200
    assert unpaid.json().get("paid") is not True

    # pay via demo endpoint
    pay = client.post(f"/api/_demo_pay/{rid}")
    assert pay.status_code == 200

    # now full report is available
    paid = client.get(f"/api/report/{rid}")
    assert paid.status_code == 200
    assert paid.json()["paid"] is True


def test_iq_report_html_renders_after_payment(client):
    r = client.post("/api/iq-test", json=_base_body(name="HTML Viewer"))
    rid = r.json()["report_id"]
    client.post(f"/api/_demo_pay/{rid}")
    page = client.get(f"/report/{rid}")
    assert page.status_code == 200
    assert "IQ Assessment Report" in page.text


# ── validation ───────────────────────────────────────────────────────────

def test_rejects_too_few_answers(client):
    r = client.post("/api/iq-test", json=_base_body(answers=[1, 2, 3]))
    assert r.status_code == 422


def test_rejects_too_many_answers(client):
    r = client.post("/api/iq-test", json=_base_body(answers=[1] * 25))
    assert r.status_code == 422


def test_rejects_invalid_answer_value(client):
    bad = _correct_answers()
    bad[5] = 7
    r = client.post("/api/iq-test", json=_base_body(answers=bad))
    assert r.status_code == 422


def test_rejects_age_too_young(client):
    r = client.post("/api/iq-test", json=_base_body(age=10))
    assert r.status_code == 422


def test_rejects_age_too_old(client):
    r = client.post("/api/iq-test", json=_base_body(age=150))
    assert r.status_code == 422


def test_allows_unanswered_as_minus_one(client):
    ans = [-1] * 20
    r = client.post("/api/iq-test", json=_base_body(answers=ans))
    assert r.status_code == 200
    assert r.json()["teaser"]["iq_score"] > 0


# ── teaser never leaks paid content ──────────────────────────────────────

def test_teaser_has_no_paid_fields(client):
    r = client.post("/api/iq-test", json=_base_body())
    t = r.json()["teaser"]
    assert "categories" not in t
    assert "cognitive_strengths" not in t
    assert "areas_for_growth" not in t
    assert "recommendations" not in t
    assert "learning_style" not in t


# ── landing page route ───────────────────────────────────────────────────

def test_iq_test_landing_page(client):
    r = client.get("/en/iq-test")
    assert r.status_code == 200
    assert "How" in r.text and "Sharp" in r.text


def test_iq_test_redirect(client):
    r = client.get("/iq-test", follow_redirects=False)
    assert r.status_code in (301, 307)
    assert "/en/iq-test" in r.headers["location"]


# ── pricing ──────────────────────────────────────────────────────────────

def test_iq_test_order_price(client, monkeypatch):
    monkeypatch.setattr(api, "rzp_client", lambda: _StubRzp())
    r = client.post("/api/iq-test", json=_base_body(phone=PHONE_IQ_1))
    rid = r.json()["report_id"]
    order = client.post("/api/order",
                        json={"report_id": rid, "phone": PHONE_IQ_1})
    assert order.status_code == 200
    d = order.json()
    if "amount" in d:
        assert d["amount"] == 49900
