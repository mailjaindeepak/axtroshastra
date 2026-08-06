"""Regression guards for two Ashtakoot accuracy bugs found via an AstroSage
Kundli Milan cross-check (tests/accuracy/milan_compatibility_accuracy_testset.json,
2026-08-06):

Bug 1 (Gana table): GANA_SCORE had a deliberately asymmetric variant that scored
Manushya(groom)-Deva(bride) as 6 and Deva(groom)-Rakshasa(bride) as 1. AstroSage
scores both pairings the same regardless of groom/bride direction (5 and 0
respectively) — confirmed on 3 independent real charts.

Bug 2 (Vashya split signs): VASHYA was keyed only by whole moon-sign, so every
Capricorn moon got the same group regardless of degree. Capricorn is a classical
split sign — verified against AstroSage that a moon at 5.7 deg into Capricorn
(front half) reads as Chatushpad, not the Jalachar the old fixed table always
returned.
"""
from cities_in import CITIES_IN
import products


def _person(name, dob, tob, city, gender):
    lat, lon, tz = CITIES_IN[city]
    return {"name": name, "dob": dob, "tob": tob, "gender": gender,
            "lat": lat, "lon": lon, "tz": tz}


def _koota(result, name):
    return next(k["score"] for k in result["kootas"] if k["name"] == name)


def test_gana_manushya_groom_deva_bride_scores_five():
    """Real pair: Vaibhav (Manushya gana) / Riya (Deva gana), Delhi/Delhi.
    AstroSage: Gana = 5. Previously we scored this 6."""
    boy = _person("Vaibhav", "1996-03-14", "09:15", "delhi", "male")
    girl = _person("Riya", "1997-11-02", "04:40", "delhi", "female")
    r = products.compute_milan(boy, girl)
    assert _koota(r, "Gana") == 5
    assert r["total"] == 14.5


def test_gana_deva_groom_rakshasa_bride_scores_zero():
    """Real pair: Rishi (Deva gana) / Dimple (Rakshasa gana), Jaipur/Ahmedabad.
    AstroSage: Gana = 0. Previously we scored this 1."""
    boy = _person("Rishi", "1994-05-21", "12:00", "jaipur", "male")
    girl = _person("Dimple", "1995-09-08", "12:00", "ahmedabad", "female")
    r = products.compute_milan(boy, girl)
    assert _koota(r, "Gana") == 0
    assert r["total"] == 8.5


def test_vashya_capricorn_front_half_is_chatushpad_not_jalachar():
    """Real pair: Golu (moon 5.7 deg into Capricorn) / Pooja, Kolkata/Mumbai.
    AstroSage: Golu's Vashya = Chatushpad, giving Vashya koota score 1 against
    Pooja's Manav. Previously the fixed per-sign table always read Capricorn as
    Jalachar, scoring 0.5 instead."""
    boy = _person("Golu", "1999-06-30", "23:55", "kolkata", "male")
    girl = _person("Pooja", "2000-01-01", "00:10", "mumbai", "female")
    r = products.compute_milan(boy, girl)
    assert _koota(r, "Vashya") == 1
    assert r["total"] == 22.5


def test_vashya_group_helper_splits_capricorn_and_sagittarius_by_degree():
    assert products._vashya_group(9, 5.0) == "Q"     # Capricorn front half
    assert products._vashya_group(9, 25.0) == "J"    # Capricorn back half
    assert products._vashya_group(8, 5.0) == "M"     # Sagittarius front half
    assert products._vashya_group(8, 25.0) == "Q"    # Sagittarius back half
    # non-split signs are unaffected by degree
    assert products._vashya_group(0, 5.0) == products._vashya_group(0, 25.0) == "Q"
