# -*- coding: utf-8 -*-
"""
shaadi_hi — Hinglish→Devanagari localizer for the marriage (shaadi) funnel.

Same architecture as milan_hi: translate whole text-runs of an already-rendered
Hinglish page/report to conversational Devanagari. Only runs that fully resolve
(via the HI phrase dict, proper-noun TOK tokens, or a templated pattern) are
swapped; scripts/styles/attributes, names, numbers and anything unknown are left
untouched. Used for:
  * the /hi/marriage landing page  (localize applied to the Hinglish shaadi.html)
  * the Devanagari marriage report  (localize applied to render_report output)

Source of truth text is Hinglish; English values in the codebase's FRAG/EN dicts
were used only as reference while translating.
"""
import re
import html as _htmlmod

from shaadi_hi_data import HI_DATA

# ---------------------------------------------------------------- phrase dict
HI = {}
HI.update(HI_DATA)

# ---------------------------------------------------------------- proper nouns
TOK = {
    # rashis (English + Sanskrit)
    "Aries": "मेष", "Taurus": "वृषभ", "Gemini": "मिथुन", "Cancer": "कर्क",
    "Leo": "सिंह", "Virgo": "कन्या", "Libra": "तुला", "Scorpio": "वृश्चिक",
    "Sagittarius": "धनु", "Capricorn": "मकर", "Aquarius": "कुंभ", "Pisces": "मीन",
    "Mesha": "मेष", "Vrishabha": "वृषभ", "Mithuna": "मिथुन", "Karka": "कर्क",
    "Simha": "सिंह", "Kanya": "कन्या", "Tula": "तुला", "Vrishchika": "वृश्चिक",
    "Dhanu": "धनु", "Makara": "मकर", "Kumbha": "कुंभ", "Meena": "मीन",
    # nakshatras
    "Ashwini": "अश्विनी", "Bharani": "भरणी", "Krittika": "कृत्तिका", "Rohini": "रोहिणी",
    "Mrigashira": "मृगशिरा", "Ardra": "आर्द्रा", "Punarvasu": "पुनर्वसु", "Pushya": "पुष्य",
    "Ashlesha": "आश्लेषा", "Magha": "मघा", "Purva Phalguni": "पूर्व फाल्गुनी",
    "Uttara Phalguni": "उत्तर फाल्गुनी", "Hasta": "हस्त", "Chitra": "चित्रा",
    "Swati": "स्वाति", "Vishakha": "विशाखा", "Anuradha": "अनुराधा", "Jyeshtha": "ज्येष्ठा",
    "Mula": "मूल", "Purva Ashadha": "पूर्व आषाढ़ा", "Uttara Ashadha": "उत्तर आषाढ़ा",
    "Shravana": "श्रवण", "Dhanishta": "धनिष्ठा", "Shatabhisha": "शतभिषा",
    "Purva Bhadrapada": "पूर्व भाद्रपद", "Uttara Bhadrapada": "उत्तर भाद्रपद", "Revati": "रेवती",
    # planets (English + Hindi source spellings used in the report)
    "Sun": "सूर्य", "Moon": "चंद्र", "Mars": "मंगल", "Mercury": "बुध", "Jupiter": "गुरु",
    "Venus": "शुक्र", "Saturn": "शनि", "Rahu": "राहु", "Ketu": "केतु",
    "Surya": "सूर्य", "Chandra": "चंद्र", "Mangal": "मंगल", "Budh": "बुध", "Guru": "गुरु",
    "Shukra": "शुक्र", "Shani": "शनि",
    # elements
    "Fire": "अग्नि", "Earth": "पृथ्वी", "Air": "वायु", "Water": "जल",
}
_TOK_SORTED = sorted(TOK, key=len, reverse=True)
_TOK_RE = re.compile(r"(?<![A-Za-z])(" + "|".join(re.escape(t) for t in _TOK_SORTED) + r")(?![A-Za-z])")
_ASCII_LETTER = re.compile(r"[A-Za-z]")


def _tok_line(key):
    """If every alphabetic word in `key` is a known proper-noun token, return the
    fully Devanagari-substituted string; else None."""
    out = _TOK_RE.sub(lambda m: TOK[m.group(1)], key)
    return out if not _ASCII_LETTER.search(out) else None


# ---------------------------------------------------------------- small maps
MONTHS = {"Jan": "जनवरी", "Feb": "फ़रवरी", "Mar": "मार्च", "Apr": "अप्रैल",
          "May": "मई", "Jun": "जून", "Jul": "जुलाई", "Aug": "अगस्त",
          "Sep": "सितंबर", "Oct": "अक्तूबर", "Nov": "नवंबर", "Dec": "दिसंबर"}
_MON_RE = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b")

# compact planet codes used inside the North-Indian chart grid
PCODE = {"Su": "सू", "Mo": "चं", "Ma": "मं", "Me": "बु", "Ju": "गु",
         "Ve": "शु", "Sa": "श", "Ra": "रा", "Ke": "के"}
_PCODE_RE = re.compile(r"\b(Su|Mo|Ma|Me|Ju|Ve|Sa|Ra|Ke)\b")

GRADE = {"STRONG": "मज़बूत", "MODERATE": "मध्यम", "BUILDING": "निर्माणाधीन",
         "QUIET": "शांत", "ACTIVE": "सक्रिय", "MILD": "हल्का", "NEUTRAL": "सामान्य",
         "Strong": "मज़बूत", "Moderate": "मध्यम", "Building": "निर्माणाधीन",
         "Quiet": "शांत", "Active": "सक्रिय", "Mild": "हल्का"}

DIGNITY = {"own": "अपना", "exalted": "उच्च", "debilitated": "नीच",
           "neutral": "सामान्य", "retro": "वक्री", "combust": "अस्त",
           "own, retro": "अपना, वक्री"}


def _months_line(s):
    """Translate a run whose only ASCII words are month abbreviations / grade words."""
    out = _MON_RE.sub(lambda m: MONTHS[m.group(1)], s)
    out = re.sub(r"\b(STRONG|MODERATE|BUILDING|QUIET|ACTIVE|MILD|NEUTRAL|Strong|Moderate|Building|Quiet|Active|Mild)\b",
                 lambda m: GRADE[m.group(1)], out)
    return out if not _ASCII_LETTER.search(out) else None


# ---------------------------------------------------------------- run matcher
_PAIRS = sorted(HI.items(), key=lambda kv: -len(kv[0]))
_SEG = re.compile(r">([^<>]+)<")
_EMO = r"\U0001F000-\U0001FAFF☀-➿←-⇿⬀-⯿️‍⭐✦✕"
_TRAIL = re.compile(rf"^(.*?)(\s*[{_EMO}]+)\s*$")
_LEAD = re.compile(rf"^([{_EMO}]+\s*)(.*)$")
_QUOTED = re.compile(r'^([“"\'])(.*)([”"\'])$', re.DOTALL)
_SKIP = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)


def _t(s):
    s = s.strip()
    if s in HI:
        return HI[s]
    return _tok_line(s)


def _tt(s):
    return _t(s) or s


# ---- the 12 "Meeting context" phrases keyed by 7th-lord house (1..12) ----
MEETING = [
    "आपकी अपनी पहल या ख़ुद की कोशिशों से",
    "परिवार के नेटवर्क या धन-संपत्ति से",
    "भाई-बहन, पड़ोसी, या छोटी यात्राओं से",
    "घर के दायरे या माँ के पक्ष से",
    "सामाजिक मौक़ों, बच्चों के आयोजनों, या पहले रोमांस से",
    "कार्यस्थल या रोज़मर्रा के दायरों से",
    "सीधे प्रस्तावों से — साझेदारी-प्रेरित",
    "ससुराल के नेटवर्क या रूपांतरकारी परिस्थितियों से",
    "दूर के स्थानों, शिक्षा के दायरों, या किसी अलग समुदाय से",
    "करियर की परिस्थितियों या पिता के नेटवर्क से",
    "दोस्तों के दायरे से — किसी दोस्त के ज़रिए परिचय",
    "शांत या निजी परिस्थितियों से, शायद कुछ दूरी पर",
]


_HINDI_PLANET = {"Surya", "Chandra", "Mangal", "Budh", "Guru", "Shukra", "Shani",
                 "Rahu", "Ketu", "Sun", "Moon", "Mars", "Mercury", "Jupiter",
                 "Venus", "Saturn"}

# venus_style suffixes (engine.py) → Devanagari, applied after the base love-style
_VENUS_SUFFIX = [
    (" — Venus combust hai, isliye expression mein hesitation aa sakti hai; feelings genuine, awaaz dheemi.",
     " — शुक्र अस्त है, इसलिए ज़ाहिर करने में झिझक आ सकती है; भावनाएँ सच्ची, आवाज़ धीमी।"),
    (" — Venus apne hi sign mein strong hai; pyaar mein aapki instinct par bharosa kiya ja sakta hai.",
     " — शुक्र अपनी ही राशि में मज़बूत है; प्रेम में आपकी सहज-प्रवृत्ति पर भरोसा किया जा सकता है।"),
]


def _dasha_side(s):
    """'Venus + Sun + Moon' -> 'शुक्र + सूर्य + चंद्र' if all planets, else None."""
    parts = [x.strip() for x in s.split("+")]
    if all(p in TOK for p in parts):
        return " + ".join(TOK[p] for p in parts)
    return None


def _template(key):
    """Interpolated / structured patterns → Devanagari, or None."""
    # bare grade badge
    if key in GRADE:
        return GRADE[key]
    # "(Grade)" alone
    m = re.match(r"^\((Strong|Moderate|Building|Quiet|Active|Mild)\)$", key)
    if m:
        return f"({GRADE[m.group(1)]})"
    # "{GRADE} WINDOW" / "NO MAJOR WINDOW"
    if key == "NO MAJOR WINDOW":
        return "कोई बड़ी विंडो नहीं"
    m = re.match(r"^(STRONG|MODERATE|BUILDING|QUIET|ACTIVE|MILD) WINDOW$", key)
    if m:
        return f"{GRADE[m.group(1)]} विंडो"
    # "N points" / "N.5 points"
    m = re.match(r"^([\d.]+) points$", key)
    if m:
        return f"{m.group(1)} अंक"
    # "{Planet} 7th house mein"
    m = re.match(r"^(\w+) 7th house mein$", key)
    if m and m.group(1) in TOK:
        return f"{TOK[m.group(1)]} 7वें भाव में"
    # "{Sign} (vargottama)"
    m = re.match(r"^(\w+) \(vargottama\)$", key)
    if m and m.group(1) in TOK:
        return f"{TOK[m.group(1)]} (वर्गोत्तम)"
    # "{Planet}-type — see page 7"
    m = re.match(r"^(\w+)-type — see page 7$", key)
    if m and m.group(1) in TOK:
        return f"{TOK[m.group(1)]}-प्रकार — पेज 7 देखें"
    # "till <Mon YYYY>"
    m = re.match(r"^till (.+)$", key)
    if m and _MON_RE.search(m.group(1)):
        return f"{_months_line(m.group(1))} तक"
    # dignity combos: "own, retro", "exalted, combust", ...
    if re.fullmatch(r"(own|exalted|debilitated|neutral|retro|combust)(, (own|exalted|debilitated|neutral|retro|combust))*", key):
        return ", ".join(DIGNITY[x.strip()] for x in key.split(","))
    # ---- date ranges & month/grade-only runs ----
    if _MON_RE.search(key):
        # "Uske baad: <dates> (Grade)"
        m = re.match(r"^Uske baad: (.+?) \((Strong|Moderate|Building|Quiet|Active|Mild)\)$", key)
        if m:
            return f"उसके बाद: {_months_line(m.group(1)) or m.group(1)} ({GRADE[m.group(2)]})"
        mm = _months_line(key)
        if mm is not None:
            return mm
    # dasha: "X MD — Y[ + Z ...] AD"  (single or multi antardasha)
    m = re.match(r"^(\w+) MD [—-] (.+) AD$", key)
    if m and m.group(1) in TOK:
        ad = _dasha_side(m.group(2))
        if ad is not None:
            return f"{TOK[m.group(1)]} महादशा — {ad} अंतर्दशा"
    m = re.match(r"^(\w+) Mahadasha [—-] (\w+) Antardasha$", key)
    if m and m.group(1) in TOK and m.group(2) in TOK:
        return f"{TOK[m.group(1)]} महादशा — {TOK[m.group(2)]} अंतर्दशा"
    # "Yeh window (<dasha>) ko humne"
    m = re.match(r"^Yeh window \((.+?)\) ko humne$", key)
    if m:
        inner = _resolve(m.group(1), 5)
        if inner is not None:
            return f"इस विंडो ({inner}) को हमने"
    # dignity phrase tail: "{Planet} — <dignity phrase in HI/DIGNITY>"
    m = re.match(r"^(\w+) — (.+)$", key)
    if m and m.group(1) in _HINDI_PLANET and m.group(1) in TOK:
        rest = _resolve(m.group(2), 5)
        if rest is not None:
            return f"{TOK[m.group(1)]} — {rest}"
    # planet dasha-combo joins: "Mercury–Rahu", "Mercury–Rahu / Mercury–Jupiter"
    if re.fullmatch(r"[A-Za-z]+(–[A-Za-z]+)?( / [A-Za-z]+(–[A-Za-z]+)?)*", key):
        parts = re.split(r"( / |–)", key)
        out = "".join(TOK.get(x, x) if x not in (" / ", "–") else x for x in parts)
        if not _ASCII_LETTER.search(out):
            return out
    # compact chart planet-codes: "Su Me Ve Ke", "Ju* Sa", "Mo Ra", "Sa↺"
    if re.fullmatch(r"(?:[A-Z][a-z][*↺]?\s*)+", key.strip()):
        out = _PCODE_RE.sub(lambda mm: PCODE[mm.group(1)], key)
        if not _ASCII_LETTER.search(out):
            return out
    # "Window N"
    m = re.match(r"^Window (\d+)$", key)
    if m:
        return f"विंडो {m.group(1)}"
    # "Window N (dates): Head"  → head is in HI
    m = re.match(r"^Window (\d+) \((.+?)\): (.+)$", key)
    if m:
        dates = _months_line(m.group(2)) or m.group(2)
        head = HI.get(m.group(3), m.group(3))
        return f"विंडो {m.group(1)} ({dates}): {head}"
    # "Core period: <dates>"
    m = re.match(r"^Core period: (.+)$", key)
    if m:
        return f"मुख्य अवधि: {_months_line(m.group(1)) or m.group(1)}"
    # "Top window: <dates> (Grade)"
    m = re.match(r"^Top window: (.+)$", key)
    if m:
        return f"सबसे मज़बूत विंडो: {_months_line(m.group(1)) or m.group(1)}"
    # "⭐ Strongest months: ..."/"⭐ Favourable months: ..."
    m = re.match(r"^⭐ Strongest months: (.+)$", key)
    if m:
        return f"⭐ सबसे मज़बूत महीने: {_months_line(m.group(1)) or m.group(1)}"
    m = re.match(r"^⭐ Favourable months: (.+)$", key)
    if m:
        return f"⭐ अनुकूल महीने: {_months_line(m.group(1)) or m.group(1)}"
    # "7th house — SIGN:"
    m = re.match(r"^7th house — (\w+):$", key)
    if m and m.group(1) in TOK:
        return f"7वाँ भाव — {TOK[m.group(1)]}:"
    # "Darakaraka PLANET:"
    m = re.match(r"^Darakaraka (\w+):$", key)
    if m and m.group(1) in TOK:
        return f"दारकारक {TOK[m.group(1)]}:"
    # "7th lord in house N suggests the connection may come through that area of life — PHRASE."
    m = re.match(r"^7th lord in house (\d+) suggests the connection may come through that area of life — (.+)\.$", key)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 12:
            return (f"7वें भाव का स्वामी {n}वें भाव में होने से इशारा है कि रिश्ता ज़िंदगी "
                    f"के उस हिस्से से आ सकता है — {MEETING[n-1]}।")
    # dignity tails: "PLANET — neutral", "PLANET — neutral dignity", "PLANET — own", ...
    m = re.match(r"^(\w+) — (neutral|own|exalted|debilitated)( dignity)?$", key)
    if m and m.group(1) in TOK:
        dg = DIGNITY[m.group(2)]
        return f"{TOK[m.group(1)]} — {dg}" + (" गरिमा" if m.group(3) else "")
    # "SL — <dignity_txt>" handled in HI (dignity_txt full phrases are literals)
    # "Aapka nakshatra: NAME (SYMBOL)"
    m = re.match(r"^Aapka nakshatra: (.+?) \((.+?)\)$", key)
    if m:
        nm = TOK.get(m.group(1), m.group(1))
        sym = HI.get(m.group(2), m.group(2))
        return f"आपका नक्षत्र: {nm} ({sym})"
    # ---- Navamsa (D9) interpolated reasons ----
    m = re.match(r"^aapka 7th lord \((\w+)\) vargottama hai \(D1 aur D9 mein ek hi rashi\) — marriage promise strong$", key)
    if m and m.group(1) in TOK:
        return (f"आपका 7वें भाव का स्वामी ({TOK[m.group(1)]}) वर्गोत्तम है "
                f"(D1 और D9 में एक ही राशि) — मैरिज प्रॉमिस मज़बूत")
    m = re.match(r"^D9 mein 7th lord \((\w+)\) apni acchi dignity mein hai \((\w+)\)$", key)
    if m and m.group(1) in TOK:
        return f"D9 में 7वें भाव का स्वामी ({TOK[m.group(1)]}) अपनी अच्छी स्थिति में है ({DIGNITY.get(m.group(2), m.group(2))})"
    m = re.match(r"^Venus D9 mein strong hai \((\w+)\)$", key)
    if m:
        return f"शुक्र D9 में मज़बूत है ({DIGNITY.get(m.group(1), m.group(1))})"
    m = re.match(r"^D9 mein 7th lord \((\w+)\) debilitated hai — timing par thoda extra dhyaan$", key)
    if m and m.group(1) in TOK:
        return f"D9 में 7वें भाव का स्वामी ({TOK[m.group(1)]}) नीच है — समय पर थोड़ा अतिरिक्त ध्यान"
    # occupants: "P1, P2 — yeh partnership ke rang ko sabse seedha shape dete hain:"
    m = re.match(r"^(.+) — yeh partnership ke rang ko sabse seedha shape dete hain:$", key)
    if m:
        pls = [x.strip() for x in m.group(1).split(",")]
        if all(p in TOK for p in pls):
            return (", ".join(TOK[p] for p in pls) +
                    " — ये साझेदारी के रंग को सबसे सीधे आकार देते हैं:")
    # sade-sati next phase: "Next phase <date> se. Filhaal Shani ka is angle se koi delay-pressure nahi."
    m = re.match(r"^Next phase (.+) se\. Filhaal Shani ka is angle se koi delay-pressure nahi\.$", key)
    if m:
        d = _months_line(m.group(1)) or m.group(1)
        return f"अगला चरण {d} से। फ़िलहाल शनि का इस एंगल से कोई देरी-दबाव नहीं।"
    # venus love-style: "Your love-style is <base>[<suffix>]."
    m = re.match(r"^Your love-style is (.+)$", key)
    if m:
        inner = m.group(1).rstrip(".").strip()
        for en_suf, hi_suf in _VENUS_SUFFIX:
            en = en_suf.rstrip(".")
            if inner.endswith(en):
                base = inner[:-len(en)].strip()
                if base in HI:
                    return f"आपकी प्रेम-शैली {HI[base]}{hi_suf}"
        if inner in HI:
            return f"आपकी प्रेम-शैली {HI[inner]} है।"
    # generic "... (Moderate)" / "... (Building)" grade suffix on a date line
    m = re.match(r"^(.+) \((Strong|Moderate|Building|Quiet|Active|Mild)\)$", key)
    if m:
        inner = _resolve(m.group(1), 5)
        if inner is not None:
            return f"{inner} ({GRADE[m.group(2)]})"
    return None


def _resolve(key, depth=0):
    key = key.strip()
    if not key or depth > 5:
        return None
    if key in HI:
        return HI[key]
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
    # " · "-separated lists (rule why-lists, legends): resolve each atom
    if " · " in key:
        parts = key.split(" · ")
        res = [_resolve(pp, depth + 1) for pp in parts]
        if all(r is not None for r in res):
            return " · ".join(res)
    # ", "-separated lists (e.g. manglik cancellation reasons) — only if every
    # part independently resolves (prose with commas won't, so it's left alone)
    if ", " in key and " · " not in key and len(key.split(", ")) <= 4:
        parts = key.split(", ")
        res = [_resolve(pp, depth + 1) for pp in parts]
        if all(r is not None for r in res):
            return ", ".join(res)
    tk = _tok_line(key)
    if tk is not None:
        return tk
    return _template(key)


def _neutralize_toggle(html):
    """On a Devanagari page/report the client Hinglish↔English swap must not run
    (it would replace Devanagari nodes like 'नहीं' via the EXACT map). Force the
    saved language to 'hi' everywhere the funnel defaults to 'en', and hide the
    in-page Hinglish/English capsule (language is fixed by URL for /hi/*)."""
    html = html.replace("var l = localStorage.getItem('axlang') || 'en';",
                        "var l = 'hi';")
    html = html.replace("var saved='en'; try{ saved=localStorage.getItem('axlang')||'en'; }catch(e){}",
                        "var saved='hi';")
    html = html.replace("var saved='en';try{saved=localStorage.getItem('axlang')||'en';}catch(e){}",
                        "var saved='hi';")
    return html


def localize(html):
    """Translate the Hinglish shell of a rendered page/report to Devanagari."""
    holds = []

    def _hold(m):
        holds.append(m.group(0))
        return f"\x00{len(holds)-1}\x00"
    tmp = _SKIP.sub(_hold, html)

    def _tr(m):
        raw = m.group(1)
        # collapse internal whitespace so multi-line source runs match the dict keys
        key = re.sub(r"\s+", " ", _htmlmod.unescape(raw.strip()))
        lead = raw[:len(raw) - len(raw.lstrip())]
        tail = raw[len(raw.rstrip()):]
        hi = _resolve(key)
        if hi is not None:
            return ">" + lead + hi + tail + "<"
        return m.group(0)
    tmp = _SEG.sub(_tr, tmp)

    tmp = re.sub(r"\x00(\d+)\x00", lambda m: holds[int(m.group(1))], tmp)

    tmp = _neutralize_toggle(tmp)
    tmp = tmp.replace('<html lang="hi-IN"', '<html lang="hi"', 1)
    tmp = tmp.replace('<html lang="en"', '<html lang="hi"', 1)
    if "</head>" in tmp:
        tmp = tmp.replace("</head>", _HEAD_HI + "</head>", 1)
    return tmp


_HEAD_HI = (
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Mukta:wght@400;500;600;700;800'
    '&family=Noto+Sans+Devanagari:wght@400;500;600;700&display=swap" rel="stylesheet">'
    "<style>:root{--display:'Mukta','Noto Sans Devanagari',system-ui,sans-serif;"
    "--body:'Noto Sans Devanagari','Mukta',system-ui,sans-serif;"
    "--disp:'Mukta','Noto Sans Devanagari',system-ui,sans-serif}"
    "#axlang{display:none!important}</style>"
)
