"""
milan_v2.py — redesigned Kundli Milan report (Warm palette, GenZ positioning).

Full ~30-page payload-driven renderer for compute_milan() output. Feature-flagged:
the web layer calls this only via /report/{id}?v2=1, so the live render_milan in
report_view.py is untouched while it's built out.

Every FACT is engine-computed and read here — no astrology in the view. Reuses the
classical tables (THEMES/KOOTA_UI/REMEDIES/ACTION_PLAN/ARCHETYPE) from
report_view.py. Descriptive PROSE slots call the LLM via narr(); when the LLM is
off/unfunded, narr() returns None and the deterministic bank text is used.
"""
from html import escape
from narrative import narr
from report_view import (THEMES, KOOTA_UI, REMEDIES, ACTION_PLAN, THEME_DEEP,
                         ARCHETYPE, ARCHETYPE_DEFAULT, _theme_scores)

SIGN_GLYPH = {"Aries": "♈", "Taurus": "♉", "Gemini": "♊", "Cancer": "♋",
              "Leo": "♌", "Virgo": "♍", "Libra": "♎", "Scorpio": "♏",
              "Sagittarius": "♐", "Capricorn": "♑", "Aquarius": "♒", "Pisces": "♓"}

CSS = """
:root{--cream:#FAF6EE;--beige:#DFCCB1;--espresso1:#3a2c18;--espresso2:#241810;
--gold:#C9A34E;--gold-lt:#E7CE8F;--ink:#2A2338;--muted:#8A8199;--line:#ECE3D3;
--green:#3E7D5A;--amber:#B9862E;--terra:#B4674A;--bronze:#6E4F2E;
--disp:'Fraunces',Georgia,serif;--body:'Jost',-apple-system,Segoe UI,sans-serif}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--body);background:#E8E1D4;color:var(--ink);line-height:1.6;-webkit-font-smoothing:antialiased}
.book{max-width:440px;margin:0 auto}
.pg{position:relative;min-height:720px;padding:42px 30px;overflow:hidden;background:var(--cream);border-bottom:1px solid #ded4c2}
.pn{position:absolute;bottom:18px;left:0;right:0;text-align:center;font-size:10px;letter-spacing:.35em;color:var(--muted)}
.eb{font-size:10.5px;letter-spacing:.3em;text-transform:uppercase;font-weight:700;color:var(--amber);text-align:center}
.h2{font-family:var(--disp);font-weight:400;font-size:26px;text-align:center;margin-top:8px;color:var(--ink);line-height:1.2}
.sub{color:var(--muted);text-align:center;font-size:12.5px;margin-top:6px;margin-bottom:20px}
.lead{font-family:var(--disp);font-size:16px;line-height:1.5;color:#3d352b;text-align:center;margin-bottom:8px}
.payoff{font-family:var(--disp);font-style:italic;font-size:15px;color:#3d352b;text-align:center;margin-top:18px;line-height:1.5}
.rule{width:34px;height:1px;background:var(--gold);margin:12px auto}
/* cover */
.cover{background:#DFCCB1;background-image:radial-gradient(120% 80% at 50% 0%,rgba(255,255,255,.32),rgba(255,255,255,0));color:#3A2E1F;text-align:center}
.brand{font-weight:700;font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:#7A5A24;margin:6px 0 30px}
.cover h1{font-family:var(--disp);font-weight:400;font-size:40px;color:#2A2015}
.cover h1 .amp{color:#7A5A24;font-style:italic;font-size:30px;margin:0 4px}
.ringn{font-family:var(--disp);font-size:38px;fill:#2A2015}.ringl{font-size:9px;letter-spacing:.3em;fill:rgba(58,46,31,.6)}
.arch{font-family:var(--disp);font-style:italic;font-size:21px;color:#6E4F2E;margin-top:6px}
.tag{font-family:var(--disp);font-style:italic;font-size:15px;color:rgba(58,46,31,.74);max-width:290px;margin:14px auto 0}
.pill{display:inline-block;margin-top:22px;border:1px solid rgba(58,46,31,.42);color:#4A3A24;border-radius:100px;padding:8px 20px;font-size:12px;letter-spacing:.22em;text-transform:uppercase;font-weight:600}
/* scorecard */
.area{margin:0 0 17px}.atop{display:flex;align-items:center;gap:10px;margin-bottom:7px}
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
/* playbook/acts */
.growbox{background:#FBEFE3;border:1px solid #EFD9C4;border-radius:16px;padding:17px;margin-bottom:16px}
.growbox .t{font-family:var(--disp);font-size:18px;color:var(--terra)}.growbox p{font-size:13px;color:#7a5a48;margin-top:6px}
.act{background:#fff;border:1px solid var(--line);border-left:3px solid var(--gold);border-radius:12px;padding:12px 15px;margin-bottom:10px;box-shadow:0 3px 12px rgba(90,60,20,.04)}
.act .k{font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:var(--amber);font-weight:700}.act .v{font-size:13.5px;margin-top:3px}.act .v em{font-family:var(--disp);font-style:italic;color:#6a5a48}
.ritual{font-size:11.5px;color:var(--muted);text-align:center;margin-top:12px;font-style:italic;font-family:var(--disp)}
/* will */
.will{background:radial-gradient(120% 70% at 50% 0%,var(--espresso1),var(--espresso2) 68%);color:#F3EEE4;text-align:center}
.will .eb{color:var(--gold-lt)}.will .h2{color:#fff}
.bigyes{font-family:var(--disp);font-style:italic;font-size:40px;color:#E0B45C;margin:6px 0 12px}
.will .bd{font-family:var(--disp);font-size:15.5px;line-height:1.5;color:#D8CBB4;max-width:310px;margin:0 auto}
.norm{font-size:12px;color:#B3A488;max-width:290px;margin:16px auto 0}
.scard{background:var(--cream);color:var(--ink);border-radius:18px;padding:20px;margin:22px auto 0;max-width:320px;box-shadow:0 12px 32px rgba(0,0,0,.3)}
.scard .n{font-family:var(--disp);font-size:22px}.scard .a{color:var(--amber);font-style:italic;font-family:var(--disp);font-size:13px;margin-top:2px}
.scard .b{font-family:var(--disp);font-size:36px;color:var(--gold);margin-top:8px}.scard .st{color:var(--gold);letter-spacing:4px;margin-top:3px}.scard .v{font-size:10px;letter-spacing:.2em;text-transform:uppercase;color:var(--muted);margin-top:6px}
/* profiles */
.prof{background:#fff;border:1px solid var(--line);border-radius:18px;padding:14px 18px;margin-bottom:10px;box-shadow:0 5px 18px rgba(90,60,20,.05);text-align:center}
.prof .g{display:inline-flex;align-items:center;justify-content:center;width:40px;height:40px;border-radius:12px;background:#FFF9F3;border:1px solid #F1E7D6;color:var(--amber);font-size:20px;font-family:var(--body)}
.prof .nm{font-family:var(--disp);font-size:19px;margin-top:5px}
.brg{margin:6px 0 2px}.br{display:flex;gap:7px;justify-content:center;align-items:baseline;padding:2px 0;flex-wrap:wrap}
.br b{font-family:var(--disp);font-weight:600}.br span{font-size:10px;color:var(--muted)}
.br.s{color:#9a8fae;font-size:12.5px}.br.m{background:#FBF4E7;border:1px solid #F0E2C4;border-radius:11px;padding:6px 10px;margin-top:3px;font-size:14px}.br.m b{color:var(--amber);font-size:16px}
.pmeta{font-size:11.5px;color:var(--muted);margin-top:3px}
.plove{font-family:var(--disp);font-style:italic;font-size:12.5px;color:#4a4459;margin-top:7px;border-top:1px solid var(--line);padding-top:7px;line-height:1.4}
.between{text-align:center;font-family:var(--disp);font-style:italic;font-size:15px;color:var(--terra);margin:4px 0 2px}
.moonwhy{background:#FBEFE3;border:1px solid #EFD9C4;border-radius:12px;padding:9px 14px;margin-top:10px;text-align:center}
.moonwhy p{font-size:11.6px;color:#7a5a48;font-style:italic;font-family:var(--disp);line-height:1.45}
.coupleft{background:linear-gradient(135deg,#20264a00,#241810);background:linear-gradient(135deg,var(--espresso1),var(--espresso2));color:#EDE7DA;border-radius:18px;padding:22px;text-align:center}
.coupleft .ce{font-size:28px}.coupleft h3{color:#fff;font-family:var(--disp);font-size:21px;margin-top:6px}.coupleft .ct{color:var(--gold-lt);font-style:italic;font-family:var(--disp);font-size:13.5px;margin-top:2px}.coupleft p{color:#CBBFA6;margin-top:12px;font-size:14px}
/* area/koota */
.scorebig{font-family:var(--disp);font-size:42px;text-align:center}.scorebig small{font-size:19px;color:var(--muted)}
.trophy{width:60px;height:60px;border-radius:50%;background:linear-gradient(135deg,#EAF1EC,#DDEBE1);display:flex;align-items:center;justify-content:center;font-size:28px;margin:0 auto 4px}
.trophy.a{background:linear-gradient(135deg,#FBEFE3,#F1DEC8)}
.koota{background:#fff;border:1px solid var(--line);border-radius:13px;padding:12px 14px;margin-bottom:9px;box-shadow:0 2px 10px rgba(90,60,20,.04)}
.ktop{display:flex;align-items:center;gap:10px}.kem{font-size:18px}.knm{flex:1}.knm b{font-family:var(--disp);font-size:14.5px;display:block}.ksan{font-size:10px;color:var(--muted)}
.ks{font-family:var(--disp);font-weight:700;font-size:14px;color:var(--gold)}
.kbar{height:6px;border-radius:5px;background:#EEE6D6;overflow:hidden;margin:8px 0 0}.kbar>i{display:block;height:100%}
.kt{margin-top:8px;color:#3b3450;font-size:12.5px}
.scene{background:#FBEFE3;border:1px solid #EFD9C4;border-radius:13px;padding:14px 15px;margin-bottom:14px}
.scene .t{font-family:var(--disp);font-size:14px;color:var(--terra);font-style:italic}.scene p{font-size:12.5px;color:#7a5a48;margin-top:5px}
.why{background:#fff;border:1px solid var(--line);border-radius:13px;padding:14px;margin-top:14px}.why .t{font-family:var(--disp);font-size:14.5px;color:var(--green)}.why.a .t{color:var(--terra)}.why p{font-size:13px;color:#4a4459;margin-top:5px}
.story{font-family:var(--disp);font-size:16.5px;line-height:1.65;color:#3d352b;text-align:center;margin-top:8px}.story b{color:var(--amber);font-weight:600}
/* checks/timing */
.chk{display:flex;gap:12px;align-items:flex-start;padding:13px 0;border-top:1px solid var(--line)}
.chk .bd{width:26px;height:26px;border-radius:50%;flex:0 0 auto;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800;color:#fff}
.chk .bd.ok{background:var(--green)}.chk .bd.mild{background:var(--amber)}.chk .bd.ic{background:transparent;font-size:17px}
.chk b{font-family:var(--disp);font-size:14.5px}.chk p{font-size:12px;color:var(--muted);margin-top:2px}
/* elements */
.elems{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}
.elbox{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px;text-align:center}.elbox .e{font-size:26px}.elbox b{font-family:var(--disp);display:block;margin-top:4px}
/* letter/cert/ref */
.letter{background:#fff;border:1px solid var(--line);border-radius:18px;padding:22px 20px;margin-top:14px;box-shadow:0 6px 22px rgba(90,60,20,.06)}
.letter p{font-family:var(--disp);font-size:15px;line-height:1.7;color:#3d352b}.letter .sign{font-family:var(--disp);font-style:italic;font-size:14px;color:var(--amber);margin-top:14px;text-align:right}
.cert{border:2px solid var(--gold);border-radius:16px;padding:26px 20px;margin-top:16px;text-align:center;background:linear-gradient(180deg,#fffdf8,#FAF3E4)}
.cert .seal{font-size:26px;color:var(--gold)}.cert .lbl{letter-spacing:.26em;font-size:10px;color:var(--amber);font-weight:700;margin-top:6px}
.cert .n{font-family:var(--disp);font-size:26px;margin-top:8px}.cert .a{font-family:var(--disp);font-style:italic;color:var(--amber);font-size:14px;margin-top:2px}
.cert .st{color:var(--gold);letter-spacing:5px;font-size:17px;margin:11px 0}.cert .b{font-family:var(--disp);font-size:19px}.cert .q{font-family:var(--disp);font-style:italic;font-size:12.5px;color:var(--muted);margin-top:11px}
.refbox{background:linear-gradient(135deg,var(--espresso1),var(--espresso2));color:#EDE7DA;border-radius:18px;padding:22px;margin-top:14px;text-align:center}
.refbox .l2{font-family:var(--disp);font-size:19px;color:#fff}.refbox p{font-size:13px;color:#CBBFA6;margin-top:8px}
.refbtn{display:inline-block;margin-top:14px;background:var(--gold);color:#2A2015;font-weight:700;border-radius:100px;padding:11px 22px;font-size:13px;text-decoration:none}
/* dark/method/appendix */
.dark{background:linear-gradient(135deg,var(--espresso1),var(--espresso2));color:#E9E3D6}.dark .eb{color:var(--gold-lt)}.dark .h2{color:#fff}
.mstep{display:flex;gap:12px;align-items:flex-start;margin-top:15px}.mstep .n{width:26px;height:26px;border-radius:50%;border:1px solid var(--gold);color:var(--gold);flex:0 0 auto;display:flex;align-items:center;justify-content:center;font-size:12px;font-family:var(--disp)}
.mstep b{font-family:var(--disp);font-size:14px;color:#fff}.mstep p{font-size:12px;color:#CBBFA6;margin-top:2px}
.moons{display:flex;gap:12px;justify-content:center;margin-top:18px}.moonchip{background:rgba(255,255,255,.06);border:1px solid rgba(201,163,78,.3);border-radius:12px;padding:10px 14px;text-align:center}.moonchip .g{font-size:20px;color:var(--gold-lt)}.moonchip .s{font-size:10px;color:#CBBFA6;margin-top:3px}
.tagline{font-family:var(--disp);font-style:italic;font-size:15px;color:var(--gold-lt);text-align:center;margin-top:20px}
.gloss{font-size:12px;color:#4a4459;padding:8px 0;border-top:1px solid var(--line)}.gloss:first-of-type{border-top:0}.gloss b{font-family:var(--disp);color:var(--ink)}
.crow{background:#fff;border:1px solid var(--line);border-radius:12px;padding:11px 14px;margin-bottom:8px}
.crow .ct{display:flex;justify-content:space-between;align-items:baseline}.crow .cn{font-family:var(--disp);font-size:14px}.crow .cn small{color:var(--muted);font-weight:400;font-size:10px}
.crow .sc{font-family:var(--disp);font-weight:600;color:var(--amber);font-size:14px}.crow .val{font-size:12px;margin-top:5px;color:#4a4459}.crow .rl{font-size:11px;color:#8a7f99;margin-top:4px;font-style:italic}
.total{text-align:center;background:var(--espresso2);color:#fff;border-radius:12px;padding:11px;font-family:var(--disp);font-weight:600;margin:12px 0 4px}
.verify{background:rgba(62,125,90,.14);border:1px solid rgba(62,125,90,.4);border-radius:12px;padding:14px 15px;margin-top:14px}.verify b{font-family:var(--disp);color:#9fe0bd}.verify p{font-size:12px;color:#B9D6C6;margin-top:5px}
/* actions */
.actbar{max-width:440px;margin:0 auto;padding:18px 30px 34px;background:var(--cream);text-align:center}
.actbar a{display:inline-block;margin:4px;background:linear-gradient(135deg,var(--espresso1),var(--espresso2));color:#F3EEE4;text-decoration:none;border-radius:100px;padding:12px 22px;font-weight:700;font-size:14px;font-family:var(--body)}
.actbar a.wa{background:#25D366;color:#0b2f18}
@page{size:440px 812px;margin:0}
@media print{body{background:#fff;-webkit-print-color-adjust:exact;print-color-adjust:exact}.book{max-width:440px}
.pg{width:440px;height:812px;page-break-after:always;border-bottom:none}.pg:last-child{page-break-after:auto}.actbar{display:none}}
"""

AX_PRE = ('<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
          '<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;'
          '0,9..144,600;1,9..144,400&family=Jost:wght@400;500;600;700&display=swap" rel="stylesheet">')


def _chip(pct):
    if pct >= 75: return ("fg", "var(--green)", "Strong \U0001F49A")
    if pct >= 45: return ("fa", "var(--amber)", "Solid \U0001F49B")
    return ("ft", "var(--terra)", "Grow \U0001F331")


def _ring(pct):
    circ = 439.8; dash = max(0.0, min(pct, 100)) / 100 * circ
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


def _stars(pct):
    n = max(1, min(5, round(pct / 20)))
    return "★ " * n + "☆ " * (5 - n)


def _mini_koota(k):
    pct = (k["score"] / k["max"] * 100) if k["max"] else 0
    ui = KOOTA_UI.get(k["name"], {"emoji": "•", "label": k["name"]})
    fill = "var(--green)" if pct >= 75 else ("var(--amber)" if pct >= 40 else "var(--terra)")
    sc = int(k["score"]) if float(k["score"]).is_integer() else k["score"]
    return (f'<div class="koota"><div class="ktop"><span class="kem">{ui["emoji"]}</span>'
            f'<span class="knm"><b>{escape(ui["label"])}</b><span class="ksan">{escape(k["name"])} koota</span></span>'
            f'<span class="ks">{sc}/{k["max"]}</span></div>'
            f'<div class="kbar"><i style="width:{max(pct,4):.0f}%;background:{fill}"></i></div>'
            f'<p class="kt">{escape(k.get("text",""))}</p></div>')


# ------------------------------------------------------------------ builders
def render_milan_v2(p: dict) -> str:
    m = p.get("meta", {})
    p1n = escape(m.get("p1", "Partner 1")); p2n = escape(m.get("p2", "Partner 2"))
    kootas = p.get("kootas", []); by = {k["name"]: k for k in kootas}
    pct = int(p.get("match_pct") or round((p.get("effective") or p.get("total", 0)) / 36 * 100))
    prof = p.get("profiles") or {}; pr1, pr2 = prof.get("p1", {}), prof.get("p2", {})
    arch = ARCHETYPE.get(frozenset({pr1.get("element"), pr2.get("element")}), ARCHETYPE_DEFAULT)
    themes = _theme_scores(kootas)                     # strongest first
    strong = [t for t in themes if t["pct"] >= 75]
    S = []                                             # (css_class, inner_html)

    # 1 cover
    S.append(("cover",
        f'<div class="brand">✦ Axtroshastra · Love Compatibility</div>'
        f'<h1>{p1n} <span class="amp">&amp;</span> {p2n}</h1>'
        f'<div style="display:flex;justify-content:center;margin:22px 0 6px">{_ring(pct)}</div>'
        f'<div class="arch">{escape(arch["name"])} {arch.get("emoji","")}</div>'
        f'<div class="tag">{narr(p,"headline") or escape(arch.get("tagline",""))}</div>'
        f'<div class="pill">{_verdict_word(pct)}</div>'))

    # 2 scorecard
    rows = ""
    for t in themes:
        th = t["theme"]; ap = int(round(t["pct"])); fill, _, _ = _chip(t["pct"])
        rows += (f'<div class="area"><div class="atop"><span class="aem">{th["emoji"]}</span>'
                 f'<span class="anm">{escape(th["name"])}</span><span class="apct">{ap}%</span></div>'
                 f'<div class="bar"><i class="{fill}" style="width:{max(ap,6)}%"></i></div></div>')
    S.append(("", f'<div class="eb">At a glance</div><div class="h2">How you match, in {len(themes)} areas</div>'
                  f'<div class="sub">Strongest first</div>{rows}'
                  f'<div class="foot">{len(strong)} of your {len(themes)} areas are naturally strong.</div>'))

    # 3 why you work
    flags = ""
    for t in strong[:3]:
        th = t["theme"]
        flags += (f'<div class="flag"><div class="ic">{th["emoji"]}</div><div><b>{escape(th["name"])}</b>'
                  f'<p>{escape(th["blurb"])}.</p></div></div>')
    if not flags:
        flags = '<div class="flag"><div class="ic">✨</div><div><b>Your own kind of match</b><p>A mix that’s uniquely yours.</p></div></div>'
    superp = narr(p, "summary") or (f"You’re strong where it’s hardest to build — "
              f"{', '.join(escape(t['theme']['name']) for t in strong[:3]) or 'the foundations'}.")
    S.append(("", f'<div class="eb">Your green flags</div><div class="h2">Why you two work</div>'
                  f'<div class="sub">The strengths worth celebrating \U0001F49A</div>{flags}'
                  f'<div class="super"><div class="l">YOUR SUPERPOWER</div><p>{superp}</p></div>'))

    # 4 playbook
    S += _playbook(p, by)
    # 5 will it last
    S.append(("will",
        f'<div class="eb">The honest answer</div><div class="h2">Will it last?</div>'
        f'<div class="bigyes">Yes — with intention.</div>'
        f'<p class="bd">You’ve got a strong hand: {pct}%, with your deepest foundations already solid. '
        f'Compatibility gets you to the start line; the playbook wins the race.</p>'
        f'<p class="norm">Most happy couples aren’t 100%. A strong base + a little effort = a genuinely lasting match.</p>'
        f'<div class="scard"><div class="n">{p1n} &amp; {p2n}</div><div class="a">{escape(arch["name"])} {arch.get("emoji","")}</div>'
        f'<div class="b">{pct}%</div><div class="st">{_stars(pct)}</div><div class="v">{_verdict_word(pct)}</div></div>'))

    # 6 two of you + 7 couple type
    S += _two_of_you(p, pr1, pr2)
    S.append(("", f'<div class="eb">Your couple type</div><div class="h2">The kind of pair you are ✨</div>'
                  f'<div class="coupleft"><div class="ce">{arch.get("emoji","✨")}</div>'
                  f'<h3>{escape(arch["name"])}</h3><div class="ct">{escape(arch.get("tagline",""))}</div>'
                  f'<p>{narr(p,"couple_type") or escape(arch.get("body",""))}</p></div>'))

    # 8..17 area deep-dives (2 pages each)
    S += _area_pages(themes, by, p)
    # synthesis
    S += _synthesis(p, themes, strong)
    # combined energy
    S += _combined(p, pr1, pr2)
    # checks
    S += _checks(p, by)
    # timing
    S += _timing()
    # toolkit
    S += _toolkit(p, by)
    # what score means
    S += _score_means(p, pct)
    # note
    S += _note(p, p1n, p2n)
    # keepsake
    S.append(("", f'<div class="eb">Yours to keep</div><div class="h2">Compatibility Certificate</div>'
                  f'<div class="cert"><div class="seal">✦</div><div class="lbl">AXTROSHASTRA</div>'
                  f'<div class="n">{p1n} &amp; {p2n}</div><div class="a">{escape(arch["name"])} {arch.get("emoji","")}</div>'
                  f'<div class="st">{_stars(pct)}</div><div class="b">{pct}% · {_verdict_word(pct)}</div>'
                  f'<div class="q">"According to Vedic astrology, this relationship holds warm and auspicious potential."</div></div>'))
    # referral
    S.append(("", f'<div class="eb">One last thing</div><div class="h2">Know a couple who’d love this?</div>'
                  f'<div class="sub">Every reading is calculated from real charts — no two alike</div>'
                  f'<div class="refbox"><div class="l2">Gift a friend their reading \U0001F49B</div>'
                  f'<p>If this felt true for you, it’ll mean the world to someone figuring out "is this the one?"</p>'
                  f'<a class="refbtn" href="/match">Start a reading →</a></div>'))
    # appendix
    S += _appendix(p, pr1, pr2, kootas)

    # assemble + auto-number
    pages = "".join(f'<section class="pg {cls}">{inner}<div class="pn">{i:02d}</div></section>'
                    for i, (cls, inner) in enumerate(S, 1))
    share = f"https://wa.me/?text=Our%20Kundli%20Milan%3A%20{pct}%25%20%E2%9C%A8"
    actbar = (f'<div class="actbar"><a href="#" onclick="window.print();return false;">&#11015; Download PDF</a> '
              f'<a class="wa" href="{share}" target="_blank" rel="noopener">Share on WhatsApp</a></div>')
    return (f'<!DOCTYPE html><html lang="en"><head>{AX_PRE}<title>{p1n} ✕ {p2n} — Love Compatibility</title>'
            f'<style>{CSS}</style></head><body><div class="book">{pages}</div>{actbar}</body></html>')


def _playbook(p, by):
    ranked = sorted((k for k in by.values() if k["max"]), key=lambda k: k["score"] / k["max"])
    t = next((k for k in ranked if k["name"] in REMEDIES and k["score"] / k["max"] < 0.6), None)
    if not t:
        return []
    ui = KOOTA_UI.get(t["name"], {"emoji": "\U0001F331", "label": t["name"]})
    rem = REMEDIES.get(t["name"], {}); ap = ACTION_PLAN.get(t["name"], {})
    intro = narr(p, "growth") or escape(rem.get("work_on", t.get("text", "")))
    acts = ""
    if ap.get("try"): acts += f'<div class="act"><div class="k">\U0001F3AF Try this week</div><div class="v">{escape(ap["try"])}</div></div>'
    if ap.get("talk"): acts += f'<div class="act"><div class="k">\U0001F4AC Say this</div><div class="v"><em>{escape(ap["talk"])}</em></div></div>'
    if ap.get("green"): acts += f'<div class="act"><div class="k">✅ Green flag you’ll notice</div><div class="v">{escape(ap["green"])}</div></div>'
    return [("", f'<div class="eb">Your playbook</div><div class="h2">One thing worth working on</div>'
                 f'<div class="sub">Small effort, big payoff</div>'
                 f'<div class="growbox"><div class="t">{ui["emoji"]} {escape(ui["label"])}</div><p>{intro}</p></div>{acts}')]


def _two_of_you(p, pr1, pr2):
    def card(pr):
        sun = pr.get("sun_western"); moon = escape(pr.get("sign", "")); nm = escape(pr.get("name", ""))
        glyph = SIGN_GLYPH.get(pr.get("sign"), "✦")
        srow = (f'<div class="br s">☀️ <b>{escape(sun)}</b> <span>· the sign the world knows you by</span></div>'
                if sun else "")
        return (f'<div class="prof"><div class="g">{glyph}︎</div><div class="nm">{nm}</div>'
                f'<div class="brg">{srow}<div class="br m">\U0001F319 <b>{moon} Moon</b> <span>· your love sign</span></div></div>'
                f'<div class="pmeta">{escape(pr.get("nak",""))} · {escape((pr.get("element") or "").title())} · ruled by {escape(pr.get("lord",""))}</div>'
                f'<div class="plove">"{escape(pr.get("love",""))}"</div></div>')
    el = p.get("element") or {}
    return [("", f'<div class="eb">Where it begins</div><div class="h2">The two of you</div>'
                 f'<div class="sub">You know your Sun sign. For love, we read your Moon.</div>'
                 f'{card(pr1)}<div class="between">{escape(el.get("p1",""))} meets {escape(el.get("p2",""))}</div>{card(pr2)}'
                 f'<div class="moonwhy"><p>The Sun is who you are to the world; the Moon is who you are in love — '
                 f'so Vedic matching reads the Moon, not the Sun.</p></div>')]


def _area_pages(themes, by, p):
    secs = []
    strongest = themes[0]["theme"]["name"] if themes else None
    weakest = themes[-1]["theme"]["name"] if themes else None
    for t in themes:
        th = t["theme"]; pct = int(round(t["pct"])); ks = [by[n] for n in th["kootas"] if n in by]
        strong = pct >= 55; _, col, _ = _chip(t["pct"])
        # reading page
        sd = narr(p, "deepdive_strength") if th["name"] == strongest else None
        if not sd and strong and THEME_DEEP.get(th["name"]):
            sd = escape(THEME_DEEP[th["name"]])
        lead = f'<p class="lead">{sd}</p>' if sd else ""
        reading = (f'<div class="eb">{"Your strength" if strong else "Worth a look"}</div>'
                   f'<div class="h2">{escape(th["name"])}</div>'
                   f'<div class="scorebig" style="color:{col}">{pct}<small>%</small></div>{lead}'
                   f'<p class="sub" style="margin-top:8px">{escape(th["blurb"]).capitalize()}.</p>'
                   + "".join(_mini_koota(k) for k in ks))
        secs.append(("", reading))
        # second page
        if strong:
            secs.append(("", f'<div class="eb">Keep the good thing good</div><div class="h2">How to protect it</div>'
                             f'<div class="sub">Even strengths need light care</div>'
                             f'<div class="scene"><div class="t">The only risk with an easy strength…</div>'
                             f'<p>is taking it for granted. When this comes naturally, couples stop being intentional. Keep choosing it.</p></div>'
                             f'<p class="payoff">You don’t need to fix this one — just don’t sleepwalk through how good it is.</p>'))
        else:
            wk = min(ks, key=lambda k: (k["score"] / k["max"]) if k["max"] else 1)
            rem = REMEDIES.get(wk["name"], {}); ap = ACTION_PLAN.get(wk["name"], {})
            gd = narr(p, "deepdive_growth") if th["name"] == weakest else None
            if not gd:
                gd = escape(wk.get("text", ""))
            growp = (f'<div class="scene"><div class="t">Why this is your growth edge</div><p>{gd}</p></div>'
                     if gd else "")
            acts = ""
            if ap.get("try"): acts += f'<div class="act"><div class="k">\U0001F3AF Try this week</div><div class="v">{escape(ap["try"])}</div></div>'
            if ap.get("talk"): acts += f'<div class="act"><div class="k">\U0001F4AC Say this</div><div class="v"><em>{escape(ap["talk"])}</em></div></div>'
            if rem.get("remedy"): acts += f'<div class="ritual">Optional ritual: {escape(rem["remedy"])}</div>'
            secs.append(("", f'<div class="eb">The play</div><div class="h2">You don’t need to match. Just translate.</div>'
                             f'<div class="sub">The same difference, turned into a strength</div>{growp}{acts}'))
    return secs


def _synthesis(p, themes, strong):
    st = ", ".join(escape(t["theme"]["name"]) for t in strong[:3]) or "your foundations"
    weak = escape(themes[-1]["theme"]["name"]) if themes else "one area"
    return [("", f'<div class="eb">The whole picture</div><div class="h2">Your relationship, in one breath</div>'
                 f'<div class="rule"></div>'
                 f'<p class="story">Two people <b>deeply built to last</b> — strong across {st} — '
                 f'with one honest growth edge: <b>{weak}</b>.</p>'
                 f'<p class="story" style="margin-top:14px">The rare part — the deep, hard-to-build compatibility — you already <b>have</b>. '
                 f'The workable part is exactly the kind couples <b>grow into</b>.</p>'
                 f'<p class="payoff" style="margin-top:20px">That’s not a fragile match. It’s a strong one, with a clear path.</p>')]


def _combined(p, pr1, pr2):
    el = p.get("element") or {}
    txt = narr(p, "combined_energy") or escape(el.get("text", ""))
    e1 = escape((pr1.get("element") or "").title()); e2 = escape((pr2.get("element") or "").title())
    return [("", f'<div class="eb">Your elements</div><div class="h2">Your combined energy</div>'
                 f'<div class="elems"><div class="elbox"><div class="e">\U0001F4A7</div><b>{escape(pr1.get("name",""))} · {e1}</b></div>'
                 f'<div class="elbox"><div class="e">\U0001F33F</div><b>{escape(pr2.get("name",""))} · {e2}</b></div></div>'
                 f'<p class="payoff" style="margin-top:16px">{txt}</p>')]


def _checks(p, by):
    mg = p.get("manglik") or {}
    mgy = bool(mg.get("p1") or mg.get("p2"))
    nadi = by.get("Nadi", {}); bhak = by.get("Bhakoot", {})
    cx = {c.get("koota") for c in (p.get("cancellations") or [])}
    nadi_ok = nadi.get("score", 0) > 0; bhak_ok = bhak.get("score", 0) > 0 or "Bhakoot" in cx
    def row(b, s, n, t):
        return f'<div class="chk"><div class="bd {b}">{s}</div><div><b>{n}</b><p>{escape(t)}</p></div></div>'
    ch = row("mild" if mgy else "ok", "!" if mgy else "✓", "Manglik (Mangal Dosha)", mg.get("note", ""))
    ch += row("ok" if nadi_ok else "mild", "✓" if nadi_ok else "!", "Nadi Dosha",
              "Your Nadis differ — no Nadi dosha, a strong positive sign." if nadi_ok
              else "Nadi is shared — often lifted when moon-signs differ; a pada-level check is advised.")
    ch += row("ok" if bhak_ok else "mild", "✓" if bhak_ok else "!", "Bhakoot Dosha",
              "Your Moon signs sit in a favourable position — long-term harmony supported." if bhak_ok
              else "A Bhakoot placement is present — check whether friendly moon-lords cancel it.")
    return [("", f'<div class="eb">The three big ones</div><div class="h2">The traditional checks</div>'
                 f'<div class="sub">Demystified — no fear, just facts</div>{ch}'
                 f'<p class="payoff" style="margin-top:16px">Read them as information to understand, not verdicts to fear.</p>')]


def _timing():
    rows = [("\U0001F48D", "For commitments", "Fridays and full-moon days are traditionally warm for love and vows."),
            ("\U0001F3E1", "For a new beginning", "Start something together on a rising-moon fortnight for a settled, growing start."),
            ("✈️", "For travel together", "Shared journeys deepen your bond — try to plan one each season.")]
    body = "".join(f'<div class="chk"><div class="bd ic">{e}</div><div><b>{t}</b><p>{d}</p></div></div>' for e, t, d in rows)
    return [("", f'<div class="eb">Good moments</div><div class="h2">Auspicious timing</div>'
                 f'<div class="sub">General guidance — not chart-specific dates</div>{body}')]


def _toolkit(p, by):
    weak = [k for k in by.values() if k["max"] and k["score"] / k["max"] < 0.6 and k["name"] in REMEDIES]
    acts = ""
    for k in weak[:4]:
        ui = KOOTA_UI.get(k["name"], {"emoji": "•", "label": k["name"]}); ap = ACTION_PLAN.get(k["name"], {})
        if ap.get("try"):
            acts += f'<div class="act"><div class="k">{ui["emoji"]} {escape(ui["label"])}</div><div class="v">{escape(ap["try"])}</div></div>'
    if not acts:
        acts = '<div class="act"><div class="k">💛 You’re in great shape</div><div class="v">No major work needed — just keep choosing each other.</div></div>'
    rits = ""
    for k in weak[:3]:
        rem = REMEDIES.get(k["name"], {})
        if rem.get("remedy"):
            rits += f'<div class="chk"><div class="bd ic">🪔</div><div><b>{escape(KOOTA_UI.get(k["name"],{}).get("label",k["name"]))}</b><p>{escape(rem["remedy"])}</p></div></div>'
    if not rits:
        rits = '<div class="chk"><div class="bd ic">🪔</div><div><b>A shared calm</b><p>Light a small lamp together at dusk — a grounding ritual for any couple.</p></div></div>'
    return [("", f'<div class="eb">What to actually do</div><div class="h2">Your toolkit — the actions</div>'
                 f'<div class="sub">The real levers, in one place</div>{acts}'
                 f'<p class="payoff" style="margin-top:14px">The first remedy is always action. Do one this week.</p>'),
            ("", f'<div class="eb">Optional · the traditional touch</div><div class="h2">If you like the rituals</div>'
                 f'<div class="sub">A cultural add-on — never a substitute for the actions</div>{rits}')]


def _score_means(p, pct):
    return [("", f'<div class="eb">Read this before you worry</div><div class="h2">What {pct}% really means</div>'
                 f'<div class="sub">A map, not a verdict</div>'
                 f'<div class="why a"><div class="t">It’s one input, not the whole story</div>'
                 f'<p>Guna milan measures your natural fit — not maturity, values or commitment, the real pillars of any marriage.</p></div>'
                 f'<div class="why a"><div class="t">The pattern matters more than the number</div>'
                 f'<p>You’re strong where it’s hardest to fix and grow where it’s easiest — the best-shaped score there is.</p></div>'
                 f'<div class="why a"><div class="t">Numbers don’t marry people</div>'
                 f'<p>Countless lasting marriages began below {pct}%. Use the number as information, not a verdict.</p></div>')]


def _note(p, p1n, p2n):
    default = (f"Dear {p1n} &amp; {p2n}, your charts tell the story of a bond with real staying power. "
               f"Where you differ isn’t a crack — it’s the one place a little patience turns difference into depth. "
               f"You already have the rare thing. Tend the rest gently, and you have the makings of a beautiful life together.")
    note = narr(p, "closing_note") or default
    return [("", f'<div class="eb">From us to you</div><div class="h2">A note to the couple</div><div class="rule"></div>'
                 f'<div class="letter"><p>{note}</p><div class="sign">— Your astrologer, Axtroshastra</div></div>')]


def _appendix(p, pr1, pr2, kootas):
    def crow(k):
        sc = int(k["score"]) if float(k["score"]).is_integer() else k["score"]
        return (f'<div class="crow"><div class="ct"><div class="cn">{escape(k["name"])} '
                f'<small>· {escape(k.get("meaning",""))}</small></div><div class="sc">{sc}/{k["max"]}</div></div>'
                f'<div class="val">{escape(k.get("detail",""))}</div></div>')
    g1 = SIGN_GLYPH.get(pr1.get("sign"), "✦"); g2 = SIGN_GLYPH.get(pr2.get("sign"), "✦")
    total = p.get("total"); eff = p.get("effective"); pct = p.get("match_pct")
    p1charts = (f'<div class="moons"><div class="moonchip"><div class="g">{g1}︎</div>'
                f'<div class="s">{escape(pr1.get("name",""))}<br>{escape(pr1.get("sign",""))} · {escape(pr1.get("nak",""))}</div></div>'
                f'<div class="moonchip"><div class="g">{g2}︎</div>'
                f'<div class="s">{escape(pr2.get("name",""))}<br>{escape(pr2.get("sign",""))} · {escape(pr2.get("nak",""))}</div></div></div>')
    secs = []
    # A charts
    secs.append(("", f'<div class="eb">Appendix · the receipts</div><div class="h2">The Calculations</div>'
                     f'<div class="sub">Every number, shown its working</div>'
                     f'<p class="lead">It starts with your two exact birth details — turned into the real position of the Moon.</p>'
                     f'{p1charts}<p class="payoff" style="margin-top:16px;font-size:12.5px">Kundli Milan is Moon-based — these two Moon positions drive every score.</p>'))
    # B scores 1-4
    secs.append(("", f'<div class="eb">Appendix · the 8 scores</div><div class="h2">How each score was made</div>'
                     f'<div class="sub">Factors 1–4 · every score is a rule, not an opinion</div>'
                     + "".join(crow(k) for k in kootas[:4])))
    # C scores 5-8 + total
    secs.append(("", f'<div class="eb">Appendix · the 8 scores</div><div class="h2">…and factors 5–8</div>'
                     f'<div class="sub">Then simply added up</div>'
                     + "".join(crow(k) for k in kootas[4:8])
                     + f'<div class="total">total {total}/36 → effective {eff}/36 → {pct}%</div>'))
    # D method + glossary (dark)
    gloss = [("Rashi", "your Moon’s zodiac sign (÷30° of the sky)"),
             ("Nakshatra", "the lunar mansion (÷13°20′), pinned to real stars"),
             ("Guna", "a compatibility point; 36 is the maximum"),
             ("Dosha", "a classical caution flag (Manglik, Nadi, Bhakoot)"),
             ("Ayanamsa", "the star-based correction (Lahiri) making it sidereal")]
    glossary = "".join(f'<div class="gloss" style="color:#D7D1E2;border-color:rgba(255,255,255,.08)">'
                       f'<b style="color:#fff">{n}</b> — {d}</div>' for n, d in gloss)
    secs.append(("dark", f'<div class="eb">Appendix · the method</div><div class="h2">Method &amp; glossary</div>'
                         f'<div class="sub" style="color:#B3A488">So you can check it yourself</div>'
                         f'<div style="background:rgba(255,255,255,.04);border:1px solid rgba(201,163,78,.2);border-radius:14px;padding:6px 16px;margin-bottom:12px">{glossary}</div>'
                         f'<div class="verify"><b>Verify it yourself</b><p>Put these birth details into any Lahiri-based panchang — '
                         f'the Moon positions will match, exactly. That’s the point: no opinion, only calculation.</p></div>'
                         f'<div class="tagline">Jyotish, calculated — no opinion, only calculation.</div>'))
    return secs
