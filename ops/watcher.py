"""Deep health watcher for the ops framework.

A lightweight, dependency-free (stdlib only) probe that hits the RUNNING site
over HTTP and reports a green/red verdict. Meant to run OUTSIDE the app (a
GitHub Actions cron, a FEW times a day) so the monitor never depends on the
thing it monitors.

This is deliberately NOT the fast "is it up?" pulse. That shallow liveness ping
is handled for FREE by an EXTERNAL monitor (UptimeRobot, every 5 min against
/healthz) so we don't burn GitHub Actions minutes. This watcher instead runs a
few times a day and checks the DEEPER things UptimeRobot cannot see:

Checks (all against config.TARGET_URL with config.HTTP_TIMEOUT):
  1. GET /healthz/db                    -> 200                          (DB write-durability)
  2. GET /api/pdf_health?key=<KEY>      -> 200 & JSON render_ok==true   (PDF renderer)
  3. GET /api/otp/health               -> 200                           (OTP provider)

All three are HARD checks: any failure makes the overall verdict "red" and
sends a 'critical' alert (email + WhatsApp) via ops.alerts.

No check ever raises: a timeout / connection error / bad JSON is recorded as
ok:False with the cause in `detail`, so run_checks() always returns a verdict.
The process returns an exit code (0 = healthy, non-zero = unhealthy) so the
workflow's own status reflects site health.
"""
import json
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import quote

from ops import alerts, config


def _fetch(path):
    """GET config.TARGET_URL + path. Returns (status_code, body_text, error).

    Never raises. On an HTTP error status the body is still read (urllib raises
    HTTPError which is also a response). On a transport error status_code is 0
    and `error` holds the description.
    """
    url = config.TARGET_URL + path
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            body = resp.read().decode("utf-8", "replace")
            return status, body, None
    except urllib.error.HTTPError as e:
        # A non-2xx response — still a real response we can inspect.
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            body = ""
        return e.code, body, None
    except Exception as e:  # timeout, DNS, connection refused, decode, ...
        return 0, "", "%s: %s" % (type(e).__name__, e)


def _run_one(name, path, validate):
    """Run a single check, timing it. `validate(status, body)` returns
    (ok: bool, detail: str). Any exception in validate is swallowed."""
    start = time.monotonic()
    status, body, error = _fetch(path)
    latency_ms = int((time.monotonic() - start) * 1000)
    if error is not None:
        ok, detail = False, error
    else:
        try:
            ok, detail = validate(status, body)
        except Exception as e:
            ok, detail = False, "validate error: %s: %s" % (type(e).__name__, e)
    return {
        "name": name,
        "ok": bool(ok),
        "status_code": status,
        "detail": detail,
        "latency_ms": latency_ms,
    }


def _check_healthz_db(status, body):
    if status == 200:
        return True, "db write-durability ok"
    return False, "expected 200, got %s" % status


def _check_pdf_health(status, body):
    if status != 200:
        return False, "expected 200, got %s" % status
    try:
        data = json.loads(body)
    except Exception:
        return False, "200 but body was not JSON"
    if data.get("render_ok") is True:
        return True, "render_ok true"
    return False, "200 but render_ok != true: %r" % data.get("render_ok")


def _check_otp_health(status, body):
    if status == 200:
        return True, "otp provider ok"
    return False, "otp provider unhealthy (status %s)" % status


# Every deep check is a hard check: its failure turns the verdict red.
HARD_CHECKS = ("healthz_db", "pdf_health", "otp_health")


def run_checks() -> dict:
    """Run every deep health check and return a verdict.

    Returns {"overall": "green"|"red", "checks": [...], "failures": [names]}.
    overall is "red" iff any HARD check failed. Never raises.
    """
    key = quote(config.STATS_KEY, safe="")
    results = [
        _run_one("healthz_db", "/healthz/db", _check_healthz_db),
        _run_one("pdf_health", "/api/pdf_health?key=%s" % key, _check_pdf_health),
        _run_one("otp_health", "/api/otp/health", _check_otp_health),
    ]
    failures = [c["name"] for c in results if not c["ok"]]
    hard_failed = [c["name"] for c in results
                   if not c["ok"] and c["name"] in HARD_CHECKS]
    overall = "red" if hard_failed else "green"
    return {"overall": overall, "checks": results, "failures": failures}


def _summarize(report):
    """Human-readable one-liner per failure, for the alert body."""
    by_name = {c["name"]: c for c in report["checks"]}
    lines = []
    for name in report["failures"]:
        c = by_name.get(name, {})
        lines.append("- %s: status=%s %s (%sms)" % (
            name, c.get("status_code"), c.get("detail"), c.get("latency_ms")))
    return "Deep health check is RED against %s\n\n%s" % (
        config.TARGET_URL, "\n".join(lines) if lines else "(no detail)")


def main() -> int:
    report = run_checks()
    print(json.dumps(report, indent=2))
    if report["overall"] == "red":
        try:
            alerts.send_alert("Watcher: deep health check failed",
                              _summarize(report), "critical")
        except Exception as e:  # alerts already never-raise, but stay defensive
            print("alert dispatch failed: %s" % e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
