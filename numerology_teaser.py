"""The free preview as shown inside the /en/numerology modal: the same structure as the Career Intelligence preview (dark cover, stats strip,
compact cream cards, a dashed 'your answers are ready' card that carries the unlock button), filled only with Numerology content that the
calculation engine and the approved preview already produce. Nothing here is invented: no reviews, ratings, report counts or deadlines.

The five approved preview pages (numerology_preview.py) are unchanged and still make the preview PDF; this is the on-screen presentation.
render() returns {css, html}; the landing page draws it inside a shadow root, so its styles cannot leak into the page or the other way round.
The unlock button is present only when the customer's complete report is approved and drafted (the server decides, as for the PDF)."""
import calendar

import mulank_content
import mulank_pricing
import numerology
import numerology_preview as P

esc = P.esc

CSS = """
:host{display:block;--cream:#FBF7EF;--line:#E7DCC6;--gold:#B9862E;--gold2:#C9A34E;--ink:#2A2015;--muted:#8A8251;--body:#4A3F2C;
  font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:var(--ink);line-height:1.5}
*{box-sizing:border-box;margin:0;padding:0}
.tz{width:min(430px,92vw);margin:0 auto}
.tz-cap{text-align:center;font:500 11.5px 'Inter',sans-serif;color:var(--muted);margin:2px 0 12px}
.tz-cover{background:#1F1E1C;color:#F5EEE0;border-radius:16px;padding:30px 22px 24px;text-align:center;position:relative;overflow:hidden;box-shadow:0 14px 38px rgba(48,34,14,.2)}
.tz-cover:before{content:"";position:absolute;right:-50px;top:-50px;width:170px;height:170px;border-radius:50%;background:radial-gradient(circle,rgba(201,163,78,.28),rgba(201,163,78,0) 70%)}
.tz-cover:after{content:"";position:absolute;left:-60px;bottom:-60px;width:170px;height:170px;border-radius:50%;background:radial-gradient(circle,rgba(201,163,78,.14),rgba(201,163,78,0) 70%)}
.tz-cover>*{position:relative;z-index:1}
.tz-brand{font:700 10.5px 'Inter',sans-serif;letter-spacing:.22em;color:var(--gold2)}
.tz-cover h2{font:500 25px/1.2 'Fraunces',Georgia,serif;color:#fff;margin:12px 0 12px}
.tz-name{font:600 16px 'Fraunces',Georgia,serif;color:#fff;overflow-wrap:anywhere}
.tz-born{font:400 12px 'Inter',sans-serif;color:#B9B2A2;margin-top:3px}
.tz-prep{font:400 11px 'Inter',sans-serif;color:#7d776a;margin-top:12px}
.tz-q{list-style:none;text-align:left;margin:14px auto 0;max-width:330px}
.tz-q li{font:500 13px/1.35 'Inter',sans-serif;color:#E7CE8F;padding:8px 0;border-bottom:1px solid rgba(231,206,143,.2)}
.tz-q li:last-child{border-bottom:0}
.tz-stats{display:grid;grid-template-columns:repeat(3,1fr);background:#1F1E1C;border-radius:12px;margin-top:8px;overflow:hidden}
.tz-stat{padding:12px 6px 11px;text-align:center;border-right:1px solid rgba(255,255,255,.14)}
.tz-stat:last-child{border-right:0}
.tz-stat b{display:block;font:600 18px 'Fraunces',Georgia,serif;color:#fff;line-height:1.2}
.tz-stat span{font:600 8.5px 'Inter',sans-serif;letter-spacing:.14em;text-transform:uppercase;color:#9a937f}
.tz-card{background:var(--cream);border:1px solid var(--line);border-radius:14px;padding:16px 18px 18px;margin-top:10px;box-shadow:0 2px 10px rgba(90,60,20,.06)}
.tz-label{font:700 9.5px 'Inter',sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--gold2);margin-bottom:12px}
.tz-tiles{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.tz-tile{background:linear-gradient(155deg,#FBF4E7,#F6E9CB);border:1px solid #EBDFC4;border-radius:12px;padding:10px 8px 9px;text-align:center}
.tz-tile .k{font:700 9px 'Inter',sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--gold)}
.tz-tile .n{font:600 40px/1.1 'Fraunces',Georgia,serif;color:var(--gold2);margin-top:2px}
.tz-tile .p{font:500 12px 'Inter',sans-serif;color:var(--body)}
.tz-tab{width:100%;border-collapse:collapse;margin-top:10px}
.tz-tab th{font:700 8.5px 'Inter',sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--gold);text-align:left;padding:0 0 6px}
.tz-tab td{font:500 12.5px/1.45 'Inter',sans-serif;color:var(--body);padding:8px 0;vertical-align:top;border-top:1px dashed #E3D7BA}
.tz-tab td:first-child{font-weight:700;color:var(--ink);width:34%}
.tz-note{background:#F7EEDA;border:1px solid #EBDFC4;border-radius:10px;padding:10px 12px;margin-top:10px;font:400 12px/1.5 'Inter',sans-serif;color:var(--body)}
.tz-note b{display:block;font:700 9px 'Inter',sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--gold);margin-bottom:3px}
.tz-pair{font:500 15px/1.5 'Fraunces',Georgia,serif;color:var(--ink);text-align:center;margin-bottom:10px}
.tz-trait{display:flex;gap:10px;padding:7px 0;border-top:1px dashed #E3D7BA;font:400 12.5px/1.45 'Inter',sans-serif;color:var(--body)}
.tz-trait .l{flex:0 0 30%;font:700 8.5px 'Inter',sans-serif;letter-spacing:.12em;text-transform:uppercase;color:var(--gold);padding-top:3px}
.tz-nine{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:10px}
.tz-nc{background:#F7F1E4;border:1px solid #EFE7D6;border-radius:9px;padding:6px 8px;display:flex;align-items:baseline;gap:7px;flex-wrap:wrap}
.tz-nc b{font:600 17px 'Fraunces',Georgia,serif;color:var(--ink)}.tz-nc span{font:400 11.5px 'Inter',sans-serif;color:var(--body)}
.tz-nc i{flex-basis:100%;font:700 8px 'Inter',sans-serif;font-style:normal;letter-spacing:.08em;text-transform:uppercase;color:var(--gold);min-height:10px}
.tz-nc.on{background:linear-gradient(155deg,#FBF4E7,#F6E9CB);border-color:var(--gold2)}
.tz-small{font:400 11px/1.45 'Inter',sans-serif;color:var(--muted);margin-top:8px}
.tz-lock{background:var(--cream);border:2px dashed #D9C9A3;border-radius:16px;padding:18px 16px 16px;margin-top:10px}
.tz-lock h3{font:600 17px 'Fraunces',Georgia,serif;color:var(--ink)}
.tz-lock .sub{font:400 11px 'Inter',sans-serif;color:var(--muted);margin:2px 0 8px}
.tz-ans{display:flex;gap:10px;padding:11px 0;border-bottom:1px solid #E7DCC6}
.tz-ans:last-of-type{border-bottom:0}
.tz-ic{flex:none;width:24px;height:24px;border-radius:7px;background:#F1E7D0;color:var(--gold);display:flex;align-items:center;justify-content:center}
.tz-ic svg{width:12px;height:12px}
.tz-ans b{display:block;font:600 13px/1.3 'Fraunces',Georgia,serif;color:var(--ink)}
.tz-ans span{font:400 11px/1.4 'Inter',sans-serif;color:var(--muted)}
.tz-chips{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}
.tz-chip{border:1.5px dashed #D9C9A3;border-radius:9px;background:#F4EAD4;padding:8px 6px;text-align:center;font:600 11px 'Inter',sans-serif;color:var(--body)}
.tz-cta{display:block;width:100%;margin:18px auto 0;background:#B4674A;color:#fff;border:0;border-radius:100px;padding:15px 18px;font:700 15px/1.25 'Inter',sans-serif;cursor:pointer;box-shadow:0 10px 24px rgba(0,0,0,.2);text-align:center}
.tz-cta:hover{background:#9A4E35}
.tz-was{text-align:center;font:500 12px 'Inter',sans-serif;color:var(--muted);margin-top:14px}.tz-was s{color:#9a8f76}
.tz-fine{text-align:center;font:400 11px 'Inter',sans-serif;color:var(--muted);margin-top:8px}
.tz-na{margin-top:16px;text-align:center;background:#F4EAD4;border-radius:10px;padding:11px 12px;font:500 12.5px/1.45 'Inter',sans-serif;color:var(--body)}
.tz-disc{text-align:center;font:400 10.5px/1.5 'Inter',sans-serif;color:var(--muted);margin-top:12px;padding-top:10px;border-top:1px dashed #E3D7BA}
.tz-secure{display:flex;justify-content:center;margin-top:10px}
.tz-secure span{border:1px solid #E0D3B4;border-radius:100px;padding:4px 12px;font:600 10.5px 'Inter',sans-serif;color:var(--body);background:#F8F1E0}
"""

LOCK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>')

QUESTIONS = ("What does your Mulank say about how you go about things?",
             "What does your Bhagyank say about the direction you are headed?",
             "How do your two numbers work together?",
             "What do this year and next year ask of you?",
             "Which numbers, colours and days are linked with you?")

ANSWERS = (("How might you come across to others?", "Personality, strengths and growth areas from your two numbers."),
           ("How do you work best?", "Career and working style, with ideas to think over."),
           ("How do you connect with people?", "Relationships and bonds: closeness, communication and a pattern to watch."),
           ("What do this year and next year ask of you?", "Your personal years, each with a reflection prompt."),
           ("Which numbers, colours and days are linked with you?", "Lucky references from numerology writing, shown for curiosity only."))

CHIPS = ("Strengths", "Working style", "Next two years", "Lucky references")


def _nine(E) -> str:
    mn, bn = E["mulank"]["number"], E["bhagyank"]["number"]
    out = ""
    for n in range(1, 10):
        tags = [t for t, v in (("Mulank", mn), ("Bhagyank", bn)) if n == v]
        out += f'<div class="tz-nc{" on" if tags else ""}"><b>{n}</b><span>{numerology.PLANETS[n]}</span><i>{" + ".join(tags)}</i></div>'
    return f'<div class="tz-nine">{out}</div>'


def render(E: dict, name: str, eligible: bool, today=None) -> dict:
    """{css, html} for the preview modal. E is numerology.compute_mulank(...); eligibility is decided by the caller from the content registry."""
    M, B = E["mulank"], E["bhagyank"]
    today = today or mulank_content._today()
    note11 = f"<br>{P.W_3A}" if P.passes_master(E) else ""
    same = f' {P.W_4H.format(m=M["number"], X=M["planet"])}' if M["number"] == B["number"] else ""
    prepared = f"{today.day} {calendar.month_name[today.month]} {today.year}"
    cover = (f'<div class="tz-cap">Your preview, worked out from your date of birth.</div>'
             f'<section class="tz-cover"><div class="tz-brand">AXTROSHASTRA</div><h2>Numerology Report</h2>'
             f'<div class="tz-name">{esc(name)}</div><div class="tz-born">Born {P.dob_text(E)}</div>'
             f'<div class="tz-prep">Preview prepared {prepared}</div>'
             f'<ul class="tz-q">{"".join(f"<li>{q}</li>" for q in QUESTIONS)}</ul></section>'
             f'<div class="tz-stats"><div class="tz-stat"><b>{M["number"]}</b><span>Mulank</span></div>'
             f'<div class="tz-stat"><b>{B["number"]}</b><span>Bhagyank</span></div>'
             '<div class="tz-stat"><b>15 pages</b><span>Complete report</span></div></div>')
    core = (f'<section class="tz-card"><div class="tz-label">Your core numbers</div>'
            f'<div class="tz-tiles"><div class="tz-tile"><div class="k">Mulank</div><div class="n">{M["number"]}</div><div class="p">Ruling planet: {M["planet"]}</div></div>'
            f'<div class="tz-tile"><div class="k">Bhagyank</div><div class="n">{B["number"]}</div><div class="p">Ruling planet: {B["planet"]}</div></div></div>'
            f'<table class="tz-tab"><tr><th>Number</th><th>The working</th></tr>'
            f'<tr><td>Mulank</td><td>{P.mulank_working_html(E)}</td></tr><tr><td>Bhagyank</td><td>{P.bhagyank_working_html(E)}</td></tr></table>'
            f'<div class="tz-note"><b>How to read these</b>{P.W_3B} Yours: Mulank {M["number"]} (how), Bhagyank {B["number"]} (direction).{note11}</div></section>')
    together = (f'<section class="tz-card"><div class="tz-label">Your numbers together</div>'
                f'<div class="tz-pair">Mulank {M["number"]} with Bhagyank {B["number"]}</div>'
                f'<div class="tz-trait"><div class="l">Mulank</div><div>How you go about things. Worked from your birth day. Ruled by {M["planet"]}.</div></div>'
                f'<div class="tz-trait"><div class="l">Bhagyank</div><div>Where you are headed. Worked from the whole date. Ruled by {B["planet"]}.</div></div>'
                f'<div class="tz-small" style="margin-top:10px;color:var(--body);font-size:12.5px">{P.W_4C.format(m=M["number"], b=B["number"])} Neither is ranked.{same}</div>'
                f'{_nine(E)}<div class="tz-small">Your two numbers are marked. {P.W_PLANETS}</div>'
                f'<div class="tz-note"><b>A prompt to carry with you</b>{P.Q_REFLECT}</div></section>')
    answers = "".join(f'<div class="tz-ans"><div class="tz-ic">{LOCK}</div><div><b>{a}</b><span>{d}</span></div></div>' for a, d in ANSWERS)
    if eligible:
        price, listp = mulank_pricing.MULANK_PRICE_PAISE, mulank_pricing.MULANK_LIST_PRICE_PAISE
        was = f'<div class="tz-was"><s>{P.inr(listp)}</s> {P.inr(price)}</div>' if mulank_pricing.show_list_price() else ""
        action = (f'{was}<button type="button" class="tz-cta" data-action="checkout">{P.CTA1.replace(chr(160), " ")}</button>'
                  '<div class="tz-fine">Personalised using your exact date of birth</div><div class="tz-secure"><span>Secure payment</span></div>')
        sub = "Locked. Unlock with your complete Numerology Report"
    else:
        action = '<div class="tz-na">The complete report is not available for your numbers yet. Your free preview stays on this page.</div>'
        sub = "Locked. Part of the complete Numerology Report"
    locked = (f'<section class="tz-lock"><h3>Your 5 answers are ready</h3><div class="sub">{sub}</div>{answers}'
              f'<div class="tz-chips">{"".join(f"<div class=tz-chip>{c}</div>" for c in CHIPS)}</div>{action}'
              '<div class="tz-disc">Numerology is a belief system, not a science. These readings follow contemporary numerology writing and are offered for reflection only.</div></section>')
    return {"css": CSS, "html": f'<div class="tz">{cover}{core}{together}{locked}</div>'}
