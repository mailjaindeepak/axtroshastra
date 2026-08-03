"""Server-side purchase tracking — Meta Conversions API + GA4 Measurement
Protocol. Dormant until the matching secret is set (mirrors delivery.py's
env-gated design). Never raises.

WHY THIS EXISTS
    The browser-side Pixel/gtag Purchase events fire only if the buyer stays on
    the page after paying AND has no ad-blocker / tracking-prevention (Safari
    ITP, etc.). When that client fire is lost, the ad platforms never learn the
    sale happened — so reports undercount and optimisation degrades, even though
    the payment itself succeeded server-side.

    This module re-fires the same Purchase from the payment webhook (the
    reliable source of truth), so the conversion is reported regardless of the
    browser. The customer's payment/report flow is unaffected either way.

DEDUPLICATION (so a sale is counted ONCE when both the browser and server fire)
    * Meta : event_id = report id. The browser Pixel must send the same id as
             {eventID: rid} on its Purchase fire (wired in the funnel pages).
             Meta dedups on (event_name, event_id).
    * GA4  : transaction_id = report id. The browser gtag already sends
             transaction_id: REPORT_ID; GA4 auto-dedups purchase on it.

ACTIVATION (owner's step — set these on Elastic Beanstalk, like the Twilio keys)
    META_CAPI_TOKEN    Meta Events Manager -> Pixel -> Settings -> Conversions
                       API -> Generate access token
    GA4_API_SECRET     GA4 Admin -> Data Streams -> (stream) -> Measurement
                       Protocol API secrets -> Create
    (Optional overrides: META_PIXEL_ID, GA4_MEASUREMENT_ID, META_API_VERSION —
     they default to the site's live IDs.)
"""
import os
import json
import time
import hashlib
import logging
import urllib.request
import urllib.parse

logger = logging.getLogger("uvicorn.error")

META_PIXEL_ID = os.getenv("META_PIXEL_ID", "2417544725436982")
META_CAPI_TOKEN = os.getenv("META_CAPI_TOKEN", "")
META_API_VERSION = os.getenv("META_API_VERSION", "v19.0")
GA4_MEASUREMENT_ID = os.getenv("GA4_MEASUREMENT_ID", "G-NKRQM1HJ97")
GA4_API_SECRET = os.getenv("GA4_API_SECRET", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://www.axtroshastra.com").rstrip("/")

_TIMEOUT = 5   # seconds; a slow ad-network call must never hold a request


def enabled() -> bool:
    """True if at least one destination is configured. Cheap gate so callers
    (and tests) can skip work entirely when the feature is dormant."""
    return bool(META_CAPI_TOKEN or GA4_API_SECRET)


def _sha256(value: str):
    """Lower-cased, trimmed SHA-256 hex — the format Meta expects for hashed
    user data. Returns None for empty input."""
    value = (value or "").strip().lower()
    return hashlib.sha256(value.encode()).hexdigest() if value else None


def _norm_phone(phone: str):
    """Digits-only E.164 without '+', assuming India when no country code is
    present (e.g. '98765 43210' -> '919876543210'). Meta hashes this form."""
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if len(digits) == 10:
        digits = "91" + digits
    return digits or None


def _post_json(url: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


def _meta_purchase(rid, value, currency, phone, email):
    if not META_CAPI_TOKEN:
        return
    user_data = {}
    ph = _sha256(_norm_phone(phone))
    if ph:
        user_data["ph"] = [ph]
    em = _sha256(email)
    if em:
        user_data["em"] = [em]
    payload = {
        "data": [{
            "event_name": "Purchase",
            "event_time": int(time.time()),
            "event_id": rid,                       # dedup key vs the browser Pixel
            "action_source": "website",
            "event_source_url": f"{PUBLIC_BASE_URL}/report/{rid}",
            "user_data": user_data,
            "custom_data": {"currency": currency, "value": float(value)},
        }],
    }
    url = (f"https://graph.facebook.com/{META_API_VERSION}/{META_PIXEL_ID}/events"
           f"?access_token={urllib.parse.quote(META_CAPI_TOKEN)}")
    try:
        status, body = _post_json(url, payload)
        if status >= 300:
            logger.error("[capi] Meta purchase %s -> %s %s", rid, status, body[:300])
    except Exception as e:
        logger.error("[capi] Meta purchase failed for %s: %s", rid, e)


def _ga4_client_id(rid, ga_client_id):
    """Prefer the browser's GA client id (captured at checkout) so the server
    purchase ties to the user's session/source. When it isn't available (e.g.
    the webhook path has no browser context), fall back to a STABLE id derived
    from the report id — dedup still holds via transaction_id, but session
    attribution is lost for that event."""
    if ga_client_id:
        return ga_client_id
    n = int(hashlib.sha256(rid.encode()).hexdigest()[:12], 16)
    return f"555.{n}"


def _ga4_purchase(rid, value, currency, ga_client_id):
    if not GA4_API_SECRET:
        return
    payload = {
        "client_id": _ga4_client_id(rid, ga_client_id),
        "non_personalized_ads": False,
        "events": [{
            "name": "purchase",
            "params": {
                "transaction_id": rid,             # GA4 dedups purchase on this
                "currency": currency,
                "value": float(value),
            },
        }],
    }
    url = (f"https://www.google-analytics.com/mp/collect"
           f"?measurement_id={urllib.parse.quote(GA4_MEASUREMENT_ID)}"
           f"&api_secret={urllib.parse.quote(GA4_API_SECRET)}")
    try:
        status, body = _post_json(url, payload)
        if status >= 300:
            logger.error("[ga4mp] purchase %s -> %s %s", rid, status, body[:300])
    except Exception as e:
        logger.error("[ga4mp] purchase failed for %s: %s", rid, e)


def track_purchase(rid, value=499, currency="INR", phone=None, email=None,
                   ga_client_id=None):
    """Fire a Purchase to Meta CAPI + GA4 MP. No-op unless a secret is set.
    Never raises — safe to hand to a payment background task. Do NOT call for
    free-pass unlocks (no real revenue; the browser skips them too)."""
    if not enabled():
        return
    try:
        _meta_purchase(rid, value, currency, phone, email)
        _ga4_purchase(rid, value, currency, ga_client_id)
    except Exception as e:                          # never break the caller
        logger.error("[tracking] track_purchase failed for %s: %s", rid, e)
