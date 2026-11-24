"""Vastu Career Report: the paid 16-card report, its copy gate and its delivery plumbing.

Spec: docs/vastu-career-report-spec.md section 4. Copy: docs/vastu-career-copy-student.md (decision log H).
Only Student copy is approved, so every other segment must refuse to render and refuse to be bought.
"""
import itertools
import re
from html import unescape

import pytest

import vastu_career as vc
import vastu_career_report as vr

FLAGGED = (r"anxi", r"stress", r"depress", r"panic", r"trauma", r"therap", r"counsel", r"mental", r"well-?being", r"wellness",
           r"burn-?out", r"overwhelm", r"healing", r"\bheal\b", r"diagnos", r"symptom", r"disorder", r"treatment", r"\bcure\b",
           r"remedy", r"disease", r"illness", r"patient", r"clinical", r"medic", r"doctor", r"health", r"weight", r"\bdiet\b",
           r"\bcalm", r"relief", r"peace of mind")
# decision log H: these lines were CUT by the owner and must never come back without a source
CUT_LINES = ("sleeping direction", "head toward", "above your head", "nothing piled", "small plant", "Yours faces", "favours for an entrance",
             "tidy the north-east", "side of the desk you face", "books to the east or north")
PERSONAS = ("Asha", "Rohan", "Neha", "Karan", "Vikram", "Sana")
PHONES = iter(f"98765920{n:02d}" for n in range(1, 40))
DOB_FOR = {n: f"2000-01-{n:02d}" for n in range(1, 10)}


def report(desk="W", flex="a_little", dob="2000-03-14", door=None, name="Report Tester", segment="student"):
    return vc.compute_vastu_career(name, dob, segment, desk, flex, door)


def html_of(**kw):
    return vr.render_vastu_career(report(**kw))


def text_of(h):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S)
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", t)))


def pages_of(h):
    return re.findall(r'<section class="page[^"]*">.*?</section>', h, re.S)


def page_text(h, n):
    return text_of(pages_of(h)[n - 1])


# ---------------------------------------------------------------- structure
@pytest.mark.parametrize("desk,flex", list(itertools.product(vc.DIR_OR_UNSURE, vc.FLEXIBILITY)))
def test_every_student_combination_renders_exactly_16_cards(desk, flex):
    h = html_of(desk=desk, flex=flex)
    assert len(pages_of(h)) == 16
    assert [m for m in re.findall(r'<div class="pno">(\d+)</div>', h)] == [f"{i:02d}" for i in range(1, 17)]


def test_five_own_segment_cards_and_none_from_another_segment():
    h = html_of()
    heads = [re.search(r'<h2 class="head">(.*?)</h2>', pages_of(h)[i], re.S).group(1) for i in range(3, 8)]
    assert heads == [c[0] for c in vr.STUDENT["cards"]] and len(heads) == 5
    t = text_of(h)
    for seg in vc.SEGMENTS:
        if seg == "student":
            continue
        for q, _ in vc.QUESTIONS[seg]:
            assert q not in t, (seg, q)


def test_no_placeholder_left_unfilled_no_persona_no_sample_text():
    for desk, flex, dob in itertools.product(("W", "S", "E", "not_sure"), vc.FLEXIBILITY, DOB_FOR.values()):
        t = text_of(html_of(desk=desk, flex=flex, dob=dob))
        assert not re.search(r"\{[a-z_ ]+\}", t), t[:200]
        assert "None" not in t and "undefined" not in t
        for p in PERSONAS:
            assert p not in t, p


def test_buyer_name_is_escaped():
    h = html_of(name="<script>alert(1)</script> Rao")
    assert "<script>alert(1)" not in h and "&lt;script&gt;" in h


def test_other_segments_refuse_to_render():
    for seg in vc.SEGMENTS:
        if seg in vc.READY_SEGMENTS:
            continue
        with pytest.raises(vr.NotReady):
            vr.render_vastu_career(report(segment=seg, desk="N"))


def test_ready_segments_are_exactly_the_ones_with_approved_content():
    assert vc.READY_SEGMENTS == {"student", "exam_aspirant"} and set(vr.CONTENT) == set(vc.READY_SEGMENTS)


# ---------------------------------------------------------------- copy decisions (decision log H) and honesty
def test_cut_lines_never_appear():
    for desk, flex, door in itertools.product(("W", "S", "E", "SE", "not_sure"), vc.FLEXIBILITY, (None, "N", "SW")):
        t = text_of(html_of(desk=desk, flex=flex, door=door))
        for line in CUT_LINES:
            assert line.lower() not in t.lower(), (line, desk, flex)


def test_no_flagged_vocabulary_in_any_visible_text():
    for desk, flex, dob in itertools.product(vc.DIR_OR_UNSURE, vc.FLEXIBILITY, DOB_FOR.values()):
        t = text_of(html_of(desk=desk, flex=flex, dob=dob, door="N"))
        for pat in FLAGGED:
            assert not re.search(pat, t, re.I), (pat, desk, flex, dob)


def test_belief_system_and_no_guarantees():
    h = html_of()
    t = text_of(h)
    assert "belief system, not a forecast" in page_text(h, 2) and "not a prediction" in page_text(h, 16)
    assert not re.search(r"guarantee|will (get|score|earn|crack)|ensure(s)? (marks|success)", t, re.I)
    assert "Swiss" not in t and "ephemeris" not in t.lower() and "NASA" not in t


def test_numerology_pages_are_labelled_as_numerology_not_vastu():
    h = html_of()
    assert "comes from numerology, not from Vastu" in page_text(h, 14)
    assert "From your birth number" in page_text(h, 15)


# ---------------------------------------------------------------- the fixes follow the verdict and the flexibility
def test_a_buyer_who_cannot_move_the_desk_is_never_told_to_move_or_turn_it():
    for desk in ("W", "S", "SE", "SW", "NW"):
        t = page_text(html_of(desk=desk, flex="cannot_or_shared"), 10)
        assert not re.search(r"turn the (desk|chair)|move the desk to|free corner|another corner|Turn the", t, re.I), (desk, t)
        assert "solid" in t and "lamp" in t                                     # in-place fixes only, all from the research


def test_movable_and_turnable_desks_get_the_right_turn():
    assert "a quarter turn to the right" in page_text(html_of(desk="W", flex="a_little"), 10)
    assert "Turn the chair or the desk toward north" in page_text(html_of(desk="W", flex="a_little"), 10)
    assert "a quarter turn to the left" in page_text(html_of(desk="S", flex="a_little"), 10)
    assert "Turn the desk to face east" in page_text(html_of(desk="S", flex="can_move"), 10)
    assert "free corner" in page_text(html_of(desk="S", flex="can_move"), 10)


def test_ideal_desk_is_told_to_keep_it_and_not_to_move_anything():
    t = page_text(html_of(desk="E", flex="can_move"), 10)
    assert "Keep it, and look after it" in t and "nothing to move" in t and "Turn the" not in t


def test_not_sure_asks_for_a_compass_and_draws_no_arrow():
    h = html_of(desk="not_sure")
    assert "compass app" in page_text(h, 3) and "Check the direction first" in page_text(h, 10)
    assert 'stroke="#B4572B"' not in h and "Add your direction" in page_text(h, 13)


def test_every_fix_page_says_it_needs_no_change_to_walls_doors_or_windows():
    for desk, flex in itertools.product(vc.DIR_OR_UNSURE, vc.FLEXIBILITY):
        assert "without any change to walls, doors or windows" in page_text(html_of(desk=desk, flex=flex), 10)


def test_door_line_only_when_a_direction_was_given():
    assert "main door" in page_text(html_of(door="N"), 12)
    assert "main door" not in page_text(html_of(door=None), 12)
    assert "main door" not in page_text(html_of(door="not_sure"), 12)


def test_turn_clause_in_ten_minute_fixes_only_when_it_makes_sense():
    assert "Turn the chair toward north" in page_text(html_of(desk="W", flex="a_little"), 12)
    assert "Turn the chair" not in page_text(html_of(desk="W", flex="cannot_or_shared"), 12)
    assert "Turn the chair" not in page_text(html_of(desk="E", flex="can_move"), 12)


# ---------------------------------------------------------------- verdict, rule B and numbers on the pages
def test_page_3_matches_the_verdict():
    assert "Your result: Ideal" in page_text(html_of(desk="N"), 3)
    assert "Your result: Acceptable" in page_text(html_of(desk="W", dob=DOB_FOR[5]), 3)
    assert "Your result: Change advised" in page_text(html_of(desk="S"), 3)
    assert "South is the direction most often avoided" in page_text(html_of(desk="S"), 3)
    assert "South is the direction most often avoided" not in page_text(html_of(desk="SE"), 3)


def test_rule_b_on_pages_3_and_14():
    h = html_of(desk="W", dob=DOB_FOR[8])                 # Mulank 8 is Saturn, west: acceptable becomes ideal
    assert "Your result: Ideal" in page_text(h, 3) and "points the same way" in page_text(h, 3)
    assert "this report reads your desk as ideal" in page_text(h, 14)
    h2 = html_of(desk="W", dob=DOB_FOR[5])
    assert "does not change the verdict on page 3" in page_text(h2, 14)


def test_vastu_leads_when_the_number_direction_is_south():
    t = page_text(html_of(desk="E", dob=DOB_FOR[9]), 14)
    assert "Vastu leads" in t and "not for the way you face" in t


def test_mulank_seven_gives_no_direction_and_a_colour_page():
    h = html_of(dob=DOB_FOR[7])
    assert "does not guess one for you" in page_text(h, 14)
    assert "Numerology links birth number 7 with" in page_text(h, 15)


@pytest.mark.parametrize("n", range(1, 10))
def test_every_number_has_a_colour_page(n):
    t = page_text(html_of(dob=DOB_FOR[n]), 15)
    assert f"birth number {n}" in t and vr.NUM_COLOURS[n][0] in t
    assert ("Strong colours stay small" in t) == (n in (1, 9))


# ---------------------------------------------------------------- shell: delivery plumbing and PDF
def test_report_has_a_pdf_button_and_no_whatsapp_share_button():
    # owner decision (24 Nov 2026): no "Share on WhatsApp" option on this report. WhatsApp DELIVERY of the report is unaffected.
    h = html_of()
    assert "window.print();return false;" in h and "id='ax-pdf'" in h
    assert "Share on WhatsApp" not in h and "axShare" not in h and "wa.me" not in h
    assert "@media print{#ax-stickybar{display:none!important}}" in h


def _create(client, **kw):
    body = {"name": "Paid Tester", "dob": "2000-03-14", "segment": "student", "desk_direction": "W",
            "desk_flexibility": "a_little", "door_direction": "N", "phone": next(PHONES)}
    body.update(kw)
    r = client.post("/api/vastu-career", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_preview_says_ready_only_for_approved_segments(client):
    assert _create(client)["teaser"]["ready"] is True
    assert _create(client, segment="exam_aspirant", desk_direction="S")["teaser"]["ready"] is True
    assert _create(client, segment="owner", desk_direction="W")["teaser"]["ready"] is False


def test_unpaid_report_is_not_served(client):
    rid = _create(client)["report_id"]
    assert client.get(f"/report/{rid}").status_code == 404


def test_paid_student_report_is_served_with_wired_buttons(client):
    rid = _create(client)["report_id"]
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    page = client.get(f"/report/{rid}")
    assert page.status_code == 200
    h = page.text
    assert len(pages_of(h)) == 16
    assert "axPdfDl" in h and "window.print();return false;" not in h        # the server wired the PDF button
    assert "Share on WhatsApp" not in h and "wa.me" not in h                   # owner dropped the share option
    assert "Disclaimer" not in text_of(h) and "ax-report-disclaimer" not in h  # and the shared legal box
    assert "Paid Tester" in text_of(h) and "Vastu Career Report" in h


def test_an_unapproved_segment_cannot_be_ordered(client):
    rid = _create(client, segment="professional", desk_direction="NE")["report_id"]
    r = client.post("/api/order", json={"report_id": rid, "phone": "+919876592099"})
    assert r.status_code == 409 and r.json()["detail"] == "not_available"


def test_an_approved_segment_gets_past_the_gate(client):
    rid = _create(client)["report_id"]
    r = client.post("/api/order", json={"report_id": rid, "phone": "+919876592098"})
    assert r.status_code != 409                      # it may fail later for lack of payment keys in tests, but never at the gate


def test_pdf_is_16_pages_at_323_by_623_when_chrome_is_available():
    fitz = pytest.importorskip("fitz")
    import pdfgen
    data = pdfgen.generate(html_of(desk="S", flex="cannot_or_shared", door="E"))
    if not data:
        pytest.skip("headless Chrome is not available here")
    doc = fitz.open(stream=data, filetype="pdf")
    assert len(doc) == 16
    assert {(round(p.rect.width), round(p.rect.height)) for p in doc} == {(323, 623)}


# ---------------------------------------------------------------- every Student question is answered in the paid pages (owner-approved set)
def test_student_questions_match_what_the_paid_pages_deliver():
    for flex, q1, p10 in (("can_move", "Where exactly should your desk go?", "Turn the desk to face"),
                          ("a_little", "How far, and which way, should you turn your desk?", "a quarter turn to the right"),
                          ("cannot_or_shared", "What can you fix without moving anything?", "works where it is")):
        rep = report(desk="W", flex=flex)
        assert rep["teaser"]["questions"][0]["q"] == q1
        assert p10 in page_text(vr.render_vastu_career(rep), 10)
    h = html_of(desk="W", flex="a_little")
    assert "hostel" in page_text(h, 11) and "Ten-minute fixes" in page_text(h, 12)           # question 3
    assert "wall behind you" in page_text(h, 5).lower() and "beam" in page_text(h, 5)       # question 2
    assert "Light green" in page_text(h, 6) and "birth number" in page_text(h, 15)          # question 4
    assert "bed" in page_text(h, 7) and "mirror" in page_text(h, 7)                         # question 5
    e = html_of(desk="E", flex="can_move")
    assert "look after it" in page_text(e, 10)                                              # the "good desk" variant


# ---------------------------------------------------------------- Exam aspirant (copy approved as written, 24 Nov 2026)
ASP = "exam_aspirant"


@pytest.mark.parametrize("desk,flex", list(itertools.product(vc.DIR_OR_UNSURE, vc.FLEXIBILITY)))
def test_every_aspirant_combination_renders_exactly_16_cards(desk, flex):
    h = html_of(segment=ASP, desk=desk, flex=flex)
    assert len(pages_of(h)) == 16
    assert re.findall(r'<div class="pno">(\d+)</div>', h) == [f"{i:02d}" for i in range(1, 17)]


def test_aspirant_has_its_own_five_cards_and_none_of_the_students():
    h = html_of(segment=ASP)
    heads = [re.search(r'<h2 class="head">(.*?)</h2>', pages_of(h)[i], re.S).group(1) for i in range(3, 8)]
    assert heads == [c[0] for c in vr.EXAM_ASPIRANT["cards"]]
    for c in vr.STUDENT["cards"]:
        assert c[0] not in text_of(h), c[0]
    st = text_of(html_of())
    for c in vr.EXAM_ASPIRANT["cards"]:
        assert c[0] not in st, c[0]


def test_aspirant_copy_is_the_approved_text_and_uses_the_segment_words():
    h = html_of(segment=ASP, desk="W", flex="a_little", door="N")
    assert "Exam aspirant" in page_text(h, 1) and "long study hours" in page_text(h, 1)
    assert "long study" in page_text(h, 3) and "tied to competitive tests" in page_text(h, 3)
    assert "Put tomorrow's first topic on top" in page_text(h, 12) and "Leave your phone on the desk" in page_text(h, 12)
    assert "Phone away from the desk" in page_text(h, 7) and "Your back to the door" in page_text(h, 8)
    assert "Hostel, PG or shared room" in page_text(h, 11)
    assert "One notebook for each subject" in page_text(h, 9)


def test_aspirant_page_15_has_no_dangling_page_reference():
    # the aspirant cards have no colours page, so the Student's "(page 6)" pointer must not appear
    t = page_text(html_of(segment=ASP, dob=DOB_FOR[4]), 15)
    assert "light colours on the walls." in t and "(page 6)" not in t
    assert "(page 6)" in page_text(html_of(dob=DOB_FOR[4]), 15)


def test_aspirant_cut_lines_and_vocabulary():
    for desk, flex, door in itertools.product(("W", "S", "E", "not_sure"), vc.FLEXIBILITY, (None, "N")):
        t = text_of(html_of(segment=ASP, desk=desk, flex=flex, door=door))
        for line in CUT_LINES:
            assert line.lower() not in t.lower(), (line, desk, flex)
        for pat in FLAGGED:
            assert not re.search(pat, t, re.I), (pat, desk, flex)
        assert not re.search(r"\{[a-z_ ]+\}", t)
        for p in PERSONAS:
            assert p not in t


def test_aspirant_who_cannot_move_the_desk_is_never_told_to_move_it():
    for desk in ("W", "S", "SE", "SW", "NW"):
        t = page_text(html_of(segment=ASP, desk=desk, flex="cannot_or_shared"), 10)
        assert not re.search(r"Turn the|free corner|another corner", t), (desk, t)
        assert "works where it is" in t
    assert "a quarter turn to the left" in page_text(html_of(segment=ASP, desk="S", flex="a_little"), 10)


def test_aspirant_is_orderable_and_the_rest_still_are_not(client):
    rid = _create(client, segment=ASP, desk_direction="S")["report_id"]
    assert client.post("/api/order", json={"report_id": rid, "phone": "+919876592097"}).status_code != 409
    for seg in ("professional", "wfh", "owner", "job_seeker"):
        rid = _create(client, segment=seg, desk_direction="NE")["report_id"]
        assert client.post("/api/order", json={"report_id": rid, "phone": "+919876592096"}).status_code == 409, seg


def test_paid_aspirant_report_is_served(client):
    rid = _create(client, segment=ASP, desk_direction="S", desk_flexibility="cannot_or_shared")["report_id"]
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    h = client.get(f"/report/{rid}").text
    assert len(pages_of(h)) == 16 and "Exam aspirant" in text_of(h) and "axPdfDl" in h and "Share on WhatsApp" not in h
