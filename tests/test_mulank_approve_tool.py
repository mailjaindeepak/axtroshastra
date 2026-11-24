"""The owner-approval tool records names and a date, refuses blanks and keys with no drafted text, and never touches the shipped ledger in tests."""
import importlib.util
import json
import os

import pytest

import mulank_content as mc

_P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "approve_mulank_content.py")


@pytest.fixture
def tool(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("approve_tool", _P)
    t = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(t)
    # Start from a ledger where every key is still pending review (the shipped ledger is fully approved), keeping the real key set.
    with open(t.LEDGER, encoding="utf-8") as f:
        shipped = json.load(f)
    pending = {"_about": "test copy: every key pending review", "entries": {k: {"status": mc.NEEDS_REVIEW} for k in shipped["entries"]}}
    copy = tmp_path / "mulank_registry.json"
    copy.write_text(json.dumps(pending), encoding="utf-8")
    monkeypatch.setattr(t, "LEDGER", str(copy))
    return t


def test_approving_writes_names_and_a_date_and_the_ledger_still_loads(tool):
    assert tool.main(["--editor", "Ed", "--approved-by", "Owner", "--date", "2026-11-10", "--keys", "M1", "PM1"]) == 0
    reg = mc.load_ledger(tool.LEDGER)
    assert mc.is_owner_approved(reg["M1"]) and mc.is_owner_approved(reg["PM1"]) and not mc.is_approved(reg["M2"])


def test_names_are_required_and_a_bad_key_is_refused(tool):
    with pytest.raises(SystemExit):
        tool.main(["--editor", " ", "--approved-by", "Owner", "--keys", "M1"])
    assert tool.main(["--editor", "Ed", "--approved-by", "Owner", "--keys", "M99"]) == 2
    assert not any(mc.is_approved(e) for e in mc.load_ledger(tool.LEDGER).values())


def test_dry_run_changes_nothing_and_all_approves_every_key_with_text(tool):
    assert tool.main(["--editor", "Ed", "--approved-by", "Owner", "--all", "--dry-run"]) == 0
    assert not any(mc.is_approved(e) for e in mc.load_ledger(tool.LEDGER).values())
    assert tool.main(["--editor", "Ed", "--approved-by", "Owner", "--date", "2026-11-10", "--all"]) == 0
    reg = mc.load_ledger(tool.LEDGER)
    assert all(mc.is_approved(e) for e in reg.values())
    for dob in ((29, 7, 1990), (15, 3, 1985), (22, 11, 2000), (9, 9, 1999), (4, 7, 1976)):
        assert mc.pair_readiness(*dob, today=mc._today(), registry=reg)["eligible"], dob
