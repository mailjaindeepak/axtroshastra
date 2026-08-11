"""dashboard/providers.py — live reads from provider APIs for the dashboard.

Currently: Twilio account balance. Uses only the stdlib (urllib) so no new
dependency is added, reuses the TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN env the
app already sets, caches for ~10 minutes, has a short timeout, and NEVER raises —
so the dashboard degrades gracefully to the config fallback when Twilio is
unreachable or the creds are missing.
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
