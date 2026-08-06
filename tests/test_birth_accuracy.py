"""Engine ACCURACY against AstroSage — our own max-entropy Indian birth cases.

Companion to test_celebrity_accuracy.py (public figures). These are hand-picked
births chosen to stress the engine: extreme geography (Leh 34N, Bhuj 69.7E),
edge times (23:50, 03:40, noon), and a spread of years — the kinds of inputs a
single reference set of celebrities may not cover.

For each birth we feed AstroSage's EXACT published inputs (its own geocoded
lat/lon and time) into the engine and assert the four core Vedic values shown on
AstroSage's Avakhada Chakra: the ascendant sign (lagna), the moon sign (rashi),
the moon's nakshatra, and the (sidereal/Hindu) sun sign. AstroSage defaults to
the Lahiri ayanamsa — the same our engine uses — so these must agree.

Data: tests/birth_accuracy.json. Grow it by pasting the Avakhada values from any
AstroSage VedicReport (Lagna / Rasi / Nakshatra-Pada / SunSign Indian).
"""
import json
import os

import pytest

import engine

_DATA = os.path.join(os.path.dirname(__file__), "birth_accuracy.json")
with open(_DATA, encoding="utf-8") as fh:
    BIRTHS = json.load(fh)

_S2E = dict(zip(engine.SIGNS, engine.SIGNS_EN))


def _engine_values(b):
    r = engine.compute_report(
        name="qa", dob=b["dob"], tob=b["tob"], tz_offset_hours=5.5,
        lat=b["lat"], lon_geo=b["lon"], female=False, time_quality="T0")
    ch = r["chart"]
    moon = ch["planets"]["Moon"]
    return {
        "Ascendant": _S2E.get(ch["lagna"], ch["lagna"]),
        "Moon": _S2E.get(moon["sign"], moon["sign"]),
        "Nakshatra": moon["nakshatra"],
        "Sun": _S2E.get(ch["planets"]["Sun"]["sign"], ch["planets"]["Sun"]["sign"]),
    }


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
