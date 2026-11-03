"""Mulank paid report: the 15-card Version C report (323x623 pt when printed).

Port of the approved Stage C builder. Text comes from mulank_bank (approved wording rows plus the drafted
banks); whether a piece may be shown comes only from mulank_content.REGISTRY.

  mode="production"  Every registry key the report needs must be `verified` (named reviewer + date) AND have
                     drafted text. Anything else raises: there is no fallback line, no sample text and no
                     substitution of another pair's reading. This is the only mode the website uses.
  mode="sample"      Test PDFs only. Also shows `sample_ok` entries and prints fallback lines where content is
                     missing, and every page is labelled as a sample. Refused when live payment keys are set.
"""
import datetime
import html as _h
import os
import re

import mulank_bank as bank
import mulank_content as mc
import mulank_qc
import numerology
from numerology_preview import FONT_LINKS, clean_name
from numerology_preview_theme import THEME_CSS, THEME_DEFS

PLANETS = numerology.PLANETS
NODES = {"Rahu", "Ketu"}
ART = lambda p: ("the " + p) if p in ("Sun", "Moon") else p
esc = lambda t: _h.escape(str(t), quote=False)
norm = lambda t: re.sub(r"\s+", " ", str(t).replace("\xa0", " ")).strip()
COLOUR_HEX = {"Cream": "#F4EBD7", "White": "#FFFFFF", "Gold": "#C9A34E", "Yellow": "#E2A93B", "Green": "#7FA487",
              "Blue": "#7B95BF", "Red": "#C25B4A", "Orange": "#E39A5B", "Pink": "#E5A9B9", "Silver": "#C9CCD3"}


class ReportNotAvailable(Exception):
    """The pair is not sellable (some registry key is not verified or has no drafted text)."""
    def __init__(self, missing):
        super().__init__("report not available")
        self.missing = list(missing)


class ContentMissing(Exception):
    """Production render hit a gap that would have needed a fallback line."""


def _live_keys() -> bool:
    return (os.getenv("RAZORPAY_KEY_ID", "") or "").startswith("rzp_live_")


def _ok(reg, key, sample):
    e = reg.get(key)
    if mc.is_approved(e):
        return True
    return bool(sample and e is not None and e.status == mc.SAMPLE_OK)


EXTRA_CSS = """
.rp-foot{position:absolute;bottom:27px;left:0;right:0;text-align:center;font-family:var(--sans);font-size:9px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:#8A6420;z-index:3;pointer-events:none}
.rp-foot.sample{bottom:30px;font-size:8.5px;letter-spacing:.07em;color:#8F4020}
.rp-stamp{position:absolute;top:15px;left:50%;transform:translateX(-50%);z-index:3;white-space:nowrap;font:700 8.5px var(--sans);letter-spacing:.07em;text-transform:uppercase;color:#8F4020;border:1px solid rgba(143,64,32,.55);border-radius:6px;padding:2px 9px;background:rgba(250,245,237,.9);pointer-events:none}
.rp-note{position:absolute;top:10px;left:50%;transform:translateX(-50%);width:min(330px,90%);z-index:4;border:1px dashed rgba(180,87,43,.55);border-radius:10px;padding:6px 10px;font:10px/1.4 var(--sans);color:var(--muted);text-align:center;background:rgba(250,245,237,.96)}
.c7t td{padding:5px 9px}
"""


def build_report(day, month, year, name, *, today=None, registry=None, mode="production", foot_label=None, first=None) -> dict:
    """Render the report. Raises ReportNotAvailable / ContentMissing in production, numerology.NumerologyInputError
    for a bad date and ValueError for a bad name. Returns {html, pair_key, n_cards, trace, meta, mode}."""
    if mode not in ("production", "sample"):
        raise ValueError("mode")
    sample = mode == "sample"
    if sample and _live_keys():
        raise RuntimeError("sample reports are never rendered while live payment keys are configured")
    today = today or mc._today()
    reg = mc.REGISTRY if registry is None else registry
    name = clean_name(name)
    first = (first or name.split(" ")[0])
    E = numerology.compute_mulank(day, month, year, today=today)
    if not sample:
        ready = mc.pair_readiness(day, month, year, today=today, registry=reg)
        missing = list(ready["missing"]) + ["text:" + k for k in mc.required_keys(E) if mc.is_approved(reg.get(k)) and not bank.has_text(k)]
        if missing:
            raise ReportNotAvailable(missing)

    row = bank.row
    Mk, Bk = E["mulank"], E["bhagyank"]
    PYC, PYN = E["personal_year"]["current"], E["personal_year"]["next"]
    m, b = Mk["number"], Bk["number"]
    mp, bp = Mk["planet"], Bk["planet"]
    X, Y = ART(mp), ART(bp)
    pk = E["pair_key"]
    d0 = datetime.date.fromisoformat(E["meta"]["dob"])
    ref = datetime.date.fromisoformat(E["meta"]["reference_date"])
    dtxt = f"{d0.day} {d0.strftime('%B')} {d0.year}"
    rtxt = f"{ref.day} {ref.strftime('%B')} {ref.year}"
    trace = []
    meta = {}

    def rec(i, text):
        trace.append((i, norm(text)))

    if sample:
        label = foot_label or "Sample report &middot; illustrative, not production-verified"
        FOOT = f'<div class="rp-foot sample">{label}</div><div class="pgn"></div></section>'
    else:
        FOOT = '<div class="rp-foot">Axtroshastra &middot; Mulank numerology report</div><div class="pgn"></div></section>'
    stamp = (lambda t: f'<div class="rp-stamp">{t}</div>') if sample else (lambda t: "")
    sec = lambda inner, cls="": f'<section class="page{(" " + cls) if cls else ""}"><div class="col">\n  {inner}\n</div>'
    DISC = f'<p class="fine" style="text-align:center;margin-top:14px">{esc(row("D"))}</p>'
    pt = lambda icon, b_, span, cls="": (f'<div class="pt{cls}"><svg class="pi"><use href="#{icon}"/></svg><div class="tx">'
                                         + (f"<b>{esc(b_)}</b>" if b_ else "") + f"<span>{esc(span)}</span></div></div>")

    def slot(t, **kw):
        for k, v in kw.items():
            t = t.replace("{" + k + "}", str(v))
        return t

    def fallback(tag, text):
        if not sample:
            raise ContentMissing(tag)
        rec(tag, text)
        return text

    Mok, Bok = _ok(reg, f"M{m}", sample) and m in bank.M, _ok(reg, f"B{b}", sample) and b in bank.B
    auth = bank.PB.get(pk) if _ok(reg, f"PB:{pk}", sample) else None
    cmpd = bank.CMP.get(pk) if _ok(reg, f"CMP:{pk}", sample) else None
    lk = bank.LK.get(pk) if _ok(reg, f"LK:{pk}", sample) else None
    psent = bank.PS.get(pk) if _ok(reg, f"PS:{pk}", sample) else None
    cards = []

    # ---------------- card 1 cover ----------------
    cards.append(f'''<section class="page sand"><div class="col">
  <div class="cov-brand">Axtroshastra</div>
  <svg class="constel" viewBox="0 0 230 80" fill="none" style="width:min(210px,72%);margin:16px auto 4px;display:block" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="14,66 60,54 104,42 150,31 210,13" stroke="currentColor" stroke-width="1.1" stroke-dasharray="2 5" opacity=".5"/>
  <circle cx="14" cy="66" r="3" fill="currentColor"/><circle cx="60" cy="54" r="3" fill="currentColor"/><circle cx="104" cy="42" r="3" fill="currentColor"/>
  <g transform="translate(150 31)" stroke="currentColor" stroke-width="1.4"><path d="M0 -7V7M-7 0H7M-5 -5l10 10M5 -5l-10 10"/></g>
  <g transform="translate(210 13)"><path d="M0 -9V9M-9 0H9M-6 -6l12 12M6 -6l-12 12" stroke="currentColor" stroke-width="1.6"/><circle r="3.6" fill="var(--sand)" stroke="currentColor" stroke-width="1.5"/></g>
</svg>
  <div class="cov-title">Your<br>Numerology<br>Report</div>
  <div class="cov-sub">Your Mulank, Your Bhagyank<br>and the Years Ahead</div>
  <div class="cov-line"></div>
  <div class="cov-person"><div class="cov-name2" style="overflow-wrap:anywhere">{esc(name)}</div><div class="cov-born">{dtxt}</div></div>
  <div class="cov-type"><svg class="ti pi"><use href="#i-compass"/></svg><span>A reading of the two numbers at the heart of your date of birth, and of the years just ahead.</span></div>
  <div class="cov-div"></div>
  <div class="cov-sys">Report prepared {rtxt}<span class="pw">Powered by personalised numerological analysis</span></div>
  <div class="cov-trust">Indian numerology</div>
</div>{FOOT}''')
    rec("1a", "Indian numerology")

    # ---------------- card 2 note ----------------
    note_top = '<div class="rp-note">Numbers come from the tested engine; interpretive copy is illustrative, not production-verified.</div>' if sample else ""
    cards.append(f'''<section class="page note"><div class="col">

  <div class="noteframe">
    <svg class="fan nftop" viewBox="0 0 54 30" fill="none"><rect x="6" y="13" width="42" height="20" fill="#FBF7EE"/><g stroke="currentColor" stroke-width="1" stroke-linecap="round"><path d="M27 27 L12 15M27 27 L18 12M27 27 L27 9M27 27 L36 12M27 27 L42 15"/><path d="M12 15 A19 19 0 0 1 42 15"/></g></svg>
    <svg class="crn ctl" viewBox="0 0 13 13"><path d="M6.5 0 L13 6.5 L6.5 13 L0 6.5 Z" fill="currentColor"/></svg>
    <svg class="crn ctr" viewBox="0 0 13 13"><path d="M6.5 0 L13 6.5 L6.5 13 L0 6.5 Z" fill="currentColor"/></svg>
    <svg class="crn cbl" viewBox="0 0 13 13"><path d="M6.5 0 L13 6.5 L6.5 13 L0 6.5 Z" fill="currentColor"/></svg>
    <svg class="crn cbr" viewBox="0 0 13 13"><path d="M6.5 0 L13 6.5 L6.5 13 L0 6.5 Z" fill="currentColor"/></svg>
    <div class="notebox">
      <div class="ne">A note to you</div>
      <div class="nh">Two numbers, read with care</div>
      <p>{esc(row("2a"))}</p>
      <p>{esc(row("2c"))}</p>
      <p>This report reads them together, not apart, and then looks at your personal years: the one now running and the one ahead. Where a line fits, keep it. Where it does not, leave it.</p>
      <p>{esc(row("2b"))}</p>
      <div class="sig">&mdash; Your Axtroshastra analyst</div>
    </div>
    <svg class="fan nfbot" viewBox="0 0 54 30" fill="none"><rect x="6" y="13" width="42" height="20" fill="#FBF7EE"/><g stroke="currentColor" stroke-width="1" stroke-linecap="round"><path d="M27 27 L12 15M27 27 L18 12M27 27 L27 9M27 27 L36 12M27 27 L42 15"/><path d="M12 15 A19 19 0 0 1 42 15"/></g></svg>
  </div>
</div>{note_top}{FOOT}''')
    for i_ in ("2a", "2b", "2c"):
        rec(i_, row(i_))

    # ---------------- card 3 core numbers ----------------
    def reduce_lines(w):
        return [f"{' + '.join(str(a))} = {x}" for a, x in zip(w, w[1:])]
    if len(Mk["working"]) == 1:
        mulank_cell = f"Birth day {Mk['working'][0]} = <b>{m}</b>"
    else:
        ml = reduce_lines(Mk["working"])
        mulank_cell = f"Birth day {Mk['working'][0]}<br>" + "<br>".join(ml[:-1] + [ml[-1].rsplit("= ", 1)[0] + f"= <b>{m}</b>"])
    alld = f"{d0.day:02d}{d0.month:02d}{d0.year}"
    bl = reduce_lines(Bk["working"])
    head_b = f"{d0.day:02d} &middot; {d0.month:02d} &middot; {d0.year}<br>{'+'.join(alld)} = "
    if bl:
        bl[-1] = bl[-1].rsplit("= ", 1)[0] + f"= <b>{b}</b>"
        bh_cell = head_b + f"{Bk['working'][0]}<br>" + ", then ".join(bl)
    else:                                   # the digit sum is already a single digit
        bh_cell = head_b + f"<b>{b}</b>"

    def passes(w):
        return [x for x in w[1:-1] if x in (11, 22)]
    lead = None
    for ld, w in [("Your birth-day total", Mk["working"]), ("Your date-of-birth total", Bk["working"]),
                  (f"Your {PYC['year']} personal-year total", PYC["working"]), (f"Your {PYN['year']} personal-year total", PYN["working"])]:
        if passes(w):
            lead = f"{ld} passes through {passes(w)[0]} before reducing to {w[-1]}."
            break
    method = ("Mulank is the birth day reduced to a single digit. Bhagyank is every digit of the full date of birth added together, "
              "then reduced to a single digit. The numbers 11 and 22 are always taken down to a single digit here, and the working is shown each time.")
    ps = [f"<p>{method}</p>"]
    if lead:
        ps.append(f'<p style="margin-top:8px">{esc(lead)} {esc(row("3a"))}</p>')
        rec("3a", row("3a"))
    t3c = row("3c").replace("{m}", str(m)).replace("{b}", str(b))
    ps.append(f'<p style="margin-top:8px">{esc(row("3b"))}</p>')
    ps.append(f'<p style="margin-top:8px"><b>{esc(t3c)}</b></p>')
    rec("3b", row("3b"))
    rec("3c", t3c)
    cards.append(sec(f'''<div class="eyebrow">Core numbers</div>
  <h2 class="head">Your two numbers</h2><div class="rule"></div>
  <div class="sgrid">
    <div class="herocard" style="margin-top:0;padding:16px 10px"><div class="hd">Mulank</div><div class="hg" style="font-size:54px;line-height:1">{m}</div><p style="margin-top:6px">Ruled by {X}</p></div>
    <div class="herocard" style="margin-top:0;padding:16px 10px"><div class="hd">Bhagyank</div><div class="hg" style="font-size:54px;line-height:1">{b}</div><p style="margin-top:6px">Ruled by {Y}</p></div>
  </div>
  <table class="tw"><tr><th>Number</th><th>The working</th></tr>
    <tr><td>Mulank</td><td>{mulank_cell}</td></tr>
    <tr><td>Bhagyank</td><td>{bh_cell}</td></tr>
  </table>
  <div class="callout"><div class="ch">How these are worked out</div>{"".join(ps)}</div>''') + FOOT)

    # ---------------- card 4 pair ----------------
    items = []
    F_M, F_B = slot(row("8i"), m=m), slot(row("8j"), b=b)
    F_PS = "This report does not include a reading of how these two numbers work together for this combination."
    ic_m = "i-moon" if mp == "Moon" else "i-compass"
    if Mok:
        t = slot(row("4a"), m=m, X=X).replace("{M.themes}", bank.M[m]["themes"])
        items.append(pt(ic_m, f"Mulank {m}, {X}", t))
        rec("4a", t)
    else:
        items.append(pt(ic_m, None, fallback("F-M@4", F_M)))
    if Bok:
        t = slot(row("4b"), b=b, Y=Y).replace("{B.themes}", bank.B[b]["themes"])
        items.append(pt("i-target", f"Bhagyank {b}, {Y}", t))
        rec("4b", t)
    else:
        items.append(pt("i-target", None, fallback("F-B@4", F_B)))
    t4c = slot(row("4c"), m=m, b=b)
    rec("4c", t4c)
    if psent and psent.get("general"):
        t4d = psent["general"]
        rec("4d", t4d)
    else:
        t4d = fallback("F-PS", F_PS)
    items.append(pt("i-scales", "The two together", t4c + " " + t4d))
    relXY, relYX = bank.REL.get(f"{mp}>{bp}"), bank.REL.get(f"{bp}>{mp}")
    L = {"friend": "a friend", "neutral": "neutral", "adversary": "an adversary"}
    if m == b:
        box = slot(row("4h"), m=m, X=X)
        rec("4h", box)
    elif not mc.relation_keys(mp, bp):          # Rahu/Ketu pairs and the conflicted Venus/Mars pair: the approved statement 4i
        box = row("4i")
        rec("4i", box)
    elif not (relXY and relYX and _ok(reg, f"R:{mp}>{bp}", sample) and _ok(reg, f"R:{bp}>{mp}", sample)):
        box = fallback("4i", row("4i"))
    else:
        t = row("4e").split("Text: ", 1)[1]
        box = slot(t, X=X, Y=Y, labXY=L[relXY], labYX=L[relYX])
        rec("4e", box)
        if relXY != relYX:
            box += " " + row("4f")
            rec("4f", row("4f"))
        box += " " + row("4g")
        rec("4g", row("4g"))
    head4 = f'<h2 class="head">{esc(auth["heading"])}</h2>' if auth else ""
    cards.append(sec(f'''<div class="eyebrow">Core numbers &middot; The pair</div>
  {head4}<div class="rule"></div>
  <div class="pts">
    {"".join(items)}
  </div>
  <div class="callout"><div class="ch">Planetary links</div><p>{esc(box)}</p></div>
  {DISC}''') + FOOT)

    # ---------------- cards 5-7 pair bank ----------------
    if auth:
        pts5 = "".join(pt(i, b_, s) for i, b_, s in auth["pers"])
        cards.append(sec(f'''<div class="eyebrow">Your personality</div>
  <h2 class="head">How you come across</h2><div class="rule"></div>
  <div class="verdict sum"><svg class="pi ic"><use href="#i-moon"/></svg><span>{esc(auth["verdict"])}</span></div>
  <div class="pts">{pts5}</div>''', "roomy") + FOOT)
        rec("5a", auth["pers"][0][2])
        sp = "".join(f'<div class="sp"><div class="spt">{a}</div><div class="spl"><span>{l}</span><span>{r}</span></div><div class="spline"><span class="spd" style="left:{p}%"></span></div></div>'
                     for a, l, r, p in auth["dials"])
        t6a, t6c, lead6 = row("6a"), auth["dial_note"], "The dial to watch is pace."
        if not t6c.startswith(lead6):
            raise ContentMissing("6c")
        cards.append(sec(f'''<div class="exlabel">Your personality dials</div>
  <h2 class="action">{esc(auth["dial_head"])}</h2>
  <div class="subtit">{esc(t6a)}</div><div class="exrule"></div>
  <div class="spec">{sp}</div>
  <div class="leg" style="margin-top:14px">
    <div class="lr"><span class="dot" style="background:#C9A34E"></span><span class="lt"><b>{lead6}</b>{esc(t6c[len(lead6):])}</span></div>
  </div>
  <div class="take"><b>The read</b>{esc(auth["dial_read"])}</div>
  {DISC}''', "ex") + FOOT)
        rec("6a", t6a)
        rec("6c", t6c)
        rows = ""
        for sname, gname, bars in auth["table"]:
            if bars:
                s_ = f'<div class="bx" style="margin-top:3px"><div class="bt" style="height:6px"><i style="width:{bars[0]}%"></i></div></div>'
                g_ = f'<div class="bx" style="margin-top:3px"><div class="bt" style="height:6px"><i style="width:{bars[1]}%;background:linear-gradient(90deg,#E7B48F,var(--terra))"></i></div></div>'
            else:
                s_ = g_ = ""
            rows += f"<tr><td>{esc(sname)}{s_}</td><td>{esc(gname)}{g_}</td></tr>"
        t7a = slot(row("7a"), tip1=auth["tips"][0], tip2=auth["tips"][1], tip3=auth["tips"][2])
        t7c = slot(row("7c"), strong1=auth["strongs"][0], strong2=auth["strongs"][1], strong3=auth["strongs"][2],
                   advice1=auth["advice"][0], advice2=auth["advice"][1], advice3=auth["advice"][2])
        cards.append(sec(f'''<div class="eyebrow">Strengths &amp; Challenges</div>
  <h2 class="head">What carries you, and where to grow</h2><div class="rule"></div>
  <table class="tw c7t"><tr><th>Strength</th><th>Growth area</th></tr>{rows}</table>
  <p class="fine" style="margin-top:4px;text-align:center">{esc(row("7b"))}</p>
  <div class="callout"><div class="ch">A growth lens</div><p>{esc(t7a)}</p></div>
  <div class="take"><b>The read</b>{esc(t7c)}</div>
  {DISC}''') + FOOT)
        rec("7a", t7a)
        rec("7b", row("7b"))
        rec("7c", t7c)
    elif not sample:
        raise ContentMissing("PB")
    else:
        meta["omitted_cards_5_6_7"] = True

    # ---------------- card 8 career 1 ----------------
    it8 = []
    t8a = row("8a")
    rec("8a", t8a)
    if Mok:
        mm = bank.M[m]
        t8b_head = f"Working style, Mulank {m}, {X}."
        t8b = "In work terms" + slot(row("8b").split(". In work terms", 1)[1], m=m).replace("{M.style}", mm["style"])
        it8.append(pt("i-scales", t8b_head, t8b))
        rec("8b", t8b_head + " " + t8b)
    else:
        it8.append(pt("i-scales", None, fallback("8i", F_M)))
    parts, lead8c = [], "Strengths writers note at work."
    if Mok:
        t8c = slot(row("8c"), m=m).replace("{M.strengths}", bank.M[m]["strengths"])
        if not t8c.startswith(lead8c):
            raise ContentMissing("8c")
        parts.append(t8c[len(lead8c):].strip())
        rec("8c", t8c)
    if Bok:
        t8d = slot(row("8d"), b=b).replace("{B.strengths}", bank.B[b]["strengths"])
        parts.append(t8d)
        rec("8d", t8d)
    if parts:
        it8.append(pt("i-people", lead8c if Mok else None, " ".join(parts)))
    wants, clauses, lead8e = [], 0, "Bringing the two together."
    if Mok:
        t8e = slot(row("8e"), m=m).replace("{M.want}", bank.M[m]["want"])
        if not t8e.startswith(lead8e):
            raise ContentMissing("8e")
        wants.append(t8e[len(lead8e):].strip())
        rec("8e", t8e)
        clauses += 1
    if Bok:
        t8f = slot(row("8f"), b=b).replace("{B.want}", bank.B[b]["want"])
        wants.append(t8f)
        rec("8f", t8f)
        clauses += 1
    if not Bok:
        it8.append(pt("i-people", None, fallback("8j", F_B)))
    if clauses:
        g = row("8g")
        both = g.split("One clause shown:")[0].replace("Both clauses shown:", "").strip()
        one = g.split("One clause shown:")[1].strip()
        t8g = both if clauses == 2 else one
        wants.append(t8g)
        rec("8g", t8g)
        it8.append(pt("i-compass", lead8e if Mok else None, " ".join(wants)))
    if psent and psent.get("work"):
        rec("8h", psent["work"])
        it8.append(pt("i-scales", None, psent["work"]))
    cards.append(sec(f'''<div class="eyebrow">Career &amp; Relationships &middot; Work</div>
  <h2 class="head">How you tend to work</h2><div class="rule"></div>
  <p class="lead" style="font-size:14px;margin-top:12px">{esc(t8a)}</p>
  <div class="pts">{"".join(it8)}</div>''') + FOOT)

    # ---------------- card 9 career 2 ----------------
    it9, edge, lead9a = [], [], "A point to watch."
    if Mok:
        t9a = slot(row("9a"), m=m).replace("{M.edge}", bank.M[m]["edge"])
        if not t9a.startswith(lead9a):
            raise ContentMissing("9a")
        edge.append(t9a[len(lead9a):].strip())
        rec("9a", t9a)
    else:
        edge.append(fallback("F-M@9", F_M))
    if Bok:
        t9b = slot(row("9b"), b=b).replace("{B.edge}", bank.B[b]["edge"])
        edge.append(t9b)
        rec("9b", t9b)
    else:
        edge.append(fallback("F-B@9", F_B))
    if Mok or Bok:                         # 9c only follows at least one real edge line (QA-NOTES-v4 item 11)
        edge.append(row("9c"))
        rec("9c", row("9c"))
    it9.append(pt("i-alert", lead9a, " ".join(edge), " warn"))
    qs, lead9d = [], "Questions to reflect on."
    if Mok:
        t9d = slot(row("9d"), m=m).replace("{M.question}", bank.M[m]["question"])
        if not t9d.startswith(lead9d):
            raise ContentMissing("9d")
        qs.append(t9d[len(lead9d):].strip())
        rec("9d", t9d)
    if Bok:
        t9e = row("9e").replace("{B.question}", bank.B[b]["question"])
        qs.append(t9e)
        rec("9e", t9e)
    if qs:
        it9.append(pt("i-compass", lead9d if Mok else None, " ".join(qs)))
    if Mok:
        flds = bank.M[m]["fields"]
        flds = flds[0] if len(flds) == 1 else ", ".join(flds[:-1]) + " and " + flds[-1]
        t9f = slot(row("9f"), m=m).replace("{M.fields}", flds)
        lead9f = f"Fields linked with Mulank {m}."
        if not t9f.startswith(lead9f):
            raise ContentMissing("9f")
        it9.append(pt("i-book", lead9f, t9f[len(lead9f):].strip()))
        rec("9f", t9f)
    else:
        t9g = fallback("9g", slot(row("9g"), m=m))
        it9.append(pt("i-book", None, t9g))
    cards.append(sec(f'''<div class="eyebrow">Career &amp; Relationships &middot; Work</div>
  <div class="rule"></div>
  <div class="pts">{"".join(it9)}</div>''', "roomy") + FOOT)

    # ---------------- card 10 bonds ----------------
    if cmpd:
        bpts = "".join(pt(i, b_, s, c_) for i, b_, s, c_ in cmpd["bonds"])
        cp = cmpd["compat"]
        comp = ""
        if cp["mulank"] == m:
            trs = "".join(f"<tr><td>{esc(a)}</td><td>{esc(n)}</td></tr>" for a, n in cp["rows"])
            comp = (f'<table class="tw"><tr><th>For a Mulank {m}</th><th>Numbers</th></tr>{trs}</table>\n'
                    '  <p class="fine" style="text-align:center;margin-top:8px">Compatibility tables vary between traditional schools.</p>')
        st10 = stamp("PENDING EXPERT REVIEW &middot; compatibility lists") if not mc.is_approved(reg.get(f"CMP:{pk}")) else ""
        cards.append(sec(f'''<div class="eyebrow">Career &amp; Relationships &middot; Bonds</div>
  <h2 class="head">How you bond</h2><div class="rule"></div>
  <div class="pts">{bpts}</div>
  {comp}
  {DISC}''') + st10 + FOOT)
    else:
        t10a = fallback("10a-fallback", f"A compatibility list for Mulank {m} is not included in this edition.")
        cards.append(sec(f'''<div class="eyebrow">Career &amp; Relationships &middot; Bonds</div>
  <h2 class="head">How you bond</h2><div class="rule"></div>
  <div class="scard" style="margin-top:16px;width:100%"><p>{esc(t10a)}</p></div>
  {DISC}''') + stamp("PENDING EXPERT REVIEW &middot; compatibility lists") + FOOT)

    # ---------------- card 11 personal years ----------------
    def py_working(py):
        p, w = py["parts"], py["working"]
        ls = reduce_lines(w)
        if not ls:                          # the total is already a single digit
            return f"{p['day']} + {p['month']} + {p['year']} = {py['total']}"
        ls[-1] = ls[-1].rsplit("= ", 1)[0] + f"= {py['number']}"
        return f"{p['day']} + {p['month']} + {p['year']} = {py['total']}<br>" + ", then ".join(ls)
    tile = lambda lab, py: (f'<div class="herocard" style="margin-top:0;padding:16px 10px"><div class="hd">{py["year"]} &middot; {lab}</div>'
                            f'<div class="hg" style="font-size:54px;line-height:1">{py["number"]}</div><p style="margin-top:6px;font-size:12px">{py_working(py)}</p></div>')
    mt = []
    for nn in (PYC["number"], PYN["number"]):
        w = [nm for nm, v in (("Mulank", m), ("Bhagyank", b)) if v == nn]
        if w:
            mt.append(f"Your Personal Year {nn} matches your {' and '.join(w)}.")
    for s_ in mt:
        rec("11b", s_)
    yc, yn = bank.Y.get(PYC["number"]), bank.Y.get(PYN["number"])
    okc, okn = _ok(reg, f"Y{PYC['number']}", sample) and yc, _ok(reg, f"Y{PYN['number']}", sample) and yn
    ytab = ""
    if okc and okn and all(k in yc and k in yn for k in ("theme", "pace", "often")):
        ytab = f'''<table class="tw"><tr><th></th><th>{PYC["year"]}</th><th>{PYN["year"]}</th></tr>
    <tr><td>Theme</td><td>{esc(yc["theme"])}</td><td>{esc(yn["theme"])}</td></tr>
    <tr><td>Pace</td><td>{esc(yc["pace"])}</td><td>{esc(yn["pace"])}</td></tr>
    <tr><td>{esc(row("11a"))}</td><td>{esc(yc["often"])}</td><td>{esc(yn["often"])}</td></tr>
  </table>
  <p class="fine" style="margin-top:8px">{esc(row("11c"))}</p>'''
        rec("11a", row("11a"))
        rec("11c", row("11c"))
    elif not sample:
        raise ContentMissing("Y-table")
    pm = (f"Personal year = birth day ({d0.day} gives {' + '.join(str(d0.day))} = {PYC['parts']['day']}) + birth month ({PYC['parts']['month']}) "
          "+ the digits of the calendar year, reduced to a single digit.")
    days = (datetime.date(PYN["year"], 1, 1) - ref).days
    t11d = (f"This report counts personal years from 1 January to 31 December. As of {rtxt}, {days} days remain before your "
            f"Personal Year {PYN['number']} begins on 1 January {PYN['year']}.")
    rec("11d", t11d)
    cards.append(sec(f'''<div class="eyebrow">Personal years</div>
  <h2 class="head">Two years, side by side</h2><div class="rule"></div>
  <div class="sgrid">{tile("this year", PYC)}{tile("next year", PYN)}</div>
  {ytab}
  <div class="callout"><div class="ch">How this is worked out</div><p>{esc(pm)}{(" " + esc(" ".join(mt))) if mt else ""}</p></div>
  <div class="callout"><div class="ch">Timing</div><p>{esc(t11d)}</p></div>''') + FOOT)

    # ---------------- card 12 cycle ----------------
    on = {PYC["number"]: ("#B9862E", "#B9862E", "#FFFFFF"), PYN["number"]: ("#C9A34E", "#B9862E", "#FFFFFF")}
    circ = ""
    for n in range(1, 10):
        x = 30 + 40 * (n - 1)
        f_, s_, t_ = on.get(n, ("#FAF5ED", "#DCCFB2", "#4C4A57"))
        circ += (f'<circle cx="{x}" cy="62" r="15" fill="{f_}" stroke="{s_}" stroke-width="1.5"/><text x="{x}" y="67" text-anchor="middle" '
                 f'font-family="Fraunces,Georgia,serif" font-size="14" font-weight="600" fill="{t_}">{n}</text>')
    xc, xn = 30 + 40 * (PYC["number"] - 1), 30 + 40 * (PYN["number"] - 1)
    names = ["Begin", "Pair", "Express", "Build", "Change", "Care", "Reflect", "Reap", "Close"]
    lab = "".join(f'<text x="{30 + 40 * i}" y="100" text-anchor="middle">{nm}</text>' for i, nm in enumerate(names))
    svg = (f'<svg viewBox="0 0 380 130" width="100%" style="max-width:380px;margin-top:10px" role="img" aria-label="Nine-year personal cycle with two years marked">'
           f'<line x1="30" y1="62" x2="350" y2="62" stroke="#DCCFB2" stroke-width="1.5"/>{circ}'
           f'<g font-family="Inter,sans-serif" font-size="9.5" fill="#6B6380" font-weight="600">{lab}</g>'
           f'<g font-family="Inter,sans-serif" font-size="10" fill="#B9862E" font-weight="700" text-anchor="middle"><text x="{xc}" y="30">{PYC["year"]}</text><text x="{xn}" y="30">{PYN["year"]}</text></g>'
           f'<g font-family="Inter,sans-serif" font-size="9.5" fill="#B9862E" font-weight="600" text-anchor="middle"><text x="{xc}" y="44">now</text><text x="{xn}" y="44">next</text></g></svg>')
    kk = (10 - PYC["number"]) % 9 or 9
    y1 = PYC["year"] + kk
    if PYC["number"] == 1:
        t12b = f"Years 3 to 9: express, build, change, care, reflect, reap and close. Your next Personal Year 1 begins on 1 January {y1}."
        lb = "<b>Years 3 to 9:</b>" + esc(t12b[len("Years 3 to 9:"):])
    else:
        t12b = f"Your next Personal Year 1 begins on 1 January {y1}."
        lb = esc(t12b)
    rec("12b", t12b)
    cyc = auth and PYC["number"] == 1 and PYN["number"] == 2
    head12 = f'<h2 class="action">{esc(auth["cycle_head"])}</h2>' if cyc else ""
    read12 = f'<div class="take"><b>The read</b>{esc(auth["cycle_read"])}</div>' if cyc else ""
    cards.append(sec(f'''<div class="exlabel">Your personal-year cycle</div>
  {head12}
  <div class="subtit">The nine-year cycle, your two years marked</div><div class="exrule"></div>
  {svg}
  <div class="leg" style="margin-top:14px">
    <div class="lr"><span class="dot" style="background:#C9BFA6"></span><span class="lt">{lb}</span></div>
  </div>
  {read12}
  {DISC}''', "roomy ex") + FOOT)

    # ---------------- card 13 quick reference ----------------
    NA = "This reference is not included for your numbers in this edition."
    if lk:
        sw = "".join(f'<span style="width:18px;height:18px;border-radius:50%;background:{COLOUR_HEX[c]};border:1px solid #DCCFB2"></span>' for c in lk["colours"] if c in COLOUR_HEX)
        numcap = "Traditionally linked: " + ", ".join(f"{n} {PLANETS[n]}" for n in lk["numbers"])
        t13b = row("13b")
        tiles = (f'<div class="scard"><div class="sl">Numbers</div><div class="sv" style="font-size:22px">{" &middot; ".join(map(str, lk["numbers"]))}</div><p style="font-size:11.5px;margin-top:6px">{esc(numcap)}</p></div>'
                 f'<div class="scard"><div class="sl">Colours</div><div class="sv" style="font-size:16px">{" &middot; ".join(map(esc, lk["colours"]))}</div><div style="display:flex;gap:6px;margin-top:8px">{sw}</div></div>'
                 f'<div class="scard"><div class="sl">Days</div><div class="sv" style="font-size:18px">{" &middot; ".join(map(esc, lk["days"]))}</div><p style="font-size:11.5px;margin-top:6px">{mp}\'s day and {bp}\'s day</p></div>'
                 f'<div class="scard"><div class="sl">Gemstone</div><div class="sv" style="font-size:18px">{" &middot; ".join(map(esc, lk["gems"]))}</div><p style="font-size:11.5px;margin-top:6px">{esc(t13b)}</p></div>')
        rec("13b", t13b)
        howto = ('<div class="pts" style="margin-top:14px">\n    <div class="pt"><svg class="pi"><use href="#i-gem"/></svg><div class="tx"><b>How to use them lightly</b>'
                 '<span>Pick one favourite: a colour in what you wear on an important day, or a day you set aside for a fresh start.</span></div></div>\n  </div>')
    else:
        fallback("13a-fallback", NA)
        tiles = "".join(f'<div class="scard"><div class="sl">{n_}</div><p style="font-size:11.5px;margin-top:6px">{esc(NA)}</p></div>' for n_ in ("Numbers", "Colours", "Days", "Gemstone"))
        howto = ""
    t13c = row("13c")
    rec("13c", t13c)
    st13 = stamp("PENDING EXPERT REVIEW &middot; lucky-number selection") if not mc.is_approved(reg.get(f"LK:{pk}")) else ""
    cards.append(sec(f'''<div class="eyebrow">Practical guidance</div>
  <h2 class="head">Your quick reference</h2><div class="rule"></div>
  <div class="sgrid">{tiles}</div>
  <div class="callout"><div class="ch">A gentle note</div><p>{esc(t13c)}</p></div>
  {howto}''', "roomy") + st13 + FOOT)

    # ---------------- card 14 reflection prompts ----------------
    def blocks(py, role):
        y = bank.Y.get(py["number"]) or {}
        need = [("start", "Explore", "explore"), ("cont", "Continue", "continue_")] if role == "cur" else [("start", "Explore", "explore"), ("stop", "Reconsider", "reconsider")]
        if not (_ok(reg, f"Y{py['number']}", sample) and all(y.get(k) for _, _, k in need)):
            t = fallback("14g", slot(row("14g"), n=py["number"]))
            return f'<div class="blk cont" style="background:var(--box-fill)"><div class="bb">{esc(t)}</div></div>'
        out = ""
        for cls, lbl, k in need:
            out += f'<div class="blk {cls}"><div class="bh">{lbl}</div><div class="bb">{esc(y[k])}</div></div>'
            rec({"cur": {"explore": "14b", "continue_": "14c"}, "nxt": {"explore": "14d", "reconsider": "14e"}}[role][k], lbl.upper() + ". " + y[k])
        return out
    a1, a2 = row("14a").split("/ Prompts", 1)
    t14a1, t14a2 = a1.strip(), ("Prompts" + a2).replace("Years 1 and 2", f"Years {PYC['number']} and {PYN['number']}").strip()
    cards.append(sec(f'''<div class="exlabel">Practical guidance</div>
  <h2 class="action">{esc(t14a1)}</h2>
  <div class="subtit">{esc(t14a2)}</div><div class="exrule"></div>
  <div class="exlabel" style="width:100%;text-align:left;margin-top:12px">Rest of {PYC["year"]} &middot; Personal Year {PYC["number"]}</div>
  <div class="blocks" style="margin-top:8px">{blocks(PYC, "cur")}</div>
  <div class="exlabel" style="width:100%;text-align:left;margin-top:14px">{PYN["year"]} &middot; Personal Year {PYN["number"]}</div>
  <div class="blocks" style="margin-top:8px">{blocks(PYN, "nxt")}</div>
  {DISC}''', "ex") + FOOT)
    rec("14a", t14a1 + " " + t14a2)

    # ---------------- card 15 thank you ----------------
    planets_txt = ", ".join(f"{n} {PLANETS[n]}" for n in range(1, 10))
    t15d = row("15d")
    if planets_txt not in t15d:
        raise ContentMissing("15d")
    cards.append(f'''<section class="page end"><div class="col">
  <div class="eyebrow">With gratitude</div>
  <h2 class="head" style="overflow-wrap:anywhere">Thank you, {esc(first)}</h2><div class="rule"></div>
  <p class="lead">Thank you for trusting Axtroshastra with your numbers. We hope this reading gives you something useful to reflect on as the year turns.</p>
  <p class="lead">Curious about another part of your life? These are also on our site:</p>
  <div class="pts">
    <div class="pt"><svg class="pi"><use href="#i-people"/></svg><div class="tx"><b>Compatibility</b><span>How two people's details sit side by side.</span></div></div>
    <div class="pt"><svg class="pi"><use href="#i-clock"/></svg><div class="tx"><b>Marriage Timing</b><span>Timing themes around marriage.</span></div></div>
    <div class="pt"><svg class="pi"><use href="#i-trend"/></svg><div class="tx"><b>Career Growth</b><span>Themes for your next career steps.</span></div></div>
    <div class="pt"><svg class="pi"><use href="#i-book"/></svg><div class="tx"><b>Life Blueprint</b><span>A wider read across areas of life.</span></div></div>
  </div>
  <p class="lead" style="font-style:italic;text-align:center;color:var(--gold2-t);margin-top:18px">Your numbers are calculated from your date of birth by the method shown in this report; {esc(row("15a"))}</p>
  <p class="fine" style="text-align:center">{esc(row("15b"))}</p>
  <p class="fine" style="text-align:center;margin-top:8px">{esc(t15d)}</p>
  <div class="cov-trust">www.axtroshastra.com &middot; Indian numerology</div>
</div><svg class="endconst" viewBox="0 0 210 170" width="50" height="40.5" style="position:absolute;right:8px;bottom:30px;opacity:.5;z-index:0;pointer-events:none"><g stroke="#b9862e" fill="#b9862e" stroke-linecap="round" opacity="0.9"><circle cx="16" cy="150" r="2.3"/><circle cx="64" cy="110" r="2.3"/><circle cx="110" cy="132" r="2.3"/><circle cx="158" cy="80" r="2.3"/><circle cx="198" cy="30" r="2.3"/><path d="M16 150 L64 110 L110 132 L158 80 L198 30" fill="none" stroke-width="0.8" stroke-dasharray="3 5"/><path d="M158 71v18M149 80h18" stroke-width="1.3"/><path d="M198 21v18M189 30h18" stroke-width="1.3"/></g></svg>{FOOT}''')
    for i_ in ("15a", "15b", "15d"):
        rec(i_, row(i_))

    n_cards = len(cards)
    if not sample and n_cards != 15:
        raise ContentMissing("card count")
    title = ("Mulank Numerology Report SAMPLE (test document, not a customer report)" if sample else "Your Mulank Numerology Report")
    doc = ('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n'
           '<meta name="robots" content="noindex,nofollow">\n<meta name="referrer" content="no-referrer">\n'
           f"<title>{title}</title>\n{FONT_LINKS}<style>\n{THEME_CSS}{EXTRA_CSS}</style>\n</head>\n<body>\n{THEME_DEFS}\n" + "\n\n".join(cards) + "\n</body>\n</html>\n")
    if not sample:                          # last line of defence: an incomplete or sample-marked report is never delivered
        problems = mulank_qc.lint_report_html(doc, 15, vocabulary=False)
        if problems:
            raise ContentMissing(problems[0][1])
    meta.update(E=E, pair=pk, days=days, y1=y1)
    return {"html": doc, "pair_key": pk, "n_cards": n_cards, "trace": trace, "meta": meta, "mode": mode}
