"""Golden-file regression guard. (#3)

Recomputes a known chart with a PINNED as-of date and compares the stable subset
of the output against a committed snapshot. Any unintended change to the astronomy
or scoring engine will fail this test. Regenerate deliberately with:
    python tests/regen_golden.py
"""
import json
import os
from datetime import datetime, timedelta

from engine import compute_report, compute_chart
import divisional
from vidyarthi import compute_vidyarthi_report

GOLDEN = os.path.join(os.path.dirname(__file__), "golden")
ASOF = datetime(2025, 1, 1)


def _marriage_snapshot():
    rep = compute_report(name="Golden", dob="1990-03-21", tob="08:15",
                         tz_offset_hours=5.5, lat=28.61, lon_geo=77.21,
                         female=True, time_quality="T0", as_of=ASOF)
    return {"meta": rep["meta"], "chart": rep["chart"], "manglik": rep["manglik"],
            "significators": rep["significators"], "current_period": rep["current_period"],
            "windows": rep["windows"], "teaser_moon": rep["teaser"]["moon_sign"]}


def _divisional_snapshot():
    local = datetime.fromisoformat("1990-03-21T08:15:00")
    chart = compute_chart(local - timedelta(hours=5.5), 28.61, 77.21)
    return divisional.analyze(chart)


def _vidyarthi_snapshot():
    rep = compute_vidyarthi_report(name="Golden", dob="1990-03-21", tob="08:15",
                                   tz_offset_hours=5.5, lat=28.61, lon_geo=77.21,
                                   female=True, time_quality="T0", as_of=ASOF)
    return {"meta": rep["meta"], "chart": rep["chart"],
            "significators": rep["significators"], "current_period": rep["current_period"],
            "windows": rep["windows"], "teaser_moon": rep["teaser"]["moon_sign"]}


def _norm(obj):
    return json.loads(json.dumps(obj, sort_keys=True, default=str))


def test_marriage_report_matches_golden():
    golden = json.load(open(os.path.join(GOLDEN, "marriage_T0.json")))
    assert _norm(_marriage_snapshot()) == golden


def test_divisional_matches_golden():
    golden = json.load(open(os.path.join(GOLDEN, "divisional.json")))
    assert _norm(_divisional_snapshot()) == golden


def test_marriage_report_produces_windows():
    # Baseline sanity: the engine must always return at least one window (never-zero rule).
    assert len(_marriage_snapshot()["windows"]) >= 1


def test_marriage_windows_are_future_and_not_too_wide():
    # A marriage window must never start in the past (a still-running antardasha
    # legitimately began years ago, but showing that reads as a data error), and
    # must not span an implausibly long block (the old merge collapsed consecutive
    # ADs into a ~7-year window). Checked on BOTH genders — the engine branches on
    # `female` for significators (see tests/test_significators / CLAUDE.md §12).
    asof = datetime(2026, 9, 1)
    for female in (True, False):
        rep = compute_report(name="G", dob="1994-06-15", tob="10:30",
                             tz_offset_hours=5.5, lat=28.61, lon_geo=77.21,
                             female=female, time_quality="T0", as_of=asof)
        windows = rep["windows"]
        assert windows, f"no windows for female={female}"
        for w in windows:
            start = datetime.strptime(w["start"], "%Y-%m")
            end = datetime.strptime(w["end"], "%Y-%m")
            assert start.year >= asof.year, \
                f"window {w['start']}–{w['end']} starts in the past (female={female})"
            assert (end - start).days <= 365 * 4, \
                f"window {w['start']}–{w['end']} is implausibly long (female={female})"
        # the pre-payment teaser range must also start in the present or future
        tw = rep["teaser"]["first_window_teaser"]
        if tw and tw != "—":
            assert int(tw[:4]) >= asof.year, f"teaser {tw} starts in the past (female={female})"


def test_vidyarthi_matches_golden():
    golden = json.load(open(os.path.join(GOLDEN, "vidyarthi_T0.json")))
    assert _norm(_vidyarthi_snapshot()) == golden
