"""Divisional charts, yogas, and ashtakavarga — determinism + classical invariants."""
from types import SimpleNamespace

import divisional as dv


def _graha(sign, lon=None, dignity="neutral"):
    return SimpleNamespace(sign=sign, lon=(sign * 30 + 5) if lon is None else lon,
                           dignity=dignity)


def _chart(signs, lagna_sign=0, lagna_lon=5.0, dignities=None):
    dignities = dignities or {}
    grahas = {name: _graha(signs[name], dignity=dignities.get(name, "neutral"))
              for name in signs}
    return {"grahas": grahas, "lagna_sign": lagna_sign, "lagna_lon": lagna_lon}


BASE_SIGNS = {"Sun": 0, "Moon": 1, "Mars": 2, "Mercury": 3, "Jupiter": 4,
              "Venus": 5, "Saturn": 6, "Rahu": 7, "Ketu": 1}


def test_navamsa_known_values():
    assert dv.navamsa_sign(0.0) == 0          # 0 Aries -> Aries (movable, 1st navamsa)
    assert dv.navamsa_sign(3.34) == 1         # Aries 3°20' -> Taurus
    assert dv.navamsa_sign(30.0) == 9         # 0 Taurus (fixed) -> Capricorn


def test_dasamsa_known_values():
    assert dv.dasamsa_sign(0.0) == 0          # odd sign Aries -> starts same sign
    assert dv.dasamsa_sign(30.0) == 9         # even sign Taurus -> starts 9th (Capricorn)


def test_bhinnashtakavarga_totals():
    expected = {"Sun": 48, "Moon": 49, "Mars": 39, "Mercury": 54,
                "Jupiter": 56, "Venus": 52, "Saturn": 39}
    chart = _chart(BASE_SIGNS)
    for planet, total in expected.items():
        assert sum(dv.bhinnashtakavarga(chart, planet)) == total, planet


def test_sarvashtakavarga_grand_total_is_337():
    chart = _chart(BASE_SIGNS)
    sav = dv.sarvashtakavarga(chart)
    assert len(sav) == 12
    assert sum(sav) == 337


def test_yoga_budha_aditya_detected():
    signs = dict(BASE_SIGNS, Sun=5, Mercury=5)   # Sun + Mercury same sign
    names = [y["name"] for y in dv.yogas(_chart(signs))]
    assert any("Budha-Aditya" in n for n in names)


def test_analyze_is_deterministic():
    chart = _chart(BASE_SIGNS)
    assert dv.analyze(chart) == dv.analyze(chart)
