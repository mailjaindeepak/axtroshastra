"""Structural tests for the ops GitHub Actions workflows.

These tests parse the YAML workflow files and verify invariants that the audit
found were violated — concurrency group alignment, always() on failure paths,
continue-on-error on setup steps, and comment accuracy.  They run as part of
the normal pytest suite so regressions are caught before push."""
import re
import sys
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


# --------------------------------------------------------------------------- #
# Guard — every third-party import used by test files must be declared in
#          requirements-dev.txt (or its -r includes) so CI doesn't break.
# --------------------------------------------------------------------------- #
_REPO = Path(__file__).resolve().parents[1]
_STDLIB = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else set()


def _third_party_imports(path):
    """Return top-level non-stdlib, non-local import names from a .py file."""
    found = set()
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith("import "):
            mod = line.split()[1].split(".")[0].split(",")[0]
            found.add(mod)
        elif line.startswith("from ") and "import" in line:
            mod = line.split()[1].split(".")[0]
            if mod == ".":
                continue
            found.add(mod)
    local = {p.stem for p in _REPO.glob("*.py")} | {
        p.name for p in _REPO.iterdir() if p.is_dir() and (p / "__init__.py").exists()
    } | {"tests"}
    return found - _STDLIB - local - {"__future__"}


def _declared_packages():
    """Package names declared across all requirements files CI installs."""
    declared = set()
    todo = [_REPO / "requirements-dev.txt"]
    seen = set()
    while todo:
        f = todo.pop()
        if f in seen or not f.exists():
            continue
        seen.add(f)
        for line in f.read_text().splitlines():
            line = line.split("#")[0].strip()
            if line.startswith("-r "):
                todo.append(f.parent / line[3:].strip())
                continue
            if not line or line.startswith("-"):
                continue
            name = re.split(r"[>=<!\[]", line)[0].strip().lower().replace("-", "_")
            declared.add(name)
    return declared


# Map PyPI package names to their importable module names when they differ
_IMPORT_TO_PACKAGE = {
    "yaml": "pyyaml",
    "cv2": "opencv_python",
    "PIL": "pillow",
    "bs4": "beautifulsoup4",
    "attr": "attrs",
    "dateutil": "python_dateutil",
    "dotenv": "python_dotenv",
    "mysql": "pymysql",
    "xhtml2pdf": "xhtml2pdf",
    "_pytest": "pytest",
}


def test_test_imports_declared_in_requirements():
    """Every third-party import in tests/ must appear in requirements-dev.txt."""
    if not _STDLIB:
        pytest.skip("sys.stdlib_module_names unavailable (Python < 3.10)")
    declared = _declared_packages()
    missing = {}
    for test_file in sorted((_REPO / "tests").glob("*.py")):
        for mod in _third_party_imports(test_file):
            pkg = _IMPORT_TO_PACKAGE.get(mod, mod).lower().replace("-", "_")
            if pkg not in declared:
                missing.setdefault(pkg, []).append(test_file.name)
    assert not missing, (
        "Test files import packages not in requirements-dev.txt: "
        + "; ".join(f"{pkg} (used by {', '.join(fs)})" for pkg, fs in missing.items())
    )
