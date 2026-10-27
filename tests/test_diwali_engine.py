"""Pure unit tests for diwali.compute_diwali (no DB, no api.py, no network).

Run: python3 -m pytest tests/test_diwali_engine.py -q -p no:cacheprovider --noconftest
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import engine  # noqa: E402
import diwali  # noqa: E402

VIKRAM = dict(name="Vikram Rao", dob="1984-08-14", tob="07:40", tz=5.5, lat=18.52, lon=73.86)


def run(**kw):
    args = dict(VIKRAM)
    opts = dict(gender="male", work_type="business", steering=None, place="Pune")
    for k in list(kw):
        (args if k in args else opts)[k] = kw.pop(k)
    return diwali.compute_diwali(args["name"], args["dob"], args["tob"], args["tz"],
                                 args["lat"], args["lon"], **opts)


@pytest.fixture(scope="module")
def vik():
    return run()


# ---------------------------------------------------------------- contract shape
TOP = {"product", "meta", "chart", "period", "sade_sati", "months", "area_order", "first_reason",
       "scores", "areas", "money_extra", "marriage_extra", "strengths", "lookback", "luck",
       "timeline", "best_time", "summary", "diwali", "answers", "wrapped", "teaser"}
META = {"name", "first_name", "dob", "tob", "place", "gender", "work_type", "steering",
        "time_quality", "basis", "lang", "variant", "age", "age_band", "as_of", "span", "gift"}
TEASER = {"name", "moon_sign", "nakshatra", "lagna_sign", "basis", "period", "sade_sati", "planets",
          "kundli", "strongest_area", "move", "words", "emphasis_area", "questions", "teasers"}


def test_payload_has_every_contract_key(vik):
    assert TOP <= set(vik)
    assert vik["product"] == "diwali"
    assert META <= set(vik["meta"])
    assert set(vik["meta"]["gift"]) == {"on", "giver_name", "message"}
    assert vik["meta"]["lang"] == "en" and vik["meta"]["variant"] == "/en/diwali"
    assert vik["meta"]["as_of"] == "2026-11-08" and vik["meta"]["span"] == "Nov 2026 – Oct 2027"
    assert set(vik["chart"]) == {"lagna", "moon", "planets", "houses"}
    assert len(vik["chart"]["planets"]) == 9
    assert all(set(p) == {"name", "sign", "house", "dignity", "retro", "nakshatra"}
               for p in vik["chart"]["planets"])
    assert sorted(vik["chart"]["houses"], key=int) == [str(i) for i in range(1, 13)]
    assert {"md", "ad", "ad_end", "next_ad", "turning_points"} <= set(vik["period"])
    assert set(vik["sade_sati"]) == {"active", "phase", "phases"}
    for m in vik["months"]:
        assert {"ym", "label", "year", "tone", "care_reason", "transits", "tags"} <= set(m)
        assert m["tone"] in ("best", "good", "steady", "careful")
        assert "Moon" not in m["transits"] and "Sun" in m["transits"]
    assert set(vik["scores"]) == set(diwali.AREAS)
    for a in diwali.AREAS:
        ar = vik["areas"][a]
        assert ar["state"] in ("good", "steady", "careful")
        assert set(ar["windows"]) == {"best", "good", "careful"}
        assert [t["key"] for t in ar["topics"]] == [f"{a}.t{i}" for i in range(1, len(diwali.TOPICS[a]) + 1)]
        for t in ar["topics"]:
            assert t["state"] in ("good", "steady", "careful")
            assert t["when"] in ("best", "good", "careful", "steady")
            assert t["why"] and "(" not in t["why"]
        for pic in ar["picture"]:
            assert pic["state"] in ("best", "good", "careful") and pic["months_label"]
            assert isinstance(pic["months_label"], list) and len(pic["months_label"]) <= 3
            assert all(isinstance(x, str) and 0 < len(x) <= 12 for x in pic["months_label"]), pic
            assert pic["months_text"] and isinstance(pic["caption"], list)
    assert set(vik["money_extra"]["dhana_yoga"]) >= {"present", "rule_text", "lords"}
    assert set(vik["marriage_extra"]["manglik"]) == {"lagna_rule", "moon_rule", "cancelled", "reason"}
    assert set(vik["marriage_extra"]["seventh"]) == {"sign", "lord", "lord_dignity"}
    assert set(vik["lookback"]) == {"good", "hard"}
    assert set(vik["luck"]) == {"bright_spots", "ninth"}
    assert len(vik["timeline"]) == 4 and set(vik["best_time"]) == {"from", "to"}
    assert len(vik["diwali"]["days"]) == 5 and len(vik["diwali"]["puja_times"]) == 9
    assert len(vik["answers"]) == 5 and all(a["state"] in ("good", "steady", "careful") for a in vik["answers"])
    assert {"strongest_area", "best", "careful", "move", "words"} <= set(vik["wrapped"])
    assert len(vik["wrapped"]["words"]) == 3
    assert TEASER == set(vik["teaser"])
    assert vik["teaser"]["period"] == "Mercury – Jupiter"


# ---------------------------------------------------------------- teaser never leaks a month
MONTH_RE = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|January|February|"
                      r"March|April|June|July|August|September|October|November|December)\b")
YEAR_RE = re.compile(r"(?<!\d)(19|20)\d\d(?!\d)")
YM_RE = re.compile(r"\d{4}-\d{2}")


@pytest.mark.parametrize("kw", [{}, {"steering": "money"}, {"steering": "luck", "time_quality": "T3"},
                                {"dob": "2003-02-20", "tob": "23:10", "gender": "female", "work_type": "student"},
                                {"dob": "1958-12-01", "tob": "04:05", "work_type": "home", "steering": "marriage"},
                                {"dob": "1991-05-30", "tob": "13:30", "time_quality": "T2", "work_type": "job"}])
def test_teaser_has_no_month_year_or_ym(kw):
    p = run(**kw)
    blob = json.dumps(p["teaser"], ensure_ascii=False)
    assert not MONTH_RE.search(blob), MONTH_RE.search(blob)
    assert not YEAR_RE.search(blob), YEAR_RE.search(blob)
    assert not YM_RE.search(blob)
    # the full Wrapped card does carry months (allowed inside the card, O-30)
    assert any(MONTH_RE.search(w["line"]) for w in p["wrapped"]["words"])
    assert all("●●●–●●●" in w["line_masked"] or not MONTH_RE.search(w0["line"])
               for w, w0 in zip(p["teaser"]["words"], p["wrapped"]["words"]))


# ---------------------------------------------------------------- inputs: every branch
@pytest.mark.parametrize("wt", diwali.WORK_TYPES)
def test_every_work_type_skipped_starts_with_situation_first(wt):
    p = run(work_type=wt)
    assert p["meta"]["work_type"] == wt
    assert p["area_order"][0] == diwali.SITUATION_ORDER[wt][0]
    assert sorted(p["area_order"]) == sorted(diwali.AREAS)
    assert p["first_reason"] == "situation"
    assert p["teaser"]["emphasis_area"] == p["area_order"][0]
    assert p["teaser"]["questions"] == diwali.QUESTIONS[p["area_order"][0]]


@pytest.mark.parametrize("steer", ["money", "career", "business", "family", "marriage"])
def test_every_steering_area_comes_first(steer):
    p = run(steering=steer, work_type="job")
    assert p["area_order"][0] == steer and p["first_reason"] == "picked"
    assert [a["q"] for a in p["answers"]] == diwali.QUESTIONS[steer]
    assert p["teaser"]["teasers"] == diwali.TEASERS[steer]


def test_steering_luck_and_none():
    luck = run(steering="luck", work_type="home")
    none = run(steering=None, work_type="home")
    assert luck["area_order"] == none["area_order"]          # areas as if skipped (O-31)
    assert luck["first_reason"] == "situation"
    assert [a["q"] for a in luck["answers"]] == diwali.QUESTIONS["luck"]
    assert all(a["state"] != "careful" for a in luck["answers"])   # positives only
    assert luck["teaser"]["emphasis_area"] == "luck"
    assert none["teaser"]["emphasis_area"] == none["area_order"][0] == "family"


def test_both_genders():
    m, f = run(gender="male"), run(gender="female")
    assert m["meta"]["gender"] == "male" and f["meta"]["gender"] == "female"
    assert m["marriage_extra"]["karakas"] == ["Venus"]
    assert f["marriage_extra"]["karakas"] == ["Venus", "Jupiter"]     # CLAUDE.md §12 incident
    # Jupiter as a karaka adds marriage points when it sits in the 1st/7th (Vikram: Jul 2027, Leo = 1st)
    pos = diwali._positions(datetime(2027, 7, 15, 12))
    leo = diwali.SIGN_NAMES.index("Leo")
    fem = diwali._area_term(pos, leo, "marriage", True)[0]
    mal = diwali._area_term(pos, leo, "marriage", False)[0]
    assert fem == mal + 1
    with pytest.raises(ValueError):
        run(gender="other")


def test_time_quality_basis_switch():
    t0, t2, t3 = run(time_quality="T0"), run(time_quality="T2", tob="13:00"), run(time_quality="T3", tob="12:00")
    assert t0["meta"]["basis"] == "lagna" and t0["chart"]["houses"]["1"]["sign"] == "Leo"
    for p in (t2, t3):
        assert p["meta"]["basis"] == "moon"
        assert p["chart"]["houses"]["1"]["sign"] == p["chart"]["moon"]["sign"]
        assert all(m["tone"] != "best" for m in p["months"])        # T2/T3 cap: no best
        assert all(not a["windows"]["best"] for a in p["areas"].values())
        assert p["marriage_extra"]["manglik"]["lagna_rule"] is None  # O-17: Moon rule only
        assert p["best_time"]["from"]                                # still names a best time
    assert any(m["tone"] == "best" for m in t0["months"])


def _lagna_edge_tob():
    """A birth time whose rising sign changes within the next 45 minutes."""
    base = datetime(1990, 6, 1, 6, 0)
    for k in range(0, 240, 5):
        loc = base + timedelta(minutes=k)
        a = engine.compute_chart(loc - timedelta(hours=5.5), 28.61, 77.21)["lagna_sign"]
        b = engine.compute_chart(loc + timedelta(minutes=30) - timedelta(hours=5.5), 28.61, 77.21)["lagna_sign"]
        if a != b:
            return loc.strftime("%H:%M")
    raise AssertionError("no edge found")


def test_t1_stable_vs_unstable():
    stable = run(time_quality="T1")                      # Vikram 07:40 Leo, stable ±45 min
    assert stable["meta"]["basis"] == "lagna"
    edge = _lagna_edge_tob()
    p = run(dob="1990-06-01", tob=edge, lat=28.61, lon=77.21, time_quality="T1")
    assert p["meta"]["basis"] == "moon"                  # falls back to the Moon chart
    assert p["meta"]["time_quality"] == "T1"


@pytest.mark.parametrize("dob,band", [("2005-01-10", "u25"), ("1994-03-03", "25_40"),
                                      ("1975-07-07", "40_60"), ("1950-11-20", "60p"),
                                      ("1966-11-08", "60p"), ("1966-11-09", "40_60")])
def test_age_bands(dob, band):
    p = run(dob=dob, tob="10:00")
    assert p["meta"]["age_band"] == band


def test_gift_on_off():
    off = run()
    assert off["meta"]["gift"] == {"on": False, "giver_name": "", "message": ""}
    on = run(gift_on=True, giver_name="  Priya ", gift_message="Happy Diwali")
    assert on["meta"]["gift"] == {"on": True, "giver_name": "Priya", "message": "Happy Diwali"}
    neither = run(gift_on=True)
    assert neither["meta"]["gift"] == {"on": True, "giver_name": "", "message": ""}
    # gift text never leaks into the teaser (sent to the browser before payment)
    assert "Priya" not in json.dumps(on["teaser"])
    off_name = run(gift_on=False, giver_name="Priya")
    assert off_name["meta"]["gift"]["giver_name"] == ""


def test_invalid_inputs_raise():
    for kw in ({"work_type": "retired"}, {"steering": "health"}, {"time_quality": "T9"}):
        with pytest.raises(ValueError):
            run(**kw)


# ---------------------------------------------------------------- area order (E4)
SIT = diwali.SITUATION_ORDER


@pytest.mark.parametrize("wt", diwali.WORK_TYPES)
def test_area_order_equal_scores_keeps_situation_table(wt):
    order, why = diwali.area_order(wt, None, {a: 1 for a in diwali.AREAS})
    assert order == SIT[wt] and why == "situation"


def test_area_order_fine_tune_gap_rule():
    base = {"business": 0, "money": 0, "career": 0, "family": 0, "marriage": 0}
    # spec worked example: Business 2, Family 2, Money 1, Marriage 1, Career 0
    ex = dict(base, business=2, family=2, money=1, marriage=1, career=0)
    assert diwali.area_order("business", None, ex)[0] == ["business", "money", "family", "career", "marriage"]
    # 1-point gap: no swap
    one = dict(base, family=1)
    assert diwali.area_order("business", None, one)[0] == SIT["business"]
    # 2-point gap swaps neighbours
    two = dict(base, career=2)
    assert diwali.area_order("business", None, two)[0] == ["business", "career", "money", "family", "marriage"]
    # first place pinned even when the 2nd outscores it by 3
    pin = dict(base, money=3)
    assert diwali.area_order("business", None, pin)[0][0] == "business"
    # chosen area pinned; the rest follow the situation order with the fine-tune
    picked = diwali.area_order("job", "marriage", dict(base, marriage=0, business=3))
    assert picked == (["marriage", "career", "money", "business", "family"], "picked")
    # Better luck picked -> areas exactly as if skipped
    assert diwali.area_order("job", "luck", base) == diwali.area_order("job", None, base)


# ---------------------------------------------------------------- Sade Sati (E3)
def test_sade_sati_vikram_phases_incl_2027_move_back(vik):
    ss = vik["sade_sati"]
    assert ss["active"] and ss["phase"] == "setting"
    assert ss["phases"] == [
        {"phase": "setting", "from": "2025-04", "to": "2027-05"},   # Saturn in Pisces since Mar 2025
        {"phase": "pause", "from": "2027-06", "to": "2027-10"},     # Aries 3 Jun 2027
        {"phase": "setting", "from": "2027-11", "to": "2028-02"},   # back to Pisces 20 Oct 2027
    ]
    assert vik["teaser"]["sade_sati"] == {"active": True, "phase": "setting"}


def test_sade_sati_inactive_chart():
    # Moon sign far from Saturn (Saturn in Pisces/Aries): pick a chart and check shape
    for dob in ("1990-01-15", "1995-06-15", "2000-03-15", "1985-09-15"):
        p = run(dob=dob, tob="12:00")
        ss = p["sade_sati"]
        if not ss["active"]:
            assert ss["phase"] is None
            assert all(ph["phase"] in ("rising", "peak", "setting", "pause") for ph in ss["phases"])
            return
    pytest.skip("all sampled charts in Sade Sati")


# ---------------------------------------------------------------- strengths, months, determinism
def test_strengths_always_three():
    for dob, tob in (("1984-08-14", "07:40"), ("1960-02-29", "01:00"), ("2001-12-31", "23:59"),
                     ("1977-04-04", "16:20"), ("1999-09-09", "09:09")):
        p = run(dob=dob, tob=tob)
        assert len(p["strengths"]) == 3
        assert len({s["planet"] for s in p["strengths"]}) == 3


def test_twelve_distinct_months(vik):
    yms = [m["ym"] for m in vik["months"]]
    assert yms == ["2026-11", "2026-12"] + [f"2027-{i:02d}" for i in range(1, 11)]
    assert [m["label"] for m in vik["months"]][:3] == ["Nov", "Dec", "Jan"]
    assert len({json.dumps(m["transits"], sort_keys=True) for m in vik["months"]}) == 12


def test_deterministic_for_fixed_as_of(monkeypatch):
    a = run(steering="money")

    class Later(datetime):
        @classmethod
        def utcnow(cls):
            return datetime(2031, 5, 5)

        @classmethod
        def now(cls, tz=None):
            return datetime(2031, 5, 5)

    monkeypatch.setattr(engine, "datetime", Later)
    b = run(steering="money")
    assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)


def test_routes_through_shared_engine(monkeypatch):
    """CLAUDE.md §21: chart facts come from engine.compute_chart / compute_report."""
    calls = {"chart": 0, "report": 0}
    real_chart, real_report = engine.compute_chart, engine.compute_report

    def spy_chart(*a, **k):
        calls["chart"] += 1
        return real_chart(*a, **k)

    def spy_report(*a, **k):
        calls["report"] += 1
        return real_report(*a, **k)

    monkeypatch.setattr(engine, "compute_chart", spy_chart)
    monkeypatch.setattr(engine, "compute_report", spy_report)
    p = run()
    assert calls["report"] >= 1 and calls["chart"] >= 1
    ch = real_chart(datetime(1984, 8, 14, 2, 10), 18.52, 73.86)
    assert p["chart"]["lagna"]["sign"] == diwali.SIGN_NAMES[ch["lagna_sign"]]
    assert p["chart"]["moon"]["nakshatra"] == engine.NAKSHATRAS[ch["grahas"]["Moon"].nak]


def test_sign_names_never_cancer():
    for dob in ("1984-07-20", "1990-07-25", "2000-07-18"):
        assert "Cancer" not in json.dumps(run(dob=dob, tob="12:00"))


# ---------------------------------------------------------------- sample chart sanity (persona.json / TIMING.md)
def test_vikram_chart_matches_persona(vik):
    by = {p["name"]: p for p in vik["chart"]["planets"]}
    assert vik["chart"]["lagna"]["sign"] == "Leo"
    assert vik["chart"]["moon"] == {"sign": "Aquarius", "nakshatra": "Purva Bhadrapada", "pada": 2}
    assert (by["Saturn"]["sign"], by["Saturn"]["dignity"], by["Saturn"]["house"]) == ("Libra", "exalted", 3)
    assert by["Sun"]["sign"] == "Karka"
    assert vik["period"]["md"] == "Mercury" and vik["period"]["ad"] == "Jupiter"
    assert vik["period"]["ad_end"] == "2028-02"


def test_vikram_timing_matches_approved_reading(vik):
    me = vik["money_extra"]
    assert me["gold_months"] == ["2026-11", "2027-07", "2027-09"]          # TIMING: Venus only
    assert me["sub_period_rule_fired"] is False
    assert me["loan_months"] == ["2026-12", "2027-07", "2027-08"]   # Jan 2027 is careful: not a loan month
    assert me["dhana_yoga"]["present"]
    tone = {m["ym"]: m for m in vik["months"]}
    assert tone["2026-11"]["tone"] == "good"
    assert tone["2027-01"]["tone"] == "careful" and tone["2027-01"]["care_reason"] == "reactions"
    for ym in ("2027-02", "2027-03", "2027-04"):
        assert tone[ym]["tone"] == "careful" and tone[ym]["care_reason"] == "spending"
    assert tone["2027-07"]["tone"] == "best"
    for ym in ("2027-08", "2027-09", "2027-10"):
        assert tone[ym]["tone"] == "good"
    assert vik["area_order"] == ["business", "money", "family", "career", "marriage"]   # spec worked example
    assert vik["scores"] == {"business": 2, "family": 2, "money": 1, "marriage": 1, "career": 0}
    assert [s["planet"] for s in vik["strengths"]] == ["Saturn", "Jupiter", "Mars"]
    assert vik["lookback"]["hard"] == ["2025-11", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]
    mg = vik["marriage_extra"]["manglik"]
    assert mg == {"lagna_rule": True, "moon_rule": False, "cancelled": True,
                  "reason": "Mars in own or exalted sign"}
    assert [t["theme"] for t in vik["timeline"]] == ["A steady new start", "Spend with care",
                                                      "The turning point", "Growth with a steady hand"]
    # parts cut from summary: the careful part is exactly Jan–May, the best part holds Jul
    assert [(t["from"], t["to"], t["tone"]) for t in vik["timeline"]] == [
        ("2026-11", "2026-12", "good"), ("2027-01", "2027-05", "careful"),
        ("2027-06", "2027-07", "best"), ("2027-08", "2027-10", "good")]
    assert vik["wrapped"]["move"] == "Save in spring. Act in summer."
    tps = {(t["ym"], t["kind"]) for t in vik["period"]["turning_points"]}
    assert ("2026-11", "jupiter_moves") in tps and ("2027-06", "saturn_moves") in tps


# ---------------------------------------------------------------- Diwali dates + puja times
def test_diwali_days_and_puja_cities(vik):
    assert [d["date"] for d in vik["diwali"]["days"]] == ["2026-11-06", "2026-11-07", "2026-11-08",
                                                          "2026-11-10", "2026-11-11"]
    cities = [p["city"] for p in vik["diwali"]["puja_times"]]
    assert cities == ["Delhi", "Mumbai", "Bengaluru", "Chennai", "Ahmedabad", "Kolkata",
                      "Pune", "Hyderabad", "Jaipur"]
    assert all(p["source"] for p in vik["diwali"]["puja_times"])


def test_puja_times_agree_with_vrishabha_lagna_computation():
    """Guards typos: every row is within 2 minutes of the Taurus sidereal ascendant
    rise/set after sunset on 8 Nov 2026 (the Drik Lakshmi Puja method)."""
    swe = engine.swe

    def asc(j, la, lo):
        return swe.houses_ex(j, la, lo, b'W', swe.FLG_SIDEREAL)[1][0] % 360

    def cross(target, j0, la, lo):
        a, b = j0, j0 + 0.25
        for _ in range(40):
            m = (a + b) / 2
            if (asc(m, la, lo) - target) % 360 < 180:
                b = m
            else:
                a = m
        return b

    def hhmm(j):
        y, mo, d, h = swe.revjul(j)
        t = datetime(y, mo, d) + timedelta(hours=h + 5.5)
        return t.hour * 60 + t.minute + t.second / 60

    swe.set_sid_mode(swe.SIDM_LAHIRI)
    for row in diwali.PUJA_TIMES:
        la, lo = diwali.PUJA_CITY_COORDS[row["city"]]
        s = cross(30, swe.julday(2026, 11, 8, 11.0), la, lo)
        e = cross(60, s, la, lo)
        sh, sm = map(int, row["start"].split(":"))
        eh, em = map(int, row["end"].split(":"))
        assert abs(sh * 60 + sm - hhmm(s)) <= 2, row
        assert abs(eh * 60 + em - hhmm(e)) <= 2, row


# ---------------------------------------------------------------- fix round (verifier findings)
def test_moon_only_manglik_ignores_lagna_cancellation():
    p = diwali.compute_diwali("V", "1984-08-14", "07:40", 5.5, 18.52, 73.86, gender="male",
                              work_type="business", steering="marriage", time_quality="T3")
    mg = p["marriage_extra"]["manglik"]
    assert mg == {"lagna_rule": None, "moon_rule": False, "cancelled": False, "reason": None}
    assert p["areas"]["marriage"]["topics"][4]["why"] == "Mars does not meet the Manglik rule."


def test_gold_months_follow_printed_rule_exactly():
    p = diwali.compute_diwali("A B", "2005-03-08", "20:09", 5.5, 19.0, 73.0, gender="male",
                              work_type="job", steering=None)
    sub = p["money_extra"]["sub_period_rule_fired"]
    want = [m["ym"] for m in p["months"]
            if sub or any(m["transits"][x]["house"] in (2, 11) for x in ("Venus", "Jupiter"))]
    assert p["money_extra"]["gold_months"] == want and "2027-08" in want


def test_loan_why_names_the_real_house():
    p = diwali.compute_diwali("A B", "1954-10-01", "15:16", 5.5, 19.0, 73.0, gender="male",
                              work_type="job", steering=None)
    assert p["money_extra"]["loan_months"] == ["2027-10"]
    assert p["areas"]["money"]["topics"][3]["why"] == "Mars passes the gains part."


def test_wrapped_careful_label_across_year():
    summ = {"best": {"from": "2027-07", "to": "2027-07", "label": "Jul 2027"},
            "careful": [{"from": "2026-12", "to": "2027-01", "reason": "spending", "label": "Dec 2026–Jan 2027"}]}
    w = diwali._wrapped("money", summ)
    assert w["words"][1]["line"] == "Dec–Jan is for planning, not spending."
    assert w["careful"]["from"] == "2026-12" and w["best"]["label"] == "Jul 2027"


def test_months_label_splits_gappy_runs():
    assert diwali._months_label(["2026-12", "2027-01", "2027-07", "2027-08"]) == \
        "Dec 2026–Jan 2027, Jul–Aug 2027"
    assert diwali._months_label(["2026-11", "2027-07", "2027-09"]) == "Nov 2026, Jul 2027, Sep 2027"
    assert diwali._months_label(["2027-06", "2027-07"]) == "Jun–Jul 2027"


def test_picture_shows_both_loan_windows(vik):
    pic = {x["label"]: x["months_label"] for x in vik["areas"]["money"]["picture"]}
    assert pic["clearing loans"] == ["Dec 26", "Jul–Aug 27"]       # careful Jan 2027 is left out
    txt = {x["label"]: x["months_text"] for x in vik["areas"]["money"]["picture"]}
    assert txt["clearing loans"] == "Dec 2026, Jul–Aug 2027"


def test_next_good_money_time_starts_at_first_good_month(vik):
    # TIMING: "May begin in Nov 2026, strongest Jun–Jul 2027".
    assert vik["areas"]["money"]["topics"][1]["months"][0] == "2026-11"
    for a in ("money", "career", "business"):
        w = vik["areas"][a]["windows"]
        first = min(w["best"] + w["good"])
        t2 = vik["areas"][a]["topics"][1]["months"]
        assert t2 and t2[0] == first, a


def test_family_tag_counts_fifth_house(vik):
    # Jupiter in the 1st aspects the 5th: TIMING approves Nov–Dec 2026 and Jul–Oct 2027.
    fam = vik["areas"]["family"]["topics"][1]["months"]
    for ym in ("2026-11", "2026-12", "2027-07", "2027-08", "2027-09", "2027-10"):
        assert ym in fam


# ---------------------------------------------------------------- one source of truth: summary
CASES = [{}, {"steering": "money"}, {"time_quality": "T3", "steering": "luck"},
         {"dob": "2003-02-20", "tob": "23:10", "gender": "female", "work_type": "student"},
         {"dob": "1958-12-01", "tob": "04:05", "work_type": "home", "steering": "marriage"},
         {"dob": "1991-05-30", "tob": "13:30", "time_quality": "T2", "work_type": "job"},
         {"dob": "1977-03-09", "tob": "18:20", "gender": "female", "work_type": "business"}]


def _yms(a, b):
    out, (y, m) = [], (int(a[:4]), int(a[5:]))
    while f"{y:04d}-{m:02d}" <= b:
        out.append(f"{y:04d}-{m:02d}")
        y, m = diwali._add_months(y, m, 1)
    return out


@pytest.mark.parametrize("kw", CASES)
def test_summary_matches_month_tones(kw):
    p = run(**kw)
    s, tone = p["summary"], {m["ym"]: m for m in p["months"]}
    # careful runs cover exactly the careful months, each run maximal and in order
    cov = [y for c in s["careful"] for y in _yms(c["from"], c["to"])]
    assert cov == [m["ym"] for m in p["months"] if m["tone"] == "careful"]
    for c in s["careful"]:
        assert c["reason"] in ("reactions", "spending")
        assert c["label"] == diwali._range_label(_yms(c["from"], c["to"]))
        reasons = [tone[y]["care_reason"] for y in _yms(c["from"], c["to"])]
        assert reasons.count(c["reason"]) * 2 >= len(reasons)
    assert s["best"]["from"] == p["best_time"]["from"] and s["best"]["to"] == p["best_time"]["to"]
    if any(m["tone"] == "best" for m in p["months"]):
        assert all(tone[y]["tone"] == "best" for y in _yms(s["best"]["from"], s["best"]["to"]))
    assert s["good_label"] == diwali._months_label([m["ym"] for m in p["months"] if m["tone"] == "good"])
    assert s["steady_label"] == diwali._months_label([m["ym"] for m in p["months"] if m["tone"] == "steady"])
    # every place that states the overall best/careful time reads summary
    w = p["wrapped"]
    assert {k: w["best"][k] for k in ("from", "to")} == {k: s["best"][k] for k in ("from", "to")}
    if s["careful"]:
        longest = max(s["careful"], key=lambda c: len(_yms(c["from"], c["to"])))
        assert w["careful"] == longest
        assert longest["label"].split(" ")[0].split("–")[0] in w["words"][1]["line"]
    else:
        assert w["careful"] is None
    _check_timeline(p)
    # no best/good topic or picture month is a careful month (overall or for that area)
    over = {y for y in tone if tone[y]["tone"] == "careful"}
    for a, ad in p["areas"].items():
        bad = over | set(ad["windows"]["careful"])
        for t in ad["topics"]:
            if t["state"] == "good" or t["when"] in ("best", "good"):
                assert not bad & set(t["months"]), t["key"]
        assert not over & set(ad["windows"]["best"] + ad["windows"]["good"]), a
    assert not over & set(p["money_extra"]["loan_months"])
    # no Wrapped word fails the bank lint (PATIENT used to)
    assert all(x["word"] not in ("PATIENT", "CALM") for x in w["words"])


def _check_timeline(p):
    """timeline: 4 parts covering the 12 months in order, cut from summary, never contradicting
    the month tones: careful months only in careful parts, every careful part holds careful
    months, a careful run / the best run is never split across differently-toned parts, and each
    part's core is exactly the summary months it holds."""
    s, tone = p["summary"], {m["ym"]: m["tone"] for m in p["months"]}
    tl = p["timeline"]
    assert len(tl) == 4 and [y for seg in tl for y in _yms(seg["from"], seg["to"])] == list(tone)
    seg_of = {y: k for k, seg in enumerate(tl) for y in _yms(seg["from"], seg["to"])}
    for y, t in tone.items():
        assert (t == "careful") <= (tl[seg_of[y]]["tone"] == "careful"), (y, tl)
    for c in s["careful"]:
        assert len({seg_of[y] for y in _yms(c["from"], c["to"])}) == 1
    best_run = set(_yms(s["best"]["from"], s["best"]["to"]))
    best_parts = [seg for seg in tl if best_run & set(_yms(seg["from"], seg["to"]))]
    has_best = "best" in tone.values()
    runs = [(c["from"], c["to"]) for c in s["careful"]]
    for seg in tl:
        yms = _yms(seg["from"], seg["to"])
        # core is a list of whole runs inside the part, in order, never overlapping
        assert isinstance(seg["core"], list) and seg["core"], seg
        core = [_yms(c["from"], c["to"]) for c in seg["core"]]
        flat = [y for r in core for y in r]
        assert set(flat) <= set(yms) and flat == sorted(flat) and len(flat) == len(set(flat))
        if seg["tone"] == "careful":
            # each core entry is exactly one summary.careful run (never spans non-careful months)
            assert all((c["from"], c["to"]) in runs for c in seg["core"]), (seg, runs)
            assert all(tone[y] == "careful" for y in flat)
            assert set(flat) == {y for y in yms if tone[y] == "careful"}
        elif seg in best_parts:
            assert seg["tone"] == ("best" if has_best else "good")
            assert len(core) == 1 and set(flat) == best_run & set(yms)
        else:
            assert seg["tone"] in ("good", "steady") and core == [yms]
        if seg["tone"] == "best":   # a best part always holds a summary.best month
            assert seg in best_parts, (seg, s["best"])
    assert all(seg["tone"] == best_parts[0]["tone"] for seg in best_parts)
    assert sum(seg["tone"] == "best" for seg in tl) <= (len(best_parts) if has_best else 0)


def _random_charts(n, seed=1):
    import random
    r = random.Random(seed)
    for _ in range(n):
        d = datetime(1950, 1, 1) + timedelta(days=r.randrange(0, 55 * 365), minutes=r.randrange(0, 1440))
        yield dict(dob=d.strftime("%Y-%m-%d"), tob=d.strftime("%H:%M"),
                   lat=r.uniform(8, 32), lon=r.uniform(68, 95),
                   gender=r.choice(["male", "female"]),
                   work_type=r.choice(["job", "business", "student", "home"]),
                   steering=r.choice([None, "money", "family", "luck", "marriage"]))


@pytest.mark.parametrize("kw", list(_random_charts(150)))
def test_timeline_never_contradicts_tones_random(kw):
    # the verifier's sweep (seed 1, N=150) found careful runs inside good/steady parts
    _check_timeline(run(**kw))


def test_timeline_verifier_repros():
    p = run(dob="1964-07-10", tob="01:20", lat=19.07, lon=72.87, work_type="job")
    assert [(t["from"], t["to"], t["tone"]) for t in p["timeline"]][1] == ("2027-01", "2027-01", "careful")
    _check_timeline(p)
    p = run(dob="1975-05-05", tob="04:45", lat=22.57, lon=88.36, work_type="job")
    best = [t for t in p["timeline"] if t["tone"] == "best"][0]
    assert best["core"] == [{k: p["summary"]["best"][k] for k in ("from", "to")}]
    _check_timeline(p)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_timeline_sweep_1000(seed):
    # 1000 random charts per seed: the strict timeline check + no 'Jan–Jan' single-month range
    import json, re
    same = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)–\1\b")
    for kw in _random_charts(1000, seed):
        p = run(**kw)
        _check_timeline(p)
        hit = same.search(json.dumps({k: p[k] for k in p if k != "teaser"}, ensure_ascii=False))
        assert not hit, (kw, hit.group(0))


def test_timeline_best_part_holds_a_best_month():
    # the best run (May) used to be split off an absorbed Apr-Jun block, leaving Jun toned best
    for dob, tob, lat, lon, g, w, st in [("1998-11-02", "14:18", 28.0207, 69.6444, "female", "home", "marriage"),
                                         ("1996-02-22", "04:54", 21.79, 79.1, "male", "business", "money"),
                                         ("1969-08-03", "18:04", 13.19, 82.66, "male", "business", "family")]:
        p = run(dob=dob, tob=tob, lat=lat, lon=lon, gender=g, work_type=w, steering=st)
        for t in p["timeline"]:
            if t["tone"] == "best":
                assert t["from"] <= p["summary"]["best"]["to"] and p["summary"]["best"]["from"] <= t["to"], t
        _check_timeline(p)


def test_vikram_summary_is_one_careful_run(vik):
    # Jan (reactions) + Feb–May (spending) are consecutive careful months: one run, Jan–May,
    # the same months the 12-month tally shows. Page 5, Wrapped and tally all read this.
    s = vik["summary"]
    assert s["careful"] == [{"from": "2027-01", "to": "2027-05", "reason": "spending", "label": "Jan–May 2027"}]
    assert s["best"] == {"from": "2027-07", "to": "2027-07", "label": "Jul 2027"}
    assert vik["wrapped"]["careful"]["label"] == "Jan–May 2027"
    assert vik["wrapped"]["words"][1]["line"] == "Jan–May is for planning, not spending."


@pytest.mark.parametrize("steer", [None, "money", "family", "luck"])
def test_wrapped_lead_area_vs_strongest(steer):
    p = run(steering=steer)
    w = p["wrapped"]
    assert w["lead_area"] == p["area_order"][0]
    assert w["same"] == (w["strongest_area"] == w["lead_area"])
    assert w["strongest_area"] in diwali.AREAS


def test_short_runs_caps_at_three_lines():
    span = [f"2026-{m:02d}" for m in (11, 12)] + [f"2027-{m:02d}" for m in range(1, 11)]
    assert diwali._short_runs(["2026-11", "2026-12", "2027-07"], span) == ["Nov–Dec 26", "Jul 27"]
    assert diwali._short_runs(["2026-12", "2027-01"], span) == ["Dec–Jan 27"]
    many = ["2026-11", "2027-01", "2027-02", "2027-04", "2027-06", "2027-07", "2027-08"]
    assert diwali._short_runs(many, span) == ["Jan–Feb 27", "Jun–Aug 27", "and more"]
    assert diwali._short_runs(["2026-11", "2027-01", "2027-03"], span) == ["Nov 26", "Jan 27", "Mar 27"]


@pytest.mark.parametrize("kw", CASES)
def test_business_dials(kw):
    d = run(**kw)["areas"]["business"]["dials"]
    assert [(x["left"], x["right"]) for x in d] == [("Job", "Business"), ("Alone", "Partner")]
    for x in d:
        assert 0 <= x["value"] <= 1 and x["why"] and "(" not in x["why"]


def test_vikram_dials(vik):
    d = vik["areas"]["business"]["dials"]
    assert d[0]["value"] == 0.7 and d[1]["value"] == 0.75   # Saturn own/exalted + Mercury in the 1st
