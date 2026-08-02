"""
narrative.py — optional LLM "narrative layer" for report prose.

The engine stays 100% deterministic: it computes every FACT (window dates, guna
scores, koota results, dignities, manglik status, the chart). This module only
rewrites the *descriptive prose* around those facts into warmer, more creative
copy — the sentences that today come from the hand-authored banks
(jyotish_maps.py, the inline dicts in report_view.py). If it's disabled or fails,
the renderers fall straight back to those banks, so a report is NEVER broken by
this layer.

Design guarantees:
  * PROVIDER-SWAPPABLE  — Anthropic (Claude) or OpenAI (ChatGPT), one env var.
  * NO NEW DEPENDENCIES — both APIs are called over stdlib urllib, so nothing
    needs adding to the offline EB wheelhouse (packages/).
  * FACTS FROZEN        — the model is given the numbers as read-only context and
    told never to alter them; a post-generation validator drops any section whose
    prose contains a score/percentage that doesn't match the payload.
  * SAFE OUTPUT         — every returned string is html.escape()-d (the template
    owns all markup), so model output can never break layout or inject HTML.
  * CACHED              — generated once at payment time and stored on the report
    payload (payload["narrative"]); renderers just read it. Never per-view.
  * NEVER RAISES        — any error returns {} and the banks take over.

Wiring:
  api.py webhook  -> generate_narrative(payload) -> store payload["narrative"]
  report_view.py  -> narr(p, "key") or <deterministic bank default>

Env:
  NARRATIVE_ENABLED   "1" to turn the layer on (default off -> banks only)
  NARRATIVE_PROVIDER  "claude" (default) | "openai"
  NARRATIVE_MODEL     override model id (else per-provider default below)
  NARRATIVE_LANG      "english" (default) | "hi" (Devanagari); per-report meta.lang wins
  NARRATIVE_TONE      one extra voice line appended to the system prompt
  NARRATIVE_TEMPERATURE  default "0.7"
  NARRATIVE_MAX_TOKENS   default "1500"
  NARRATIVE_TIMEOUT      seconds, default "30"
  ANTHROPIC_API_KEY  / OPENAI_API_KEY
"""
import html
import json
import logging
import os
import re
import urllib.request
import urllib.error
from datetime import datetime, timedelta

logger = logging.getLogger("axtroshastra.narrative")

DEFAULT_MODEL = {"claude": "claude-sonnet-5", "openai": "gpt-4o-mini"}
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
ANTHROPIC_VERSION = "2023-06-01"

MAX_SECTION_CHARS = 1600     # a runaway section is dropped (fallback to bank)

# --------------------------------------------------------------------------- #
# config (read at call time so a dashboard/env change needs no redeploy)
# --------------------------------------------------------------------------- #
def enabled() -> bool:
    return os.getenv("NARRATIVE_ENABLED") == "1"

def _provider() -> str:
    p = (os.getenv("NARRATIVE_PROVIDER") or "claude").strip().lower()
    return p if p in ("claude", "openai") else "claude"

def _model() -> str:
    return os.getenv("NARRATIVE_MODEL") or DEFAULT_MODEL[_provider()]

def _lang() -> str:
    # Only two output languages are supported: 'hi' (Devanagari) and 'english'.
    v = (os.getenv("NARRATIVE_LANG") or "english").strip().lower()
    return "hi" if v in ("hi", "hindi", "devanagari") else "english"

def _resolve_lang(payload: dict) -> str:
    """Per-report locale wins over the global NARRATIVE_LANG env, so a Hindi buyer
    always gets Devanagari prose regardless of the server default. Reads the report's
    stored locale (meta.lang, set from the /hi/ vs /en/ funnel); falls back to _lang().
    Returns one of: 'hi' (Devanagari) | 'english'. (Hinglish is not an output language.)"""
    meta = (payload or {}).get("meta") or {}
    loc = str(meta.get("lang") or (payload or {}).get("lang") or "").strip().lower()
    if loc in ("hi", "hindi", "devanagari"):
        return "hi"
    if loc in ("en", "english"):
        return "english"
    return _lang()

def _float(name, default):
    try:
        return float(os.getenv(name, default))
    except Exception:
        return float(default)

# Per-product output-token budget. Marriage v2 has ~32 slots and needs headroom;
# other products keep the smaller default. Env NARRATIVE_MAX_TOKENS overrides all.
MAX_TOKENS_BY_PRODUCT = {"marriage": 8000}
DEFAULT_MAX_TOKENS = 4096

def _max_tokens(product: str) -> int:
    env = os.getenv("NARRATIVE_MAX_TOKENS")
    if env:
        try:
            return int(float(env))
        except Exception:
            pass
    return MAX_TOKENS_BY_PRODUCT.get(product, DEFAULT_MAX_TOKENS)

# --------------------------------------------------------------------------- #
# which prose slots each product exposes to the LLM.  key -> writing brief.
# Renderers read these keys via narr(p, key); anything not produced (or dropped
# by validation) falls back to the deterministic bank text, so this list can
# grow safely one slot at a time.
# --------------------------------------------------------------------------- #
SECTION_SPECS = {
    "milan": [
        ("headline", "A short, warm one-line verdict for the couple (max ~10 words)."),
        ("summary", "2-3 sentences on the overall match — what's strong underneath the attraction."),
        ("couple_type", "3-4 vivid sentences describing this couple's dynamic, using their two names."),
        ("deepdive_strength", "3-4 sentences celebrating their single strongest area and what it means for the relationship."),
        ("deepdive_growth", "4-5 sentences on their weakest area: the real, chart-based reason it's low, and how to bridge it, using their two names. Warm, specific, never fatalistic."),
        ("growth", "2-3 sentences framing their one growth area as fixable and normal, not a red flag."),
        ("combined_energy", "2-3 sentences on their element pairing and what it means day to day."),
        ("closing_note", "A warm 4-5 sentence closing letter to the couple, by name — the emotional payload."),
    ],
    # Marriage report v2 (see claude/marriage-report-blueprint.md). ~32 prose slots
    # across 4 tiers. One LLM call returns all of them as one JSON object; each slot
    # falls back to its deterministic English bank in report_view.py if missing or
    # dropped by a guardrail. Manglik pages are deliberately NOT slots (deterministic).
    "marriage": [
        # ---- Tier 1: Main page ----
        ("top_summary", "2-3 warm sentences answering 'when will marriage happen' from the strongest window."),
        # ---- Tier 2: Summary ----
        ("windows_intro", "2 sentences framing the 1-3 windows ahead as a timeline, encouraging."),
        ("chart_teaser", "2 sentences on what the chart says about marriage at a glance."),
        ("partner_teaser", "1-2 intriguing sentences hinting at the kind of partner indicated."),
        ("story_teaser", "2 sentences: why it hasn't happened yet and that momentum is turning."),
        ("action_teaser", "2 sentences on the single most useful thing to do now."),
        # ---- Tier 3: Detailed report ----
        ("window_1", "3-4 sentences on what the strongest window means and why it lights up, plain language."),
        ("window_2", "2-3 sentences on the second window; how it differs from the first."),
        ("window_3", "2-3 sentences on the third window or the longer outlook beyond it."),
        ("action_strong", "2-3 encouraging, non-fatalistic sentences on making the most of good windows."),
        ("action_weak", "2-3 sentences reframing quiet periods: what to do (and not force) now."),
        ("past_pattern", "3-4 reassuring sentences on why past periods did/didn't convert - timing, not failure."),
        ("outlook", "2-3 sentences on the shape of the next 3 years and the months to watch."),
        ("sade_sati_note", "2-3 calm, non-fatalistic sentences on the Saturn cycle's current phase."),
        ("remedies_note", "2-3 sentences framing remedies as optional support, agency first, zero pressure."),
        ("partner_personality", "2-3 sentences on the partner's likely personality, from the 7th sign."),
        ("meeting_context", "3-4 sentences on the partner's background and how/where you may meet; love-vs-arranged."),
        ("love_pattern", "3-4 sentences on how this person loves, from their nakshatra and Venus."),
        # ---- Tier 4: Astrology details ----
        ("method_intro", "2-3 sentences on why this sidereal/whole-sign method is authentic and trustworthy."),
        ("chart_reading", "2-3 sentences reading the overall shape of the birth chart, plainly."),
        ("lagna_moon", "2-3 sentences on the two lenses - ascendant and Moon - and what each governs."),
        ("planet_strengths", "3-4 sentences on what the planetary dignities mean for this person, plainly."),
        ("nakshatra_deep", "3-4 sentences on the classical character of this birth star."),
        ("seventh_house", "2-3 sentences on the 7th house as the seat of marriage in this chart."),
        ("seventh_lord", "3-4 sentences on the 7th lord as the 'marriage switch' and what its condition implies."),
        ("karakas", "2-3 sentences on Venus (and Jupiter) as the natural significators of union."),
        ("darakaraka", "2-3 sentences explaining the Jaimini spouse-indicator and what it adds."),
        ("node_axis", "2-3 sentences on any Rahu/Ketu link to the 7th axis - the karmic dimension."),
        ("dasha_periods", "3-4 sentences on what the active and upcoming periods bring for marriage."),
        ("transits", "2-3 sentences on Jupiter and Saturn transits as the 'go' and 'slow' signals."),
        ("navamsa_reading", "3-4 sentences on the D9 as the marriage-promise chart and what its strength band says."),
        ("closing_note", "A warm 3-4 sentence closing note to the reader."),
    ],
    "blueprint": [
        ("persona", "3-4 sentences painting who this person is, from lagna and Moon."),
        ("career", "3 sentences on career direction, from the 10th lord."),
        ("closing_note", "A warm 3-4 sentence closing note."),
    ],
    "vidyarthi": [
        ("hero", "2-3 motivating sentences on this student's academic/career promise."),
        ("closing_note", "A warm 3-4 sentence closing note to the student."),
    ],
}

# --------------------------------------------------------------------------- #
# public entry
# --------------------------------------------------------------------------- #
def generate_narrative(payload: dict) -> dict:
    """Return {section_key: escaped_prose} for this report, or {} to fall back to
    the deterministic banks. Never raises."""
    if not enabled():
        return {}
    product = (payload.get("product")
               or (payload.get("meta") or {}).get("product") or "marriage")
    spec = SECTION_SPECS.get(product)
    if not spec:
        return {}
    try:
        facts = _facts_for_llm(payload, product)
        system = _system_prompt(product, spec, _resolve_lang(payload))
        user = _user_prompt(facts, spec)
        raw = _call(system, user, _max_tokens(product))
        if not raw:
            return {}
        data = _parse_json(raw)
        if not isinstance(data, dict):
            logger.warning("[narrative] non-dict output for %s", product)
            return {}
        out = {}
        allowed = _allowed_numbers(facts)
        truth = _planet_truth(facts)
        for key, _brief in spec:
            val = data.get(key)
            if not isinstance(val, str):
                continue
            val = val.strip()
            if not val or len(val) > MAX_SECTION_CHARS:
                continue
            if not _numbers_ok(val, allowed):
                logger.warning("[narrative] section %r dropped: unknown figure", key)
                continue
            if not _claims_ok(val, truth):
                logger.warning("[narrative] section %r dropped: chart-contradicting placement", key)
                continue
            out[key] = html.escape(val)
        logger.info("[narrative] %s/%s lang=%s model=%s -> %d/%d sections generated",
                    _provider(), product, _resolve_lang(payload), _model(), len(out), len(spec))
        return out
    except Exception as e:
        logger.error("[narrative] generation failed (%s/%s): %s",
                     _provider(), product, e)
        return {}


def narr(payload: dict, key: str):
    """Renderer helper: the generated prose for a slot, or None to use the bank.
    Kept here so report_view.py has a single import surface."""
    return (payload.get("narrative") or {}).get(key)


# --------------------------------------------------------------------------- #
# fact extraction (PII-minimised) + prompts
# --------------------------------------------------------------------------- #
def _first_name(s: str) -> str:
    return (s or "").strip().split(" ")[0] if s else ""


def _facts_for_llm(payload: dict, product: str) -> dict:
    """A compact, PII-scrubbed view of the computed facts. We never send mobile,
    email, exact DOB or birth coordinates — only first names and the astrological
    results the prose needs to stay accurate."""
    meta = dict(payload.get("meta") or {})
    for k in list(meta.keys()):          # drop private/internal fields
        if k.startswith("_"):
            meta.pop(k, None)
    meta.pop("phone", None)
    if meta.get("name"):
        meta["name"] = _first_name(meta["name"])
    for who in ("p1", "p2"):
        if meta.get(who):
            meta[who] = _first_name(meta[who])

    facts = {"product": product, "meta": meta}
    # copy only the factual result blocks the prose describes (never PII)
    for k in ("teaser", "significators", "windows", "manglik", "current_period",
              "kootas", "total", "max_total", "verdict", "effective",
              "effective_verdict", "element", "match_pct", "cancellations",
              "persona", "career", "roadmap", "extras", "chart", "navamsa"):
        if k in payload:
            facts[k] = payload[k]

    # Marriage: the report hides windows starting >4 years out when a nearer one
    # exists (report_view_v2._visible_windows). Mirror that here so the LLM never
    # narrates a window the reader can't see. Uses the frozen report date so it
    # stays consistent with the rendered view.
    if product == "marriage" and isinstance(facts.get("windows"), list):
        try:
            gen = datetime.strptime(meta.get("generated", ""), "%Y-%m-%d")
            cutoff = gen + timedelta(days=int(4 * 365.25))
            near = [w for w in facts["windows"]
                    if datetime.strptime(w.get("start", ""), "%Y-%m") <= cutoff]
            if near:
                facts["windows"] = near
        except Exception:
            pass
    return facts


def _system_prompt(product: str, spec, lang_code: str = "") -> str:
    lang_code = (lang_code or _lang()).strip().lower()
    if lang_code == "hi":
        lang = ("Write in warm, natural, conversational Hindi in the Devanagari script "
                "(हिंदी, देवनागरी लिपि) — the way a caring, well-spoken Indian astrologer "
                "speaks. Address the reader respectfully as 'आप'. Use everyday spoken Hindi, "
                "not heavy or over-Sanskritised textbook Hindi; a few familiar loan-words "
                "(रिश्ता, कम्पैटिबिलिटी, बैलेंस) are fine where they read naturally. Do NOT "
                "transliterate Hindi into Roman/Latin letters. Keep proper nouns and the "
                "Vedic terms in the Devanagari form given in the facts; write digits and "
                "scores as Western numerals (e.g. 36, 18/36, 85%). Sound like a real person "
                "who has actually read this chart, never like a translation.")
    else:
        lang = ("Write in warm, natural, conversational English — the way a caring, "
                "well-spoken astrologer speaks to someone they genuinely want to help. "
                "Clear, human and encouraging, never stiff or textbook-like.")
    tone = os.getenv("NARRATIVE_TONE", "").strip()
    keys = ", ".join(k for k, _ in spec)
    return (
        "You are a warm, compassionate, and knowledgeable Vedic astrologer (Jyotish "
        "Shastri) writing the personal-prose layer of Axtroshastra. A deterministic "
        "engine has ALREADY computed every fact — dates, scores, signs, placements, "
        "verdicts — and the report template prints them. Your ONLY job is to turn those "
        "facts into engaging, warm, conversational prose the reader loves to read.\n\n"
        f"{lang}\n\n"
        "How to write:\n"
        "- Speak directly and warmly to the reader. Sound like a caring astrologer who "
        "has actually read this chart, not a textbook.\n"
        "- Explain any technical idea (dasha, transit, yoga, nakshatra) with a simple, "
        "everyday analogy or example. Keep sentences short and easy to follow.\n"
        "- Avoid heavy, archaic, over-technical phrasing. Be clear and human.\n\n"
        "Hard rules:\n"
        "1. NEVER invent, change, or contradict any fact you were given — no number, "
        "score, date, grade, percentage, sign, planet, house, dignity, or verdict may "
        "differ from the input. Describe what a fact MEANS; do not restate the raw "
        "scores (the template prints those itself).\n"
        "2. Do not state any placement or claim that is not in the facts. If unsure, "
        "speak to the meaning generally rather than naming a specific position.\n"
        "3. Stay reassuring and non-fatalistic — never predict doom, death, divorce, "
        "disease, or financial ruin, and avoid overly negative language. This is warm, "
        "supportive guidance, not a warning.\n"
        "4. Plain sentences only — the template owns all headings, bullets, callout "
        "boxes and layout, so do not output markdown or HTML. You may use a few tasteful, "
        "relevant emojis where they add warmth (e.g. 💖 ✨ 🌟), but sparingly — never a "
        "cluster, and at most one or two per section.\n"
        f"5. Return ONLY a JSON object with exactly these string keys: {keys}. Each value "
        "is the prose for that section.\n"
        + (f"6. Voice: {tone}\n" if tone else "")
    )


def _user_prompt(facts: dict, spec) -> str:
    briefs = "\n".join(f"- {k}: {brief}" for k, brief in spec)
    return ("Here are the computed facts for this report (JSON):\n\n"
            + json.dumps(facts, ensure_ascii=False, default=str)
            + "\n\nWrite the sections below. They appear in the report in this order and "
              "together form one flowing, cohesive report — keep the voice consistent, let "
              "earlier sections set up later ones, and do not repeat the same point across "
              "sections.\n\nSections:\n" + briefs
            + "\n\nReturn only the JSON object.")


# --------------------------------------------------------------------------- #
# fact-preservation guardrail
# --------------------------------------------------------------------------- #
_NUM_TOKEN = re.compile(r"\d+\s*/\s*\d+|\d+(?:\.\d+)?\s*%|\b\d{4}\b")

def _allowed_numbers(facts: dict) -> set:
    """Every score/percentage/year that legitimately appears in the facts. Any
    such token the model writes MUST be in this set, else the section is dropped
    (defends against the model altering a score inside prose)."""
    blob = json.dumps(facts, default=str)
    allowed = set(m.group(0).replace(" ", "") for m in _NUM_TOKEN.finditer(blob))
    # also allow "X/Y" built from separate score/max fields
    for k in facts.get("kootas", []) or []:
        try:
            allowed.add(f"{int(k['score']) if float(k['score']).is_integer() else k['score']}/{k['max']}")
        except Exception:
            pass
    if "total" in facts and "max_total" in facts:
        allowed.add(f"{facts['total']}/{facts['max_total']}")
    return allowed

def _numbers_ok(text: str, allowed: set) -> bool:
    for m in _NUM_TOKEN.finditer(text):
        if m.group(0).replace(" ", "") not in allowed:
            return False
    return True


# --------------------------------------------------------------------------- #
# qualitative fact-preservation guardrail
# --------------------------------------------------------------------------- #
# The numeric guard above only catches altered scores/percentages/years. This
# second guard catches altered *placements*: if the prose says a planet is in a
# sign, or is exalted/debilitated, that claim must agree with the computed chart
# (D1 rashi OR D9 navamsa). A contradiction drops the section back to the bank.
# It is deliberately conservative — it only fires on an explicit "<planet> in
# <sign>" / "<planet> ... exalted|debilitated" assertion, so warm prose that
# never names a placement (the desired style) is never touched.
_SIGNS_SA = ["mesha", "vrishabha", "mithuna", "karka", "simha", "kanya",
             "tula", "vrishchika", "dhanu", "makara", "kumbha", "meena"]
_SIGNS_EN = ["aries", "taurus", "gemini", "cancer", "leo", "virgo",
             "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]
_PLANETS = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu"]

def _sign_index(name: str) -> int:
    n = (name or "").strip().lower()
    if n in _SIGNS_SA:
        return _SIGNS_SA.index(n)
    if n in _SIGNS_EN:
        return _SIGNS_EN.index(n)
    return -1

_PLANET_ALT = "|".join(_PLANETS)
_SIGN_ALT = "|".join(_SIGNS_SA + _SIGNS_EN)
# "<planet> [up to 30 non-sentence chars] in [the] <sign>"
_PLACEMENT_RE = re.compile(
    r"\b(%s)\b[^.?!]{0,30}?\bin\s+(?:the\s+)?(%s)\b" % (_PLANET_ALT, _SIGN_ALT), re.I)
_PLANET_RE = re.compile(r"\b(%s)\b" % _PLANET_ALT, re.I)
# a dignity adjective in the window just after a planet name
_DIGNITY_RE = re.compile(r"\b(exalted|debilitat\w*|debilited|own\s+sign)\b", re.I)
# "fallen" is intentionally excluded — too collision-prone in love prose ("fallen for…")
_ASTRO_CTX_RE = re.compile(r"\b(%s|sign|rashi|navamsa|d9|house|chart)\b" % _SIGN_ALT, re.I)

def _planet_truth(facts: dict) -> dict:
    """planet(lower) -> {'signs': {valid sign indices, D1+D9}, 'dignities': {valid dignity words}}."""
    truth = {}
    for name, info in ((facts.get("chart") or {}).get("planets") or {}).items():
        t = truth.setdefault(name.lower(), {"signs": set(), "dignities": set()})
        si = _sign_index(info.get("sign", ""))
        if si >= 0:
            t["signs"].add(si)
        t["dignities"].add((info.get("dignity") or "neutral").lower())
    for name, info in ((facts.get("navamsa") or {}).get("planets") or {}).items():
        t = truth.setdefault(name.lower(), {"signs": set(), "dignities": set()})
        si = _sign_index(info.get("sign", ""))
        if si >= 0:
            t["signs"].add(si)
        t["dignities"].add((info.get("dignity") or "neutral").lower())
    return truth

def _claims_ok(text: str, truth: dict) -> bool:
    """False if the prose asserts a planet placement or dignity that the chart contradicts."""
    if not truth:
        return True
    for m in _PLACEMENT_RE.finditer(text):
        t = truth.get(m.group(1).lower())
        si = _sign_index(m.group(2))
        if t and si >= 0 and t["signs"] and si not in t["signs"]:
            return False
    # dignity: scan a short window after each planet; only a claim if a dignity
    # word AND an astrological context (sign / 'sign' / 'navamsa' / …) co-occur,
    # so a metaphorical "exalted sense of duty" is not treated as a chart claim.
    for m in _PLANET_RE.finditer(text):
        t = truth.get(m.group(1).lower())
        if not t or not t["dignities"]:
            continue
        window = text[m.end():m.end() + 45]
        dm = _DIGNITY_RE.search(window)
        if not dm or not _ASTRO_CTX_RE.search(window):
            continue
        word = dm.group(1).lower()
        claimed = "debilitated" if word.startswith("debili") else "own" if "own" in word else "exalted"
        if claimed not in t["dignities"]:
            return False
    return True


# --------------------------------------------------------------------------- #
# provider dispatch (stdlib HTTP — no SDK, no new wheels)
# --------------------------------------------------------------------------- #
def _call(system: str, user: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
    fn = _call_openai if _provider() == "openai" else _call_anthropic
    return fn(system, user, max_tokens)


def _http_post_json(url: str, headers: dict, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    timeout = _float("NARRATIVE_TIMEOUT", "30")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _call_anthropic(system: str, user: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        logger.warning("[narrative] ANTHROPIC_API_KEY not set")
        return ""
    model = _model()
    messages = [{"role": "user", "content": user}]
    # older Claude models support assistant prefill to force JSON
    prefill = not any(g in model for g in ("sonnet-5", "opus-5", "haiku-4-5"))
    if prefill:
        messages.append({"role": "assistant", "content": "{"})
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
    }
    if not prefill:
        body["thinking"] = {"type": "disabled"}
    if os.getenv("NARRATIVE_TEMPERATURE"):
        body["temperature"] = _float("NARRATIVE_TEMPERATURE", "0.7")
    headers = {"x-api-key": key, "anthropic-version": ANTHROPIC_VERSION,
               "content-type": "application/json"}
    try:
        out = _http_post_json(ANTHROPIC_URL, headers, body)
    except urllib.error.HTTPError as e:
        logger.error("[narrative] anthropic HTTP %s (model=%s): %s", e.code, _model(), e.read()[:300])
        return ""
    parts = out.get("content") or []
    text = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
    if not text:
        return ""
    return "{" + text if prefill else text


def _call_openai(system: str, user: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        logger.warning("[narrative] OPENAI_API_KEY not set")
        return ""
    body = {
        "model": _model(),
        "temperature": _float("NARRATIVE_TEMPERATURE", "0.7"),
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
    }
    headers = {"Authorization": f"Bearer {key}", "content-type": "application/json"}
    try:
        out = _http_post_json(OPENAI_URL, headers, body)
    except urllib.error.HTTPError as e:
        logger.error("[narrative] openai HTTP %s: %s", e.code, e.read()[:300])
        return ""
    try:
        return out["choices"][0]["message"]["content"] or ""
    except Exception:
        return ""


def _parse_json(raw: str) -> dict:
    """Tolerant JSON extraction: strip ``` fences and grab the outermost {...}."""
    s = raw.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s).strip()
    try:
        return json.loads(s)
    except Exception:
        i, j = s.find("{"), s.rfind("}")
        if 0 <= i < j:
            try:
                return json.loads(s[i:j + 1])
            except Exception:
                return {}
        return {}
