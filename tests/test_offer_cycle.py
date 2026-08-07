"""Compatibility launch-offer cycle: the price shown on the page and the price
actually charged both come from milan_offer_status(), so they can never diverge.
These guard the phase math and that the charge follows the phase (the honesty
guarantee behind the on-page countdown)."""
import api


def test_milan_offer_phase_math():
    base = api.OFFER_CYCLE_SEC * 1000  # a cycle-aligned instant (pos == 0)

    on = api.milan_offer_status(now=base + 5)
    assert on["phase"] == "on"
    assert on["price_paise"] == api.MILAN_PRICE_PAISE == 49900
    assert 0 < on["seconds_left"] <= api.OFFER_ON_SEC

    off = api.milan_offer_status(now=base + api.OFFER_ON_SEC + 5)
    assert off["phase"] == "off"
    assert off["price_paise"] == api.MILAN_FULL_PAISE == 99900
    assert 0 < off["seconds_left"] <= (api.OFFER_CYCLE_SEC - api.OFFER_ON_SEC)


def test_charge_follows_offer_phase(monkeypatch):
    """The amount charged for a compat report must equal the displayed offer
    price — ₹999 during the OFF window, ₹499 during ON — while other funnels
    stay at their flat price."""
    milan_rec = {"payload": {"meta": {"variant": "/en/compatibility"}}}
    other_rec = {"payload": {"meta": {"variant": "/en/marriage"}}}

    monkeypatch.setattr(api, "milan_offer_status",
                        lambda now=None: {"phase": "off", "price_paise": api.MILAN_FULL_PAISE,
                                          "full_paise": api.MILAN_FULL_PAISE, "seconds_left": 600})
    assert api._order_amount_paise(milan_rec) == api.MILAN_FULL_PAISE   # ₹999 when OFF
    assert api._order_amount_paise(other_rec) == api.PRICE_PAISE        # unaffected

    monkeypatch.setattr(api, "milan_offer_status",
                        lambda now=None: {"phase": "on", "price_paise": api.MILAN_PRICE_PAISE,
                                          "full_paise": api.MILAN_FULL_PAISE, "seconds_left": 600})
    assert api._order_amount_paise(milan_rec) == api.MILAN_PRICE_PAISE  # ₹499 when ON


def test_offer_status_endpoint_shape():
    from fastapi.testclient import TestClient
    c = TestClient(api.app)
    body = c.get("/api/offer_status").json()
    assert body["phase"] in ("on", "off")
    assert {"phase", "price_paise", "full_paise", "seconds_left"} <= set(body)
    assert body["price_paise"] in (api.MILAN_PRICE_PAISE, api.MILAN_FULL_PAISE)
