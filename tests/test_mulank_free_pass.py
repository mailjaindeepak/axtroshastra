"""R3: Numerology free passes (for testing and gifts) while Razorpay stays the real payment path.

Pins down: only the admin can mint; passes are MK- prefixed and Numerology-only; a pass unlocks exactly one report once; every refused attempt
leaves the pass unspent; a pass sends no Purchase and no Razorpay order; the price path is untouched. Real throwaway MySQL from conftest."""
import itertools
import re
from pathlib import Path

import pytest

import api
import db_v2
import mulank_content as mc
import mulank_fulfilment
import mulank_routes
import numerology
import reports_v2
import tracking

_seq = itertools.count(1)
PAGE = Path(__file__).resolve().parent.parent / "pages" / "numerology.html"
KEY = "test-admin-key-pass"


@pytest.fixture
def eligible(monkeypatch):
    d = numerology.compute_mulank(29, 7, 1990, today=mc._today())
    monkeypatch.setattr(mc, "REGISTRY", {k: mc.Entry(mc.VERIFIED, "Test Reviewer", "2026-11-03") for k in mc.required_keys(d)})


@pytest.fixture
def admin(monkeypatch):
    monkeypatch.setattr(api, "STATS_KEY", KEY)


@pytest.fixture
def fulfilled(monkeypatch):
    calls = []
    monkeypatch.setattr(mulank_routes, "FULFIL", lambda rid, bg: calls.append(rid))
    return calls


@pytest.fixture
def no_razorpay(monkeypatch):
    """A free pass must never reach Razorpay: any attempt to build a client fails the test."""
    def boom():
        raise AssertionError("a free pass must not touch Razorpay")
    monkeypatch.setattr(api, "rzp_client", boom)


def _lead(client, phone=True):
    p = "98%08d" % (70000000 + next(_seq))
    r = client.post("/api/mulank", json={"name": "Priya Sharma", "dob": "29/07/1990", "gender": "female", "country_code": "+91", "phone": p if phone else "",
                                         "consent_terms": True, "marketing_optin": False})
    assert r.status_code == 200, r.text
    return r.json()["report_id"]


def _mint(client, n=1):
    r = client.get(f"/api/mulank/make_pass?key={KEY}&n={n}")
    assert r.status_code == 200, r.text
    return r.json()["passes"]


def _raw_pass(token):
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO passes(token) VALUES(%s)", (token,))
        conn.commit()
    finally:
        conn.close()


def _used(token):
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT used FROM passes WHERE token=%s", (token,))
            row = cur.fetchone()
        return None if row is None else bool(row[0])
    finally:
        conn.close()


def _rec(rid):
    conn = db_v2.get_conn()
    try:
        return reports_v2.read_report(conn, rid)
    finally:
        conn.close()


def _redeem(client, rid, tok):
    return client.post("/api/mulank/order", json={"report_id": rid, "pass": tok})


# ------------------------------------------------------------------ minting
def test_only_the_admin_can_mint(client, monkeypatch):
    monkeypatch.setattr(api, "STATS_KEY", KEY)
    assert client.get("/api/mulank/make_pass").status_code == 403
    assert client.get("/api/mulank/make_pass?key=wrong").status_code == 403
    monkeypatch.setattr(api, "STATS_KEY", "")
    assert client.get("/api/mulank/make_pass?key=").status_code == 403           # no admin key configured: always refused


def test_minted_passes_are_mk_prefixed_unique_stored_unused_and_private(client, admin):
    r = client.get(f"/api/mulank/make_pass?key={KEY}&n=4")
    j = r.json()
    assert r.status_code == 200 and len(set(j["passes"])) == 4 and all(re.fullmatch(r"MK-[A-Za-z0-9_-]{8,}", t) for t in j["passes"])
    assert all(f"/en/numerology?pass={t}" in link for t, link in zip(j["passes"], j["links"]))
    assert all(_used(t) is False for t in j["passes"])
    assert r.headers["cache-control"] == "no-store" and "noindex" in r.headers["x-robots-tag"]


def test_mint_count_is_clamped(client, admin):
    assert len(client.get(f"/api/mulank/make_pass?key={KEY}&n=999").json()["passes"]) == 30
    assert len(client.get(f"/api/mulank/make_pass?key={KEY}&n=0").json()["passes"]) == 1


# ------------------------------------------------------------------ redeeming
def test_a_pass_unlocks_the_report_once_without_razorpay_or_a_purchase(client, admin, eligible, no_razorpay, monkeypatch):
    sent = []
    monkeypatch.setattr(tracking, "_post_json", lambda *a, **k: sent.append(a) or (200, "{}"))
    for name in ("META_CAPI_TOKEN", "GA4_API_SECRET", "LINKEDIN_CAPI_TOKEN", "OAIQ_CAPI_TOKEN", "X_PIXEL_TOKEN"):
        monkeypatch.setattr(tracking, name, "configured")
    monkeypatch.setattr(mulank_fulfilment, "run_fulfilment", lambda rid: {"status": "ready"})
    rid, tok = _lead(client), _mint(client)[0]
    assert not _rec(rid)["paid"]
    r = _redeem(client, rid, tok)
    assert r.status_code == 200 and r.json() == {"free": True}
    assert _rec(rid)["paid"] and _used(tok) is True
    assert sent == []                                                             # a free pass is not a sale
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT amount_paise, method, status FROM payments WHERE report_id=%s", (rid,))
            assert cur.fetchone() == (0, "free_pass", "captured")
    finally:
        conn.close()


def test_a_pass_cannot_be_reused_on_another_report(client, admin, eligible, fulfilled):
    a, b, tok = _lead(client), _lead(client), _mint(client)[0]
    assert _redeem(client, a, tok).json() == {"free": True}
    r = _redeem(client, b, tok)
    assert r.status_code == 409 and r.json()["detail"] == "invalid_pass"
    assert not _rec(b)["paid"] and fulfilled == [a]


def test_a_pass_minted_for_another_product_is_not_accepted_and_stays_unspent(client, eligible, fulfilled):
    _raw_pass("shared-token-abc")                                                # what the shared /api/make_pass would have issued
    rid = _lead(client)
    r = _redeem(client, rid, "shared-token-abc")
    assert r.status_code == 409 and r.json()["detail"] == "invalid_pass"
    assert not _rec(rid)["paid"] and _used("shared-token-abc") is False and fulfilled == []


def test_unknown_and_never_issued_passes_are_refused(client, eligible):
    rid = _lead(client)
    assert _redeem(client, rid, "MK-never-issued").status_code == 409
    assert _redeem(client, rid, "MK-" + "x" * 80).status_code == 409
    assert not _rec(rid)["paid"]


def test_an_incomplete_pair_cannot_be_unlocked_and_the_pass_is_not_burned(client, admin, monkeypatch, fulfilled):
    monkeypatch.setattr(mc, "REGISTRY", {})                                      # nothing approved
    rid, tok = _lead(client), _mint(client)[0]
    r = _redeem(client, rid, tok)
    assert r.status_code == 409 and r.json()["detail"] == "not_available"
    assert not _rec(rid)["paid"] and _used(tok) is False and fulfilled == []


def test_an_already_paid_report_does_not_spend_a_second_pass(client, admin, eligible, fulfilled):
    rid, t1, t2 = _lead(client), *_mint(client, 2)
    assert _redeem(client, rid, t1).json() == {"free": True}
    assert _redeem(client, rid, t2).json() == {"already_paid": True}
    assert _used(t2) is False and fulfilled == [rid]


def test_unknown_report_and_another_products_report_do_not_spend_the_pass(client, admin, eligible, fulfilled):
    tok = _mint(client)[0]
    assert _redeem(client, "no-such-report-id", tok).status_code == 404
    conn = db_v2.get_conn()
    try:
        other = "ot%030d" % next(_seq)
        reports_v2.save_report(conn, other, {"product": "marriage", "dob": "1990-07-29", "meta": {}}, [], product="marriage",
                               phone="98%08d" % (71000000 + next(_seq)))
        conn.commit()
    finally:
        conn.close()
    assert _redeem(client, other, tok).status_code == 404
    assert _used(tok) is False and not _rec(other)["paid"] and fulfilled == []


def test_a_report_without_a_contact_cannot_be_unlocked_by_a_pass(client, admin, eligible, fulfilled):
    conn = db_v2.get_conn()
    try:
        rid = "mk%030d" % next(_seq)
        reports_v2.save_report(conn, rid, {"product": "numerology_mulank", "dob": "1990-07-29", "meta": {}}, [], product="numerology_mulank", phone=None)
        conn.commit()
    finally:
        conn.close()
    tok = _mint(client)[0]
    r = _redeem(client, rid, tok)
    assert r.status_code == 400 and r.json()["detail"] == "contact_required" and _used(tok) is False


def test_fulfilment_runs_once_for_a_pass(client, admin, eligible, fulfilled):
    rid, tok = _lead(client), _mint(client)[0]
    _redeem(client, rid, tok)
    _redeem(client, rid, tok)                                                    # replay of the same request
    assert fulfilled == [rid]


def test_pass_attempts_are_rate_limited(client, admin, eligible, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "1")
    mulank_routes._hits.clear()
    rid = _lead(client)
    codes = [_redeem(client, rid, "MK-guess-%d" % i).status_code for i in range(8)]
    assert codes[:6] == [409] * 6 and codes[6:] == [429, 429]
    mulank_routes._hits.clear()


def test_the_normal_order_path_is_unchanged_when_no_pass_is_sent(client, eligible, monkeypatch):
    class _Rz:
        class order:
            @staticmethod
            def create(d):
                return {"id": "order_" + d["receipt"], "amount": d["amount"], "currency": d["currency"]}
    monkeypatch.setattr(api, "rzp_client", lambda: _Rz())
    rid = _lead(client)
    r = client.post("/api/mulank/order", json={"report_id": rid})
    assert r.status_code == 200 and r.json()["amount"] == 29900 and r.json()["razorpay_order_id"] == "order_" + rid


# ------------------------------------------------------------------ the page
def test_the_page_keeps_the_pass_out_of_the_address_bar_and_sends_no_purchase_for_it():
    html = PAGE.read_text(encoding="utf-8")
    assert "history.replaceState" in html and "pass=([^&#]*)" in html
    assert "if(d.free){ PASS=''; showPaid(); return; }" in html
    free_branch = html.split("if(d.free){")[1].split("}")[0]
    assert "track(" not in free_branch                                           # no checkout or purchase event for a pass
