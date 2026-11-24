"""Mulank eligibility: nothing sells until every key is verified by a named reviewer."""
from datetime import date

import pytest

import mulank_content as mc
import numerology

TODAY = date(2026, 11, 3)
V = mc.Entry(mc.VERIFIED, "Test Reviewer", "2026-11-03")


def _full_registry(day, month, year):
    res = numerology.compute_mulank(day, month, year, today=TODAY)
    return {k: V for k in mc.required_keys(res)}


def test_all_pairs_eligible_with_shipped_registry():
    """All 106 ledger entries were approved by the owner on 4 Nov 2026 and text exists for each, so every birthday is sellable."""
    pairs = set()
    for y in range(1900, 2026):
        for m in range(1, 13):
            for d in range(1, 29):
                r = mc.pair_readiness(d, m, y, today=TODAY)
                assert r["eligible"] is True and r["reason_code"] == "ok", (d, m, y, r["missing"])
                pairs.add(r["pair_key"])
    assert len(pairs) == 81


def test_empty_ledger_makes_every_pair_ineligible():
    for d, m, y in ((29, 7, 1990), (15, 3, 1985), (22, 11, 2000), (9, 9, 1999)):
        r = mc.pair_readiness(d, m, y, today=TODAY, registry={})
        assert r["eligible"] is False and r["reason_code"] == "content_not_approved"


def test_sample_ok_never_counts():
    reg = {k: mc.Entry(mc.SAMPLE_OK, "Someone", "2026-11-03")
           for k in mc.required_keys(numerology.compute_mulank(29, 7, 1990, today=TODAY))}
    assert mc.pair_readiness(29, 7, 1990, today=TODAY, registry=reg)["eligible"] is False


@pytest.mark.parametrize("by,on", [("", "2026-11-03"), ("Name", ""), ("  ", "x")])
def test_verified_needs_named_reviewer_and_date(by, on):
    reg = _full_registry(29, 7, 1990)
    reg["M2"] = mc.Entry(mc.VERIFIED, by, on)
    r = mc.pair_readiness(29, 7, 1990, today=TODAY, registry=reg)
    assert r["eligible"] is False and "M2" in r["missing"]


def test_fixture_with_every_key_verified_is_eligible():
    reg = _full_registry(29, 7, 1990)
    r = mc.pair_readiness(29, 7, 1990, today=TODAY, registry=reg)
    assert r["eligible"] is True and r["missing"] == [] and r["reason_code"] == "ok"


def test_each_missing_key_blocks():
    base = _full_registry(29, 7, 1990)
    for k in list(base):
        reg = {x: v for x, v in base.items() if x != k}
        r = mc.pair_readiness(29, 7, 1990, today=TODAY, registry=reg)
        assert r["eligible"] is False and r["missing"] == [k]


def test_ordered_pair_key_not_reversed():
    keys = mc.required_keys(numerology.compute_mulank(29, 7, 1990, today=TODAY))
    assert {"M2", "B1", "PM2", "PG1", "CB2", "LK2", "LK1"} <= set(keys) and "PS:2-1" not in keys
    assert "R:Moon>Sun" in keys and "R:Sun>Moon" in keys


def test_equal_planets_need_no_relation_cells():
    for y in range(1950, 2010):
        for m in range(1, 13):
            for d in range(1, 29):
                r = numerology.compute_mulank(d, m, y, today=TODAY)
                if r["mulank"]["number"] == r["bhagyank"]["number"]:
                    assert not [k for k in mc.required_keys(r) if k.startswith("R:")]
                    return
    pytest.fail("no equal-number DOB found")


def test_personal_years_required_and_rechecked_each_year():
    k_now = mc.required_keys(numerology.compute_mulank(29, 7, 1990, today=date(2026, 12, 31)))
    k_next = mc.required_keys(numerology.compute_mulank(29, 7, 1990, today=date(2027, 1, 1)))
    assert "Y1" in k_now and "Y2" in k_now
    assert k_now != k_next


def test_invalid_dob_raises():
    with pytest.raises(numerology.NumerologyInputError):
        mc.pair_readiness(31, 2, 1990, today=TODAY)


def test_no_verified_entry_without_reviewer_in_shipped_registry():
    for k, e in mc.REGISTRY.items():
        assert e.status in mc.STATUSES
        if e.status == mc.VERIFIED:
            assert e.reviewed_by.strip() and e.reviewed_on.strip(), k


def test_gap_log_line_has_no_pii():
    r = mc.pair_readiness(29, 7, 1990, today=TODAY)
    line = mc.gap_log_line(r)
    assert line.startswith("[mulank] ineligible pair=2-1 reason=") and " missing=" in line
    assert "1990" not in line and "29" not in line.split("missing=")[0]

# ------------------------------------------------------------------ expert verification vs owner approval vs completeness
PIN = date(2026, 11, 3)


def _entries(d, m, y, mk):
    E = numerology.compute_mulank(d, m, y, today=PIN)
    return {k: mk() for k in mc.required_keys(E)}


EXPERT = lambda: mc.Entry(mc.VERIFIED, "Expert Name", "2026-11-03")
OWNER = lambda: mc.Entry(mc.OWNER_APPROVED, editor="Editor Name", approved_by="Owner Name", approved_on="2026-11-03")


def test_owner_approval_needs_editor_approver_and_date():
    assert mc.is_owner_approved(OWNER()) and mc.is_approved(OWNER()) and not mc.is_expert_verified(OWNER())
    for blank in ("editor", "approved_by", "approved_on"):
        kw = dict(editor="E", approved_by="O", approved_on="2026-11-03")
        kw[blank] = "  "
        e = mc.Entry(mc.OWNER_APPROVED, **kw)
        assert not mc.is_approved(e), blank


def test_sample_needs_review_and_pending_never_count_even_with_names_filled_in():
    for st in (mc.SAMPLE_OK, mc.NEEDS_REVIEW, mc.PENDING):
        e = mc.Entry(st, "Expert", "2026-11-03", approved_by="Owner", approved_on="2026-11-03", editor="Editor")
        assert not mc.is_approved(e), st


def test_expert_owner_and_mixed_approval_are_reported_separately():
    for mk, basis in ((EXPERT, "expert"), (OWNER, "owner")):
        r = mc.pair_readiness(29, 7, 1990, today=PIN, registry=_entries(29, 7, 1990, mk))
        assert r["eligible"] and r["approved"] and r["approval_basis"] == basis and r["reason_code"] == "ok"
    reg = _entries(29, 7, 1990, EXPERT)
    reg["M2"] = OWNER()
    assert mc.pair_readiness(29, 7, 1990, today=PIN, registry=reg)["approval_basis"] == "mixed"


def test_approved_but_incomplete_is_never_sellable(monkeypatch):
    import mulank_bank as bank
    monkeypatch.setattr(mc, "REGISTRY", _entries(15, 3, 1985, OWNER))          # every key approved, but one block has no drafted text
    monkeypatch.delitem(bank.PM, 6)
    r = mc.pair_readiness(15, 3, 1985, today=PIN)
    assert r["approved"] is True and r["complete"] is False and r["eligible"] is False
    assert r["reason_code"] == "content_incomplete" and any(k.startswith("text:") for k in r["missing"])


def test_complete_but_not_approved_is_never_sellable():
    r = mc.pair_readiness(29, 7, 1990, today=PIN, registry={})                   # text exists for every pair, nothing approved
    assert r["complete"] is True and r["approved"] is False and r["eligible"] is False and r["reason_code"] == "content_not_approved"


def test_approved_and_complete_is_sellable_for_pair_2_1(monkeypatch):
    monkeypatch.setattr(mc, "REGISTRY", _entries(29, 7, 1990, OWNER))
    r = mc.pair_readiness(29, 7, 1990, today=PIN)
    assert r["eligible"] and r["complete"] and r["approval_basis"] == "owner" and r["missing"] == []


def test_sale_open_follows_eligibility_not_a_single_approval(monkeypatch):
    assert mc.sale_open(registry={}, today=PIN) is False                         # an empty ledger sells nothing
    assert mc.sale_open(today=PIN) is True                                       # the shipped ledger approves every key
    monkeypatch.setattr(mc, "REGISTRY", {"M2": OWNER()})
    assert mc.sale_open(today=PIN) is False                                      # one approved entry does not open sale
    monkeypatch.setattr(mc, "REGISTRY", _entries(29, 7, 1990, OWNER))
    assert mc.sale_open(today=PIN) is True


def test_relation_rule_nodes_and_conflict_use_the_approved_statement_4i():
    assert mc.relation_keys("Rahu", "Moon") == [] and mc.relation_keys("Sun", "Ketu") == []
    assert mc.relation_keys("Venus", "Mars") == [] and mc.relation_keys("Mars", "Venus") == []
    assert mc.relation_keys("Moon", "Sun") == ["R:Moon>Sun", "R:Sun>Moon"] and mc.relation_keys("Moon", "Moon") == []


def test_ledger_is_strict_and_the_shipped_one_approves_every_entry(tmp_path):
    import json
    bad = tmp_path / "x.json"
    bad.write_text(json.dumps({"entries": {"M2": {"status": "approved-ish"}}}))
    with pytest.raises(ValueError):
        mc.load_ledger(str(bad))
    bad.write_text(json.dumps({"entries": {"M10": {"status": "pending"}}}))
    with pytest.raises(ValueError):
        mc.load_ledger(str(bad))
    shipped = mc.load_ledger()
    assert shipped and all(mc.is_approved(e) and mc.has_text(k) for k, e in shipped.items())


def test_every_approved_ledger_entry_has_drafted_text():
    for k, e in mc.REGISTRY.items():
        if mc.is_approved(e):
            assert mc.has_text(k), k
