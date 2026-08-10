"""ops.mechanic — the responder must: parse the current EB version label, run a
Method-B rollback and report True/False, self-heal stuck payments over HTTP, and
NEVER raise even when subprocess / urllib blow up. It must ALWAYS alert.

(Flat filename on purpose: a tests/ops/ subdir would shadow the `ops` source
package on pytest's import path.)"""
import json
import subprocess
import urllib.error
import urllib.request

import ops.config as config
import ops.mechanic as mechanic


class _Proc:
    """Stand-in for subprocess.CompletedProcess."""
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _record_alerts(monkeypatch):
    """Replace mechanic.alerts.send_alert with a recorder; return the list."""
    calls = []
    monkeypatch.setattr(mechanic.alerts, "send_alert",
                        lambda subject, body, severity="warning":
                        calls.append((subject, body, severity)) or
                        {"email": True, "whatsapp": False})
    return calls


def _record_history(monkeypatch):
    """Replace mechanic.history.record_rollback with a recorder so nothing hits
    disk; return the list of (from_label, to_label, reason) tuples."""
    calls = []
    monkeypatch.setattr(mechanic.history, "record_rollback",
                        lambda from_label, to_label, reason="":
                        calls.append((from_label, to_label, reason)) or True)
    return calls


# --------------------------------------------------------------------------- #
# ROLLBACK
# --------------------------------------------------------------------------- #
def test_current_version_parses_label(monkeypatch):
    monkeypatch.setattr(config, "EB_ENV", "AxtroShastraProd")
    monkeypatch.setattr(config, "AWS_REGION", "ap-south-1")

    captured = {}

    def _fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return _Proc(returncode=0, stdout="app-2026-08-06-abc123\n")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    assert mechanic.current_version() == "app-2026-08-06-abc123"
    # correct EB env + region flow into the CLI args, no shell=True
    assert "AxtroShastraProd" in captured["cmd"]
    assert "ap-south-1" in captured["cmd"]
    assert captured["cmd"][0] == "aws"


def test_current_version_none_on_null_and_error(monkeypatch):
    # `--output text` prints literal "None" when the field is null
    monkeypatch.setattr(subprocess, "run",
                        lambda cmd, **kw: _Proc(returncode=0, stdout="None\n"))
    assert mechanic.current_version() is None

    # non-zero returncode -> None
    monkeypatch.setattr(subprocess, "run",
                        lambda cmd, **kw: _Proc(returncode=255, stderr="boom"))
    assert mechanic.current_version() is None


def test_current_version_never_raises(monkeypatch):
    def _boom(*a, **k):
        raise OSError("aws not installed")
    monkeypatch.setattr(subprocess, "run", _boom)
    assert mechanic.current_version() is None


def test_rollback_success_returns_true_and_alerts(monkeypatch):
    monkeypatch.setattr(config, "EB_ENV", "AxtroShastraProd")
    monkeypatch.setattr(config, "AWS_REGION", "ap-south-1")
    alert_calls = _record_alerts(monkeypatch)

    captured = {}

    def _fake_run(cmd, **kw):
        captured["cmd"] = cmd
        assert kw.get("shell") is not True  # never shell=True
        return _Proc(returncode=0, stdout='{"ok": true}')

    monkeypatch.setattr(subprocess, "run", _fake_run)
    assert mechanic.rollback("app-good-42") is True
    assert "app-good-42" in captured["cmd"]
    assert "update-environment" in captured["cmd"]
    # always alerts, at critical severity
    assert len(alert_calls) == 1
    assert alert_calls[0][2] == "critical"
    assert "app-good-42" in alert_calls[0][1]


def test_rollback_failure_returns_false_and_alerts(monkeypatch):
    alert_calls = _record_alerts(monkeypatch)
    monkeypatch.setattr(subprocess, "run",
                        lambda cmd, **kw: _Proc(returncode=1, stderr="access denied"))
    assert mechanic.rollback("app-good-42") is False
    assert len(alert_calls) == 1
    assert alert_calls[0][2] == "critical"
    assert "FAILED" in alert_calls[0][0]


def test_rollback_never_raises_when_subprocess_throws(monkeypatch):
    alert_calls = _record_alerts(monkeypatch)

    def _boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd="aws", timeout=60)
    monkeypatch.setattr(subprocess, "run", _boom)
    # must not raise, must return False, must still alert
    assert mechanic.rollback("app-good-42") is False
    assert len(alert_calls) == 1


# --------------------------------------------------------------------------- #
# AUTO-ROLLBACK  (armed/disarmed safety gate)
# --------------------------------------------------------------------------- #
def test_auto_rollback_disarmed_skips_and_records(monkeypatch):
    # DISARMED (the safe default): must NOT redeploy, but must alert + record.
    monkeypatch.setattr(config, "OPS_ROLLBACK_ARMED", False)
    alert_calls = _record_alerts(monkeypatch)
    hist_calls = _record_history(monkeypatch)

    # current_version() is allowed to run; give it a benign fake.
    monkeypatch.setattr(subprocess, "run",
                        lambda cmd, **kw: _Proc(returncode=0, stdout="app-live\n"))
    # If rollback were ever called it would also hit subprocess.run above, so
    # guard by asserting no update-environment happened via the recorded history.
    assert mechanic.auto_rollback_if_armed(reason="two failures") is False

    # alerted at warning, mentioning the disarmed skip
    assert len(alert_calls) == 1
    assert alert_calls[0][2] == "warning"
    assert "SKIPPED" in alert_calls[0][0]
    # recorded a skipped rollback in history
    assert len(hist_calls) == 1
    assert hist_calls[0][1] == "(skipped-disarmed)"
    assert hist_calls[0][2] == "two failures"


def test_auto_rollback_armed_rolls_back_and_records(monkeypatch):
    # ARMED: must redeploy the given last-good label and record from->to.
    monkeypatch.setattr(config, "OPS_ROLLBACK_ARMED", True)
    monkeypatch.setattr(config, "OPS_LAST_GOOD", "")
    monkeypatch.setattr(config, "EB_ENV", "AxtroShastraProd")
    monkeypatch.setattr(config, "AWS_REGION", "ap-south-1")
    alert_calls = _record_alerts(monkeypatch)
    hist_calls = _record_history(monkeypatch)

    seen = []

    def _fake_run(cmd, **kw):
        seen.append(cmd)
        # current_version() reads a label; update-environment just needs rc 0.
        return _Proc(returncode=0, stdout="app-current-bad\n")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    assert mechanic.auto_rollback_if_armed("app-good-7",
                                           reason="two failures") is True

    # an actual update-environment (rollback) was issued to the good label
    assert any("update-environment" in c and "app-good-7" in c for c in seen)
    # rollback fired its critical alert
    assert any(sev == "critical" for _, _, sev in alert_calls)
    # history recorded current(bad) -> target(good)
    assert len(hist_calls) == 1
    assert hist_calls[0][0] == "app-current-bad"
    assert hist_calls[0][1] == "app-good-7"


def test_auto_rollback_armed_no_target_aborts(monkeypatch):
    # ARMED but no label anywhere -> abort safely, alert critical, no rollback.
    monkeypatch.setattr(config, "OPS_ROLLBACK_ARMED", True)
    monkeypatch.setattr(config, "OPS_LAST_GOOD", "")
    alert_calls = _record_alerts(monkeypatch)
    hist_calls = _record_history(monkeypatch)

    def _boom(*a, **k):
        raise AssertionError("subprocess must not be called without a target")
    monkeypatch.setattr(subprocess, "run", _boom)

    assert mechanic.auto_rollback_if_armed(None, reason="two failures") is False
    assert len(alert_calls) == 1
    assert alert_calls[0][2] == "critical"
    assert hist_calls == []  # nothing rolled back, nothing recorded


def test_auto_rollback_uses_config_last_good_when_no_arg(monkeypatch):
    # ARMED, no arg, but OPS_LAST_GOOD is set -> that label is used.
    monkeypatch.setattr(config, "OPS_ROLLBACK_ARMED", True)
    monkeypatch.setattr(config, "OPS_LAST_GOOD", "app-config-good")
    monkeypatch.setattr(config, "EB_ENV", "AxtroShastraProd")
    monkeypatch.setattr(config, "AWS_REGION", "ap-south-1")
    _record_alerts(monkeypatch)
    hist_calls = _record_history(monkeypatch)

    monkeypatch.setattr(subprocess, "run",
                        lambda cmd, **kw: _Proc(returncode=0, stdout="app-now\n"))
    assert mechanic.auto_rollback_if_armed(reason="cfg") is True
    assert hist_calls[0][1] == "app-config-good"


# --------------------------------------------------------------------------- #
# REMEDIATE
# --------------------------------------------------------------------------- #
class _FakeResp:
    def __init__(self, payload):
        self._raw = json.dumps(payload).encode("utf-8")
    def read(self):
        return self._raw
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def test_remediate_stuck_payments_hits_reconcile(monkeypatch):
    monkeypatch.setattr(config, "TARGET_URL", "https://example.test")
    monkeypatch.setattr(config, "STATS_KEY", "sekret")
    alert_calls = _record_alerts(monkeypatch)

    captured = {}

    def _fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        return _FakeResp({"recovered": 3, "checked": 12})

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
    out = mechanic.remediate("stuck_payments")

    assert out["ok"] is True
    assert out["result"] == {"recovered": 3, "checked": 12}
    # hit the reconcile endpoint, as a POST, carrying the admin key
    assert "/api/reconcile" in captured["url"]
    assert "key=sekret" in captured["url"]
    assert captured["method"] == "POST"
    assert len(alert_calls) == 1


def test_remediate_unknown_kind_is_safe(monkeypatch):
    alert_calls = _record_alerts(monkeypatch)
    out = mechanic.remediate("does_not_exist")
    assert out["ok"] is False
    assert "unknown" in out["error"]
    assert len(alert_calls) == 1


def test_remediate_never_raises_when_urllib_throws(monkeypatch):
    monkeypatch.setattr(config, "TARGET_URL", "https://example.test")
    monkeypatch.setattr(config, "STATS_KEY", "sekret")
    alert_calls = _record_alerts(monkeypatch)

    def _boom(*a, **k):
        raise urllib.error.URLError("connection refused")
    monkeypatch.setattr(urllib.request, "urlopen", _boom)

    out = mechanic.remediate("stuck_payments")
    assert out["ok"] is False
    assert "error" in out
    assert len(alert_calls) == 1  # still alerted


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def test_cli_rollback_exit_codes(monkeypatch):
    monkeypatch.setattr(mechanic, "rollback", lambda label: label == "good")
    assert mechanic.main(["rollback", "--last-good", "good"]) == 0
    assert mechanic.main(["rollback", "--last-good", "bad"]) == 1


def test_cli_remediate_exit_codes(monkeypatch):
    monkeypatch.setattr(mechanic, "remediate",
                        lambda kind: {"ok": kind == "stuck_payments"})
    assert mechanic.main(["remediate", "--kind", "stuck_payments"]) == 0


def test_cli_auto_rollback_exit_zero_regardless(monkeypatch):
    # A disarmed skip is intended behaviour, so the CLI exits 0 whether the
    # underlying call rolled back (True) or safely skipped (False).
    seen = {}

    def _fake(last_good=None, reason=""):
        seen["last_good"] = last_good
        seen["reason"] = reason
        return False  # e.g. disarmed skip

    monkeypatch.setattr(mechanic, "auto_rollback_if_armed", _fake)
    assert mechanic.main(["auto-rollback", "--reason", "2 failures"]) == 0
    assert seen["reason"] == "2 failures"
    assert seen["last_good"] is None

    monkeypatch.setattr(mechanic, "auto_rollback_if_armed",
                        lambda last_good=None, reason="": True)
    assert mechanic.main(["auto-rollback", "--reason", "x",
                          "--last-good", "app-good"]) == 0
