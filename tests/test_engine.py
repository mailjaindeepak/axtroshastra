"""Engine tests: the astrology must be fully deterministic (no LLM, no randomness)."""
import json

from engine import compute_report

BIRTH = dict(name="Asha", dob="1995-08-15", tob="10:30",
             tz_offset_hours=5.5, lat=28.61, lon_geo=77.21,
             female=True, time_quality="T0")


def test_engine_is_deterministic():
    a = compute_report(**BIRTH)
    b = compute_report(**BIRTH)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_report_has_expected_shape():
    r = compute_report(**BIRTH)
    assert "meta" in r
    assert "teaser" in r
    assert r["meta"]["name"] == "Asha"
