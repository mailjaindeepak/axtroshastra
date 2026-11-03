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
URGENCY = ("countdown", "hurry", "only today", "limited time", "last chance", "expires", "offer ends", "left in stock", "ends in", "selling fast")


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


# ------------------------------------------------------------------ nothing purchasable (today's live state)
def test_nothing_purchasable_shows_no_price_and_no_paid_section(client):
    h = client.get("/en/numerology").text
    t = _text(h)
    assert "Generate My Free Preview" in t and "See My Free Preview" not in t
    assert 'class="offer"' not in h and "₹" not in t
    assert "nothing to buy on this page" in t and "Nothing is charged on this page" in t
    assert "<!--MK_" not in h


# ------------------------------------------------------------------ instant sale for ready combinations
def test_sale_state_shows_free_vs_complete_with_299_and_no_unconfirmed_499(client, monkeypatch):
    _open_sale(monkeypatch)
    h = client.get("/en/numerology").text
    t = _text(h)
    assert 'class="offer"' in h and "Your free preview" in t and "Your complete numerology report" in t
    assert "₹299" in t and "₹499" not in t and "Save" not in t and '<s class="mk-was">' not in h
    assert "separate purchase" in t and "Free preview now" in t and "nothing to buy" not in t
    assert "Generate My Free Preview" in t and "Private link and a PDF you can download" in t
    for pt in nl.PAID_POINTS + nl.FREE_POINTS:
        assert pt in t


def test_sale_state_with_confirmed_regular_price_strikes_499_and_highlights_299(client, monkeypatch):
    _open_sale(monkeypatch)
    monkeypatch.setenv("MULANK_LIST_PRICE_CONFIRMED", "1")
    h = client.get("/en/numerology").text
    assert '<s class="mk-was">' in h and "₹499" in _text(h) and "₹299" in _text(h) and "Save ₹200" in _text(h)
    assert h.index('<s class="mk-was">') < h.index('<span class="mk-now">')                 # regular price first, selling price next to it


def test_the_landing_page_never_sells_directly_the_preview_comes_first(client, monkeypatch):
    _open_sale(monkeypatch)
    h = client.get("/en/numerology").text
    assert 'data-action="checkout"' not in h and 'data-action="preorder"' not in h and "razorpay" not in h.lower()
    assert 'href="#hero"' in h


def test_form_fields_are_unchanged(client, monkeypatch):
    _open_sale(monkeypatch)
    h = client.get("/en/numerology").text
    names = set(re.findall(r'<(?:input|select)[^>]*\bname="([^"]+)"', h))
    assert names == {"name", "dob", "gender", "phone", "consent_terms", "marketing_optin", "website"}


# ------------------------------------------------------------------ owner-approved pre-order
def test_preorder_state_is_worded_as_a_preorder_with_promise_and_refund_link(client, pre):
    h = client.get("/en/numerology").text
    t = _text(h)
    assert 'class="offer"' in h and "Pre-order" in t and PROMISE in t and "This is a pre-order, not an instant download" in t
    assert 'href="/refund"' in h and "₹299" in t
    assert "Private link and a PDF you can download" not in t and "instant" not in t.lower().replace("not an instant download", "")
    assert "<!--MK_" not in h


def test_preorder_stays_hidden_while_not_fully_configured(client, monkeypatch):
    monkeypatch.setenv("MULANK_PREORDER", "1")
    h = client.get("/en/numerology").text
    assert 'class="offer"' not in h and "₹" not in _text(h)


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
        assert "setinterval" not in h and "countdown" not in h.lower()
        assert "belief system, not a science" in t


def test_price_block_uses_the_single_price_constant():
    import mulank_pricing as mp
    assert nl._inr(mp.MULANK_PRICE_PAISE) == "₹299" and nl._inr(mp.MULANK_LIST_PRICE_PAISE) == "₹499"
    assert "₹299" in nl.price_block() and "₹499" not in nl.price_block()
