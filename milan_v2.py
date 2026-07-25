"""
milan_v2.py — redesigned Kundli Milan report (Warm palette, GenZ positioning).

A payload-driven renderer for the compute_milan() output. Feature-flagged: the
web layer calls this only when ?v2=1 (or REPORT_V2=1), so the live render_milan
in report_view.py is untouched while this is built out.

Everything is computed by the engine and read here — no astrology in the view.
Reuses the classical data tables (THEMES, KOOTA_UI, REMEDIES, ACTION_PLAN,
ARCHETYPE) from report_view.py so nothing is duplicated. LLM prose (narrative.py)
fills descriptive slots via narr(); missing -> the deterministic text is used.
"""
from html import escape
from narrative import narr
from report_view import (THEMES, KOOTA_UI, REMEDIES, ACTION_PLAN,
                         ARCHETYPE, ARCHETYPE_DEFAULT, _theme_scores)

# theme name -> a short "what it means for love" label used on the scorecard
AREA_LABEL = {
    "Chemistry & Attraction": "the spark & pull",
    "Everyday Vibe": "daily energy & moods",
    "Mind & Values": "how your minds meet",
    "Love & Long-Term": "the forever stuff",
    "Health & Vitality": "the deepest foundation",
}
SIGN_GLYPH = {"Aries": "♈", "Taurus": "♉", "Gemini": "♊",
              "Cancer": "♋", "Leo": "♌", "Virgo": "♍",
              "Libra": "♎", "Scorpio": "♏", "Sagittarius": "♐",
              "Capricorn": "♑", "Aquarius": "♒", "Pisces": "♓"}

CSS = """
:root{--cream:#FAF6EE;--beige:#DFCCB1;--espresso1:#3a2c18;--espresso2:#241810;
--gold:#C9A34E;--gold-lt:#E7CE8F;--ink:#2A2338;--muted:#8A8199;--line:#ECE3D3;
--green:#3E7D5A;--amber:#B9862E;--terra:#B4674A;--bronze:#6E4F2E;
--disp:'Fraunces',Georgia,serif;--body:'Jost',-apple-system,Segoe UI,sans-serif}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--body);background:#E8E1D4;color:var(--ink);line-height:1.6;-webkit-font-smoothing:antialiased}
.book{max-width:440px;margin:0 auto}
.pg{position:relative;min-height:720px;padding:44px 30px;overflow:hidden;background:var(--cream);border-bottom:1px solid #ded4c2}
.pn{position:absolute;bottom:18px;left:0;right:0;text-align:center;font-size:10px;letter-spacing:.35em;color:var(--muted)}
.eb{font-size:10.5px;letter-spacing:.3em;text-transform:uppercase;font-weight:700;color:var(--amber);text-align:center}
.h2{font-family:var(--disp);font-weight:400;font-size:27px;text-align:center;margin-top:8px;color:var(--ink)}
.sub{color:var(--muted);text-align:center;font-size:12.5px;margin-top:6px;margin-bottom:22px}
.payoff{font-family:var(--disp);font-style:italic;font-size:15.5px;color:#3d352b;text-align:center;margin-top:18px;line-height:1.5}
/* cover */
.cover{background:#DFCCB1;background-image:radial-gradient(120% 80% at 50% 0%,rgba(255,255,255,.32),rgba(255,255,255,0));color:#3A2E1F;text-align:center}
.brand{font-family:var(--body);font-weight:700;font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:#7A5A24;margin:6px 0 30px}
.cover h1{font-family:var(--disp);font-weight:400;font-size:40px;color:#2A2015}
.cover h1 .amp{color:#7A5A24;font-style:italic;font-size:30px;margin:0 4px}
.ringn{font-family:var(--disp);font-size:38px;fill:#2A2015}.ringl{font-size:9px;letter-spacing:.3em;fill:rgba(58,46,31,.6)}
.arch{font-family:var(--disp);font-style:italic;font-size:21px;color:#6E4F2E;margin-top:6px}
.tag{font-family:var(--disp);font-style:italic;font-size:15px;color:rgba(58,46,31,.74);max-width:290px;margin:14px auto 0}
.pill{display:inline-block;margin-top:22px;border:1px solid rgba(58,46,31,.42);color:#4A3A24;border-radius:100px;padding:8px 20px;font-size:12px;letter-spacing:.22em;text-transform:uppercase;font-weight:600}
/* scorecard */
.area{margin:0 0 18px}
.atop{display:flex;align-items:center;gap:10px;margin-bottom:7px}
.aem{font-size:19px}.anm{font-family:var(--disp);font-size:16px;flex:1}.apct{font-family:var(--disp);font-size:15px;color:var(--muted)}
.bar{height:8px;border-radius:6px;background:#EEE6D6;overflow:hidden}.bar>i{display:block;height:100%;border-radius:6px}
.fg{background:linear-gradient(90deg,#4E9C72,#3E7D5A)}.fa{background:linear-gradient(90deg,#E0B45C,#C9A34E)}.ft{background:linear-gradient(90deg,#E0A583,#C57E56)}
.foot{text-align:center;color:var(--muted);font-size:12.5px;margin-top:4px;font-style:italic;font-family:var(--disp)}
/* flags/super */
.flag{display:flex;gap:13px;align-items:flex-start;background:#fff;border:1px solid var(--line);border-radius:16px;padding:15px 17px;margin-bottom:12px;box-shadow:0 4px 16px rgba(90,60,20,.05)}
.flag .ic{width:36px;height:36px;flex:0 0 auto;border-radius:50%;background:#E7F1EA;color:var(--green);display:flex;align-items:center;justify-content:center;font-size:17px}
.flag b{font-family:var(--disp);font-size:15.5px;display:block}.flag p{font-size:12.5px;color:var(--muted);margin-top:2px}
.super{background:linear-gradient(135deg,var(--espresso1),var(--espresso2));color:#F3EEE4;border-radius:18px;padding:20px;margin-top:18px;text-align:center}
.super .l{color:var(--gold);letter-spacing:.26em;font-size:10px;font-weight:700}.super p{font-family:var(--disp);font-size:17px;line-height:1.5;margin-top:9px;color:#EDE7DA}
/* playbook */
.growbox{background:#FBEFE3;border:1px solid #EFD9C4;border-radius:16px;padding:17px;margin-bottom:16px}
.growbox .t{font-family:var(--disp);font-size:18px;color:var(--terra)}.growbox p{font-size:13px;color:#7a5a48;margin-top:6px}
.act{background:#fff;border:1px solid var(--line);border-left:3px solid var(--gold);border-radius:12px;padding:12px 15px;margin-bottom:10px;box-shadow:0 3px 12px rgba(90,60,20,.04)}
.act .k{font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:var(--amber);font-weight:700}.act .v{font-size:13.5px;margin-top:3px}.act .v em{font-family:var(--disp);font-style:italic;color:#6a5a48}
/* will it last */
.will{background:radial-gradient(120% 70% at 50% 0%,var(--espresso1),var(--espresso2) 68%);color:#F3EEE4;text-align:center}
.will .eb{color:var(--gold-lt)}.will .h2{color:#fff}
.bigyes{font-family:var(--disp);font-style:italic;font-size:40px;color:#E0B45C;margin:6px 0 12px}
.will .bd{font-family:var(--disp);font-size:15.5px;line-height:1.5;color:#D8CBB4;max-width:310px;margin:0 auto}
.norm{font-size:12px;color:#B3A488;max-width:290px;margin:16px auto 0}
.scard{background:var(--cream);color:var(--ink);border-radius:18px;padding:20px;margin:22px auto 0;max-width:320px;box-shadow:0 12px 32px rgba(0,0,0,.3)}
.scard .n{font-family:var(--disp);font-size:22px}.scard .a{color:var(--amber);font-style:italic;font-family:var(--disp);font-size:13px;margin-top:2px}
.scard .b{font-family:var(--disp);font-size:36px;color:var(--gold);margin-top:8px}.scard .v{font-size:10px;letter-spacing:.2em;text-transform:uppercase;color:var(--muted);margin-top:6px}
/* profiles */
.prof{background:#fff;border:1px solid var(--line);border-radius:18px;padding:14px 18px;margin-bottom:10px;box-shadow:0 5px 18px rgba(90,60,20,.05);text-align:center}
.prof .g{display:inline-flex;align-items:center;justify-content:center;width:40px;height:40px;border-radius:12px;background:#FFF9F3;border:1px solid #F1E7D6;color:var(--amber);font-size:20px;font-family:var(--body)}
.prof .nm{font-family:var(--disp);font-size:19px;margin-top:5px}
.brg{margin:6px 0 2px}.br{display:flex;gap:7px;justify-content:center;align-items:baseline;padding:2px 0;flex-wrap:wrap}
.br b{font-family:var(--disp);font-weight:600}.br span{font-size:10px;color:var(--muted)}
.br.s{color:#9a8fae;font-size:12.5px}
.br.m{background:#FBF4E7;border:1px solid #F0E2C4;border-radius:11px;padding:6px 10px;margin-top:3px;font-size:14px}.br.m b{color:var(--amber);font-size:16px}
.pmeta{font-size:11.5px;color:var(--muted);margin-top:3px}
.plove{font-family:var(--disp);font-style:italic;font-size:12.5px;color:#4a4459;margin-top:7px;border-top:1px solid var(--line);padding-top:7px;line-height:1.4}
.between{text-align:center;font-family:var(--disp);font-style:italic;font-size:15px;color:var(--terra);margin:4px 0 2px}
.moonwhy{background:#FBEFE3;border:1px solid #EFD9C4;border-radius:12px;padding:9px 14px;margin-top:10px;text-align:center}
.moonwhy p{font-size:11.6px;color:#7a5a48;font-style:italic;font-family:var(--disp);line-height:1.45}
/* koota cards */
.koota{background:#fff;border:1px solid var(--line);border-radius:14px;padding:13px 15px;margin-bottom:10px;box-shadow:0 2px 10px rgba(90,60,20,.04)}
.ktop{display:flex;align-items:center;gap:10px}.kem{font-size:19px}.knm{flex:1}.knm b{font-family:var(--disp);font-size:15px;display:block}.ksan{font-size:10.5px;color:var(--muted)}
.ks{font-family:var(--disp);font-weight:700;font-size:14px;color:var(--gold)}
.kbar{height:7px;border-radius:5px;background:#EEE6D6;overflow:hidden;margin:9px 0 0}.kbar>i{display:block;height:100%}
.kt{margin-top:9px;color:#3b3450;font-size:13px}
.kfix{margin-top:10px;background:#FBF6EC;border:1px solid #F0E2C4;border-radius:11px;padding:11px 12px}
.kfix p{font-size:12.5px;margin-top:5px;color:#4a4636}.kfix p:first-child{margin-top:0}
.wpk{font-family:var(--disp);font-weight:800;font-size:11.5px;color:var(--terra);margin-right:5px}
/* checks / method */
.chk{display:flex;gap:12px;align-items:flex-start;padding:13px 0;border-top:1px solid var(--line)}
.chk .bd{width:26px;height:26px;border-radius:50%;flex:0 0 auto;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800;color:#fff}
.chk .bd.ok{background:var(--green)}.chk .bd.mild{background:var(--amber)}
.chk b{font-family:var(--disp);font-size:14.5px}.chk p{font-size:12px;color:var(--muted);margin-top:2px}
.dark{background:linear-gradient(135deg,var(--espresso1),var(--espresso2));color:#E9E3D6}
.dark .eb{color:var(--gold-lt)}.dark .h2{color:#fff}
.mstep{display:flex;gap:12px;align-items:flex-start;margin-top:15px}
.mstep .n{width:26px;height:26px;border-radius:50%;border:1px solid var(--gold);color:var(--gold);flex:0 0 auto;display:flex;align-items:center;justify-content:center;font-size:12px;font-family:var(--disp)}
.mstep b{font-family:var(--disp);font-size:14px;color:#fff}.mstep p{font-size:12px;color:#CBBFA6;margin-top:2px}
.tagline{font-family:var(--disp);font-style:italic;font-size:15px;color:var(--gold-lt);text-align:center;margin-top:20px}
.crow{background:#fff;border:1px solid var(--line);border-radius:12px;padding:11px 14px;margin-bottom:8px}
.crow .ct{display:flex;justify-content:space-between;align-items:baseline}.crow .cn{font-family:var(--disp);font-size:14px}.crow .cn small{color:var(--muted);font-weight:400;font-size:10px}
.crow .sc{font-family:var(--disp);font-weight:600;color:var(--amber);font-size:14px}.crow .val{font-size:12px;margin-top:5px;color:#4a4459}.crow .rule{font-size:11px;color:#8a7f99;margin-top:4px;font-style:italic}
.actbar{max-width:440px;margin:0 auto;padding:18px 30px 34px;background:var(--cream);text-align:center}
.actbar a{display:inline-block;margin:4px;background:linear-gradient(135deg,var(--espresso1),var(--espresso2));color:#F3EEE4;text-decoration:none;border-radius:100px;padding:12px 22px;font-weight:700;font-size:14px;font-family:var(--body)}
.actbar a.wa{background:#25D366;color:#0b2f18}
@page{size:440px 812px;margin:0}
@media print{body{background:#fff;-webkit-print-color-adjust:exact;print-color-adjust:exact}.book{max-width:440px}
.pg{width:440px;height:812px;page-break-after:always;border-bottom:none}.pg:last-child{page-break-after:auto}
.actbar{display:none}}
"""

AX_PRE = ('<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
          '<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;'
          '0,9..144,600;1,9..144,400&family=Jost:wght@400;500;600;700&display=swap" rel="stylesheet">')


def _chip(pct):
    if pct >= 75: return ("Strong \U0001F49A", "fg", "var(--green)")
    if pct >= 45: return ("Solid \U0001F49B", "fa", "var(--amber)")
    return ("Grow \U0001F331", "ft", "var(--terra)")


def _ring(pct):
    circ = 439.8
    dash = max(0.0, min(pct, 100)) / 100 * circ
    return (f'<svg width="164" height="164" viewBox="0 0 164 164">'
            f'<circle cx="82" cy="82" r="70" fill="none" stroke="rgba(58,46,31,.18)" stroke-width="7"/>'
            f'<circle cx="82" cy="82" r="70" fill="none" stroke="#5C4426" stroke-width="7" stroke-linecap="round" '
            f'stroke-dasharray="{dash:.1f} {circ}" transform="rotate(-90 82 82)"/>'
            f'<text class="ringn" x="82" y="84" text-anchor="middle">{pct}%</text>'
            f'<text class="ringl" x="82" y="104" text-anchor="middle">COMPATIBLE</text></svg>')


def _verdict_word(pct):
    if pct >= 88: return "Excellent Match"
    if pct >= 68: return "Very Good Match"
    if pct >= 50: return "Good Match"
    return "Worth Understanding"


def render_milan_v2(p: dict) -> str:
    m = p.get("meta", {})
    p1n = escape(m.get("p1", "Partner 1")); p2n = escape(m.get("p2", "Partner 2"))
    kootas = p.get("kootas", [])
    by = {k["name"]: k for k in kootas}
    pct = int(p.get("match_pct") or round((p.get("effective") or p.get("total", 0)) / 36 * 100))
    prof = p.get("profiles") or {}
    pr1, pr2 = prof.get("p1", {}), prof.get("p2", {})
    arch = ARCHETYPE.get(frozenset({pr1.get("element"), pr2.get("element")}), ARCHETYPE_DEFAULT)
    themes = _theme_scores(kootas)                 # strongest first
    strong = [t for t in themes if t["pct"] >= 75]
    weak = [t for t in themes if t["pct"] < 45]

    # ---- cover ----
    cover = f"""<section class="pg cover">
      <div class="brand">✦ Axtroshastra · Love Compatibility</div>
      <h1>{p1n} <span class="amp">&amp;</span> {p2n}</h1>
      <div style="display:flex;justify-content:center;margin:22px 0 6px">{_ring(pct)}</div>
      <div class="arch">{escape(arch['name'])} {arch.get('emoji','')}</div>
      <div class="tag">{escape((narr(p,'headline') or arch.get('tagline','')))}</div>
      <div class="pill">{_verdict_word(pct)}</div><div class="pn">01</div></section>"""

    # ---- scorecard ----
    rows = ""
    for t in themes:
        th = t["theme"]; ap = int(round(t["pct"])); label, fill, _ = _chip(t["pct"])
        rows += (f'<div class="area"><div class="atop"><span class="aem">{th["emoji"]}</span>'
                 f'<span class="anm">{escape(th["name"])}</span><span class="apct">{ap}%</span></div>'
                 f'<div class="bar"><i class="{fill}" style="width:{max(ap,6)}%"></i></div></div>')
    scorecard = f"""<section class="pg"><div class="eb">At a glance</div>
      <div class="h2">How you match, in {len(themes)} areas</div><div class="sub">Strongest first</div>
      {rows}<div class="foot">{len(strong)} of your {len(themes)} areas are naturally strong.</div>
      <div class="pn">02</div></section>"""

    # ---- why you work ----
    flags = ""
    for t in strong[:3]:
        th = t["theme"]
        flags += (f'<div class="flag"><div class="ic">{th["emoji"]}</div><div><b>{escape(th["name"])}</b>'
                  f'<p>{escape(th["blurb"])}.</p></div></div>')
    if not flags:
        flags = '<div class="flag"><div class="ic">✨</div><div><b>Your own kind of match</b><p>A mix that’s uniquely yours.</p></div></div>'
    superp = (narr(p, "summary") or
              f"You’re strong where it’s hardest to build — {', '.join(escape(t['theme']['name']) for t in strong[:3]) or 'the foundations'}.")
    why = f"""<section class="pg"><div class="eb">Your green flags</div>
      <div class="h2">Why you two work</div><div class="sub">The strengths worth celebrating \U0001F49A</div>
      {flags}<div class="super"><div class="l">YOUR SUPERPOWER</div><p>{superp}</p></div>
      <div class="pn">03</div></section>"""

    # ---- playbook (weakest koota that has a fix) ----
    play = _playbook_section(p, by)

    # ---- will it last ----
    will = f"""<section class="pg will"><div class="eb">The honest answer</div><div class="h2">Will it last?</div>
      <div class="bigyes">Yes — with intention.</div>
      <p class="bd">You’ve got a strong hand: {pct}%, with your deepest foundations already solid. Compatibility gets you to the start line; the playbook wins the race.</p>
      <p class="norm">Most happy couples aren’t 100%. A strong base + a little effort = a genuinely lasting match.</p>
      <div class="scard"><div class="n">{p1n} &amp; {p2n}</div><div class="a">{escape(arch['name'])} {arch.get('emoji','')}</div>
      <div class="b">{pct}%</div><div class="v">{_verdict_word(pct)}</div></div><div class="pn">05</div></section>"""

    # ---- the two of you (sun -> moon bridge) ----
    twoyou = _two_of_you(p, pr1, pr2, arch)

    # ---- the 8 factors ----
    factors = _factors_section(p, kootas)

    # ---- traditional checks ----
    checks = _checks_section(p, by)

    # ---- calculations appendix ----
    appendix = _appendix(p, pr1, pr2, kootas)

    body = cover + scorecard + why + play + will + twoyou + factors + checks + appendix
    share = ("https://wa.me/?text=" +
             f"Our%20Kundli%20Milan%3A%20{pct}%25%20-%20{arch['name'].replace(' ','%20')}%20%E2%9C%A8")
    actbar = (f'<div class="actbar"><a href="#" onclick="window.print();return false;">'
              f'&#11015; Download PDF</a> <a class="wa" href="{share}" target="_blank" rel="noopener">'
              f'Share on WhatsApp</a></div>')
    return (f'<!DOCTYPE html><html lang="en"><head>{AX_PRE}<title>{p1n} ✕ {p2n} '
            f'— Love Compatibility</title><style>{CSS}</style></head>'
            f'<body><div class="book">{body}</div>{actbar}</body></html>')


def _playbook_section(p, by):
    ranked = sorted((k for k in by.values() if k["max"]), key=lambda k: k["score"] / k["max"])
    target = next((k for k in ranked if k["name"] in REMEDIES and k["score"] / k["max"] < 0.6), None)
    if not target:
        return ""
    ui = KOOTA_UI.get(target["name"], {"emoji": "\U0001F331", "label": target["name"]})
    rem = REMEDIES.get(target["name"], {})
    ap = ACTION_PLAN.get(target["name"], {})
    intro = narr(p, "growth") or rem.get("work_on", target.get("text", ""))
    acts = ""
    if ap.get("try"): acts += f'<div class="act"><div class="k">\U0001F3AF Try this week</div><div class="v">{escape(ap["try"])}</div></div>'
    if ap.get("talk"): acts += f'<div class="act"><div class="k">\U0001F4AC Say this</div><div class="v"><em>{escape(ap["talk"])}</em></div></div>'
    if ap.get("green"): acts += f'<div class="act"><div class="k">✅ Green flag you’ll notice</div><div class="v">{escape(ap["green"])}</div></div>'
    return f"""<section class="pg"><div class="eb">Your playbook</div>
      <div class="h2">One thing worth working on</div><div class="sub">Small effort, big payoff</div>
      <div class="growbox"><div class="t">{ui['emoji']} {escape(ui['label'])}</div><p>{escape(intro)}</p></div>
      {acts}<div class="pn">04</div></section>"""


def _two_of_you(p, pr1, pr2, arch):
    def card(pr):
        sun = pr.get("sun_western"); moon = escape(pr.get("sign", "")); nm = escape(pr.get("name", ""))
        glyph = SIGN_GLYPH.get(moon, "✦")
        sunrow = (f'<div class="br s">☀️ <b>{escape(sun)}</b> <span>· the sign the world knows you by</span></div>'
                  if sun else "")
        return (f'<div class="prof"><div class="g">{glyph}︎</div><div class="nm">{nm}</div>'
                f'<div class="brg">{sunrow}'
                f'<div class="br m">\U0001F319 <b>{moon} Moon</b> <span>· your love sign</span></div></div>'
                f'<div class="pmeta">{escape(pr.get("nak",""))} · {escape((pr.get("element") or "").title())} '
                f'· ruled by {escape(pr.get("lord",""))}</div>'
                f'<div class="plove">"{escape(pr.get("love",""))}"</div></div>')
    el = p.get("element") or {}
    return f"""<section class="pg"><div class="eb">Where it begins</div>
      <div class="h2">The two of you</div><div class="sub">You know your Sun sign. For love, we read your Moon.</div>
      {card(pr1)}<div class="between">{escape(el.get('p1','') )} meets {escape(el.get('p2',''))}</div>{card(pr2)}
      <div class="moonwhy"><p>The Sun is who you are to the world; the Moon is who you are in love — so Vedic matching reads the Moon, not the Sun.</p></div>
      <div class="pn">06</div></section>"""


def _factors_section(p, kootas):
    ranked = sorted(kootas, key=lambda k: (k["score"] / k["max"]) if k["max"] else 0, reverse=True)
    cancelled = {c.get("koota") for c in (p.get("cancellations") or [])}
    cards = ""
    for k in ranked:
        pct = (k["score"] / k["max"] * 100) if k["max"] else 0
        ui = KOOTA_UI.get(k["name"], {"emoji": "•", "label": k["name"], "blurb": k.get("meaning", "")})
        fill = "var(--green)" if pct >= 75 else ("var(--amber)" if pct >= 40 else "var(--terra)")
        sc = int(k["score"]) if float(k["score"]).is_integer() else k["score"]
        fix = ""
        if k["max"] and k["score"] / k["max"] < 0.5 and k["name"] in REMEDIES:
            rem = REMEDIES[k["name"]]
            canc = ('<p style="color:var(--green);font-weight:700">✅ Traditionally cancelled — a lighter priority.</p>'
                    if k["name"] in cancelled else "")
            split = (f'<p><span class="wpk">\U0001F465 Each of you</span> {escape(rem["each"])}</p>' if rem.get("each")
                     else "".join(f'<p><span class="wpk">\U0001F464</span> {escape(rem[x])}</p>' for x in ("p1", "p2") if rem.get(x)))
            fix = f'<div class="kfix">{canc}<p><span class="wpk">\U0001F4A1 Work on it</span> {escape(rem.get("work_on",""))}</p>{split}</div>'
        cards += (f'<div class="koota"><div class="ktop"><span class="kem">{ui["emoji"]}</span>'
                  f'<span class="knm"><b>{escape(ui["label"])}</b><span class="ksan">{escape(k["name"])} koota</span></span>'
                  f'<span class="ks">{sc}/{k["max"]}</span></div>'
                  f'<div class="kbar"><i style="width:{max(pct,4):.0f}%;background:{fill}"></i></div>'
                  f'<p class="kt">{escape(k.get("text",""))}</p>{fix}</div>')
    return f"""<section class="pg"><div class="eb">The full reading</div>
      <div class="h2">All 8 factors, decoded</div><div class="sub">The classical Ashtakoota system, in plain English</div>
      {cards}<div class="pn">07</div></section>"""


def _checks_section(p, by):
    mg = p.get("manglik") or {}
    mg_badge = "mild" if (mg.get("p1") or mg.get("p2")) else "ok"
    mg_sym = "!" if (mg.get("p1") or mg.get("p2")) else "✓"
    nadi = by.get("Nadi", {}); bhak = by.get("Bhakoot", {})
    nadi_ok = (nadi.get("score", 0) > 0)
    bhak_ok = (bhak.get("score", 0) > 0) or ("Bhakoot" in {c.get("koota") for c in (p.get("cancellations") or [])})
    def row(badge, sym, name, text):
        return f'<div class="chk"><div class="bd {badge}">{sym}</div><div><b>{name}</b><p>{escape(text)}</p></div></div>'
    checks = row(mg_badge, mg_sym, "Manglik (Mangal Dosha)", mg.get("note", ""))
    checks += row("ok" if nadi_ok else "mild", "✓" if nadi_ok else "!", "Nadi Dosha",
                  "Your Nadis differ — no Nadi dosha, a strong positive sign." if nadi_ok
                  else "Nadi is shared — see the cancellation note; often lifted when moon-signs differ.")
    checks += row("ok" if bhak_ok else "mild", "✓" if bhak_ok else "!", "Bhakoot Dosha",
                  "Your Moon signs sit in a favourable position — long-term harmony supported." if bhak_ok
                  else "A Bhakoot placement is present — check whether it’s cancelled by friendly moon-lords.")
    return f"""<section class="pg"><div class="eb">The three big ones</div>
      <div class="h2">The traditional checks</div><div class="sub">Demystified — no fear, just facts</div>
      {checks}<div class="pn">17</div></section>"""


def _appendix(p, pr1, pr2, kootas):
    def crow(k):
        sc = int(k["score"]) if float(k["score"]).is_integer() else k["score"]
        return (f'<div class="crow"><div class="ct"><div class="cn">{escape(k["name"])} '
                f'<small>· {escape(k.get("meaning",""))}</small></div><div class="sc">{sc}/{k["max"]}</div></div>'
                f'<div class="val">{escape(k.get("detail",""))}</div></div>')
    rows = "".join(crow(k) for k in kootas)
    total = p.get("total"); eff = p.get("effective"); pct = p.get("match_pct")
    g1 = SIGN_GLYPH.get(pr1.get("sign"), "✦"); g2 = SIGN_GLYPH.get(pr2.get("sign"), "✦")
    return f"""<section class="pg dark"><div class="eb">The proof</div>
      <div class="h2">How this was calculated</div><div class="sub" style="color:#B3A488">Not guessed. Computed.</div>
      <div class="mstep"><div class="n">1</div><div><b>Your real sky, at birth</b><p>True Moon positions from your birth details — Swiss Ephemeris, sidereal zodiac, Lahiri ayanamsa.</p></div></div>
      <div class="mstep"><div class="n">2</div><div><b>The classical method</b><p>Ashtakoota (36-guna) across 8 factors; dosha rules applied exactly.</p></div></div>
      <div class="mstep"><div class="n">3</div><div><b>The eight scores</b><p style="color:#CBBFA6">total {total}/36 → effective {eff}/36 → {pct}% · no opinion, only calculation.</p></div></div>
      <div style="background:#fff;border-radius:12px;padding:6px 14px;margin-top:16px">{rows}</div>
      <div class="tagline">Jyotish, calculated — no opinion, only calculation.</div><div class="pn">21</div></section>"""
