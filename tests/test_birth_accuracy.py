"""Engine ACCURACY against AstroSage — our own max-entropy Indian birth cases.

Companion to test_celebrity_accuracy.py (public figures). These are hand-picked
births chosen to stress the engine: extreme geography (Leh 34N, Bhuj 69.7E),
edge times (23:50, 03:40, noon), and a spread of years — the kinds of inputs a
single reference set of celebrities may not cover.

For each birth we feed AstroSage's EXACT published inputs (its own geocoded
lat/lon and time) into the engine and assert the sidereal sign of the ascendant
AND all nine grahas (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu,
Ketu) from AstroSage's "Planetary Positions" table, plus the moon's nakshatra.
AstroSage defaults to the Lahiri ayanamsa — the same our engine uses — so these
must agree. The 5 seed births were verified 50/50 (10 bodies x 5) on 2026-08-06.

Data: tests/birth_accuracy.json. Grow it by pasting a report's Planetary
Positions signs (ASC + the nine grahas) + the moon's nakshatra.
"""
import json
import os

import pytest

import engine

_DATA = os.path.join(os.path.dirname(__file__), "birth_accuracy.json")
with open(_DATA, encoding="utf-8") as fh:
    BIRTHS = json.load(fh)

_S2E = dict(zip(engine.SIGNS, engine.SIGNS_EN))


def _sign(s):
    return _S2E.get(s, s)


def _engine_values(b):
    r = engine.compute_report(
        name="qa", dob=b["dob"], tob=b["tob"], tz_offset_hours=5.5,
        lat=b["lat"], lon_geo=b["lon"], female=False, time_quality="T0")
    ch = r["chart"]
    P = ch["planets"]
    out = {"Ascendant": _sign(ch["lagna"]), "Nakshatra": P["Moon"]["nakshatra"]}
    for body in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu"):
        out[body] = _sign(P[body]["sign"])
    # Ketu is always opposite Rahu; use the engine's own value when present.
    out["Ketu"] = (_sign(P["Ketu"]["sign"]) if "Ketu" in P
                   else engine.SIGNS_EN[(engine.SIGNS_EN.index(out["Rahu"]) + 6) % 12])
    return out


def test_fixture_is_non_trivial():
    assert len(BIRTHS) >= 5, f"expected >= 5 reference births, got {len(BIRTHS)}"


@pytest.mark.parametrize("b", BIRTHS, ids=[b["id"] for b in BIRTHS])
def test_engine_matches_astrosage(b):
    ours = _engine_values(b)
    mismatches = {
        field: (ours.get(field), want)
        for field, want in b["expected"].items()
        if ours.get(field) != want
    }
    assert not mismatches, (
        f"{b['id']} ({b['place']}): engine disagrees with AstroSage on "
        + ", ".join(f"{f} [engine={g!r} astrosage={w!r}]"
                    for f, (g, w) in mismatches.items())
    )
