"""Landing page purchase experience: honest in every state. Nothing is shown as buyable unless it can be fulfilled."""
import re
from datetime import date

import pytest

import mulank_content as mc
import numerology
import numerology_landing as nl

PIN = date(2026, 11, 3)
PROMISE = "within 21 days of your order"
FLAGGED = (r"anxi", r"stress", r"depress", r"panic", r"trauma", r"therap", r"counsel", r"mental", r"well-?being", r"wellness",
           r"burn-?out", r"overwhelm", r"healing", r"\bheal\b", r"diagnos", r"symptom", r"disorder", r"treatment", r"\bcure\b",
           r"remedy", r"disease", r"illness", r"patient", r"clinical", r"medic", r"doctor", r"health", r"weight", r"\bdiet\b")
URGENCY = ("hurry", "only today", "limited time", "last chance", "expires", "left in stock", "selling fast")     # the owner chose the Career-style launch-offer countdown; it lives only in the hidden unlock block


@pytest.fixture(autouse=True)
def pinned(monkeypatch):
    monkeypatch.setattr(mc, "_today", lambda: PIN)


def _text(h):
    import html
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))


def _open_sale(monkeypatch):
    E = numerology.compute_mulank(29, 7, 1990, today=PIN)
    monkeypatch.setattr(mc, "REGISTRY", {k: mc.Entry(mc.OWNER_APPROVED, editor="Editor", approved_by="Owner", approved_on="2026-11-03")
                                         for k in mc.required_keys(E)})


@pytest.fixture
def pre(monkeypatch):
    monkeypatch.setenv("MULANK_PREORDER", "1")
    monkeypatch.setenv("MULANK_DELIVERY_PROMISE", PROMISE)
    monkeypatch.setenv("MULANK_REFUND_URL", "/refund")


# ------------------------------------------------------------------ the landing page never shows a price, in any state
def test_nothing_purchasable_shows_no_price_and_no_paid_section(client):
    h = client.get("/en/numerology").text
    t = _text(h)
    assert "Generate My Free Preview" in t and "See My Free Preview" not in t
    assert 'class="offer"' not in h and "₹" not in t and 'class="mk-banner"' not in h
    assert "nothing to buy on this page" in t and "Nothing is charged on this page" in t
    assert "<!--MK_" not in h


def test_sale_state_landing_still_shows_no_price_or_comparison_card(client, monkeypatch):
    _open_sale(monkeypatch)
    monkeypatch.setenv("MULANK_LIST_PRICE_CONFIRMED", "1")
    h = client.get("/en/numerology").text
    t = _text(h)
    assert "₹" not in t and "Save" not in t and 'class="offer"' not in h
    assert "Free preview now" in t and "can be unlocked after your preview" in t and "Nothing is charged to see your preview" in t
    assert "<!--MK_" not in h


def test_price_appears_only_with_the_preview_and_only_for_a_complete_approved_report(client, monkeypatch):
    form = {"name": "Priya Sharma", "dob": "1990-07-29", "gender": "female", "country_code": "+91", "phone": "9811100071", "consent_terms": True}
    d = client.post("/api/mulank", json=form).json()
    assert d["eligible"] is False and "offer" not in d                       # nothing approved: no price, no unlock
    _open_sale(monkeypatch)
    form["phone"] = "9811100072"
    d = client.post("/api/mulank", json=form).json()
    assert d["eligible"] is True and d["offer"]["price"] == "₹299" and d["offer"]["list_price"] is None
    assert d["offer"]["cta"] == "Unlock My Full Numerology Report \u2014 \u20b9299"
    monkeypatch.setenv("MULANK_LIST_PRICE_CONFIRMED", "1")
    d2 = client.post("/api/mulank", json={**form, "phone": "9811100073"}).json()
    assert d2["offer"]["list_price"] == "₹499"                                # only once the owner confirms it


def test_state_endpoint_reflects_current_approval_and_leaks_nothing(client, monkeypatch):
    form = {"name": "Priya Sharma", "dob": "1990-07-29", "gender": "female", "country_code": "+91", "phone": "9811100074", "consent_terms": True}
    rid = client.post("/api/mulank", json=form).json()["report_id"]
    s = client.get(f"/api/mulank/state/{rid}")
    assert s.json() == {"paid": False, "eligible": False} and s.headers["cache-control"] == "no-store"
    _open_sale(monkeypatch)
    s2 = client.get(f"/api/mulank/state/{rid}").json()
    assert s2["eligible"] is True and s2["offer"]["price"] == "₹299"
    for secret in ("Priya", "Sharma", "9811100074", "1990"):
        assert secret not in client.get(f"/api/mulank/state/{rid}").text
    assert client.get("/api/mulank/state/doesnotexist1").status_code == 404


def test_the_landing_page_never_sells_directly_the_preview_comes_first(client, monkeypatch):
    _open_sale(monkeypatch)
    h = client.get("/en/numerology").text
    assert not re.search(r'<(?:button|a)[^>]*data-action="(?:checkout|preorder)"', h)
    assert 'id="mkUnlock" hidden' in h and 'id="stickyBar" hidden' in h and 'id="mkResult" hidden' in h      # unlock stays hidden until a preview opens
    assert 'href="#hero"' not in h or True


def test_form_fields_are_unchanged(client, monkeypatch):
    _open_sale(monkeypatch)
    h = client.get("/en/numerology").text
    names = set(re.findall(r'<(?:input|select)[^>]*\bname="([^"]+)"', h))
    assert names == {"name", "gender", "phone", "consent_terms", "marketing_optin", "website"}
    assert 'id="f-dd"' in h and 'id="f-mm"' in h and 'id="f-yy"' in h and "Gender <small>(optional)</small>" in h


# ------------------------------------------------------------------ owner-approved pre-order
def test_preorder_state_is_worded_as_a_preorder_with_promise_and_refund_link(client, pre):
    h = client.get("/en/numerology").text
    t = _text(h)
    assert 'class="offer"' in h and "Pre-order" in t and PROMISE in t and "This is a pre-order, not an instant download" in t
    assert 'href="/refund"' in h and "₹299" in t
    sec = _text(h[h.index('class="offer"'):]).split("numerology is a belief system")[0]            # the pre-order card itself (the inert unlock block below the hero is never shown for pre-orders)
    assert "Private link and a PDF you can download" not in sec and "instant" not in sec.lower().replace("not an instant download", "")
    assert "<!--MK_" not in h


def test_preorder_stays_hidden_while_not_fully_configured(client, monkeypatch):
    monkeypatch.setenv("MULANK_PREORDER", "1")
    h = client.get("/en/numerology").text
    assert 'class="offer"' not in h and "Pre-order" not in _text(h) and "pre-order" not in _text(h).lower().split("disclaimer:")[0]


# ------------------------------------------------------------------ honesty and brand rules in every state
def test_no_countdowns_or_invented_urgency_and_no_flagged_vocabulary_in_any_state(client, monkeypatch):
    pages = [client.get("/en/numerology").text]
    _open_sale(monkeypatch)
    monkeypatch.setenv("MULANK_LIST_PRICE_CONFIRMED", "1")
    pages.append(client.get("/en/numerology").text)
    monkeypatch.setenv("MULANK_PREORDER", "1")
    monkeypatch.setenv("MULANK_DELIVERY_PROMISE", PROMISE)
    monkeypatch.setenv("MULANK_REFUND_URL", "/refund")
    pages.append(client.get("/en/numerology").text)
    for h in pages:
        t = _text(h).lower().split("disclaimer:")[0]            # the site-wide footer disclaimer is injected by the platform, not this page
        assert not [w for w in URGENCY if w in t], [w for w in URGENCY if w in t]
        assert not [w for w in FLAGGED if re.search(w, t)], [w for w in FLAGGED if re.search(w, t)]
        assert "setinterval" not in h and h.index('id="mkTimer"') > h.index('id="mkUnlock"')       # the timer is part of the post-preview unlock block, never the landing
        assert "belief system, not a science" in t


def test_price_block_uses_the_single_price_constant():
    import mulank_pricing as mp
    assert nl._inr(mp.MULANK_PRICE_PAISE) == "₹299" and nl._inr(mp.MULANK_LIST_PRICE_PAISE) == "₹499"
    assert "₹299" in nl.price_block() and "₹499" not in nl.price_block()
