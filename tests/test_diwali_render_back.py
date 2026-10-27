"""RENDER-B: diwali_report_back.cards_back. Pure test, no DB, no api import."""
import copy
import re

import pytest

import diwali_report_back as rb

YMS = [f"2026-{m:02d}" for m in (11, 12)] + [f"2027-{m:02d}" for m in range(1, 11)]
TONES = ["good", "best", "careful", "careful", "steady", "good", "best", "good", "steady", "careful", "good", "best"]
REASONS = [None, None, "spending", "spending", None, None, None, None, None, "reactions", None, None]


def _payload():
    months = [{"ym": ym, "label": rb.MON[int(ym[5:]) - 1], "year": int(ym[:4]), "tone": t, "care_reason": r,
               "transits": {}, "tags": []} for ym, t, r in zip(YMS, TONES, REASONS)]
    signs = ["Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces", "Aries", "Taurus",
             "Gemini", "Cancer", "Leo"]
    lords = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter", "Mars", "Venus", "Mercury", "Moon", "Sun"]
    planets = [{"name": n, "sign": s, "house": h, "dignity": "neutral", "retro": n in ("Rahu", "Ketu", "Saturn"),
                "nakshatra": "Hasta"} for n, s, h in [
        ("Sun", "Cancer", 11), ("Moon", "Virgo", 1), ("Mars", "Aries", 8), ("Mercury", "Leo", 12),
        ("Jupiter", "Pisces", 7), ("Venus", "Gemini", 10), ("Saturn", "Capricorn", 5), ("Rahu", "Taurus", 9),
        ("Ketu", "Scorpio", 3)]]
    return {
        "product": "diwali",
        "meta": {"name": "Meera Iyer", "first_name": "Meera", "dob": "1990-02-03", "tob": "10:15", "place": "Chennai",
                 "gender": "female", "work_type": "job", "steering": None, "time_quality": "T0", "basis": "lagna",
                 "lang": "en", "variant": "/en/diwali", "age": 36, "age_band": "25_40", "as_of": "2026-11-08",
                 "span": "Nov 2026 – Oct 2027", "gift": {"on": False, "giver_name": "", "message": ""}},
        "chart": {"lagna": {"sign": "Virgo"}, "moon": {"sign": "Virgo", "nakshatra": "Hasta", "pada": 3},
                  "planets": planets,
                  "houses": {str(i + 1): {"sign": signs[i], "lord": lords[i]} for i in range(12)}},
        "period": {"md": "Venus", "ad": "Saturn", "ad_end": "2027-05", "next_ad": {"lord": "Mercury", "from": "2027-05"},
                   "turning_points": [{"ym": "2026-12", "kind": "ad"}, {"ym": "2027-05", "kind": "transit"}]},
        "sade_sati": {"active": True, "phase": "rising",
                      "phases": [{"phase": "rising", "from": "2025-03", "to": "2027-03"},
                                 {"phase": "rising", "from": "2027-08", "to": "2028-06"}]},
        "months": months,
        "area_order": ["career", "money", "family", "marriage", "business"], "first_reason": "situation",
        "scores": {"career": 1}, "areas": {"career": {"windows": {"best": ["2026-12"]}}},
        "money_extra": {"dhana_yoga": {"present": False}, "gold_months": ["2026-11", "2027-07"], "loan_months": []},
        "strengths": [{"planet": "Jupiter", "sign": "Pisces", "house": 7, "dignity": "own"}] * 3,
        "luck": {"bright_spots": [{"area": a, "fact": "x"} for a in ["money", "career", "business", "family", "marriage"]],
                 "ninth": {"sign": "Taurus", "lord": "Venus"}},
        "best_time": {"from": "2026-12", "to": "2026-12"},
        # engine shape (diwali._summary): built from the month tones above
        "summary": {"best": {"from": "2026-12", "to": "2026-12", "label": "Dec 2026"},
                    "careful": [{"from": "2027-01", "to": "2027-02", "reason": "spending", "label": "Jan–Feb 2027"},
                                {"from": "2027-08", "to": "2027-08", "reason": "reactions", "label": "Aug 2027"}],
                    "good_label": "Nov 2026, Apr 2027, Jun 2027, Sep 2027", "steady_label": "Mar 2027, Jul 2027"},
        "diwali": {"days": [{"name": n, "date": d} for n, d in [("Dhanteras", "Fri 6 Nov"), ("Kali Chaudas", "Sat 7 Nov"),
                                                              ("Lakshmi Puja", "Sun 8 Nov"), ("Govardhan", "Tue 10 Nov"),
                                                              ("Bhai Dooj", "Wed 11 Nov")]],
                   "puja_times": [{"city": c, "start": "6:00", "end": "8:00 pm", "source": "test"} for c in
                                  ["Delhi", "Mumbai", "Bengaluru", "Chennai", "Ahmedabad", "Kolkata", "Pune", "Hyderabad", "Jaipur"]]},
        "wrapped": {"strongest_area": "career", "best": {"from": "2026-12", "to": "2026-12"},
                    "careful": {"from": "2027-01", "to": "2027-02"}, "move": "Plan in winter, act in spring.",
                    "words": [{"word": "focused", "line": "a"}, {"word": "patient", "line": "b"}, {"word": "bright", "line": "c"}]},
    }


stub = lambda k: f"<{k}>"


def _ids(cards):
    return [m.group(1) if m else None for m in (re.match(r'<section class="[^"]*"[^>]*\bid="([^"]+)"', c) for c in cards)]


def test_card_list_and_ids():
    cards = rb.cards_back(_payload(), stub)
    assert len(cards) == 28
    assert all(c.startswith('<section class="page') and c.endswith("</section>") for c in cards)
    assert all(c.count("<section") == 1 for c in cards)
    assert _ids(cards) == ["a-luck", None, "s-1-sadesati", None, "s-1-strengths", "s-1-slow", "s-1-months", None,
                           "part-2", "s-2-1", "s-2-2", "s-2-3", "s-2-4", "s-2-5", "s-2-6", None,
                           "e-1", "e-2", "e-3", "b-1", "b-2", "b-3", "b-4", None, "b-5", None, "b-6", "b-7"]


def test_page_refs_are_placeholders_for_real_ids():
    html = "".join(rb.cards_back(_payload(), stub))
    refs = set(re.findall(r"p\.@@([\w-]+)@@", html))
    assert refs and refs <= set(_ids(rb.cards_back(_payload(), stub))) | {"s-0-6"}
    assert not re.search(r"\bp\.\d", html)


def test_prose_is_escaped_and_used():
    html = "".join(rb.cards_back(_payload(), stub))
    assert "&lt;luck.headline&gt;" in html and "&lt;months.2027-03.do&gt;" in html and "&lt;takeaways.5&gt;" in html
    assert "<luck.headline>" not in html


def test_months_tally_sums_to_12():
    p = _payload()
    t = rb.tally(p["months"], p["summary"])
    assert sum(n for _, _, n, _ in t) == 12
    assert [n for _, _, n, _ in t] == [3, 4, 2, 3]
    assert [x for _, _, _, x in t] == ["Dec · May · Oct", "Nov · Apr · Jun · Sep", "Mar · Jul", "Jan–Feb · Aug"]
    html = rb.months_cards(p, stub)[1]
    nums = [int(x) for x in re.findall(r'<div class="(?:best|good|steady|care)"><b>(\d+)</b>', html)]
    assert sum(nums) == 12
    assert "Jan–Feb" in html  # careful run in the tally box


def test_tally_note_text():
    p = _payload()
    assert rb.tally_note(p["months"], p["summary"]) == ("Careful for spending in Jan–Feb 2027 and for quick reactions in "
                                                       "Aug 2027, easier from Sep 2027.")


def test_slow_card_and_tally_read_summary_not_month_reasons():
    """One careful run whose months carry two reasons: summary says one careful time (spending)."""
    p = _payload()
    p["summary"]["careful"] = [{"from": "2027-01", "to": "2027-02", "reason": "spending", "label": "Jan–Feb 2027"}]
    card = rb.slow_card(p, stub)
    assert "One careful time" in card and "slow.reactions" not in card and "slow.spending.title" in card
    assert rb.tally_note(p["months"], p["summary"]) == "Careful for spending in Jan–Feb 2027, easier from Mar 2027."


def test_kandil_states_follow_months():
    cards = rb.months_cards(_payload(), stub)
    a, b = cards
    # first half: 1 best (Dec), 2 careful (Jan, Feb), 3 good/steady
    assert a.count(">Best time</text>") == 1 and a.count(">Careful time</text>") == 2
    assert a.count('id="a4halo"') == 1 and 'id="a4halo"' not in b
    assert a.count("<tr><td>") == 6 and b.count("<tr><td>") == 6
    assert "Nov 2026 – Apr 2027:" in a and "May – Oct 2027:" in b


def test_gold_diyas():
    html = rb.part2_cards(_payload(), stub)[3]
    assert html.count("BEST FOR GOLD</text>") == 2
    assert html.count("BEST OVERALL</text>") == 3  # Dec 2026, May 2027, Oct 2027: best but not gold
    assert "Two months shine for gold" in html


def test_sadesati_segments_with_pause_and_return():
    p = _payload()
    segs, _ = rb.ss_segments(p["sade_sati"], "2026-11")
    assert [s[0] for s in segs] == ["rising", "pause", "return"]
    assert segs[1][1:] == ("2027-04", "2027-07")
    html = rb.sadesati_cards(p, stub)[0]
    assert "FIRST PHASE" in html and "PAUSE" in html and "SHORT RETURN" in html
    off = dict(p["sade_sati"], active=False, phases=[])
    assert rb.ss_segments(off, "2026-11")[0][0][0] == "none"


def test_luck_stays_in_when_picked():
    p = _payload()
    p["meta"]["steering"] = "luck"
    p["first_reason"] = "picked"
    cards = rb.cards_back(p, stub)
    assert _ids(cards)[0] == "a-luck" and len(cards) == 28  # render_diwali lifts it to the top
    assert "Three fresh-start plans" in "".join(cards) and "You picked Better luck" in "".join(cards)


def test_turning_point_label_not_doubled():
    html = rb.luck_cards(_payload(), lambda k: "First turning point. Growth comes." if k.startswith("luck.turning") else k)[0]
    assert "<b>First turning point.</b> Growth comes." in html and html.count("turning point.") == 2


def test_blessing_uses_bank_keys():
    html = rb.part2_cards(_payload(), stub)[6]
    assert "&lt;blessing.title&gt;" in html and "&lt;blessing.text&gt;" in html and "— &lt;blessing.sign&gt;" in html


def test_no_careful_month_card_and_tally_agree():
    p = _payload()
    for m in p["months"]:
        if m["tone"] == "careful":
            m["tone"], m["care_reason"] = "steady", None
    p["summary"]["careful"] = []
    card = rb.slow_card(p, stub)
    assert "No careful time" in card and "One careful time" not in card and "slow." not in card
    assert "your best time finds you ready" in card
    assert rb.tally_note(p["months"], p["summary"]).startswith("No careful month")
    p["meta"]["time_quality"] = "T3"                     # spec §2 rule 10: no best time for T2/T3
    assert "best time" not in rb.slow_card(p, stub).lower()


def test_wrapped_careful_none():
    p = _payload()
    p["summary"]["careful"] = []
    html = rb.part2_cards(p, stub)[7]
    assert '<div class="wl">Careful time</div><b>Clear</b>' in html and '>None<' not in html


def test_sadesati_soon_not_called_off():
    p = _payload()
    p["sade_sati"] = {"active": False, "phase": None, "phases": [{"phase": "rising", "from": "2027-06", "to": "2027-10"},
                                                                 {"phase": "rising", "from": "2028-03", "to": "2029-07"}]}
    assert rb.ss_status(p) == "soon"
    html = "".join(rb.cards_back(p, stub))
    assert "You are not in it" not in html and "Yours begins before next Diwali." in html
    assert "Free steps for when it begins" in html


def test_sadesati_back_and_forth_is_return():
    ph = [{"phase": "rising", "from": "2025-04", "to": "2027-05"}, {"phase": "peak", "from": "2027-06", "to": "2027-10"},
          {"phase": "rising", "from": "2027-11", "to": "2028-02"}, {"phase": "peak", "from": "2028-03", "to": "2029-07"}]
    segs, idx = rb.ss_segments({"active": True, "phases": ph}, "2026-11")
    assert [s[0] for s in segs] == ["rising", "peak", "return", "peak"]
    svg = rb.sadesati_svg(segs, idx)
    # pill labels fit their pills; month labels stay on canvas and never overlap on a row
    for m in re.finditer(r'<rect x="([\d.]+)" y="58" width="([\d.]+)".*?\n(?:<text x="([\d.]+)" y="74"[^>]*>([^<]+)<)?', svg):
        if m.group(4):
            assert rb.ss_text_w(m.group(4)) + 10 <= float(m.group(2))
    rows = {}
    for x, y, t in re.findall(r'<text x="([\d.]+)" y="(100|114)" class="ml">([^<]+)<', svg):
        l, r = float(x), float(x) + len(t) * 5.4
        assert 0 <= l and r <= 373
        assert all(r + 6 <= a or l >= b + 6 for a, b in rows.get(y, []))
        rows.setdefault(y, []).append((l, r))
    assert "till Jul 2029" in svg


@pytest.mark.parametrize("dob,tob,gender,work,steer,gift", [
    ("1990-02-03", "10:15", "male", "job", None, False),
    ("1985-07-21", "04:40", "female", "business", "luck", True),
    ("2001-11-30", "22:05", "female", "home", "marriage", False),
    ("1972-03-14", "13:30", "male", "student", "money", True)])
def test_real_payload_every_key_in_bank(dob, tob, gender, work, steer, gift):
    """The real engine + the real bank: every key the renderer asks for exists (no stub)."""
    import diwali
    import diwali_bank
    p = diwali.compute_diwali("Asha Rao", dob, tob, 5.5, 13.08, 80.27, place="Chennai", gender=gender,
                              work_type=work, steering=steer, gift_on=gift)
    bank = diwali_bank.bank(p)
    assert [k for k in rb.back_keys(p) if k not in bank] == []
    html = "".join(rb.cards_back(p, lambda k: bank[k]))
    assert 'id="a-luck"' in html and "Asha" in html
    for w in ["Vikram", "Priya"]:
        assert w not in html


def test_chart_back_pages_from_payload():
    html = "".join(rb.back_cards(_payload(), stub))
    assert "Thank you, Meera" in html and "<b>Meera</b>" in html
    assert "Karka" in html and "Cancer" not in html
    assert "Sa R</span>" in html and "Ra R</span>" not in html
    assert "Yours: Venus, with a Saturn sub-period, moving to a Mercury sub-period before next Diwali." in html
    assert "Yours is in its first phase." in html
    assert html.count("<tr><td><b>") == 9 + 12


def test_no_persona_or_banned_strings():
    src = open(rb.__file__).read()
    p = _payload()
    html = "".join(rb.cards_back(p, stub))
    for w in ["Vikram", "Priya", "Purva Bhadrapada", "Mercury, with a Jupiter", "p.37"]:
        assert w not in src and w not in html, w
    assert "Pune" not in src  # the city name only reaches a report via payload puja_times
    text = re.sub(r"<style.*?</style>|<svg.*?</svg>|<[^>]+>", " ", html, flags=re.S).lower()
    for w in ["stretch", "window", "cancer", "astrosage", "guarantee", "dosha", "remed"]:
        assert w not in text, w


def test_back_keys_lists_every_prose_call():
    keys = rb.back_keys(_payload())
    assert "luck.headline" in keys and "months.2026-11.do" in keys and "takeaways.1" in keys
    assert len(keys) == len(set(keys))


def test_does_not_mutate_payload():
    p = _payload()
    before = copy.deepcopy(p)
    rb.cards_back(p, stub)
    assert p == before


def test_wrapped_words_come_from_prose():
    p = _payload()
    pr = lambda k: "ZEBRAWORD: zebra line\nQUOKKA: q\nYAK: y" if k == "wrapped.words" else stub(k)
    html = rb.part2_cards(p, pr)[7]
    assert "<b>ZEBRAWORD</b><span>zebra line</span>" in html and "<b>YAK</b>" in html
    assert "wrapped.words" in rb.back_keys(p)


def test_wrapped_words_fallback_and_banned_word():
    p = _payload()
    p["wrapped"]["words"] = [{"word": "rising", "line": "a"}, {"word": "PATIENT", "line": "b"}, {"word": "x", "line": "c"}]
    html = rb.part2_cards(p, stub)[7]  # stub '<wrapped.words>' has no 'WORD: line' rows → payload words
    assert "<b>RISING</b>" in html and "PATIENT" not in html and "<b>STEADY</b>" in html
    assert [r["word"] for r in rb.wrapped_words("A: 1\nPATIENT: 2\nCALM: 3", [])] == ["A", "STEADY", "READY"]
    assert [r["word"] for r in rb.wrapped_words("STEADY: 1\nCALM: 2\nC: 3", [])] == ["STEADY", "READY", "C"]


def test_wrapped_tiles_from_summary():
    p = _payload()
    p["wrapped"]["best"] = {"from": "2027-09", "to": "2027-09"}      # stale wrapped ranges are ignored
    html = rb.part2_cards(p, stub)[7]
    assert '<div class="wl">Best time</div><b>Dec</b><span class="y">2026</span>' in html
    assert '<div class="wl">Careful time</div><b>Jan–Feb</b><span class="y">2027</span>' in html


def test_half_headline_names_how_the_half_ends():
    """A half that ends on good months never reads 'then go carefully' (verifier, v03)."""
    T = {"s": "steady", "g": "good", "c": "careful", "b": "best"}
    hh = lambda s: rb.half_headline([{"tone": T[c]} for c in s])
    assert hh("sscggg") == "a steady start, a careful patch, then good months."
    assert hh("gggggc") == "a good start, then go carefully."
    assert hh("gcgggg") == "a good start, a careful patch, then good again."
    assert hh("ssssss") == "steady all through."


def test_slow_card_box_covering_two_runs_says_so():
    """Heading counts summary runs; one spending box over two runs says 'both times' (no dates on this card)."""
    p = _payload()
    p["summary"]["careful"] = [{"from": "2027-01", "to": "2027-01", "reason": "spending", "label": "Jan 2027"},
                               {"from": "2027-07", "to": "2027-10", "reason": "spending", "label": "Jul–Oct 2027"}]
    card = rb.slow_card(p, stub)
    assert "Two careful times" in card and card.count('class="win"') == 1 and "slow.spending.title&gt;, both times" in card
    assert "2027" not in card
