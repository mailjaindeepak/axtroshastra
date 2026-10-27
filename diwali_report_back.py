"""Diwali report, back half (RENDER-B): Better luck → Sade Sati → strengths → months to go slow →
12 months → Part 2 · Your Diwali → end plan → back pages.

cards_back(payload, prose) -> list[str], one `<section class="page …">` per card, markup copied from
docs/diwali/mock/kit-3c/m3_4_luck_year.html, m3_5_diwali.html, m3_6_plan_back.html. Only data and
text change: chart-derived words come from `prose(key)` (narrative or bank) or the payload; pictures
are drawn from payload months/states. Page refs are `p.@@<card-id>@@` (the assembler fills them).
"""
from html import escape
import re
import textwrap
from datetime import date

from diwali_bank import has_best, lint_text

MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
AREA_LABEL = {"money": "Money", "career": "Career", "business": "Business", "family": "Family",
              "marriage": "Marriage", "luck": "Better luck"}
AREA_ICON = {"money": "i-coins", "career": "i-trend", "business": "i-store", "family": "i-people",
             "marriage": "i-marigold", "luck": "i-diya"}
PL_ABBR = {"Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me", "Jupiter": "Ju", "Venus": "Ve",
           "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke"}
WORDS = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve"]
TOCL = '<a class="tocl" href="#contents">Contents</a><div class="pgn"></div></section>'
DIYA = '<svg class="diya-i"><use href="#i-diya"/></svg>'
RANG = '<svg class="rangoli"><use href="#i-rangoli"/></svg>'


def e(s):
    return escape(str(s if s is not None else ""), quote=False).replace("@", "&#64;")  # keep p.@@id@@ markers out of text


def ea(s):
    return escape(str(s if s is not None else ""), quote=True).replace("@", "&#64;")  # keep p.@@id@@ markers out of text


def link(cid, text, arrow=True):
    return f'<a class="xr" href="#{cid}">{text}, p.@@{cid}@@{" →" if arrow else ""}</a>'


def ordinal(n):
    n = int(n)
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def sign(s):
    """Plain sign name; Cancer is always Karka (R3)."""
    s = re.sub(r"\s*\(.*?\)", "", str(s or "")).strip()
    return "Karka" if s.lower() in ("cancer", "karka") else s


def sign3(s):
    s = sign(s)
    return s if s == "Karka" else s[:3]


def day_label(iso):
    """'2026-11-06' -> 'Fri 6 Nov' (mock 3C date table format)."""
    try:
        d = date.fromisoformat(iso)
    except (TypeError, ValueError):
        return str(iso or "")
    return f"{d:%a} {d.day} {MON[d.month - 1]}"


def time_range(a, b):
    """'17:54','19:50' -> '5:54 – 7:50 pm' (mock 3C puja table format)."""
    def t(x):
        h, m = (int(v) for v in str(x).split(":"))
        return f"{(h - 1) % 12 + 1}:{m:02d}", "am" if h < 12 else "pm"
    try:
        (s1, p1), (s2, p2) = t(a), t(b)
    except ValueError:
        return f"{a} – {b}"
    return f"{s1} – {s2} {p2}" if p1 == p2 else f"{s1} {p1} – {s2} {p2}"


def ym_parts(ym):
    y, m = ym.split("-")
    return int(y), int(m)


def ym_label(ym):
    y, m = ym_parts(ym)
    return f"{MON[m - 1]} {y}"


def runs(yms):
    """Consecutive-month runs: [["2027-06","2027-07"], ["2027-09"]]."""
    out = []
    for ym in sorted(yms):
        y, m = ym_parts(ym)
        if out:
            py, pm = ym_parts(out[-1][-1])
            if (py * 12 + pm) + 1 == y * 12 + m:
                out[-1].append(ym)
                continue
        out.append([ym])
    return out


def run_short(r):
    """'Jun–Jul' or 'Nov' (no year: tally boxes)."""
    a, b = MON[ym_parts(r[0])[1] - 1], MON[ym_parts(r[-1])[1] - 1]
    return a if r[0] == r[-1] else f"{a}–{b}"


def run_long(r):
    """'Jan–Feb 2027', 'Dec 2026 – Jan 2027', 'May 2027'."""
    (ya, ma), (yb, mb) = ym_parts(r[0]), ym_parts(r[-1])
    if r[0] == r[-1]:
        return f"{MON[ma - 1]} {ya}"
    if ya == yb:
        return f"{MON[ma - 1]}–{MON[mb - 1]} {ya}"
    return f"{MON[ma - 1]} {ya} – {MON[mb - 1]} {yb}"


def span_label(a, b):
    """Headline range: 'Nov 2026 – Apr 2027' or 'May – Oct 2027'."""
    (ya, ma), (yb, mb) = ym_parts(a), ym_parts(b)
    if a == b:
        return ym_label(a)
    if ya == yb:
        return f"{MON[ma - 1]} – {MON[mb - 1]} {yb}"
    return f"{MON[ma - 1]} {ya} – {MON[mb - 1]} {yb}"


def wrap2(text, width=16):
    lines = textwrap.wrap(text, width) or [""]
    return lines[0], " ".join(lines[1:])


# ---------------------------------------------------------------- pictures (exact kit-3c markup)

KX = [30.8, 92.5, 154.2, 215.8, 277.5, 339.2]
KY = [14.8, 18.8, 20.8, 20.8, 18.8, 14.8]
_K_TASSEL = ('<line x1="0" y1="0" x2="0" y2="16" stroke="#B9862E" stroke-width="1.2"/>'
             '<path d="M-10 82 q3 10 0 20 q-3 5 0 10" fill="none" stroke="#7A2E36" stroke-width="2" stroke-linecap="round"/>'
             '<path d="M-5 82 q3 8 0 16 q-3 4 0 8" fill="none" stroke="#E39B2B" stroke-width="2" stroke-linecap="round"/>'
             '<path d="M0 82 q3 10 0 20 q-3 5 0 10" fill="none" stroke="#7A2E36" stroke-width="2" stroke-linecap="round"/>'
             '<path d="M5 82 q3 8 0 16 q-3 4 0 8" fill="none" stroke="#E39B2B" stroke-width="2" stroke-linecap="round"/>'
             '<path d="M10 82 q3 10 0 20 q-3 5 0 10" fill="none" stroke="#7A2E36" stroke-width="2" stroke-linecap="round"/>'
             '<rect x="-8" y="16" width="16" height="6" rx="1.5" fill="#C9A34E" stroke="#B9862E" stroke-width="1"/>')
_K_BAND = ('<rect x="-26" y="46" width="52" height="12" fill="#7A2E36" stroke="#B9862E" stroke-width="1.2" />'
           '<g fill="#F2C14E"><circle cx="-17" cy="52" r="1.6"/><circle cx="-6" cy="52" r="1.6"/><circle cx="6" cy="52" r="1.6"/><circle cx="17" cy="52" r="1.6"/></g>'
           '<path d="M-6 22 L-10 46 M6 22 L10 46 M-10 58 L-6 82 M10 58 L6 82" stroke="#B9862E" stroke-width=".9" fill="none" opacity=".8"/>')
_K_GOOD = ('<circle cx="0" cy="52" r="40" fill="none" stroke="#B9862E" stroke-width="1.3"/>' + _K_TASSEL +
           '<path d="M-12 22 L12 22 L26 46 L26 58 L12 82 L-12 82 L-26 58 L-26 46Z" fill="#F7E2A6" stroke="#B9862E" stroke-width="1.4" stroke-linejoin="round" />'
           + _K_BAND)
_K_RAYS = "".join(
    f'<line x1="{a}" y1="{b}" x2="{c}" y2="{d}" stroke="#B9862E" stroke-width="2.2" stroke-linecap="round"/>'
    for a, b, c, d in [("22.0", "13.9", "29.0", "1.8"), ("38.1", "30.0", "50.2", "23.0"), ("44.0", "52.0", "58.0", "52.0"),
                       ("38.1", "74.0", "50.2", "81.0"), ("22.0", "90.1", "29.0", "102.2"), ("0.0", "96.0", "0.0", "110.0"),
                       ("-22.0", "90.1", "-29.0", "102.2"), ("-38.1", "74.0", "-50.2", "81.0"), ("-44.0", "52.0", "-58.0", "52.0"),
                       ("-38.1", "30.0", "-50.2", "23.0"), ("-22.0", "13.9", "-29.0", "1.8")])
_K_BEST = ('<circle cx="0" cy="52" r="58" fill="url(#a4halo)"/>' + _K_RAYS + _K_TASSEL +
           '<path d="M-12 22 L12 22 L26 46 L26 58 L12 82 L-12 82 L-26 58 L-26 46Z" fill="url(#a4lit)" stroke="#B9862E" stroke-width="1.8" stroke-linejoin="round" />'
           + _K_BAND +
           '<path d="M40 6 Q40 12 46 12 Q40 12 40 18 Q40 12 34 12 Q40 12 40 6Z" fill="#F2C14E" stroke="#B9862E" stroke-width=".7"/>'
           '<path d="M-42 73 Q-42 78 -37 78 Q-42 78 -42 83 Q-42 78 -47 78 Q-42 78 -42 73Z" fill="#F2C14E" stroke="#B9862E" stroke-width=".7"/>')
_K_CARE = ('<line x1="0" y1="0" x2="0" y2="16" stroke="#B9862E" stroke-width="1.2"/>'
           '<path d="M-10 82 q3 8 0 15 q-3 4 0 8" fill="none" stroke="#9C907A" stroke-width="2" stroke-linecap="round"/>'
           '<path d="M-5 82 q3 6 0 12 q-3 3 0 6" fill="none" stroke="#9C907A" stroke-width="2" stroke-linecap="round"/>'
           '<path d="M0 82 q3 8 0 15 q-3 4 0 8" fill="none" stroke="#9C907A" stroke-width="2" stroke-linecap="round"/>'
           '<path d="M5 82 q3 6 0 12 q-3 3 0 6" fill="none" stroke="#9C907A" stroke-width="2" stroke-linecap="round"/>'
           '<path d="M10 82 q3 8 0 15 q-3 4 0 8" fill="none" stroke="#9C907A" stroke-width="2" stroke-linecap="round"/>'
           '<rect x="-8" y="16" width="16" height="6" rx="1.5" fill="#E9E3D6" stroke="#9C907A" stroke-width="1"/>'
           '<path d="M-12 22 L12 22 L26 46 L26 58 L12 82 L-12 82 L-26 58 L-26 46Z" fill="#E9E3D6" stroke="#9C907A" stroke-width="1.4" stroke-linejoin="round" stroke-dasharray="3.2 2.4"/>'
           '<rect x="-26" y="46" width="52" height="12" fill="none" stroke="#9C907A" stroke-width="1.2" stroke-dasharray="3.2 2.4"/>'
           '<g fill="#9C907A"><circle cx="-17" cy="52" r="1.6"/><circle cx="-6" cy="52" r="1.6"/><circle cx="6" cy="52" r="1.6"/><circle cx="17" cy="52" r="1.6"/></g>'
           '<path d="M-6 22 L-10 46 M6 22 L10 46 M-10 58 L-6 82 M10 58 L6 82" stroke="#9C907A" stroke-width=".9" fill="none" opacity=".8"/>')
_K_DEFS = ('<defs><radialGradient id="a4halo"><stop offset="0" stop-color="#F2C14E" stop-opacity=".85"/><stop offset=".6" stop-color="#F2C14E" stop-opacity=".45"/><stop offset="1" stop-color="#F2C14E" stop-opacity="0"/></radialGradient>'
           '<linearGradient id="a4lit" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F8D978"/><stop offset="1" stop-color="#E39B2B"/></linearGradient></defs>')
_K_DOTS = ('<g fill="#E39B2B"><circle cx="10" cy="12.9" r="2.2"/><circle cx="50" cy="16.2" r="2.2"/><circle cx="70" cy="17.5" r="2.2"/><circle cx="110" cy="19.5" r="2.2"/><circle cx="130" cy="20.2" r="2.2"/><circle cx="170" cy="20.9" r="2.2"/><circle cx="190" cy="21.0" r="2.2"/><circle cx="230" cy="20.5" r="2.2"/><circle cx="250" cy="19.9" r="2.2"/><circle cx="270" cy="19.1" r="2.2"/><circle cx="290" cy="18.1" r="2.2"/><circle cx="310" cy="16.9" r="2.2"/><circle cx="330" cy="15.5" r="2.2"/><circle cx="350" cy="13.8" r="2.2"/></g>')


def kandils_svg(months, with_defs):
    """Six akash kandils (No. 6), state marks v3: best / good / steady / careful."""
    h = 139 if with_defs else 141
    out = [f'<svg viewBox="0 0 370 {h}" width="100%" role="img" aria-label="Six akash kandils, one per month" style="display:block;margin-top:14px">'
           '<style>.nm{font:600 13.5px Fraunces,Georgia,serif;fill:#1B1D2A}.mo{font:500 10px Inter,sans-serif;fill:#4C4A57}.cr{font:500 10px Inter,sans-serif;fill:#B4572B}.rh{font:700 9px Inter,sans-serif;letter-spacing:.14em;fill:#B9862E}</style>',
           _K_DEFS if with_defs else "", '<path d="M0 12 Q185 30 370 12" fill="none" stroke="#3E7D5A" stroke-width="1.1"/>']
    for i, mo in enumerate(months[:6]):
        x, y, tone = KX[i], KY[i], mo.get("tone")
        if tone == "best":
            body, sc = _K_BEST, "0.6"
            pill = (f'<rect x="{x - 21.8:.1f}" y="120.8" width="43.6" height="14.2" rx="7.1" fill="#3E7D5A"/>'
                    f'<text x="{x}" y="130.8" text-anchor="middle" style="font:700 7.2px Inter,sans-serif;fill:#fff">Best time</text>')
        elif tone == "careful":
            body, sc = _K_CARE, "0.48"
            pill = (f'<rect x="{x - 27.8:.1f}" y="120.8" width="55.5" height="14.2" rx="7.1" fill="none" stroke="#B4572B" stroke-width="1.1" stroke-dasharray="3.2 2.4"/>'
                    f'<text x="{x}" y="130.8" text-anchor="middle" style="font:700 7.2px Inter,sans-serif;fill:#B4572B">Careful time</text>')
        else:
            body, sc = _K_GOOD, "0.516"
            pill = (f'<rect x="{x - 21.8:.1f}" y="120.8" width="43.6" height="14.2" rx="7.1" fill="#FFFDF8" stroke="#B9862E" stroke-width="1.2"/>'
                    f'<text x="{x}" y="130.8" text-anchor="middle" style="font:700 7.2px Inter,sans-serif;fill:#8A6420">{"Good time" if tone == "good" else "Steady"}</text>')
        out.append(f'<g transform="translate({x} {y}) scale({sc})">{body}</g>'
                   f'<text x="{x}" y="102" text-anchor="middle" class="nm" style="font-size:13px">{e(mo.get("label"))}</text>'
                   f'<text x="{x}" y="114" text-anchor="middle" class="mo" style="font-size:9px">{e(mo.get("year"))}</text>' + pill)
    out.append(_K_DOTS + "</svg>")
    return "".join(out)


def _anar(x, best):
    if best:
        g = ('<ellipse cx="0" cy="-116" rx="48" ry="75" fill="url(#a4halo2)"/>'
             '<path d="M0 -30 Q-14.3 -254.0 -26.0 -59.0" fill="none" stroke="#D9692A" stroke-width="3.2" stroke-linecap="round" stroke-dasharray="0.01 6.5"/>'
             '<path d="M0 -30 Q-7.2 -290.0 -13.0 -59.0" fill="none" stroke="#E39B2B" stroke-width="3.2" stroke-linecap="round" stroke-dasharray="0.01 6.5"/>'
             '<path d="M0 -30 L0 -176" fill="none" stroke="#D9692A" stroke-width="3.2" stroke-linecap="round" stroke-dasharray="0.01 6.5"/>'
             '<path d="M0 -30 Q7.2 -290.0 13.0 -59.0" fill="none" stroke="#E39B2B" stroke-width="3.2" stroke-linecap="round" stroke-dasharray="0.01 6.5"/>'
             '<path d="M0 -30 Q14.3 -254.0 26.0 -59.0" fill="none" stroke="#D9692A" stroke-width="3.2" stroke-linecap="round" stroke-dasharray="0.01 6.5"/>'
             '<line x1="0.0" y1="-186.0" x2="0.0" y2="-196.0" stroke="#B9862E" stroke-width="2" stroke-linecap="round"/>'
             '<line x1="4.2" y1="-184.2" x2="11.3" y2="-191.3" stroke="#B9862E" stroke-width="2" stroke-linecap="round"/>'
             '<line x1="6.0" y1="-180.0" x2="16.0" y2="-180.0" stroke="#B9862E" stroke-width="2" stroke-linecap="round"/>'
             '<line x1="-6.0" y1="-180.0" x2="-16.0" y2="-180.0" stroke="#B9862E" stroke-width="2" stroke-linecap="round"/>'
             '<line x1="-4.2" y1="-184.2" x2="-11.3" y2="-191.3" stroke="#B9862E" stroke-width="2" stroke-linecap="round"/>'
             '<path d="M0 -186 Q0 -180 6 -180 Q0 -180 0 -174 Q0 -180 -6 -180 Q0 -180 0 -186Z" fill="#F2C14E" stroke="#B9862E" stroke-width=".7"/>'
             '<path d="M-32 -143.5 Q-32 -138.5 -27 -138.5 Q-32 -138.5 -32 -133.5 Q-32 -138.5 -37 -138.5 Q-32 -138.5 -32 -143.5Z" fill="#F2C14E" stroke="#B9862E" stroke-width=".7"/>'
             '<path d="M32 -124.0 Q32 -119.0 37 -119.0 Q32 -119.0 32 -114.0 Q32 -119.0 27 -119.0 Q32 -119.0 32 -124.0Z" fill="#F2C14E" stroke="#B9862E" stroke-width=".7"/>'
             '<path d="M-5 -26 L5 -26 L13 0 L-13 0Z" fill="url(#a4lit2)" stroke="#B9862E" stroke-width="1.7" stroke-linejoin="round" />')
        pill = (f'<rect x="{x - 32.6:.1f}" y="140" width="65.3" height="15" rx="7.5" fill="#3E7D5A"/>'
                f'<text x="{x}" y="150.8" text-anchor="middle" style="font:700 8px Inter,sans-serif;letter-spacing:.08em;fill:#fff">BEST TIME</text>')
    else:
        g = ('<path d="M0 -30 Q-8.2 -144.6 -15.0 -43.2" fill="none" stroke="#B9862E" stroke-width="2.4" stroke-linecap="round" stroke-dasharray="0.01 7.5"/>'
             '<path d="M0 -30 Q-4.1 -163.3 -7.5 -43.2" fill="none" stroke="#E39B2B" stroke-width="2.4" stroke-linecap="round" stroke-dasharray="0.01 7.5"/>'
             '<path d="M0 -30 L0 -104" fill="none" stroke="#B9862E" stroke-width="2.4" stroke-linecap="round" stroke-dasharray="0.01 7.5"/>'
             '<path d="M0 -30 Q4.1 -163.3 7.5 -43.2" fill="none" stroke="#E39B2B" stroke-width="2.4" stroke-linecap="round" stroke-dasharray="0.01 7.5"/>'
             '<path d="M0 -30 Q8.2 -144.6 15.0 -43.2" fill="none" stroke="#B9862E" stroke-width="2.4" stroke-linecap="round" stroke-dasharray="0.01 7.5"/>'
             '<path d="M-5 -26 L5 -26 L13 0 L-13 0Z" fill="#F3DDB8" stroke="#B9862E" stroke-width="1.3" stroke-linejoin="round" />')
        pill = (f'<rect x="{x - 32.6:.1f}" y="140" width="65.3" height="15" rx="7.5" fill="#FFFDF8" stroke="#B9862E" stroke-width="1.2"/>'
                f'<text x="{x}" y="150.8" text-anchor="middle" style="font:700 8px Inter,sans-serif;letter-spacing:.08em;fill:#8A6420">GOOD TIME</text>')
    return (f'<g transform="translate({x} 132) scale(0.6)">{g}<path d="M-8.4 -15 L8.4 -15" stroke="#7A2E36" stroke-width="2.2"/></g>' + pill)


def anars_svg(highlights):
    """No. 5 anar fountains: [(month dict, is_turning_point, caption)] (1–4)."""
    n = len(highlights)
    xs = [48, 139, 231, 322] if n == 4 else [round(371 * (2 * i + 1) / (2 * n), 1) for i in range(n)]
    out = ['<svg viewBox="0 0 371 222" width="100%" role="img" aria-label="Four anar fountains marking the best-time highlights" style="display:block;margin-top:10px">'
           '<style>.nm{font:600 13.5px Fraunces,Georgia,serif;fill:#1B1D2A}.mo{font:500 9.5px Inter,sans-serif;fill:#4C4A57}.tp{font:700 7.5px Inter,sans-serif;letter-spacing:.1em;fill:#3E7D5A}</style>'
           '<defs><radialGradient id="a4halo2"><stop offset="0" stop-color="#F2C14E" stop-opacity=".85"/><stop offset=".6" stop-color="#F2C14E" stop-opacity=".45"/><stop offset="1" stop-color="#F2C14E" stop-opacity="0"/></radialGradient>'
           '<linearGradient id="a4lit2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F8D978"/><stop offset="1" stop-color="#E39B2B"/></linearGradient></defs>']
    out += [f'<text x="{x}" y="14" text-anchor="middle" class="tp">TURNING POINT</text>'
            for x, (_, tp, _c) in zip(xs, highlights) if tp]
    for x, (mo, _tp, cap) in zip(xs, highlights):
        l1, l2 = wrap2(cap)
        out.append(_anar(x, mo.get("tone") == "best") +
                   f'<text x="{x}" y="172" text-anchor="middle" class="nm">{e(mo.get("label"))}</text>'
                   f'<text x="{x}" y="184" text-anchor="middle" class="mo" style="font-size:9px">{e(mo.get("year"))}</text>'
                   f'<text x="{x}" y="198" text-anchor="middle" class="mo">{e(l1)}</text>'
                   f'<text x="{x}" y="209" text-anchor="middle" class="mo">{e(l2)}</text>')
    out.append("</svg>")
    return "".join(out)


_D_LIT = ('<circle cx="0" cy="-14" r="34" fill="url(#a5halo)"/>'
          + "".join(f'<line x1="{a}" y1="{b}" x2="{c}" y2="{d}" stroke="#B9862E" stroke-width="2" stroke-linecap="round"/>'
                    for a, b, c, d in [("-25.0", "-14.0", "-34.0", "-14.0"), ("-21.7", "-26.5", "-29.4", "-31.0"),
                                       ("-12.5", "-35.7", "-17.0", "-43.4"), ("0.0", "-39.0", "0.0", "-48.0"),
                                       ("12.5", "-35.7", "17.0", "-43.4"), ("21.7", "-26.5", "29.4", "-31.0"),
                                       ("25.0", "-14.0", "34.0", "-14.0")])
          + '<path d="M0 -31.0 C14.3 -12.3 12.9 3 0 3 C-12.9 3 -14.3 -12.3 0 -31.0Z" fill="#E39B2B" stroke="#D9692A" stroke-width=".8"/>'
            '<path d="M0 -14.7 C5.7 -5.2 5.0 3 0 3 C-5.0 3 -5.7 -5.2 0 -14.7Z" fill="#FFF3C2"/>'
            '<path d="M-24 0 Q0 24 24 0 Q0 5 -24 0Z" fill="url(#a5lit)" stroke="#B9862E" stroke-width="1.9" stroke-linejoin="round"/>'
            '<path d="M-13 7 Q0 13 13 7" fill="none" stroke="#7A2E36" stroke-width="1" stroke-dasharray="1.5 2.5"/>')
_D_GOOD = ('<circle cx="0" cy="-6" r="17" fill="none" stroke="#B9862E" stroke-width="1.3"/>'
           '<path d="M0 -15.0 C7.6 -5.1 6.8 3 0 3 C-6.8 3 -7.6 -5.1 0 -15.0Z" fill="#E39B2B" stroke="#D9692A" stroke-width=".8"/>'
           '<path d="M0 -6.4 C3.0 -1.3 2.6 3 0 3 C-2.6 3 -3.0 -1.3 0 -6.4Z" fill="#FFF3C2"/>'
           '<path d="M-24 0 Q0 24 24 0 Q0 5 -24 0Z" fill="#FBF4E7" stroke="#B9862E" stroke-width="1.5" stroke-linejoin="round"/>'
           '<path d="M-13 7 Q0 13 13 7" fill="none" stroke="#C9A34E" stroke-width="1" stroke-dasharray="1.5 2.5"/>')
_D_CARE = ('<circle cx="0" cy="0" r="1.8" fill="#9C907A"/>'
           '<path d="M0 -3 q-3 -4 0 -8 q3 -4 0 -8" fill="none" stroke="#9C907A" stroke-width="1" stroke-linecap="round" opacity=".8"/>'
           '<path d="M-24 0 Q0 24 24 0 Q0 5 -24 0Z" fill="#E9E3D6" stroke="#9C907A" stroke-width="1.5" stroke-linejoin="round" stroke-dasharray="3.2 2.4"/>'
           '<path d="M-13 7 Q0 13 13 7" fill="none" stroke="#9C907A" stroke-width="1" stroke-dasharray="1.5 2.5"/>')
DX = [30.8, 92.5, 154.1, 215.8, 277.5, 339.2]


def gold_svg(months, gold):
    """No. 1 diyas, one per month: lit = best for gold / best overall."""
    out = ['<svg viewBox="0 0 370 250" width="100%" role="img" aria-label="Twelve diyas, one per month; the fully lit ones are the best months for gold or the best months overall; the others show their usual good, steady or careful tone" style="display:block;margin-top:14px">'
           '<defs><radialGradient id="a5halo"><stop offset="0" stop-color="#F2C14E" stop-opacity=".85"/><stop offset=".6" stop-color="#F2C14E" stop-opacity=".45"/><stop offset="1" stop-color="#F2C14E" stop-opacity="0"/></radialGradient>'
           '<linearGradient id="a5lit" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F8D978"/><stop offset="1" stop-color="#E39B2B"/></linearGradient></defs>'
           '<line x1="0" y1="128" x2="370" y2="128" stroke="#E6DCC6" stroke-width="1"/>']
    for i, mo in enumerate(months[:12]):
        x, y = DX[i % 6], (62 if i < 6 else 186)
        tone, is_gold = mo.get("tone"), mo.get("ym") in gold
        tag = None
        if is_gold or tone == "best":
            body, sc, tag = _D_LIT, "0.78", ("BEST FOR GOLD" if is_gold else "BEST OVERALL")
            nm = "700 11px Inter,sans-serif;fill:#1B1D2A" if is_gold else "600 11px Inter,sans-serif;fill:#4C4A57"
        elif tone == "careful":
            body, sc, nm, word, col = _D_CARE, "0.68", "600 11px Inter,sans-serif;fill:#9C907A", "CAREFUL", "#B4572B"
        else:
            body, sc, nm, col = _D_GOOD, "0.72", "600 11px Inter,sans-serif;fill:#4C4A57", "#8A6420"
            word = "GOOD" if tone == "good" else "STEADY"
        out.append(f'<g transform="translate({x} {y}) scale({sc})">{body}</g>'
                   f'<text x="{x}" y="{y + 30}" text-anchor="middle" style="font:{nm}">{e(mo.get("label"))}</text>'
                   f'<text x="{x}" y="{y + 41}" text-anchor="middle" style="font:500 8px Inter,sans-serif;fill:#A79A7E">{e(mo.get("year"))}</text>')
        if tag:
            out.append(f'<rect x="{x - 29:.1f}" y="{y + 47}" width="58" height="13" rx="6.5" fill="#3E7D5A"/>'
                       f'<text x="{x}" y="{y + 56.5}" text-anchor="middle" style="font:700 6px Inter,sans-serif;letter-spacing:.03em;fill:#fff">{tag}</text>')
        else:
            out.append(f'<text x="{x}" y="{y + 56.5}" text-anchor="middle" style="font:700 7px Inter,sans-serif;letter-spacing:.04em;fill:{col}">{word}</text>')
    out.append("</svg>")
    return "".join(out)


SS_LABEL = {"rising": "FIRST PHASE", "peak": "PEAK PHASE", "setting": "LAST PHASE", "pause": "PAUSE",
            "return": "SHORT RETURN", "none": "NOT ACTIVE"}
SS_X0, SS_PX, SS_X1 = 14.0, 20.2, 348.95  # Nov of this Diwali at 14, 20.2 px per month, strip ends ~Mar after next Diwali


def ss_segments(sade_sati, base_ym):
    """[(kind, from_ym, to_ym)] inside the strip; gaps between phases become 'pause', a phase repeated
    after a pause becomes 'return'. No phase at all → one 'none' segment."""
    by, bm = ym_parts(base_ym)
    idx = lambda ym: (ym_parts(ym)[0] - by) * 12 + ym_parts(ym)[1] - bm
    last_i = int((SS_X1 - SS_X0) / SS_PX)
    ph = sorted((p for p in (sade_sati or {}).get("phases") or [] if idx(p["to"]) >= 0 and idx(p["from"]) <= last_i),
                key=lambda p: p["from"])
    order = {"rising": 0, "peak": 1, "setting": 2}
    segs, seen, last = [], set(), -1
    for p in ph:
        if segs and idx(p["from"]) - idx(segs[-1][2]) > 1:
            segs.append(("pause", _shift(segs[-1][2], 1), _shift(p["from"], -1)))
        kind = p["phase"]
        # a phase seen before, after a pause or after a later phase (Saturn stepping back), is a return
        if kind in order and kind in seen and (segs[-1][0] == "pause" or order[kind] < last):
            kind = "return"
        if p["phase"] in order:
            seen.add(p["phase"])
            last = max(last, order[p["phase"]])
        segs.append((kind, p["from"], p["to"]))
    if not segs:
        segs = [("none", base_ym, _shift(base_ym, last_i))]
    return segs, idx


def _shift(ym, k):
    y, m = ym_parts(ym)
    t = y * 12 + m - 1 + k
    return f"{t // 12}-{t % 12 + 1:02d}"


def ss_text_w(s):
    """Rough width of a .ph pill label (700 8.5px caps, .1em tracking)."""
    return len(s) * 6.6


def sadesati_svg(segs, idx):
    out = ['<svg viewBox="0 0 373 122" width="100%" role="img" aria-label="Sade Sati phases" style="display:block;margin-top:12px">\n'
           '<style>.ph{font:700 8.5px Inter,sans-serif;letter-spacing:.1em}.ml{font:500 9.5px Inter,sans-serif;fill:#4C4A57}.sm{font:500 8.5px Inter,sans-serif;fill:#8A8199}</style>\n']
    labels = []
    last_i = int((SS_X1 - SS_X0) / SS_PX)
    for n, (kind, a, b) in enumerate(segs):
        x0 = max(SS_X0, SS_X0 + idx(a) * SS_PX) + (2 if n else 0)
        x1 = min(SS_X1, SS_X0 + (idx(b) + 1) * SS_PX)
        w, cx = max(x1 - x0, 6), (x0 + x1) / 2
        if kind in ("pause", "none"):
            out.append(f'<rect x="{x0:.1f}" y="58" width="{w:.1f}" height="24" rx="12" fill="#F7E2A6" stroke="#B9862E" stroke-width="1.4"/>\n')
            fill = "#8A6420"
        else:
            out.append(f'<rect x="{x0:.1f}" y="58" width="{w:.1f}" height="24" rx="12" fill="#E9E3D6" stroke="#9C907A" stroke-width="1.3" stroke-dasharray="3.2 2.4"/>\n')
            fill = "#6E6553"
        lab = SS_LABEL.get(kind, e(kind).upper())
        if ss_text_w(lab) + 10 > w:  # too narrow for the full label: try the first word, else leave it to the legend
            lab = {"SHORT RETURN": "RETURN", "NOT ACTIVE": "NONE"}.get(lab, lab.split()[0])
        if ss_text_w(lab) + 10 <= w:
            out.append(f'<text x="{cx:.1f}" y="74" text-anchor="middle" class="ph" fill="{fill}">{lab}</text>\n')
        labels.append((x0, "start" if n == 0 else "middle", ym_label(a) if idx(a) >= 0 else ym_label(_shift(a, -idx(a)))))
    end = segs[-1][2]
    labels.append((min(SS_X1, SS_X0 + (idx(end) + 1) * SS_PX), "end",
                   ym_label(end) if idx(end) <= last_i else f"till {ym_label(end)}"))
    nd = SS_X0 + 12 * SS_PX
    out.append(f'<line x1="{SS_X0}" y1="30" x2="{SS_X0}" y2="56" stroke="#B9862E" stroke-width="1.2"/><text x="{SS_X0}" y="24" class="sm">This Diwali</text>\n'
               f'<line x1="{nd:.1f}" y1="30" x2="{nd:.1f}" y2="56" stroke="#B9862E" stroke-width="1.2" stroke-dasharray="3 2.5"/><text x="{nd:.1f}" y="24" text-anchor="middle" class="sm">Next Diwali</text>\n')
    rows = {100: [], 114: []}  # placed [left, right] extents per row; a label that fits neither row is dropped
    for x, anchor, text in labels:
        tw = len(text) * 5.4
        left = x if anchor == "start" else x - tw if anchor == "end" else x - tw / 2
        left = max(0.0, min(left, 373 - tw))
        for y in (100, 114):
            if all(left + tw + 6 <= l or left >= r + 6 for l, r in rows[y]):
                rows[y].append((left, left + tw))
                out.append(f'<text x="{left:.1f}" y="{y}" class="ml">{text}</text>\n')
                break
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------- cards

TP_CAPTION = {"jupiter_moves": "Growth comes to you", "saturn_moves": "Growth with a steady hand"}
TAG_CAPTION = [("gold", "Gains come more easily"), ("work", "Your work gets noticed"), ("deals", "Deals move more easily"),
               ("travel", "Luck and support open up"), ("family", "Warmth at home grows")]


def highlight_caption(m, tp_kind=None):
    """Anar caption from the month's own facts (turning point kind, then tags, then tone); no dates."""
    if tp_kind in TP_CAPTION:
        return TP_CAPTION[tp_kind]
    tags = m.get("tags") or []
    for tag, cap in TAG_CAPTION:
        if tag in tags:
            return cap
    return "Your strongest support" if m.get("tone") == "best" else "Steady support grows"


def luck_cards(p, prose):
    """Better luck and a fresh beginning (2 cards). RENDER-A puts these first when steering == 'luck'."""
    P = lambda k: e(prose(k))
    months = p.get("months") or []
    tps = {t.get("ym") for t in (p.get("period") or {}).get("turning_points") or []}
    pick = [m for m in months if m.get("tone") == "best" or m.get("ym") in tps]
    pick += [m for m in months if m.get("tone") == "good" and m not in pick]
    pick = sorted(pick[:4], key=lambda m: m["ym"])
    tpk = {t.get("ym"): t.get("kind") for t in (p.get("period") or {}).get("turning_points") or []}
    hl = [(m, m["ym"] in tps, highlight_caption(m, tpk.get(m["ym"]))) for m in pick]
    tp_items = "".join(
        f'\n    <div class="lr"><span class="dot" style="background:#3E7D5A"></span><span class="lt">{bold_first(prose(f"luck.turning.{n}"))}</span></div>'
        for n in range(1, min(2, len([h for h in hl if h[1]])) + 1))
    c1 = (f'<section class="page ex" id="a-luck"><div class="col">\n'
          f'  <div class="exlabel">{DIYA}Better luck and a fresh beginning</div>\n'
          + (f'  <p class="lead" style="text-align:center;margin-top:4px;font-size:14px;color:var(--gold)">{P("luck.opener")}</p>\n'
             if p["meta"].get("steering") == "luck" else "") +
          f'  <h2 class="action">{P("luck.headline")}</h2>\n'
          f'  <div class="subtit">Your {"best" if has_best(p) else "good"}-time highlights, from this Diwali to the next <span style="white-space:nowrap">({e(p["meta"].get("span"))})</span></div><div class="exrule"></div>\n'
          f'  {anars_svg(hl) if hl else ""}\n'
          f'  <div class="leg" style="margin-top:8px">{tp_items}\n  </div>\n'
          f'  <div class="callout" style="margin-top:12px"><div class="ch">What the months before this Diwali built</div><p>{P("luck.built")}</p></div>\n'
          f'</div>{TOCL}')
    spots = {b.get("area"): b for b in (p.get("luck") or {}).get("bright_spots") or []}
    order = [a for a in p.get("area_order") or [] if a in spots] or list(spots)
    rows = "".join(
        f'\n    <div class="sr" style="padding:2px 0"><span class="num">{i}</span><span class="st"><b>{AREA_LABEL.get(a, e(a))}:</b> {P(f"luck.bright.{a}")}</span></div>'
        for i, a in enumerate(order, 1))
    c2 = (f'<section class="page"><div class="col">\n'
          f'  <div class="eyebrow">{DIYA}Better luck and a fresh beginning</div>\n'
          f'  <h2 class="head" style="font-size:24px">A bright spot in every area</h2><div class="rule"></div>\n'
          f'  <div style="width:100%;text-align:left;margin-top:8px">{rows}\n  </div>\n'
          f'  <div class="win"><span class="wg grn">Good</span><div class="wt">Luck and blessings</div><div class="wd">{P("luck.blessings.what")}<br><b>Do:</b> {P("luck.blessings.do")}<br><b>Why:</b> {P("luck.blessings.why")}<br><b>When:</b> {P("luck.blessings.when")} · {link("s-1-months", "your 12 months")}</div></div>\n'
          f'  <div class="win"><div class="wt" style="font-size:14px">Small fresh-start habits</div><div class="wd">{P("luck.habits")}</div></div>\n'
          f'  <div class="take" style="margin-top:12px"><b>The read</b>{P("luck.read")}</div>\n'
          f'</div>{TOCL}')
    return [c1, c2]


SS_STEPS = [("i-book", ""), ("i-check", ""), ("i-clock", ""), ("i-scales", " warn"), ("i-coins", " good")]
# legend lines: what each phase is (chart-independent definitions; the buyer's own read is in sadesati.*)
SS_TEXT = {"rising": "Saturn walks the sign before your Moon sign. New duties may appear.",
           "peak": "Saturn sits on your Moon sign. Work asks for steady effort.",
           "setting": "Saturn walks the sign after your Moon sign. Shared costs ask for a clear plan.",
           "pause": "The phase rests for a while, a good time to save ahead.",
           "return": "Saturn steps back for a short while, then moves on.",
           "none": "Saturn is away from your Moon sign for now."}


def ss_status(p):
    """'active' (running now), 'soon' (a phase starts before next Diwali) or 'off'."""
    ss = p.get("sade_sati") or {}
    if ss.get("active"):
        return "active"
    months = p.get("months") or []
    if months:
        a, b = months[0]["ym"], months[-1]["ym"]
        if any(ph.get("phase") in ("rising", "peak", "setting") and ph.get("from", "9999") <= b and ph.get("to", "0000") >= a
               for ph in ss.get("phases") or []):
            return "soon"
    return "off"


def split_steps(text):
    """bank 'Title: text' lines → [(title, text)]."""
    out = []
    for line in str(text or "").splitlines():
        t, _, rest = line.partition(":")
        if line.strip():
            out.append((t.strip(), rest.strip()) if rest else ("", t.strip()))
    return out


def sadesati_cards(p, prose):
    P = lambda k: e(prose(k))
    months = p.get("months") or []
    ss = p.get("sade_sati") or {}
    status = ss_status(p)
    segs, idx = ss_segments(ss, months[0]["ym"] if months else "2026-11")
    leg = "".join(
        f'\n    <div class="lr"><span class="dot" style="background:{"#E39B2B" if k in ("pause", "none") else "#9C907A"}"></span><span class="lt"><b>{SS_LABEL.get(k, k).capitalize()}.</b> {SS_TEXT.get(k, "")}</span></div>'
        for k in dict.fromkeys(s[0] for s in segs))
    c1 = (f'<section class="page ex" id="s-1-sadesati"><div class="col">\n'
          f'  <div class="exlabel">{DIYA}Sade Sati check</div>\n'
          f'  <h2 class="action">{P("sadesati.headline")}</h2>\n'
          f'  <div class="subtit">Saturn\'s slow pass near your Moon sign, from this Diwali to the next and a little after</div><div class="exrule"></div>\n'
          f'  {sadesati_svg(segs, idx)}\n'
          f'  <div class="leg" style="margin-top:10px">{leg}\n  </div>\n'
          f'  <div class="callout" style="margin-top:14px"><div class="ch">What Sade Sati means</div><p>{P("sadesati.means")}</p></div>\n'
          f'</div>{TOCL}')
    steps = "".join(
        f'\n    <div class="pt{cls}"><svg class="pi"><use href="#{ic}"/></svg><div class="tx"><b>{e(t)}</b><span>{e(x)}</span></div></div>'
        for (ic, cls), (t, x) in zip(SS_STEPS, split_steps(prose("sadesati.steps"))))
    wg = '<span class="wg grn">Good</span>' if status == "off" else '<span class="wg">Steady</span>'
    head = {"active": "Free steps for this phase", "soon": "Free steps for when it begins"}.get(status, "Free steps to keep things steady")
    c2 = (f'<section class="page"><div class="col">\n'
          f'  <div class="eyebrow">{DIYA}Sade Sati check</div>\n'
          f'  <h2 class="head" style="font-size:24px">{head}</h2><div class="rule"></div>\n'
          f'  <div class="win">{wg}<div class="wt">What it means for you</div><div class="wd">{P("sadesati.what")}<br><b>Why:</b> {P("sadesati.why")}<br><b>When:</b> {P("sadesati.when")}, {link("s-1-months", "your 12 months")}</div></div>\n'
          f'  <div class="pts" style="gap:11px">{steps}\n  </div>\n'
          f'</div>{TOCL}')
    return [c1, c2]


def strengths_card(p, prose):
    P = lambda k: e(prose(k))
    wins = "".join(
        f'\n  <div class="win"><span class="wg grn">Good</span><div class="wt">{i}. {P(f"strengths.{i}.title")}</div><div class="wd">{P(f"strengths.{i}.what")}<br><b>Do:</b> {P(f"strengths.{i}.do")}<br><b>Why:</b> {P(f"strengths.{i}.why")}</div></div>'
        for i in range(1, len((p.get("strengths") or [None] * 3)[:3]) + 1))
    return (f'<section class="page" id="s-1-strengths"><div class="col">\n'
            f'  <div class="eyebrow">{DIYA}Your 3 strengths</div>\n'
            f'  <h2 class="head" style="font-size:24px">What you can lean on</h2><div class="rule"></div>\n'
            f'  <p class="lead" style="font-size:13px">Three things your chart gives you, from this Diwali to the next. Each comes with one thing to do.</p>{wins}\n'
            f'</div>{TOCL}')


SLOW_REASONS = ("reactions", "spending")  # the engine's care reasons; the bank writes slow.<reason>.*


def slow_reasons(p):
    """Care reasons of the overall careful times (payload.summary.careful), in order ([] when none)."""
    rs = [c.get("reason") for c in (p.get("summary") or {}).get("careful") or []]
    return [r for r in dict.fromkeys(rs) if r in SLOW_REASONS]


def slow_card(p, prose):
    P = lambda k: e(prose(k))
    rs = slow_reasons(p)
    if not rs:
        lead = "so your best time finds you ready" if has_best(p) else "so your good months find you ready"
        return (f'<section class="page" id="s-1-slow"><div class="col">\n'
                f'  <div class="eyebrow">{DIYA}Months to go slow</div>\n'
                f'  <h2 class="head" style="font-size:24px">No careful time, and what keeps it that way</h2><div class="rule"></div>\n'
                f'  <div class="win"><span class="wg grn">Good</span><div class="wt">No month needs extra care</div><div class="wd">No month from this Diwali to the next is marked careful.<br><b>Do:</b> keep the saving habit in the steady months, {lead}.<br><b>When:</b> every month · {link("s-1-months", "your 12 months")}</div></div>\n'
                f'</div>{TOCL}')
    care = (p.get("summary") or {}).get("careful") or []
    # the heading counts summary runs, one box per reason: a box covering several runs says so (no dates here)
    k = {r: sum(c.get("reason") == r for c in care) for r in rs}
    many = {r: "" if k[r] < 2 else ", both times" if k[r] == 2 else f", all {WORDS[k[r]].lower()} times" for r in rs}
    wins = "".join(
        f'\n  <div class="win"><span class="wg mod">Careful</span><div class="wt">{P(f"slow.{r}.title")}{many[r]}</div><div class="wd">{P(f"slow.{r}.what")}<br><b>Do:</b> {P(f"slow.{r}.do")}<br><b>Watch:</b> {P(f"slow.{r}.watch")}<br><b>Why:</b> {P(f"slow.{r}.why")}<br><b>When:</b> {P(f"slow.{r}.when")} · {link("s-1-months", "your 12 months")}</div></div>'
        for r in rs)
    n = len(care)
    return (f'<section class="page" id="s-1-slow"><div class="col">\n'
            f'  <div class="eyebrow">{DIYA}Months to go slow</div>\n'
            f'  <h2 class="head" style="font-size:24px">{WORDS[n]} careful time{"s" if n > 1 else ""}, and what helps</h2><div class="rule"></div>{wins}\n'
            f'</div>{TOCL}')


TALLY = [("best", "Best", ("best",)), ("good", "Good", ("good",)), ("steady", "Steady", ("steady",)), ("care", "Careful", ("careful",))]


def _short(label):
    """'Nov–Dec 2026, Aug–Oct 2027' -> 'Nov–Dec · Aug–Oct' (tally boxes carry no year)."""
    return re.sub(r"\s*\d{4}", "", str(label or "")).replace(", ", " · ").strip()


def tally(months, summary):
    """[(css, label, count, months_text)]: counts from the 12 month tones (always sum to 12); the ranges
    named come from payload.summary, the engine's one source for overall best/good/steady/careful."""
    sm = summary or {}
    n = lambda t: sum(m.get("tone") == t for m in months)
    best = sm.get("best") or {}
    bset = {m["ym"] for m in months if best.get("from") and best["from"] <= m["ym"] <= best.get("to", best["from"])}
    other = [m["ym"] for m in months if m.get("tone") == "best" and m["ym"] not in bset]
    # ponytail: summary.best is the first best run; any later best months are named from the tones
    btxt = " · ".join(x for x in [_short(best.get("label")) if n("best") and bset else ""] + [run_short(r) for r in runs(other)] if x)
    care = " · ".join(_short(c.get("label")) for c in sm.get("careful") or [])
    return [("best", "Best", n("best"), btxt or "none"), ("good", "Good", n("good"), _short(sm.get("good_label")) or "none"),
            ("steady", "Steady", n("steady"), _short(sm.get("steady_label")) or "none"),
            ("care", "Careful", n("careful"), care or "none")]


def tally_note(months, summary):
    care = (summary or {}).get("careful") or []
    if not care:
        return "No careful month from this Diwali to the next."
    word = {"reactions": "for quick reactions", "spending": "for spending"}
    parts = [f'{word[c["reason"]] + " " if c.get("reason") in word else ""}in {c.get("label")}' for c in care]
    last = max(c["to"] for c in care)
    after = [m for m in months if m["ym"] > last]
    tail = f", easier from {ym_label(after[0]['ym'])}" if after else ""
    return "Careful " + " and ".join(parts) + tail + "."


H_START = {"best": "a bright start", "good": "a good start", "steady": "a steady start", "careful": "a careful start"}
H_THEN = {"best": "then your brightest months", "good": "then good months", "steady": "then steady gains",
          "careful": "then go carefully"}
H_ALL = {"best": "bright all through", "good": "good months all through", "steady": "steady all through",
         "careful": "go carefully all through"}


H_MID = {"best": "a bright patch", "good": "a good patch", "steady": "a steady patch", "careful": "a careful patch"}


def half_headline(ms):
    """'a steady start, a careful patch, then good months.' from the half's own tones (no dates):
    the start, the most notable tone in between (if any), and how the half ends."""
    tones = [m.get("tone") or "steady" for m in ms]
    t0, tn = tones[0], tones[-1]
    mid = set(tones[1:-1]) - {t0, tn}
    t1 = next((t for t in ("best", "careful", "good", "steady") if t in mid), None)
    if tn == t0 and not t1:
        return f"{H_ALL.get(t0, 'steady all through')}."
    if tn == t0:   # the half returns to how it began
        return f"{H_START.get(t0, 'a steady start')}, {H_MID[t1]}, then {'bright' if t0 == 'best' else t0} again."
    return f"{H_START.get(t0, 'a steady start')}{', ' + H_MID[t1] if t1 else ''}, {H_THEN[tn]}."


def months_cards(p, prose):
    P = lambda k: e(prose(k))
    months = (p.get("months") or [])[:12]
    span = e(p["meta"].get("span"))
    cards = []
    for half in (0, 1):
        ms = months[half * 6: half * 6 + 6]
        if not ms:
            continue
        rows = "".join(f'\n    <tr><td>{e(m.get("label"))}</td><td>{P("months.%s.do" % m["ym"])}</td><td>{P("months.%s.watch" % m["ym"])}</td></tr>' for m in ms)
        extra = ""
        if half == 1:
            t = "".join(f'<div class="{c}"><b>{n}</b><div class="k">{lab}</div><div class="m">{e(txt)}</div></div>' for c, lab, n, txt in tally(months, p.get("summary")))
            extra = (f'\n  <div class="tally-h">Your 12 months, in numbers</div>\n  <div class="tally">{t}</div>\n'
                     f'  <div class="tally-n">{e(tally_note(months, p.get("summary")))}</div>')
        sid = ' id="s-1-months"' if half == 0 else ""
        cards.append(f'<section class="page ex"{sid}><div class="col">\n'
                     f'  <div class="exlabel">{DIYA}Your 12 months</div>\n'
                     f'  <h2 class="action">{span_label(ms[0]["ym"], ms[-1]["ym"])}: {half_headline(ms)}</h2>\n'
                     f'  <div class="subtit">From this Diwali to the next ({span}), months {half * 6 + 1} to {half * 6 + len(ms)}</div><div class="exrule"></div>\n'
                     f'  {kandils_svg(ms, half == 0)}\n'
                     f'  <table class="mtab" style="margin-top:8px">\n    <tr><th>Month</th><th>Do</th><th>Watch</th></tr>{rows}\n  </table>{extra}\n'
                     f'</div>{TOCL}')
    return cards


PART2_TOC = [("s-2-1", "2.1 Diwali across India"), ("s-2-2", "2.2 Lakshmi Puja time in your city"),
             ("s-2-3", "2.3 Good months for gold and big buys"), ("s-2-4", "2.4 Lakshmi and prosperity practices"),
             ("s-2-5", "2.5 Your fresh-start plan"), ("s-2-6", "2.6 A Diwali blessing")]
PRACTICES = [("Clean and light the home before Diwali", "an orderly home and clear accounts welcome Lakshmi.",
              "clear one cupboard and stop one money leak, such as a subscription nobody uses."),
             ("Chopda Pujan, the new account books", "a fresh book means an honest count of what came in and what went out.",
              "on Lakshmi Puja day, write this month's money in and money out on the first page. Look at it again on the first of every month."),
             ("Daan of food or a book", "giving keeps money moving and keeps the hand open.",
              "fix one small giving amount each month, from the business or the home, and keep to it till next Diwali.")]
FAN = ('<svg class="fan {pos}" viewBox="0 0 54 30" fill="none"><rect x="6" y="13" width="42" height="20" fill="#FBF7EE"/><g stroke="currentColor" stroke-width="1" stroke-linecap="round">'
       '<path d="M27 27 L12 15M27 27 L18 12M27 27 L27 9M27 27 L36 12M27 27 L42 15"/><path d="M12 15 A19 19 0 0 1 42 15"/></g></svg>')
CRN = "".join(f'<svg class="crn {c}" viewBox="0 0 13 13"><path d="M6.5 0 L13 6.5 L6.5 13 L0 6.5 Z" fill="currentColor"/></svg>' for c in ("ctl", "ctr", "cbl", "cbr"))
MITHAI = ('<svg viewBox="0 0 270 132" width="210" aria-hidden="true" style="display:block;margin:14px auto 0"><path d="M22 36 L36 6 L234 6 L248 36Z" fill="#F1E2C2" stroke="#B9862E" stroke-width="1.4" stroke-linejoin="round"/><path d="M34 31 L44 11 L226 11 L236 31" fill="none" stroke="#C9A34E" stroke-width=".8" stroke-dasharray="1 3"/><text x="135" y="26" text-anchor="middle" style="font:italic 500 12px Fraunces,Georgia,serif;fill:#7A2E36">Shubh Deepavali</text><rect x="6" y="34" width="258" height="94" rx="9" fill="#EAD7B0" stroke="#B9862E" stroke-width="1.5"/><rect x="15" y="42" width="240" height="78" rx="4" fill="#FBF4E7" stroke="#C9A34E" stroke-width="1"/>'
          '<path d="M91.0 81.0 L85.9 89.3 L86.2 99.0 L77.6 103.6 L73.0 112.2 L63.3 111.9 L55.0 117.0 L46.7 111.9 L37.0 112.2 L32.4 103.6 L23.8 99.0 L24.1 89.3 L19.0 81.0 L24.1 72.7 L23.8 63.0 L32.4 58.4 L37.0 49.8 L46.7 50.1 L55.0 45.0 L63.3 50.1 L73.0 49.8 L77.6 58.4 L86.2 63.0 L85.9 72.7Z" fill="#FFFDF8" stroke="#C9A34E" stroke-width="1" stroke-linejoin="round"/><circle cx="55" cy="81" r="27" fill="none" stroke="#EADFC6" stroke-width="1"/>'
          '<path d="M171.0 81.0 L165.9 89.3 L166.2 99.0 L157.6 103.6 L153.0 112.2 L143.3 111.9 L135.0 117.0 L126.7 111.9 L117.0 112.2 L112.4 103.6 L103.8 99.0 L104.1 89.3 L99.0 81.0 L104.1 72.7 L103.8 63.0 L112.4 58.4 L117.0 49.8 L126.7 50.1 L135.0 45.0 L143.3 50.1 L153.0 49.8 L157.6 58.4 L166.2 63.0 L165.9 72.7Z" fill="#FFFDF8" stroke="#C9A34E" stroke-width="1" stroke-linejoin="round"/><circle cx="135" cy="81" r="27" fill="none" stroke="#EADFC6" stroke-width="1"/>'
          '<path d="M251.0 81.0 L245.9 89.3 L246.2 99.0 L237.6 103.6 L233.0 112.2 L223.3 111.9 L215.0 117.0 L206.7 111.9 L197.0 112.2 L192.4 103.6 L183.8 99.0 L184.1 89.3 L179.0 81.0 L184.1 72.7 L183.8 63.0 L192.4 58.4 L197.0 49.8 L206.7 50.1 L215.0 45.0 L223.3 50.1 L233.0 49.8 L237.6 58.4 L246.2 63.0 L245.9 72.7Z" fill="#FFFDF8" stroke="#C9A34E" stroke-width="1" stroke-linejoin="round"/><circle cx="215" cy="81" r="27" fill="none" stroke="#EADFC6" stroke-width="1"/>'
          '<g transform="translate(55 81) scale(.85)"><path d="M0 -21 L28 0 L0 21 L-28 0Z" fill="#EFE4CF" stroke="#B9A07A" stroke-width="1.3" stroke-linejoin="round"/><path d="M0 -14 L19 0 L0 14 L-19 0Z" fill="#FAF8F3" opacity=".9"/><ellipse cx="-8" cy="-5" rx="6" ry="3.2" transform="rotate(-30 -8 -5)" fill="#fff" opacity="0.8"/></g>'
          '<g transform="translate(135 81) scale(.85)"><circle r="22" fill="#F4B740" stroke="#C98A22" stroke-width="1.3"/><circle cx="-9" cy="4" r="1.5" fill="#D98A1E"/><circle cx="-2" cy="-3" r="1.5" fill="#D98A1E"/><circle cx="6" cy="7" r="1.5" fill="#D98A1E"/><circle cx="10" cy="-4" r="1.5" fill="#D98A1E"/><circle cx="-4" cy="12" r="1.5" fill="#D98A1E"/><circle cx="7" cy="-13" r="1.5" fill="#D98A1E"/><ellipse cx="-7" cy="-9" rx="6" ry="3.2" transform="rotate(-30 -7 -9)" fill="#fff" opacity="0.8"/></g>'
          '<g transform="translate(215 81) scale(.85)"><rect x="-19" y="-19" width="38" height="38" rx="4" fill="#F4EBD8" stroke="#C9A877" stroke-width="1.3"/><ellipse cx="-6" cy="-5" rx="4" ry="1.8" transform="rotate(-25 -6 -5)" fill="#7FA35A"/><ellipse cx="6" cy="4" rx="4" ry="1.8" transform="rotate(30 6 4)" fill="#7FA35A"/><ellipse cx="-3" cy="9" rx="3.6" ry="1.6" transform="rotate(-10 -3 9)" fill="#7FA35A"/></g>'
          '<path d="M84 52 Q84 57 89 57 Q84 57 84 62 Q84 57 79 57 Q84 57 84 52Z" fill="#F2C14E" stroke="#B9862E" stroke-width=".6"/><path d="M244 52 Q244 57 249 57 Q244 57 244 62 Q244 57 239 57 Q244 57 244 52Z" fill="#F2C14E" stroke="#B9862E" stroke-width=".6"/></svg>')
_LEG = '<div class="lr" style="align-items:center;gap:8px"><span style="display:inline-block;min-width:74px;text-align:center;font:700 8px/{lh} Inter,sans-serif;letter-spacing:.08em;{st}">{tag}</span><span class="lt">{txt}</span></div>'


def _months_between(a, b):
    (ya, ma), (yb, mb) = ym_parts(a), ym_parts(b)
    return yb * 12 + mb - ya * 12 - ma


def range_tile(r):
    """Wrapped tile: ('Jun–Jul', '2027') or ('Dec–Jan', '2026–27')."""
    a, b = (r or {}).get("from"), (r or {}).get("to") or (r or {}).get("from")
    if not a:
        return "", ""
    (ya, ma), (yb, mb) = ym_parts(a), ym_parts(b)
    big = MON[ma - 1] if a == b else f"{MON[ma - 1]}–{MON[mb - 1]}"
    return big, (str(ya) if ya == yb else f"{ya}–{str(yb)[2:]}")


def part2_cards(p, prose):
    P = lambda k: e(prose(k))
    meta, months = p["meta"], (p.get("months") or [])[:12]
    first_area = (p.get("area_order") or ["money"])[0] if meta.get("steering") != "luck" else "luck"
    cards = []
    toc = "".join(f'<a class="xr" href="#{cid}"><span>{t}</span><span>p.@@{cid}@@</span></a>' for cid, t in PART2_TOC)
    cards.append(f'<section class="page part" id="part-2"><svg class="garland"><use href="#i-garland"/></svg>{RANG}<div class="col"><div class="eyebrow">{DIYA}Part 2 · Your Diwali</div><div class="partno">2</div><h2 class="head">Your Diwali</h2><div class="rule"></div>'
                 f'<p class="lead" style="text-align:center">The festival days, your puja time, good months for gold, simple practices, a fresh-start plan and a blessing for the months ahead.</p><div class="mtoc" style="margin-top:18px">{toc}</div></div>{TOCL}')
    dw = p.get("diwali") or {}
    days = "".join(f'<tr><td><b>{e(d.get("name"))}</b></td><td>{e(day_label(d.get("date")))}</td></tr>' for d in dw.get("days") or [])
    puja_day = next((day_label(d.get("date")) for d in dw.get("days") or [] if "Lakshmi" in (d.get("name") or "")), "Sun 8 Nov")
    cards.append(f'<section class="page" id="s-2-1">{RANG}<div class="col"><div class="eyebrow">{DIYA}2.1 · Diwali across India</div><h2 class="head">Five days of light, 2026</h2><div class="rule"></div>'
                 f'<p class="lead" style="font-size:14px">The same for every family. Each community marks its own day.</p><table class="dtab"><tr><th>Day</th><th>Date</th></tr>{days}</table>'
                 f'<p class="fine">Dates for New Delhi; your city may differ by a day.</p><div class="callout"><div class="ch">Shubh Deepavali</div><p>Wishing you and your family a bright and happy Diwali. May every lamp you light bring warmth to your home and good fortune to the months ahead.</p></div></div>{TOCL}')
    puja = "".join(f'<tr><td><b>{e(t.get("city"))}</b></td><td>{e(time_range(t.get("start"), t.get("end")))}</td></tr>' for t in dw.get("puja_times") or [])
    own = [t.get("city") for t in dw.get("puja_times") or [] if "Drik" not in (t.get("source") or "")]
    src = ("Times from Drik Panchang." if not own else
           f"Times from Drik Panchang; {_and(own)} worked out by us with the same method.")
    cards.append(f'<section class="page" id="s-2-2">{RANG}<div class="col"><div class="eyebrow">{DIYA}2.2 · Lakshmi Puja time in your city</div><h2 class="head">The puja time in your city</h2><div class="rule"></div>'
                 f'<p class="lead">Lakshmi Puja is on <b>{puja_day} 2026</b>. The good time for the puja begins soon after sunset, so it changes from city to city.</p><table class="dtab"><tr><th>City</th><th>Puja time</th></tr>{puja}</table>'
                 f'<p class="fine">{src} If your city is not listed, ask your family priest or check a local panchang.</p></div>{TOCL}')
    gold = set((p.get("money_extra") or {}).get("gold_months") or [])
    ng = len([m for m in months if m["ym"] in gold])
    any_best_only = any(m.get("tone") == "best" and m["ym"] not in gold for m in months)
    head = (f"{WORDS[ng]} month{'s shine' if ng != 1 else ' shines'} for gold and large buys." if ng
            else "Your best months suit planned buys.")
    leg = [_LEG.format(lh="15px", st="color:#fff;background:#3E7D5A;border-radius:8px", tag="BEST FOR GOLD", txt="Best for gold, jewellery or a large buy.")]
    if any_best_only:
        leg.append(_LEG.format(lh="15px", st="color:#fff;background:#3E7D5A;border-radius:8px", tag="BEST OVERALL", txt="Best month overall, not a gold month. Fine for planned buys."))
    leg += [_LEG.format(lh="13px", st="color:#8A6420;border:1.2px solid #B9862E;border-radius:8px", tag="GOOD TIME", txt="Good or steady time. Fine for small, planned buys."),
            _LEG.format(lh="13px", st="color:#B4572B;border:1.1px dashed #B4572B;border-radius:8px", tag="CAREFUL TIME", txt="Careful time. Hold large buys if they can wait.")]
    cards.append(f'<section class="page ex" id="s-2-3">{RANG}<div class="col"><div class="exlabel">{DIYA}2.3 · Good months for gold and big buys</div><h2 class="action">{head}</h2><div class="subtit">From this Diwali to the next · one diya for each month</div><div class="exrule"></div>'
                 f'{gold_svg(months, gold)}<div class="leg" style="margin-top:10px">{"".join(leg)}</div>'
                 f'<p class="fine" style="margin-top:8px"><b>Our method:</b> we mark a month when Venus or Jupiter passes the money or gains part of your chart, or when your current sub-period planet rules those parts. It is our own rule, not a promise.</p>'
                 f'<div class="callout" style="margin-top:10px"><div class="ch">Before you buy gold</div><p>Check the BIS hallmark on every piece. Ask for the making charge in writing. Avoid loans for festive-sale buys. We do not forecast gold prices.</p></div></div>{TOCL}')
    prac = "".join(f'<div class="callout"><div class="ch">{t}</div><p><b>The habit:</b> {h}<br><b>Your step:</b> {e(s)}</p></div>' for t, h, s in PRACTICES)
    cards.append(f'<section class="page" id="s-2-4">{RANG}<div class="col"><div class="eyebrow">{DIYA}2.4 · Lakshmi and prosperity practices</div><h2 class="head">Old ways, simple habits</h2><div class="rule"></div>'
                 f'<p class="lead" style="font-size:14px">Each practice pairs a tradition with the habit behind it and one step for your household. Nothing to buy. These are for money and luck, with no promised result.</p>{prac}'
                 f'<p class="fine" style="margin-top:10px"><b>Why these:</b> {P("practices.why")}</p></div>{TOCL}')
    plans = "".join(f'<div class="sr"><div class="num">{i}</div><div class="st">{if_then(prose(f"plan.fresh.{i}"))}</div></div>' for i in (1, 2, 3))
    lead_name = "Better luck" if first_area == "luck" else {"family": "Family & children"}.get(first_area, AREA_LABEL.get(first_area, ""))
    lead = (f"You picked {lead_name}, so your plan starts there." if p.get("first_reason") == "picked"
            else f"Your plan starts with {lead_name}, the area that comes first for you.")
    lead += ' Small "If this, then I will…" plans are easier to keep than large wishes. Each one follows a time in your chart.'
    cards.append(f'<section class="page" id="s-2-5">{RANG}<div class="col"><div class="eyebrow">{DIYA}2.5 · Your fresh-start plan</div><h2 class="head">Three {"fresh-start" if first_area == "luck" else AREA_LABEL.get(first_area, "").lower()} plans for the months ahead</h2><div class="rule"></div>'
                 f'<p class="lead" style="font-size:14px">{e(lead)}</p><div class="scores">{plans}</div>'
                 f'<div class="callout" style="margin-top:14px"><div class="ch">When</div><p>{P("plan.fresh.when")} See exactly when: {link("s-1-months", "your 12 months")}</p></div>'
                 f'<p class="fine" style="margin-top:10px">Write the three plans on the first page of your new account book, so you see them each month.</p></div>{TOCL}')
    # blessing + gift sign-off: bank-only keys (branched on gift; names from the form only)
    cards.append(f'<section class="page note" id="s-2-6">{RANG}<div class="col"><div class="noteframe">{FAN.format(pos="nftop")}{CRN}<div class="notebox"><div class="ne">{DIYA}A Diwali blessing</div><div class="nh">{P("blessing.title")}</div>'
                 f'<p>{P("blessing.text")}</p>{MITHAI}<div class="sig">— {P("blessing.sign")}</div></div>{FAN.format(pos="nfbot")}</div></div>{TOCL}')
    # Wrapped card (light theme v2)
    w = p.get("wrapped") or {}
    area = w.get("strongest_area") or first_area
    sm = p.get("summary") or {}   # overall ranges: payload.summary only (best; the longest careful run)
    bb, by = range_tile(sm.get("best"))
    care = max(sm.get("careful") or [], key=lambda c: _months_between(c["from"], c["to"]), default=None)
    cb, cy = range_tile(care) if care else ("Clear", "no careful time")
    best_word = "Best time" if has_best(p) else "Good time"   # spec §2 rule 10: no best time for T2/T3
    words = wrapped_words(prose("wrapped.words"), w.get("words"))
    ww = "".join(f'<div class="w {c}"><b>{e(x["word"])}</b><span>{e(x["line"])}</span></div>' for c, x in zip("gcb", words))
    cards.append(f'<section class="page ex">{RANG}<div class="col"><div class="exlabel">{DIYA}2.6 · Your Wrapped card</div><h2 class="action">Till next Diwali, your chart says</h2><div class="subtit">From this Diwali to the next ({e(meta.get("span"))})</div><div class="exrule"></div>'
                 f'<div class="wr"><div class="whero"><svg class="pi"><use href="#{AREA_ICON.get(area, "i-coins")}"/></svg><div class="wl">Strongest area</div><div class="wbig">{AREA_LABEL.get(area, e(area))}</div></div>'
                 f'<div class="wrow"><div class="wt best"><div class="wl">{best_word}</div><b>{bb}</b><span class="y">{by}</span></div><div class="wt care"><div class="wl">Careful time</div><b>{cb}</b><span class="y">{cy}</span></div></div>'
                 f'<div class="wmove"><div class="wl">One big move</div><p>{e(w.get("move"))}</p></div></div>'
                 f'<div class="take" style="margin-top:14px;padding-bottom:0"><b style="margin-bottom:0">Till next Diwali, you are…</b></div><div class="ww">{ww}</div></div>{TOCL}')
    return cards


WRAPPED_SPARE = ["STEADY", "READY", "FOCUSED", "HOPEFUL", "GROUNDED", "BRIGHT"]  # lint-clean stand-ins, in order


def wrapped_words(text, fallback):
    """prose 'wrapped.words' ('WORD: line' x3) → [{word, line}]; payload words if the prose is not 3 clean lines.
    A word that fails the bank lint (e.g. 'PATIENT', 'CALM') becomes the first unused WRAPPED_SPARE word."""
    rows = [dict(zip(("word", "line"), (a.strip().upper(), b.strip())))
            for a, sep, b in (ln.partition(":") for ln in str(text or "").splitlines()) if sep and a.strip()]
    if len(rows) < 3:
        rows = [{"word": str(x.get("word", "")).upper(), "line": x.get("line") or ""} for x in (fallback or [])]
    rows = rows[:3]
    spare = [w for w in WRAPPED_SPARE if w not in {r["word"] for r in rows}]
    for r in rows:
        if lint_text(r["word"], allow_dates=True):
            r["word"] = spare.pop(0)
    return rows


def bold_first(text):
    """'Money leads. It tends…' → '<b>Money leads.</b> It tends…' (escaped)."""
    m = re.match(r"(.+?[.!?])\s+(.*)", text, re.S)
    return f"<b>{e(m.group(1))}</b> {e(m.group(2))}" if m else f"<b>{e(text)}</b>"


def if_then(text):
    """'If X, then I will Y.' → '<b>If X,</b> then I will Y.' (escaped)."""
    a, sep, b = str(text).partition(", then ")
    return f"<b>{e(a)},</b> then {e(b)}" if sep else e(text)


PLAN_TITLES = {"d30": "Open the new books well", "d90": "Steady the base", "d365": "Save, then grow"}


def plan_cards(p, prose):
    P = lambda k: e(prose(k))
    pri = "".join(f'\n    <div class="sr"><div class="num">{i}</div><div class="st">{bold_first(prose(f"plan.p{i}"))}</div></div>' for i in range(1, 6))
    e1 = (f'<section class="page" id="e-1"><div class="col">\n  <div class="eyebrow">Your top priorities</div>\n'
          f'  <h2 class="head">Where to put your energy</h2><div class="rule"></div>\n  <div class="scores">{pri}\n  </div>\n'
          f'  <div class="verdict gold"><div class="vl">If you do only one thing</div><div class="vt">{P("plan.one")}</div></div>\n'
          f'  <p class="fine" style="margin-top:10px">{link("s-0-6", "Your timeline", arrow=False)} shows all the months in one picture.</p>\n</div>{TOCL}')
    tli = "".join(
        f'\n    <div class="tli"><div class="dt">{dt}</div><div class="th">{PLAN_TITLES[k]}</div><div class="td">{"<br>".join("· " + e(s.strip()) for s in str(prose(f"plan.{k}")).splitlines() if s.strip())}</div></div>'
        for k, dt in (("d30", "First 30 days"), ("d90", "First 90 days"), ("d365", "All 365 days")))
    e2 = (f'<section class="page" id="e-2"><div class="col">\n  <div class="eyebrow">Your 30 / 90 / 365 days</div>\n'
          f'  <h2 class="head">From this Diwali, step by step</h2><div class="rule"></div>\n  <div class="tl" style="margin-top:14px;text-align:left">{tli}\n  </div>\n'
          f'  <p class="fine" style="margin-top:12px">Each month, marked best, good or careful: {link("s-1-months", "your 12 months")}</p>\n</div>{TOCL}')
    ks = "".join(
        f'\n    <div class="k"><div class="n">{i}</div><div class="t">{bold_first(prose(f"takeaways.{i}"))}{" See " + link("s-1-months", "your 12 months") if i in (3, 4) else ""}</div></div>'
        for i in range(1, 6))
    e3 = (f'<section class="page sand" id="e-3"><div class="col">\n  <div class="eyebrow">5 takeaways</div>\n'
          f'  <h2 class="head">What to remember</h2><div class="rule"></div>\n  <div class="wk">{ks}\n  </div>\n</div>{TOCL}')
    return [e1, e2, e3]


# South-Indian grid: fixed sign boxes in markup order (center box after Aquarius)
SOUTH = ["Pisces", "Aries", "Taurus", "Gemini", "Aquarius", None, "Cancer", "Capricorn", "Leo", "Sagittarius", "Scorpio", "Libra", "Virgo"]
HOUSE_PART = ["Part for yourself", "Money part", "Effort and courage part", "Home part", "Children and planning part",
              "Loans and competition part", "Partner part", "Shared-money part", "Luck part", "Work part", "Gains part", "Spending part"]
WORK = {"job": "someone in a job", "business": "a business owner", "student": "a student", "home": "someone who runs the home"}
PHASE_WORD = {"rising": "first", "peak": "middle", "setting": "last"}


DIGNITY_WORDS = {"exalted": "Very strong: at its best, called exalted", "own": "Strong: in its own sign",
                 "debilitated": "Needs support: at its weakest, called debilitated",
                 "friendly": "At ease in a friendly sign", "enemy": "Works harder in this sign"}
HOUSE_WORDS = {1: "Close to you; shapes how you come across", 2: "Works on money and speech", 3: "Adds effort and courage",
               4: "Turns to home and comfort", 5: "Turns to planning and ideas", 6: "Takes on loans and competition",
               7: "A mind that turns to people", 8: "Works on shared money, quietly", 9: "Brings luck and teachers",
               10: "Puts its force into work and name", 11: "Helps gains and contacts", 12: "Works quietly, behind the scenes"}


def planet_words(pl):
    """'Strength in words' cell from the planet's dignity, else its house."""
    return DIGNITY_WORDS.get(pl.get("dignity")) or HOUSE_WORDS.get(pl.get("house"), "Steady in its sign")


def _and(xs):
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def planets_standout(p):
    planets = (p.get("chart") or {}).get("planets") or []
    best = [x.get("name") for x in planets if x.get("dignity") in ("exalted", "own")]
    if best:
        out = f"{WORDS[len(best)]} planet{'s sit' if len(best) > 1 else ' sits'} in {'their' if len(best) > 1 else 'its'} best sign{'s' if len(best) > 1 else ''}: {_and(best)}."
    else:
        out = "No planet sits in its own or best sign; each works through the part of life it sits in."
    src = list(dict.fromkeys(s.get("planet") for s in p.get("strengths") or [] if s.get("planet")))
    if src:
        out += f" Your strengths in this report come from {_and(src)}."
    return out


def back_cards(p, prose):
    P = lambda k: e(prose(k))
    meta, ch = p["meta"], p.get("chart") or {}
    first = e(meta.get("first_name") or meta.get("name") or "")
    lagna, moon = sign((ch.get("lagna") or {}).get("sign")), ch.get("moon") or {}
    planets = ch.get("planets") or []
    in_sign = {}
    for pl in planets:
        ab = PL_ABBR.get(pl.get("name"), str(pl.get("name", ""))[:2])
        if pl.get("retro") and pl.get("name") not in ("Rahu", "Ketu"):
            ab += " R"
        in_sign.setdefault(sign(pl.get("sign")), []).append(ab)
    cells = []
    for s in SOUTH:
        if s is None:
            cells.append(f'<div class="kc center"><b>{first}</b><span>D-1 · Lahiri</span></div>')
            continue
        pl = f'<span class="pl">{" ".join(in_sign.get(sign(s), []))}</span>' if in_sign.get(sign(s)) else ""
        if sign(s) == lagna:
            cells.append(f'<div class="kc" style="background:rgba(201,163,78,.16)">{sign3(s)}<span style="position:absolute;top:4px;right:4px;font-size:7.5px;font-weight:700;color:var(--maroon);letter-spacing:.06em">LAGNA</span>{pl}</div>')
        else:
            cells.append(f'<div class="kc">{sign3(s)}{pl}</div>')
    b1 = (f'<section class="page" id="b-1"><div class="col">\n  <div class="eyebrow">B.1 · Your birth chart</div>\n'
          f'  <h2 class="head">The chart behind this report</h2><div class="rule"></div>\n  <div class="kundli">\n    {"".join(cells)}\n  </div>\n'
          f'  <p class="lead" style="font-size:14px;margin-top:14px">Your rising sign, called lagna, is <b>{e(lagna)}</b>, shaded above. Your Moon sign is <b>{e(sign(moon.get("sign")))}</b> and your birth star, or nakshatra, is <b>{e(moon.get("nakshatra"))}</b>.</p>\n'
          f'  <p class="fine">Su Sun · Mo Moon · Ma Mars · Me Mercury · Ju Jupiter · Ve Venus · Sa Saturn · Ra Rahu · Ke Ketu · R means the planet was moving backward at birth, called retrograde.</p>\n'
          f'  <p class="fine">The same chart, drawn the South-Indian way: each sign keeps its own box.</p>\n</div>{TOCL}')
    rows = "".join(f'\n    <tr><td><b>{e(pl.get("name"))}</b></td><td>{e(sign(pl.get("sign")))}</td><td>{ordinal(pl.get("house") or 0)}</td><td>{e(planet_words(pl))}</td></tr>' for pl in planets)
    b2 = (f'<section class="page" id="b-2"><div class="col">\n  <div class="eyebrow">B.2 · Your planets</div>\n'
          f'  <h2 class="head">Where each planet sits</h2><div class="rule"></div>\n  <table class="dtab" style="font-size:11px">\n    <tr><th>Planet</th><th>Sign</th><th>House</th><th>Strength in words</th></tr>{rows}\n  </table>\n'
          f'  <div class="callout"><div class="ch">What stands out</div><p>{e(planets_standout(p))}</p></div>\n</div>{TOCL}')
    hs = ch.get("houses") or {}
    hrows = "".join(f'\n    <tr><td><b>{HOUSE_PART[n - 1]}</b></td><td>{ordinal(n)}</td><td>{e(sign((hs.get(str(n)) or {}).get("sign")))}</td><td>{e((hs.get(str(n)) or {}).get("lord"))}</td></tr>' for n in range(1, 13))
    b3 = (f'<section class="page" id="b-3"><div class="col">\n  <div class="eyebrow">B.3 · Houses used in this report</div>\n'
          f'  <h2 class="head">The parts of your chart, simply</h2><div class="rule"></div>\n  <table class="dtab" style="font-size:11.5px">\n    <tr><th>Part of life</th><th>House</th><th>Your sign</th><th>Ruler</th></tr>{hrows}\n  </table>\n'
          f'  <p class="fine">Houses are counted from your {"rising sign" if meta.get("basis") != "moon" else "Moon sign"}, {e(sign((hs.get("1") or {}).get("sign")) or lagna)}, which is the 1st house. The ruler of a house is the planet that owns its sign.</p>\n</div>{TOCL}')
    b4a = (f'<section class="page" id="b-4"><div class="col">\n  <div class="eyebrow">B.4 · Astrology made simple · 1 of 2</div>\n'
           f'  <h2 class="head">How a chart is read</h2><div class="rule"></div>\n  <div class="pts">\n'
           f'    <div class="pt"><svg class="pi"><use href="#i-compass"/></svg><div class="tx"><b>A birth chart</b><span>A map of the sky at the minute and place you were born.</span></div></div>\n'
           f'    <div class="pt"><svg class="pi"><use href="#i-store"/></svg><div class="tx"><b>Houses</b><span>The chart is cut into 12 parts. Each part stands for one area of life, such as money, home or work.</span></div></div>\n'
           f'    <div class="pt"><svg class="pi"><use href="#i-gem"/></svg><div class="tx"><b>Planets</b><span>Nine planets sit in those parts. Each adds its own nature: Jupiter grows, Saturn steadies, Venus pleases.</span></div></div>\n'
           f'    <div class="pt"><svg class="pi"><use href="#i-moon"/></svg><div class="tx"><b>Rising sign vs Moon sign</b><span>The rising sign, or lagna, was coming up in the east when you were born; it sets the houses. The Moon sign, or rashi, is where the Moon sat; it shows the mind.</span></div></div>\n'
           f'  </div>\n</div>{TOCL}')
    per = p.get("period") or {}
    nxt = per.get("next_ad") or {}
    if per.get("ad_end") and per["ad_end"] <= ((p.get("months") or [{}])[-1].get("ym") or "9999"):
        tail = f", moving to a {e(nxt.get('lord'))} sub-period before next Diwali" if nxt.get("lord") else ", which changes before next Diwali"
    else:
        tail = " that runs past next Diwali"
    yours = f"Yours: {e(per.get('md'))}, with a {e(per.get('ad'))} sub-period{tail}." if per.get("md") else ""
    ss, status = p.get("sade_sati") or {}, ss_status(p)
    ss_line = (f"Yours is in its {PHASE_WORD[ss['phase']]} phase." if status == "active" and ss.get("phase") in PHASE_WORD
               else "Yours begins before next Diwali." if status == "soon"
               else "You are not in it from this Diwali to the next." if status == "off" else "")
    b4b = (f'<section class="page"><div class="col">\n  <div class="eyebrow">B.4 · Astrology made simple · 2 of 2</div>\n'
           f'  <h2 class="head">How timing is read</h2><div class="rule"></div>\n  <div class="pts">\n'
           f'    <div class="pt"><svg class="pi"><use href="#i-hourglass"/></svg><div class="tx"><b>Planet periods</b><span>Called dasha. Life runs in long chapters, each led by one planet, with shorter sub-periods inside. {yours}</span></div></div>\n'
           f'    <div class="pt"><svg class="pi"><use href="#i-trend"/></svg><div class="tx"><b>Planet movements</b><span>Called transits. Planets keep moving today. When one passes a part of your chart, that area becomes active for a while.</span></div></div>\n'
           f'    <div class="pt"><svg class="pi"><use href="#i-saturn"/></svg><div class="tx"><b>Sade Sati</b><span>Saturn\'s slow pass over your Moon sign and the signs on each side, in three phases of about 30 months each. It asks for care and steady work, and it ends. {ss_line}</span></div></div>\n'
           f'  </div>\n  <div class="callout"><div class="ch">Putting it together</div><p>We read the planet period you are in first, then the planet movements from this Diwali to the next, both from your own chart.</p></div>\n</div>{TOCL}')
    exact = meta.get("basis") != "moon"
    time_a = ("Your time was given exactly, so this report uses your rising sign in full." if exact
              else "Your birth time was not given exactly, so this report reads from your Moon sign.")
    picked = p.get("first_reason") == "picked"
    b5a = (f'<section class="page" id="b-5"><div class="col">\n  <div class="eyebrow">B.5 · Your doubts answered · 1 of 2</div>\n'
           f'  <h2 class="head">Common questions</h2><div class="rule"></div>\n  <div class="scores">\n'
           f'    <div class="sr"><div class="num">?</div><div class="st"><b>Is anything here certain?</b><br>No. Astrology shows tendencies and good times. Your own choices and effort shape what comes.</div></div>\n'
           f'    <div class="sr"><div class="num">?</div><div class="st"><b>Why does birth time matter?</b><br>The rising sign changes about every two hours, and it sets all the houses. A few minutes can move a planet into another part of life.</div></div>\n'
           f'    <div class="sr"><div class="num">?</div><div class="st"><b>What if the birth time is not known exactly?</b><br>Then the chart is read from the Moon sign, which is less precise for houses, and the report says so. {time_a}</div></div>\n'
           f'  </div>\n</div>{TOCL}')
    q4 = ('<b>Why does my chosen area come first?</b><br>You told us what matters most, so we put it first. The other areas follow.' if picked
          else '<b>Why does this area come first?</b><br>We start with the area that matters most for your situation. The other areas follow.')
    b5b = (f'<section class="page"><div class="col">\n  <div class="eyebrow">B.5 · Your doubts answered · 2 of 2</div>\n'
           f'  <h2 class="head">More questions</h2><div class="rule"></div>\n  <div class="scores">\n'
           f'    <div class="sr"><div class="num">?</div><div class="st"><b>Why do reports differ?</b><br>Each report is built from its own birth date, time and place. Other astrologers may also use a different method, so details can change.</div></div>\n'
           f'    <div class="sr"><div class="num">?</div><div class="st"><b>How do I read best, good and careful times?</b><br>Best: the strongest support. Good: steady support. Careful: go slowly. Each covers whole months, never one lucky day.</div></div>\n'
           f'    <div class="sr"><div class="num">?</div><div class="st"><b>What does "our method" mean for gold?</b><br>Our own rule marks a month when Jupiter or Venus passes your money part or gains part, or your sub-period planet rules them. It is not a price forecast.</div></div>\n'
           f'    <div class="sr"><div class="num">?</div><div class="st">{q4}</div></div>\n'
           f'  </div>\n</div>{TOCL}')
    work = WORK.get(meta.get("work_type"), "your situation")
    order_line = (f"The order of the areas: the one you picked comes first, then the usual order for {work}, lightly adjusted by your chart." if picked
                  else f"The order of the areas: the usual order for {work}, lightly adjusted by your chart.")
    basis_line = ("Your birth time was given exactly, so your rising sign is used in full." if exact
                  else "Your birth time was not exact, so the houses are read from your Moon sign, which is less precise.")
    b6 = (f'<section class="page" id="b-6"><div class="col">\n  <div class="eyebrow">B.6 · Methodology &amp; disclaimer</div>\n'
          f'  <h2 class="head">How this report was made</h2><div class="rule"></div>\n'
          f'  <p class="lead">Your chart is worked out with the Swiss ephemeris and the Lahiri ayanamsa, the standard most Indian astrologers use.</p>\n'
          f'  <p class="lead">{basis_line} Best months for gold follow our own stated rule.</p>\n'
          f'  <p class="lead">{order_line}</p>\n  <p class="lead">This report never predicts a figure.</p>\n'
          f'  <p class="fine" style="margin-top:12px">For reflection — not financial, legal or professional advice. Nothing here is a promise of future events. Decisions about money, work and family remain your own.</p>\n</div>{TOCL}')
    b7 = (f'<section class="page end" id="b-7"><div class="col">\n  <div class="eyebrow">With gratitude</div>\n'
          f'  <h2 class="head">Thank you, {first}</h2><div class="rule"></div>\n'
          f'  <p class="lead">Thank you for trusting Axtroshastra this Diwali. We hope this reading helps you plan the months ahead with a clear mind.</p>\n'
          f'  <p class="lead">Have another question? Each of these is on our site, computed the same honest way:</p>\n  <div class="pts">\n'
          f'    <div class="pt"><svg class="pi"><use href="#i-trend"/></svg><div class="tx"><b>Career Intelligence</b><span>Your work timing and the right next move.</span></div></div>\n'
          f'    <div class="pt"><svg class="pi"><use href="#i-book"/></svg><div class="tx"><b>Life Blueprint</b><span>A full read across the ten areas of your life.</span></div></div>\n'
          f'    <div class="pt"><svg class="pi"><use href="#i-clock"/></svg><div class="tx"><b>Marriage Timing</b><span>The good periods for marriage.</span></div></div>\n'
          f'    <div class="pt"><svg class="pi"><use href="#i-people"/></svg><div class="tx"><b>Compatibility</b><span>How two charts work together.</span></div></div>\n  </div>\n'
          f'  <p class="lead" style="font-style:italic;text-align:center;color:var(--gold2);margin-top:14px">Shubh Deepavali to you and your family. May every lamp you light bring warmth to your home.</p>\n'
          f'  <div class="cov-trust">www.axtroshastra.com &middot; Swiss ephemeris &middot; Lahiri ayanamsa</div>\n</div>{TOCL}')
    return [b1, b2, b3, b4a, b4b, b5a, b5b, b6, b7]


def cards_back(payload, prose):
    """Back half of the report, in report order. Better luck is always included; when the buyer picked
    it, RENDER-A's render_diwali lifts the a-luck cards to the top."""
    return (luck_cards(payload, prose) + sadesati_cards(payload, prose) + [strengths_card(payload, prose), slow_card(payload, prose)]
            + months_cards(payload, prose) + part2_cards(payload, prose) + plan_cards(payload, prose)
            + back_cards(payload, prose))


def back_keys(payload):
    """Every prose key cards_back asks for, for this payload, in order (for CONTENT/CONNECT)."""
    seen = []
    rec = lambda k: (seen.append(k), k)[1]
    cards_back(payload, rec)
    return list(dict.fromkeys(seen))
