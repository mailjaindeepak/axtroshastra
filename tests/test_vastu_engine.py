"""Vastu Career Report engine: verdicts, rule B, validation, free-data-only teaser, vocabulary.

Spec: docs/vastu-career-report-spec.md sections 2, 3, 6. The direction matrix and number table under test are
WORKING DEFAULTS approved for the mock only (PENDING owner approval); these tests pin the logic, not the final cells.
"""
import itertools
import json
import re
from datetime import date

import pytest

import vastu_career as vc

TODAY = date(2026, 11, 20)
FLAGGED = (r"anxi", r"stress", r"depress", r"panic", r"trauma", r"therap", r"counsel", r"mental", r"well-?being", r"wellness",
           r"burn-?out", r"overwhelm", r"healing", r"\bheal\b", r"diagnos", r"symptom", r"disorder", r"treatment", r"\bcure\b",
           r"remedy", r"disease", r"illness", r"patient", r"clinical", r"medic", r"doctor", r"health", r"weight", r"\bdiet\b",
           r"\bcalm", r"relief", r"peace of mind")
DOB_FOR_NUMBER = {1: "2000-01-01", 2: "2000-01-02", 3: "2000-01-03", 4: "2000-01-04", 5: "2000-01-05",
                  6: "2000-01-06", 7: "2000-01-07", 8: "2000-01-08", 9: "2000-01-09"}


def run(segment="student", desk="E", flex="can_move", dob="2000-01-05", door=None, name="Test Person"):
    return vc.compute_vastu_career(name, dob, segment, desk, flex, door, today=TODAY)


# ---------------------------------------------------------------- verdicts from the matrix
@pytest.mark.parametrize("segment", vc.SEGMENTS)
@pytest.mark.parametrize("desk", vc.DIRECTIONS)
def test_every_segment_and_direction_gets_a_known_verdict(segment, desk):
    t = run(segment, desk)["teaser"]
    assert t["verdict"] in ("ideal", "acceptable", "change")
    cell = vc.MATRIX[segment]
    base = "ideal" if desk in cell["ideal"] else "acceptable" if desk in cell["acceptable"] else "change"
    if base == "acceptable":
        assert t["verdict"] in ("acceptable", "ideal")           # only rule B may lift it
    else:
        assert t["verdict"] == base                              # ideal stays ideal, change is never upgraded


def test_not_sure_gives_unknown_and_no_arrow():
    t = run("student", "not_sure")["teaser"]
    assert t["verdict"] == "unknown" and t["compass"]["desk"] is None and t["rule_b"] is False


# ---------------------------------------------------------------- rule B
def test_rule_b_upgrades_acceptable_when_the_desk_faces_the_number_direction():
    # professional: NE is acceptable; birth day 3 is Jupiter, whose direction is NE
    t = run("professional", "NE", dob=DOB_FOR_NUMBER[3])["teaser"]
    assert t["verdict"] == "ideal" and t["rule_b"] is True
    assert "birth number" in t["why"] and "acceptable" in t["why"]


def test_acceptable_stays_acceptable_when_the_number_points_elsewhere():
    t = run("professional", "NE", dob=DOB_FOR_NUMBER[5])["teaser"]           # Mercury, north
    assert t["verdict"] == "acceptable" and t["rule_b"] is False


def test_a_change_verdict_is_never_upgraded_even_if_the_number_agrees():
    # owner: west is change; Mulank 8 is Saturn, west
    t = run("owner", "W", dob=DOB_FOR_NUMBER[8])["teaser"]
    assert t["verdict"] == "change" and t["rule_b"] is False
    # mulank 9 is Mars, south: south is change for a student and must stay change
    assert run("student", "S", dob=DOB_FOR_NUMBER[9])["teaser"]["verdict"] == "change"


def test_ideal_is_not_changed_by_the_number_and_rule_b_is_not_reported():
    t = run("student", "N", dob=DOB_FOR_NUMBER[5])["teaser"]                 # north is ideal AND the number direction
    assert t["verdict"] == "ideal" and t["rule_b"] is False


def test_the_same_desk_can_differ_by_date_of_birth_only_through_rule_b():
    a = run("professional", "NE", dob=DOB_FOR_NUMBER[3])["teaser"]["verdict"]
    b = run("professional", "NE", dob=DOB_FOR_NUMBER[4])["teaser"]["verdict"]
    assert (a, b) == ("ideal", "acceptable")


# ---------------------------------------------------------------- numbers
def test_mulank_comes_from_the_birth_day_and_master_numbers_reduce():
    assert run(dob="2000-03-14")["teaser"]["number"]["mulank"] == 5
    assert run(dob="2000-03-29")["teaser"]["number"]["mulank"] == 2           # 2 + 9 = 11 -> 2 (numerology.py reduces masters)
    assert run(dob="2000-03-22")["teaser"]["number"]["mulank"] == 4


def test_mulank_seven_has_no_direction_and_says_so():
    n = run(dob=DOB_FOR_NUMBER[7])["teaser"]["number"]
    assert n["direction"] is None and "colour instead of a direction" in n["tip"]


def test_every_number_but_seven_has_a_direction_and_a_tip():
    for k, dob in DOB_FOR_NUMBER.items():
        n = run(dob=dob)["teaser"]["number"]
        assert n["mulank"] == k
        assert (n["direction"] is None) == (k == 7)
        assert n["tip"]


def test_south_tip_never_tells_anyone_to_face_south():
    n = run(dob=DOB_FOR_NUMBER[9])["teaser"]["number"]
    assert "not the way to face" in n["tip"]


# ---------------------------------------------------------------- the teaser carries free data only
def test_teaser_has_five_own_segment_questions_and_none_from_another():
    seen = {}
    for seg in vc.SEGMENTS:
        qs = [q["q"] for q in run(seg)["teaser"]["questions"]]
        assert len(qs) == 5 and len(set(qs)) == 5
        seen[seg] = set(qs)
    for a, b in itertools.combinations(vc.SEGMENTS, 2):
        assert not (seen[a] & seen[b]), (a, b)


def test_teaser_has_no_fixes_cards_or_colours():
    blob = json.dumps(run("owner", "W", "a_little", door="N")["teaser"]).lower()
    for k in ('"fixes"', '"cards"', '"colours"', '"colors"', '"colour"', '"remedies"', '"do"', '"dont"'):
        assert k not in blob
    assert "rental" not in blob and "hostel" not in blob


def test_door_direction_is_only_a_label_in_the_teaser():
    assert run(door="NE")["teaser"]["door_label"] == "North-East"
    assert run(door=None)["teaser"]["door_label"] == "Not given"
    assert run(door="not_sure")["teaser"]["door_label"] == "Not sure"


def test_flexibility_changes_the_wording_for_a_change_verdict_but_never_asks_to_move_a_fixed_desk():
    cannot = run("student", "S", "cannot_or_shared")["teaser"]
    assert "without moving the desk" in cannot["why"] and "seat, light and layout" in cannot["stand"]
    movable = run("student", "S", "can_move")["teaser"]
    assert "you can change it" in movable["stand"] and "without moving" not in movable["why"]


# ---------------------------------------------------------------- validation: explicit field errors, never a silent default
@pytest.mark.parametrize("kwargs,field", [
    (dict(name=""), "name"), (dict(name="x" * 61), "name"),
    (dict(dob="not-a-date"), "dob"), (dict(dob="2030-01-01"), "dob"), (dict(dob="1899-05-05"), "dob"), (dict(dob="2001-02-30"), "dob"),
    (dict(segment="astronaut"), "segment"), (dict(segment=""), "segment"),
    (dict(desk="up"), "desk_direction"), (dict(desk=None), "desk_direction"),
    (dict(flex="maybe"), "desk_flexibility"), (dict(flex=None), "desk_flexibility"),
    (dict(door="sideways"), "door_direction"),
])
def test_bad_input_raises_a_field_error(kwargs, field):
    with pytest.raises(vc.VastuInputError) as e:
        run(**kwargs)
    assert e.value.field == field and e.value.message


def test_name_is_trimmed_and_collapsed():
    assert run(name="  Asha   Rao ")["teaser"]["name"] == "Asha Rao"


# ---------------------------------------------------------------- vocabulary (Meta Health and Wellness, CLAUDE.md 5b)
def test_no_flagged_vocabulary_anywhere_in_visible_teaser_text_or_questions():
    texts = []
    for seg, desk, flex in itertools.product(vc.SEGMENTS, vc.DIR_OR_UNSURE, vc.FLEXIBILITY):
        for dob in DOB_FOR_NUMBER.values():
            t = run(seg, desk, flex, dob=dob)["teaser"]
            texts += [t["why"], t["stand"], t["number"]["tip"], t["verdict_label"], t["segment_label"]]
    for seg in vc.SEGMENTS:
        for q in vc.QUESTIONS[seg]:
            texts += list(q)
    for q in vc.STUDENT_Q1.values():
        texts += list(q)
    for tx in set(texts):
        for pat in FLAGGED:
            assert not re.search(pat, tx, re.I), (pat, tx)


def test_report_shape_for_save_report():
    r = run("job_seeker", "SE", "can_move", door="E")
    assert r["product"] == "vastu_career" and r["meta"]["segment"] == "job_seeker"
    assert r["meta"]["desk_direction"] == "SE" and r["meta"]["door_direction"] == "E"
    assert set(r) == {"product", "meta", "teaser"}


# ---------------------------------------------------------------- the approved Student question set (owner, 24 Nov 2026)
def _q(seg="student", desk="W", flex="a_little", dob="2000-03-14"):
    return [q["q"] for q in run(seg, desk, flex, dob=dob)["teaser"]["questions"]]


def test_student_question_one_follows_the_flexibility_and_the_verdict():
    assert _q(desk="W", flex="can_move")[0] == "Where exactly should your desk go?"
    assert _q(desk="W", flex="a_little")[0] == "How far, and which way, should you turn your desk?"
    assert _q(desk="W", flex="cannot_or_shared")[0] == "What can you fix without moving anything?"
    assert _q(desk="S", flex="cannot_or_shared")[0] == "What can you fix without moving anything?"        # change verdict, same flexibility
    assert _q(desk="E", flex="can_move")[0] == "What small habits keep a good desk working?"               # ideal overrides flexibility
    assert _q(desk="not_sure", flex="a_little")[0] == "What should you do about your desk?"


def test_student_questions_two_to_five_are_the_approved_ones():
    assert _q()[1:] == ["Is anything around your seat going against Vastu?",
                        "What can you change tonight, even in a hostel or shared room?",
                        "Which colours are linked with your study corner and your birth number?",
                        "Are any of your study habits on tradition's avoid list?"]


def test_no_locked_question_repeats_what_the_free_preview_already_answers():
    # the free preview shows the verdict, the first choices and the number's direction, so no locked question may ask for them
    for desk, flex in itertools.product(vc.DIR_OR_UNSURE, vc.FLEXIBILITY):
        for q in _q(desk=desk, flex=flex):
            low = q.lower()
            assert "facing the right way" not in low and "which way should you face" not in low, q
            assert "birth number point" not in low and "direction does your birth number" not in low, q


def test_other_segments_questions_are_unchanged_drafts():
    for seg in vc.SEGMENTS:
        if seg != "student":
            assert _q(seg, desk="N") == [q for q, _ in vc.QUESTIONS[seg]]
