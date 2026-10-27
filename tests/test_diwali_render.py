"""RENDER-A unit tests: diwali_report.render_diwali with a stub bank and stub back cards.
Pure: no DB, no api.py. Run with --noconftest."""
import copy
import os
import re
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BACK_IDS = ["a-luck", None, "s-1-sadesati", "s-1-strengths", "s-1-slow", "s-1-months", None, "part-2",
            "s-2-1", "s-2-2", "s-2-3", "s-2-4", "s-2-5", "s-2-6", "e-1", "e-2", "e-3",
            "b-1", "b-2", "b-3", "b-4", "b-5", "b-6", "b-7"]


class _FakeBank(dict):
    def __missing__(self, k):
        return f"<{k}>"


def _stubs():
    bank = types.ModuleType("diwali_bank")
    bank.bank = lambda payload: _FakeBank()
    bank.has_best = lambda p: (p.get("meta") or {}).get("time_quality") not in ("T2", "T3")
    back = types.ModuleType("diwali_report_back")

    def cards_back(payload, prose):
        out = []
        for i, cid in enumerate(BACK_IDS):
            idattr = f' id="{cid}"' if cid else ""
            out.append(f'<section class="page"{idattr}><div class="col"><h2>{cid or "more"} {i}</h2>'
                       f'<a class="xr" href="#s-0-6">timeline, p.@@s-0-6@@</a></div><div class="pgn"></div></section>')
        return out
    back.cards_back = cards_back
    return bank, back


@pytest.fixture(autouse=True)
def _stub_modules(monkeypatch):
    """diwali_report imports diwali_bank / diwali_report_back lazily inside its functions, so swapping them in
    sys.modules per test is enough; monkeypatch puts the real modules back after each test (no leak into
    the other diwali test files when the suite runs in one session)."""
    bank, back = _stubs()
    monkeypatch.setitem(sys.modules, "diwali_bank", bank)
    monkeypatch.setitem(sys.modules, "diwali_report_back", back)


import diwali_report  # noqa: E402

YMS = [f"2026-{m:02d}" for m in (11, 12)] + [f"2027-{m:02d}" for m in range(1, 11)]
TONES = ["good", "steady", "careful", "careful", "careful", "careful", "steady", "best", "best", "good", "good", "good"]


def _area(prefix, n, picture=None):
    return {"state": "good",
            "windows": {"best": ["2027-06", "2027-07"], "good": ["2026-11", "2027-08"], "careful": ["2027-02", "2027-03"]},
            "topics": [{"key": f"{prefix}.t{i}", "state": ["good", "steady", "careful"][i % 3],
                        "when": ["best", "good", "careful", "steady"][i % 4], "months": [], "why": "fact"}
                       for i in range(1, n + 1)],
            "picture": picture or []}


def payload(gift=False, order=None, steering="money", work="business"):
    strands = [{"label": "Home life", "state": "good", "months_label": "Nov–Dec 26\nJul–Oct 27"},
               {"label": "Family talks", "state": "careful", "months_label": "Jan–Feb 27"},
               {"label": "Happy news", "state": "best", "months_label": "Jul–Oct 27"}]
    return {
        "product": "diwali",
        "meta": {"name": "Asha Verma", "first_name": "Asha", "dob": "1990-03-21", "tob": "18:05", "place": "Jaipur",
                 "gender": "female", "work_type": work, "steering": steering, "time_quality": "T0", "basis": "lagna",
                 "lang": "en", "variant": "/en/diwali", "age": 36, "age_band": "25_40", "as_of": "2026-11-08",
                 "span": "Nov 2026 – Oct 2027",
                 "gift": {"on": gift, "giver_name": "Ravi" if gift else "", "message": ""}},
        "chart": {"lagna": {"sign": "Cancer"}, "moon": {"sign": "Taurus", "nakshatra": "Rohini", "pada": 1},
                  "planets": [], "houses": {}},
        "months": [{"ym": ym, "label": ym, "year": int(ym[:4]), "tone": t, "care_reason": None, "transits": {}, "tags": []}
                   for ym, t in zip(YMS, TONES)],
        "area_order": order or ["money", "business", "family", "career", "marriage"],
        "first_reason": "picked" if steering else "situation",
        "scores": {"money": 2, "business": 2, "family": 1, "career": 0, "marriage": 1},
        "areas": {"money": _area("money", 7), "career": _area("career", 5), "business": _area("business", 5),
                  "family": _area("family", 5, strands), "marriage": _area("marriage", 5, strands[:2])},
        "money_extra": {"dhana_yoga": {"present": True}, "gold_months": ["2027-06", "2027-09"], "loan_months": ["2027-06", "2027-08"]},
        # engine shape (diwali.py): plain booleans, lagna_rule None when read from the Moon sign
        "marriage_extra": {"manglik": {"lagna_rule": True, "moon_rule": False,
                                       "cancelled": True, "reason": "Mars sits in its own sign."}},
        "lookback": {"good": ["2025-12", "2026-01", "2026-02"], "hard": ["2026-07", "2026-08"]},
        "timeline": [{"from": "2026-11", "to": "2027-01", "tone": "good", "theme": "A steady new start"},
                     {"from": "2027-02", "to": "2027-04", "tone": "careful", "theme": "Spend with care"},
                     {"from": "2027-05", "to": "2027-07", "tone": "best", "theme": "The turning point"},
                     {"from": "2027-08", "to": "2027-10", "tone": "good", "theme": "Growth with a steady hand"}],
        "best_time": {"from": "2027-06", "to": "2027-07"},
        "summary": {"best": {"from": "2027-06", "to": "2027-07", "label": "Jun–Jul 2027"},
                    "careful": [{"from": "2027-01", "to": "2027-04", "reason": "spending", "label": "Jan–Apr 2027"}],
                    "good_label": "Nov 2026, Aug–Oct 2027", "steady_label": "Dec 2026, May 2027"},
        "answers": [{"q": f"Question {i}?", "state": "good"} for i in range(1, 6)],
    }


DIALS = [{"left": "Job", "right": "Business", "value": 0.8, "why": "x"},     # engine shape (diwali.py)
         {"left": "Alone", "right": "Partner", "value": 0.62, "why": "y"}]


def _set_best(p, a, b):
    p["best_time"] = {"from": a, "to": b}
    p["summary"]["best"] = {"from": a, "to": b, "label": f"{a}–{b}"}


def ids(html):
    return re.findall(r'<section class="[^"]*"[^>]*\bid="([^"]+)"', html)


def cards(html):
    return re.findall(r'<section class="page', html)


def test_complete_doc_and_card_count_stable():
    h = diwali_report.render_diwali(payload())
    assert h.startswith("<!DOCTYPE html>") and h.rstrip().endswith("</html>")
    n = len(cards(h))
    assert n == len(cards(diwali_report.render_diwali(payload())))
    # front 8 + part1 1 + lookback 2 + back 24, plus the areas: openers + topic cards packed by estimated
    # height. The stub's one-word prose is short, so cards hold more topics than real prose would.
    area_cards = len(re.findall(r'class="eyebrow">[^<]* · \d+ of \d+<', h))
    assert n == 35 + 5 + area_cards, n
    assert len(ids(h)) == len(set(ids(h)))


def test_gift_page_only_when_on_and_note_moves():
    off, on = diwali_report.render_diwali(payload()), diwali_report.render_diwali(payload(gift=True))
    assert 'id="s-0-2"' not in off and 'id="s-0-2"' in on
    assert ids(off)[1] == "s-0-3" and ids(on)[1] == "s-0-2" and ids(on)[2] == "s-0-3"
    assert len(cards(on)) == len(cards(off)) + 1
    assert "From Ravi" in on and "A Diwali gift from Ravi" in on


def test_area_order_changes_card_order():
    a = ids(diwali_report.render_diwali(payload()))
    b = ids(diwali_report.render_diwali(payload(order=["marriage", "career", "money", "family", "business"], steering="marriage")))
    pos = lambda lst: [x for x in lst if x.startswith("a-") and x != "a-luck"]
    assert pos(a) == ["a-money", "a-business", "a-family", "a-career", "a-marriage"]
    assert pos(b) == ["a-marriage", "a-career", "a-money", "a-family", "a-business"]


def test_luck_picked_moves_better_luck_before_areas():
    h = diwali_report.render_diwali(payload(steering="luck"))
    i = ids(h)
    assert i.index("a-luck") < i.index("a-money")
    assert "You picked Better luck" in h


def test_every_link_resolves_and_no_placeholders():
    for p in (payload(), payload(gift=True), payload(steering=None, work="student")):
        h = diwali_report.render_diwali(p)
        have = set(ids(h))
        for target in re.findall(r'<a [^>]*href="#([^"]+)"', h):
            assert target in have, target
        assert "p.@@" not in h and "@@" not in h


def test_page_numbers_match_card_positions():
    h = diwali_report.render_diwali(payload(gift=True))
    order = {}
    for n, sec in enumerate(re.findall(r'<section class="[^"]*"[^>]*>', h), 1):
        m = re.search(r'id="([^"]+)"', sec)
        if m:
            order[m.group(1)] = n
    for cid, num in re.findall(r'<a class="xr[^"]*" href="#([^"]+)"><span>[^<]*</span><span>p\.(\d+)</span>', h):
        assert int(num) == order[cid], (cid, num)


def test_pictures_follow_payload_months():
    p = payload()
    for m in p["months"]:
        m["ym"] = m["ym"]  # same span
    h = diwali_report.render_diwali(p)
    assert "BEST: JUN–JUL" in h and "Jun–Jul 2027" in h
    p2 = copy.deepcopy(p)
    _set_best(p2, "2027-09", "2027-10")
    p2["timeline"][3]["tone"] = "best"
    h2 = diwali_report.render_diwali(p2)
    assert "BEST: SEP–OCT" in h2 and "Sep–Oct 2027" in h2


def test_no_persona_literals_in_source_and_karka():
    src = open(diwali_report.__file__, encoding="utf-8").read()
    assert "Vikram" not in src and "Priya" not in src
    h = diwali_report.render_diwali(payload())
    assert "Cancer" not in re.sub(r"<[^>]+>", " ", h) and diwali_report._sign("Cancer") == "Karka"


def test_user_text_is_escaped():
    p = payload(gift=True)
    p["meta"]["gift"]["message"] = "<script>alert(1)</script>"
    h = diwali_report.render_diwali(p)
    assert "<script>alert(1)" not in h and "&lt;script&gt;" in h


def _text(h):
    import html
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)))


def test_manglik_accepts_engine_booleans_and_none():
    p = payload()
    h = _text(diwali_report.render_diwali(p))
    assert "Rising-sign rule: By this rule, yes." in h and "Moon rule: By this rule, no." in h
    p["marriage_extra"]["manglik"]["lagna_rule"] = None
    assert "Rising-sign rule: Not used" in _text(diwali_report.render_diwali(p))


def _card_text(h, cid):
    i = h.find(f'id="{cid}"')
    return _text(h[i:h.find("</section>", i)])


def test_area_opener_uses_headline_and_one_position_line():
    h = diwali_report.render_diwali(payload())
    for a in ("money", "business", "family", "career", "marriage"):
        t = _card_text(h, "a-" + a)
        head = a != "career"   # business owner: mock 3C v2 a-career is a plain card, head = topic 1
        assert (f"<{a}.headline>" in t) == head and t.count(f"<{a}.opener>") == 1, t[:200]
    h = diwali_report.render_diwali(payload(work="job", steering="career"))
    t = _card_text(h, "a-career")
    assert "<career.headline>" in t and 'class="page ex"' in h[h.index('id="a-career"') - 30:h.index('id="a-career"')]


def test_mock3c_area_shapes():
    """Business owner: Business topic 1 on the dials opener; Career opener plain with topics 1-2 (mock 3C v2)."""
    p = payload()
    p["areas"]["business"]["dials"] = DIALS
    h = diwali_report.render_diwali(p)
    b = _card_text(h, "a-business")
    assert "two dials" in b and "<business.t1.what>" in b and "<business.t2.what>" not in b
    c = _card_text(h, "a-career")
    assert "<career.t1.what>" in c and "<career.t2.what>" in c and "<career.t3.what>" not in c
    assert "Business · 2 of" in h and "Career · 2 of" in h and "Business · 1 of" not in h


def test_diya_path_marks_follow_scores_not_every_best_month():
    p = payload()  # every area has best months; scores money/business=2 are the top
    marks = {a: diwali_report._mark(p["areas"][a], p["scores"][a], 2) for a in p["area_order"]}
    assert marks == {"money": "best", "business": "best", "family": "good", "career": "good", "marriage": "good"}
    heavy = {"state": "good", "windows": {"best": ["2027-01"], "good": ["2027-02"], "careful": ["2027-03", "2027-04", "2027-05"]}}
    assert diwali_report._mark(heavy, 2, 2) == "careful"
    # money, business + Better luck (best_time set)
    assert "and three burn brightest" in _card_text(diwali_report.render_diwali(p), "s-0-7")


def test_narrative_keys_reach_the_page():
    p = payload(steering=None)
    p["meta"]["basis"] = "moon"
    keys = ["lookback.from", "timeline.1", "timeline.4", "timeline.best", "note.order",
            "note.answers_intro", "note.less_precise", "note.helpline"]
    p["narrative"] = {k: f"NARR {k}" for k in keys}
    p["narrative"]["timeline.2"] = "Feb–Apr 2027 · Spend with care. NARR seg two"
    p["narrative"]["timeline.best"] = "Your single best time: NARR best"
    h = _text(diwali_report.render_diwali(p))
    for k in keys:
        if k != "timeline.best":
            assert f"NARR {k}" in h, k
    assert "NARR seg two" in h and "Spend with care. Feb–Apr 2027" not in h
    assert "Your single best time: NARR best" in h and "time: Your single" not in h


def _best_labels(h):
    i = h.find('id="s-0-6"')
    return re.findall(r">BEST: ([^<]+)<", h[i:h.find("</section>", i)])


def test_timeline_best_label_spans_quarters():
    p = payload()
    _set_best(p, "2026-12", "2027-01")
    assert _best_labels(diwali_report.render_diwali(p)) == ["DEC–JAN"]
    _set_best(p, "2027-01", "2027-02")
    assert _best_labels(diwali_report.render_diwali(p)) == ["JAN", "FEB"]


def test_business_dials_only_from_engine():
    p = payload()
    assert 'class="sp"' not in _card_text_raw(diwali_report.render_diwali(p), "a-business")
    p["areas"]["business"]["dials"] = DIALS
    t = _card_text_raw(diwali_report.render_diwali(p), "a-business")
    assert t.count('class="sp"') == 2 and "left:80%" in t and "left:62%" in t and "two dials" in t


def _card_text_raw(h, cid):
    i = h.find(f'id="{cid}"')
    return h[i:h.find("</section>", i)]


def test_no_doubled_labels():
    p = payload()
    p["narrative"] = {"glance.money": "Best time. Money grows.", "glance.luck": "Good time. Luck builds.",
                      "money.t7.title": "Your wealth combination: present"}
    h = _text(diwali_report.render_diwali(p))
    assert "present: present" not in h and "Your wealth combination: present" in h
    assert "Money · Best time. Money grows." in h and "Best time. Best time" not in h
    assert "Best time. Good time" not in h


def test_card_heads_name_the_bank_topics_for_every_work_type():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_real_bank", os.path.join(os.path.dirname(diwali_report.__file__), "diwali_bank.py"))
    rb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rb)
    titles = [t["title"] for t in rb.MONEY + rb.FAMILY + rb.MARRIAGE[:4]]  # marriage.t5 = the Manglik card, no head
    titles += [t["title"] for tbl in (rb.CAREER, rb.BUSINESS) for w in tbl for t in tbl[w]]
    missing = [t for t in titles if t not in diwali_report.SHORT and t.split(":")[0] not in diwali_report.SHORT]
    assert not missing, missing


def test_render_text_has_no_status_phrase():
    h = _text(diwali_report.render_diwali(payload(steering="marriage", order=["marriage", "career", "money", "family", "business"])))
    assert "your Marriage" not in h


def test_timeline_single_month_and_five_month_parts():
    p = payload()
    p["timeline"][0].update({"from": "2027-06", "to": "2027-06"})
    p["timeline"][1].update({"from": "2026-11", "to": "2027-03"})
    for ym in ("2026-11", "2026-12", "2027-01", "2027-02", "2027-03", "2027-06"):
        p["months"] = [m for m in p.get("months") or [] if m["ym"] != ym] + [{"ym": ym, "tone": "steady"}]
    h = diwali_report.render_diwali(p)
    i = h.find('id="s-0-6"')
    sec = h[i:h.find("</section>", i)]
    assert ">JUN<" in sec and "JUN–JUN" not in sec and "Jun–Jun" not in sec
    seg2 = re.search(r"NOV–MAR", sec)
    assert seg2
    for m in ("Nov", "Dec", "Jan", "Feb", "Mar"):
        assert m.upper() in sec or m in sec
    assert sec.count('cy="118"') >= 6  # 1 + 5 dots
