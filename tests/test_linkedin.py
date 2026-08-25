"""LinkedIn Insight Tag + Conversions API — the paid-ads funnel

    Click -> Landing -> Form Filled -> Checkout Initiated -> Purchase

The funnel rides on the Meta Pixel calls the landing pages already make, so the
load-bearing guarantees are structural rather than per-page:

  * the Insight Tag is injected AFTER the Meta block, or the bridge that wraps
    window.fbq would run before fbq exists and the whole funnel would be silent;
  * every conversion is INDEPENDENTLY dormant until its id is configured, so
    shipping this with an empty config is a no-op rather than a stream of errors;
  * the server-side Conversions API never sends a phone number — LinkedIn has no
    hashed-phone id type and rejects the event — even though the Meta CAPI right
    next to it does send one;
  * a sale is deduped browser-vs-server on eventId == report id.
"""
import io
import json
import os

import api
import tracking

KUNDLI = {"name": "LI Buyer", "dob": "1991-06-10", "tob": "09:20",
          "time_quality": "T0", "place": "Delhi", "gender": "female"}

# A page that already carries the hardcoded Meta/Clarity block (pages/*.html)
# and one that does not (the report page, /account, /login).
STATIC_PAGE = ("<html><head><title>t</title><script>clarity.ms/tag</script>"
               "<script>fbq('init','x')</script></head><body>hi</body></html>")
BARE_PAGE = "<html><head><title>t</title></head><body>hi</body></html>"
# A funnel landing page is identified by its Lead fire — the same marker
# api._is_funnel_page() looks for. Only these fire the Landing conversion.
FUNNEL_PAGE = ("<html><head><title>t</title></head><body>"
               "<script>fbq('track','Lead',{},{eventID:R});</script>"
               "</body></html>")


def _configure(monkeypatch, landing="1111111", lead="2222222",
               checkout="3333333", purchase="4444444", partner="10777105"):
    """api reads these from env at import time, so tests set the module
    attributes directly (same approach test_tracking.py uses for the keys)."""
    monkeypatch.setattr(api, "LINKEDIN_PARTNER_ID", partner)
    monkeypatch.setattr(api, "_LINKEDIN_CONV_LANDING", landing)
    monkeypatch.setattr(api, "_LINKEDIN_CONV", {k: v for k, v in {
        "Lead": lead, "InitiateCheckout": checkout, "Purchase": purchase,
    }.items() if v})


# ----------------------------------------------------------- browser: the tag

def test_tag_lands_after_meta_on_a_hardcoded_page(monkeypatch):
    """pages/*.html embed Meta by hand, so _inject_ga_meta_clarity skips them —
    LinkedIn must still be added, and still after fbq."""
    _configure(monkeypatch)
    out = api._inject_tracking(STATIC_PAGE)
    assert "snap.licdn.com" in out
    assert out.index("fbq") < out.index("snap.licdn.com"), \
        "bridge wraps window.fbq — it must be parsed after the Meta snippet"


def test_tag_lands_after_meta_on_a_python_built_page(monkeypatch):
    """The report page has no hardcoded block: Meta is injected, then LinkedIn
    after it. Regression guard for the ordering inside _inject_tracking."""
    _configure(monkeypatch)
    out = api._inject_tracking(BARE_PAGE)
    assert "connect.facebook.net" in out and "snap.licdn.com" in out
    assert out.index("connect.facebook.net") < out.index("snap.licdn.com")


def test_injection_is_idempotent(monkeypatch):
    _configure(monkeypatch)
    once = api._inject_tracking(BARE_PAGE)
    twice = api._inject_tracking(once)
    assert twice.count("snap.licdn.com") == once.count("snap.licdn.com") == 1


def test_every_funnel_step_is_wired(monkeypatch):
    """The four steps the ads funnel reports on."""
    _configure(monkeypatch)
    out = api._inject_tracking(FUNNEL_PAGE)
    conv = json.loads(out.split("var CONV = ")[1].split(";")[0])
    assert conv == {"Lead": "2222222",              # form filled
                    "InitiateCheckout": "3333333",  # checkout opened
                    "Purchase": "4444444"}          # paid
    assert 'var LANDING = "1111111"' in out         # landing, fired on page load
    assert '_linkedin_partner_id = "10777105"' in out


def test_bridge_passes_event_id_for_dedup(monkeypatch):
    """The browser fire must carry Meta's {eventID: rid} as LinkedIn's event_id,
    or LinkedIn cannot discard the server-side copy of the same sale."""
    _configure(monkeypatch)
    out = api._inject_tracking(BARE_PAGE)
    assert "p.event_id = String(eventId)" in out
    assert "arguments[3] && arguments[3].eventID" in out


def test_unconfigured_conversions_are_dormant(monkeypatch):
    """No ids set -> the base tag still loads (retargeting + landing views still
    work) but nothing tries to fire a conversion."""
    _configure(monkeypatch, landing="", lead="", checkout="", purchase="")
    out = api._inject_tracking(FUNNEL_PAGE)
    assert "snap.licdn.com" in out
    assert "var CONV = {};" in out
    assert 'var LANDING = "";' in out


def test_empty_partner_id_removes_linkedin_entirely(monkeypatch):
    _configure(monkeypatch, partner="")
    assert "snap.licdn.com" not in api._inject_tracking(BARE_PAGE)


def test_real_landing_page_carries_the_tag(client, monkeypatch):
    """End-to-end through the actual route, not just the injector."""
    _configure(monkeypatch)
    body = client.get("/en/marriage-v3").text
    assert "snap.licdn.com" in body
    assert body.index("fbq") < body.index("snap.licdn.com")


# ------------------------------------------------- server: the Conversions API

def test_capi_dormant_without_token(monkeypatch):
    monkeypatch.setattr(tracking, "LINKEDIN_CAPI_TOKEN", "")
    monkeypatch.setattr(tracking, "LINKEDIN_CONV_PURCHASE_CAPI", "999")
    sent = []
    monkeypatch.setattr(tracking, "_post_json", lambda *a, **k: sent.append(a))
    tracking._linkedin_purchase("rid1", 499, "INR", "a@b.com")
    assert sent == []


def test_capi_dormant_without_conversion_rule(monkeypatch):
    """The token alone is not enough — the CAPI needs its OWN conversion rule,
    separate from the Insight Tag's, or LinkedIn has nothing to attribute to."""
    monkeypatch.setattr(tracking, "LINKEDIN_CAPI_TOKEN", "tok")
    monkeypatch.setattr(tracking, "LINKEDIN_CONV_PURCHASE_CAPI", "")
    sent = []
    monkeypatch.setattr(tracking, "_post_json", lambda *a, **k: sent.append(a))
    tracking._linkedin_purchase("rid1", 499, "INR", "a@b.com")
    assert sent == []


def _capture(monkeypatch):
    monkeypatch.setattr(tracking, "LINKEDIN_CAPI_TOKEN", "tok")
    monkeypatch.setattr(tracking, "LINKEDIN_CONV_PURCHASE_CAPI", "70203")
    sent = {}

    def _fake(url, payload, headers=None):
        sent["url"], sent["payload"], sent["headers"] = url, payload, headers
        return 201, "{}"

    monkeypatch.setattr(tracking, "_post_json", _fake)
    return sent


def test_capi_payload_matches_linkedin_schema(monkeypatch):
    sent = _capture(monkeypatch)
    tracking._linkedin_purchase("rid42", 499, "INR", "Buyer@Example.com",
                                li_fat_id="fat123", client_ip_address="1.2.3.4")
    p = sent["payload"]
    assert sent["url"] == "https://api.linkedin.com/rest/conversionEvents"
    assert p["conversion"] == "urn:lla:llaPartnerConversion:70203"
    assert p["eventId"] == "rid42"                    # dedup key vs the browser
    assert p["conversionValue"] == {"currencyCode": "INR", "amount": "499.00"}
    assert isinstance(p["conversionValue"]["amount"], str)   # schema wants a string
    # epoch MILLISECONDS, not seconds — LinkedIn rejects anything over 90 days old
    assert p["conversionHappenedAt"] > 1_000_000_000_000
    assert sent["headers"]["X-Restli-Protocol-Version"] == "2.0.0"
    assert sent["headers"]["Authorization"] == "Bearer tok"
    assert sent["headers"]["LinkedIn-Version"] == tracking.LINKEDIN_API_VERSION


def test_capi_sends_every_identifier_it_has(monkeypatch):
    sent = _capture(monkeypatch)
    tracking._linkedin_purchase("rid42", 499, "INR", "Buyer@Example.com",
                                li_fat_id="fat123", client_ip_address="1.2.3.4")
    ids = {u["idType"]: u["idValue"] for u in sent["payload"]["user"]["userIds"]}
    assert ids["SHA256_EMAIL"] == tracking._sha256("buyer@example.com")  # lowercased
    assert ids["LINKEDIN_FIRST_PARTY_ADS_TRACKING_UUID"] == "fat123"
    assert ids["PLAINTEXT_IP_ADDRESS"] == "1.2.3.4"


def test_capi_never_sends_a_phone(monkeypatch):
    """LinkedIn has no hashed-phone id type. The Meta CAPI beside it DOES send
    one, so this guards against someone 'fixing' the asymmetry."""
    sent = _capture(monkeypatch)
    tracking.track_purchase("rid42", 499, "INR", phone="9876543210",
                            email="a@b.com", client_ip_address="1.2.3.4")
    blob = json.dumps(sent["payload"])
    assert "9876543210" not in blob
    assert tracking._sha256(tracking._norm_phone("9876543210")) not in blob
    assert "SHA256_PHONE" not in blob


def test_capi_skips_an_event_it_could_never_match(monkeypatch):
    """Phone-only buyer with no email, no click id and no IP: LinkedIn would
    400 the request and could not attribute it anyway, so we don't send it."""
    sent = _capture(monkeypatch)
    tracking._linkedin_purchase("rid42", 499, "INR", email=None)
    assert sent == {}


def test_li_fat_id_alone_is_enough(monkeypatch):
    """The common case for these ads: a phone-only sale that is still
    attributable because the click id was captured at landing."""
    sent = _capture(monkeypatch)
    tracking._linkedin_purchase("rid42", 499, "INR", email=None, li_fat_id="fat123")
    ids = [u["idType"] for u in sent["payload"]["user"]["userIds"]]
    assert ids == ["LINKEDIN_FIRST_PARTY_ADS_TRACKING_UUID"]


def test_one_dead_destination_does_not_block_the_others(monkeypatch):
    """Meta, GA4 and LinkedIn each fire independently — a network failure in one
    must not cost the sale its report in the other two."""
    monkeypatch.setattr(tracking, "META_CAPI_TOKEN", "tok")

    def _boom(*a, **k):
        raise RuntimeError("meta is down")

    fired = []
    monkeypatch.setattr(tracking, "_meta_purchase", _boom)
    monkeypatch.setattr(tracking, "_ga4_purchase", lambda *a, **k: fired.append("ga4"))
    monkeypatch.setattr(tracking, "_linkedin_purchase",
                        lambda *a, **k: fired.append("linkedin"))
    assert tracking.track_purchase("rid1", 499, "INR", "98765", "a@b.com") is None
    assert fired == ["ga4", "linkedin"]


def test_enabled_flips_on_the_linkedin_token_alone(monkeypatch):
    monkeypatch.setattr(tracking, "META_CAPI_TOKEN", "")
    monkeypatch.setattr(tracking, "GA4_API_SECRET", "")
    monkeypatch.setattr(tracking, "LINKEDIN_CAPI_TOKEN", "tok")
    assert tracking.enabled() is True


# ------------------------------------------------------ the click id round-trip

def test_click_id_cookie_is_persisted_at_order(client):
    """The tag parks li_fat_id in a first-party cookie at landing; /api/order
    reads it server-side so no page JS had to be edited to forward it."""
    rid = client.post("/api/kundli", json=KUNDLI).json()["report_id"]
    client.post("/api/order", json={"report_id": rid},
                cookies={"ax_li_fat": "fat-abc-123"})
    assert api.get_report(rid)["payload"]["meta"]["_li_fat_id"] == "fat-abc-123"


def test_click_id_reaches_the_purchase_fire(client, monkeypatch, pay_webhook):
    """...and survives all the way to the webhook's server-side Purchase."""
    calls = []
    monkeypatch.setattr(tracking, "track_purchase",
                        lambda *a, **k: calls.append(k))
    rid = client.post("/api/kundli", json=KUNDLI).json()["report_id"]
    client.post("/api/order", json={"report_id": rid},
                cookies={"ax_li_fat": "fat-abc-123"})
    pay_webhook(client, rid, "pay_li_1", "+919812345678", "buyer@example.com")
    assert calls and calls[0]["li_fat_id"] == "fat-abc-123"


def test_missing_click_id_is_not_stored(client):
    """No cookie -> no key, rather than an empty string that would look like a
    real identifier to _linkedin_purchase."""
    rid = client.post("/api/kundli", json=KUNDLI).json()["report_id"]
    client.post("/api/order", json={"report_id": rid})
    assert "_li_fat_id" not in api.get_report(rid)["payload"].get("meta", {})


# ------------------------------------------------ the bridge's one dependency

FUNNEL_EVENTS = ("fbq('track','Lead'",
                 "fbq('track','InitiateCheckout')",
                 "fbq('track','Purchase'")

PAGES_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pages")


def _funnel_pages():
    """Every pages/*.html that fires at least one funnel event."""
    for dirpath, _dirs, names in os.walk(PAGES_ROOT):
        for n in sorted(names):
            if not n.endswith(".html"):
                continue
            path = os.path.join(dirpath, n)
            html = io.open(path, encoding="utf-8", errors="replace").read()
            if any(e in html for e in FUNNEL_EVENTS):
                yield os.path.relpath(path, PAGES_ROOT), html


def test_every_funnel_page_still_carries_the_meta_pixel():
    """CI GATE — the one way this design can fail silently.

    LinkedIn conversions are re-emitted from the Meta Pixel calls (see
    api._linkedin_head), so a funnel page that loses its Pixel keeps looking
    fine while its LinkedIn reporting quietly goes to zero. Meta's own numbers
    would drop too, but nobody watches two dashboards at once. This turns that
    into a build failure instead.

    If Meta is ever dropped site-wide, delete this test AND replace the bridge
    with explicit lintrk() calls — do not simply loosen the assertion.
    """
    pages = list(_funnel_pages())
    assert pages, "no funnel pages matched — FUNNEL_EVENTS is stale"
    missing = [name for name, html in pages if "fbq('init'" not in html]
    assert not missing, (
        "these pages fire a funnel event but no longer initialise the Meta "
        "Pixel, so their LinkedIn conversions are dead: %s" % missing)


def test_changing_the_meta_pixel_id_cannot_affect_linkedin(monkeypatch):
    """Swapping the Pixel ID is a no-op for LinkedIn: the bridge only mirrors
    fbq('track', ...) calls, and fbq('init', <id>) passes through untouched."""
    _configure(monkeypatch)
    bridge = api._inject_tracking(BARE_PAGE).split("var CONV = ")[1]
    assert "arguments[0] === 'track'" in bridge
    conv = json.loads(bridge.split(";")[0])
    assert "init" not in conv and set(conv) == {"Lead", "InitiateCheckout",
                                                "Purchase"}


# ------------------------------------------- Landing fires ONLY where a Lead can

def test_landing_fires_on_a_funnel_page(monkeypatch):
    _configure(monkeypatch)
    assert 'var LANDING = "1111111"' in api._inject_tracking(FUNNEL_PAGE)


def test_landing_does_not_fire_on_the_report_page(monkeypatch):
    """THE DOUBLE-COUNT BUG. The post-payment redirect loads /report/<id>; that
    page load used to fire Landing a second time for the same buyer, inflating
    the top of the funnel and wrecking the Landing -> Form Filled rate."""
    _configure(monkeypatch)
    out = api._inject_tracking(BARE_PAGE)          # report page: no Lead fire
    assert 'var LANDING = "";' in out
    assert "1111111" not in out


def test_landing_does_not_fire_on_content_pages(monkeypatch):
    """Blog, celebrity, legal and /account pages are not ad destinations."""
    _configure(monkeypatch)
    assert 'var LANDING = "";' in api._inject_tracking(STATIC_PAGE)


def test_base_tag_still_loads_where_landing_does_not(monkeypatch):
    """Scoping the CONVERSION must not scope the TAG — retargeting audiences,
    click attribution and the li_fat_id capture all need site-wide coverage."""
    _configure(monkeypatch)
    out = api._inject_tracking(BARE_PAGE)
    assert "snap.licdn.com" in out
    assert "ax_li_fat" in out                      # click id still captured
    assert '_linkedin_partner_id = "10777105"' in out


def test_funnel_page_detection_matches_the_real_pages():
    """The marker must match every real funnel page and no content page —
    a spacing change in one page would silently drop it from the funnel."""
    funnel = {n for n, h in _funnel_pages()}
    assert len(funnel) >= 17, "expected the 17 product landing pages, got %d" % len(funnel)
    for name, html in _funnel_pages():
        assert api._is_funnel_page(html), "%s fires Lead but is not detected" % name
