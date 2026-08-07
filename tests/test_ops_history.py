"""ops.history — the append-only JSON-lines store the admin dashboard reads must:
record each of the three event kinds (run / rollback / alert) with a UTC
timestamp, read them back in order, tolerate a corrupt line, never raise when the
path is unwritable/missing, and expose a CLI that records each kind.

(Flat filename on purpose: a tests/ops/ subdir would shadow the `ops` source
package on pytest's import path — same reasoning as test_ops_mechanic.py.)"""
import json

import ops.config as config
import ops.history as history


def _point_at_tmp(monkeypatch, tmp_path):
    """Redirect the history store to a throwaway file under tmp_path."""
    p = tmp_path / "ops_history.jsonl"
    monkeypatch.setattr(config, "OPS_HISTORY_PATH", str(p))
    return p


# --------------------------------------------------------------------------- #
# Writers + readers
# --------------------------------------------------------------------------- #
def test_record_run_writes_timestamped_line(monkeypatch, tmp_path):
    p = _point_at_tmp(monkeypatch, tmp_path)
    assert history.record_run("pass", "all good", run_url="http://ci/1") is True

    lines = p.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    ev = json.loads(lines[0])
    assert ev["kind"] == "run"
    assert ev["status"] == "pass"
    assert ev["detail"] == "all good"
    assert ev["run_url"] == "http://ci/1"
    # UTC ISO-8601 timestamp with an offset
    assert ev["ts"].endswith("+00:00")


def test_record_rollback_and_alert(monkeypatch, tmp_path):
    _point_at_tmp(monkeypatch, tmp_path)
    assert history.record_rollback("app-bad", "app-good", "smoke failed") is True
    assert history.record_alert("critical", "Rollback triggered") is True

    roll = history.last_event(kind="rollback")
    assert roll["from"] == "app-bad"
    assert roll["to"] == "app-good"
    assert roll["reason"] == "smoke failed"

    alert = history.last_event(kind="alert")
    assert alert["severity"] == "critical"
    assert alert["subject"] == "Rollback triggered"


def test_read_events_order_filter_and_limit(monkeypatch, tmp_path):
    _point_at_tmp(monkeypatch, tmp_path)
    history.record_run("pass", "one")
    history.record_run("fail", "two")
    history.record_rollback("a", "b", "r")

    # oldest-first, all kinds
    allev = history.read_events()
    assert [e["kind"] for e in allev] == ["run", "run", "rollback"]

    # filter by kind
    runs = history.read_events(kind="run")
    assert len(runs) == 2 and all(e["kind"] == "run" for e in runs)

    # limit keeps the most recent
    last1 = history.read_events(limit=1)
    assert len(last1) == 1 and last1[0]["kind"] == "rollback"


def test_read_missing_file_returns_empty(monkeypatch, tmp_path):
    _point_at_tmp(monkeypatch, tmp_path)  # nothing written yet
    assert history.read_events() == []
    assert history.last_event() is None


def test_read_tolerates_corrupt_line(monkeypatch, tmp_path):
    p = _point_at_tmp(monkeypatch, tmp_path)
    history.record_run("pass", "good")
    # append a half-written / garbage line
    with open(p, "a", encoding="utf-8") as fh:
        fh.write("{not valid json\n")
    history.record_alert("info", "later")

    events = history.read_events()
    # the corrupt line is skipped, the two valid ones survive
    assert [e["kind"] for e in events] == ["run", "alert"]


def test_append_never_raises_on_bad_path(monkeypatch):
    # A directory path is not writable as a file -> must swallow, return False.
    monkeypatch.setattr(config, "OPS_HISTORY_PATH", "/")
    assert history.record_run("pass", "x") is False
    # readers on an unreadable path must also not raise
    assert history.read_events() == []


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def test_cli_record_run(monkeypatch, tmp_path):
    _point_at_tmp(monkeypatch, tmp_path)
    rc = history.main(["record-run", "--status", "fail",
                       "--detail", "boom", "--run-url", "http://ci/9"])
    assert rc == 0
    ev = history.last_event(kind="run")
    assert ev["status"] == "fail"
    assert ev["run_url"] == "http://ci/9"


def test_cli_record_rollback(monkeypatch, tmp_path):
    _point_at_tmp(monkeypatch, tmp_path)
    rc = history.main(["record-rollback", "--from", "v1", "--to", "v0",
                       "--reason", "bad deploy"])
    assert rc == 0
    ev = history.last_event(kind="rollback")
    assert ev["from"] == "v1" and ev["to"] == "v0" and ev["reason"] == "bad deploy"


def test_cli_record_alert(monkeypatch, tmp_path):
    _point_at_tmp(monkeypatch, tmp_path)
    rc = history.main(["record-alert", "--severity", "warning",
                       "--subject", "heads up"])
    assert rc == 0
    ev = history.last_event(kind="alert")
    assert ev["severity"] == "warning" and ev["subject"] == "heads up"
