"""Annual-report engine additions: sign_change_dates, doshas, sade_sati_stages,
saturn_house_timeline. Engine only (no api import, no DB): run with
  DB_BACKEND=sqlite pytest --noconftest tests/test_engine_annual.py
(tests/conftest.py imports api, which needs MySQL / would reach prod RDS.)
"""
import random
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
import swisseph as swe

import engine

IST = engine.IST
START, END = datetime(2026, 11, 6), datetime(2027, 11, 30)


def _cross(planet, s=START, e=END):
    return engine.sign_change_dates(planet, s, e)


def _near(c, y, mo, d, h, mi, minutes=5):
    want = datetime(y, mo, d, h, mi, tzinfo=IST)
    assert abs(c["at"] - want) <= timedelta(minutes=minutes), (c["at"], want)


# ------------------------------------------------------------ (a) expected values
def test_nodes_change_sign_2026_12_05_ist():
    rahu, ketu = _cross("Rahu"), _cross("Ketu")
    assert len(rahu) == len(ketu) == 1
    _near(rahu[0], 2026, 12, 5, 22, 32)
    assert rahu[0]["date"] == ketu[0]["date"] == "2026-12-05"
    assert (rahu[0]["from_name"], rahu[0]["to_name"]) == ("Aquarius", "Capricorn")
    assert (ketu[0]["from_name"], ketu[0]["to_name"]) == ("Leo", "Cancer")


def test_jupiter_crossings_incl_retrograde_reentry():
    j = _cross("Jupiter")
    assert [(c["from_name"], c["to_name"]) for c in j] == [
        ("Leo", "Cancer"), ("Cancer", "Leo"), ("Leo", "Virgo")]
    _near(j[0], 2027, 1, 25, 1, 32)
    assert j[1]["date"] == "2027-06-26"
    _near(j[2], 2027, 11, 26, 18, 45)


def test_saturn_crossings():
    s = _cross("Saturn")
    assert [(c["from_name"], c["to_name"]) for c in s] == [("Pisces", "Aries"), ("Aries", "Pisces")]
    _near(s[0], 2027, 6, 3, 5, 28)
    _near(s[1], 2027, 10, 20, 7, 12)
    assert [c["date"] for c in s] == ["2027-06-03", "2027-10-20"]


def _chart(y, mo, d, h, mi, lat, lon):
    utc = datetime(y, mo, d, h, mi) - timedelta(hours=5.5)
    return engine.compute_chart(utc, lat, lon)


A = _chart(2005, 6, 14, 12, 0, 28.61, 77.21)   # birth time unknown: noon
B = _chart(1996, 10, 19, 12, 30, 18.52, 73.86)


@pytest.mark.parametrize("chart,moon", [(A, "Leo"), (B, "Sagittarius")])
def test_personas_dhaiya_and_no_other_doshas(chart, moon):
    assert engine.SIGNS_EN[chart["grahas"]["Moon"].sign] == moon
    d = engine.doshas(chart, as_of=START)
    assert d["kaal_sarp"] is False and d["pitra"] is False
    assert d["shani_dhaiya"]["active"] is True
    assert d["shani_dhaiya"]["saturn_sign_name"] == "Pisces"
    assert d["shani_dhaiya"]["kind"] == ("8th" if moon == "Leo" else "4th")


@pytest.mark.parametrize("chart", [A, B])
def test_persona_dhaiya_windows_exact(chart):
    tl = engine.saturn_house_timeline(chart["grahas"]["Moon"].sign, START, END)
    kind = 8 if chart is A else 4
    assert tl["start_house"] == kind
    assert [c["date"] for c in tl["changes"]] == ["2027-06-03", "2027-10-20"]
    assert tl["changes"][1]["house"] == kind


def test_persona_b_no_sade_sati_in_window():
    r = engine.sade_sati_stages(B["grahas"]["Moon"].sign, START, END)
    assert r["stage_at_start"] == "none" and r["changes"] == [] and r["next_start"]


# ------------------------------------------------------------ (b) doshas branches
SEVEN = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")


def fake(lons, rahu=0.0, moon_sign=None, sun=None):
    g = {p: SimpleNamespace(lon=l, sign=int(l // 30)) for p, l in zip(SEVEN, lons)}
    if sun is not None:
        g["Sun"] = SimpleNamespace(lon=sun, sign=int(sun // 30))
    g["Rahu"] = SimpleNamespace(lon=rahu, sign=int(rahu // 30))
    if moon_sign is not None:
        g["Moon"] = SimpleNamespace(lon=moon_sign * 30 + 5.0, sign=moon_sign)
    return {"grahas": g}


def test_kaal_sarp_branches():
    assert engine.doshas(fake([10, 20, 30, 40, 50, 60, 70]), as_of=START)["kaal_sarp"] is True
    d = engine.doshas(fake([190, 200, 210, 220, 230, 240, 250]), as_of=START)
    assert d["kaal_sarp"] is True and d["kaal_sarp_detail"]["side"] == "ketu_to_rahu"
    d = engine.doshas(fake([10, 20, 30, 40, 50, 60, 200]), as_of=START)   # one across
    assert d["kaal_sarp"] is False and d["kaal_sarp_detail"]["side"] is None
    assert engine.doshas(fake([0, 20, 30, 40, 50, 60, 70]), as_of=START)["kaal_sarp"] is False  # conjunct Rahu


def test_pitra_branches():
    assert engine.doshas(fake([10, 20, 30, 40, 50, 60, 70], rahu=5.0), as_of=START)["pitra"] is True
    assert engine.doshas(fake([10, 20, 30, 40, 50, 60, 70], rahu=95.0), as_of=START)["pitra"] is False


@pytest.mark.parametrize("moon,kind", [(8, "4th"), (4, "8th"), (0, None)])
def test_dhaiya_branches(moon, kind):
    # as_of 2026-11-06: Saturn in Pisces (index 11)
    d = engine.doshas(fake([10] * 7, moon_sign=moon), as_of=START)["shani_dhaiya"]
    assert d["kind"] == kind and d["active"] is (kind is not None)
    assert d["saturn_sign"] == 11


def test_dhaiya_uses_current_not_natal_saturn():
    # natal Saturn in Cancer = 4th from Aries Moon, but Saturn NOW is Pisces (12th): false
    c = fake([10, 20, 30, 40, 50, 60, 100], moon_sign=0)
    assert c["grahas"]["Saturn"].sign == 3
    assert engine.doshas(c, as_of=START)["shani_dhaiya"]["active"] is False


# ------------------------------------------------------------ (c) sade sati stages
def test_sade_sati_aries_moon_stages():
    r = engine.sade_sati_stages(0, START, END)
    assert r["stage_at_start"] == "first" and r["active_at_start"] and r["next_start"] is None
    assert [(c["date"], c["stage"]) for c in r["changes"]] == [
        ("2027-06-03", "second"), ("2027-10-20", "first")]


def test_sade_sati_inactive_moon_has_next_start():
    r = engine.sade_sati_stages(4, START, END)   # Leo Moon: Saturn Pisces is 8th
    assert r["stage_at_start"] == "none" and r["changes"] == []
    assert r["next_start"] and r["next_start"] > "2030"


def test_sade_sati_third_stage_and_exit():
    r = engine.sade_sati_stages(10, START, datetime(2030, 1, 1))   # Aquarius Moon: Saturn Pisces = 2nd
    assert r["stage_at_start"] == "third"
    assert (r["changes"][0]["date"], r["changes"][0]["stage"]) == ("2027-06-03", "none")


# ------------------------------------------------------------ (d) SECOND-METHOD cross-check
def test_second_method_cross_check_NOT_outside_reference_50_charts():
    """SECOND-METHOD cross-check, NOT an outside reference (AstroSage etc. come later).
    Independent path: direct swe calls with FLG_MOSEPH, hourly sampling + linear
    interpolation, vs the engine's bisection; classifications from raw longitudes."""
    rnd = random.Random(20261106)
    flags = swe.FLG_MOSEPH | swe.FLG_SIDEREAL
    ids = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY,
           "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE}

    def lons(utc):
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        j = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute / 60)
        L = {k: swe.calc_ut(j, v, flags)[0][0] % 360 for k, v in ids.items()}
        L["Ketu"] = (L["Rahu"] + 180) % 360
        return L

    import math
    n_cross = 0
    for _ in range(50):
        y, mo, d = rnd.randint(1960, 2010), rnd.randint(1, 12), rnd.randint(1, 28)
        lat, lon = rnd.uniform(8, 34), rnd.uniform(68, 96)
        birth = datetime(y, mo, d, rnd.randint(0, 23), rnd.randint(0, 59))
        chart = engine.compute_chart(birth - timedelta(hours=5.5), lat, lon)
        # --- classification
        as_of = datetime(rnd.randint(2025, 2035), rnd.randint(1, 12), 15, 12, 0)
        L = lons(birth - timedelta(hours=5.5))
        s = [math.sin(math.radians(L[p] - L["Rahu"])) for p in SEVEN]
        ks = all(x > 1e-9 for x in s) or all(x < -1e-9 for x in s)
        pitra = int(L["Sun"] // 30) == int(L["Rahu"] // 30)
        sat_now = int(lons(as_of - timedelta(hours=5.5))["Saturn"] // 30)
        h = (sat_now - int(L["Moon"] // 30)) % 12 + 1
        d_ = engine.doshas(chart, as_of=as_of)
        assert d_["kaal_sarp"] == ks and d_["pitra"] == pitra
        assert d_["shani_dhaiya"]["active"] == (h in (4, 8))
        # --- sign changes over a 12-month window
        ws = datetime(rnd.randint(2020, 2035), rnd.randint(1, 12), 1)
        we = ws + timedelta(days=365)
        for planet in ("Saturn", "Jupiter", "Rahu"):
            mine = engine.sign_change_dates(planet, ws, we)
            ref, t = [], ws - timedelta(hours=5.5)
            prev = lons(t)[planet]
            while t < we - timedelta(hours=5.5):
                t2 = t + timedelta(hours=1)
                cur = lons(t2)[planet]
                if int(prev // 30) != int(cur // 30):
                    # unwrap across 360/0 so interpolation is linear
                    b = 30 * (int(cur // 30) if (cur - prev) % 360 < 180 else int(prev // 30))
                    b = b % 360
                    p2 = prev if abs(prev - b) < 180 else prev - 360 * (1 if prev > b else -1)
                    c2 = cur if abs(cur - b) < 180 else cur - 360 * (1 if cur > b else -1)
                    ref.append((t + (t2 - t) * ((b - p2) / (c2 - p2))).replace(tzinfo=timezone.utc))
                t, prev = t2, cur
            assert len(mine) == len(ref), (planet, ws, mine, ref)
            for m, r in zip(mine, ref):
                assert abs(m["at"] - r) <= timedelta(minutes=30), (planet, m["at"], r)
            n_cross += len(mine)
    assert n_cross > 20   # the windows really exercised crossings


# ------------------------------------------------------------ (e) rule 21: shared engine path
def test_new_functions_route_through_shared_sidereal_lon(monkeypatch):
    calls = []
    cut = engine.jd(datetime(2027, 1, 1) - timedelta(hours=5.5))

    def fake_lon(pid, j):
        calls.append(pid)
        return (29.0 if j < cut else 31.0), 0.1

    monkeypatch.setattr(engine, "sidereal_lon", fake_lon)
    r = engine.sign_change_dates("Saturn", datetime(2026, 12, 1), datetime(2027, 2, 1))
    assert len(r) == 1 and r[0]["date"] == "2027-01-01" and r[0]["to_sign"] == 1
    assert set(calls) == {swe.SATURN}
    calls.clear()
    engine.sign_change_dates("Ketu", datetime(2026, 12, 1), datetime(2026, 12, 3))
    assert set(calls) == {engine.PLANETS["Rahu"]}   # Ketu derived from Rahu, same helper
    calls.clear()
    engine.doshas(fake_chart := fake([10] * 7, moon_sign=0), as_of=START)
    assert calls == [swe.SATURN]
