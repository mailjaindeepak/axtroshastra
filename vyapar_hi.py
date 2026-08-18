"""
vyapar_hi.py — server-side Devanagari (Hindi) localisation for the Vyapar
(business growth) report.

render_vyapar (report_view.py) is authored in English. For a Hindi buyer
(report meta.lang == 'hi') we run the rendered HTML through a safe, exact
text-node translation pass: only whole visible text runs that appear verbatim
in the HI_DATA dictionary are swapped. Everything else is left untouched — so:

  * Devanagari LLM prose from narrative.py (already Hindi) passes through unchanged.
  * Names, numbers, %/scores, dates and emoji pass through unchanged.
  * Nothing inside <script>/<style>/tag-attributes is ever touched.

This mirrors milan_hi.py exactly (same protect → translate → restore core). The
phrase dictionary lives in vyapar_hi_data.py; astro TERMS (planets, nakshatras,
elements, dasha lords) are already Devanagari in jyotish_maps.py and arrive that
way from the engine, so they are not re-translated here.

Wiring (api.py, _render_for): after render_vyapar(payload), if payload
meta.lang == 'hi', call localize(html). Wrapped in try/except there, but this
module also never raises — worst case it returns the input unchanged.
"""
import re
import html as _htmlmod
from vyapar_hi_data import HI_DATA

# text runs between tags, and the script/style blocks we must never touch
_SEG = re.compile(r">([^<>]+)<")
_SKIP = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)

# wrapper handling so "“phrase”", "phrase ✦", "✦ phrase" still resolve
_EMO = r"\U0001F000-\U0001FAFF☀-➿←-⇿⬀-⯿️‍✦✧❖·—–"
_TRAIL = re.compile(rf"^(.*?)(\s*[{_EMO}]+)\s*$")
_LEAD = re.compile(rf"^([{_EMO}]+\s*)(.*)$")
_QUOTED = re.compile(r'^([“"\'])(.*)([”"\'])$', re.DOTALL)


# Proper-noun Devanagari (rashis, nakshatras, planets, elements) — the exact
# proven values from shaadi_hi.TOK, kept local so the vyapar report path doesn't
# import that large module. Chart TERMS the report templates emit repeatedly.
_TOK = {
    "Aries": "मेष", "Taurus": "वृषभ", "Gemini": "मिथुन", "Cancer": "कर्क",
    "Leo": "सिंह", "Virgo": "कन्या", "Libra": "तुला", "Scorpio": "वृश्चिक",
    "Sagittarius": "धनु", "Capricorn": "मकर", "Aquarius": "कुंभ", "Pisces": "मीन",
    "Mesha": "मेष", "Vrishabha": "वृषभ", "Mithuna": "मिथुन", "Karka": "कर्क",
    "Simha": "सिंह", "Kanya": "कन्या", "Tula": "तुला", "Vrishchika": "वृश्चिक",
    "Dhanu": "धनु", "Makara": "मकर", "Kumbha": "कुंभ", "Meena": "मीन",
    "Ashwini": "अश्विनी", "Bharani": "भरणी", "Krittika": "कृत्तिका", "Rohini": "रोहिणी",
    "Mrigashira": "मृगशिरा", "Ardra": "आर्द्रा", "Punarvasu": "पुनर्वसु", "Pushya": "पुष्य",
    "Ashlesha": "आश्लेषा", "Magha": "मघा", "Hasta": "हस्त", "Chitra": "चित्रा",
    "Swati": "स्वाति", "Vishakha": "विशाखा", "Anuradha": "अनुराधा", "Jyeshtha": "ज्येष्ठा",
    "Mula": "मूल", "Shravana": "श्रवण", "Dhanishta": "धनिष्ठा", "Shatabhisha": "शतभिषा",
    "Revati": "रेवती",
    "Sun": "सूर्य", "Moon": "चंद्र", "Mars": "मंगल", "Mercury": "बुध", "Jupiter": "गुरु",
    "Venus": "शुक्र", "Saturn": "शनि", "Rahu": "राहु", "Ketu": "केतु",
    "Surya": "सूर्य", "Chandra": "चंद्र", "Mangal": "मंगल", "Budh": "बुध", "Guru": "गुरु",
    "Shukra": "शुक्र", "Shani": "शनि",
}
_PLANETS = {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"}
_SIGNS = {"Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
          "Sagittarius", "Capricorn", "Aquarius", "Pisces"}
# fixed astro terms + the recurring English suffix labels on chart chips
_TERMS = {
    "Mahadasha": "महादशा", "Antardasha": "अंतर्दशा", "sub-period": "अंतर्दशा",
    "Sade Sati": "साढ़े साती", "peak phase": "चरम दौर", "rising": "लग्न",
    "your business face": "आपका कारोबारी चेहरा",
    "how you run things": "आप कैसे चलाते हैं",
}
_TOK_RE = re.compile(r"(?<![A-Za-z])(" +
                     "|".join(re.escape(t) for t in sorted(_TOK, key=len, reverse=True)) +
                     r")(?![A-Za-z])")
_HAS_EN = re.compile(r"[A-Za-z]{3,}")


def _token_pass(key):
    """Chart-chip fallback: translate short label runs built from planet/sign
    names + fixed astro terms (e.g. 'Moon in Pisces', 'Ketu Mahadasha — Saturn
    Antardasha'). Returns Devanagari ONLY if the whole chip resolves — a run
    still holding English words is left to HI_DATA / the LLM narrative, so a long
    fallback sentence is never mangled into half-Hindi."""
    # planet-in-sign → natural Hindi word order
    m = re.fullmatch(r"([A-Z][a-z]+) in ([A-Z][a-z]+)", key)
    if m and m.group(1) in _PLANETS and m.group(2) in _SIGNS:
        return _TOK[m.group(2)] + " में " + _TOK[m.group(1)]
    # "until/till/by <date>" → "<date> तक" (तक follows the date in Hindi)
    m = re.fullmatch(r"(?:until|till|by)\s+(.+)", key)
    if m:
        rest = m.group(1).strip()
        chk = re.sub(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b", "", rest)
        if not _HAS_EN.search(chk):
            return rest + " तक"
    if len(key) > 60:
        return None
    out = key
    out = re.sub(r"\b([A-Z][a-z]+)–([A-Z][a-z]+) period\b",
                 lambda x: _TOK.get(x.group(1), x.group(1)) + "–" +
                 _TOK.get(x.group(2), x.group(2)) + " दशा", out)
    out = re.sub(r"\b([A-Z][a-z]+) period\b",
                 lambda x: _TOK.get(x.group(1), x.group(1)) + " दशा", out)
    for en, hi in _TERMS.items():
        out = re.sub(r"\b" + re.escape(en) + r"\b", hi, out)
    out = _TOK_RE.sub(lambda x: _TOK[x.group(1)], out)
    # month abbreviations in date labels (Sep 2029) legitimately stay Latin, like
    # numerals — ignore them when deciding whether English text remains.
    residual = re.sub(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b", "", out)
    return out if (out != key and not _HAS_EN.search(residual)) else None


def _resolve(key, depth=0):
    """Whole text run → Devanagari, or None. Exact HI_DATA lookup first, then
    peel surrounding quotes / leading / trailing emoji and retry recursively,
    then the chart-chip token pass."""
    key = key.strip()
    if not key or depth > 4:
        return None
    if key in HI_DATA:
        return HI_DATA[key]
    q = _QUOTED.match(key)
    if q and q.group(2).strip():
        inner = _resolve(q.group(2), depth + 1)
        if inner is not None:
            return q.group(1) + inner + q.group(3)
    le = _LEAD.match(key)
    if le and le.group(2).strip():
        inner = _resolve(le.group(2), depth + 1)
        if inner is not None:
            return le.group(1) + inner
    te = _TRAIL.match(key)
    if te and te.group(1).strip():
        inner = _resolve(te.group(1), depth + 1)
        if inner is not None:
            return inner + " " + te.group(2).strip()
    # "<chart-chip prefix> — <fragment>" where the fragment is a known HI_DATA
    # phrase (e.g. "Ketu Mahadasha — detachment and endings — a phase to…").
    # Split on the FIRST " — ": translate the short prefix via the token pass,
    # resolve the remainder recursively.
    if " — " in key:
        left, right = key.split(" — ", 1)
        lhs = _token_pass(left.strip())
        rhs = _resolve(right, depth + 1)
        if lhs is not None and rhs is not None:
            return lhs + " — " + rhs
    tp = _token_pass(key)
    if tp is not None:
        return tp
    return None


# Devanagari font retarget: the report's --serif (Fraunces) and --sans
# (system) can't render Devanagari, so point them at Devanagari webfonts. This
# :root is injected just before </head>, AFTER the report's own :root, so it wins.
_HEAD_HI = (
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Tiro+Devanagari+Hindi'
    '&family=Mukta:wght@400;500;600;700;800'
    '&family=Noto+Sans+Devanagari:wght@400;500;600;700&display=swap" rel="stylesheet">'
    "<style>:root{--serif:'Tiro Devanagari Hindi','Noto Serif Devanagari',Georgia,serif;"
    "--sans:'Mukta','Noto Sans Devanagari',system-ui,sans-serif}</style>"
)


def localize(html: str) -> str:
    """Translate the fixed English shell of a rendered vyapar report to Devanagari.
    Safe: only whole text runs present in HI_DATA are swapped; scripts/styles/attrs
    and any unknown text (incl. Devanagari LLM prose, names, numbers) are kept."""
    try:
        holds = []

        def _hold(m):
            holds.append(m.group(0))
            return f"\x00{len(holds) - 1}\x00"

        tmp = _SKIP.sub(_hold, html)

        def _tr(m):
            raw = m.group(1)
            key = _htmlmod.unescape(raw.strip())
            lead = raw[:len(raw) - len(raw.lstrip())]
            tail = raw[len(raw.rstrip()):]
            hi = _resolve(key)
            if hi is not None:
                return ">" + lead + hi + tail + "<"
            return m.group(0)

        tmp = _SEG.sub(_tr, tmp)
        tmp = re.sub(r"\x00(\d+)\x00", lambda m: holds[int(m.group(1))], tmp)

        tmp = tmp.replace('<html lang="en"', '<html lang="hi"', 1)
        tmp = tmp.replace("</head>", _HEAD_HI + "</head>", 1)
        return tmp
    except Exception:
        return html
