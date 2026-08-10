"""ops.mechanic — the RESPONDER. Runs only when the watcher (or a workflow)
has decided something is wrong, and tries to put it right, in order of blast
radius:

  1. REMEDIATE — the light touch. A stdlib-only HTTP nudge to the running app
     that fixes a known, self-contained fault (e.g. paid-but-undelivered reports
     stuck in the queue) WITHOUT redeploying anything. Cheap, reversible, tried
     first.
  2. ROLLBACK — the big hammer. Method B: redeploy the last-known-good version
     label on Elastic Beanstalk via the AWS CLI. Used when the deploy itself is
     bad and only shipping the previous artifact will recover the site.

Design rules (same as the rest of ops):
  * NEVER raises — a recovery tool that crashes is worse than useless; every
    entry point returns a value and swallows its own errors.
  * ALWAYS alerts — whatever it does (or fails to do) goes out through
    ops.alerts so a human sees it, because auto-recovery must be observable.
  * No new dependencies — subprocess + the AWS CLI for rollback, stdlib urllib
    for remediation. Nothing to pip-install in the workflow.
"""
import argparse
import json
import logging
import subprocess
import sys
import urllib.parse
import urllib.request

from ops import config, alerts, history

log = logging.getLogger("ops.mechanic")

# How long to wait on the AWS CLI before giving up (seconds).
_AWS_TIMEOUT = 60


# --------------------------------------------------------------------------- #
# 1) ROLLBACK  (Method B — redeploy last-good version on Elastic Beanstalk)
# --------------------------------------------------------------------------- #
def current_version():
    """Return the VersionLabel currently deployed to EB_ENV, or None.

    We record this BEFORE a rollback so the label can be stashed as the next
    "last good" once the site is healthy again. Never raises."""
    try:
        proc = subprocess.run(
            ["aws", "elasticbeanstalk", "describe-environments",
             "--environment-names", config.EB_ENV,
             "--region", config.AWS_REGION,
             "--query", "Environments[0].VersionLabel",
             "--output", "text"],
            capture_output=True, text=True, timeout=_AWS_TIMEOUT,
        )
    except Exception as e:
        log.error("current_version: aws CLI failed: %s", e)
        return None
    if proc.returncode != 0:
        log.error("current_version: aws returned %s: %s",
                  proc.returncode, (proc.stderr or "").strip())
        return None
    label = (proc.stdout or "").strip()
    # `--output text` prints the literal string "None" when the field is null.
    if not label or label == "None":
        return None
    return label


def rollback(last_good_label: str) -> bool:
    """Redeploy `last_good_label` to EB_ENV via `aws elasticbeanstalk
    update-environment`. Returns True on success (returncode 0). ALWAYS fires a
    critical alert with the outcome. Never raises."""
    ok = False
    detail = ""
    try:
        proc = subprocess.run(
            ["aws", "elasticbeanstalk", "update-environment",
             "--environment-name", config.EB_ENV,
             "--version-label", last_good_label,
             "--region", config.AWS_REGION],
            capture_output=True, text=True, timeout=_AWS_TIMEOUT,
        )
        ok = proc.returncode == 0
        detail = (proc.stdout if ok else proc.stderr) or ""
        detail = detail.strip()
    except Exception as e:
        detail = f"aws CLI raised: {e}"
        log.error("rollback: %s", detail)

    if ok:
        subject = f"Rollback triggered on {config.EB_ENV}"
        body = (f"Redeployed last-good version '{last_good_label}' to "
                f"{config.EB_ENV} ({config.AWS_REGION}).\n\n{detail}")
    else:
        subject = f"Rollback FAILED on {config.EB_ENV}"
        body = (f"Could NOT redeploy version '{last_good_label}' to "
                f"{config.EB_ENV} ({config.AWS_REGION}). Manual intervention "
                f"needed.\n\n{detail}")
    try:
        alerts.send_alert(subject, body, "critical")
    except Exception as e:  # alerts already swallow, but belt-and-braces
        log.error("rollback: alert failed: %s", e)
    return ok


# --------------------------------------------------------------------------- #
# 1b) AUTO-ROLLBACK  (armed/disarmed wrapper around rollback — the SAFETY gate)
# --------------------------------------------------------------------------- #
def auto_rollback_if_armed(last_good_label: str = None, reason: str = "") -> bool:
    """Roll back ONLY if auto-rollback is armed (config.OPS_ROLLBACK_ARMED).

    This is the gate the unattended robot-customer failure path calls. Because a
    blind auto-rollback on a *running* site (as opposed to a just-shipped bad
    deploy) is dangerous, it is DISARMED by default: when disarmed we log, alert,
    and record the skipped rollback in history, but do NOT touch the deployment.

    Returns True only when an actual rollback was performed and succeeded.
    ALWAYS records to history and alerts. Never raises."""
    # --- Disarmed: the safe default. Observe, don't act. ---
    if not config.OPS_ROLLBACK_ARMED:
        log.warning("auto_rollback_if_armed: DISARMED — skipping rollback (%s)",
                    reason)
        try:
            alerts.send_alert(
                "Auto-rollback SKIPPED (disarmed)",
                f"Auto-rollback is disarmed (OPS_ROLLBACK_ARMED != 1), so no "
                f"redeploy was attempted.\n\nReason: {reason}\n\n"
                f"Arm it by setting OPS_ROLLBACK_ARMED=1 once you trust the "
                f"robot to roll the site back on its own.",
                "warning")
        except Exception as e:
            log.error("auto_rollback_if_armed: alert failed: %s", e)
        try:
            history.record_rollback(from_label=current_version(),
                                    to_label="(skipped-disarmed)",
                                    reason=reason)
        except Exception as e:
            log.error("auto_rollback_if_armed: history failed: %s", e)
        return False

    # --- Armed: figure out where to roll back to. ---
    target = last_good_label or config.OPS_LAST_GOOD
    if not target:
        log.error("auto_rollback_if_armed: ARMED but no last-good label")
        try:
            alerts.send_alert(
                "Auto-rollback ABORTED (no last-good label)",
                "Auto-rollback is armed but no last-good version label was "
                "given (pass --last-good or set OPS_LAST_GOOD). Roll back "
                "manually in the EB console.\n\n"
                f"Reason: {reason}",
                "critical")
        except Exception as e:
            log.error("auto_rollback_if_armed: alert failed: %s", e)
        return False

    current = current_version()
    result = rollback(target)
    try:
        history.record_rollback(from_label=current, to_label=target,
                                reason=reason)
    except Exception as e:
        log.error("auto_rollback_if_armed: history failed: %s", e)
    return result


# --------------------------------------------------------------------------- #
# 2) REMEDIATE  (lightweight self-heal over HTTP — stdlib urllib only)
# --------------------------------------------------------------------------- #
def _post_json(path: str, params: dict) -> dict:
    """POST to `${TARGET_URL}{path}?<params>` and return parsed JSON.
    Raises on failure — callers wrap it."""
    qs = urllib.parse.urlencode(params)
    url = f"{config.TARGET_URL}{path}?{qs}"
    req = urllib.request.Request(url, data=b"", method="POST")
    with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT) as resp:
        raw = resp.read().decode("utf-8") or "{}"
    return json.loads(raw)


def _remediate_stuck_payments() -> dict:
    """Recover paid-but-undelivered reports by asking the app to run its
    deliver-capable reconcile sweep."""
    return _post_json("/api/reconcile", {"key": config.STATS_KEY})


# dispatch table — extend with new self-heal actions as they appear.
_REMEDIES = {
    "stuck_payments": _remediate_stuck_payments,
}


def remediate(kind: str) -> dict:
    """Run the self-heal action named `kind`. Returns a result dict:
    {"kind", "ok", "result"} on success or {"kind", "ok": False, "error"} on
    failure. ALWAYS alerts with what it did. Never raises."""
    fn = _REMEDIES.get(kind)
    if fn is None:
        out = {"kind": kind, "ok": False, "error": f"unknown remediation: {kind}"}
        try:
            alerts.send_alert(f"Remediation skipped: {kind}",
                              out["error"], "warning")
        except Exception as e:
            log.error("remediate: alert failed: %s", e)
        return out

    try:
        data = fn()
        out = {"kind": kind, "ok": True, "result": data}
        subject = f"Remediation ran: {kind}"
        body = f"Self-heal '{kind}' completed.\n\n{json.dumps(data, default=str)}"
        severity = "info"
    except Exception as e:
        out = {"kind": kind, "ok": False, "error": str(e)}
        subject = f"Remediation FAILED: {kind}"
        body = f"Self-heal '{kind}' raised: {e}"
        severity = "warning"
        log.error("remediate: %s failed: %s", kind, e)

    try:
        alerts.send_alert(subject, body, severity)
    except Exception as e:
        log.error("remediate: alert failed: %s", e)
    return out


# --------------------------------------------------------------------------- #
# CLI — so the GitHub Actions workflows can invoke the mechanic
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="ops.mechanic",
        description="The ops mechanic: rollback (Method B) or remediate.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_roll = sub.add_parser("rollback",
                            help="Redeploy the last-good EB version label.")
    p_roll.add_argument("--last-good", required=True, dest="last_good",
                        help="VersionLabel to redeploy.")

    p_auto = sub.add_parser(
        "auto-rollback",
        help="Roll back ONLY if armed (OPS_ROLLBACK_ARMED=1); else alert only.")
    p_auto.add_argument("--reason", default="", help="Why it was triggered.")
    p_auto.add_argument("--last-good", dest="last_good", default=None,
                        help="VersionLabel to redeploy (else OPS_LAST_GOOD).")

    p_rem = sub.add_parser("remediate", help="Run a lightweight self-heal.")
    p_rem.add_argument("--kind", required=True, choices=sorted(_REMEDIES),
                       help="Which remediation to run.")

    args = parser.parse_args(argv)

    if args.cmd == "rollback":
        return 0 if rollback(args.last_good) else 1
    if args.cmd == "auto-rollback":
        # Exit 0 whether it rolled back OR safely skipped (disarmed) — a skip is
        # the intended, non-error behaviour, so the workflow step stays green.
        auto_rollback_if_armed(args.last_good, args.reason)
        return 0
    if args.cmd == "remediate":
        return 0 if remediate(args.kind).get("ok") else 1
    return 1  # pragma: no cover — argparse enforces a subcommand


if __name__ == "__main__":
    sys.exit(main())
