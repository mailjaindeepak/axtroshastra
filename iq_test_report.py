"""IQ Test — paid report renderer.

render_iq_test(payload) → complete HTML document string.
Reuses the shared _VYAPAR_CSS / _VYAPAR_DEFS card-per-page theme from
report_view.py (per CLAUDE.md §8). 11-page card layout, 430×830px per card.
"""

from html import escape

from report_view import _VYAPAR_CSS, _VYAPAR_DEFS
from iq_test_questions import CATEGORY_LABELS, CATEGORY_ORDER

# ── icon SVG defs specific to IQ test (supplement _VYAPAR_DEFS) ─────────
_IQ_DEFS = r'''<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
<symbol id="i-brain" viewBox="0 0 24 24"><path d="M12 3a5 5 0 0 0-5 5c0 1.5.5 2.8 1.3 3.8L12 16l3.7-4.2A5 5 0 0 0 17 8a5 5 0 0 0-5-5z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 16v5M9 21h6" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></symbol>
<symbol id="i-lightning" viewBox="0 0 24 24"><path d="M13 2L4 14h7l-1 8 9-12h-7z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></symbol>
<symbol id="i-grow" viewBox="0 0 24 24"><path d="M12 22V8M8 12l4-4 4 4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/><path d="M5 3h14" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></symbol>
<symbol id="i-star" viewBox="0 0 24 24"><path d="M12 2l3 6.2 6.8 1-4.9 4.8L18 20.8 12 17.5 6 20.8l1.1-6.8L2.2 9.2l6.8-1z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></symbol>
<symbol id="i-bulb" viewBox="0 0 24 24"><path d="M9 18h6M12 2a7 7 0 0 0-4 12.7V17h8v-2.3A7 7 0 0 0 12 2z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></symbol>
<symbol id="i-method" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M12 8v4l2.5 1.5" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></symbol>
</defs></svg>'''

# ── category icons ──────────────────────────────────────────────────────
_CAT_ICON = {
    "pattern_recognition": "i-trend",
    "logical_reasoning": "i-compass",
    "verbal_analogies": "i-book",
    "odd_one_out": "i-target",
}

# ── bar color per performance label ─────────────────────────────────────
_BAR_COLOR = {
    "Exceptional": "var(--green)",
    "Strong": "var(--gold)",
    "Moderate": "var(--terra)",
    "Developing": "var(--mauve)",
}

# ── classification badge color ──────────────────────────────────────────
_CLASS_COLOR = {
    "Exceptional": "var(--green)",
    "Superior": "var(--green)",
    "Above Average": "var(--gold)",
    "Average": "var(--gold2)",
    "Below Average": "var(--terra)",
}


def _pno(n: int) -> str:
    return f'<div class="pno">{n}</div>'


def _icon(name: str, cls: str = "ic") -> str:
    return f'<svg class="{cls}"><use href="#{name}"/></svg>'


def _bar_svg(pct: int, color: str, w: int = 300, h: int = 14) -> str:
    """Horizontal bar chart showing percentage filled."""
    fill_w = max(2, round(pct / 100 * w))
    return (
        f'<svg viewBox="0 0 {w} {h}" style="width:100%;height:{h}px;display:block;margin:6px 0">'
        f'<rect x="0" y="0" width="{w}" height="{h}" rx="{h//2}" fill="var(--track)"/>'
        f'<rect x="0" y="0" width="{fill_w}" height="{h}" rx="{h//2}" fill="{color}"/>'
        f'</svg>'
    )


def _percentile_bar(pctile: int) -> str:
    """Wide percentile bar with marker."""
    pos = max(2, min(98, pctile))
    return (
        '<svg viewBox="0 0 300 30" style="width:100%;height:30px;display:block;margin:10px 0">'
        '<rect x="0" y="10" width="300" height="10" rx="5" fill="var(--track)"/>'
        f'<rect x="0" y="10" width="{pos * 3}" height="10" rx="5" fill="var(--gold)"/>'
        f'<circle cx="{pos * 3}" cy="15" r="7" fill="var(--gold)" stroke="#fff" stroke-width="2"/>'
        f'<text x="{pos * 3}" y="6" text-anchor="middle" fill="var(--ink)" '
        f'style="font-family:var(--sans);font-size:9px;font-weight:700">{pctile}%</text>'
        '</svg>'
    )


def render_iq_test(p: dict) -> str:
    """Render the full paid IQ test report as a complete HTML document."""
    m = p.get("meta", {})
    scores = p.get("scores", {})
    profile = p.get("profile", {})
    cats = scores.get("categories", {})

    name = escape(m.get("name", ""))
    first = name.split(" ")[0] if name else "there"
    age = m.get("age", "")
    generated = escape(m.get("generated", ""))
    iq = scores.get("iq", 100)
    classification = escape(scores.get("classification", "Average"))
    pctile = scores.get("percentile", 50)
    raw = scores.get("raw", 0)
    total = scores.get("total", 20)
    time_s = scores.get("time_taken_seconds", 0)
    time_min = time_s // 60
    time_sec = time_s % 60

    cls_color = _CLASS_COLOR.get(classification, "var(--gold)")

    pages = []

    # ── Page 1: Cover ────────────────────────────────────────────────
    pages.append(f'''
    <div class="page sand">
      <div class="col">
        <div class="cov-brand">AXTROSHASTRA</div>
        <div style="margin:18px 0 6px">
          {_icon("i-brain", "ic")}
        </div>
        <div class="cov-name">{name}</div>
        <div class="eyebrow" style="margin-top:4px">IQ ASSESSMENT REPORT</div>
        <div class="rule"></div>
        <div class="cov-pills">
          <span class="cp"><span class="g">&#9830;</span> Age: {age}</span>
          <span class="cp"><span class="g">&#9830;</span> Score: {iq}</span>
          <span class="cp"><span class="g">&#9830;</span> {classification}</span>
        </div>
        <div class="cov-trust">{generated}</div>
      </div>
      {_pno(1)}
    </div>''')

    # ── Page 2: A Note for You ───────────────────────────────────────
    pages.append(f'''
    <div class="page">
      <div class="col" style="text-align:left">
        <div class="eyebrow">A NOTE FOR YOU</div>
        <h2 class="head" style="text-align:left">Before you read this report</h2>
        <div class="rule"></div>
        <div class="lead" style="margin-top:18px">
          <b>Dear {first},</b><br><br>
          This report measures a specific set of cognitive abilities: pattern recognition,
          logical reasoning, verbal-analogical thinking, and classification skills. These
          are real, measurable dimensions of how your mind works.<br><br>
          But they are not the whole picture. Intelligence shows up in many ways: emotional
          awareness, creativity, physical coordination, social intuition, persistence.
          No single test captures all of it.<br><br>
          What this report <i>does</i> give you is a clear, honest look at where your
          analytical mind is strong and where it has room to grow. Use the strengths to
          your advantage and treat the growth areas as exactly that: areas to grow, not
          fixed limits.<br><br>
          Every score here can improve with practice. That is not a consolation; it is a
          neuroscience fact.
        </div>
      </div>
      {_pno(2)}
    </div>''')

    # ── Page 3: Your IQ Score ────────────────────────────────────────
    pages.append(f'''
    <div class="page">
      <div class="col">
        <div class="eyebrow">YOUR RESULT</div>
        <h2 class="head">Your IQ Score</h2>
        <div class="rule"></div>
        <div style="margin:24px 0 8px;width:140px;height:140px;border-radius:50%;
             border:6px solid {cls_color};display:flex;align-items:center;
             justify-content:center;flex-direction:column">
          <span style="font-family:var(--serif);font-weight:700;font-size:48px;
                color:var(--ink);line-height:1">{iq}</span>
          <span style="font-family:var(--sans);font-size:11px;color:var(--muted);
                margin-top:2px">IQ Score</span>
        </div>
        <div class="verdict gold" style="margin:10px 0 6px">
          {_icon("i-star")}
          <span>{classification}</span>
        </div>
        <div style="width:100%;margin-top:16px">
          <div style="font-family:var(--sans);font-size:12px;color:var(--mauve);
               text-align:left;margin-bottom:2px">
            You scored higher than <b style="color:var(--ink)">{pctile}%</b> of test-takers
          </div>
          {_percentile_bar(pctile)}
        </div>
        <div class="callout" style="margin-top:18px;width:100%">
          <p style="margin:0;text-align:left">
            You answered <b>{raw}</b> out of <b>{total}</b> questions correctly
            in <b>{time_min}m {time_sec:02d}s</b>.
          </p>
        </div>
      </div>
      {_pno(3)}
    </div>''')

    # ── Pages 4-7: Category breakdowns ───────────────────────────────
    for i, cat in enumerate(CATEGORY_ORDER):
        cat_data = cats.get(cat, {})
        cat_label = escape(CATEGORY_LABELS.get(cat, cat))
        correct = cat_data.get("correct", 0)
        cat_total = cat_data.get("total", 5)
        pct = cat_data.get("pct", 0)
        perf_label = escape(cat_data.get("label", "Moderate"))
        icon_id = _CAT_ICON.get(cat, "i-target")
        bar_color = _BAR_COLOR.get(perf_label, "var(--gold)")

        interpretation = ""
        from iq_test_questions import PROFILE_TEXT
        cat_text = PROFILE_TEXT.get(cat, {})
        interpretation = escape(cat_text.get(perf_label, ""))

        pages.append(f'''
        <div class="page">
          <div class="col" style="text-align:left">
            <div class="eyebrow">CATEGORY {i + 1} OF 4</div>
            <h2 class="head" style="text-align:left;display:flex;align-items:center;gap:10px">
              <svg style="width:28px;height:28px;color:var(--gold)"><use href="#{icon_id}"/></svg>
              {cat_label}
            </h2>
            <div class="rule"></div>
            <div style="display:flex;justify-content:space-between;align-items:baseline;
                 width:100%;margin-top:20px">
              <span style="font-family:var(--serif);font-weight:600;font-size:28px;
                    color:var(--ink)">{correct}/{cat_total}</span>
              <span class="verdict {'gold' if perf_label in ('Exceptional', 'Strong') else 'terra'}"
                    style="margin:0">
                {perf_label}
              </span>
            </div>
            {_bar_svg(pct, bar_color)}
            <div style="font-family:var(--sans);font-size:12px;color:var(--mauve);
                 margin-top:2px">{pct}% correct</div>
            <div class="lead" style="margin-top:20px">
              {interpretation}
            </div>
          </div>
          {_pno(4 + i)}
        </div>''')

    # ── Page 8: Cognitive Strengths ───────────────────────────────────
    strengths = profile.get("cognitive_strengths", [])
    strength_cards = ""
    for s in strengths[:3]:
        s_title = escape(s.get("title", ""))
        s_body = escape(s.get("body", ""))
        s_interp = escape(s.get("interpretation", ""))
        cat_icon = _CAT_ICON.get(s.get("category", ""), "i-star")
        strength_cards += f'''
        <div class="pt good">
          <svg class="pi"><use href="#{cat_icon}"/></svg>
          <div class="tx">
            <b>{s_title}</b>
            {s_body}
            {('<br><br><span style="color:var(--body)">' + s_interp[:200] + '</span>') if s_interp else ''}
          </div>
        </div>'''

    if not strength_cards:
        strength_cards = '''
        <div class="pt">
          <svg class="pi"><use href="#i-star"/></svg>
          <div class="tx"><b>Balanced Profile</b>
          Your scores are evenly distributed, showing a well-rounded cognitive profile.</div>
        </div>'''

    pages.append(f'''
    <div class="page">
      <div class="col" style="text-align:left">
        <div class="eyebrow">YOUR STRENGTHS</div>
        <h2 class="head" style="text-align:left">Cognitive Strengths</h2>
        <div class="rule"></div>
        <div class="pts" style="margin-top:20px">
          {strength_cards}
        </div>
      </div>
      {_pno(8)}
    </div>''')

    # ── Page 9: Growth Areas & Recommendations ───────────────────────
    growth = profile.get("areas_for_growth", [])
    growth_cards = ""
    for g in growth[:3]:
        g_title = escape(g.get("title", ""))
        g_body = escape(g.get("body", ""))
        g_tip = escape(g.get("tip", ""))
        cat_icon = _CAT_ICON.get(g.get("category", ""), "i-grow")
        growth_cards += f'''
        <div class="pt warn">
          <svg class="pi"><use href="#{cat_icon}"/></svg>
          <div class="tx">
            <b>{g_title}</b>
            {g_body}
            {('<br><br><span style="font-weight:600;color:var(--terra)">Tip:</span> ' + g_tip) if g_tip else ''}
          </div>
        </div>'''

    if not growth_cards:
        growth_cards = '''
        <div class="pt good">
          <svg class="pi"><use href="#i-check"/></svg>
          <div class="tx"><b>No major gaps</b>
          All four categories scored above the moderate threshold. Keep challenging yourself to maintain this edge.</div>
        </div>'''

    pages.append(f'''
    <div class="page">
      <div class="col" style="text-align:left">
        <div class="eyebrow">GROWTH AREAS</div>
        <h2 class="head" style="text-align:left">Where You Can Grow</h2>
        <div class="rule"></div>
        <div class="pts" style="margin-top:20px">
          {growth_cards}
        </div>
      </div>
      {_pno(9)}
    </div>''')

    # ── Page 10: Learning Style ──────────────────────────────────────
    ls = profile.get("learning_style", {})
    ls_name = escape(ls.get("name", "Balanced Learner"))
    ls_desc = escape(ls.get("description", ""))
    ls_tips = ls.get("tips", [])
    tips_html = "".join(
        f'<div class="pt good"><svg class="pi"><use href="#i-check"/></svg>'
        f'<div class="tx">{escape(t)}</div></div>'
        for t in ls_tips[:4]
    )

    pages.append(f'''
    <div class="page">
      <div class="col" style="text-align:left">
        <div class="eyebrow">HOW YOU LEARN</div>
        <h2 class="head" style="text-align:left">Your Learning Style</h2>
        <div class="rule"></div>
        <div class="verdict gold" style="margin:14px 0 8px">
          {_icon("i-bulb")}
          <span>{ls_name}</span>
        </div>
        <div class="lead">{ls_desc}</div>
        <div class="pts" style="margin-top:18px">
          {tips_html}
        </div>
      </div>
      {_pno(10)}
    </div>''')

    # ── Page 11: Methodology & Thank You ─────────────────────────────
    pages.append(f'''
    <div class="page sand">
      <div class="col" style="text-align:left">
        <div class="eyebrow">METHODOLOGY</div>
        <h2 class="head" style="text-align:left">How This Test Works</h2>
        <div class="rule"></div>
        <div class="lead" style="margin-top:14px;font-size:14px">
          This assessment measures four cognitive domains through 20 carefully
          selected questions, scored against a calibrated difficulty curve. Your
          raw score is mapped to the IQ scale (mean 100, standard deviation 15)
          with age-based norming adjustments, following the same statistical model
          used in standard psychometric testing.<br><br>
          The percentile reflects where your score falls relative to the general
          population. Category-level scores are computed independently, giving you
          a profile of relative strengths across different types of thinking.<br><br>
          IQ tests measure analytical and reasoning ability. They do not measure
          creativity, emotional intelligence, practical skills, or wisdom. A score
          is a starting point for understanding how your mind works, not a final
          verdict on what you can achieve.
        </div>
        <div style="margin-top:28px;text-align:center;width:100%">
          <div class="cov-brand">AXTROSHASTRA</div>
          <div style="font-family:var(--serif);font-size:18px;color:var(--ink);
               margin-top:10px">Thank you, {first}.</div>
          <div style="font-family:var(--sans);font-size:12px;color:var(--mauve);
               margin-top:8px">
            Share this test with friends and family.
          </div>
        </div>
      </div>
      {_pno(11)}
    </div>''')

    # ── assemble full document ───────────────────────────────────────
    all_pages = "\n".join(pages)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IQ Assessment Report — {name}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@400;600;700&display=swap" rel="stylesheet">
<style>
{_VYAPAR_CSS}

/* IQ test overrides */
.ic{{width:24px;height:24px;fill:none;stroke:currentColor;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round}}
.cov-brand{{font-family:var(--sans);font-weight:700;font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--gold)}}

@media print{{
  body{{padding:0;background:#fff}}
  .page{{box-shadow:none;margin:0;break-after:page;break-inside:avoid;overflow:hidden;
         width:430px;height:830px;border-radius:0}}
  #axPdfDl,#axShare,#axlang,.action-bar{{display:none!important}}
}}
@page{{size:430px 830px;margin:0}}
</style>
</head>
<body>
{_VYAPAR_DEFS}
{_IQ_DEFS}
{all_pages}
<div style="text-align:center;padding:20px 0 30px">
  <button id="axPdfDl" onclick="window.print();return false"
          style="display:inline-flex;align-items:center;gap:8px;padding:12px 28px;
                 background:var(--gold);color:#fff;border:0;border-radius:999px;
                 font-family:var(--sans);font-weight:700;font-size:14px;cursor:pointer">
    Download PDF
  </button>
  <button id="axShare" data-text="Check out my IQ Assessment from AxtroShastra!"
          style="display:inline-flex;align-items:center;gap:8px;padding:12px 28px;
                 background:var(--green);color:#fff;border:0;border-radius:999px;
                 font-family:var(--sans);font-weight:700;font-size:14px;cursor:pointer;
                 margin-left:10px">
    Share on WhatsApp
  </button>
</div>
</body>
</html>'''
