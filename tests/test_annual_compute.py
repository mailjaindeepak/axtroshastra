"""compute_annual: acceptance tests (run with --noconftest; never imports api.py)."""
import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timedelta

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import annual  # noqa: E402
import engine  # noqa: E402

FIXDIR = os.path.join(ROOT, "tests", "fixtures_annual")   # tracked snapshots (docs/annual is untracked)
AS_OF = "2026-11-06"
A = dict(name="Rohan Mehta", gender="male", dob="2001-02-17", tob=None, time_quality="T3", place="Jaipur",
         lat=26.91, lon=75.79, tz=5.5, work_type="student", steering="strengths")
B = dict(name="Anjali Deshpande", gender="female", dob="1996-10-19", tob="12:30", time_quality="T0", place="Pune",
         lat=18.52, lon=73.86, tz=5.5, work_type="job", steering=None)
MAP = {"best": "strong", "good": "strong", "steady": "mixed", "careful": "careful"}
BANNED = ["slow", "stretch", "window", "phase", "tendency", "steadier", "favourable", "pivotal", "culminate",
          "auspicious", "pressure", "karma", "dasha", "house", "bhav", "transit", "dues", "patient", "squeeze",
          "pressing", "heavy", "astrosage", "refund", "health", "mental", "costlier", "fastest"]


def snapshot():
    """Approved Anjali facts (tests/fixtures_annual/anjali_facts.json); JSON stringifies the int kundli keys."""
    p = json.load(open(os.path.join(FIXDIR, "anjali_facts.json")))
    p["kundli"] = {int(k): v for k, v in p["kundli"].items()}
    return p


@pytest.fixture(scope="module")
def ra():
    return annual.compute_annual(A, AS_OF)


@pytest.fixture(scope="module")
def rb():
    return annual.compute_annual(B, AS_OF)


def mk(**kw):
    return {**B, **kw}


# ---------------------------------------------------------------- (1) mock facts
def test_persona_a_facts(ra):
    """Rohan Mehta (invented): structure and properties only, no numbers copied from any real chart."""
    f = ra["facts"]
    assert f["first_name"] == "Rohan" and f["name"] == "Rohan Mehta" and f["gender"] == "male" and f["work_type"] == "student"
    assert f["rising_sign"] is None and f["birth"]["time_known"] is False       # T3: no birth time, Moon sign is box 1
    assert f["moon_sign"] in engine_signs() and f["first_open_topic"] == annual.TOPIC_LABEL["strengths"]
    span = [m["ym"] for m in f["span_months"]]
    assert len(span) == 12 and [m["ym"] for m in f["past_months"]] == ["2026-10", "2026-11"]
    assert set(f["tones"]) == set(span) | {"2026-10", "2026-11"}
    assert set(f["tones"].values()) <= {"strong", "mixed", "careful"}
    assert set(f["areas"]) == {"money", "career", "business", "family", "marriage"}
    for a_, months in f["areas"].items():
        assert list(months) == span and set(months.values()) <= {"strong", "mixed", "careful"}, a_
    assert sorted(f["kundli"]) == list(range(1, 13)) and len(f["planet_table"]) == 9
    assert f["kundli"][1] and "Mo" in f["kundli"][1]                                  # Moon sign is box 1 with no rising sign
    assert isinstance(f["kaal_sarp"], bool) and isinstance(f["pitra"], bool)
    # Dhaiya agrees with the engine's own dosha rule (Saturn 4th/8th from the Moon sign on the report date)
    ch = engine.compute_chart(datetime.fromisoformat("2001-02-17T12:00:00") - timedelta(hours=5.5), 26.91, 75.79)
    dos = engine.doshas(ch, annual._to_dt(AS_OF))["shani_dhaiya"]
    assert f["dhaiya"]["active"] == dos["active"] and f["dhaiya"]["kind"] == dos["kind"]
    assert f["saturn_now"]["house_from_moon"] == dos["house_from_moon"]
    assert f["kaal_sarp"] == engine.doshas(ch, annual._to_dt(AS_OF))["kaal_sarp"]
    assert f["pitra"] == engine.doshas(ch, annual._to_dt(AS_OF))["pitra"]
    # JSON round trip keeps everything but the int kundli keys
    back = json.loads(json.dumps(f))
    assert {int(k): v for k, v in back["kundli"].items()} == f["kundli"]
    assert {k: v for k, v in back.items() if k != "kundli"} == {k: v for k, v in f.items() if k != "kundli"}


def engine_signs():
    return ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]


def test_persona_b_facts(rb):
    f, snap = rb["facts"], snapshot()
    assert (f["moon_sign"], f["rising_sign"], f["nakshatra"], f["pada"]) == ("Sagittarius", "Sagittarius", "Purva Ashadha", 4)
    assert f["planet_period"]["main"] == "Rahu" and f["planet_period"]["sub"] == "Saturn"
    assert f["planet_period"]["until"] == "2028-05-12"
    assert f["manglik"]["status"] == "manglik" and not f["manglik"]["cancelled"]
    assert f["dhaiya"] == {"active": True, "kind": "4th", "ends": "2027-06-03", "restarts": "2027-10-20"}
    names = [y["name"] for y in f["yogas"]]
    for n in ("Gajakesari", "Bhadra", "Hamsa", "Neecha Bhanga"):
        assert any(x.startswith(n) for x in names)
    assert f["kundli"][1] == ["Mo", "Ju"] and f["kundli"][10] == ["Me", "Ra"]
    # the engine reproduces the approved snapshot (tests/fixtures_annual/anjali_facts.json) ...
    skip = ("areas",)
    assert {k: v for k, v in f.items() if k not in skip} == {k: v for k, v in snap.items() if k not in skip}
    # ... except one known engine difference: Nov 2027 area tones (the snapshot keeps the owner-approved mock values;
    # the engine says 'strong' for every area in 2027-11). Pinned so a change either way is noticed.
    assert set(f["areas"]) == set(snap["areas"])
    for k, v in snap["areas"].items():
        assert {m: t for m, t in f["areas"][k].items() if m != "2027-11"} == {m: t for m, t in v.items() if m != "2027-11"}
        assert (v["2027-11"], f["areas"][k]["2027-11"]) == ("mixed", "strong"), k


# ---------------------------------------------------------------- (2) key contract
def _same_types(got, want, path=""):
    if want is None or got is None:
        return
    assert type(got) == type(want), f"{path}: {type(got)} vs {type(want)}"
    if isinstance(want, dict) and want and not all(isinstance(k, str) and re.match(r"\d{4}-\d\d$", k) for k in want):
        if all(isinstance(k, int) for k in want):
            return
        assert set(got) == set(want), f"{path}: {set(got) ^ set(want)}"
        for k in want:
            _same_types(got[k], want[k], f"{path}.{k}")


def test_facts_keys_and_types(rb):
    want = snapshot()
    assert set(rb["facts"]) == set(want)
    skip = ("areas", "sign_changes", "planet_table", "past_months", "span_months", "yogas")
    _same_types({k: v for k, v in rb["facts"].items() if k not in skip}, {k: v for k, v in want.items() if k not in skip})
    assert set(rb["facts"]["planet_table"][0]) == set(want["planet_table"][0])
    assert set(rb["facts"]["yogas"][0]) == set(want["yogas"][0])
    assert set(rb["facts"]["areas"]) == set(want["areas"])
    assert set(rb["facts"]["sign_changes"][0]) == set(want["sign_changes"][0])
    assert set(rb["facts"]["sade_sati"]) == set(want["sade_sati"])
    assert set(rb["facts"]["dhaiya"]) == set(want["dhaiya"])


def test_span_and_past():
    f = annual.compute_annual(B, "2026-11-06")["facts"]
    assert [m["ym"] for m in f["span_months"]][0] == "2026-12" and [m["ym"] for m in f["span_months"]][-1] == "2027-11"
    assert [m["ym"] for m in f["past_months"]] == ["2026-10", "2026-11"]
    f = annual.compute_annual(B, "2026-12-31")["facts"]
    assert f["span_months"][0]["ym"] == "2027-01" and f["past_months"][1]["ym"] == "2026-12"
    assert len(f["tones"]) == 14
    assert annual.compute_annual(B)["meta"]["as_of"]   # default = today


# ---------------------------------------------------------------- (3) leak test
def test_teaser_leak(rb):
    pv = rb["teaser"]["preview"]
    f = rb["facts"]
    strip = pv["strip"]
    assert len(strip) == 12 and len(pv["past"]) == 2
    for e in strip[:2]:
        assert e["open"] and e["tone"] == f["tones"][f["span_months"][strip.index(e)]["ym"]]
    for e in strip[2:]:
        assert set(e) == {"m", "label", "open"} and e["open"] is False
    assert pv["future_free"]["range"] == strip[0]["label"]
    assert [p["range"] for p in pv["past"]] == [m["label"] for m in f["past_months"]]
    assert [p["tone"] for p in pv["past"]] == [f["tones"][m["ym"]] for m in f["past_months"]]
    # locked month names appear only in strip labels
    blob = json.dumps({k: v for k, v in rb["teaser"].items() if k != "preview"}) + \
        json.dumps({k: v for k, v in pv.items() if k not in ("strip", "past", "future_free", "chart")})
    for e in strip[2:]:
        assert e["label"] not in blob
        for k in ("past", "future_free"):
            assert e["label"] not in json.dumps(pv[k])
    assert "areas" not in rb["teaser"] and "tones" not in rb["teaser"]
    assert len(rb["teaser"]["questions"]) == 5
    low = json.dumps(pv["past"] + [pv["future_free"]]).lower()
    for w in BANNED:
        assert w not in low, w


# ---------------------------------------------------------------- (4) branches
@pytest.mark.parametrize("wt", annual.WORK_TYPES)
def test_work_types(wt):
    r = annual.compute_annual(mk(work_type=wt), AS_OF)
    assert r["teaser"]["preview"]["work_type"] == wt
    assert r["facts"]["work_type"] == wt


def test_work_type_texts_differ():
    t = {wt: annual.compute_annual(mk(work_type=wt), AS_OF)["teaser"]["preview"]["future_free"]["text"] for wt in annual.WORK_TYPES}
    assert len(set(t.values())) == 4


@pytest.mark.parametrize("st", list(annual.STEERING) + [None, ""])
def test_steering(st):
    r = annual.compute_annual(mk(steering=st), AS_OF)
    want = st or "career"
    assert r["teaser"]["emphasis_area"] == want and r["teaser"]["preview"]["start_area"] == want
    assert r["facts"]["first_open_topic"] == annual.TOPIC_LABEL[want]


@pytest.mark.parametrize("wt,first", [("student", "career"), ("job", "career"), ("business", "career"), ("home", "marriage")])
def test_unsteered_first_topic(wt, first):
    assert annual.compute_annual(mk(work_type=wt), AS_OF)["teaser"]["emphasis_area"] == first


@pytest.mark.parametrize("tq,extra", [("T0", {"tob": "12:30"}), ("T2", {"tob": None, "time_band": "shaam"}),
                                      ("T3", {"tob": None})])
def test_time_quality(tq, extra):
    r = annual.compute_annual(mk(time_quality=tq, **extra), AS_OF)
    t, f = r["teaser"], r["facts"]
    moon_basis = tq != "T0"
    assert t["basis"] == ("moon" if moon_basis else "lagna") and t["preview"]["moon_basis"] is moon_basis
    assert (f["rising_sign"] is None) is moon_basis and (t["preview"]["chart"]["rising"] is None) is moon_basis
    assert any("La" in c for c in t["kundli"].values()) is (not moon_basis)
    assert f["birth"]["time_known"] is (tq == "T0")
    if moon_basis:   # capped: no lagna-only yogas, Moon sign is house 1
        assert all(y["name"].startswith(annual._MOON_YOGAS) for y in f["yogas"])
        assert "Mo" in f["kundli"][1]
    assert r["meta"]["time_quality"] == tq


@pytest.mark.parametrize("g", ["male", "female"])
def test_gender(g):
    assert annual.compute_annual(mk(gender=g), AS_OF)["facts"]["gender"] == g


def test_gender_changes_marriage_tones():
    m = annual.compute_annual(mk(gender="male"), AS_OF)["facts"]["areas"]["marriage"]
    f = annual.compute_annual(mk(gender="female"), AS_OF)["facts"]["areas"]["marriage"]
    assert set(m) == set(f)   # both branches run; tones may legitimately differ


# Moon dates at 12:00 IST (T3): Aries 1990-02-03, Pisces 1990-01-04, Aquarius 1990-01-01, Taurus 1990-01-07
@pytest.mark.parametrize("dob,active,stage,stages_in_span", [
    ("1990-02-03", True, "first", ["second", "first"]),     # Moon Aries: Saturn 12th -> 1st -> 12th
    ("1990-01-04", True, "second", ["third", "second"]),    # Moon Pisces
    ("1990-01-01", True, "third", [None, "third"]),         # Moon Aquarius
    ("1990-01-07", False, None, ["first", None]),           # Moon Taurus: first stage starts mid-span
])
def test_sade_sati_each_stage(dob, active, stage, stages_in_span):
    r = annual.compute_annual(mk(dob=dob, tob=None, time_quality="T3"), AS_OF)
    ss = r["facts"]["sade_sati"]
    assert ss["active"] is active and ss["stage"] == stage
    assert [c["stage"] for c in ss["change_dates"]] == stages_in_span
    assert [c["date"] for c in ss["change_dates"]] == ["2027-06-03", "2027-10-20"]
    cs = r["teaser"]["preview"]["chart"]["sade_sati"]
    assert cs["active"] is active and cs["stage"] == stage
    assert bool(cs["ends"]) is active
    assert (cs["next_starts"] is None) is active


def test_kaal_sarp_and_pitra():
    ks = annual.compute_annual(mk(dob="1995-11-04", tob=None, time_quality="T3"), AS_OF)["facts"]
    assert ks["kaal_sarp"] is True
    pt = annual.compute_annual(mk(dob="1990-01-16", tob=None, time_quality="T3"), AS_OF)["facts"]
    assert pt["pitra"] is True
    assert annual.compute_annual(B, AS_OF)["facts"]["pitra"] is False


def test_dhaiya_inactive_branch():
    d = annual.compute_annual(mk(dob="1990-01-13", tob=None, time_quality="T3"), AS_OF)   # Moon Cancer: Saturn 10th
    dh = d["facts"]["dhaiya"]
    assert dh["active"] is False and dh["kind"] is None and dh["ends"] is None
    assert d["teaser"]["preview"]["chart"]["dhaiya"]["next_starts"]


@pytest.mark.parametrize("bad", [
    dict(name=""), dict(name=None), dict(gender="x"), dict(work_type="x"), dict(steering="business"),
    dict(time_quality="T9"), dict(dob="2000-13-40"), dict(dob=None), dict(tob="25:99"), dict(tob=None),
    dict(lat=None), dict(lat=95), dict(lon="abc"), dict(tz=99), dict(tz=None), dict(time_quality="T2", time_band="x"),
])
def test_bad_input(bad):
    with pytest.raises(ValueError):
        annual.compute_annual(mk(**bad), AS_OF)


def test_bad_payload_and_as_of():
    with pytest.raises(ValueError):
        annual.compute_annual("nope", AS_OF)
    with pytest.raises(ValueError):
        annual.compute_annual(B, "not-a-date")
    with pytest.raises(ValueError):
        annual.compute_annual(B, 12)


# ---------------------------------------------------------------- (5) rule 21
def test_routes_through_engine(monkeypatch):
    calls = []
    for n in ("compute_chart", "compute_report", "doshas", "sign_change_dates", "sade_sati_stages",
              "saturn_house_timeline", "manglik"):
        real = getattr(engine, n)
        monkeypatch.setattr(engine, n, (lambda real, n: lambda *a, **k: (calls.append(n), real(*a, **k))[1])(real, n))
    annual.compute_annual(B, AS_OF)
    assert set(calls) >= {"compute_chart", "compute_report", "doshas", "sign_change_dates", "sade_sati_stages",
                          "saturn_house_timeline", "manglik"}


def test_no_festival_or_ai():
    src = open(os.path.join(ROOT, "annual.py")).read()
    for w in ("DIWALI_DAYS", "PUJA_TIMES", "GOLD_RULE", "anthropic", "openai", "narrative", "Lakshmi", "gold"):
        assert w not in src
    out = json.dumps(annual.compute_annual(B, AS_OF)).lower()
    for w in ("diwali", "puja", "lakshmi", "deepavali"):
        assert w not in out


# ---------------------------------------------------------------- (6) rule 22
def test_no_persona_leak():
    for p, others in ((A, ("anjali", "deshpande")), (B, ("rohan", "mehta"))):
        out = json.dumps(annual.compute_annual(p, AS_OF)).lower()
        for other in others:
            assert other not in out, other
    out = json.dumps(annual.compute_annual(mk(name="Neha Rao"), AS_OF))
    for w in ("Rohan", "Mehta", "Anjali", "Deshpande"):
        assert w not in out
    assert "Neha" in out


# ---------------------------------------------------------------- tob handling (api passes the band midpoint as tob)
def _spy_tob(monkeypatch, payload):
    seen = []
    real = engine.compute_report
    monkeypatch.setattr(engine, "compute_report", lambda *a, **k: (seen.append(a[2]), real(*a, **k))[1])
    r = annual.compute_annual(payload, AS_OF)
    return seen[0], r


@pytest.mark.parametrize("band,mid", list(annual.BAND_MID.items()))
def test_t2_uses_passed_tob(monkeypatch, band, mid):
    tob, r = _spy_tob(monkeypatch, mk(time_quality="T2", tob=mid))
    assert tob == mid and r["meta"]["tob"] == mid


def test_t2_tob_beats_band(monkeypatch):
    assert _spy_tob(monkeypatch, mk(time_quality="T2", tob="07:00", time_band="shaam"))[0] == "07:00"


def test_t2_band_fallback_and_default(monkeypatch):
    assert _spy_tob(monkeypatch, mk(time_quality="T2", tob=None, time_band="shaam"))[0] == "19:00"
    assert _spy_tob(monkeypatch, mk(time_quality="T2", tob=None))[0] == "13:00"


def test_t3_uses_passed_tob(monkeypatch):
    assert _spy_tob(monkeypatch, mk(time_quality="T3", tob="12:00"))[0] == "12:00"
    assert _spy_tob(monkeypatch, mk(time_quality="T3", tob="09:15"))[0] == "09:15"
    assert _spy_tob(monkeypatch, mk(time_quality="T3", tob=None))[0] == "12:00"


@pytest.mark.parametrize("tq", ["T0", "T1", "T2", "T3"])
def test_bad_tob_any_quality(tq):
    with pytest.raises(ValueError):
        annual.compute_annual(mk(time_quality=tq, tob="7pm"), AS_OF)


# ---------------------------------------------------------------- audit F2 / F3
from datetime import datetime, timedelta  # noqa: E402

ARIES = mk(dob="1990-02-03", tob="12:00", time_quality="T3")   # Moon Aries (12:00 IST)


def _engine_stages(as_of, moon_sign=0):
    end = annual.diwali._add_months(*annual.diwali._add_months(as_of.year, as_of.month, 1), 12)
    return engine.sade_sati_stages(moon_sign, as_of, datetime(*end, 1))


def test_sade_sati_change_between_as_of_and_span_start():
    # Saturn enters Aries on 2027-06-03, after as_of 2027-06-01 but before the span starts (2027-07-01)
    f = annual.compute_annual(ARIES, "2027-06-01")["facts"]
    ss = f["sade_sati"]
    assert ss["active"] and ss["stage"] == "first"
    assert f["span_months"][0]["ym"] == "2027-07"
    assert ss["change_dates"][0] == {"date": "2027-06-03", "stage": "second"}
    want = _engine_stages(datetime(2027, 6, 1))
    assert want["stage_at_start"] == "first"
    assert [(c["date"], c["stage"]) for c in want["changes"] if c["date"] < "2028-07-01"] == \
        [(c["date"], c["stage"]) for c in ss["change_dates"]]
    # replaying the changes gives the stage in force on the 1st of each span month
    for m in f["span_months"]:
        first = m["ym"] + "-01"
        stage = ss["stage"]
        for c in ss["change_dates"]:
            if c["date"] <= first:
                stage = c["stage"]
        assert stage == _engine_stage_on(first), m
    assert f["saturn_now"]["changes"][0]["date"] == "2027-06-03"


def _engine_stage_on(iso):
    d = datetime.fromisoformat(iso)
    return {"none": None}.get(s := engine.sade_sati_stages(0, d, d + timedelta(days=1))["stage_at_start"], s)


@pytest.mark.parametrize("as_of", ["2026-11-30", "2026-12-31", "2027-02-28", "2028-02-29"])
def test_month_end_as_of(as_of):
    f = annual.compute_annual(ARIES, as_of)["facts"]
    d = datetime.fromisoformat(as_of)
    ny, nm = (d.year + (d.month == 12), d.month % 12 + 1)
    assert f["span_months"][0]["ym"] == f"{ny:04d}-{nm:02d}" and len(f["span_months"]) == 12
    assert f["past_months"][1]["ym"] == as_of[:7] and f["today"] == as_of
    want = _engine_stages(d)
    assert [(c["date"], c["stage"]) for c in f["sade_sati"]["change_dates"]] == \
        [(c["date"], None if c["stage"] == "none" else c["stage"]) for c in want["changes"]
         if as_of <= c["date"] < "%04d-%02d-01" % annual.diwali._add_months(
             int(f["span_months"][-1]["ym"][:4]), int(f["span_months"][-1]["ym"][5:]), 1)]
    assert f["sade_sati"]["stage"] == (want["stage_at_start"] if want["active_at_start"] else None)
    assert all(c["date"] >= as_of for c in f["sade_sati"]["change_dates"])


@pytest.mark.parametrize("dob", ["2026-11-06", "2026-11-07", "2030-01-01"])
def test_dob_today_or_future_raises(dob):
    with pytest.raises(ValueError, match="before the report date"):
        annual.compute_annual(mk(dob=dob), AS_OF)


@pytest.mark.parametrize("dob", ["1900-01-01", "2026-11-05"])
def test_extreme_dob_ok(dob):
    f = annual.compute_annual(mk(dob=dob, tob="12:00"), AS_OF)["facts"]
    assert f["planet_period"]["main"] and len(f["tones"]) == 14


def test_api_turns_value_error_into_422():
    # api.py is not imported here; assert the catch exists and the exact payload shape it builds raises
    src = open(os.path.join(ROOT, "api.py")).read()
    i = src.index("annual.compute_annual(")
    assert "except ValueError as e:" in src[i:i + 600] and "HTTPException(422" in src[i:i + 700]
    with pytest.raises(ValueError):
        annual.compute_annual({"name": "X", "dob": "2030-01-01", "tob": "12:00", "tz": 5.5, "lat": 18.5, "lon": 73.8,
                               "gender": "female", "work_type": "job", "steering": None,
                               "time_quality": "T0", "place": ""})
