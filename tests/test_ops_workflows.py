"""Structural tests for the ops GitHub Actions workflows.

These tests parse the YAML workflow files and verify invariants that the audit
found were violated — concurrency group alignment, always() on failure paths,
continue-on-error on setup steps, and comment accuracy.  They run as part of
the normal pytest suite so regressions are caught before push."""
import re
from pathlib import Path

import yaml
import pytest

_WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def _load(name):
    return yaml.safe_load((_WORKFLOWS / name).read_text())


# --------------------------------------------------------------------------- #
# Finding 1 — every deploy-capable workflow must share the same concurrency
#             group so they can never run in parallel.
# --------------------------------------------------------------------------- #
_DEPLOY_WORKFLOWS = ["ci.yml", "ops-deploy-guard.yml", "eb-rollback.yml"]


def test_all_deploy_workflows_share_concurrency_group():
    groups = set()
    for name in _DEPLOY_WORKFLOWS:
        wf = _load(name)
        for job_key, job in wf.get("jobs", {}).items():
            conc = job.get("concurrency") or wf.get("concurrency")
            if conc:
                g = conc if isinstance(conc, str) else conc.get("group")
                groups.add(g)
        top = wf.get("concurrency")
        if top:
            g = top if isinstance(top, str) else top.get("group")
            groups.add(g)
    assert len(groups) == 1, (
        f"deploy workflows use different concurrency groups: {groups}; "
        "all must be 'eb-deploy' to prevent parallel deploys"
    )
    assert "eb-deploy" in groups


# --------------------------------------------------------------------------- #
# Finding 2 — rollback / failure steps in deploy workflows must use always()
#             so they fire even when a prior step (like eb deploy) fails.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("wf_name", ["ci.yml", "ops-deploy-guard.yml"])
def test_rollback_step_uses_always(wf_name):
    wf = _load(wf_name)
    for job_key, job in wf.get("jobs", {}).items():
        for step in job.get("steps", []):
            name = step.get("name", "")
            if "roll back" in name.lower() or "rollback" in name.lower():
                cond = str(step.get("if", ""))
                assert "always()" in cond, (
                    f"{wf_name} job '{job_key}' step '{name}' has if: "
                    f"'{cond}' without always() — the step will be silently "
                    f"skipped when a prior step (like eb deploy) fails"
                )


# --------------------------------------------------------------------------- #
# Finding 3 — the monitor's "Install robot dependencies" step must use
#             continue-on-error so a npm/playwright install failure doesn't
#             silently skip all Phase C alert/recording steps.
# --------------------------------------------------------------------------- #
def test_monitor_robot_install_has_continue_on_error():
    wf = _load("ops-monitor.yml")
    for job_key, job in wf.get("jobs", {}).items():
        for step in job.get("steps", []):
            name = step.get("name", "")
            if "install robot" in name.lower():
                assert step.get("continue-on-error") is True, (
                    f"ops-monitor.yml step '{name}' must have "
                    f"continue-on-error: true so a npm/playwright install "
                    f"failure doesn't silently skip Phase C alerts"
                )


# --------------------------------------------------------------------------- #
# Finding 4 — the test count comment in ci.yml must stay in sync.
# --------------------------------------------------------------------------- #
def test_ci_comment_test_count_matches_architecture():
    ci_text = (_WORKFLOWS / "ci.yml").read_text()
    arch_text = (_WORKFLOWS.parents[1] / "ops" / "ARCHITECTURE.md").read_text()
    ci_counts = re.findall(r"pytest\s*\((\d+)\)", ci_text)
    arch_counts = re.findall(r"Pytest\*\*\s*\((\d+)\s+tests\)", arch_text)
    assert ci_counts, "could not find pytest count in ci.yml comment"
    assert arch_counts, "could not find pytest count in ARCHITECTURE.md"
    assert ci_counts[0] == arch_counts[0], (
        f"ci.yml says pytest({ci_counts[0]}) but ARCHITECTURE.md says "
        f"pytest({arch_counts[0]}); keep them in sync"
    )
