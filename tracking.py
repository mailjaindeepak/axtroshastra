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
    LINKEDIN_CAPI_TOKEN         Campaign Manager -> Data -> Signals Manager ->
                                Direct API -> Generate access token. Use THAT
                                advertiser path, not a developer app: it needs
                                no app review and the token does not expire.
                                Campaign Manager does not store it, so copy it
                                once. (The developer-portal OAuth route is for
                                partner platforms and expires every 60 days.)
    LINKEDIN_CONV_PURCHASE_CAPI Numeric id of a Campaign Manager conversion rule
                                whose conversionMethod is CONVERSIONS_API. This
                                MUST be a DIFFERENT rule from the Insight Tag's
                                purchase conversion — LinkedIn requires one rule
                                per data source (browser vs server) and dedups
                                across them on eventId. See docs/linkedin_ads.md.
    (Optional overrides: META_PIXEL_ID, GA4_MEASUREMENT_ID, META_API_VERSION,
     LINKEDIN_API_VERSION — they default to the site's live IDs.)

WHY LINKEDIN TAKES NO PHONE
    Meta matches on hashed phone; LinkedIn's Conversions API does not support it
    at all. Its accepted identifiers are SHA256_EMAIL, the li_fat_id click id
    (LINKEDIN_FIRST_PARTY_ADS_TRACKING_UUID), IP, GOOGLE_AID, ACXIOM_ID,
    first+last name, externalIds and lead. Most buyers here pay with a phone and
    no email, so the li_fat_id captured at landing is what carries the match —
    without it a phone-only sale cannot be attributed to LinkedIn at all.
"""
import os
import json
import time
import hashlib
import logging
import urllib.request
import urllib.parse
import urllib.error

logger = logging.getLogger("uvicorn.error")

META_PIXEL_ID = os.getenv("META_PIXEL_ID", "1454249773521031")
META_CAPI_TOKEN = os.getenv("META_CAPI_TOKEN", "")
META_API_VERSION = os.getenv("META_API_VERSION", "v19.0")
GA4_MEASUREMENT_ID = os.getenv("GA4_MEASUREMENT_ID", "G-NKRQM1HJ97")
GA4_API_SECRET = os.getenv("GA4_API_SECRET", "")
LINKEDIN_CAPI_TOKEN = os.getenv("LINKEDIN_CAPI_TOKEN", "")
LINKEDIN_CONV_PURCHASE_CAPI = os.getenv("LINKEDIN_CONV_PURCHASE_CAPI", "")
# Marketing API version, "YYYYMM". LinkedIn sunsets each version ~12 months on;
# bump this env var when the deprecation warning appears in the response body.
LINKEDIN_API_VERSION = os.getenv("LINKEDIN_API_VERSION", "202608")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://www.axtroshastra.com").rstrip("/")

_TIMEOUT = 5   # seconds; a slow ad-network call must never hold a request


def enabled() -> bool:
    """True if at least one destination is configured. Cheap gate so callers
    (and tests) can skip work entirely when the feature is dormant."""
    return bool(META_CAPI_TOKEN or GA4_API_SECRET or LINKEDIN_CAPI_TOKEN)


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


def _post_json(url: str, payload: dict, headers: dict = None):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers=headers or {"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


def _meta_purchase(rid, value, currency, phone, email,
                   fbc=None, fbp=None, client_user_agent=None,
                   client_ip_address=None):
    if not META_CAPI_TOKEN:
        return
    user_data = {}
    ph = _sha256(_norm_phone(phone))
    if ph:
        user_data["ph"] = [ph]
    em = _sha256(email)
    if em:
        user_data["em"] = [em]
    if fbc:
        user_data["fbc"] = fbc
    if fbp:
        user_data["fbp"] = fbp
    if client_user_agent:
        user_data["client_user_agent"] = client_user_agent
    if client_ip_address:
        user_data["client_ip_address"] = client_ip_address
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


def _linkedin_purchase(rid, value, currency, email,
                       li_fat_id=None, client_ip_address=None):
    """Stream a Purchase to LinkedIn's Conversions API.

    POST /rest/conversionEvents, one event per call. `eventId` is the report id,
    the same value the browser Insight Tag sends as {event_id: rid} — LinkedIn
    dedups on it and keeps the browser copy, so a sale is counted once even when
    both fire.

    NOTE the identifier list deliberately omits phone: LinkedIn has no hashed-
    phone id type (see module docstring). An event with no usable identifier is
    dropped here rather than sent, because LinkedIn rejects it with a 400 and an
    unmatched event cannot be attributed anyway.
    """
    if not (LINKEDIN_CAPI_TOKEN and LINKEDIN_CONV_PURCHASE_CAPI):
        return
    user_ids = []
    em = _sha256(email)
    if em:
        user_ids.append({"idType": "SHA256_EMAIL", "idValue": em})
    if li_fat_id:
        user_ids.append({"idType": "LINKEDIN_FIRST_PARTY_ADS_TRACKING_UUID",
                         "idValue": li_fat_id})
    if client_ip_address:
        user_ids.append({"idType": "PLAINTEXT_IP_ADDRESS",
                         "idValue": client_ip_address})
    if not user_ids:
        logger.info("[li-capi] purchase %s skipped - no LinkedIn-usable identifier", rid)
        return
    payload = {
        "conversion": f"urn:lla:llaPartnerConversion:{LINKEDIN_CONV_PURCHASE_CAPI}",
        # epoch MILLISECONDS, and LinkedIn rejects anything older than 90 days.
        "conversionHappenedAt": int(time.time() * 1000),
        "conversionValue": {"currencyCode": currency,
                            "amount": f"{float(value):.2f}"},   # amount is a string
        "eventId": rid,
        "user": {"userIds": user_ids},
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINKEDIN_CAPI_TOKEN}",
        "LinkedIn-Version": LINKEDIN_API_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }
    try:
        status, body = _post_json("https://api.linkedin.com/rest/conversionEvents",
                                  payload, headers)
        if status >= 300:
            logger.error("[li-capi] purchase %s -> %s %s", rid, status, body[:300])
    except urllib.error.HTTPError as e:
        # LinkedIn puts the useful validation detail in the response body
        # ("must contain one of these fields...", "Conversion time should be
        # within 90 days", version sunset notices) - log it or debugging is blind.
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")[:400]
        except Exception:
            pass
        logger.error("[li-capi] purchase %s -> %s %s", rid, e.code, detail)
    except Exception as e:
        logger.error("[li-capi] purchase failed for %s: %s", rid, e)


def track_purchase(rid, value=499, currency="INR", phone=None, email=None,
                   ga_client_id=None, fbc=None, fbp=None,
                   client_user_agent=None, client_ip_address=None,
                   li_fat_id=None):
    """Fire a Purchase to Meta CAPI + GA4 MP + LinkedIn CAPI. No-op unless a
    secret is set. Never raises — safe to hand to a payment background task. Do
    NOT call for free-pass unlocks (no real revenue; the browser skips them too).

    Each destination is wrapped separately so one network failure cannot stop
    the others from reporting the same sale."""
    if not enabled():
        return
    for fire in (
        lambda: _meta_purchase(rid, value, currency, phone, email,
                               fbc=fbc, fbp=fbp,
                               client_user_agent=client_user_agent,
                               client_ip_address=client_ip_address),
        lambda: _ga4_purchase(rid, value, currency, ga_client_id),
        lambda: _linkedin_purchase(rid, value, currency, email,
                                   li_fat_id=li_fat_id,
                                   client_ip_address=client_ip_address),
    ):
        try:
            fire()
        except Exception as e:                      # never break the caller
            logger.error("[tracking] track_purchase failed for %s: %s", rid, e)
