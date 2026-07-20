"""Unit tests for the /padhai student career & academic timing engine.
Mirrors tests/test_engine.py's shape for the marriage engine."""
from vidyarthi import compute_vidyarthi_report

BIRTH = dict(name="Test Student", dob="2008-08-15", tob="10:30",
             tz_offset_hours=5.5, lat=28.61, lon_geo=77.21,
             female=True, time_quality="T0")


def test_vidyarthi_is_deterministic():
    a = compute_vidyarthi_report(**BIRTH)
    b = compute_vidyarthi_report(**BIRTH)
    import json
    assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)


def test_report_has_expected_shape():
    r = compute_vidyarthi_report(**BIRTH)
    assert r["product"] == "vidyarthi"
    assert "meta" in r and "teaser" in r and "chart" in r and "windows" in r
    assert r["meta"]["name"] == "Test Student"
    assert "study_strength" in r["extras"]
    assert "career_direction" in r["extras"]


def test_windows_never_zero():
    # Same never-zero fallback rule as the marriage engine (engine.py:compute_report).
    r = compute_vidyarthi_report(**BIRTH)
    assert len(r["windows"]) >= 1


def test_teaser_never_leaks_full_report_fields():
    r = compute_vidyarthi_report(**BIRTH)
    assert "windows" not in r["teaser"]
    assert "extras" not in r["teaser"]
