"""Vastu Career Report: the paid 16-card report (one card per page, 430x830, printed to 323x623 pt).

Spec: docs/vastu-career-report-spec.md section 4. Visual design: the approved mock; the shared theme (_VYAPAR_CSS and
_VYAPAR_DEFS in report_view.py) is reused as is. TEXT comes only from owner-approved copy: for a segment that is not in
vastu_career.READY_SEGMENTS this module refuses to render (NotReady), so nothing unapproved can ever reach a buyer.

Approved so far: Student (docs/vastu-career-copy-student.md, decision log section H: approved with four cuts).
Every page is built from the buyer's OWN saved answers (payload meta and the free teaser computed by vastu_career.py);
no sample name, number or trait is ever baked in.
"""
import math
from datetime import datetime
from html import escape

import vastu_career as vc
from report_view import _VYAPAR_CSS, _VYAPAR_DEFS

TOTAL = 16
DIRN = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SW": 225, "W": 270, "NW": 315}
DIR_KEY = {v: k for k, v in vc.DIR_NAME.items()}


class NotReady(Exception):
    """The segment's copy is not approved yet."""


# nearest traditional first choice to turn toward, and how to turn (geometry, not a Vastu claim).
# Student first choices are E, N, NE. West (acceptable) and the change cells below are covered; a desk already facing a first choice needs none.
TURN = {
    "W": ("North", "a quarter turn to the right"),
    "S": ("East", "a quarter turn to the left"),
    "SE": ("East", "an eighth of a turn to the left"),
    "NW": ("North", "an eighth of a turn to the right"),
    "SW": ("East", "a long turn to the left"),
}

# numerology colours (research doc section 2: mostly one numerologist, low consensus) with display swatches
NUM_COLOURS = {
    1: ("gold, orange, yellow, or red and maroon", [("Gold", "#D4A93C"), ("Orange", "#E08A3C"), ("Yellow", "#F1D98B")]),
    2: ("white, cream, silver and light blue", [("White", "#F4F1EA"), ("Cream", "#F3E6C8"), ("Light blue", "#A9C8E0")]),
    3: ("yellow shades", [("Pale yellow", "#F6E3A1"), ("Sunflower", "#E8C547"), ("Mustard", "#C9A227")]),
    4: ("white, yellow and green", [("White", "#F4F1EA"), ("Soft yellow", "#F1D98B"), ("Leaf green", "#6F9F7A")]),
    5: ("green shades", [("Soft green", "#A8C9A2"), ("Leaf green", "#6F9F7A"), ("Deep green", "#3E7D5A")]),
    6: ("white and off-white", [("White", "#F4F1EA"), ("Off-white", "#EFE7D6"), ("Ivory", "#E8DCC0")]),
    7: ("white, yellow and red", [("White", "#F4F1EA"), ("Soft yellow", "#F1D98B"), ("Red", "#C0392B")]),
    8: ("white, yellow and green", [("White", "#F4F1EA"), ("Soft yellow", "#F1D98B"), ("Leaf green", "#6F9F7A")]),
    9: ("red, pink, maroon and orange", [("Red", "#C0392B"), ("Pink", "#E8A2B0"), ("Maroon", "#7A1F2B"), ("Orange", "#E08A3C")]),
}

# ---------------------------------------------------------------- approved copy, Student (decision log H applied)
STUDENT = {
    "label": "Student",
    "tagline": "Your study desk, read through traditional Vastu, with fixes you can do this week.",
    "comfort": "A tidy desk and a steady routine do most of the work. Vastu gives you a place to start.",
    "purpose": "study",
    "why_matters": "Sources most often name the east and the north for focus, and the north-east as the best of all for learning.",
    "cards": [
        ("Which way to face while studying", "Tradition favours <b>east</b>, <b>north</b> or <b>north-east</b>.", [
            ("i-compass", "East, the first choice", "Most guides name it for focus."),
            ("i-compass", "North and north-east", "Also favoured. Several sources call north-east the best of all for learning."),
            ("i-alert", "West and south", "West is a secondary option. South is usually avoided, so if the room forces a south-facing seat, the fixes on page 10 still help.", "warn")]),
        ("Where the desk sits in the room", "The seat matters as much as the direction.", [
            ("i-shield", "A solid wall behind you", "Avoid sitting with a door, window or open space at your back."),
            ("i-alert", "No beam overhead", "A heavy beam directly above the seat is traditionally avoided.", "warn"),
            ("i-check", "The door in view", "You can see the door without sitting in line with it. Keep space open in front of you.")]),
        ("Colours that suit a study corner", "Light, plain colours are the traditional choice for concentration.", [
            ("i-book", "Light green and light yellow", "Soft colours for a wall, a curtain or a desk mat."),
            ("i-book", "White and light blue", "Clean and plain."),
            ("i-alert", "Strong red and black", "Usually kept for small accents only.", "warn")]),
        ("On your desk: what to keep, what to drop", "A short list beats a long one.", [
            ("i-check", "Keep", "A lamp, your books for today and a clean writing surface.", "good"),
            ("i-alert", "Drop", "Studying on the bed, clutter, and a mirror facing the desk.", "warn"),
            ("i-clock", "Reset nightly", "Clear the desk before you sleep so tomorrow starts clean.")]),
        ("Light and fresh air", "Natural light and fresh air support long hours at a desk.", [
            ("i-moon", "Morning light from the east or north", "A window on those sides is traditionally preferred."),
            ("i-check", "A nearby window", "Open it for a few minutes each day."),
            ("i-clock", "A warm lamp for evenings", "Soft light that does not glare on the page.")]),
    ],
    "org": ("Books, notes and desk order", "Order is the easiest fix, and it works in any room.", [
        ("i-check", "One item, one place", "Pens, charger and notebook each get a spot. Return them after use."),
        ("i-book", "Books within reach", "Keep what you use daily on the desk and the rest on a shelf."),
        ("i-check", "A clear surface", "A lamp, today's books and a clean writing surface are enough.", "good")]),
    "small": ("Small room, hostel or shared desk", "Not every student has a room of their own. These still work.", [
        ("i-people", "Share the desk, claim a corner", "Face east or north when you sit down, even at a shared table."),
        ("i-shield", "A solid wall behind you", "Even at a shared table, choose the seat with a wall at your back."),
        ("i-book", "Use a folding board or a tray", "Set up a study spot you can open and clear in a minute.")]),
    "dont": "Study on the bed. Leave a mirror facing the desk. Leave clutter or broken items on the desk.",
}

CONTENT = {"student": STUDENT}          # a segment appears here only after the owner approves its copy


def _content(segment):
    if segment not in vc.READY_SEGMENTS or segment not in CONTENT:
        raise NotReady(segment)
    return CONTENT[segment]


# ---------------------------------------------------------------- html helpers
def _pt(icon, title, text, kind=""):
    return (f'<div class="pt {kind}"><svg class="ic pi"><use href="#{icon}"/></svg>'
            f'<div class="tx"><b>{title}</b>{text}</div></div>')


def _pts(rows):
    return "".join(_pt(*r) for r in rows)


def _card(n, eyebrow, head, lead, rows, extra=""):
    eb = f'<div class="eyebrow">{eyebrow}</div>' if eyebrow else ""
    ld = f'<div class="lead">{lead}</div>' if lead else ""
    return (f'<!-- {n:02d} -->\n<section class="page"><div class="col">{eb}<h2 class="head">{head}</h2><div class="rule"></div>'
            f'{ld}<div class="pts">{_pts(rows)}</div>{extra}</div><div class="pno">{n:02d}</div></section>')


_CONSTEL = '''<svg class="constel" viewBox="0 0 230 80" fill="none" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="14,66 60,54 104,42 150,31 210,13" stroke="#5A3C14" stroke-width="1.1" stroke-dasharray="2 5" opacity=".55"/>
    <circle cx="14" cy="66" r="3" fill="#B9862E"/><circle cx="60" cy="54" r="3" fill="#B9862E"/><circle cx="104" cy="42" r="3" fill="#B9862E"/>
    <g transform="translate(150 31)" stroke="#B9862E" stroke-width="1.4"><path d="M0 -7V7M-7 0H7M-5 -5l10 10M5 -5l-10 10"/></g>
    <g transform="translate(210 13)"><path d="M0 -9V9M-9 0H9M-6 -6l12 12M6 -6l-12 12" stroke="#B9862E" stroke-width="1.6"/><circle r="3.6" fill="#E4D5BE" stroke="#B9862E" stroke-width="1.5"/></g>
  </svg>'''


def _generated(meta):
    g = str(meta.get("generated") or "")
    try:
        d = datetime.strptime(g[:10], "%Y-%m-%d")
        return f"{d.day} {d.strftime('%B %Y')}"
    except ValueError:
        return ""


def _first_name(name):
    return (str(name or "").split() or ["there"])[0]


def _lc(s):
    return s[:1].lower() + s[1:]


def _compass(c):
    def wedge(d, op):
        a1, a2 = math.radians(DIRN[d] - 22.5), math.radians(DIRN[d] + 22.5)
        return (f'<path d="M0 0 L{108 * math.sin(a1):.1f} {-108 * math.cos(a1):.1f} A108 108 0 0 1 '
                f'{108 * math.sin(a2):.1f} {-108 * math.cos(a2):.1f} Z" fill="#C9A34E" opacity="{op}"/>')
    shade = "".join(wedge(d, .5) for d in c["ideal"]) + "".join(wedge(d, .22) for d in c["acceptable"])
    arrow = (f'<g transform="rotate({DIRN[c["desk"]]})" stroke="#B4572B" stroke-width="3" stroke-linecap="round">'
             '<path d="M0 0 L0 -80"/><path d="M0 -80 L-8 -68M0 -80 L8 -68"/></g>') if c.get("desk") else ""
    return ('<svg viewBox="-130 -130 260 260" style="width:100%;max-width:290px;margin:14px auto 0;display:block" role="img" '
            'aria-label="Compass with the favoured directions shaded and your desk direction marked">'
            f'<circle r="108" fill="#FBF4E7" stroke="#CBBDA1" stroke-width="1.5"/>{shade}'
            '<g stroke="#B9AE96" stroke-width="1"><path d="M0 -108V108M-108 0H108M-76.4 -76.4L76.4 76.4M76.4 -76.4L-76.4 76.4"/></g>'
            '<g font-family="Georgia,serif" font-size="14" fill="#2A2338" text-anchor="middle"><text y="-114">N</text><text x="122" y="5">E</text><text y="126">S</text><text x="-122" y="5">W</text></g>'
            '<g font-size="10" fill="#4A4459" text-anchor="middle"><text x="62" y="-84">NE</text><text x="62" y="92">SE</text><text x="-62" y="92">SW</text><text x="-62" y="-84">NW</text></g>'
            f'{arrow}<circle r="5" fill="#2A2338"/></svg>')


# ---------------------------------------------------------------- page 3 and page 10 (depend on the verdict and the flexibility)
def _verdict_points(C, t):
    v, dn = t["verdict"], t["desk_label"]
    if v == "ideal":
        first = (f"{escape(dn)} is named as acceptable for {C['purpose']}, and your birth number points the same way, so this report reads your desk as ideal."
                 if t["rule_b"] else f"{escape(dn)} is one of the traditional first choices for {C['purpose']}.")
        return [("i-compass", "Your result: Ideal", first), ("i-check", "Why it matters", C["why_matters"]),
                ("i-target", "What you can do", "Keep it as it is. Page 10 lists a few habits that keep it that way.")]
    if v == "acceptable":
        return [("i-compass", "Your result: Acceptable", f"{escape(dn)} is named as a secondary option for {C['purpose']}: not the first choice, easy to improve."),
                ("i-check", "Why it matters", C["why_matters"]),
                ("i-target", "What you can do", "Page 10 lists the steps that match whether you can move your desk.")]
    if v == "change":
        extra = " South is the direction most often avoided." if t["desk_direction"] == "S" else ""
        return [("i-compass", "Your result: Change advised", f"{escape(dn)} is not among the traditional first choices for {C['purpose']}.{extra}"),
                ("i-check", "Why it matters", C["why_matters"]),
                ("i-target", "What you can do", "Page 10 lists the steps that match whether you can move your desk.")]
    return [("i-compass", "Your result: Not sure yet", "We could not place your desk, so there is no result yet."),
            ("i-check", "Why it matters", "The way you face is what Vastu reads first."),
            ("i-target", "What you can do", "Stand at your desk, open a compass app and note where you face. Page 10 gives steps that work whichever way it turns out.")]


_RENTAL = ("i-check", "Rental-friendly", "Everything on this page works without any change to walls, doors or windows.", "good")


def _fix_page(t, flex):
    v, dk = t["verdict"], t["desk_direction"]
    if v == "ideal":
        return ("Keep it, and look after it", "Your desk reads <b>ideal</b>, so there is nothing to move. These habits keep it that way.", [
            ("i-check", "Keep the direction as it is", "The way you face already works for you.", "good"),
            ("i-clock", "Clear the desk each night", "Two minutes before you sleep."),
            ("i-target", "Keep the north or east side of the desk light", "A lamp or a book stand is enough."), _RENTAL])
    if v == "unknown":
        return ("Check first, then fix", "We could not place your desk, so these steps work whichever way you face.", [
            ("i-compass", "Check the direction first", "Stand where you sit, open a compass app and note the way you face. Then open your preview again to see your result."),
            ("i-check", "Whichever way you face", "Keep the desk clear, a lamp at the side and a solid wall behind you."), _RENTAL])
    target, turn = TURN[dk]
    if flex == "can_move":
        return ("What you can do, since you can move your desk", "You told us you <b>can move your desk</b>. Here are the fixes in order of effort.", [
            ("i-compass", f"Turn the desk to face {target.lower()}", f"From {escape(t['desk_label']).lower()} that is {turn}, toward one of the traditional first choices."),
            ("i-target", "Or set it up in a free corner", "A free corner on the east or north side of the room suits study hours."),
            ("i-shield", "Keep the wall behind you solid", "Avoid a door, window or open space at your back."), _RENTAL])
    if flex == "a_little":
        return ("What you can do, since you can turn a little", "You told us you can <b>turn it a little</b>. Here are the fixes in order of effort.", [
            ("i-compass", f"Turn the chair or the desk toward {target.lower()}", f"From {escape(t['desk_label']).lower()} that is {turn}. No heavy lifting."),
            ("i-target", "Or use another corner of the same room", "A corner on the east or north side suits study hours."), _RENTAL])
    return ("What you can do, since the desk stays", "You told us your desk <b>cannot move or is shared</b>. Every step here works where it is.", [
        ("i-shield", "Keep the wall behind you solid", "Choose the seat with a wall at your back, away from a door or window behind you."),
        ("i-check", "A clear desk and a lamp", "Keep a lamp, today's books and a clean writing surface. Clear the rest.", "good"),
        ("i-book", "Light colours", "A light desk mat or curtain in green, yellow, white or light blue."),
        ("i-alert", "No mirror, no bed", "Keep a mirror from facing the desk, and do not study on the bed.", "warn"), _RENTAL])


# ---------------------------------------------------------------- pages 14 and 15 (numerology, shared by every segment)
def _number_pages(t):
    n = t["number"]
    num, planet, ndir = n["mulank"], n["planet"], n["direction"]
    dn = t["desk_label"]
    lead = (f'This page comes from numerology, not from Vastu. Your birth day is <b>{escape(str(n["working"][0]))}</b>, '
            f'so your birth number (Mulank) is <b>{num}</b>, ruled by {escape(planet)}.')
    if ndir is None:
        rows = [("i-alert", "No single direction for this number",
                 f"Traditions place {escape(planet)} in different directions, so this report does not guess one for you."),
                ("i-check", "Your desk verdict stands", "The verdict on page 3 comes from Vastu and your desk direction alone."),
                ("i-book", "Use the next page", "Your number's colours are on the next page.")]
    else:
        if t["rule_b"]:
            meet = f"Vastu lists {escape(dn)} as acceptable for your desk. Your number points the same way, so this report reads your desk as ideal."
        elif ndir == "South" and t["desk_direction"] != "S":
            meet = ("South is your number's direction, but Vastu advises against facing south at a desk, so Vastu leads. "
                    "Use south for something you place, not for the way you face.")
        elif t["verdict"] == "unknown":
            meet = "Your desk direction is not known yet, so your number changes nothing on page 3. Where the two disagree, Vastu leads."
        else:
            meet = f"Your desk faces {escape(dn)}, so your number does not change the verdict on page 3. Where the two disagree, Vastu leads."
        rows = [("i-compass", f"{escape(ndir)} is linked to your number",
                 f"In this tradition {escape(planet)} is placed in the {escape(ndir.lower())}. {escape(n['tip'])}"),
                ("i-check", "How it meets your desk", meet),
                ("i-alert", "A guide, not a rule", "Numerology and Vastu are different traditions. Use this page as extra colour for your corner.", "warn")]
    p14 = _card(14, "From your birth number", "Your number's direction", lead, rows)
    phrase, swatches = NUM_COLOURS[num]
    sw = "".join(f'<div style="text-align:center"><div style="width:66px;height:66px;border-radius:50%;background:{c};border:1px solid #E9E1D0"></div>'
                 f'<div style="font-size:12px;margin-top:6px;color:var(--muted)">{escape(nm)}</div></div>' for nm, c in swatches)
    bold = num in (1, 9)
    tail = (_pt("i-alert", "Strong colours stay small", "Reds and oranges are bold. Keep them to a pen pot or a cushion, and the walls light.", "warn") if bold
            else _pt("i-book", "Keep the walls light", "Vastu advice for a study corner prefers light colours on the walls (page 6)."))
    p15 = (f'<!-- 15 -->\n<section class="page"><div class="col"><div class="eyebrow">From your birth number</div>'
           f'<h2 class="head">Your number\'s colour</h2><div class="rule"></div>'
           f'<div class="lead">Numerology links birth number {num} with <b>{escape(phrase)}</b>. Use them as accents, not as wall colours.</div>'
           f'<div style="display:flex;gap:12px;margin-top:20px;justify-content:center">{sw}</div>'
           f'<div class="pts">{_pt("i-check", "Where to use it", "A notebook cover, a desk mat, a plant pot or a cushion on your chair.", "good")}{tail}</div>'
           '</div><div class="pno">15</div></section>')
    return p14, p15


# ---------------------------------------------------------------- the report
_STICKY = """<style>
#ax-stickybar{position:fixed;left:0;right:0;bottom:0;z-index:9997;background:linear-gradient(180deg,rgba(250,245,237,0),var(--cream) 22%);padding:14px 16px calc(14px + env(safe-area-inset-bottom))}
#ax-stickybar .inner{max-width:430px;margin:0 auto;display:flex;gap:10px}
#ax-stickybar a{flex:1;display:flex;align-items:center;justify-content:center;gap:8px;min-height:52px;text-align:center;text-decoration:none;border-radius:12px;padding:12px 10px;font:700 15px/1.15 var(--sans);-webkit-tap-highlight-color:transparent}
#ax-stickybar svg{width:19px;height:19px;flex:none}
#ax-stickybar .pdf{background:var(--ink);color:#F5EEE0;box-shadow:0 6px 16px rgba(42,35,56,.28)}
#ax-stickybar .pdf svg{color:var(--gold2)}
@media print{#ax-stickybar{display:none!important}}</style>
<div id='ax-stickybar'><div class='inner'>
<a class='pdf' id='ax-pdf' href='#' onclick='window.print();return false;'><svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'><path d='M12 3v12'/><path d='M6 11l6 6 6-6'/><path d='M4 21h16'/></svg>Download PDF</a>
</div></div>"""


def render_vastu_career(payload: dict) -> str:
    meta = payload.get("meta") or {}
    t = payload.get("teaser") or {}
    seg = meta.get("segment")
    C = _content(seg)                                  # raises NotReady for an unapproved segment
    name = escape(str(meta.get("name") or ""))
    first = escape(_first_name(meta.get("name")))
    flex = meta.get("desk_flexibility")
    dn = escape(t["desk_label"])
    pages = []

    pages.append(f'''<!-- 01 COVER -->
<section class="page sand"><div class="col">
  <div class="cov-brand">AxtroShastra &middot; Vastu Career Report</div>
  {_CONSTEL}
  <div class="cov-name">{name}</div>
  <div class="cov-type"><svg class="ti" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3 14l4-4 3 3 6-7"/><path d="M13 4h4v4"/></svg><span>{escape(C["tagline"])}</span></div>
  <div class="cov-pills"><span class="cp"><span class="g">&#9650;</span> {escape(C["label"])}</span><span class="cp"><span class="g">&#10022;</span> Desk faces {dn}</span><span class="cp"><span class="g">&#9675;</span> {escape(t["flexibility_label"])}</span></div>
  <div class="cov-comfort">{escape(C["comfort"])}</div>
  <div class="cov-trust">Traditional Vastu guidance &middot; Generated {escape(_generated(meta))}</div>
</div><div class="pno">01</div></section>''')

    pages.append(f'''<!-- 02 NOTE -->
<section class="page note"><div class="col">
  <div class="noteframe">
    <div class="ne">A note for you</div>
    <div class="nh">Before you read on</div>
    <p>Dear {first}, this report looks at the place where you spend your hours: your desk. It follows Vastu Shastra, an old Indian tradition about how a space is arranged, and it keeps every step practical.</p>
    <p>Vastu is a belief system, not a forecast. Use what suits your space, skip what does not, and judge for yourself whether it helps you settle in and focus.</p>
    <div class="sig">&mdash; Your astrologer, AxtroShastra</div>
  </div>
</div><div class="pno">02</div></section>''')

    note3 = "This verdict comes from your desk direction. Your birth number adds a separate note on page 14."
    pages.append(_card(3, "Your desk check", "Your desk, read against Vastu", escape(t["why"]), _verdict_points(C, t),
                       f'<div class="callout" style="width:100%;text-align:left;margin-top:14px">{note3}</div>'))
    for i, (head, lead, rows) in enumerate(C["cards"]):
        pages.append(_card(4 + i, "", head, lead, rows))
    pages.append(_card(9, "Organise", C["org"][0], C["org"][1], C["org"][2]))
    fh, fl, fr = _fix_page(t, flex)
    pages.append(_card(10, "Your fixes", fh, fl, fr))
    pages.append(_card(11, "Small and shared spaces", C["small"][0], C["small"][1], C["small"][2]))

    target = TURN.get(t["desk_direction"], ("", ""))[0]
    turn_clause = (f" Turn the chair toward {target.lower()} if you can." if target and flex in ("can_move", "a_little")
                   and t["verdict"] in ("acceptable", "change") else "")
    door = ""
    if meta.get("door_direction") in vc.DIRECTIONS:
        door = ('<div class="reflect">If you know which way your main door faces, keep the entrance clean and well lit. '
                'Tradition counts it as the way a home takes in good things.</div>')
    pages.append(f'''<!-- 12 -->
<section class="page"><div class="col">
  <div class="eyebrow">Tonight</div><h2 class="head">Ten-minute fixes</h2><div class="rule"></div>
  <div class="lead">Do these before you sleep. No tools needed.</div>
  <div class="dwcard">
    <div class="dwrow do"><svg class="ic pi"><use href="#i-check"/></svg><div class="tx"><b>Do</b>Clear the desk.{turn_clause} Open a window for five minutes. Keep one lamp at the side.</div></div>
    <div class="dwrow watch"><svg class="ic pi"><use href="#i-alert"/></svg><div class="tx"><b>Don't</b>{escape(C["dont"])}</div></div>
  </div>
  {door}
</div><div class="pno">12</div></section>''')

    if t["compass"].get("desk"):
        cl = f'You face <b>{dn}</b> now. The shaded arcs mark the traditional first choices for {C["purpose"]} (lighter: acceptable).'
        cap = "Red arrow: the way you face now."
    else:
        cl = f'The shaded arcs mark the traditional first choices for {C["purpose"]} (lighter: acceptable).'
        cap = "Add your direction to see it here."
    pages.append(f'''<!-- 13 -->
<section class="page"><div class="col">
  <div class="eyebrow">Compass</div><h2 class="head">Your desk on the compass</h2><div class="rule"></div>
  <div class="lead">{cl}</div>
  {_compass(t["compass"])}
  <div class="klegend" style="margin-top:12px;font-size:12.5px;color:var(--muted)">{cap}</div>
</div><div class="pno">13</div></section>''')

    p14, p15 = _number_pages(t)
    pages += [p14, p15]

    pages.append(f'''<!-- 16 THANK YOU -->
<section class="page sand"><div class="col">
  <div class="cov-brand">AxtroShastra</div>
  {_CONSTEL}
  <div class="cov-name" style="font-size:clamp(30px,9vw,40px)">Thank you, {first}</div>
  <div class="cov-comfort">Start with one fix tonight. A tidy desk is a good beginning.</div>
  <div class="cov-trust" style="max-width:300px;line-height:1.5">This report shares traditional Vastu and numerology ideas for reflection. It is not a prediction and does not promise any result.</div>
</div><div class="pno">16</div></section>''')

    assert len(pages) == TOTAL, len(pages)
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{name} &mdash; Vastu Career Report | Axtroshastra</title><style>\n{_VYAPAR_CSS}\n</style></head><body>\n'
            f'{_VYAPAR_DEFS}\n<!--ax:no-report-disclaimer-->\n' + "\n\n".join(pages) + f"\n{_STICKY}\n</body></html>")
