"""Hindi (Devanagari) report leakage guards.

The owner's bug: English/Hinglish text leaking into the HINDI reports. Three
defence layers are tested here:

1. COMPOSE-TIME — report_view_v2 builds every deterministic *_bank fallback in
   Devanagari when meta.lang == 'hi' (the banks are interpolated f-strings the
   exact-match localizer can never translate after render).
2. LOCALIZE-TIME — shaadi_hi/milan_hi translate the fixed shell, incl. the
   structural strings that used to slip through (mantras, gem advisories,
   Sade Sati composite, multi-antardasha labels, the cover method note...).
3. SERVE-TIME — the report chrome injected AFTER localization (hamburger nav,
   account toast, PDF toasts) ships in-language, and the legacy v1 milan
   fallback is localized instead of shipping raw Hinglish.

The sweep: strip <script>/<style>, walk every visible text node, and flag any
run of >= 4 consecutive Latin-script words. Allowlisted proper nouns (brand,
data sources, product keywords) are neutral — they neither count toward nor
break a run, so real English around them is still caught.
"""
import html as htmlmod
import json
import re

import pytest

import milan_hi
import milan_v2
import narrative
import report_view_v2
import shaadi_hi
import vyapar_hi
from blueprint_hi_report import render_blueprint_hi
from engine import compute_report
from products import compute_blueprint, compute_milan, compute_vyapar
from report_view import render_vyapar

# --------------------------------------------------------------------------- #
# sweep machinery
# --------------------------------------------------------------------------- #
ALLOW = {"Axtroshastra", "AXTROSHASTRA", "NASA", "JPL", "Swiss", "Ephemeris",
         "WhatsApp", "CAREER", "PDF", "D1", "D9", "Chrome"}
_WORD = re.compile(r"[A-Za-z][A-Za-z'’\-]*")


def _text_nodes(html):
    html = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    return [htmlmod.unescape(n).strip() for n in re.findall(r">([^<>]+)<", html)
            if n.strip()]


def _latin_runs(text, min_words=4):
    runs, cur = [], []
    for tok in re.split(r"\s+", text):
        w = tok.strip(" ,.;:!?—–()\"'“”‘’|·")
        if w in ALLOW:
            continue                      # neutral: doesn't count, doesn't break
        if w and _WORD.fullmatch(w):
            cur.append(w)
        elif re.search(r"[ऀ-ॿ0-9]", tok):
            if len(cur) >= min_words:
                runs.append(" ".join(cur))
            cur = []
    if len(cur) >= min_words:
        runs.append(" ".join(cur))
    return runs


def _sweep(html):
    leaks = []
    for node in _text_nodes(html):
        for run in _latin_runs(node):
            leaks.append(run)
    return leaks


# --------------------------------------------------------------------------- #
# fixtures: deterministic charts (fixed lat/lon/tz — no geocoding)
# --------------------------------------------------------------------------- #
def _marriage_payload(tq="T0"):
    p = compute_report(name="Asha Sharma", dob="1994-06-21", tob="08:30",
                       tz_offset_hours=5.5, lat=28.61, lon_geo=77.20,
                       female=True, time_quality=tq)
    p["meta"]["lang"] = "hi"
    p["meta"]["report_id"] = "TESTHI"
    p["meta"]["_birth"] = {"dob": "1994-06-21", "tob": "08:30", "tz": 5.5,
                           "lat": 28.61, "lon": 77.20, "place": "New Delhi"}
    return p


P1 = {"name": "Asha", "dob": "1992-04-15", "tob": "08:30", "tz": 5.5,
      "lat": 28.61, "lon": 77.20, "gender": "female"}
P2 = {"name": "Vikram", "dob": "1990-11-02", "tob": "21:10", "tz": 5.5,
      "lat": 19.07, "lon": 72.87, "gender": "male"}


def _milan_payload():
    p = compute_milan(P1, P2)
    p["meta"]["lang"] = "hi"
    p["meta"]["report_id"] = "TESTHI"
    return p


def _vyapar_payload():
    p = compute_vyapar("Rohit Verma", "1987-10-06", "09:25", 5.5, 26.9124, 75.7873)
    p["meta"]["lang"] = "hi"
    p["meta"]["report_id"] = "TESTHI"
    return p


def _blueprint_payload(**kw):
    defaults = dict(name="Ananya Iyer", dob="1994-06-15", tob="08:30", tz=5.5,
                     lat=28.6139, lon=77.2090, time_quality="T0")
    defaults.update(kw)
    p = compute_blueprint(**defaults)
    p["meta"]["lang"] = "hi"
    return p


DUMMY_HI = "यह एक नमूना हिंदी अनुच्छेद है जो एलएलएम से आता है।"


# --------------------------------------------------------------------------- #
# 1) full-report sweeps
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("tq", ["T0", "T2"])
def test_marriage_hindi_banks_have_no_english_runs(tq):
    """LLM off/failed: every deterministic bank must render in Devanagari."""
    html = shaadi_hi.localize(report_view_v2.render_report_v2(_marriage_payload(tq)))
    leaks = _sweep(html)
    assert not leaks, f"English/Hinglish leaked into Hindi marriage report ({tq}): {leaks[:8]}"


def test_marriage_hindi_with_llm_has_no_english_runs():
    """LLM on (Devanagari prose in every slot): the shell must not leak either."""
    p = _marriage_payload()
    p["narrative"] = {k: DUMMY_HI for k, _ in narrative.SECTION_SPECS["marriage"]}
    html = shaadi_hi.localize(report_view_v2.render_report_v2(p))
    leaks = _sweep(html)
    assert not leaks, f"structural English leaked into Hindi marriage report: {leaks[:8]}"


@pytest.mark.parametrize("with_llm", [False, True])
def test_milan_hindi_has_no_english_runs(with_llm):
    p = _milan_payload()
    if with_llm:
        p["narrative"] = {k: DUMMY_HI for k, _ in narrative.SECTION_SPECS["milan"]}
    html = milan_hi.localize(milan_v2.render_milan_v2(p))
    leaks = _sweep(html)
    assert not leaks, f"English/Hinglish leaked into Hindi milan report: {leaks[:8]}"


@pytest.mark.parametrize("with_llm", [False, True])
def test_vyapar_hindi_has_no_english_runs(with_llm):
    """The /hi/business-growth report must be pure Devanagari. with_llm=False is
    the worst case (deterministic banks only) — every bank must compose in Hindi
    at render time; with_llm=True proves the localized shell doesn't leak either."""
    p = _vyapar_payload()
    if with_llm:
        p["narrative"] = {k: DUMMY_HI for k, _ in narrative.SECTION_SPECS["vyapar"]}
    html = vyapar_hi.localize(render_vyapar(p))
    leaks = _sweep(html)
    assert not leaks, f"English/Hinglish leaked into Hindi vyapar report: {leaks[:8]}"


@pytest.mark.parametrize("birth", [
    dict(name="Ananya Iyer", dob="1994-06-15", tob="08:30", tz=5.5, lat=28.6139, lon=77.2090),
    dict(name="Rohan Verma", dob="1988-11-02", tob="23:45", tz=5.5, lat=19.0760, lon=72.8777),
    dict(name="Kavya Reddy", dob="2001-11-03", tob="04:10", tz=5.5, lat=13.0827, lon=80.2707),
])
def test_blueprint_hindi_has_no_english_runs(birth):
    """The /hi/life-blueprint report (blueprint_hi_report.render_blueprint_hi,
    a real renderer, not a post-render translator) must be pure Devanagari
    for any real chart — three distinct births exercise different wheel-tag
    combinations (thriving/building/watch), dignities, dashas and elements."""
    p = _blueprint_payload(**birth)
    html = render_blueprint_hi(p)
    leaks = _sweep(html)
    assert not leaks, f"English/Hinglish leaked into Hindi blueprint report: {leaks[:8]}"


# --------------------------------------------------------------------------- #
# 2) shaadi_hi structural patterns (regression units)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("src,must_not_contain,must_contain", [
    # _resolve period-strip bug: the composed cover line must translate FULLY
    ("Generated 2026-08-03 · NASA JPL data (Swiss Ephemeris) · Lahiri ayanamsa · "
     "Whole-sign houses · Lagna-based analysis with full house precision.",
     "Lagna-based", "लग्न-आधारित"),
    ("Om Sham Shanaishcharaya Namah — 108 times, on Saturday", "Om Sham", "ॐ शं शनैश्चराय नमः"),
    ("Blue Sapphire — only after expert trial, if Saturn is well-placed — only "
     "after a trial, via a qualified jeweller/astrologer.", "Sapphire", "नीलम"),
    ("Ruby — only if Sun is well-placed — only after a trial, via a qualified "
     "jeweller/astrologer.", "Ruby", "माणिक"),
    ("Emerald — only after expert trial.", "Emerald", "पन्ना"),
    ("A gemstone isn't advised for Jupiter right now — the mantra and fast day "
     "are enough.", "gemstone", "गुरु"),
    ("No gemstone advised for a Ketu period — favour clarity, closure and simple habits.",
     "gemstone", "केतु"),
    ("Jupiter Mahadasha — Venus + Sun + Moon Antardasha", "Mahadasha", "गुरु महादशा — शुक्र + सूर्य + चंद्र अंतर्दशा"),
    ("Sade Sati is not currently running. The next phase begins around Oct 2041. "
     "For now, Saturn is not adding delay-pressure from this angle.",
     "Sade Sati", "साढ़ेसाती अभी नहीं चल रही"),
    ("Your love-style is sensory and loyal — love means comfort, food, touch and "
     "permanence — with Venus strong in its own sign, you can trust your instincts in love.",
     "love-style", "आपकी प्रेम-शैली"),
    ("No weak Mahadasha/Antardasha periods are flagged in the near term — no "
     "period-specific remedy is needed right now.", "flagged", "महादशा/अंतर्दशा"),
    ("Send CAREER on WhatsApp →", "Send", "CAREER भेजें"),
    ("Chandra Lagna system (Moon-as-ascendant) — the classical Parashari method "
     "used when the birth time is approximate; windows are shown with honest, wider ranges.",
     "Chandra Lagna system", "चंद्र लग्न पद्धति"),
])
def test_shaadi_hi_resolves_structural_strings(src, must_not_contain, must_contain):
    out = shaadi_hi._resolve(src)
    assert out is not None, f"unresolved: {src!r}"
    assert must_not_contain not in out, f"{src!r} -> {out!r}"
    assert must_contain in out, f"{src!r} -> {out!r}"


def test_shaadi_hi_title_pattern_keeps_name():
    out = shaadi_hi._resolve("Asha Sharma — Marriage Timing Report | Axtroshastra")
    assert out == "Asha Sharma — विवाह समय रिपोर्ट | Axtroshastra"


# --------------------------------------------------------------------------- #
# 3) chrome + v1 fallback (served page, post-localize injections)
# --------------------------------------------------------------------------- #
def _paid_hindi_marriage(client):
    r = client.post("/api/kundli", json={
        "name": "Chrome Tester", "dob": "1992-02-11", "tob": "10:10",
        "time_quality": "T0", "place": "Delhi", "gender": "female",
        "variant": "/hi/marriage"})
    assert r.status_code == 200, r.text
    rid = r.json()["report_id"]
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    return rid


def test_report_page_chrome_is_hindi(client):
    rid = _paid_hindi_marriage(client)
    html = client.get(f"/report/{rid}").text
    assert "मेन्यू" in html, "hamburger nav must be the Hindi one on a hi report"
    assert "लॉगिन / मेरा अकाउंट" in html
    assert "Account created" not in html
    assert "अकाउंट बन गया" in html
    assert "Preparing your PDF" not in html
    assert "तैयार हो रही है" in html


def test_report_page_chrome_stays_english_for_en(client):
    r = client.post("/api/kundli", json={
        "name": "Chrome Tester", "dob": "1992-02-11", "tob": "10:10",
        "time_quality": "T0", "place": "Delhi", "gender": "female",
        "variant": "/en/marriage"})
    rid = r.json()["report_id"]
    client.post(f"/api/_demo_pay/{rid}")
    html = client.get(f"/report/{rid}").text
    assert "Menu" in html and "मेन्यू" not in html
    assert "Account created" in html


def test_milan_v1_fallback_is_localized():
    """?v2=0 / v2-render-failure path: the legacy Hinglish milan render must be
    localized for a Hindi report AND its client language-toggle neutralized."""
    import api
    html = api._render_for("milan", _milan_payload())
    assert re.search(r"[ऀ-ॿ]", html), "v1 fallback not localized"
    # the v1 template's axlang bootstrap must be pinned to 'hi' (it hides the
    # body pre-paint for 'en' and would fight the localized page)
    assert "var l = 'hi';" in html, "v1 axlang bootstrap must be pinned to hi"
    assert "localStorage.getItem('axlang') || 'en'" not in html
    assert "#axlang{display:none!important}" in html, "toggle capsule must be hidden"


# --------------------------------------------------------------------------- #
# 4) LLM layer: facts scrub, prompt directives, Devanagari guardrail
# --------------------------------------------------------------------------- #
HINGLISH_KOOTA = ("Do air moons — baatein kabhi khatam nahi hongi. Mental match "
                  "excellent; grounding (routine, decisions) ko conscious effort "
                  "dena hoga.")


def _milan_llm_payload(lang):
    return {
        "product": "milan",
        "meta": {"p1": "Asha", "p2": "Vikram", "lang": lang},
        "total": 28, "max_total": 36,
        "element": {"p1": "air", "p2": "air", "text": HINGLISH_KOOTA},
        "kootas": [{"name": "Bhakoot", "score": 7, "max": 7, "text": HINGLISH_KOOTA},
                   {"name": "Nadi", "score": 8, "max": 8, "text": "some unmapped hinglish text"}],
    }


def test_milan_facts_scrub_substitutes_devanagari_for_hi():
    facts = narrative._facts_for_llm(_milan_llm_payload("hi"), "milan")
    blob = json.dumps(facts, ensure_ascii=False)
    assert "baatein kabhi khatam" not in blob, "Hinglish koota text fed to the LLM"
    assert "some unmapped hinglish text" not in blob, "unmapped Hinglish must be dropped"
    assert re.search(r"[ऀ-ॿ]", blob), "hi facts should carry the Devanagari twin"
    # scores/names/meanings survive
    assert facts["kootas"][0]["score"] == 7 and facts["kootas"][1]["name"] == "Nadi"


def test_milan_facts_scrub_drops_hinglish_for_english():
    facts = narrative._facts_for_llm(_milan_llm_payload("en"), "milan")
    blob = json.dumps(facts, ensure_ascii=False)
    assert "baatein kabhi khatam" not in blob
    assert "text" not in facts["kootas"][0]


def test_hi_system_prompt_has_language_directives():
    spec = narrative.SECTION_SPECS["milan"]
    sp = narrative._system_prompt("milan", spec, "hi")
    assert "देवनागरी" in sp
    assert "no Roman-script sentences" in sp and "Hinglish" in sp
    assert "Mesha → मेष" in sp     # Roman-facts → Devanagari-output instruction
    # English prompt unchanged / no Hindi rules
    sp_en = narrative._system_prompt("milan", spec, "english")
    assert "Hinglish" not in sp_en


def test_devanagari_guardrail_drops_english_sections(monkeypatch):
    """A hi report whose model output slips into English keeps the Hindi bank
    instead (section dropped); Devanagari sections pass."""
    monkeypatch.setenv("NARRATIVE_ENABLED", "1")
    monkeypatch.setenv("NARRATIVE_PROVIDER", "claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    out_obj = {"summary": "This couple is wonderful and their bond will only deepen with time.",
               "headline": "एक बेहद प्यारी और टिकाऊ जोड़ी"}
    monkeypatch.setattr(narrative, "_http_post_json",
                        lambda url, headers, body, timeout=None:
                        {"content": [{"type": "text", "text": json.dumps(out_obj, ensure_ascii=False)}]})
    monkeypatch.setattr(narrative, "_model", lambda: "claude-sonnet-5")
    payload = {"product": "milan", "meta": {"p1": "A", "p2": "B", "lang": "hi"}}
    out = narrative.generate_narrative(payload)
    assert "summary" not in out, "English section must be dropped for a hi report"
    assert "headline" in out


def test_devanagari_ratio_helper():
    assert narrative._devanagari_ok("आपका रिश्ता D9 में मज़बूत है — NASA data से जाँचा।")
    assert not narrative._devanagari_ok("Your bond is strong and will deepen over time.")
    assert narrative._devanagari_ok("2027 · 18/36 · 85%")   # no letters at all


# --------------------------------------------------------------------------- #
# 5) admin backfill route
# --------------------------------------------------------------------------- #
def test_backfill_narrative_requires_key(client):
    assert client.post("/api/backfill_narrative").status_code == 403


def test_backfill_narrative_queues_hindi_marriage_reports(client):
    rid = _paid_hindi_marriage(client)
    r = client.post("/api/backfill_narrative", params={"key": "test-stats-key"})
    assert r.status_code == 200
    data = r.json()
    assert rid in data["queued"]
    assert data["narrative_enabled"] is False   # env off in tests -> tasks no-op


def test_backfill_narrative_single_rid(client):
    rid = _paid_hindi_marriage(client)
    r = client.post("/api/backfill_narrative", params={"key": "test-stats-key", "rid": rid})
    assert r.status_code == 200
    assert r.json()["queued"] == [rid]
    # unpaid/unknown rid -> 404
    assert client.post("/api/backfill_narrative",
                       params={"key": "test-stats-key", "rid": "nope"}).status_code == 404
