"""
Rate limiting and bot defense. (#4)

- Token-bucket limiter keyed by client IP (in-process; swap for Redis when you
  run multiple instances).
- Per-path policies so the expensive/compute and payment routes are stricter than
  static pages.
- CAPTCHA verification helper (hCaptcha or reCAPTCHA), env-gated: when no secret
  is configured `captcha_ok()` returns True so nothing breaks in dev.

Wire-up (in api.py):
    from ratelimit import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)

Env:
  RATE_LIMIT_ENABLED   "1" (default) | "0"
  CAPTCHA_PROVIDER     "" (off) | "hcaptcha" | "recaptcha"
  CAPTCHA_SECRET       provider secret
"""
import json
import os
import threading
import time
import urllib.parse
import urllib.request

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# path-prefix -> (capacity, refill_tokens_per_second)
POLICIES = {
    "/api/kundli":  (10, 10 / 60),    # 10 burst, ~10/min sustained (compute-heavy)
    "/api/milan":   (10, 10 / 60),
    "/api/order":   (12, 12 / 60),    # payment endpoint — card-testing guard
    "/api/webhook": (600, 10.0),      # provider callbacks — generous, never block Razorpay
    "/api/make_pass": (5, 5 / 60),
    "/api/":        (60, 60 / 60),    # other api routes
    "/":            (240, 240 / 60),  # pages / static — lenient
}

_buckets: dict = {}
_lock = threading.Lock()


def _policy(path: str):
    for prefix in sorted(POLICIES, key=len, reverse=True):
        if path.startswith(prefix):
            return POLICIES[prefix]
    return POLICIES["/"]


def _client_ip(request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def allow(ip: str, path: str) -> bool:
    """Consume one token for (ip, policy). True if allowed, False if over limit."""
    cap, refill = _policy(path)
    now = time.monotonic()
    bkey = (ip, cap, refill)
    with _lock:
        tokens, last = _buckets.get(bkey, (cap, now))
        tokens = min(cap, tokens + (now - last) * refill)
        if tokens < 1.0:
            _buckets[bkey] = (tokens, now)
            return False
        _buckets[bkey] = (tokens - 1.0, now)
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if os.getenv("RATE_LIMIT_ENABLED", "1") != "1":
            return await call_next(request)
        ip = _client_ip(request)
        if not allow(ip, request.url.path):
            return JSONResponse({"error": "rate_limited",
                                 "detail": "Too many requests. Thodi der baad try kijiye."},
                                status_code=429, headers={"Retry-After": "30"})
        return await call_next(request)


def captcha_ok(token: str, remote_ip: str = "") -> bool:
    """Verify a CAPTCHA token. Returns True when CAPTCHA is disabled (no secret)."""
    provider = os.getenv("CAPTCHA_PROVIDER", "").lower()
    secret = os.getenv("CAPTCHA_SECRET", "")
    if not provider or not secret:
        return True
    if not token:
        return False
    endpoints = {
        "hcaptcha": "https://hcaptcha.com/siteverify",
        "recaptcha": "https://www.google.com/recaptcha/api/siteverify",
    }
    url = endpoints.get(provider)
    if not url:
        return True
    try:
        payload = urllib.parse.urlencode(
            {"secret": secret, "response": token, "remoteip": remote_ip}).encode()
        with urllib.request.urlopen(url, data=payload, timeout=6) as r:
            return bool(json.load(r).get("success"))
    except Exception:
        return False  # fail closed on verification error
