"""teaser["preview"] (v8): shape, tones, past window, determinism, and the strict no-leak test.
Pure: run with --noconftest. Runs against the REAL reading texts; only the fallback test stubs them."""
import json
import re
import sys
import types

import pytest

import diwali
import diwali_readings

MONTHS_FULL = ["January", "February", "March", "April", "May", "June", "July", "August",
               "September", "October", "November", "December"]
MONTH_RE = re.compile(r"\b(" + "|".join(MONTHS_FULL + [m[:3] for m in MONTHS_FULL]) + r")\b")
YEAR_RE = re.compile(r"(?<!\d)(19|20)\d\d(?!\d)")
BANNED = ["stretch", "window", "phase", "tendency", "tended", "tends", "steadier", "favourable",
          "pivotal", "culminate", "auspicious", "pressure", "karma", "dasha", "house", "bhav",
          "transit", "dues", "patient", "anxiety", "stress", "depress", "health", "disease",
          "illness", "medical", "therapy", "burnout", "astrosage"]
WT = ("job", "business", "student", "home")
KW = dict(name="Neha Kulkarni", dob="1990-03-12", tob="09:30", tz=5.5, lat=18.52, lon=73.86,
          gender="female", work_type="job", steering="career", place="Pune")


def run(**o):
    return diwali.compute_diwali(**{**KW, **o})["teaser"]["preview"]


def strip_allowed(teaser):
    """teaser JSON with every allowed preview field removed, so any other month/year is a leak."""
    t = json.loads(json.dumps(teaser))
    pv = t["preview"]
    for b in pv["past"]:
        b.pop("range"), b.pop("text")
    pv["future_free"].pop("range"), pv["future_free"].pop("text")
    for e in pv["strip"]:
        e.pop("label")
    return t


CASES = [dict(work_type=w, gender=g) for w in WT for g in ("male", "female")] + \
    [dict(steering=s) for s in diwali.STEERING] + \
    [dict(time_quality=q) for q in ("T0", "T1", "T2", "T3")]


@pytest.mark.parametrize("o", CASES)
def test_shape_and_no_leak(o):
    t = diwali.compute_diwali(**{**KW, **o})["teaser"]
    pv = t["preview"]
    assert pv["version"] == 8 and pv["work_type"] == o.get("work_type", "job")
    assert [b["range"] for b in pv["past"]] == ["Jul – Aug 2026", "Sep – Oct 2026"]
    assert pv["future_free"]["range"] == "Nov – Dec 2026"
    st = pv["strip"]
    assert len(st) == 12 and [e["open"] for e in st] == [True] * 2 + [False] * 10
    assert st[0]["label"] == "Nov 2026" and st[-1]["label"] == "Oct 2027"
    assert "".join(e["m"] for e in st) == "NDJFMAMJJASO"
    assert all("tone" not in e and "text" not in e for e in st[2:])
    assert [e["tone"] for e in st[:2]] and all(e["tone"] in ("good", "steady", "careful") for e in st[:2])
    heads = {"good": "A good time", "steady": "A mixed time", "careful": "A slower, costlier time"}
    for b in pv["past"] + [pv["future_free"]]:
        assert b["heading"] == heads[b["tone"]]
    # strict leak test: month names/years only in the allowed fields
    rest = json.dumps(strip_allowed(t), ensure_ascii=False)
    assert not MONTH_RE.search(rest), MONTH_RE.search(rest)
    assert not YEAR_RE.search(rest), YEAR_RE.search(rest)
    for b in pv["past"] + [pv["future_free"]]:
        assert not MONTH_RE.search(b["text"]) and not YEAR_RE.search(b["text"])
        for w in BANNED:
            assert w not in (b["heading"] + " " + b["text"]).lower(), w
    assert "answers" not in t and "best_time" not in t and "months" not in t


def test_moon_basis():
    for q, moon in (("T0", False), ("T1", False), ("T2", True), ("T3", True)):
        pv = run(time_quality=q)
        assert pv["moon_basis"] is moon
        assert (pv["chart"]["rising"] is None) is moon
        assert pv["chart"]["moon"] in diwali.SANSKRIT.values()


def test_tone_is_more_serious_of_two_months(monkeypatch):
    seq = {"best": "good", "good": "good", "steady": "steady", "careful": "careful"}
    assert diwali._pv_block("past", [{"label": "Jul", "year": 2026, "tone": "best"},
                                     {"label": "Aug", "year": 2026, "tone": "careful"}], "job", 0, 0)["tone"] == "careful"
    assert diwali._pv_block("future", [{"label": "Dec", "year": 2026, "tone": "good"},
                                       {"label": "Jan", "year": 2027, "tone": "steady"}], "job", 0, 0)["range"] == "Dec 2026 – Jan 2027"
    assert set(seq.values()) == set(diwali._PV_RANK)


def test_past_blocks_come_from_previous_window():
    old = diwali.compute_diwali(**KW, as_of="2025-11-08")["months"]
    pv = run()
    want = diwali._pv_block("past", old[-4:-2], "job", 0, 0)["tone"]
    assert pv["past"][0]["tone"] == want


def test_deterministic_and_chart_variation():
    assert run() == run()
    assert run(as_of="2026-11-08") == run()
    texts = {run(dob=d, tob=t, lat=la, lon=lo)["future_free"]["text"]
             for d, t, la, lo in (("1990-03-12", "09:30", 18.52, 73.86), ("1985-07-01", "14:10", 28.6, 77.2),
                                  ("1995-11-23", "06:45", 12.97, 77.59), ("2001-01-09", "22:00", 19.07, 72.87),
                                  ("1978-09-15", "03:20", 13.08, 80.27), ("1999-05-05", "17:35", 22.57, 88.36))}
    assert len(texts) > 1


def test_readings_pick_fallback_and_normalising(monkeypatch):
    assert diwali_readings.pick("past", "nope", "best", 4) == diwali_readings.pick("past", "job", "good", 4)
    monkeypatch.setitem(sys.modules, "diwali_readings_future", types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, "diwali_readings_past", types.SimpleNamespace())
    assert "may" in diwali_readings.pick("future", "job", "good", 0)
    assert diwali_readings.pick("past", "job", "good", 0).startswith("These two months")
    pv = run()  # whole preview still builds with the text modules missing
    assert pv["future_free"]["text"] and len(pv["past"]) == 2


def test_fixture_matches_engine_shape():
    fx = json.load(open("docs/diwali/preview-v8-fixture.json"))
    assert fx["preview"]["version"] == 8 and len(fx["preview"]["strip"]) == 12


def test_moon_fixture():
    fx = json.load(open("docs/diwali/preview-v8-fixture-moon.json"))
    assert fx["preview"]["moon_basis"] is True and fx["preview"]["chart"]["rising"] is None
