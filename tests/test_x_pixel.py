"""X (Twitter) pixel + Conversions API — pixel rf9y2

Browser side:
  * The X pixel base code (uwt.js + twq('config','rf9y2')) is injected into every
    served page via api._inject_x_pixel, chained in _inject_tracking.
  * A funnel bridge wraps window.fbq (same pattern as the LinkedIn bridge) to
    mirror Lead / InitiateCheckout / Purchase to the matching X event id.
  * The twclid click id is parked in a first-party cookie (ax_twclid) at landing,
    read at /api/order, and forwarded to the server-side Conversions API.

Server side:
  * tracking._x_purchase fires the Purchase conversion to X's Conversions API,
    dormant until X_PIXEL_TOKEN is set.
"""
import hashlib
import json

import api
import tracking


BARE_PAGE = "<html><head><title>t</title></head><body>hi</body></html>"
STATIC_PAGE = ("<html><head><title>t</title><script>clarity.ms/tag</script>"
               "<script>fbq('init','x')</script></head><body>hi</body></html>")

KUNDLI = {"name": "XBuyer", "dob": "1991-08-15", "tob": "10:30",
          "time_quality": "T0", "place": "Delhi", "gender": "male",
          "phone": "+919800000081"}


# ------------------------------------------------------------- browser: pixel

def test_pixel_injected_on_bare_page():
    out = api._inject_tracking(BARE_PAGE)
    assert "ads-twitter.com/uwt.js" in out
    assert "twq('config','rf9y2')" in out


def test_pixel_injected_on_hardcoded_static_page():
    out = api._inject_tracking(STATIC_PAGE)
    assert "ads-twitter.com/uwt.js" in out
    assert "twq('config','rf9y2')" in out


def test_injection_is_idempotent():
    once = api._inject_tracking(BARE_PAGE)
    twice = api._inject_tracking(once)
    assert twice.count("ads-twitter.com/uwt.js") == 1


def test_pixel_dormant_when_id_empty(monkeypatch):
    monkeypatch.setattr(api, "X_PIXEL_ID", "")
    out = api._inject_tracking(BARE_PAGE)
    assert "ads-twitter.com/uwt.js" not in out


# -------------------------------------------------------- browser: funnel bridge

def test_funnel_bridge_maps_all_three_events():
    out = api._inject_tracking(BARE_PAGE)
    conv = json.loads(out.split("var CONV = ")[1].split(";\n")[0])
    assert conv == {
        "Lead": "tw-rf9y2-rgqp0",
        "InitiateCheckout": "tw-rf9y2-rgqow",
        "Purchase": "tw-rf9y2-rgqob",
    }


def test_bridge_passes_conversion_id_for_dedup():
    out = api._inject_tracking(BARE_PAGE)
    assert "if(cid) p.conversion_id = String(cid)" in out
    assert "arguments[3] && arguments[3].eventID" in out


# -------------------------------------------------------- browser: twclid cookie

def test_twclid_cookie_capture_in_pixel():
    out = api._inject_tracking(BARE_PAGE)
    assert "ax_twclid" in out
    assert "twclid=([^&#]+)" in out


# ------------------------------------------------- server: twclid round-trip

def test_twclid_persisted_at_order(client):
    rid = client.post("/api/kundli", json=KUNDLI).json()["report_id"]
    client.post("/api/order", json={"report_id": rid},
                cookies={"ax_twclid": "tw-click-abc-123"})
    assert api.get_report(rid)["payload"]["meta"]["_twclid"] == "tw-click-abc-123"


def test_twclid_absent_when_no_cookie(client):
    kundli = {**KUNDLI, "phone": "+919800000082", "name": "NoTwclid"}
    rid = client.post("/api/kundli", json=kundli).json()["report_id"]
    client.post("/api/order", json={"report_id": rid})
    assert "_twclid" not in api.get_report(rid)["payload"].get("meta", {})


# ------------------------------------------------- server: X Conversions API

def _capture_x(monkeypatch):
    monkeypatch.setattr(tracking, "X_PIXEL_TOKEN", "test-tok")
    monkeypatch.setattr(tracking, "X_PIXEL_ID", "rf9y2")
    monkeypatch.setattr(tracking, "X_EVENT_PURCHASE", "tw-rf9y2-rgqob")
    sent = {}

    def _fake(url, payload, headers=None):
        sent["url"], sent["payload"], sent["headers"] = url, payload, headers
        return 200, "{}"

    monkeypatch.setattr(tracking, "_post_json", _fake)
    return sent


def test_capi_payload_matches_x_schema(monkeypatch):
    sent = _capture_x(monkeypatch)
    tracking._x_purchase("rid-x-42", phone="9876543210", email="Buyer@Test.com",
                         twclid="tw-click-999",
                         client_user_agent="Mozilla/5.0", client_ip_address="1.2.3.4")
    p = sent["payload"]
    assert sent["url"] == "https://ads-api.x.com/12/measurement/conversions/rf9y2"
    assert sent["headers"]["X-Pixel-Token"] == "test-tok"
    c = p["conversions"][0]
    assert c["event_id"] == "tw-rf9y2-rgqob"
    assert c["conversion_id"] == "rid-x-42"
    assert c["event_source_url"].endswith("/report/rid-x-42")
    ids = c["identifiers"][0]
    assert ids["twclid"] == "tw-click-999"
    assert ids["hashed_email"] == hashlib.sha256(b"buyer@test.com").hexdigest()
    assert ids["ip_address"] == "1.2.3.4"
    assert ids["user_agent"] == "Mozilla/5.0"
    expected_phone = hashlib.sha256("+919876543210".encode()).hexdigest()
    assert ids["hashed_phone_number"] == expected_phone


def test_capi_dormant_without_token(monkeypatch):
    monkeypatch.setattr(tracking, "X_PIXEL_TOKEN", "")
    sent = {}
    monkeypatch.setattr(tracking, "_post_json",
                        lambda *a, **k: sent.update({"called": True}))
    tracking._x_purchase("rid1", email="a@b.com")
    assert "called" not in sent


def test_capi_skips_when_no_identifiers(monkeypatch):
    sent = _capture_x(monkeypatch)
    tracking._x_purchase("rid-noident")
    assert sent == {}


def test_twclid_alone_is_enough(monkeypatch):
    sent = _capture_x(monkeypatch)
    tracking._x_purchase("rid-tw", twclid="tw-click-only")
    ids = sent["payload"]["conversions"][0]["identifiers"][0]
    assert list(ids.keys()) == ["twclid"]


def test_ip_plus_ua_is_enough(monkeypatch):
    sent = _capture_x(monkeypatch)
    tracking._x_purchase("rid-ipua", client_ip_address="10.0.0.1",
                         client_user_agent="UA/1.0")
    ids = sent["payload"]["conversions"][0]["identifiers"][0]
    assert "ip_address" in ids and "user_agent" in ids
    assert "twclid" not in ids


def test_one_dead_destination_does_not_block_x(monkeypatch):
    monkeypatch.setattr(tracking, "X_PIXEL_TOKEN", "tok")
    monkeypatch.setattr(tracking, "META_CAPI_TOKEN", "tok")
    x_called = []

    def _boom(*a, **k):
        raise ConnectionError("simulated")

    monkeypatch.setattr(tracking, "_meta_purchase", _boom)

    orig_x = tracking._x_purchase
    def _spy(*a, **k):
        x_called.append(1)
        return orig_x(*a, **k)
    monkeypatch.setattr(tracking, "_x_purchase", _spy)

    monkeypatch.setattr(tracking, "_post_json", lambda *a, **k: (200, "{}"))
    tracking.track_purchase("rid-iso", phone="9800000083", email="a@b.com",
                            twclid="tw-test", client_ip_address="1.1.1.1")
    assert x_called, "X CAPI must still fire even if Meta CAPI explodes"
