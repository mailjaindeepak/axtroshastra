"""Mulank free preview renderer: five Version C cards (323x623 pt when printed).

Pages 1-2 are personal (name, DOB, computed numbers). Pages 3-5 are STATIC: they come
from functions whose parameters are only display flags (never the result, name or date),
so locked content cannot leak. Locked values are never rendered at all; the blurred
strips are fixed synthetic pseudo-words. Eligibility is decided here, server side, from
the content registry: ineligible pairs get an availability message and no price or
purchase button, so nobody is sent into a checkout that would fail.

Public entry point: build_preview(). PDF bytes: render_pdf(html).
"""
import html as _html
import random
import re

import mulank_content
import mulank_pricing
import numerology
from numerology_preview_theme import THEME_CSS, THEME_DEFS

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]

# ---- approved wording (Stage B final) ----
W_3A = "Some numerology writers retain 11 and 22 as special numbers; this report reduces them to single digits, so other readings may differ."
W_3B = "Contemporary Indian numerology writing reads Mulank as how you go about things and Bhagyank as your direction. Neither is ranked here."
W_4C = "Read together, Mulank {m} sets how you go about things and Bhagyank {b} sets where you are headed."
W_4H = "Your Mulank and Bhagyank are both {m}, linked with {X}."
W_PLANETS = "Planet links follow the scheme used in Indian numerology; some writers assign 4 and 7 differently."
DISC_SHORT = "Numerology is a belief system, not a science. Readings follow contemporary writing, for reflection only."
DISC_LONG = "Numerology is a belief system, not a science. These readings follow contemporary numerology writing and are offered for reflection, not prediction."
Q_REFLECT = "Think of a goal you are working toward at the moment. How are you going about it, and how does that sit with where you hope to end up?"
CTA_HEAD = "Your Numbers Are Just the Beginning."
CTA_COPY = ("You've discovered your core numbers. Your complete report takes a deeper look at the personality patterns, "
            "career themes, relationships and personal-year interpretations associated with them.")
_PRICE_TXT = "\u20b9%d" % (mulank_pricing.MULANK_PRICE_PAISE // 100)
CTA1 = "Unlock My Full Numerology Report\u00a0\u2014\u00a0" + _PRICE_TXT   # purchase card after page 3 (non-breaking so the price never wraps alone)
CTA2 = CTA1                                                              # repeated on page 5
CTA_BAR = "Unlock My Full Report"                                        # the compact purchase bar
CTA_PREORDER_SHORT = "Pre-order My Report"
CTA_PREORDER = "Pre-order My Report for \u20b9299"

FONT_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600'
    '&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">\n')

FOOT = '<div class="pv-foot">Axtroshastra &middot; Free preview</div><div class="pgn"></div></section>'


def esc(s) -> str:
    return _html.escape(str(s), quote=True)


def fine(t=DISC_SHORT) -> str:
    return f'<p class="fine" style="text-align:center;margin-top:14px">{t}</p>'


def lock(px, extra="") -> str:
    return (f'<svg width="{px}" height="{px}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            f'stroke-linecap="round" style="color:var(--gold);flex:0 0 auto{extra}"><rect x="4.5" y="10.5" width="15" height="10" rx="2.2"/>'
            '<path d="M8 10.5V7a4 4 0 0 1 8 0v3.5"/></svg>')


ARIA = 'role="group" aria-label="Locked preview of this section"'


def inr(paise: int) -> str:
    rupees, rem = divmod(int(paise), 100)
    return f"₹{rupees:,}" + (f".{rem:02d}" if rem else "")


def clean_name(raw) -> str:
    name = re.sub(r"[\x00-\x1f\x7f]", " ", str(raw or ""))
    name = re.sub(r"\s+", " ", name).strip()
    if not name or len(name) > 80:
        raise ValueError("name must be 1 to 80 characters")
    return name


def _cta_attrs(cta_url):
    if cta_url is None:
        return None
    if not (cta_url.startswith("https://") or (cta_url.startswith("/") and not cta_url.startswith("//"))):
        raise ValueError("cta_url must be an https URL or a site-relative path")
    return esc(cta_url)


def cta_button(label: str, cta_url, extra_style="", action="checkout") -> str:
    """A real link when the site supplies the checkout URL; otherwise a button the page script wires up."""
    href = _cta_attrs(cta_url)
    st = f' style="{extra_style}"' if extra_style else ""
    if href:
        return f'<a class="pv-cta wide" data-action="{action}" href="{href}"{st}>{label}</a>'
    return f'<button type="button" class="pv-cta wide" data-action="{action}"{st}>{label}</button>'


# ------------------------------------------------------------------ working strings
def _steps(w):
    return [" + ".join(str(w[i])) + f" = {w[i + 1]}" for i in range(len(w) - 1)]


def mulank_working_html(E):
    w, day = E["mulank"]["working"], int(E["meta"]["dob"][8:10])
    if len(w) == 1:
        return f"Birth day {day}<br>Already a single digit: <b>{w[0]}</b>"
    st = _steps(w)
    st[-1] = st[-1].rsplit("=", 1)[0] + f"= <b>{w[-1]}</b>"
    return f"Birth day {day}<br>" + "<br>".join(st)


def bhagyank_working_html(E):
    w = E["bhagyank"]["working"]
    y, m, d = E["meta"]["dob"].split("-")
    out = f"{d} &middot; {m} &middot; {y}<br>" + "+".join(d + m + y) + f" = {w[0]}"
    if len(w) == 1:
        return out.replace(f"= {w[0]}", f"= <b>{w[0]}</b>")
    st = _steps(w)
    st[-1] = st[-1].rsplit("=", 1)[0] + f"= <b>{w[-1]}</b>"
    return out + "<br>" + ", then ".join(st)


def passes_master(E):
    return any(x in (11, 22) for k in ("mulank", "bhagyank") for x in E[k]["working"][:-1])


def dob_text(E):
    y, m, d = (int(x) for x in E["meta"]["dob"].split("-"))
    return f"{d} {MONTHS[m - 1]} {y}"


# ------------------------------------------------------------------ personal pages
def page1(E, name):
    M, B = E["mulank"], E["bhagyank"]
    note11 = f'<p style="margin-top:5px">{W_3A}</p>' if passes_master(E) else ""
    return f'''<section class="page"><div class="col">
  <div class="eyebrow">Free preview &middot; Your core numbers</div>
  <h2 class="head">Your core numbers</h2><div class="rule"></div>
  <div class="verdict gold" style="margin-top:10px;padding:9px 18px"><div class="vl">Prepared for</div><div class="vt" style="font-size:20px;font-weight:600;margin-top:2px;overflow-wrap:anywhere" data-slot="name">{esc(name)}</div><div style="font-size:13px;color:var(--muted);margin-top:2px">Born {dob_text(E)}</div></div>
  <div class="sgrid" style="margin-top:10px">
    <div class="herocard" style="margin-top:0;padding:10px 10px"><div class="hd">Mulank</div><div class="hg" style="font-size:44px;line-height:1;margin-top:4px">{M["number"]}</div><p style="margin-top:4px">Ruling planet: {M["planet"]}</p></div>
    <div class="herocard" style="margin-top:0;padding:10px 10px"><div class="hd">Bhagyank</div><div class="hg" style="font-size:44px;line-height:1;margin-top:4px">{B["number"]}</div><p style="margin-top:4px">Ruling planet: {B["planet"]}</p></div>
  </div>
  <table class="tw t6" style="margin-top:2px"><tr><th>Number</th><th>The working</th></tr>
    <tr><td>Mulank</td><td>{mulank_working_html(E)}</td></tr>
    <tr><td>Bhagyank</td><td>{bhagyank_working_html(E)}</td></tr>
  </table>
  <div class="callout c12" style="margin-top:8px;padding:9px 14px"><div class="ch">How to read these</div><p>{W_3B} Yours: Mulank {M["number"]} (how), Bhagyank {B["number"]} (direction).</p>{note11}</div>
  {fine()}
</div>{FOOT}'''


def nine_grid(E):
    cells = []
    mn, bn = E["mulank"]["number"], E["bhagyank"]["number"]
    for n in range(1, 10):
        tags = [t for t, v in (("Mulank", mn), ("Bhagyank", bn)) if n == v]
        tg = f'<i>{" + ".join(tags)}</i>' if tags else "<i>&nbsp;</i>"
        cells.append(f'<div class="nc{" on" if tags else ""}"><b>{n}</b><span>{numerology.PLANETS[n]}</span>{tg}</div>')
    return '<div class="ngrid">' + "".join(cells) + "</div>"


def page2(E):
    M, B = E["mulank"], E["bhagyank"]
    same = ""
    if M["number"] == B["number"]:
        same = f'<p style="font-size:13px;color:var(--muted);margin-top:8px;text-align:center">{W_4H.format(m=M["number"], X=M["planet"])}</p>'
    return f'''<section class="page"><div class="col">
  <div class="eyebrow">Free preview &middot; Your numbers together</div>
  <h2 class="head">Mulank {M["number"]} with Bhagyank {B["number"]}</h2><div class="rule"></div>
  <div class="sgrid" style="margin-top:14px">
    <div class="scard pair"><div class="sl">Mulank</div><div class="pn">{M["number"]}</div><div class="pp">{M["planet"]}</div><div class="pr">How you go about things</div><div class="ps">Worked from your birth day</div></div>
    <div class="scard pair"><div class="sl">Bhagyank</div><div class="pn">{B["number"]}</div><div class="pp">{B["planet"]}</div><div class="pr">Where you are headed</div><div class="ps">Worked from the whole date</div></div>
  </div>
  <p class="lede-c" style="margin-top:14px;font-size:15px;line-height:1.5;color:var(--ink)">{W_4C.format(m=M["number"], b=B["number"])} Neither is ranked.</p>{same}
  <div class="exlabel" style="width:100%;text-align:left;margin-top:16px">The nine numbers and their planets</div>
  {nine_grid(E)}
  <p style="width:100%;text-align:left;font-size:11px;line-height:1.45;color:var(--muted);margin-top:6px">Your two numbers are marked. {W_PLANETS}</p>
  <div class="take" style="margin-top:12px"><b>A prompt to carry with you</b>{Q_REFLECT}</div>
  {fine()}
</div>{FOOT}'''


# ------------------------------------------------------------------ static pages (no result-derived input)
_CONS, _VOW = "bdgjkpvxz", "aeiou"


def _syn(seed, n):
    rng = random.Random(seed * 7919 + 13)
    return " ".join("".join(rng.choice(_CONS) + rng.choice(_VOW) for _ in range(rng.choice((2, 3)))) + rng.choice(("", "", "x", "z"))
                    for _ in range(n))


def _veil(seed, n, size=11.5):
    return (f'<span aria-hidden="true" style="position:relative;display:block"><span class="blurval" style="display:block;filter:blur(3.2px);'
            f'-webkit-filter:blur(3.2px);font-size:{size}px;line-height:1.4">{_syn(seed, n)}</span>'
            '<i style="position:absolute;left:-3px;right:-3px;top:-2px;bottom:-2px;background:linear-gradient(180deg,rgba(247,241,228,.10),rgba(247,241,228,.42));pointer-events:none"></i></span>')


def render_locked_quickref():
    cards = [("Lucky Numbers", "Numbers linked with your two numbers in numerology writing."),
             ("Lucky Colours", "Colours linked with your two numbers."),
             ("Lucky Days", "Days of the week linked with your two numbers."),
             ("Gemstones", "Gemstones linked with your two numbers, shown for curiosity only.")]
    out = "".join(f'<div class="scard"><div class="sl">{lab}</div><div class="sv" style="margin-top:10px">{lock(22)}</div>'
                  f'<p style="font-size:12.5px;margin-top:8px">{d}</p></div>' for lab, d in cards)
    return f'<div class="sgrid">{out}</div>'


def render_page3():
    return f'''<section class="page roomy"><div class="col">
  <div class="eyebrow">Locked &middot; In your complete report</div>
  <h2 class="head">Your Quick Reference</h2><div class="rule"></div>
  <p class="lede-c" style="margin-top:8px;font-size:14.5px">Four references that come with your complete report.</p>
  {render_locked_quickref()}
  <div class="callout"><div class="ch">About these references</div><p>Each is an association drawn from numerology writing, shown for curiosity and reflection only.</p></div>
  {fine()}
</div>{FOOT}'''


def render_cta_visual():
    bars = lambda *ws: "".join(f'<u style="width:{w}%"></u>' for w in ws)
    return f'''<div class="stackvis" aria-hidden="true">
    <div class="mc mc3"></div><div class="mc mc2"></div>
    <div class="mc mc1"><div class="mcc"></div><div class="mcl">{bars(62, 44)}</div><div class="mcring"></div><div class="mcl m2">{bars(88, 74, 80, 52)}</div></div>
    <div class="mclock">{lock(16)}</div>
  </div>'''


def render_page4(cta_url=None):
    list_p, price = mulank_pricing.MULANK_LIST_PRICE_PAISE, mulank_pricing.MULANK_PRICE_PAISE
    save, was = "", ""
    if mulank_pricing.show_list_price():            # only after the owner confirms Rs 499 is a genuine regular price
        save = f'<div class="psave">You save {inr(list_p - price)}</div>'
        was = f'<s class="was"><span class="sr">Regular price </span>{inr(list_p)}</s>'
    return f'''<section class="page"><div class="col">
  <div class="eyebrow">Your complete report</div>
  <h2 class="head">{CTA_HEAD}</h2><div class="rule"></div>
  <p class="lede-c" style="margin-top:12px;font-size:15.5px;line-height:1.5">{CTA_COPY}</p>
  {render_cta_visual()}
  <div class="pricebox"><div class="pl">Complete numerology report</div>
    <div class="pp2">{was}<span class="now"><span class="sr">Now </span>{inr(price)}</span></div>{save}</div>
  {cta_button(CTA1, cta_url, "margin-top:12px")}
  {fine()}
</div>{FOOT}'''


def render_page4_preorder(promise, refund_href, cta_url=None):
    """Pre-order variant of page 4 (pair not yet sellable). The wording never says "unlock" or "download now":
    the report is delivered later, as the owner promised. `promise` and `refund_href` come from owner-set config only."""
    price, list_p = mulank_pricing.MULANK_PRICE_PAISE, mulank_pricing.MULANK_LIST_PRICE_PAISE
    save, was = "", ""
    if mulank_pricing.show_list_price():
        save = f'<div class="psave">You save {inr(list_p - price)}</div>'
        was = f'<s class="was"><span class="sr">Regular price </span>{inr(list_p)}</s>'
    return f'''<section class="page"><div class="col">
  <div class="eyebrow">Pre-order</div>
  <h2 class="head">Pre-order Your Complete Report</h2><div class="rule"></div>
  <p class="lede-c" style="margin-top:12px;font-size:15px;line-height:1.5">Your complete numerology report is not ready for your numbers yet. Pre-order it now and we will deliver it {esc(promise)}.</p>
  {render_cta_visual()}
  <div class="pricebox"><div class="pl">Pre-order price</div><div class="pp2">{was}<span class="now">{inr(price)}</span></div>{save}</div>
  <p style="width:100%;text-align:left;font-size:12.5px;line-height:1.5;color:var(--body);margin-top:10px"><b>This is a pre-order, not an instant download.</b> Your report will appear at your private link when it is ready. Refunds and cancellation: see our <a href="{esc(refund_href)}" style="color:var(--terra)">refund policy</a>.</p>
  {cta_button(CTA_PREORDER, cta_url, "margin-top:12px", "preorder")}
  {fine()}
</div>{FOOT}'''


def render_page4_unavailable(waitlist_consent_text=""):
    wl = ""
    if waitlist_consent_text:
        wl = f'''<div class="wlbox">
    <div class="wh">Hear from us when it is ready</div>
    <p>If you would like a message on the WhatsApp number you gave us when the complete report becomes available for your numbers, tick the box below.</p>
    <label class="consent"><input type="checkbox" name="waitlist_consent" value="1"><span class="ct">{esc(waitlist_consent_text)}</span></label>
    <button type="button" class="pv-sec" data-action="waitlist">Notify me when it is ready</button>
  </div>'''
    return f'''<section class="page"><div class="col">
  <div class="eyebrow">Availability</div>
  <h2 class="head" style="font-size:27px">Your complete report is not ready for your numbers yet.</h2><div class="rule"></div>
  <p class="lede-c" style="margin-top:12px;font-size:15.5px;line-height:1.5">We are still preparing the complete report for this combination of numbers, so it cannot be purchased today. The first three pages of this preview are unchanged, and no date is promised.</p>
  {wl}
  {fine()}
</div>{FOOT}'''


def render_unlock_minis():
    items = [
        ("i-people", "Personality, strengths and challenges", "How you may come across, with strengths and growth areas alongside each other.", 301, "bars"),
        ("i-compass", "Career and working style", "Working style, strengths at work and ideas to think over.", 311, "lines"),
        ("i-scales", "Relationships and bonds", "Themes in how you connect with others.", 321, "lines"),
        ("i-hourglass", "Personal years and reflection prompts", "The personal year for this year and for next year, each with its own prompt.", 331, "dots"),
    ]
    out = ""
    for ic, ti, de, seed, kind in items:
        shape = {"bars": '<div class="mbars"><u style="width:72%"></u><u style="width:48%"></u><u style="width:61%"></u></div>',
                 "dots": '<div class="mdots"><u></u><u></u><u class="hi"></u><u></u><u></u><u></u></div>'}.get(kind, "")
        out += (f'<div class="scard mini"><div class="mh"><svg class="pi" style="width:20px;height:20px;color:var(--gold);flex:0 0 auto"><use href="#{ic}"/></svg>'
                f'<b>{ti}</b>{lock(15)}</div><p class="md">{de}</p>'
                f'<div {ARIA} class="mv">{_veil(seed, 5, 11.5)}{shape}</div></div>')
    return out


def render_page5(buyable=True, cta_url=None, preorder=False):
    if preorder:
        head, button, disc = "What Your Report Will Include", cta_button(CTA_PREORDER_SHORT, cta_url, "margin-top:14px", "preorder"), DISC_LONG
    elif buyable:
        head, button, disc = "What You&#8217;ll Unlock", cta_button(CTA2, cta_url, "margin-top:14px"), DISC_LONG
    else:
        head, button, disc = "What the Report Covers", "", DISC_LONG
    return f'''<section class="page"><div class="col">
  <div class="eyebrow">Inside your complete report</div>
  <h2 class="head">{head}</h2><div class="rule"></div>
  <div class="minis">{render_unlock_minis()}</div>
  {button}
  {fine(disc)}
</div>{FOOT}'''


# ------------------------------------------------------------------ document
EXTRA_CSS = """
/* ---- Mulank preview components (tokens and theme untouched) ---- */
.pv-foot{position:absolute;bottom:30px;left:0;right:0;text-align:center;font-family:var(--sans);font-size:9.5px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:var(--gold-t,#8A6420);z-index:3;pointer-events:none}
.tw.t6 td{padding:6px 9px}.tw.t6 th{padding-bottom:5px}
.callout.c12 p{font-size:12px;line-height:1.45}
.scard.pair{text-align:center;padding:12px 10px}
.scard.pair .pn{font-family:var(--serif);font-size:44px;font-weight:600;color:var(--gold2);line-height:1.05;margin-top:2px}
.scard.pair .pp{font-size:12.5px;font-weight:700;color:var(--ink);margin-top:2px}
.scard.pair .pr{font-family:var(--serif);font-size:14px;color:var(--ink);margin-top:8px;line-height:1.25}
.scard.pair .ps{font-size:11px;color:var(--muted);margin-top:3px}
.ngrid{width:100%;margin-top:8px;display:grid;grid-template-columns:repeat(3,1fr);gap:7px}
.nc{background:var(--box-fill);border:1px solid var(--box-line);border-radius:10px;padding:6px 8px 5px;text-align:left;display:grid;grid-template-columns:auto 1fr;column-gap:8px;align-items:baseline}
.nc b{font-family:var(--serif);font-size:19px;font-weight:600;color:var(--ink);line-height:1.1}
.nc span{font-size:12.5px;color:var(--body)}
.nc i{grid-column:1/3;font-style:normal;font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;font-weight:700;color:var(--gold-t);min-height:12px}
.nc.on{background:linear-gradient(155deg,#FBF4E7,#F6E9CB);border-color:var(--gold)}
.stackvis{position:relative;width:100%;height:178px;margin-top:14px}
.stackvis .mc{position:absolute;left:50%;top:6px;width:122px;height:164px;margin-left:-61px;border-radius:9px;background:var(--cream);border:1px solid #E1D3B3;box-shadow:0 6px 16px rgba(48,34,14,.14)}
.stackvis .mc3{transform:translateX(-62px) rotate(-8deg);background:#F4EBD7}
.stackvis .mc2{transform:translateX(62px) rotate(8deg);background:#F4EBD7}
.stackvis .mc1{z-index:2;padding:14px 12px;display:flex;flex-direction:column;align-items:center;gap:9px;background:linear-gradient(160deg,#FBF4E7,#F3E6C8);border-color:var(--gold2)}
.stackvis .mcc{width:34px;height:2px;background:var(--gold);opacity:.7;border-radius:2px}
.mcl{width:100%;display:flex;flex-direction:column;align-items:center;gap:5px}.mcl.m2{align-items:flex-start;margin-top:4px}
.mcl u,.mbars u{display:block;height:5px;border-radius:3px;background:rgba(185,134,46,.38);text-decoration:none}
.stackvis .mcring{width:38px;height:38px;border-radius:50%;border:2px solid var(--gold2);box-shadow:0 0 0 4px rgba(201,163,78,.16)}
.stackvis .mclock{position:absolute;z-index:3;left:50%;top:150px;margin-left:-14px;width:28px;height:28px;border-radius:50%;background:var(--card);border:1px solid var(--gold2);display:flex;align-items:center;justify-content:center;box-shadow:0 3px 8px rgba(48,34,14,.18)}
.pricebox{width:100%;margin-top:14px;background:var(--box-fill);border:1px solid #EBDFC4;border-radius:14px;padding:12px 16px;text-align:center}
.pricebox .pl{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--gold-t);font-weight:700}
.pricebox .pp2{display:flex;align-items:baseline;justify-content:center;gap:14px;margin-top:2px}
.pricebox .was{font-family:var(--serif);font-size:22px;color:var(--muted);text-decoration:line-through;text-decoration-thickness:1.5px}
.pricebox .now{font-family:var(--serif);font-size:40px;font-weight:600;color:var(--ink);line-height:1.15;letter-spacing:.01em}
.pricebox .psave{font-size:12px;font-weight:700;color:var(--green);margin-top:2px}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.pv-cta.wide{width:100%;text-align:center;line-height:1.25;padding:14px 18px;text-decoration:none;cursor:pointer}
@media print{.pv-cta{display:inline-flex!important}}
.pv-sec{display:inline-flex;justify-content:center;width:100%;background:transparent;color:var(--ink);border:1.5px solid var(--gold);border-radius:100px;padding:12px 18px;font-size:14px;font-weight:700;font-family:var(--sans);margin-top:12px;cursor:pointer}
@media print{.pv-sec{display:inline-flex!important}}
.wlbox{width:100%;margin-top:16px;background:var(--box-fill);border:1px solid #EBDFC4;border-radius:14px;padding:14px 16px;text-align:left}
.wlbox .wh{font-family:var(--serif);font-size:17px;font-weight:600;color:var(--ink)}
.wlbox p{font-size:13px;color:var(--body);margin-top:6px;line-height:1.5}
.consent{display:flex;gap:10px;align-items:flex-start;margin-top:10px;padding:9px 10px;border:1px solid #EBDFC4;border-radius:10px;background:rgba(250,245,237,.96)}
.consent input{flex:0 0 auto;width:18px;height:18px;margin-top:1px;accent-color:var(--gold)}
.consent .ct{font-size:11.5px;line-height:1.45;color:var(--body)}
.minis{width:100%;margin-top:12px;display:flex;flex-direction:column;gap:9px}
.scard.mini{padding:11px 13px 12px}
.scard.mini .mh{display:flex;gap:10px;align-items:center}
.scard.mini .mh b{font-family:var(--serif);font-size:15px;color:var(--ink);font-weight:600;flex:1;line-height:1.2}
.scard.mini .md{font-size:12.5px;line-height:1.4;margin-top:4px;color:var(--muted)}
.scard.mini .mv{margin-top:8px;display:flex;gap:12px;align-items:center;padding:0 4px}
.scard.mini .mv > span{flex:1;min-width:0}
.mbars{flex:0 0 38%;display:flex;flex-direction:column;gap:5px}
.mdots{flex:0 0 34%;display:flex;gap:5px;align-items:center}
.mdots u{display:block;width:11px;height:11px;border-radius:50%;background:rgba(185,134,46,.3);text-decoration:none}.mdots u.hi{background:rgba(185,134,46,.65)}
"""


def _document(pages: list) -> str:
    return ('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            '<meta name="robots" content="noindex,nofollow">\n<meta name="referrer" content="no-referrer">\n'
            '<title>Your Mulank Numerology Free Preview</title>\n' + FONT_LINKS +
            "<style>\n" + THEME_CSS + EXTRA_CSS + "</style>\n</head>\n<body>\n" + THEME_DEFS + "\n" +
            "\n\n".join(pages) + "\n</body>\n</html>\n")


def build_preview(day, month, year, name, *, today=None, cta_url=None,
                  waitlist_consent_text="", registry=None, preorder=None, refund_href=None) -> dict:
    """Validate, compute, decide eligibility server side and render the five cards.

    Raises numerology.NumerologyInputError for a bad DOB and ValueError for a bad name
    or cta_url. Gender is deliberately not a parameter. cta_url is the site's real
    checkout route (supplied by the caller); it is never built or guessed here.
    Returns {"html", "eligible", "pair_key", "content_version", "pages"}."""
    nm = clean_name(name)
    today = today or mulank_content._today()
    E = numerology.compute_mulank(day, month, year, today=today)
    ready = mulank_content.pair_readiness(day, month, year, today=today, registry=registry)
    if ready["eligible"]:
        p4, p5 = render_page4(cta_url), render_page5(True, cta_url)
    elif preorder and preorder.get("enabled"):
        p4 = render_page4_preorder(preorder["promise"], refund_href or preorder["refund_url"], cta_url)
        p5 = render_page5(True, cta_url, preorder=True)
    else:
        p4, p5 = render_page4_unavailable((waitlist_consent_text or "").strip()), render_page5(False)
    pages = [page1(E, nm), page2(E), render_page3(), p4, p5]
    return {"html": _document(pages), "eligible": ready["eligible"], "pair_key": E["pair_key"],
            "preorder": bool(not ready["eligible"] and preorder and preorder.get("enabled")),
            "content_version": ready["content_version"], "pages": len(pages)}


def render_pdf(html: str):
    """PDF bytes through the shared headless-Chrome helper, or None if Chrome is unavailable."""
    import pdfgen
    return pdfgen.generate(html)
