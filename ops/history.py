"""ops.history — an append-only history store for the ops framework.

The future admin dashboard reads this to show "what did the bots do, and when".
It records three kinds of events, each stamped with a UTC ISO-8601 timestamp:

  * run      — a robot-customer run  (pass/fail + detail + optional run_url)
  * rollback — a Method-B rollback   (from-version -> to-version + reason)
  * alert    — an alert that fired   (severity + subject)

Design rules (same as the rest of ops):
  * NEVER raises — a bookkeeping helper that crashes must never take down the
    caller (the mechanic, a workflow step). Every entry point swallows its own
    errors and returns instead of propagating.
  * Stdlib only — the store is a JSON-lines file at config.OPS_HISTORY_PATH.
    One JSON object per line, appended; no database, no S3, no dependencies.

CLI (so the GitHub Actions workflows can record events):
  python -m ops.history record-run --status pass|fail --detail "..." [--run-url ...]
  python -m ops.history record-rollback --from X --to Y --reason "..."
  python -m ops.history record-alert --severity S --subject "..."
"""
import argparse
import json
import logging
import sys
from datetime import datetime, timezone

from ops import config

log = logging.getLogger("ops.history")


def _now():
    """Current time as a UTC ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _append(event: dict) -> bool:
    """Append one event dict as a JSON line to the history file. Never raises;
    returns True on success, False if the write failed."""
    try:
        line = json.dumps(event, default=str)
        with open(config.OPS_HISTORY_PATH, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        return True
    except Exception as e:
        log.error("history: could not append %s: %s", event.get("kind"), e)
        return False


# --------------------------------------------------------------------------- #
# Writers
# --------------------------------------------------------------------------- #
def record_run(status: str, detail: str, run_url: str = None) -> bool:
    """Record a robot-customer run. status is typically 'pass' or 'fail'."""
    return _append({
        "kind": "run",
        "ts": _now(),
        "status": status,
        "detail": detail,
        "run_url": run_url,
    })


def record_rollback(from_label, to_label, reason: str = "") -> bool:
    """Record a rollback from `from_label` to `to_label` with a reason."""
    return _append({
        "kind": "rollback",
        "ts": _now(),
        "from": from_label,
        "to": to_label,
        "reason": reason,
    })


def record_alert(severity: str, subject: str) -> bool:
    """Record that an alert fired (severity in {info, warning, critical})."""
    return _append({
        "kind": "alert",
        "ts": _now(),
        "severity": severity,
        "subject": subject,
    })


# --------------------------------------------------------------------------- #
# Readers (for the admin dashboard)
# --------------------------------------------------------------------------- #
def read_events(limit: int = None, kind: str = None) -> list:
    """Return recorded events oldest-first (dashboards can reverse as needed).
    Optionally filter by `kind` and cap to the most recent `limit`. Never raises;
    returns [] if the store is missing or unreadable. Malformed lines are
    skipped rather than fatal."""
    events = []
    try:
        with open(config.OPS_HISTORY_PATH, "r", encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    ev = json.loads(raw)
                except Exception:
                    continue  # tolerate a partially-written / corrupt line
                if kind is not None and ev.get("kind") != kind:
                    continue
                events.append(ev)
    except FileNotFoundError:
        return []
    except Exception as e:
        log.error("history: could not read %s: %s", config.OPS_HISTORY_PATH, e)
        return events
    if limit is not None and limit >= 0:
        events = events[-limit:]
    return events


def last_event(kind: str = None):
    """Return the most recent event (optionally of a given kind), or None."""
    events = read_events(kind=kind)
    return events[-1] if events else None


# --------------------------------------------------------------------------- #
# CLI — so the GitHub Actions workflows can record events
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="ops.history",
        description="Append-only ops history store (JSON-lines).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("record-run", help="Record a robot-customer run.")
    p_run.add_argument("--status", required=True, choices=["pass", "fail"],
                       help="Run outcome.")
    p_run.add_argument("--detail", required=True, help="Human-readable detail.")
    p_run.add_argument("--run-url", dest="run_url", default=None,
                       help="Link to the CI run.")

    p_roll = sub.add_parser("record-rollback", help="Record a rollback.")
    p_roll.add_argument("--from", required=True, dest="from_label",
                        help="Version rolled back FROM.")
    p_roll.add_argument("--to", required=True, dest="to_label",
                        help="Version rolled back TO.")
    p_roll.add_argument("--reason", default="", help="Why it happened.")

    p_alert = sub.add_parser("record-alert", help="Record that an alert fired.")
    p_alert.add_argument("--severity", required=True,
                         help="info | warning | critical.")
    p_alert.add_argument("--subject", required=True, help="Alert subject.")

    args = parser.parse_args(argv)

    if args.cmd == "record-run":
        return 0 if record_run(args.status, args.detail, args.run_url) else 1
    if args.cmd == "record-rollback":
        return 0 if record_rollback(args.from_label, args.to_label,
                                    args.reason) else 1
    if args.cmd == "record-alert":
        return 0 if record_alert(args.severity, args.subject) else 1
    return 1  # pragma: no cover — argparse enforces a subcommand


if __name__ == "__main__":
    sys.exit(main())
