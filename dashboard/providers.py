"""dashboard/providers.py — live reads from provider APIs for the dashboard.

Twilio account balance + Razorpay payment history. Uses only stdlib (urllib)
so no new dependency is added, reuses the existing env vars the app already
sets, caches results, has short timeouts, and NEVER raises — so the dashboard
degrades gracefully when a provider is unreachable or creds are missing.
"""
import base64
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime

_CACHE_TTL = 600  # 10 minutes
_twilio_cache = {"data": None, "ts": 0.0}
_rzp_cache = {"data": None, "ts": 0.0}


def twilio_balance():
    """Return the live Twilio balance, cached ~10 min. Never raises.

    Success: {"live": True, "balance": "$19.98", "currency": "USD",
              "as_of": "<iso>"}
    Otherwise: {"live": False, "note": "<why — creds missing / unreachable>"}
    """
    now = time.time()
    cached = _twilio_cache.get("data")
    if cached is not None and (now - _twilio_cache.get("ts", 0.0)) < _CACHE_TTL:
        return cached

    sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    tok = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    if not (sid and tok):
        res = {"live": False,
               "note": "Twilio credentials not set — showing saved balance."}
        _twilio_cache.update(data=res, ts=now)
        return res

    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Balance.json"
    auth = base64.b64encode(f"{sid}:{tok}".encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": "Basic " + auth})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
        raw = str(data.get("balance", "")).strip()
        currency = (data.get("currency") or "USD").upper()
        symbol = "$" if currency == "USD" else ""
        # Twilio returns e.g. "19.98" or "-3.50"; render with a leading symbol.
        display = (symbol + raw) if raw else "—"
        res = {"live": True, "balance": display, "currency": currency,
               "as_of": datetime.utcnow().isoformat() + "Z"}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            ValueError, OSError):
        res = {"live": False,
               "note": "Twilio Balance API unreachable — showing saved balance."}
    _twilio_cache.update(data=res, ts=now)
    return res


def razorpay_payments(limit=100):
    """Fetch captured payments from Razorpay, cached ~10 min. Never raises.

    Success: {"live": True, "payments": [{id, amount_inr, contact, email,
              method, created_at, notes, order_id}, ...]}
    Otherwise: {"live": False, "payments": [], "note": "<why>"}
    """
    now = time.time()
    cached = _rzp_cache.get("data")
    if cached is not None and (now - _rzp_cache.get("ts", 0.0)) < _CACHE_TTL:
        return cached

    key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
    if not (key_id and key_secret):
        res = {"live": False, "payments": [],
               "note": "Razorpay credentials not set."}
        _rzp_cache.update(data=res, ts=now)
        return res

    all_payments = []
    skip = 0
    try:
        while True:
            page_size = min(limit - len(all_payments), 100)
            url = ("https://api.razorpay.com/v1/payments"
                   f"?count={page_size}&skip={skip}")
            auth = base64.b64encode(f"{key_id}:{key_secret}".encode()).decode()
            req = urllib.request.Request(
                url, headers={"Authorization": "Basic " + auth})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())
            items = data.get("items") or []
            for p in items:
                if (p.get("status") or "") != "captured":
                    continue
                all_payments.append({
                    "id": p.get("id", ""),
                    "amount_inr": (p.get("amount") or 0) // 100,
                    "contact": p.get("contact") or "",
                    "email": p.get("email") or "",
                    "method": p.get("method") or "",
                    "created_at": _unix_to_iso(p.get("created_at")),
                    "notes": p.get("notes") or {},
                    "order_id": p.get("order_id") or "",
                })
            if len(items) < page_size or len(all_payments) >= limit:
                break
            skip += len(items)
        res = {"live": True, "payments": all_payments}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            ValueError, OSError):
        res = {"live": False, "payments": [],
               "note": "Razorpay API unreachable."}
    _rzp_cache.update(data=res, ts=now)
    return res


def _unix_to_iso(ts):
    """Convert Unix timestamp to ISO string, or return empty."""
    if not ts:
        return ""
    try:
        return datetime.utcfromtimestamp(int(ts)).isoformat()
    except (ValueError, OSError, OverflowError):
        return ""
