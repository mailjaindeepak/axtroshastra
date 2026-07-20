"""Astrology ACCURACY tests — verify the engine against an independent reference.

The golden-file tests (test_regression.py) snapshot our OWN output to catch
accidental drift. This suite is different: it checks CORRECTNESS against a trusted
third party (AstroSage) for well-known public figures.

For each celebrity we feed AstroSage's exact published birth details into
`compute_report` and assert the sign (rashi) of the ascendant and all nine grahas
matches AstroSage's chart.

Why compare signs only: any Lahiri-sidereal engine computes the same rashi for a
given birth moment, so signs are a robust cross-implementation check. Exact
degrees, house systems, and nakshatra spellings legitimately differ between tools,
so they are deliberately NOT compared (they'd cause false failures).

Data: tests/celebrity_charts.json — collected once from AstroSage celebrity
birth-chart pages. Each record carries the AstroSage `rating` for provenance.
"""
import json
import os

import pytest

import engine

_DATA = os.path.join(os.path.dirname(__file__), "celebrity_charts.json")
with open(_DATA, encoding="utf-8") as fh:
    CELEBS = json.load(fh)

# Engine reports signs in Sanskrit (Mesha, Vrishabha, ...); AstroSage uses English.
_SIGN_SANSKRIT_TO_EN = dict(zip(engine.SIGNS, engine.SIGNS_EN))


def _engine_signs(celeb):
    """Run the birth details through the engine, return {body: English sign}."""
    report = engine.compute_report(
        name=celeb["name"],
        dob=celeb["dob"],
        tob=celeb["tob"],
        tz_offset_hours=celeb["tz_offset_hours"],
        lat=celeb["lat"],
        lon_geo=celeb["lon"],
        female=False,          # gender affects narrative only, not chart positions
        time_quality="T0",
    )
    signs = {"Ascendant": _SIGN_SANSKRIT_TO_EN.get(
        report["chart"]["lagna"], report["chart"]["lagna"])}
    for planet, info in report["chart"]["planets"].items():
        signs[planet] = _SIGN_SANSKRIT_TO_EN.get(info["sign"], info["sign"])
    return signs


def test_fixture_is_non_trivial():
    """Guard against an empty/broken fixture silently making the suite pass."""
    assert len(CELEBS) >= 20, f"expected >= 20 reference charts, got {len(CELEBS)}"


@pytest.mark.parametrize("celeb", CELEBS, ids=[c["name"] for c in CELEBS])
def test_chart_signs_match_astrosage(celeb):
    ours = _engine_signs(celeb)
    mismatches = {
        body: (ours.get(body), expected_sign)
        for body, expected_sign in celeb["expected"].items()
        if ours.get(body) != expected_sign
    }
    assert not mismatches, (
        f"{celeb['name']} ({celeb.get('rating')}): engine disagrees with AstroSage on "
        + ", ".join(
            f"{body} [engine={got!r} astrosage={want!r}]"
            for body, (got, want) in mismatches.items()
        )
    )
