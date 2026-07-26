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
  NARRATIVE_LANG      "hinglish" (default) | "english"
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
    return (os.getenv("NARRATIVE_LANG") or "hinglish").strip().lower()

def _float(name, default):
    try:
        return float(os.getenv(name, default))
    except Exception:
        return float(default)

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
    "marriage": [
        ("top_summary", "2-3 warm sentences answering 'when will marriage happen' from their strongest window."),
        ("chart_intro", "2 sentences introducing what their chart says about marriage, plain language."),
        ("partner", "3-4 sentences on the kind of partner and how they may meet, from the indications."),
        ("love_pattern", "3-4 sentences on how this person loves, from their nakshatra and Venus."),
        ("action_intro", "2-3 encouraging sentences on what to do now, non-fatalistic."),
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
        system = _system_prompt(product, spec)
        user = _user_prompt(facts, spec)
        raw = _call(system, user)
        if not raw:
            return {}
        data = _parse_json(raw)
        if not isinstance(data, dict):
            logger.warning("[narrative] non-dict output for %s", product)
            return {}
        out = {}
        allowed = _allowed_numbers(facts)
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
            out[key] = html.escape(val)
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
              "persona", "career", "roadmap", "extras", "chart"):
        if k in payload:
            facts[k] = payload[k]
    return facts


def _system_prompt(product: str, spec) -> str:
    lang = ("Write in warm, natural Hinglish (Hindi-English mix, Roman script), the "
            "way a caring Indian astrologer speaks."
            if _lang() == "hinglish" else
            "Write in warm, natural English.")
    tone = os.getenv("NARRATIVE_TONE", "").strip()
    keys = ", ".join(k for k, _ in spec)
    return (
        "You are the narrative writer for Axtroshastra, a computational Vedic "
        "astrology product. You are given the EXACT results already computed by a "
        "deterministic engine. Your ONLY job is to turn them into vivid, warm, "
        "personal prose.\n\n"
        f"{lang}\n"
        "Hard rules:\n"
        "1. NEVER invent, change, or contradict any number, score, date, grade, "
        "percentage, sign, or verdict. Describe meaning; do not restate the raw "
        "scores (the report prints those itself).\n"
        "2. Be reassuring and non-fatalistic — never predict doom, death, divorce, "
        "or medical/financial outcomes. Astrology here is guidance, not certainty.\n"
        "3. No markdown, no HTML, no emojis, no headings — plain sentences only.\n"
        f"4. Return ONLY a JSON object with exactly these string keys: {keys}. "
        "Each value is the prose for that section.\n"
        + (f"5. Voice: {tone}\n" if tone else "")
    )


def _user_prompt(facts: dict, spec) -> str:
    briefs = "\n".join(f"- {k}: {brief}" for k, brief in spec)
    return ("Here are the computed facts for this report (JSON):\n\n"
            + json.dumps(facts, ensure_ascii=False, default=str)
            + "\n\nWrite these sections:\n" + briefs
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
# provider dispatch (stdlib HTTP — no SDK, no new wheels)
# --------------------------------------------------------------------------- #
def _call(system: str, user: str) -> str:
    return (_call_openai if _provider() == "openai" else _call_anthropic)(system, user)


def _http_post_json(url: str, headers: dict, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    timeout = _float("NARRATIVE_TIMEOUT", "30")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _call_anthropic(system: str, user: str) -> str:
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
        "max_tokens": int(_float("NARRATIVE_MAX_TOKENS", "4096")),
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
        logger.error("[narrative] anthropic HTTP %s: %s", e.code, e.read()[:300])
        return ""
    parts = out.get("content") or []
    text = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
    if not text:
        return ""
    return "{" + text if prefill else text


def _call_openai(system: str, user: str) -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        logger.warning("[narrative] OPENAI_API_KEY not set")
        return ""
    body = {
        "model": _model(),
        "temperature": _float("NARRATIVE_TEMPERATURE", "0.7"),
        "max_tokens": int(_float("NARRATIVE_MAX_TOKENS", "4096")),
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
