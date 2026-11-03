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


def test_all_pairs_ineligible_with_shipped_registry():
    pairs = set()
    for y in range(1900, 2026):
        for m in range(1, 13):
            for d in range(1, 29):
                r = mc.pair_readiness(d, m, y, today=TODAY)
                assert r["eligible"] is False
                assert r["reason_code"] == "content_not_verified"
                pairs.add(r["pair_key"])
    assert len(pairs) == 81


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
    assert "PS:2-1" in keys and "PS:1-2" not in keys
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
    assert line.startswith("[mulank] ineligible pair=2-1 missing=")
    assert "1990" not in line and "29" not in line.split("missing=")[0]
