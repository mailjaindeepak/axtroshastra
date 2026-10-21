"""Unit tests for the IQ test scoring engine (iq_test.py).

Scoring is deterministic — same inputs always produce the same output. These
tests verify shape, calibration, boundary conditions, and that the teaser
never leaks paid content.
"""
import pytest
from iq_test import compute_iq_report
from iq_test_questions import QUESTIONS, TOTAL_QUESTIONS


def _all_correct():
    return [q["correct"] for q in QUESTIONS]


def _all_wrong():
    return [(q["correct"] + 1) % 4 for q in QUESTIONS]


def _half_correct():
    ans = []
    for i, q in enumerate(QUESTIONS):
        ans.append(q["correct"] if i < 10 else (q["correct"] + 1) % 4)
    return ans


# ── report shape ─────────────────────────────────────────────────────────

def test_report_has_expected_shape():
    r = compute_iq_report("Priya", 25, "female", _all_correct(), 600)
    assert r["product"] == "iq_test"
    assert set(r.keys()) == {"product", "meta", "teaser", "scores", "profile"}
    assert set(r["teaser"].keys()) == {
        "iq_score", "classification", "percentile", "highlight_1", "highlight_2"}
    assert set(r["scores"].keys()) == {
        "raw", "total", "iq", "percentile", "classification",
        "time_taken_seconds", "age_adjustment", "time_bonus", "categories"}
    assert set(r["profile"].keys()) == {
        "cognitive_strengths", "areas_for_growth", "learning_style",
        "recommendations"}


def test_meta_fields():
    r = compute_iq_report("Arjun", 30, "male", _half_correct(), 700)
    assert r["meta"]["name"] == "Arjun"
    assert r["meta"]["age"] == 30
    assert r["meta"]["gender"] == "male"
    assert "generated" in r["meta"]


def test_gender_none_defaults_to_unspecified():
    r = compute_iq_report("Test", 25, None, _half_correct(), 600)
    assert r["meta"]["gender"] == "unspecified"


# ── teaser never leaks paid data ─────────────────────────────────────────

def test_teaser_does_not_leak_categories():
    r = compute_iq_report("Leaky", 25, "female", _all_correct(), 600)
    t = r["teaser"]
    assert "categories" not in t
    assert "cognitive_strengths" not in t
    assert "areas_for_growth" not in t
    assert "learning_style" not in t
    assert "recommendations" not in t


# ── calibration boundaries ───────────────────────────────────────────────

def test_all_correct_iq_above_140():
    r = compute_iq_report("Genius", 25, "male", _all_correct(), 500)
    assert r["scores"]["iq"] >= 140


def test_all_wrong_iq_below_80():
    r = compute_iq_report("Oops", 25, "male", _all_wrong(), 900)
    assert r["scores"]["iq"] < 80


def test_half_correct_iq_near_100():
    r = compute_iq_report("Average", 25, "male", _half_correct(), 700)
    iq = r["scores"]["iq"]
    assert 90 <= iq <= 115


def test_raw_score_counts():
    r = compute_iq_report("Count", 25, "male", _all_correct(), 600)
    assert r["scores"]["raw"] == TOTAL_QUESTIONS
    assert r["scores"]["total"] == TOTAL_QUESTIONS

    r2 = compute_iq_report("Count2", 25, "male", _all_wrong(), 600)
    assert r2["scores"]["raw"] == 0


# ── age adjustment ───────────────────────────────────────────────────────

def test_young_age_bonus():
    base = compute_iq_report("Base", 25, "male", _half_correct(), 800)
    young = compute_iq_report("Young", 18, "male", _half_correct(), 800)
    assert young["scores"]["age_adjustment"] == 2
    assert base["scores"]["age_adjustment"] == 0
    assert young["scores"]["iq"] == base["scores"]["iq"] + 2


def test_older_age_bonus():
    base = compute_iq_report("Base", 25, "male", _half_correct(), 800)
    older = compute_iq_report("Older", 55, "male", _half_correct(), 800)
    assert older["scores"]["age_adjustment"] == 1
    assert older["scores"]["iq"] == base["scores"]["iq"] + 1


# ── time bonus ───────────────────────────────────────────────────────────

def test_fast_time_bonus():
    slow = compute_iq_report("Slow", 25, "male", _half_correct(), 900)
    fast = compute_iq_report("Fast", 25, "male", _half_correct(), 500)
    assert fast["scores"]["time_bonus"] == 2
    assert slow["scores"]["time_bonus"] == 0
    assert fast["scores"]["iq"] == slow["scores"]["iq"] + 2


def test_medium_time_bonus():
    r = compute_iq_report("Medium", 25, "male", _half_correct(), 650)
    assert r["scores"]["time_bonus"] == 1


# ── category scores ──────────────────────────────────────────────────────

def test_categories_present():
    r = compute_iq_report("Cats", 25, "male", _all_correct(), 600)
    cats = r["scores"]["categories"]
    assert len(cats) == 4
    for cat, d in cats.items():
        assert set(d.keys()) == {"correct", "total", "pct", "label"}
        assert d["total"] == 5
        assert 0 <= d["pct"] <= 100


def test_all_correct_category_scores():
    r = compute_iq_report("Perfect", 25, "male", _all_correct(), 600)
    for cat, d in r["scores"]["categories"].items():
        assert d["correct"] == 5
        assert d["pct"] == 100


# ── percentile ───────────────────────────────────────────────────────────

def test_percentile_range():
    for ans_fn in [_all_correct, _all_wrong, _half_correct]:
        r = compute_iq_report("P", 25, "male", ans_fn(), 700)
        assert 1 <= r["scores"]["percentile"] <= 99


# ── classification ───────────────────────────────────────────────────────

def test_classification_labels():
    valid = {"Exceptional", "Superior", "Above Average", "Average", "Below Average"}
    for ans_fn in [_all_correct, _all_wrong, _half_correct]:
        r = compute_iq_report("C", 25, "male", ans_fn(), 700)
        assert r["scores"]["classification"] in valid


# ── profile content ──────────────────────────────────────────────────────

def test_profile_has_learning_style():
    r = compute_iq_report("Learner", 25, "male", _all_correct(), 600)
    ls = r["profile"]["learning_style"]
    assert "title" in ls
    assert "description" in ls


def test_profile_has_recommendations():
    r = compute_iq_report("Rec", 25, "male", _all_correct(), 600)
    recs = r["profile"]["recommendations"]
    assert len(recs) == 4
    for rec in recs:
        assert "category" in rec
        assert "text" in rec


# ── unanswered questions ─────────────────────────────────────────────────

def test_unanswered_treated_as_wrong():
    unanswered = [-1] * TOTAL_QUESTIONS
    r = compute_iq_report("Skip", 25, "male", unanswered, 600)
    assert r["scores"]["raw"] == 0


# ── determinism ──────────────────────────────────────────────────────────

def test_deterministic():
    a = compute_iq_report("Det", 28, "female", _half_correct(), 700)
    b = compute_iq_report("Det", 28, "female", _half_correct(), 700)
    assert a["scores"]["iq"] == b["scores"]["iq"]
    assert a["scores"]["categories"] == b["scores"]["categories"]
    assert a["teaser"] == b["teaser"]
