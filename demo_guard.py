"""DEMO_MODE must never be on in production.

DEMO_MODE=1 turns on /api/_demo_pay/{report_id}, which unlocks ANY report for free with no payment, and it makes the login code come back in the
API response (auth.py), which lets anyone sign in as any phone number. It exists only for local development and the test suite.

A comment saying "never set it in production" is not a control. This module is the control: when the process looks like a production or public
deployment, DEMO_MODE is forced OFF at start-up, removed from the environment (auth.py reads the variable itself), and a CRITICAL line is logged.
The site keeps serving, closed, instead of staying open. Turning it off is fail-closed; the log and the deploy test make the mistake visible.

Signals that mean "not a private local machine" (any one is enough):
  * a live Razorpay key (rzp_live_...)
  * PUBLIC_BASE_URL pointing anywhere except localhost / 127.0.0.1
  * a database host that is not local
  * APP_ENV / ENVIRONMENT set to production
  * running on Elastic Beanstalk (/opt/elasticbeanstalk or /var/app/current exist)
A developer using a public tunnel (ngrok and the like) therefore cannot use DEMO_MODE either, which is the safe default: a tunnel would publish the
free-unlock route to the internet.
"""
import logging
import os
from urllib.parse import urlparse

logger = logging.getLogger("axtroshastra")

LOCAL_HOSTS = {"", "localhost", "127.0.0.1", "::1", "0.0.0.0", "testserver"}
PRODUCTION_WORDS = {"prod", "production", "live"}
EB_MARKERS = ("/opt/elasticbeanstalk", "/var/app/current")


def _host(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    return (urlparse(url if "://" in url else "//" + url).hostname or "").lower()


def blockers(env=None, exists=os.path.exists) -> list:
    """Why DEMO_MODE is not allowed here. An empty list means this looks like a private local machine."""
    env = os.environ if env is None else env
    out = []
    if (env.get("RAZORPAY_KEY_ID") or "").strip().startswith("rzp_live_"):
        out.append("a live Razorpay key is configured")
    host = _host(env.get("PUBLIC_BASE_URL", ""))
    if host and host not in LOCAL_HOSTS and not host.endswith(".localhost"):
        out.append(f"PUBLIC_BASE_URL points at {host}")
    db_host = (env.get("DB_HOST") or "").strip().lower()
    if db_host and db_host not in LOCAL_HOSTS and not db_host.endswith(".localhost"):
        out.append("the database host is not local")
    for name in ("APP_ENV", "ENVIRONMENT", "ENV", "STAGE"):
        if (env.get(name) or "").strip().lower() in PRODUCTION_WORDS:
            out.append(f"{name} says production")
    if any(exists(p) for p in EB_MARKERS):
        out.append("running on Elastic Beanstalk")
    return out


def enforce(requested: bool, env=None, exists=os.path.exists) -> bool:
    """The DEMO_MODE value the app must use. `requested` is what the environment asked for. If that is True but this looks like production,
    return False, remove the variable from the environment (auth.py reads it independently), and log CRITICAL."""
    if not requested:
        return False
    reasons = blockers(env, exists)
    if not reasons:
        return True
    logger.critical("[security] DEMO_MODE=1 was set but is IGNORED and switched off: %s. It would let anyone unlock any report for free and read "
                    "login codes. Remove DEMO_MODE from the environment.", "; ".join(reasons))
    target = os.environ if env is None else env
    try:
        target.pop("DEMO_MODE", None)
    except Exception:
        pass
    return False
