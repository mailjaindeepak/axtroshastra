"""DEMO_MODE must never be on in production.

DEMO_MODE=1 registers /api/_demo_pay/{id} (unlock any report for free) and makes auth.py return the login code in the API response. These tests prove
that on anything that looks like production the app switches it off by itself, and that on a private local machine it still works as before.
The last tests start the real app in a fresh process, as a production server would, instead of only calling the helper."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import demo_guard

ROOT = Path(__file__).resolve().parent.parent
NO_EB = lambda p: False


# ------------------------------------------------------------------ what counts as "not a private local machine"
@pytest.mark.parametrize("env", [
    {},
    {"DB_HOST": "127.0.0.1", "DB_PORT": "3307"},
    {"DB_HOST": "localhost", "PUBLIC_BASE_URL": "http://localhost:8000"},
    {"PUBLIC_BASE_URL": "http://127.0.0.1:8000", "RAZORPAY_KEY_ID": "rzp_test_abc123"},
    {"APP_ENV": "development", "ENVIRONMENT": "dev"},
])
def test_a_private_local_machine_is_allowed(env):
    assert demo_guard.blockers(env, NO_EB) == []
    assert demo_guard.enforce(True, dict(env), NO_EB) is True


@pytest.mark.parametrize("env,fragment", [
    ({"RAZORPAY_KEY_ID": "rzp_live_abc123"}, "live Razorpay key"),
    ({"PUBLIC_BASE_URL": "https://www.axtroshastra.com"}, "axtroshastra.com"),
    ({"PUBLIC_BASE_URL": "https://axtroshastra.in/"}, "axtroshastra.in"),
    ({"PUBLIC_BASE_URL": "https://abc123.ngrok.app"}, "ngrok"),
    ({"PUBLIC_BASE_URL": "www.axtroshastra.com"}, "axtroshastra.com"),                  # no scheme still parses
    ({"DB_HOST": "axtro.abc123.ap-south-1.rds.amazonaws.com"}, "database host"),
    ({"DB_HOST": "10.0.3.7"}, "database host"),
    ({"APP_ENV": "production"}, "APP_ENV"),
    ({"ENVIRONMENT": "Prod"}, "ENVIRONMENT"),
])
def test_every_production_signal_blocks_demo_mode(env, fragment):
    reasons = demo_guard.blockers(env, NO_EB)
    assert reasons and any(fragment in r for r in reasons), reasons
    env2 = dict(env, DEMO_MODE="1")
    assert demo_guard.enforce(True, env2, NO_EB) is False
    assert "DEMO_MODE" not in env2                       # removed, because auth.py reads the variable on its own


def test_elastic_beanstalk_blocks_demo_mode():
    for marker in ("/opt/elasticbeanstalk", "/var/app/current"):
        exists = lambda p, m=marker: p == m
        assert any("Elastic Beanstalk" in r for r in demo_guard.blockers({}, exists))
        assert demo_guard.enforce(True, {"DEMO_MODE": "1"}, exists) is False


def test_demo_mode_that_was_never_requested_stays_off_and_touches_nothing():
    env = {"RAZORPAY_KEY_ID": "rzp_live_x"}
    assert demo_guard.enforce(False, env, NO_EB) is False and env == {"RAZORPAY_KEY_ID": "rzp_live_x"}


def test_the_guard_logs_a_critical_line_naming_the_reason(caplog):
    with caplog.at_level("CRITICAL", logger="axtroshastra"):
        demo_guard.enforce(True, {"RAZORPAY_KEY_ID": "rzp_live_x", "DEMO_MODE": "1"}, NO_EB)
    assert any(r.levelname == "CRITICAL" and "IGNORED" in r.getMessage() and "live Razorpay key" in r.getMessage() for r in caplog.records)


def test_the_guard_never_logs_a_secret(caplog):
    with caplog.at_level("CRITICAL", logger="axtroshastra"):
        demo_guard.enforce(True, {"RAZORPAY_KEY_ID": "rzp_live_SUPERSECRETVALUE", "DB_HOST": "db.internal.example", "DEMO_MODE": "1"}, NO_EB)
    assert "SUPERSECRETVALUE" not in caplog.text


# ------------------------------------------------------------------ the real app, started the way a server starts it
PROBE = r"""
import json, os
import api, auth
from fastapi.testclient import TestClient
c = TestClient(api.app)
routes = sorted(r.path for r in api.app.routes if "_demo_pay" in getattr(r, "path", ""))
print("RESULT " + json.dumps({"demo_mode": api.DEMO_MODE, "env": os.environ.get("DEMO_MODE"), "auth": auth._demo_mode(), "routes": routes,
                              "demo_pay_status": c.post("/api/_demo_pay/anything").status_code}))
"""


def _probe(extra_env):
    env = dict(os.environ)
    for k in ("DEMO_MODE", "RAZORPAY_KEY_ID", "PUBLIC_BASE_URL", "APP_ENV", "ENVIRONMENT", "ENV", "STAGE"):
        env.pop(k, None)
    env.update(extra_env)
    out = subprocess.run([sys.executable, "-c", PROBE], cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
    lines = [l for l in out.stdout.splitlines() if l.startswith("RESULT ")]
    assert lines, f"probe did not run:\n{out.stdout[-800:]}\n{out.stderr[-1500:]}"
    return json.loads(lines[-1][7:]), out.stderr


@pytest.mark.parametrize("prod_env", [
    {"RAZORPAY_KEY_ID": "rzp_live_test123"},
    {"PUBLIC_BASE_URL": "https://www.axtroshastra.com"},
    {"APP_ENV": "production"},
], ids=["live-key", "public-url", "app-env"])
def test_a_production_looking_server_started_with_demo_mode_has_no_free_unlock_and_no_login_code_echo(prod_env):
    result, stderr = _probe({"DEMO_MODE": "1", **prod_env})
    assert result["demo_mode"] is False and result["env"] is None and result["auth"] is False
    assert result["routes"] == [] and result["demo_pay_status"] in (404, 405)            # the free-unlock route does not exist
    assert "IGNORED" in stderr or "DEMO_MODE" in stderr                                    # and the mistake was logged loudly


def test_the_same_server_on_a_private_machine_still_has_demo_mode():
    result, _ = _probe({"DEMO_MODE": "1"})
    assert result["demo_mode"] is True and result["auth"] is True and result["routes"] == ["/api/_demo_pay/{rid}"]
