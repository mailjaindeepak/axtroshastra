"""Compatibility (Kundli Milan) ACCURACY against AstroSage.

The single-chart engine is already cross-checked (test_celebrity_accuracy,
test_birth_accuracy). This does the same for the 36-guna Ashtakoot MATCH: for 5
real couples we feed AstroSage's exact birth details into `compute_milan` and
assert every koota's points AND the /36 total match AstroSage's MatchMaking
report — the reference our users compare against.

Guna-milan koota tables vary between traditions; these fixtures pin our tables to
AstroSage's convention (Gana Manushya-Deva=5, Deva-Rakshasa=0; Vashya treats
Capricorn as Chatushpada). Data: tests/milan_accuracy.json.
"""
import json
import os

import pytest

import products

_DATA = os.path.join(os.path.dirname(__file__), "milan_accuracy.json")
with open(_DATA, encoding="utf-8") as fh:
    PAIRS = json.load(fh)


def test_fixture_is_non_trivial():
    assert len(PAIRS) >= 5, f"expected >= 5 reference couples, got {len(PAIRS)}"


@pytest.mark.parametrize("case", PAIRS, ids=[c["pair"] for c in PAIRS])
def test_milan_matches_astrosage(case):
    res = products.compute_milan(case["p1"], case["p2"])
    ours = {k["name"]: k["score"] for k in res["kootas"]}

    mismatches = {
        koota: (ours.get(koota), pts)
        for koota, pts in case["expected_kootas"].items()
        if ours.get(koota) != pts
    }
    assert not mismatches, (
        f"{case['pair']}: koota disagreement with AstroSage — "
        + ", ".join(f"{k} [ours={g} astrosage={w}]" for k, (g, w) in mismatches.items())
    )
    assert round(res["total"], 1) == case["expected_total"], (
        f"{case['pair']}: total {round(res['total'], 1)} != AstroSage {case['expected_total']}")
