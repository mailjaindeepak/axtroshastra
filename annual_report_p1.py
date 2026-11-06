"""Annual Report, PART 1 (short version), base pages 1 to 12. pages(p) -> 12 HTML cards. Pure: everything comes from p.
Page numbers are BASE 54-card numbers; the assembler remaps them to the final numbering."""
import html as _h
import re
from annual_assets import (card, part_label, chip, tile, tiles, mini_strip, strip_big, counts, callout, tl_bar, steps,
                           mname, mshort, mrange, scope)

E = _h.escape
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
RANK = {'strong': 0, 'mixed': 1, 'careful': 2}
BLUE = '#2B5C9E'
# Part 3 pages (spec table): chart 44, planets 45, 12 parts 46, timing 47, patterns 48, words 49 A-H / 50 I-R / 51 S-Z
TOPICS = [('Career and work', 'career', 18), ('Money and savings', 'money', 20), ('Marriage and relationships', 'marriage', 23),
          ('Luck and big decisions', None, 25), ('Strengths, study and growth', None, 27)]


RANKS = {'strong': 0, 'mixed': 1, 'careful': 2}


def tone_of(vals):
    """The tone most months have; on a tie the more careful tone."""
    vals = list(vals)
    if not vals:
        return 'mixed'
    return max(RANKS, key=lambda k: (vals.count(k), RANKS[k]))


def tie_note(vals):
    vals = list(vals)
    c = {k: vals.count(k) for k in RANKS}
    top = max(c.values()) if vals else 0
    tied = [k for k in RANKS if c[k] == top]
    if len(tied) == 3:
        return 'three-way tie, the more careful tone is shown'
    return ('tie: ' + ', '.join(f'{c[k]} {k}' for k in tied)) if len(tied) > 1 else ''


def act_chip_text(n):
    return f'{n} STRONG {"MONTH" if n == 1 else "MONTHS"} TO ACT'


def _plan():
    """Act-month rule lives in annual_report_p2 (single source); imported lazily."""
    import annual_report_p2 as P
    return P


# ---------- helpers ----------
def _d(iso):
    if not iso:
        return ''
    y, m, d = iso[:10].split('-')
    return f'{int(d)} {MON[int(m) - 1]} {y}'


def pk(lst, i):
    return lst[i % len(lst)]


def lk(n, text=None):
    return f'<a class="xr" href="#p{n}" style="color:{BLUE}">{text or "see p." + str(n)}</a>'


def term(t, n):
    return f'<a class="xr" href="#p{n}" style="color:{BLUE}">{t}</a>'


def sm(p):
    return [m['ym'] for m in p['span_months']]


def ov(p):
    return {ym: p['tones'][ym] for ym in sm(p)}


def tone_map(p, key):
    if key == 'career' and p.get('work_type') == 'business' and p['areas'].get('business'):
        key = 'business'
    src = (p['areas'] or {}).get(key) if key else None
    if not src:
        return ov(p)
    return {ym: src.get(ym, p['tones'][ym]) for ym in sm(p)}


def cnt(t):
    v = list(t.values())
    return {k: v.count(k) for k in RANK}


def tag(t):
    return tone_of(t.values())


def ctext(t):
    c = cnt(t)
    return f'{c["strong"]} strong, {c["mixed"]} mixed, {c["careful"]} careful months'


def months_of(t, tone):
    return [ym for ym in t if t[ym] == tone]


def longest_run(t, tone):
    best, cur = [], []
    for ym in t:
        if t[ym] == tone:
            cur.append(ym)
            if len(cur) > len(best):
                best = list(cur)
        else:
            cur = []
    return best


def stage_word(p):
    s = str(p['sade_sati'].get('stage') or '').lower()
    for k, w in (('first', 'first'), ('1', 'first'), ('second', 'second'), ('2', 'second'), ('third', 'third'), ('3', 'third')):
        if k in s:
            return w
    return ''


def has_dhaiya(p):
    d = p['dhaiya']
    return bool(d.get('active') or (d.get('restarts') and d['restarts'][:7] in sm(p)))


def manglik_on(p):
    return str(p['manglik'].get('status') or '').startswith('manglik')


def span_text(p):
    return f"{p['span_months'][0]['label']} to {p['span_months'][-1]['label']}"


def changes_in_span(p):
    return sorted([c for c in p['sign_changes'] if c['date'][:7] in sm(p)], key=lambda c: c['date'])


def first_topic(p):
    for i, (n, _, _) in enumerate(TOPICS):
        if n == p.get('first_open_topic'):
            return i
    return 0


def eases_from(p, ym):
    o, s = ov(p), sm(p)
    for m in s[s.index(ym) + 1:]:
        if o[m] != 'careful':
            return f'from {mname(m)}'
    return f'after {mname(s[-1])}'


def para(txt, size=12.5, top=10, color='var(--body)'):
    return f'<p style="width:100%;text-align:left;font-size:{size}px;line-height:1.5;color:{color};margin-top:{top}px">{txt}</p>'


def subhead(txt, top=14):
    return (f'<div style="width:100%;text-align:left;margin-top:{top}px;font:700 10px/1 var(--sans);letter-spacing:.14em;'
            f'text-transform:uppercase;color:var(--gold)">{txt}</div>')


def pg(body, n, title):
    return card(body, n, part_label(1, 'Short version'), title)


# ---------- page 1 and 2 ----------
def _fit(name, full, floor=10):
    """Style for a name that must never clip: normal names (longest word <= 14 letters) get no style at all; longer
    words shrink with length (never below floor px) and may wrap anywhere."""
    w = max((len(x) for x in str(name).split()), default=0)
    if w <= 14:
        return ''
    return f' style="font-size:{max(floor, min(full, round(full * 14 / w, 1))):g}px;overflow-wrap:anywhere;word-break:break-word"'


def _cover(p):
    b = p['birth']
    when = _d(b.get('date'))
    when += f", {E(b['time_text'])}" if b.get('time_known') and b.get('time_text') else ', birth time not sure'
    if b.get('place'):
        when += f", {E(b['place'])}"
    body = ('<div style="text-align:center;padding-top:96px"><div class="cov-brand">AXTROSHASTRA</div>'
            '<div class="cov-title">Annual Report</div>'
            f'<div class="cov-sub">Your next 12 months<br>{E(span_text(p))}</div>'
            '<div class="cov-line" style="margin:26px auto"></div>'
            f'<div class="cov-person"><div class="cov-name2"{_fit(p["name"], 20)}>{E(p["name"])}</div><div class="cov-born">{when}</div></div>'
            '<div class="cov-div"></div>'
            f'<div class="cov-sys">Moon sign: <b>{E(p["moon_sign"])}</b><br>Birth star: <b>{E(p["nakshatra"])}</b>, part {p["pada"]}</div>'
            '<div class="cov-pow">Read from your birth chart</div></div>')
    return card(body, 1)


def _note(p):
    body = ('<div class="noteframe" style="margin-top:90px"><div class="notebox"><div class="ne">A note for you</div>'
            f'<div class="nh"{_fit(p["first_name"], 21)}>Dear {E(p["first_name"])},</div>'
            '<p>This report looks at your next 12 months, month by month. It reads your birth chart and tells you which '
            'months people have long read as strong, mixed or careful.</p>'
            '<p>Read it like a friend\'s guide, not a rule book. Use it to plan your months.</p>'
            '<p>Part 1 is the short version (pp 1 to 12). Part 2 has the detail. Part 3 explains the words.</p>'
            '<div class="sig">Team Axtroshastra</div></div></div>')
    return card(body, 2)


# ---------- page 3 ----------
def _p3(p):
    key = tiles([('Part 1', 'Short version', f'The answers in a few pages. {lk(1, "pp 1 to 12")}'),
                 ('Part 2', 'Details', f'Every topic and month in full. {lk(13, "pp 13 to 44")}'),
                 ('Part 3', 'Astrology guide', f'Plain words for every term. {lk(45, "pp 45 to 54")}')])
    ex = lambda tn, w: f'<div class="pt"><div class="tx" style="font-size:12.5px">{chip(tn)} {w}</div></div>'
    marks = ('<div class="pts" style="margin-top:10px;gap:9px">'
             + ex('strong', 'Months traditionally read as easier for your plans.')
             + ex('mixed', 'Months with some good parts and some quiet parts.')
             + ex('careful', 'Months to take step by step.') + '</div>')
    s = sm(p)
    sample = mini_strip(ov(p), None, s)
    moon = ''
    if p.get('rising_sign') is None:
        moon = callout('Birth time not sure', f'Your birth time is not sure, so this report reads from your {term("Moon sign", 51)}, '
                       f'{E(p["moon_sign"])}. That sign needs no birth time.')
    body = (para('Every month and every topic gets one mark. A topic\'s mark is the tone that most of its 12 months have. '
                 'The counts for those months are printed next to the mark.', 12.5, 12)
            + subhead('The marks', 10) + marks + subhead(f'Your 12 months, {mshort(s[0])} to {mshort(s[-1])}', 12) + sample
            + subhead('The three parts', 12) + key
            + para(f'Look for the words in <b style="color:{BLUE}">blue</b>. They are explained in Part 3, {lk(45, "pp 45 to 54")}.', 12, 10) + moon)
    return pg(body, 3, 'How to read this report')


# ---------- page 4 (contents) ----------
def _p4c(p):
    s, o = sm(p), ov(p)
    first = TOPICS[first_topic(p)][0]
    P1 = ['How to read this report', 'Contents', 'Your chart in short', 'Your 5 answers', 'Your 12 months at a glance',
          'Strong and careful months', 'Patterns in one page', 'Big decisions in short', 'Your first plan', 'Your 5 takeaways']
    P2a = ['Your chart in detail', 'Your planet period', 'Shani Dhaiya and Sade Sati', 'Manglik in detail', 'Other patterns we checked',
           'Sign changes, dated', 'Career: the answer', 'Career: more questions', 'Money: the answer',
           'Money: saving and spending', 'Money: wealth and the read', 'Marriage: the answer', 'Marriage: decisions and care',
           'Luck: the answer', 'Luck: turning points', 'Strengths: the answer', 'Strengths: growth steps']
    topic_at = {19: 0, 21: 1, 24: 2, 26: 3, 28: 4}
    P2b = ['Big decisions in detail', 'Careful months in detail', 'Quarter-by-quarter plan']
    P3 = ['How a chart is read', 'The nine planets', 'Sign by sign', 'How timing is read', 'Patterns in plain words',
          'Words A to Z (1 of 3)', 'Words A to Z (2 of 3)', 'Words A to Z (3 of 3)', 'Doubts and method', 'Thank you']

    def row(n, t, dot=''):
        star = ' <span style="color:var(--gold)">&#9733;</span>' if topic_at.get(n) is not None and TOPICS[topic_at[n]][0] == first else ''
        return f'<a class="xr" href="#p{n}"><span>{dot}{t}{star}</span><span>{n}</span></a>'

    def hd(n, t, pr):
        return f'<a class="xr h" href="#p{n}"><span>{t}</span><span>{pr}</span></a>'

    left = hd(1, 'Part 1 &middot; Short', '1 to 12') + row(1, 'Cover') + row(2, 'A note for you')
    left += ''.join(row(3 + i, t) for i, t in enumerate(P1))
    left += hd(13, 'Part 2 &middot; Details', '13 to 44') + ''.join(row(13 + i, t) for i, t in enumerate(P2a))
    right = hd(30, 'Months', '30 to 41')
    for i, ym in enumerate(s):
        dot = f'<i style="display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:6px;background:{ {"strong":"var(--green)","mixed":"var(--gold2)","careful":"var(--terra)"}[o[ym]] }"></i>'
        right += row(30 + i, mname(ym), dot)
    right += ''.join(row(42 + i, t) for i, t in enumerate(P2b))
    right += hd(45, 'Part 3 &middot; Guide', '45 to 54') + ''.join(row(45 + i, t) for i, t in enumerate(P3))
    col = lambda h: f'<div class="mtoc dense" style="margin-top:0">{h}</div>'
    body = ('<style>.ct .mtoc a.xr{font-size:10.5px;padding:1.2px 1px}.ct .mtoc a.xr.h{font-size:9px;margin-top:7px;white-space:nowrap}</style>'
            f'<div class="ct" style="width:100%;display:grid;grid-template-columns:1fr 1fr;gap:0 14px;align-items:start;margin-top:6px">{col(left)}{col(right)}</div>'
            + para('Dot = the month\'s mark. Star = the chapter you chose first.', 11, 8, 'var(--muted)'))
    return pg(body, 4, 'Contents')


# ---------- page 5 (chart in short) ----------

def _p4(p):
    pp = p['planet_period']
    nxt = str(pp['next_sub']).split('/')[-1]
    rising = p.get('rising_sign')
    t = tiles([
        ('Moon sign', E(p['moon_sign']), f'Your mind and feelings are read from this sign. {lk(51)}'),
        ('Birth star', E(p['nakshatra']), f'Part {p["pada"]} of the star the Moon sat in at birth. {lk(50)}'),
        ('Planet period now', f'{E(pp["main"])}, then {E(pp["sub"])}',
         f'Big period: {E(pp["main"])}. Small period inside it: {E(pp["sub"])}. Until {_d(pp["until"])}. {lk(51)}'),
        ('Rising sign', E(rising) if rising else 'Not used',
         (f'The sign rising in the east at birth. {lk(52)}' if rising else f'Your birth time is not sure, so we use the Moon sign. {lk(52)}'))])
    ev = ov(p)
    hl = pp['until'][:7] if pp['until'][:7] in sm(p) else None
    bar = tl_bar([(f'{E(pp["main"])} / {E(pp["sub"])}', 'Now', _d(pp['until']), 'note'),
                  (f'{E(pp["main"])} / {E(nxt)}' if '/' in str(pp['next_sub']) else E(nxt), _d(pp['until']), '', 'note')])
    if hl:
        where = f'Your small period changes on <b>{_d(pp["until"])}</b>. The box with the dark outline marks it.'
    else:
        where = f'Your small period runs to {_d(pp["until"])}, after these 12 months. It does not change inside this report.'
    ch = changes_in_span(p)
    note = (callout('Your birth time is not sure', f'So there is no rising sign here. Everything is read from the Moon sign, {E(p["moon_sign"])}, '
                    f'which stays the same at any time of day.') if not rising else
            callout('Your birth time is known', f'So the report also uses your rising sign, {E(rising)}. It changes about every two hours, '
                    'which is why the exact time matters.', 'good'))
    body = (t + subhead('Where your planet period changes', 14) + bar
            + mini_strip(ev, hl, sm(p)) + para(where, 12, 8)
            + para(f'Rahu and Ketu are two moving points in the sky. {lk(46)}', 11.5, 6, 'var(--muted)')
            + para(f'{len(ch)} sign changes fall inside your 12 months. Dates to the day: {lk(18)}.', 12, 6) + note
            + para(f'The 12 parts of a chart, and how to read the chart: {lk(45)}.', 11.5, 8, 'var(--muted)'))
    return pg(body, 5, 'Your chart in short')


# ---------- page 6 ----------
LEAD = {
    0: {'strong': ['Work moves are traditionally read as easier in most months.', 'Most months back new tasks, talks and asks at work.', 'Your work months lean strong, so plan the bigger asks.'],
        'mixed': ['Work has a mix of good and quiet months.', 'Some months push work forward and some hold it still.', 'Work moves in small steps, with a few strong months to use.'],
        'careful': ['Most work months ask for care, so go step by step.', 'Work is traditionally read as a step-by-step topic here.', 'Keep work plans simple in most months and use the strong ones.']},
    1: {'strong': ['Money months mostly read as steady and open for plans.', 'Saving and earning are traditionally read as easier in most months.', 'Most money months support clear, planned choices.'],
        'mixed': ['Money has a mix of open and quiet months.', 'Money moves unevenly, so match each choice to its month.', 'Some months suit saving and others suit waiting.'],
        'careful': ['Most money months ask you to watch what you spend.', 'Money is traditionally read as a keep-it-simple topic here.', 'Spend with a plan in most months and save in the strong ones.']},
    2: {'strong': ['Relationship months mostly read as warm and open.', 'Talks with a partner or family are traditionally read as easier.', 'Most months suit big talks and shared plans.'],
        'mixed': ['Relationships have a mix of warm and quiet months.', 'Some months suit talks and others suit giving space.', 'Take big talks to the strong months and keep the rest light.'],
        'careful': ['Most relationship months ask for gentle talks.', 'Listen first in most months and keep big talks for strong ones.', 'Keep plans simple with a partner in most months.']},
    3: {'strong': ['Luck months mostly read as open for choices.', 'Most months suit new starts and fresh choices.', 'Chances are traditionally read as easier to spot in most months.'],
        'mixed': ['Luck has a mix of open and quiet months.', 'Some months suit new starts and others suit waiting.', 'Pick your moments, as a few months stand out.'],
        'careful': ['Most months ask you to check twice before a big choice.', 'Big choices are traditionally read as better in the strong months.', 'Take big choices only in the strong months.']},
    4: {'strong': ['Study and growth months mostly read as steady.', 'Learning is traditionally read as easier in most months.', 'Most months suit new skills and courses.'],
        'mixed': ['Growth has a mix of steady and quiet months.', 'Some months suit new learning and others suit revision.', 'Use quiet months to revise and strong months to start.'],
        'careful': ['Most months ask you to keep learning plans light.', 'Go for small, steady study goals in most months.', 'Keep new courses for the strong months.']}}


def lead_line(i, t):
    tg = tag(t)
    return pk(LEAD[i][tg], cnt(t)[tg] + i)


def _p5(p):
    ft, rows = first_topic(p), ''
    for i, (name, key, _) in enumerate(TOPICS):
        t = tone_map(p, key)
        best, care = mrange(months_of(t, 'strong')), mrange(months_of(t, 'careful'))
        nm = name + (' <span style="font:700 8px/1 var(--sans);letter-spacing:.1em;color:var(--gold)">YOUR FIRST CHOICE</span>' if i == ft else '')
        c = cnt(t)
        tn = tie_note(t.values())
        tn = f'<span style="font:600 9.5px/1 var(--sans);color:var(--muted);margin-right:8px">{tn}</span>' if tn else ''
        lead = lead_line(i, t)
        cn = (f'<div style="flex:0 0 74px;font:600 9.5px/1.35 var(--sans);color:var(--gold);padding-left:8px;text-align:left">'
              f'{c["strong"]} strong<br>{c["mixed"]} mixed<br>{c["careful"]} careful</div>')
        rows += (f'<div class="k-ans" style="margin-top:3px;padding:3px 11px 3px"><div class="k-ah"><span class="k-at">{nm}</span><span>{tn}{chip(tag(t))}</span></div>'
                 f'<div class="k-lead" style="margin-top:1px;font-size:11px;line-height:1.3">{lead}</div>'
                 f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:2px">'
                 f'<div class="k-al"><b style="min-width:0;margin-right:5px">Best</b>{best or "none in these 12 months"}</div>'
                 f'<div class="k-al"><b style="min-width:0;margin-right:5px">Careful</b>{care or "none in these 12 months"}</div></div>'
                 f'<div style="display:flex;align-items:center;margin-top:2px"><div style="flex:1">{mini_strip(t)}</div>{cn}</div></div>')
    return pg(rows, 6, 'Your 5 answers')


# ---------- page 6 ----------
QLINE = {'strong': ['A good quarter to start plans and finish old ones.', 'Most of these months support moves you have been planning.',
                    'Use this quarter for the plans that matter most.', 'This quarter is traditionally read as open for new steps.'],
         'mixed': ['A quarter of small steps, with good and quiet months side by side.', 'Plans move, but not in a straight line here.',
                   'Keep plans flexible in this quarter.', 'Pick the stronger month in this quarter for your main step.'],
         'careful': ['A quarter to take step by step and check each choice twice.', 'Keep plans simple in these months.',
                     'Finish small tasks here and keep big choices for later.', 'Go gently here and look ahead to the next quarter.']}


def _p6(p):
    o, s = ov(p), sm(p)
    run = longest_run(o, 'strong')
    if run:
        runt = tile('Longest strong run', mrange(run), f'{len(run)} {"month" if len(run) == 1 else "months"} in a row')
    else:
        runt = tile('Longest strong run', 'None', 'No strong month in these 12 months')
    cm = months_of(o, 'careful')
    if cm:
        carett = tile('First careful month', mname(cm[0]), f'It gets easier {eases_from(p, cm[0])}')
    else:
        carett = tile('First careful month', 'None', 'No careful month in these 12 months')
    qs = ''
    for i in range(4):
        q = {ym: o[ym] for ym in s[i * 3:i * 3 + 3]}
        tg = tag(q)
        c = cnt(q)
        qs += (f'<div class="k-ans"><div class="k-ah"><span class="k-at">{mrange(list(q))}</span>{chip(tg)}</div>'
               f'<div class="k-al" style="color:var(--gold);font-weight:600">{c["strong"]} strong, {c["mixed"]} mixed, {c["careful"]} careful months{(" (" + tie_note(q.values()) + ")") if tie_note(q.values()) else ""}</div>'
               f'<div class="k-lead">{pk(QLINE[tg], i + c[tg])}</div></div>')
    body = (strip_big(o, cm[0] if cm else None, s) + counts(o) + tiles([runt, carett])
            + subhead('Four blocks of 3 months (quarters)', 12) + qs)
    return pg(body, 7, 'Your 12 months at a glance')


# ---------- page 7 ----------
GOOD = [['asking for a raise or a new role', 'showing your work to your boss', 'starting a bigger task or a job search'],
        ['saving more and planning big spends', 'fixing a budget and clearing small loans', 'making a plan for a bigger buy'],
        ['big talks and shared plans', 'meeting family and fixing dates', 'spending time together'],
        ['new starts and fresh choices', 'trying something new', 'signing and finishing paperwork'],
        ['starting a course or a skill', 'exams and tests', 'setting a study habit']]
GENTLE = [['quitting in a rush', 'big arguments with your boss', 'saying yes to every task'],
          ['big buys on a whim', 'lending money to friends', 'signing a loan in a hurry'],
          ['big arguments', 'deciding in a hurry', 'bringing up old matters'],
          ['quick big choices', 'signing without reading', 'new starts you have not planned'],
          ['too many courses at once', 'skipping revision', 'starting something new in a rush']]


def _p7(p):
    out = ''
    for i, (name, key, pgno) in enumerate(TOPICS):
        t = tone_map(p, key)
        st, mx, ca = months_of(t, 'strong'), months_of(t, 'mixed'), months_of(t, 'careful')
        good = pk(GOOD[i], len(st) + i)
        gent = pk(GENTLE[i], len(ca) + i)
        if st:
            gl = f'<b style="color:var(--green)">Strong: {mrange(st)}</b><br>Good for {good}.'
        elif mx:
            gl = f'<b style="color:var(--gold)">No strong month. Mixed: {mrange(mx)}</b><br>Closest months. Use them for {good}.'
        else:
            gl = '<b style="color:var(--muted)">No strong or mixed month</b><br>Every month here is careful.'
        if ca:
            cl = f'<b style="color:var(--terra)">Careful: {mrange(ca)}</b><br>Go gently with {gent}.'
        else:
            cl = '<b style="color:var(--green)">No careful month</b><br>' + pk(['Keep your usual pace here.', 'Your usual pace works here.', 'No need to change your pace.', 'Plan as you normally would.', 'This topic stays open all year.'], i)
        out += (f'<div style="width:100%;margin-top:5px;text-align:left"><div style="display:flex;justify-content:space-between;align-items:center;'
                f'font-family:var(--serif);font-size:14.5px;font-weight:600;color:var(--ink);padding:0 2px 4px">'
                f'<span>{name}</span><span>{chip(tag(t))}</span></div>'
                f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:11px;line-height:1.35">'
                f'<div style="background:var(--green-bg);border:1px solid #CFE3D6;border-radius:10px;padding:6px 9px">{gl}</div>'
                f'<div style="background:var(--terra-bg);border:1px dashed var(--terra);border-radius:10px;padding:6px 9px">{cl}</div></div></div>')
    body = para('Each topic below shows its strong months and its careful months, with one line on what each is read for.', 12, 4) + out
    return pg(body, 8, 'Strong and careful months')


# ---------- page 8 ----------
VERDICT = ['This does not decide anything. It is one pattern.', 'One pattern among many in a chart. It decides nothing.',
           'A pattern is a pointer, not a final word.']


def _pat(title, what, have, means, i, mode):
    v = pk(VERDICT, i)
    rows = [('What it is', what), ('Do you have it', have), ('What it means for you', means), ('Decides nothing', v)]
    if mode == 'mid':
        rows = [('What it is', what + ' ' + have), ('What it means for you', means), ('Decides nothing', v)]
    if mode == 'tiny':
        rows = [('Do you have it', have), ('What it means for you', means)]
    body = ''.join(f'<div style="font-size:11px;line-height:1.35;margin-top:2px;color:var(--body)"><b style="font:700 8px/1 var(--sans);letter-spacing:.1em;'
                   f'text-transform:uppercase;color:var(--gold)">{a}</b> {b}</div>' for a, b in rows)
    return (f'<div class="k-q" style="margin-top:{5 if mode == 'tiny' else 5}px;padding:{5 if mode == 'tiny' else 5}px 11px"><div class="k-qh" style="font-size:14px"><span>{title}</span>'
            f'{chip("note", "IN YOUR CHART")}</div>{body}</div>')


def _p8(p):
    pats, absent, ch = [], [], changes_in_span(p)
    ss = p['sade_sati']
    if ss.get('active'):
        sw = stage_word(p)
        pats.append(('Sade Sati', f'Saturn near your Moon sign for about seven years. {lk(52)}',
                     f'Yes, you are in the {sw + " stage" if sw else "stages"} now.',
                     'It is traditionally read as a time for steady work and simple plans. The three stages are on p.49.'))
    else:
        absent.append('Sade Sati')
    if has_dhaiya(p):
        d = p['dhaiya']
        o = (re.search(r'\d+\w{2}', str(d.get('kind'))) or [None])
        o = o.group(0) if hasattr(o, 'group') else 'a set'
        ends = f'It pauses on {_d(d["ends"])}' + (f' and starts again on {_d(d["restarts"])}.' if d.get('restarts') else '.') if d.get('ends') else ''
        pats.append(('Shani Dhaiya', f'Saturn\'s spell of about 30 months, when Saturn sits {o} from your Moon sign. {lk(52)}',
                     f'Yes, Saturn is {o} from your Moon sign. {ends}',
                     'It is traditionally read as a reason to choose big steps with care. The months it covers are marked on p.10.'))
    else:
        absent.append('Shani Dhaiya')
    mg = p['manglik']
    if manglik_on(p):
        where = ('from your rising sign and your Moon sign' if (p.get('rising_sign') and mg.get('from_lagna') and mg.get('from_moon'))
                 else 'from your Moon sign' if not p.get('rising_sign') else 'from your rising sign' if mg.get('from_lagna') else 'from your Moon sign')
        canc = ('Something in the chart softens it, so it is read as lighter.'
                if mg.get('cancelled') else 'Nothing in the chart softens it, so it counts.')
        pats.append(('Manglik', f'Mars in one of six set boxes of the chart. {lk(51)}',
                     f'Yes, Mars sits there when counted {where}. {canc}',
                     f'It is traditionally read when a marriage is being looked at. Full page: {lk(16)}.'))
    else:
        absent.append('Manglik')
    if p.get('kaal_sarp'):
        pats.append(('Kaal Sarp', f'All planets sit between Rahu and Ketu, two sky points. {lk(50)}', 'Yes, your chart has this.',
                     'It is traditionally read as a reason to keep plans simple and steady.'))
    else:
        absent.append('Kaal Sarp')
    if p.get('pitra'):
        pats.append(('Pitra', f'The Sun and Rahu, a sky point, share a sign. {lk(51)}', 'Yes, your chart has this.',
                     'It is traditionally read as a link to family and elders.'))
    else:
        absent.append('Pitra')
    if p.get('yogas'):
        ny = len(p['yogas'])
        ns = sum('Pancha' in y['name'] for y in p['yogas'])
        more = f', and {ns} of them {"is a strength yoga" if ns == 1 else "are strength yogas"}' if ns else ''
        pats.append(('Yogas found', f'A yoga is two or more planets that help you. {lk(52)}',
                     f'Yes: {ny} {"yoga" if ny == 1 else "yogas"}{more}. Names are on {lk(17, "p.17")}.',
                     'Traditionally read as strengths to lean on.'))
    else:
        absent.append('positive yogas')
    n = len(pats) + 1
    mode = 'tiny' if n >= 5 else 'mid' if n >= 4 else 'full'
    cards = ''.join(_pat(*x, i, mode) for i, x in enumerate(pats))
    # sign change card (always present)
    items = ''.join(f'<span><b>{E(c["planet"])}</b> {_d(c["date"])}<br><span style="color:var(--muted)">{E(c["from"])} to {E(c["to"])}</span></span>' for c in ch)
    grid = (f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:5px 8px;font-size:10px;line-height:1.3;margin-top:7px">{items}</div>'
            if n < 4 else '')
    scard = (f'<div class="k-q" style="margin-top:{5 if mode == 'tiny' else 5}px;padding:{5 if mode == 'tiny' else 5}px 11px"><div class="k-qh" style="font-size:14px"><span>Sign changes</span>'
             f'{chip("note", f"{len(ch)} IN YOUR 12 MONTHS")}</div>'
             f'<div style="font-size:11px;line-height:1.4;margin-top:3px"><b style="font:700 8px/1 var(--sans);letter-spacing:.1em;text-transform:uppercase;color:var(--gold)">What it is</b> '
             f'The day a planet moves into the next sign. {lk(52)} Yours: {len(ch)} fall in these months. Dates to the day: {lk(18)}.</div>{grid}</div>')
    pp = p['planet_period']
    extra = ''
    if len(pats) <= 2:
        extra = callout('What carries your months', f'Your months are shaped by the planet period (big period {E(pp["main"])}, small period {E(pp["sub"])}) and by '
                        f'the {len(ch)} sign changes above. {lk(14)}')
    ab = (f'<p style="width:100%;text-align:left;font-size:11.5px;line-height:1.5;color:var(--muted);margin-top:10px;border-top:1px solid var(--line);padding-top:8px">'
          f'Not in your chart: {", ".join(absent)}.</p>') if absent else ''
    body = (cards + scard + extra + ab)
    return pg(body, 9, 'Patterns in one page')


# ---------- page 9 ----------
def _p9(p):
    s, o = sm(p), ov(p)
    P = _plan()
    gold = P.act_months(p, 'gold')
    dropped, held = P.left_out(p), P.stage_months(p)
    top = ''
    why = ''
    if dropped:
        why = para(f'{len(dropped)} strong {"month is" if len(dropped) == 1 else "months are"} left out ({mrange(dropped)}) because a Saturn stage covers {"it" if len(dropped) == 1 else "them"}.', 11.5, 6, 'var(--muted)')
    ss = p['sade_sati']
    no_dates = bool(ss.get('active')) and 'no stage dates' in P._stage_line(p)
    rule = callout('The rule' + (f': strong months to act are {mrange(gold)}' if gold else ''),
                   f'A month to act is a strong month when Saturn\'s long spell is not running (Shani Dhaiya or Sade Sati, {lk(49)}). '
                   + ('Neither stage is on in these 12 months, so every strong month counts.' if not held and not no_dates else
                      (f'Months inside those stages here: {mrange(held)}.' if held else '')
                      + (' Your Sade Sati has no stage dates, so no month is left out for it.' if no_dates else '')))
    items = [('Gold', 'gold', 'Ask in writing for the purity stamp and the making charge.'),
             ('Property', 'property', 'Read every paper and check the seller\'s papers twice.'),
             ('Vehicle', 'vehicle', 'Compare two offers and check the papers before you pay.'),
             ('Move', 'move', 'Fix the new place and the date before you leave the old one.')]
    rows = ''
    for name, kind, line in items:
        act = P.act_months(p, kind)
        ad = {ym: ('strong' if ym in act else 'none') for ym in s}
        rows += (f'<div class="k-ans"><div class="k-ah"><span class="k-at">{name}</span>'
                 f'{chip("strong", act_chip_text(len(act))) if act else chip("note", "NO MONTH FITS")}</div>'
                 f'<div class="k-lead">{line}</div>{mini_strip(ad, act[0] if act else None, s)}</div>')
    body = (top + why + rule + rows + para(f'Full detail for each choice: {lk(42)}.', 11.5, 8, 'var(--muted)'))
    return pg(body, 10, 'Big decisions in short')


# ---------- page 10 ----------
CAREFUL_DO = ['Keep plans small, check each choice twice, and keep big buys for a strong month.',
              'Finish small tasks, read before you sign, and wait for a stronger month for big steps.',
              'Choose simple steps, ask one more person before a big choice, and note what you decide.']
TONE_LINE = {'strong': ['Good for starting what you have planned.', 'Use it for the step you have waited on.', 'Good for asks and fresh starts.'],
             'mixed': ['Some good parts and some quiet parts.', 'Move on small things and let big ones wait.', 'A middle month, so keep plans flexible.'],
             'careful': ['Go step by step.', 'Keep plans simple and check twice.', 'A month to finish small tasks.']}


def _p10(p):
    s, o = sm(p), ov(p)
    ft = first_topic(p)
    name, key, _ = TOPICS[ft]
    t = tone_map(p, key)
    st = months_of(t, 'strong')
    cm = months_of(o, 'careful')
    sm1 = next((ym for ym in s if o[ym] == 'strong'), None)
    m1 = (f'<b>Start with {name.lower()}, the topic you chose first.</b> '
          + (f'Its strong months are {mrange(st)}.' if st else 'It has no strong month, so plan around its mixed months '
             + (mrange(months_of(t, 'mixed')) or 'and keep steps small') + '.'))
    m2 = (f'<b>Get ready for {mname(cm[0])}, your first careful month.</b> Finish open tasks before it starts.' if cm
          else '<b>Check your month at the start of each month.</b> You have no careful month, so use the month cards to pick your best days.')
    m3 = (f'<b>Use {mname(sm1)}, your first strong month.</b> It starts on {_d(sm1 + "-01")}. Put your main step there.' if sm1
          else '<b>Use your first mixed month for your main step.</b> You have no strong month in these 12 months.')
    stp = steps([('Move 1.', m1), ('Move 2.', m2), ('Move 3.', m3)])
    if cm:
        cal = callout(f'Your first careful month: {mname(cm[0])}',
                      f'{pk(CAREFUL_DO, len(cm))} It gets easier {eases_from(p, cm[0])}.', 'careful')
    else:
        cal = callout('No careful month', 'Every month in these 12 months is strong or mixed, so there is nothing to brace for.', 'good')
    if sm1:
        good = callout(f'Your first strong month: {mname(sm1)}', f'It starts on {_d(sm1 + "-01")}. {pk(TONE_LINE["strong"], len(st))}', 'good')
    else:
        good = callout('No strong month', 'Use your mixed months. They have some good parts.')
    first3 = tiles([(mname(ym), chip(o[ym]), pk(TONE_LINE[o[ym]], i + len(ym))) for i, ym in enumerate(s[:3])])
    body = (stp + cal + good + subhead('Your first three months', 14) + first3
            + mini_strip(o, cm[0] if cm else sm1, s))
    return pg(body, 11, 'Your first plan')


# ---------- page 11 ----------
def _p11(p):
    s, o = sm(p), ov(p)
    # 1 strongest topic
    best = max(range(5), key=lambda i: (cnt(tone_map(p, TOPICS[i][1]))['strong'], -i))
    bt = tone_map(p, TOPICS[best][1])
    bs = months_of(bt, 'strong')
    k1 = (f'<b>{TOPICS[best][0]} is your strongest topic.</b> It has {len(bs)} strong months: {mrange(bs)}.' if bs else
          '<b>No topic has a strong month.</b> Your mixed months are your best chance. Use them for small steps.')
    cm = months_of(o, 'careful')
    k2 = (f'<b>Your first careful month is {mname(cm[0])}.</b> Go step by step then. It gets easier {eases_from(p, cm[0])}.' if cm else
          '<b>You have no careful month.</b> Keep your usual pace in all 12 months.')
    ss = p['sade_sati']
    if ss.get('active'):
        k3 = f'<b>Sade Sati is the pattern that matters most.</b> It means Saturn near your Moon sign. You are in its {stage_word(p) + " stage" if stage_word(p) else "stages"}. {lk(15)}'
    elif has_dhaiya(p):
        k3 = (f'<b>Shani Dhaiya is the pattern that matters most.</b> It is a 30-month Saturn spell. It sits on part of your 12 months'
              + (f' and pauses on {_d(p["dhaiya"]["ends"])}' if p['dhaiya'].get('ends') else '') + f'. {lk(15)}')
    elif manglik_on(p) and not p['manglik'].get('cancelled'):
        k3 = f'<b>Manglik is the pattern that matters most.</b> It means Mars in a set box. It is read for your marriage months. {lk(16)}'
    elif p.get('kaal_sarp') or p.get('pitra'):
        k3 = f'<b>{"Kaal Sarp" if p.get("kaal_sarp") else "Pitra"} is the pattern that matters most.</b> It is one pointer among many, a pattern of sky points. {lk(17)}'
    else:
        ju = [c for c in changes_in_span(p) if c['planet'] == 'Jupiter']
        k3 = (f'<b>Jupiter\'s sign change is the one to watch.</b> It moves on {_d(ju[0]["date"])}. {lk(18)}' if ju else
              f'<b>Your planet period carries your months.</b> Big period {E(p["planet_period"]["main"])}, small period {E(p["planet_period"]["sub"])}. {lk(14)}')
    act = _plan().act_any(p)
    k4 = (f'<b>Your first good month for a big decision is {mname(act[0])}.</b> Gold, property, vehicle and a move: {lk(10)}.' if act else
          f'<b>No month passes the big-decision check.</b> Wait for a strong month outside a Saturn pattern. {lk(10)}')
    k5 = (f'<b>Each month, open its card first.</b> The 12 month cards run from {mshort(s[0])} to {mshort(s[-1])}: {lk(30, "see pp 30 to 41")}. '
          'Read the strip, then the Do and Watch lines.')
    c = cnt(o)
    body = (steps([k1, k2, k3, k4, k5]) + subhead('Your 12 months', 10) + strip_big(o, cm[0] if cm else None, s)
            + f'<div class="k-al" style="margin-top:6px;color:var(--gold);font-weight:700">{ctext(o)}</div>'
            + callout('Keep this page', 'This page is the whole report in five lines. Look at it again at the start of each month.'))
    return pg(body, 12, 'Your 5 takeaways')


def pages(p):
    cards = [_cover(p), _note(p), _p3(p), _p4c(p), _p4(p), _p5(p), _p6(p), _p7(p), _p8(p), _p9(p), _p10(p), _p11(p)]
    return [scope(h, 'm1') for h in cards]


PAGE_TITLES_P1 = ['Cover', 'A note for you', 'How to read this report', 'Contents', 'Your chart in short', 'Your 5 answers',
                  'Your 12 months at a glance', 'Strong and careful months', 'Patterns in one page', 'Big decisions in short',
                  'Your first plan', 'Your 5 takeaways']

if __name__ == '__main__':
    assert len(PAGE_TITLES_P1) == 12
    print('titles ok (pages(p) needs a facts dict and annual_report_p2)')
