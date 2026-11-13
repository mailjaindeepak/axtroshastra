"""Annual Report, PART 2 (base cards 13 to 44) in production: pure functions of the facts dict p.
Public: pages(p), PAGE_TITLES_P2, act_months, act_any, left_out, stage_months, _stage_line (imported by Part 1), wealth_found (Part 3).
Card numbers and 'p.NN' references stay in the BASE 54-card numbering; the assembler remaps them."""
import annual_assets as A


def _span_lbl(p):
    """'Dec to Nov': first and last month of this report's 12-month span."""
    ms = [m['ym'] for m in p['span_months']]
    return f'{A.mshort(ms[0])} to {A.mshort(ms[-1])}'


SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']

PAGE_TITLES_P2 = ['Your chart in detail', 'Your planet period', 'Shani Dhaiya and Sade Sati', 'Manglik in detail',
                  'Other patterns we checked', 'Sign changes, dated', 'Career and work', 'Career and work',
                  'Money and savings', 'Money and savings', 'Money and savings', 'Marriage and relationships',
                  'Marriage and relationships', 'Luck and big decisions', 'Luck and big decisions',
                  'Strengths, study and growth', 'Strengths, study and growth', 'Dec 2026', 'Jan 2027', 'Feb 2027',
                  'Mar 2027', 'Apr 2027', 'May 2027', 'Jun 2027', 'Jul 2027', 'Aug 2027', 'Sep 2027', 'Oct 2027',
                  'Nov 2027', 'Big decisions in detail', 'Careful months in detail', 'Quarter-by-quarter plan']


# ======================================================================
# SECTION 2a: chart, planet period, Dhaiya and Sade Sati, Manglik, other patterns, sign changes (cards 13-18)
# Annual Report mock, PART 2 pages 12 to 17: chart, planet period, Saturn patterns, Manglik, other patterns, sign changes. Every finding is read from the person dict p. Only generic framing text lives here.
# ======================================================================
_a_SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
_a_MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
_a_ORD = {1: '1st', 2: '2nd', 3: '3rd'}
_a_PART = f'{A.part_label(2, "Details")}'
_a_STAGE_OF_POS = {12: 'first', 1: 'second', 2: 'third'}
_a_MANGLIK_PARTS = (1, 2, 4, 7, 8, 12)
_a_AREA = {1: 'you and how you start things', 2: 'your savings and family talk', 3: 'effort, skills and short trips',
        4: 'home and your family base', 5: 'study, children and creative work', 6: 'daily work and routine',
        7: 'partners and close deals', 8: 'sudden changes and shared money', 9: 'luck, learning and long trips',
        10: 'career and standing', 11: 'gains and friends', 12: 'spending and time away'}
_a_PART_SHORT = {1: 'you', 2: 'money, family', 3: 'effort, skills', 4: 'home', 5: 'study, children', 6: 'daily work', 7: 'partners',
              8: 'sudden change', 9: 'luck, learning', 10: 'career', 11: 'gains, friends', 12: 'spending, rest'}
_a_READ_FOR = {'Sun': 'your core self and drive', 'Moon': 'feelings and daily mood', 'Mars': 'energy and courage',
            'Mercury': 'talk, study and trade', 'Jupiter': 'growth and good advice', 'Venus': 'love and comfort',
            'Saturn': 'effort and time', 'Rahu': 'strong pulls and wants', 'Ketu': 'letting go and focus'}
_a_THEME = {  # planet: (theme, career, money, marriage, luck, strengths)
    'Sun': ('your standing and confidence', 'Bosses and recognition come into focus', 'Money linked to your name and rank',
            'Close ties are read through respect', 'Support from elders and seniors', 'Leadership and self-belief'),
    'Moon': ('your feelings and daily needs', 'Work with people and the public', 'Money moves with daily needs',
             'Warmth and care in close ties', 'Support from mother, home and the public', 'Feeling, memory and care for others'),
    'Mars': ('energy and action', 'Drive, action and competing', 'Quick moves with money, big or small',
             'Energy and sharp words in close ties', 'Luck comes through taking action', 'Courage and stamina'),
    'Mercury': ('talk, study and trade', 'Talking, writing, trade and learning', 'Money from skills and small deals',
                'Talk and understanding set the tone', 'Luck through contacts and quick thinking', 'Sharp thinking and learning'),
    'Jupiter': ('growth and good advice', 'Growth, teachers and good advisers', 'Steady growth and savings',
                'Goodwill and commitment', 'Luck is read as open and wide', 'Wisdom and good sense'),
    'Venus': ('love and comfort', 'Art, style, service and people skills', 'Comfort, buying and enjoying money',
              'Love, romance and togetherness', 'Luck through charm and good company', 'Taste, charm and a love of beauty'),
    'Saturn': ('effort and time', 'Effort that earns a higher post step by step', 'Careful saving and building up',
               'Doing your duty and staying loyal to close people', 'Luck that builds up with time', 'Discipline and staying power'),
    'Rahu': ('strong wants and new paths', 'Big wants, new fields and unusual paths', 'Sudden gains and sudden spending',
             'A strong pull toward someone different', 'Luck through the unusual and the foreign', 'Ambition and trying new things'),
    'Ketu': ('letting go and focus', 'Quiet, deep work away from the crowd', 'Less interest in money for its own sake',
             'Deep bonds that need little talk', 'Luck through letting go', 'Focus, insight and standing apart')}
_a_TOPICS = ['Career and work', 'Money and savings', 'Marriage and relationships', 'Luck and big decisions', 'Strengths and growth']
_a_PLAIN6 = {'moon': 'the sign the Moon sat in', 'rising': 'the sign rising at birth', 'chart': 'a map of the sky at birth',
          'parts': 'the 12 areas of life', 'period': 'a long block ruled by one planet',
          'sub': 'a smaller block inside it', 'change': 'a planet moving into the next sign',
          'dhaiya': 'Saturn in your 4th or 8th sign', 'sade': 'Saturn near your Moon sign',
          'manglik': 'Mars in certain parts of the chart', 'kaal': 'all planets on one side of Rahu and Ketu',
          'pitra': 'Sun and Rahu sharing one sign', 'yoga': 'a helpful link between planets',
          'cancel': 'a rule that softens the pattern', 'planets': 'the nine planets of the chart'}
_a_NOT_VERDICT = {
    'dhaiya': 'One pattern among many. Your other months are shaped by more than this.',
    'sade': 'This reading is one thread. It sits next to everything else in your chart.',
    'manglik': 'This is only something to talk about. It does not rule on any person or any match.',
    'kaal': 'Only a note about how planets sit. Your chart has many other parts that count too.',
    'pitra': 'Some astrologers note it and many do not. It decides nothing alone.',
    'yoga': 'Yogas are good signs on paper. They do not promise anything.'}


# ---------- small helpers
def _a_D(iso):
    y, m, d = iso[:10].split('-')
    return f'{int(d)} {_a_MON[int(m) - 1]} {y}'


def _a_ym_name(iso):
    y, m, _ = iso.split('-')
    return f'{_a_MON[int(m) - 1]} {y}'


def _a_o(n):
    return _a_ORD.get(n, f'{n}th')


def _a_pos(frm, sign):
    return (_a_SIGNS.index(sign) - _a_SIGNS.index(frm)) % 12 + 1


def _a_see(n, txt=None):
    return f'<a class="xr" href="#p{n}">{txt or f"see p.{n}"}</a>'


def _a_term(name, key, n):
    """Term in bold, six plain words, link to its Part 3 page."""
    return f'<b>{name}</b> ({_a_PLAIN6[key]}; {_a_see(n)})'


def _a_idx(p, n=3):
    return _a_SIGNS.index(p['moon_sign']) % n


def _a_base(p):
    return p['rising_sign'] or p['moon_sign']


def _a_sign_of(p, planet):
    return next((r['sign'] for r in p['planet_table'] if r['planet'] == planet), None)


def _a_lead(t):
    return f'<p class="lead" style="font-size:14px;line-height:1.5;margin-top:11px">{t}</p>'


def _a_small(t, mt=10):
    return f'<p class="fine" style="margin-top:{mt}px">{t}</p>'


_a_LBL = ('font:700 9px/1.3 var(--sans);letter-spacing:.12em;text-transform:uppercase;color:var(--gold);display:block;margin-top:4px')
_a_TXT = 'font-size:11px;line-height:1.35;color:var(--body)'


def _a_pcard(title, here, rows, verdict, compact=False):
    """Pattern box: what it is / do you have it / what it means for you / Not a verdict."""
    pill = (f'<span style="font:700 8.5px/1 var(--sans);letter-spacing:.12em;text-transform:uppercase;padding:4px 8px;border-radius:20px;'
            + ('background:var(--gold);color:#fff' if here else 'border:1px solid var(--line);color:var(--muted)')
            + f'">{"In your chart" if here else "Not in your chart"}</span>')
    LI = _a_LBL.replace('display:block', 'display:inline;margin-right:5px')
    tx, mt, gap, pad = (('font-size:10.5px;line-height:1.25;color:var(--body)', 2, 4, '5px 10px') if compact
                        else (_a_TXT, 3, 7, '7px 11px'))
    body = ''.join(f'<div style="{tx};margin-top:{mt}px"><span style="{LI}">{k}</span>{v}</div>' for k, v in rows)
    body += f'<div style="{tx};margin-top:{mt}px"><span style="{LI}">Not a verdict</span>{verdict}</div>'
    return (f'<div style="width:100%;text-align:left;margin-top:{gap}px;background:var(--box-fill);border:1px solid var(--box-line);'
            f'border-radius:12px;padding:{pad}"><div style="display:flex;justify-content:space-between;align-items:center;gap:8px">'
            f'<span style="font:500 14.5px/1.2 var(--serif);color:var(--ink)">{title}</span>{pill}</div>{body}</div>')


# ---------- page 12
def _a__chart_svg(p):
    cells = [[(160, 0), (240, 80), (160, 160), (80, 80)], [(0, 0), (160, 0), (80, 80)], [(0, 0), (80, 80), (0, 160)],
             [(0, 160), (80, 80), (160, 160), (80, 240)], [(0, 160), (80, 240), (0, 320)], [(0, 320), (80, 240), (160, 320)],
             [(160, 320), (80, 240), (160, 160), (240, 240)], [(160, 320), (240, 240), (320, 320)],
             [(320, 320), (240, 240), (320, 160)], [(320, 160), (240, 240), (160, 160), (240, 80)],
             [(320, 160), (240, 80), (320, 0)], [(320, 0), (240, 80), (160, 0)]]
    s = ('<rect x="0" y="0" width="320" height="320" fill="#FDFBF5" stroke="#B9862E"/>'
         '<path d="M160,0 L320,160 L160,320 L0,160 Z M0,0 L320,320 M320,0 L0,320" fill="none" stroke="#B9862E" stroke-width="1"/>')
    b = _a_SIGNS.index(_a_base(p))
    for i, c in enumerate(cells):
        cx = sum(q[0] for q in c) / len(c)
        cy = sum(q[1] for q in c) / len(c)
        s += (f'<text x="{cx}" y="{cy - 6}" text-anchor="middle" font-size="12" fill="#B9862E">{i + 1} '
              f'<tspan font-size="10">{_a_SIGNS[(b + i) % 12][:3]}</tspan></text>')
        for j, code in enumerate(p['kundli'].get(i + 1, [])[:3]):
            s += f'<text x="{cx}" y="{cy + 12 + j * 14}" text-anchor="middle" font-size="13" font-weight="600" fill="#2A2118">{code}</text>'
    return (f'<svg viewBox="0 0 320 320" role="img" aria-label="Your birth chart" '
            f'style="display:block;width:100%;max-width:182px;height:auto;margin:0">{s}</svg>')


def _a_page12(p):
    b = _a_SIGNS.index(_a_base(p))
    key = ''.join(
        f'<div style="font-size:10.5px;line-height:1.35;color:var(--body)"><b style="color:var(--gold)">{i}</b> {_a_SIGNS[(b + i - 1) % 12]}'
        f' <span style="color:var(--muted)">· {_a_PART_SHORT[i]}</span></div>' for i in range(1, 13))
    rows = []
    for r in p['planet_table']:
        n = _a_pos(_a_base(p), r['sign'])
        rows.append([r['planet'], r['sign'], f'Part {n}', _a_READ_FOR.get(r['planet'], '')])
    if p['rising_sign']:
        note = (f'Box 1 is your {_a_term("rising sign", "rising", 45)}, {p["rising_sign"]}, worked out from your birth time. '
                f'Your Moon sign is {p["moon_sign"]}.')
        ctitle = 'Where box 1 comes from'
    else:
        note = (f'Your birth time is not sure, so box 1 is your {_a_term("Moon sign", "moon", 45)}, {p["moon_sign"]}. '
                f'The planets keep their signs. Only the part of life they land in could change if the time moves.')
        ctitle = 'Moon-sign reading'
    body = (_a_lead(f'This is your {_a_term("birth chart", "chart", 45)}. Count from box 1 and go around. '
                 f'Each box is one of {_a_term("the 12 parts of a chart", "parts", 47)}. Planet codes: Su Sun, Mo Moon, Ma Mars, '
                 f'Me Mercury, Ju Jupiter, Ve Venus, Sa Saturn, Ra Rahu, Ke Ketu.')
            + f'<div style="width:100%;display:grid;grid-template-columns:182px 1fr;gap:10px;align-items:center;margin-top:8px">{_a__chart_svg(p)}'
            f'<div style="text-align:left">{key}</div></div>'
            + A.table(['Planet', 'Sign', 'Part', 'Read for'], rows, small=True)
            + A.callout(ctitle, note))
    return A.card(body, 13, _a_PART, 'Your chart in detail')


# ---------- page 13
def _a__days(a, b):
    from datetime import date
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def _a_page13(p):
    pp = p['planet_period']
    main, sub = pp['main'], pp['sub']
    until, nxt, nxt_start = pp['until'], pp['next_sub'], pp['next_start']
    today = p['today']
    w1 = max(1, _a__days(today, until))
    segs = [(f'{main} / {sub} now', _a_D(today), _a_D(until), 'note', w1),
            (nxt, _a_D(nxt_start), 'and on', 'mixed', max(60, int(w1 * .8)))]
    span_yms = [m['ym'] for m in p['span_months']]
    hl = nxt_start[:7] if nxt_start[:7] in span_yms else None
    if hl:
        where = (f'The change lands in {_a_ym_name(nxt_start)}, inside your 12 months. The ring on the line marks it.')
    else:
        where = (f'The change comes on {_a_D(nxt_start)}, after your 12 months, so the whole line below sits inside {sub}.')
    th = _a_THEME.get(sub, _a_THEME['Moon'])
    mth = _a_THEME.get(main, _a_THEME['Moon'])
    rows = [[_a_TOPICS[i], th[i + 1]] for i in range(5)]
    body = (_a_lead(f'Life is read in long blocks called {_a_term("planet periods", "period", 48)}. Each has smaller {_a_term("sub-periods", "sub", 48)}. '
                 f'You are in the {main} period, in its {sub} sub-period.')
            + A.tiles([('Planet period', main, f'read for {mth[0]}'), ('Sub-period now', sub, f'read for {th[0]}'),
                     ('Sub-period ends', _a_D(until), f'then {nxt}')])
            + '<div class="exlabel" style="margin-top:14px;text-align:left;width:100%">Your timeline</div>'
            + A.tl_bar(segs)
            + f'<div class="exlabel" style="margin-top:14px;text-align:left;width:100%">Your 12 months, {_span_lbl(p)}</div>'
            + A.mini_strip(p['tones'], highlight=hl, months=span_yms)
            + _a_small(where, 6)
            + f'<div class="exlabel" style="margin-top:12px;text-align:left;width:100%">What {sub} is traditionally read as, topic by topic</div>'
            + A.table(['Topic', f'{sub} sub-period'], rows, small=True)
            + A.callout('Next change', f'{nxt} begins on {_a_D(nxt_start)}. Until then the {sub} sub-period sets the background for every topic in this report.'))
    return A.card(body, 14, _a_PART, 'Your planet period')


# ---------- page 14 (Saturn)
def _a__segments(p):
    """Saturn's sign by date: list of dicts start, end, sign, n (count from Moon sign), kind."""
    sn = p['saturn_now']
    pts = [(p['today'], sn['sign'])] + [(c['date'], c['to']) for c in sn['changes']]
    out = []
    for i, (d, s) in enumerate(pts):
        n = _a_pos(p['moon_sign'], s)
        kind = ('sade', _a_STAGE_OF_POS[n]) if n in _a_STAGE_OF_POS else (('dhaiya', _a_o(n)) if n in (4, 8) else (None, None))
        end = pts[i + 1][0] if i + 1 < len(pts) else None
        out.append(dict(start=d, end=end, sign=s, n=n, kind=kind[0], sub=kind[1], first=(i == 0)))
    return out


def _a__sat_strip(p, segs, compact=False):
    ch = 22 if compact else 34
    cells = ''
    col = {'dhaiya': '#C9A34E', 'sade': '#B4572B', None: '#E6DDC9'}
    for m in p['span_months']:
        ym = m['ym']
        cur = segs[0]
        for sg in segs:
            if sg['start'] <= ym + '-01':
                cur = sg
        nxt = [sg for sg in segs[1:] if sg['start'][:7] == ym]
        a = col[cur['kind']]
        bk = nxt[-1] if nxt else cur
        bgc = col[bk['kind']]
        bg = f'linear-gradient(90deg,{a} 50%,{bgc} 50%)' if nxt else a
        ring = ';outline:1.5px solid var(--ink);outline-offset:1px' if nxt else ''
        fg = '#fff' if (cur['kind'] == 'sade' or bk['kind'] == 'sade') and not nxt else 'var(--ink)'
        lab = f'{cur["n"]}' + ('&rarr;' + f'{bk["n"]}' if nxt and bk['n'] != cur['n'] else '')
        cells += (f'<div style="text-align:center"><div style="height:{ch}px;border-radius:5px;background:{bg}{ring};'
                  f'font:600 9px/{ch}px var(--sans);color:{fg}">{lab}</div>'
                  f'<div style="font:500 9.5px/1.4 var(--sans);color:var(--muted);margin-top:3px">{_a_MON[int(ym[5:]) - 1]}</div></div>')
    leg = ''.join(f'<span style="display:inline-flex;align-items:center;gap:5px;margin-right:12px"><i style="width:11px;height:11px;border-radius:3px;background:{c};display:inline-block"></i>{t}</span>'
                  for c, t in (('#C9A34E', 'Shani Dhaiya'), ('#B4572B', 'Sade Sati'), ('#E6DDC9', 'neither')))
    return (f'<div style="width:100%;display:grid;grid-template-columns:repeat(12,1fr);gap:3px;margin-top:8px">{cells}</div>'
            f'<div style="width:100%;text-align:left;font-size:10.5px;color:var(--muted);margin-top:7px">{leg}</div>'
            f'<div style="width:100%;text-align:left;font-size:10.5px;color:var(--muted);margin-top:3px">The number in a box is Saturn\'s place counted from your Moon sign. A ring marks a month with a sign change.</div>')


_a_DH_MEAN = {'4th': ['Astrologers link it with home, family comfort and your sense of belonging.',
                   'Astrologers link it with the home front, property and a settled feeling.',
                   'Astrologers link it with mother, home and the way you study.'],
           '8th': ['Astrologers link it with sudden changes, shared money and things kept out of sight.',
                   'Astrologers link it with surprises, joint money and answers that take their time.',
                   'Astrologers link it with unexpected turns, shared money and deep questions.']}
_a_SADE_MEAN = {'first': ['traditionally read as the start of a longer run, when Saturn begins to ask for steady effort. It is linked with changes in routine and spending.',
                       'traditionally read as the opening of a longer run. Astrologers link it with new routines and a closer look at spending.'],
             'second': ['traditionally read as the middle of the run, with Saturn right over your Moon sign. It is linked with a closer look at work, home and close ties.',
                        'traditionally read as the centre of the run. Astrologers link it with weighing up work, home and the people close to you.'],
             'third': ['traditionally read as the closing part of the run, when Saturn is about to leave. It is linked with sorting out what the earlier stages brought.',
                       'traditionally read as the last part of the run. Astrologers link it with tidying up what the earlier stages began.']}


def _a_page14(p):
    segs = _a__segments(p)
    i = _a_idx(p)
    moon = p['moon_sign']
    s12, s2 = _a_SIGNS[(_a_SIGNS.index(moon) - 1) % 12], _a_SIGNS[(_a_SIGNS.index(moon) + 1) % 12]
    sn = p['saturn_now']
    # table rows
    rows = []
    for sg in segs:
        when = ('Now until ' + _a_D(sg['end'])) if sg['first'] and sg['end'] else (f'{_a_D(sg["start"])} until {_a_D(sg["end"])}' if sg['end'] else f'From {_a_D(sg["start"])}')
        if sg['first'] and not sg['end']:
            when = 'Now and through your 12 months'
        name = {'dhaiya': 'Shani Dhaiya', 'sade': f'Sade Sati, {sg["sub"]} stage', None: 'Neither'}[sg['kind']]
        rows.append([when, f'{sg["sign"]} ({_a_o(sg["n"])} sign)', name])
    dh = p['dhaiya']
    compact = any(sg['kind'] == 'sade' for sg in segs) or (not dh['active'] and any(sg['kind'] == 'dhaiya' for sg in segs[1:]))
    # Dhaiya card
    dh = p['dhaiya']
    dh_start = next((s for s in segs[1:] if s['kind'] == 'dhaiya'), None)
    dh_now = bool(dh['active'])
    kind = _a_o(sn['house_from_moon']) if sn['house_from_moon'] in (4, 8) else (str(dh.get('kind') or '4th').split()[0])
    if dh_now:
        here = (f'Yes, now. Saturn is in {sn["sign"]}, your {kind} sign, until {_a_D(dh["ends"])}.'
                + (f' It comes back on {_a_D(dh["restarts"])}.' if dh.get('restarts') else ''))
        mean = _a_DH_MEAN.get(kind, _a_DH_MEAN['4th'])[i]
        dh_card = _a_pcard('Shani Dhaiya', True, [
            ('What it is', f'Saturn in your 4th or 8th sign from the Moon sign, for about two and a half years. ({_a_see(49)})'),
            ('Do you have it', here), ('What it means for you', mean)], _a_NOT_VERDICT['dhaiya'], compact)
    elif dh_start:
        dh_card = _a_pcard('Shani Dhaiya', True, [
            ('What it is', f'Saturn in your 4th or 8th sign from the Moon sign, for about two and a half years. ({_a_see(49)})'),
            ('Do you have it', f'Not now. It starts on {_a_D(dh_start["start"])}, when Saturn enters {dh_start["sign"]}, your {_a_o(dh_start["n"])} sign.'),
            ('What it means for you', _a_DH_MEAN.get(_a_o(dh_start['n']), _a_DH_MEAN['4th'])[i])], _a_NOT_VERDICT['dhaiya'], compact)
    else:
        dh_card = _a_pcard('Shani Dhaiya', False, [
            ('What it is', f'Saturn in your 4th or 8th sign from the Moon sign, for about two and a half years. ({_a_see(49)})'),
            ('Do you have it', f'Not on now. Saturn is in {sn["sign"]}, your {_a_o(sn["house_from_moon"])} sign, and no sign change in your 12 months moves it into your 4th or 8th.'),
            ('What carries your months instead', 'Your planet period on p.14 and the sign changes on p.18.')], _a_NOT_VERDICT['dhaiya'], compact)
    # Sade Sati card
    cur = segs[0]
    sade_start = next((s for s in segs[1:] if s['kind'] == 'sade'), None)
    what_sade = (f'Saturn passing the sign before your Moon sign, your Moon sign and the one after, about seven and a half years in all. '
                 f'({_a_see(49)})')
    if cur['kind'] == 'sade':
        st = cur['sub']
        nxt = segs[1] if len(segs) > 1 else None
        here = f'Yes, now, in the {st} stage. Saturn is in {cur["sign"]}, your {_a_o(cur["n"])} sign' + (f', until {_a_D(cur["end"])}.' if cur['end'] else '.')
        if nxt:
            here += (f' Then it moves to {nxt["sign"]}' + (' and the pattern ends.' if nxt['kind'] != 'sade' else f', the {nxt["sub"]} stage.'))
        sade_card = _a_pcard(f'Sade Sati, {st} stage', True, [
            ('What it is', what_sade), ('Do you have it', here),
            ('What it means for you', 'This stage is ' + _a_SADE_MEAN[st][i % 2])], _a_NOT_VERDICT['sade'], compact)
    elif sade_start:
        st = sade_start['sub']
        sade_card = _a_pcard('Sade Sati', True, [
            ('What it is', what_sade),
            ('Do you have it', f'Not now. The {st} stage starts on {_a_D(sade_start["start"])}, when Saturn enters {sade_start["sign"]}.'),
            ('What it means for you', 'That stage is ' + _a_SADE_MEAN[st][i % 2])], _a_NOT_VERDICT['sade'], compact)
    else:
        sade_card = _a_pcard('Sade Sati', False, [
            ('What it is', what_sade),
            ('Do you have it', f'Not on now. It would start when Saturn enters {s12}. Saturn is in {sn["sign"]}, your {_a_o(sn["house_from_moon"])} sign, and none of its sign changes in your 12 months reaches {s12}.'),
            ('What it would be', f'Three stages, each about two and a half years: Saturn in {s12}, then {moon}, then {s2}.')], _a_NOT_VERDICT['sade'], compact)
    stage_tiles = A.tiles([('First stage', s12, f'Saturn one sign before {moon}'), ('Second stage', moon, 'Saturn over your Moon sign'),
                         ('Third stage', s2, f'Saturn one sign after {moon}')])
    body = (_a_lead(f'Saturn stays about two and a half years in one sign. Counted from your {_a_term("Moon sign", "moon", 45)}, {moon}, some places get a name.')
            + f'<div class="exlabel" style="margin-top:{8 if compact else 12}px;text-align:left;width:100%">Saturn month by month, {_span_lbl(p)}</div>'
            + _a__sat_strip(p, segs, compact)
            + A.table(['When', 'Saturn is in', 'Named'], rows, small=True)
            + dh_card + sade_card
            )
    return A.card(body, 15, _a_PART, 'Shani Dhaiya and Sade Sati')


# ---------- page 15 (Manglik)
def _a__mars_ring(mars_part):
    return A.wheel_svg(_a_MANGLIK_PARTS, mars_part)


def _a_page15(p):
    m = p['manglik']
    i = _a_idx(p)
    rising = p['rising_sign']
    from_moon = bool(m['from_moon'])
    present = from_moon or (rising is not None and bool(m['from_lagna']))
    cancelled = present and bool(m['cancelled'])
    mars_sign = _a_sign_of(p, 'Mars')
    mars_part = _a_pos(p['moon_sign'] if rising is None else _a_base(p), mars_sign) if mars_sign else 0
    from_what = 'your Moon sign' if rising is None else 'your rising sign'
    if rising is None:
        how = (f'Your birth time is not sure, so Mars is counted from your Moon sign ({p["moon_sign"]}). This is the Moon-sign reading.')
    else:
        how = (f'Mars is counted from your rising sign ({rising}) and also from your Moon sign ({p["moon_sign"]}). '
               f'Counted from your rising sign, Mars is {"in" if m["from_lagna"] else "not in"} one of the six parts. '
               f'Counted from your Moon sign, it is {"in" if from_moon else "not in"} one of them.')
    note = m.get('note')
    rule = (str(note).replace('aspects', 'looks at') if note else 'a cancellation rule applies in your chart')
    if present:
        have = f'Yes. Mars sits in part {mars_part} counted from {from_what}, one of the six parts.' if mars_part in _a_MANGLIK_PARTS else 'Yes, it is present in your chart.'
    else:
        have = f'No. Mars sits in part {mars_part} counted from {from_what}, outside the six parts.' if mars_part else 'No.'
    if present and cancelled:
        means = ['Because it is cancelled, astrologers read the pattern as softened. Marriage months follow your own marriage tones below.',
                 'With the cancellation in place, the pattern is read as much lighter. Your marriage months matter more than the label.',
                 'The cancellation takes most of the force out of it. Your marriage months below are the better guide.'][i]
    elif present:
        means = ['Traditionally read as a strong, direct Mars. Astrologers link it with firm views in close ties and a wish for a partner of the same energy.',
                 'Traditionally read as extra Mars energy in close ties. Astrologers link it with strong feelings and a need to be heard.',
                 'Traditionally read as a lot of Mars drive. Astrologers link it with fast moves in love and a need for a partner who keeps pace.'][i]
    else:
        means = ['Nothing extra to read here. Your marriage months below come from your own marriage tones.',
                 'There is no Mars pattern to add. Your marriage months below tell the story.',
                 'No Mars pattern sits on top of your chart. Your marriage months below are the guide.'][i]
    cancel_txt = (f'Yes. {rule[0].upper() + rule[1:]}. ({_a_PLAIN6["cancel"]}; {_a_see(49)})' if cancelled
                  else ('No softening rule is found in your chart, so the reading above stays as written. It is a note, not a verdict.' if present
                        else 'Not needed, because the pattern is not present.'))
    mar = p['areas']['marriage']
    ym = [x['ym'] for x in p['span_months']]
    st = [k for k in ym if mar.get(k) == 'strong']
    cr = [k for k in ym if mar.get(k) == 'careful']
    mx = [k for k in ym if mar.get(k) == 'mixed']
    if len(st) > len(cr):
        lead_m = ['Strong months lead for marriage.', 'Marriage reads better than not across your months.', 'More strong than careful months sit on your marriage line.'][i]
    elif len(cr) > len(st):
        lead_m = ['Careful months lead for marriage.', 'Marriage reads more careful than strong across your months.', 'More careful than strong months sit on your marriage line.'][i]
    else:
        lead_m = ['Strong and careful months are level for marriage.', 'Marriage is evenly split between strong and careful months.', 'Your marriage line has as many strong as careful months.'][i]
    body = (_a_lead(f'{_a_term("Manglik", "manglik", 49)} counts when Mars sits in part 1, 2, 4, 7, 8 or 12 of the chart.')
            + _a__mars_ring(mars_part)
            + A.box('What it is', 'A Mars reading used by many astrologers when two people are considered for marriage. It looks only at where Mars sits.')
            + A.box('Do you have it', f'{have} {how}')
            + A.box('Is it cancelled', cancel_txt)
            + A.box('What it means for you', means)
            + A.box('Not a verdict', _a_NOT_VERDICT['manglik'])
            + f'<div class="exlabel" style="margin-top:13px;text-align:left;width:100%">Your marriage months, {_span_lbl(p)}</div>'
            + A.mini_strip(mar, months=ym)
            + _a_small(f'{lead_m} Strong: {A.mrange(st) or "none"}. Mixed: {A.mrange(mx) or "none"}. Careful: {A.mrange(cr) or "none"}.', 6))
    return A.card(body, 16, _a_PART, 'Manglik in detail')


# ---------- page 16 (other patterns)
_a_YOGA_PLAIN = [('gaj', 'Jupiter well placed from the Moon. Read as good sense and a good name.'),
              ('hamsa', 'Jupiter strong in its own sign in a main box. Read as a kind, wise way with people.'),
              ('bhadra', 'Mercury strong in a main box. Read as a sharp mind and skill with words and trade.'),
              ('budh', 'Sun and Mercury together. Read as quick thinking and a way with learning.'),
              ('neecha', 'A weak planet gets help from another. Read as a rise after early effort.'),
              ('raj', 'Planets of power and luck linked together. Read as a rise in standing.')]


def _a__yoga_line(y):
    n = (y.get('name') or '').lower()
    for k, t in _a_YOGA_PLAIN:
        if k in n:
            return t
    return (y.get('effect') or 'A helpful link between planets in your chart.').strip()


def _a_page16(p):
    i = _a_idx(p)
    pr = p['planet_period']
    segs = _a__segments(p)
    sade_any = any(s['kind'] == 'sade' for s in segs)
    blocks = []
    carry = [f'Your {pr["main"]} planet period and its {pr["sub"]} sub-period carry them ({_a_see(14)}).',
             f'The dated sign changes carry them ({_a_see(18)}).',
             'Your own strong, mixed and careful months, topic by topic, carry them.']
    c = 0
    if not sade_any:
        blocks.append(_a_pcard('Sade Sati', False, [
            ('What it is', f'Saturn passing near your Moon sign. ({_a_see(49)})'),
            ('Do you have it', f'Not in your chart in these 12 months. Saturn sits in {p["saturn_now"]["sign"]}, away from {p["moon_sign"]}.'),
            ('What carries your months instead', carry[c % 3])], _a_NOT_VERDICT['sade'] if False else 'It is simply absent here, so there is nothing to read.'))
        c += 1
    if p['kaal_sarp']:
        blocks.append(_a_pcard('Kaal Sarp', True, [
            ('What it is', f'All planets on one side of Rahu and Ketu. ({_a_see(49)})'),
            ('Do you have it', 'Present.'),
            ('What it means for you', ['Traditionally read as a chart where life moves in clear waves, with a few turning points.',
                                       'Traditionally read as a chart with a strong single theme running through it.',
                                       'Traditionally read as a chart where results come in bursts.'][i])], _a_NOT_VERDICT['kaal']))
    else:
        blocks.append(_a_pcard('Kaal Sarp', False, [
            ('What it is', f'All planets on one side of Rahu and Ketu. ({_a_see(49)})'),
            ('Do you have it', 'Not present.'),
            ('What carries your months instead', carry[c % 3])], 'Absent means there is no such reading to apply.'))
        c += 1
    if p['pitra']:
        blocks.append(_a_pcard('Pitra', True, [
            ('What it is', f'Sun and Rahu sharing one sign. ({_a_see(49)})'),
            ('Do you have it', 'Present. This is a pattern some astrologers note.'),
            ('What it means for you', ['Linked by some with the father side of the family and with elders.',
                                       'Linked by some with the family line and with old ties.',
                                       'Linked by some with elders and with the way family habits pass down.'][i])], _a_NOT_VERDICT['pitra']))
    else:
        blocks.append(_a_pcard('Pitra', False, [
            ('What it is', f'Sun and Rahu sharing one sign. ({_a_see(49)})'),
            ('Do you have it', 'Not present. Your Sun and Rahu sit in different signs.' if _a_sign_of(p, 'Sun') != _a_sign_of(p, 'Rahu') else 'Not present.'),
            *([('What carries your months instead', carry[c % 3])] if c < 2 else [])], 'Nothing to read here, and nothing missing either.'))
        c += 1
    ys = p['yogas']
    if ys:
        rows = ''.join(
            f'<div style="padding:3px 0;border-top:1px solid var(--box-line);{_a_TXT}"><b style="color:var(--ink)">{y["name"].split(" (")[0]}.</b> {_a__yoga_line(y)}</div>'
            for y in ys[:5])
        blocks.append(f'<div style="width:100%;text-align:left;margin-top:7px;background:var(--box-fill);border:1px solid var(--box-line);border-radius:12px;padding:7px 11px">'
                      f'<div style="display:flex;justify-content:space-between;align-items:center"><span style="font:500 14.5px/1.2 var(--serif);color:var(--ink)">Yogas found: {len(ys)}</span>'
                      f'<span style="font:700 8.5px/1 var(--sans);letter-spacing:.12em;text-transform:uppercase;padding:4px 8px;border-radius:20px;background:var(--gold);color:#fff">In your chart</span></div>'
                      f'<div style="{_a_TXT};margin:5px 0 4px">{_a_PLAIN6["yoga"].capitalize()} ({_a_see(49)}).</div>{rows}'
                      f'<span style="{_a_LBL}">Not a verdict</span><div style="{_a_TXT}">{_a_NOT_VERDICT["yoga"]}</div></div>')
    else:
        blocks.append(_a_pcard('Yogas', False, [
            ('What it is', f'{_a_PLAIN6["yoga"].capitalize()} ({_a_see(49)}).'),
            ('Do you have it', 'None found in your chart.'),
            ('What carries your months instead', carry[c % 3])], 'No yoga does not mean a weak chart. It only means none was found.'))
    here_n = int(bool(p['kaal_sarp'])) + int(bool(p['pitra'])) + int(bool(ys)) + int(sade_any)
    body = (_a_lead(f'{here_n} of 4 other patterns show up in your chart.')
            + ''.join(blocks))
    return A.card(body, 17, _a_PART, 'Other patterns we checked')


# ---------- page 17 (sign changes)
_a_PLANET_LINE = {'Rahu': 'a strong new pull', 'Ketu': 'a letting go', 'Jupiter': 'growth and goodwill', 'Saturn': 'steady effort and testing'}
_a_PCOL = {'Rahu': '#6B5E4B', 'Ketu': '#9A8B73', 'Jupiter': '#C9A34E', 'Saturn': '#B4572B'}


def _a_page17(p):
    ch = sorted(p['sign_changes'], key=lambda c: c['date'])
    moon = p['moon_sign']
    ym = [m['ym'] for m in p['span_months']]
    cells = ''
    for k in ym:
        dots = ''.join(f'<i title="{c["planet"]}" style="display:block;width:9px;height:9px;border-radius:50%;background:{_a_PCOL[c["planet"]]};margin:2px auto 0"></i>'
                       for c in ch if c['date'][:7] == k)
        cells += (f'<div style="text-align:center"><div style="height:46px;border:1px solid var(--box-line);border-radius:5px;background:var(--box-fill);padding-top:1px">{dots}</div>'
                  f'<div style="font:500 9.5px/1.4 var(--sans);color:var(--muted);margin-top:3px">{_a_MON[int(k[5:]) - 1]}</div></div>')
    leg = ''.join(f'<span style="display:inline-flex;align-items:center;gap:4px;margin-right:11px"><i style="width:9px;height:9px;border-radius:50%;background:{c};display:inline-block"></i>{n}</span>' for n, c in _a_PCOL.items())
    cnt = {n: sum(1 for c in ch if c['planet'] == n) for n in _a_PCOL}
    count_txt = ', '.join(f'{n} {v}' for n, v in cnt.items() if v)
    rows = ''
    for c in ch:
        n = _a_pos(moon, c['to'])
        rows += (f'<div style="display:flex;gap:10px;padding:8px 0;border-top:1px solid var(--box-line);text-align:left">'
                 f'<div style="flex:0 0 78px"><div style="font:600 12.5px/1.2 var(--sans);color:var(--ink)">{_a_D(c["date"])}</div>'
                 f'<div style="font:700 9px/1.6 var(--sans);letter-spacing:.1em;text-transform:uppercase;color:{_a_PCOL[c["planet"]]}">{c["planet"]}</div></div>'
                 f'<div style="flex:1;{_a_TXT}"><b style="color:var(--ink)">{c["from"]} to {c["to"]}</b>, your {_a_o(n)} sign. '
                 f'{_a_PLANET_LINE[c["planet"]].capitalize()} touches {_a_AREA[n]}.</div></div>')
    still = [(n, _a_sign_of(p, n)) for n in _a_PCOL if not cnt[n] and _a_sign_of(p, n)]
    if ch:
        intro = (f'{_a_term("Sign changes", "change", 48)} are dated below. Rahu and Ketu are the two pulling points of the chart ({_a_see(46)}). '
                 f'In your 12 months there are {len(ch)}: {count_txt}.')
    else:
        intro = (f'{_a_term("Sign changes", "change", 48)} are dated below. Rahu, Ketu, Jupiter and Saturn stay in one sign each through your 12 months, so there is no dated list.')
    body = (_a_lead(intro)
            + f'<div class="exlabel" style="margin-top:12px;text-align:left;width:100%">Your 12 months, {_span_lbl(p)}</div>'
            + f'<div style="width:100%;display:grid;grid-template-columns:repeat(12,1fr);gap:3px;margin-top:6px">{cells}</div>'
            + f'<div style="width:100%;text-align:left;font-size:10.5px;color:var(--muted);margin-top:6px">{leg}</div>'
            + f'<div style="width:100%;margin-top:10px">{rows}</div>'
            + (f'<div style="width:100%;border-top:1px solid var(--box-line)"></div>' if rows else ''))
    if still:
        lines = ''.join(f'<div style="{_a_TXT};margin-top:3px"><b style="color:var(--ink)">{n}</b> stays in {s}, your {_a_o(_a_pos(moon, s))} sign ({_a_AREA[_a_pos(moon, s)]}).</div>' for n, s in still)
        body += (f'<div class="exlabel" style="margin-top:10px;text-align:left;width:100%">No sign change in your 12 months</div>'
                 f'<div style="width:100%;text-align:left">{lines}</div>')
    body += A.callout('How to read the dates', 'All dates are India time. "Your 5th sign" means the 5th sign counted from your Moon sign, '
                    f'{moon}. The count tells you which part of life the planet is passing through.')
    return A.card(body, 18, _a_PART, 'Sign changes, dated')


def _a__pages(p):
    return [_a_page12(p), _a_page13(p), _a_page14(p), _a_page15(p), _a_page16(p), _a_page17(p)]



_a_TIGHT = ('<style>.page .head{margin-top:5px}.page .rule{margin:8px 0 0}.page .lead{font-size:13.5px;line-height:1.42;margin-top:8px}'
         '.page .exlabel{margin-top:8px!important}.page .callout{margin-top:8px;padding:8px 12px}.page .callout p{font-size:11.5px;line-height:1.4}'
         '.page .callout .ch{margin-bottom:3px}.page .nbox{margin-top:7px;padding:8px 12px}.page .nbox p{font-size:11.5px;line-height:1.4}'
         '.page .k-cnt{padding:5px 6px}.page .k-tiles,.page .k-cnts{margin-top:5px}.page .k-mini{margin-top:6px}.page .k-tile{padding:6px 10px}'
         '.page .k-tv{font-size:14.5px}.page .tw.k-sm td{padding:2px 7px}.page .tw.k-sm{margin-top:6px}.page .k-sm,.page .k-sm td{font-size:11px}</style>')


def _a_pages(p):
    return [A.scope(_a_TIGHT + h, 'm2a') for h in _a__pages(p)]


# ======================================================================
# SECTION 2b: the five chapters (cards 19-29)
# Pages 19-29: the five Part 2 chapters (Career, Money, Marriage, Luck, Strengths). Everything chart-based is read from p.
# ======================================================================
_b_FIRST_PAGE = 19
_b_SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
_b_CODE = {'Su': 'Sun', 'Mo': 'Moon', 'Ma': 'Mars', 'Me': 'Mercury', 'Ju': 'Jupiter', 'Ve': 'Venus', 'Sa': 'Saturn', 'Ra': 'Rahu', 'Ke': 'Ketu'}
_b_LORD = dict(zip(_b_SIGNS, ['Mars', 'Venus', 'Mercury', 'Moon', 'Sun', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Saturn', 'Jupiter']))
_b_WT = ('job', 'business', 'student', 'home')
_b_KEYS = ['career', 'money', 'marriage', 'luck', 'strengths']
_b_TITLES = dict(career='Career and work', money='Money and savings', marriage='Marriage and relationships',
              luck='Luck and big decisions', strengths='Strengths, study and growth')
_b_NOUN = dict(career='career and work', money='money and savings', marriage='relationships',
            luck='luck and big choices', strengths='strengths and growth')
_b_CARE_ORDER = ['careful', 'mixed', 'strong']
_b_MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

# term -> (plain meaning of six words or less, Part 3 page)
_b_GL = {'Moon sign': ('the sign your Moon sat in', 45), 'rising sign': ('sign rising at your birth time', 45),
      'the 12 parts of a chart': ('12 life areas in your chart', 47), 'planet period': ('the planet now leading your timing', 48),
      'sub-period': ('a smaller part of it', 48), 'sign change': ('a planet entering the next sign', 48),
      'yoga': ('a named planet pattern', 49), 'wealth combination': ('a planet pairing read for money', 52),
      'Manglik': ('Mars in a set place', 49), 'Shani Dhaiya': ("Saturn's two-and-a-half-year spell", 49),
      'Sade Sati': ("Saturn's seven-and-a-half-year spell", 49), 'Raj-type yoga': ('a yoga read for rising in position and money', 52)}


class _b_Gl:
    """Blue term; the six-word meaning and 'see p.NN' appear only on first use per page."""
    def __init__(s):
        s.seen = set()

    def __call__(s, key, text=None):
        m, pg = _b_GL[key]
        out = f'<span style="color:#2F5E9E;font:inherit;font-style:normal;text-decoration:underline dotted">{text or key}</span>'
        if key not in s.seen:
            out += f' ({m}, see p.{pg})'
        s.seen.add(key)
        return out


def _b_fd(iso):
    return f'{int(iso[8:])} {_b_MON[int(iso[5:7]) - 1]} {iso[:4]}'


_b__USED = {}


def _b_V(bank, *idx):
    return bank[sum(idx) % len(bank)]


def _b_VF(bank, idx, **kw):
    """Pick the first variant (from idx on) whose finished text has not been used yet."""
    for k in range(len(bank)):
        t = bank[(idx + k) % len(bank)].format(**kw)
        if _b__USED.get(t, 0) < 1:
            _b__USED[t] = _b__USED.get(t, 0) + 1
            return t
    t = bank[idx % len(bank)].format(**kw)
    _b__USED[t] = _b__USED.get(t, 0) + 1
    return t


def _b_g(x, wt):
    return x[wt] if isinstance(x, dict) else x


def _b_mw(n):
    return 'month' if n == 1 else 'months'


def _b_lead_of(c):
    """Tone with most months; a tie goes to the more careful tone."""
    return max(_b_CARE_ORDER, key=lambda t: (c[t], -_b_CARE_ORDER.index(t)))


# ---------------------------------------------------------------- wording banks
_b_LEAD = {
 'strong': ['More of your months help than hold you back in {a}. Move ahead on the plans you have been holding.',
            '{A} has the most strong months. This is a time to act on what matters most to you.',
            'Strong months lead for {a}, so support shows up more often than not.',
            '{A} reads open: strong months are ahead of the rest, so use them well.',
            'In {a}, strong months come out on top. Put your main plans there.'],
 'mixed': ['Mixed months lead for {a}: not a rush and not a stop, so pick each step with thought.',
           '{A} goes up and down. Mixed months are the most common, so plan month by month.',
           'In {a}, mixed months come first. Some steps will fit and some need a second look.',
           'For {a}, mixed months lead, so match each step to its month.',
           '{A} asks for good timing, because mixed months are the biggest group.'],
 'careful': ['Careful months lead for {a}. Go step by step and check each move before you make it.',
             '{A} has the most careful months. This is a time to prepare and keep your options open.',
             'In {a}, careful months come first. Plan well and keep each step simple.',
             '{A} asks for care in most months, so keep plans small and clear.',
             'For {a}, careful months are the biggest group. Prepare first, then move.']}
_b_NO_STRONG = ['No strong month shows. Use mixed months for key steps.', 'None here, so give main steps to mixed months.',
             'Strong months do not appear. Pick mixed ones.', 'No strong month, so time key steps for mixed ones.']
_b_NO_CARE = ['No careful month shows. Still check big steps.', 'None here. Still check each step first.',
           'Careful months do not appear here. Keep checking.', 'No careful month, so you can move at a steady pace.']
_b_READ = {
 'strong': ['{A} has strong months to lean on. Act in them and keep your plan simple.',
            '{A} leans your way. Use the strong months on what matters most.',
            'There is good support in {a}. Move early in the strong months.',
            '{A} is open. Make your key moves while it is.',
            'Plan, then go: the signs for {a} look well supported.'],
 'mixed': ['{A} is mixed. Use the strong months and go gently in the rest.',
           '{A} needs good timing. Match your big steps to the strong months.',
           'Ups and downs mark {a}. Plan around them.',
           '{A} gives you more than one kind of month. Choose your moments.',
           '{A} rewards good timing more than speed.'],
 'careful': ['{A} asks for care. Prepare now and move in your strong months.',
             'Take {a} one step at a time and check each step.',
             'Go gently in {a} and keep your options open.',
             'Use this time to plan {a}, and save your pushes for strong months.',
             '{A} asks for planning more than speed.']}
_b_WHEN = {
 'strong': ['Make your move in {S}.', '{S} are the months to use.', 'Lean on {S} for this.', 'Aim this at {S}.'],
 'mixed': ['Use {S} for the main step and keep the rest light.', 'Give the main step to {S}; the other months suit small moves.',
           'Your best fit is {S}. Treat the others as time to prepare.', 'Time the key step for {S}.'],
 'mixed0': ['No strong month here, so use {M}.', 'With no strong month in this part, {M} suit the main step.',
            'Strong months are missing here, and {M} are your next fit.', 'Use {M}, since no strong month shows.'],
 'careful': ['Keep this for {S}, and go gently in {C}.', 'Hold the main step for {S}, and keep {C} light.',
             'Save it for {S}; in {C} check twice.', 'Move in {S}, and give {C} extra care.'],
 'careful0': ['No strong month here; go gently in {C} and prepare.', 'With no strong month in this part, prepare in {C} and keep steps small.',
              'Strong months are missing here, so keep {C} simple.', 'Prepare in {C}, since no strong month shows here.']}
_b_STRONG_USE = dict(
 career=dict(job='Ask for the role or the raise you want. Share your results.', business='Start the new offer. Meet the client you have been postponing.',
             student='Apply, sit the test, and send your first applications.', home='Restart a skill, take a first order, or apply for a role.'),
 money=dict(job='Move money into savings first. Plan the larger spends.', business='Collect pending payments. Put profit aside before you spend.',
            student='Save part of any money you get. Plan fees early.', home='Fix a monthly saving amount. Plan the larger home spends.'),
 marriage='Talk through big decisions. Plan time together.', luck='Make the choices you have been holding. Start one small fresh habit.',
 strengths=dict(job='Take a course. Practise a skill. Plan a test.', business='Train yourself or your team. Add one new skill.',
                student='Plan exams and courses here. Revise the hardest subject.', home='Start a course. Practise a skill you can earn from.'))
_b_CARE_USE = dict(
 career=dict(job='Keep the current role steady. Check work in writing.', business='Keep costs plain. Finish old orders before new ones.',
             student='Revise and practise. Leave big career choices for later.', home='Prepare quietly. Learn, plan and save before you launch.'),
 money=dict(job='Spend only what is planned. Read every paper before you sign.', business='Hold back new stock and new loans. Watch cash daily.',
            student='Keep spending small. Do not lend to friends.', home='Stick to the budget. Put off big spends.'),
 marriage='Keep talks short and kind. Put off big decisions.', luck='Collect facts and wait. Keep habits small and simple.',
 strengths=dict(job='Revise what you know. Keep learning light.', business='Keep learning light. Review what works.',
                student='Revise and practise past papers. Put off new courses.', home='Keep learning light. Review what you know.'))
_b_EXAMPLE = dict(
 career=dict(job='In real life this can look like a talk about your role, a new task, or a change of team.',
             business='In real life this can look like a new client, a new hire, or a change in how you sell.',
             student='In real life this can look like exams, a first job search, or choosing a course.',
             home='In real life this can look like going back to work, or building income from home.'),
 money=dict(job='In real life this can look like a steady salary, a bonus, or a plan to save each month.',
            business='In real life this can look like uneven income, a big payment due, or a new stock purchase.',
            student='In real life this can look like pocket money, fees, or a first earning.',
            home='In real life this can look like a home budget, a small income, or shared money.'),
 marriage='In real life this can look like time with a partner, family talks, or a new bond.',
 luck='In real life this can look like a chance meeting, an offer, or a door that opens late.',
 strengths=dict(job='In real life this can look like a skill people ask you for, or a course that adds to your work.',
                business='In real life this can look like a skill your customers value, or a course for your team.',
                student='In real life this can look like exams, a course, or a skill that sets you apart.',
                home='In real life this can look like a skill people ask you for, or a course you can do at home.'))

_b_PL = {'Sun': ('confidence and standing', 'Take the lead on one thing each week.'), 'Moon': ('feeling and mind', 'Keep a regular daily routine.'),
      'Mars': ('drive and courage', 'Start the task you have been avoiding.'), 'Mercury': ('thinking and talk', 'Write or speak your ideas more often.'),
      'Jupiter': ('wisdom and good advice', 'Ask a trusted elder or teacher for guidance.'), 'Venus': ('charm and comfort', 'Spend time on what you enjoy making or doing.'),
      'Saturn': ('steady effort in work', 'Keep one habit going every day.')}
_b_WORKW = {'Sun': 'leading, public roles and being the face of a team', 'Moon': 'care, food, people and public-facing work',
         'Mars': 'building, repairs, sport and technical work', 'Mercury': 'trade, writing, numbers and tech',
         'Jupiter': 'teaching, advice and guiding others', 'Venus': 'design, art, beauty and hospitality',
         'Saturn': 'systems, craft and steady long work', 'Rahu': 'new media, tech and work with other places',
         'Ketu': 'research, analysis and fine detail'}
_b_TRAVW = {'Sun': 'trips linked to work or seniors', 'Moon': 'trips that keep you tied to home', 'Mars': 'quick or sudden moves',
         'Mercury': 'short work trips', 'Jupiter': 'long trips and study away', 'Venus': 'trips for comfort or family',
         'Saturn': 'a move that takes time to set up', 'Rahu': 'living far away or in another country', 'Ketu': 'a move away from the usual place'}
_b_SRCW = {'Sun': 'bosses, government or a title', 'Moon': 'public work, food or people', 'Mars': 'property, building or action work',
        'Mercury': 'trade, writing or tech', 'Jupiter': 'teaching, advice or savings that grow', 'Venus': 'art, comfort goods or partners',
        'Saturn': 'a steady salary and long work', 'Rahu': 'new or unusual routes', 'Ketu': 'small, focused sources'}
_b_PARTW = {'Sun': 'a proud, capable partner who wants respect', 'Moon': 'a caring, feeling partner', 'Mars': 'an active, direct partner',
         'Mercury': 'a talkative, clever partner', 'Jupiter': 'a wise, kind partner who guides', 'Venus': 'a charming, loving partner',
         'Saturn': 'a steady, serious partner', 'Rahu': 'a partner from a different background', 'Ketu': 'a quiet, private partner'}
_b_LUCKW = {'Sun': 'help from seniors', 'Moon': 'help from family and the public', 'Mars': 'luck that follows effort',
         'Mercury': 'luck through learning and talk', 'Jupiter': 'help from teachers and elders', 'Venus': 'luck through people and comfort',
         'Saturn': 'luck that comes late and steady', 'Rahu': 'unusual openings', 'Ketu': 'luck through quiet focus'}
_b_PLNOTE = {'Jupiter': 'the growth planet', 'Saturn': 'the effort planet', 'Rahu': 'a pulling point', 'Ketu': 'a pulling point'}
_b_RANK = {'Strong': 0, 'Average': 1, 'Needs care': 2}


# ---------------------------------------------------------------- chart helpers
def _b__sign_of(p, planet):
    return next((r['sign'] for r in p['planet_table'] if r['planet'] == planet), None)


def _b__join(xs):
    return xs[0] if len(xs) == 1 else ', '.join(xs[:-1]) + ' and ' + xs[-1]


def _b_ordn(k):
    return {1: '1st', 2: '2nd', 3: '3rd'}.get(k, f'{k}th')


def _b_place(p, k):
    base = p['rising_sign'] or p['moon_sign']
    sign = _b_SIGNS[(_b_SIGNS.index(base) + k - 1) % 12]
    lab = {r['planet']: _b_RANK.get(r['strength_label'], 1) for r in p['planet_table']}
    names = sorted((_b_CODE[c] for c in p['kundli'].get(k, []) if c in _b_CODE), key=lambda x: lab.get(x, 1))
    if names:
        return sign, names, names[:2], f"{_b__join(names)} {'sits' if len(names) == 1 else 'sit'} there"
    lord = _b_LORD[sign]
    return sign, names, [lord], f"No planet sits there; its owner planet {lord} is in {_b__sign_of(p, lord)}"


def _b_short(p, k):
    sg, names, key, _ = _b_place(p, k)
    return _b__join(names) if names else f"no planet sits here; its owner {key[0]} is in {_b__sign_of(p, key[0])}"


def _b_basis(p, gl):
    return (gl('rising sign'), p['rising_sign']) if p['rising_sign'] else (gl('Moon sign'), p['moon_sign'])


def _b_sky_why(p, gl, ms, i):
    """A chart reason for a run of months: a sign change inside it (not yet used), else the planet period."""
    pp = p['planet_period']
    ch = [c for c in p['sign_changes'] if c['date'][:7] in ms and _b__USED.get(('sc', c['date']), 0) < 1]
    if ch:
        c = ch[i % len(ch)]
        _b__USED[('sc', c['date'])] = 1
        same = [x['planet'] for x in p['sign_changes'] if x['date'] == c['date']]
        return _b_VF(['{w} {v} sign on {d} ({f} to {t}), a {sc} inside these months.',
                   'On {d}, {w} {v} from {f} to {t}. That {sc} of {w} falls inside these months.',
                   'A {sc} lands on {d}: {w} {v} {f} for {t}.',
                   'Inside these months, {w} {v} {f} for {t} on {d}, a {sc}.'], i, w=_b__join(same), v='change' if len(same) > 1 else 'changes',
                  d=_b_fd(c['date']), f=c['from'], t=c['to'], sc=gl('sign change'))
    return _b_VF(['You are in a {m} {pp} with a {s} {sp}.', 'Your {pp} is {m}, and the {sp} now running is {s}.',
               'The {pp} leading these months is {m}, with {s} as the {sp}.', 'Right now {m} leads your {pp}, and {s} is the {sp}.'],
              i, m=pp['main'], s=pp['sub'], pp=gl('planet period'), sp=gl('sub-period'))


def _b_first_of(ms, T, tone):
    return next((m for m in ms if T[m] == tone), None)


# ---------------------------------------------------------------- topic block
def _b_topic(ctx, q, start, ln, do, watch, why, i, do_extra=''):
    T, ms = ctx['T'], ctx['ms']
    sl = ms[start:start + ln]
    cnt = {t: sum(1 for m in sl if T[m] == t) for t in _b_CARE_ORDER}
    tone = _b_lead_of(cnt)
    S = A.mrange([m for m in sl if T[m] == 'strong'])
    M = A.mrange([m for m in sl if T[m] == 'mixed'])
    C = A.mrange([m for m in sl if T[m] == 'careful'])
    key = tone if tone != 'strong' else 'strong'
    if tone == 'mixed' and not S:
        key = 'mixed0'
    if tone == 'careful' and not S:
        key = 'careful0'
    if tone == 'mixed' and not S and not M:
        key = 'mixed'
    ph = _b_VF(_b_WHEN[key], i + ctx['n'], S=S, M=M, C=C)
    when = f"{A.mrange(sl)}: {cnt['strong']} strong, {cnt['mixed']} mixed, {cnt['careful']} careful. {ph}"
    lb = 'font:700 8.5px/1 var(--sans);letter-spacing:.1em;text-transform:uppercase;color:var(--gold);margin-right:4px'
    cell = 'font-size:11px;line-height:1.32;color:var(--body)'
    do = (do + ' ' + do_extra).strip()
    return (f'<div class="k-q k-q-{tone}" style="margin-top:6px;padding:6px 10px 7px"><div class="k-qh" style="font-size:13.5px"><span>{q}</span>{A.chip(tone)}</div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-top:3px"><div style="{cell}"><b style="{lb}">Do</b>{do}</div>'
            f'<div style="{cell}"><b style="{lb}">Watch</b>{watch}</div></div>'
            f'<div style="{cell};margin-top:3px"><b style="{lb}">Why</b>{why}</div>'
            f'<div style="{cell};margin-top:3px"><b style="{lb}">When</b>{when}</div></div>')


def _b_months_tiles(ctx, i):
    a, ttl = _b_NOUN[ctx['key']], _b_TITLES[ctx['key']]
    S = [m for m in ctx['ms'] if ctx['T'][m] == 'strong']
    C = [m for m in ctx['ms'] if ctx['T'][m] == 'careful']
    s_sub = '' if S else _b_V(_b_NO_STRONG, i, ctx['n']).format(a=a, A=ttl)
    c_sub = '' if C else _b_V(_b_NO_CARE, i, ctx['n']).format(a=a, A=ttl)
    return A.tiles([('Strong months', A.mrange(S) or 'None', s_sub), ('Careful months', A.mrange(C) or 'None', c_sub)])


def _b_bars(T, ms, label):
    sc = {'strong': 1.0, 'mixed': .58, 'careful': .22}
    col = {'strong': '#3E7D5A', 'mixed': '#C9A34E', 'careful': '#B4572B'}
    b = ''
    for k, m in enumerate(ms):
        h = 70 * sc[T[m]]
        x = 10 + k * 32
        b += (f'<rect x="{x}" y="{82 - h:.1f}" width="22" height="{h:.1f}" rx="4" fill="{col[T[m]]}"/>'
              f'<text x="{x + 11}" y="96" font-size="9" fill="#4C4A57" text-anchor="middle" font-family="Inter,sans-serif">{A.mshort(m)[0]}</text>')
    return (f'<div class="k-gx" style="height:120px"><div class="k-lead" style="margin:0 0 0 2px;font-style:italic">{label}</div>'
            f'<svg viewBox="0 0 394 100" width="100%" height="100" role="img" aria-label="{label}">{b}</svg></div>')


def _b_side_strip(label, T, ms):
    sub = {m: T[m] for m in ms}
    c = {t: sum(1 for m in ms if T[m] == t) for t in _b_CARE_ORDER}
    return (f'<div class="k-ans"><div class="k-ah"><span class="k-at">{label}</span>{A.chip(_b_lead_of(c))}</div>'
            f'<div class="k-lead">{c["strong"]} strong {_b_mw(c["strong"])}, {c["mixed"]} mixed {_b_mw(c["mixed"])}, {c["careful"]} careful {_b_mw(c["careful"])}</div>'
            f'{A.mini_strip(sub)}</div>')


def _b_the_read(ctx, i, use=True):
    t, key, wt = ctx['lead'], ctx['key'], ctx['wt']
    txt = _b_V(_b_READ[t], i, ctx['n']).format(A=_b_TITLES[key], a=_b_NOUN[key])
    if use and any(ctx['T'][m] == 'strong' for m in ctx['ms']):
        txt += f" In strong months: {_b_g(_b_STRONG_USE[key], wt)}"
    if use and any(ctx['T'][m] == 'careful' for m in ctx['ms']):
        txt += f" In careful months: {_b_g(_b_CARE_USE[key], wt)}"
    return A.callout('The read', txt, {'strong': 'good', 'mixed': 'note', 'careful': 'careful'}[t])


def _b_opener(ctx, i):
    t = ctx['lead']
    ld = _b_V(_b_LEAD[t], ctx['c'], ctx['n']).format(A=_b_TITLES[ctx['key']], a=_b_NOUN[ctx['key']])
    note = ''
    if ctx['key'] == 'career' and ctx['wt'] == 'business':
        note = '<p class="fine" style="margin-top:6px">You run a business, so these are your business months.</p>'
    return (f'<div style="margin-top:8px;display:flex;gap:10px;align-items:flex-start;text-align:left">{A.chip(t)}'
            f'<div style="font-size:12.5px;line-height:1.42;color:var(--body)">{ld}</div></div>{note}'
            f'{A.chapter_graphic(ctx["key"], ctx["T"])}{A.counts(ctx["T"])}{A.mini_strip(ctx["T"])}'
            f'{_b_months_tiles(ctx, i)}')


_b_CSS = ('<style>.k-cnt{padding:5px 6px}.k-cnt b{font-size:20px}.k-cnt span{margin-top:2px}.k-tiles,.k-cnts{margin-top:5px}.k-mini{margin-top:6px}'
       '.k-gx{margin-top:4px}.k-tile{padding:7px 10px}.k-tv{font-size:14.5px}.tw.k-sm td{padding:2px 7px}.tw.k-sm{margin-top:6px}.sr{padding:7px 0}.callout{margin-top:9px;padding:9px 13px}.callout p{font-size:12px;line-height:1.42}.scores{margin-top:6px}</style>')


def _b_ex(ctx):
    return f'<p class="fine" style="margin-top:4px">{_b_g(_b_EXAMPLE[ctx["key"]], ctx["wt"])}</p>'


def _b_page(ctx, idx, label, body):
    return A.card(_b_CSS + (f'<div class="exlabel" style="margin-top:2px">{label}</div>' if label != 'The answer' else '') + body, _b_FIRST_PAGE + idx,
                      A.part_label(2, 'Details'), _b_TITLES[ctx['key']])


# ---------------------------------------------------------------- chapters
def _b_career(ctx, idx):
    p, wt, n = ctx['p'], ctx['wt'], ctx['n']
    T, ms, c = ctx['T'], ctx['ms'], ctx['c']
    gl = _b_Gl()
    ctx['gl'] = gl
    bn, b = _b_basis(p, gl)
    sg, names, key, sent = _b_place(p, 10)
    w = _b__join([_b_WORKW[k] for k in key])
    why_work = (f"From your {bn} ({b}): your work {gl('the 12 parts of a chart', 'box')}, box 10, is {sg}. {sent}. "
                f"Traditionally read as work with {w}.")
    do_work = dict(job='Look for roles with this feel.', business='Look for offers with this feel.',
                   student='Look for courses with this feel.', home='Look for home work with this feel.')[wt]
    q1 = _b_topic(ctx, 'Kind of work that suits', 0, 11, do_work, 'Taking something only for the title.', why_work, c)
    q2 = _b_topic(ctx, _b_g(dict(job='Your next big step', business='Growing the business', student='Studies and first job',
                           home='Return to work or home income'), wt), 0, 6,
               _b_g(dict(job='Write down the one role you want next.', business='Pick one offer to grow.',
                      student='Pick one subject or skill to build.', home='Pick one way to earn that fits your day.'), wt),
               'Moving on every idea at once.', _b_sky_why(p, gl, ms[0:6], c + n), c + 1)
    a = _b_page(ctx, idx, 'The answer', _b_opener(ctx, c) + q1 + q2)
    # page B
    gl = _b_Gl()
    ctx['gl'] = gl
    q3 = _b_topic(ctx, _b_g(dict(job='Switch or stay', business='Change the plan or stay the course', student='Change course or stay',
                           home='Take a role or stay at home'), wt), 2, 6,
               _b_g(dict(job='List what you want from the next role first.', business='List what is working before you change it.',
                      student='List what you want from the course first.', home='List what you need from the next role first.'), wt),
               _b_g(dict(job='Leaving after one bad week.', business='Changing plans after one poor order.',
                      student='Dropping a course after one bad test.', home='Saying yes to the first offer.'), wt),
               _b_sky_why(p, gl, ms[2:8], c + n + 1), c + 2)
    q4 = _b_topic(ctx, _b_g(dict(job='Raise or thanks at work', business='Better pay for you and your name', student='Marks, awards and recognition',
                           home='Recognition for what you make'), wt), 6, 6,
               _b_g(dict(job='Show your work to the person who decides.', business='Show results to your best customers.',
                      student='Show your work to a teacher you trust.', home='Show what you make to people who buy it.'), wt),
               'Waiting to be noticed in silence.', _b_sky_why(p, gl, ms[6:12], c + n + 2), c + 3)
    s9, n9, _, _ = _b_place(p, 9)
    s12, n12, _, _ = _b_place(p, 12)
    f = lambda nn: _b__join(nn) if nn else 'no planet'
    found = n9 + n12
    if found:
        read = _b_V(['This is traditionally read as {t}.', 'Traditionally this points to {t}.'], c, n).format(t=_b_TRAVW[found[0]]).replace(
            'Traditionally this points to', 'Traditionally read as') if False else f"This is traditionally read as {_b_TRAVW[found[0]]}."
    else:
        read = _b_V(['Both boxes are empty, so no strong marker for a move shows.', 'Neither box holds a planet, so the months decide the timing.'], c, n)
    st = _b_first_of(ms, T, 'strong') or _b_first_of(ms, T, 'mixed')
    why_t = f"Box 9 (travel) is {s9} ({f(n9)}). Box 12 (living away) is {s12} ({f(n12)}). {read}"
    do_t = (f"Plan the trip or move for {A.mname(st)}." if st else 'Only prepare for now; all your months are careful.')
    q5 = _b_topic(ctx, 'Work travel or a move', 3, 7, do_t, 'Moving before the paperwork is ready.', why_t, c + 4)
    body = (f"{_b_ex(ctx)}{A.mini_strip(T)}{q3}{q4}{q5}{_b_the_read(ctx, c)}")
    return [a, _b_page(ctx, idx + 1, 'More questions', body)]


def _b_money(ctx, idx):
    p, wt, n = ctx['p'], ctx['wt'], ctx['n']
    T, ms, c = ctx['T'], ctx['ms'], ctx['c']
    gl = _b_Gl()
    ctx['gl'] = gl
    bn, b = _b_basis(p, gl)
    s2, s11 = _b_place(p, 2), _b_place(p, 11)
    why_src = (f"From your {bn} ({b}): your savings {gl('the 12 parts of a chart', 'box')}, box 2, is {s2[0]} ({_b_short(p, 2)}); "
               f"box 11 (income) is {s11[0]} ({_b_short(p, 11)}). "
               f"Traditionally read as money from {_b_SRCW[s11[2][0]]}, savings from {_b_SRCW[s2[2][0]]}.")
    q1 = _b_topic(ctx, _b_g(dict(job='Will money improve', business='Will business income improve', student='Will pocket money and fees work out',
                           home='Will home money improve'), wt), 0, 5,
               'Write down what comes in and goes out.', 'Spending that is written nowhere.', _b_sky_why(p, gl, ms[0:5], c + n), c)
    q2 = _b_topic(ctx, 'Where money comes from', 1, 10, 'Find which source pays best and feed it first.', 'Counting on one source only.', why_src, c + 1)
    a = _b_page(ctx, idx, 'The answer', _b_opener(ctx, c) + q1 + q2)
    gl = _b_Gl()
    ctx['gl'] = gl
    S = lambda a_, b_: [m for m in ms[a_:b_] if T[m] == 'strong']
    q3 = _b_topic(ctx, 'Months to save', 0, 7, 'Move money to savings first, before any spending.', 'Saving only what is left over.',
               _b_sky_why(p, gl, ms[0:7], c + n + 1), c + 2)
    q4 = _b_topic(ctx, 'Months for bigger spending', 4, 8, 'Plan large buys ahead and keep the papers in writing.',
               'Large spends in careful months without a plan.', _b_sky_why(p, gl, ms[4:12], c + n + 2), c + 3)
    ls = [m for m in ms[2:11] if T[m] == 'strong'] or [m for m in ms[2:11] if T[m] == 'mixed']
    lc = A.mrange([m for m in ms[2:11] if T[m] == 'careful'])
    loan_do = ('Read loan papers fully before you sign. ' + (f"If you must borrow, choose {A.mrange(ls)} and plan the repayments."
               if ls else 'No strong or mixed month shows here, so keep new loans for later.'))
    loan_w = 'Taking a loan only because it is offered.' + (f" Take extra care in {lc}." if lc else '')
    q5 = _b_topic(ctx, 'Loans: borrow with care, repay', 2, 9, loan_do, loan_w, _b_sky_why(p, gl, ms[2:11], c + n + 3), c + 4)
    b = f"{_b_ex(ctx)}{q3}{q4}{q5}{A.mini_strip(T)}"
    out = [a, _b_page(ctx, idx + 1, 'Saving and spending', b)]
    # page C: wealth
    gl = _b_Gl()
    ctx['gl'] = gl
    ys = [y['name'].split(' (')[0] for y in p['yogas']]
    ys = [y for y in ys if 'laks' not in y.lower()]
    wy = wealth_found(p)
    wc = gl('wealth combination')
    if wy:
        why_w = _b_V(['The {y} check finds {x}, a {r}. This is traditionally read as support for money and standing.',
                   'Found in your chart: {x}, a {r}. Your {y} check reads it as a money and standing pattern.'], c, n).format(
            x=_b__join(wy[:2]), r=gl('Raj-type yoga'), y=gl('yoga'))
        do_w = 'Use the support by planning around your strong months.'
    elif ys:
        why_w = (f"No Raj-type or Dhana pattern is found in your {wc} check. It does show {_b__join(ys[:2])}, "
                 f"a different kind of support, so your money months and planet period carry the rest.")
        do_w = 'Plan around your strong months, and lean on the strengths you do have.'
    else:
        why_w = (f"Your {wc} check finds none, and that is a kind answer, not a verdict. Your money months and your "
                 f"planet period carry the money story instead.")
        do_w = 'Plan around your strong months. Your steps matter more than any pattern.'
    q6 = _b_topic(ctx, 'Wealth combination', 3, 9, do_w, 'Treating a pattern as a promise.', why_w, c + 5)
    q6 = q6.replace(A.chip(_b_lead_of({t: sum(1 for m in ms[3:12] if T[m] == t) for t in _b_CARE_ORDER})), A.chip('note', 'FOUND' if wy else 'NOT FOUND'), 1)
    other = (_b_side_strip('Your business months', ctx['p']['areas']['business'], ms) if wt == 'business'
             else _b_side_strip('Family and shared money months', ctx['p']['areas']['family'], ms))
    cc = (f"{_b_bars(T, ms, 'Money by month')}{q6}{other}{_b_the_read(ctx, c + 2)}")
    out.append(_b_page(ctx, idx + 2, 'Wealth and the read', cc))
    return out


def wealth_found(p):
    """Wealth-type yogas found in person p (list of names, e.g. ['Neecha Bhanga Raja Yoga']); [] means none. Same test p.23 uses."""
    ys = [y['name'].split(' (')[0] for y in p['yogas']]
    ys = [y for y in ys if 'laks' not in y.lower()]
    return [y for y in ys if any(k in y.lower() for k in ('raja', 'raj ', 'dhana'))]


def _b_marriage(ctx, idx):
    p, wt, n = ctx['p'], ctx['wt'], ctx['n']
    T, ms, c = ctx['T'], ctx['ms'], ctx['c']
    gl = _b_Gl()
    ctx['gl'] = gl
    bn, b = _b_basis(p, gl)
    sg, names, key, sent = _b_place(p, 7)
    v = _b__sign_of(p, 'Venus')
    vl = next((r['strength_label'] for r in p['planet_table'] if r['planet'] == 'Venus'), 'Average').lower()
    why_tr = (f"From your {bn} ({b}): your partner {gl('the 12 parts of a chart', 'box')}, box 7, is {sg}. {sent}. "
              f"Traditionally read as {_b_PARTW[key[0]]}. Venus, the love planet, sits in {v} ({vl}).")
    m = p['manglik']
    has = str(m['status']).startswith('manglik')
    if has and m['cancelled']:
        ml = f"{gl('Manglik')} is present but a cancelling pattern is found" + (f" ({m['note']})" if m.get('note') else '') + '.'
    elif has:
        ml = f"{gl('Manglik')} is present and no cancelling pattern is found."
    else:
        ml = f"{gl('Manglik')} is not found in your chart."
    ml += ' The full box is on page 16.'
    q1 = _b_topic(ctx, 'Tone between people across the months', 0, 12, 'Say one kind thing a day to someone close.', 'Long silences.',
               _b_sky_why(p, gl, ms[0:12], c + n), c)
    q2 = _b_topic(ctx, 'Partnership traits', 0, 8, 'Talk early about what each person needs.', 'Expecting others to guess.', why_tr, c + 1)
    a = _b_page(ctx, idx, 'The answer', _b_opener(ctx, c) + q1 + A.callout('Manglik in one line', ml))
    gl = _b_Gl()
    ctx['gl'] = gl
    q3 = _b_topic(ctx, 'Months for important decisions', 1, 7, 'Talk big choices through in your strong months.',
               'Deciding big things in a hurry.', _b_sky_why(p, gl, ms[1:8], c + n + 1), c + 2)
    q4 = _b_topic(ctx, 'Months that need care in conversations', 5, 7, 'Listen fully, then answer.',
               'Replying in the heat of the moment.', _b_sky_why(p, gl, ms[5:12], c + n + 2), c + 3)
    body = f"{_b_ex(ctx)}{q2}{q3}{q4}{_b_the_read(ctx, c + 1)}"
    return [a, _b_page(ctx, idx + 1, 'Decisions and care', body)]


def _b_luck(ctx, idx):
    p, wt, n = ctx['p'], ctx['wt'], ctx['n']
    T, ms, c = ctx['T'], ctx['ms'], ctx['c']
    gl = _b_Gl()
    ctx['gl'] = gl
    bn, b = _b_basis(p, gl)
    sg, names, key, sent = _b_place(p, 9)
    j = _b__sign_of(p, 'Jupiter')
    jl = next((r['strength_label'] for r in p['planet_table'] if r['planet'] == 'Jupiter'), 'Average').lower()
    why_l = (f"From your {bn} ({b}): your luck {gl('the 12 parts of a chart', 'box')}, box 9, is {sg}. {sent}. "
             f"Traditionally read as {_b_LUCKW[key[0]]}. Jupiter, the luck planet, sits in {j} ({jl}).")
    dh, ss = p['dhaiya'], p['sade_sati']
    if ss['active']:
        sat = f"{gl('Sade Sati')} is on during these months."
    elif dh['active']:
        sat = f"{gl('Shani Dhaiya')} is on, ends {_b_fd(dh['ends'])} and returns {_b_fd(dh['restarts'])}."
    else:
        sat = 'No Sade Sati or Dhaiya spell is on in these months.'
    q1 = _b_topic(ctx, 'Bright spots', 1, 8, 'Say yes to open doors, then check the details.', 'Waiting for a perfect sign.', sat, c)
    q2 = _b_topic(ctx, 'The luck box of your chart', 2, 10, 'Ask an elder or teacher for their view.', 'Counting on luck without effort.', why_l, c + 1)
    q3 = _b_topic(ctx, 'Months for choices', 4, 7, 'Put your big choices in strong months. Purchases are on page 42.',
               'Choosing in a hurry.', _b_sky_why(p, gl, ms[4:12], c + n + 2), c + 2)
    a = _b_page(ctx, idx, 'The answer', _b_opener(ctx, c) + q1 + q2)
    # page B: turning points
    gl = _b_Gl()
    ctx['gl'] = gl
    qs = [f'{A.mshort(ms[k * 3])} to {A.mshort(ms[k * 3 + 2])}' for k in range(4)]
    import calendar
    _ly, _lm = int(ms[-1][:4]), int(ms[-1][5:7])
    _end = f'{calendar.monthrange(_ly, _lm)[1]} {A.mshort(ms[-1])}'
    segs = []
    for k in range(4):
        cc = {t: sum(1 for m in ms[k * 3:k * 3 + 3] if T[m] == t) for t in _b_CARE_ORDER}
        segs.append((qs[k], f'1 {A.mshort(ms[k * 3])}', _end, _b_lead_of(cc)))
    bar = A.tl_bar(segs)
    ev = {}
    for x in p['sign_changes']:
        if x['date'][:7] in ms:
            ev.setdefault((x['date'], x['from'], x['to']), []).append(x['planet'])
    rows = []
    for (d, f, t), pls in sorted(ev.items()):
        nt = _b_PLNOTE.get(pls[0], 'a planet')
        rows.append([_b_fd(d), _b__join(pls), f"{f} to {t}"])
    pp = p['planet_period']
    nxt = pp['next_sub'].split('/')[-1]
    inspan = pp['until'][:7] in ms
    per = (f"The {gl('sub-period')} {pp['sub']} ends on {_b_fd(pp['until'])}; {nxt} follows." if inspan else
           f"The {gl('sub-period')} {pp['sub']} runs past these 12 months, to {_b_fd(pp['until'])}.")
    tbl = A.table(['Date', 'Planet', 'Sign change'], rows, small=True) if rows else ''
    first = _b_first_of(ms, T, 'strong') or _b_first_of(ms, T, 'mixed') or ms[0]
    hab = next((r for r in sorted(p['planet_table'], key=lambda r: _b_RANK.get(r['strength_label'], 1)) if r['planet'] in _b_PL), None)
    why_h = (_b_V(['Your best-placed planet is {p} in {s}.', 'Your strongest planet is {p}, in {s}.', '{p} in {s} is your best-placed planet.'],
               c, n).format(p=hab['planet'], s=hab['sign']) if hab else 'Your planet table shows no outstanding planet.')
    do_h = (_b_PL[hab['planet']][1] if hab else 'Pick one small habit and keep it going.')
    q4 = _b_topic(ctx, 'Small fresh-start habits', 1, 9, do_h + f" Start in {A.mname(first)}.", 'Starting five habits at once.', why_h, c + 3)
    tp = f"<p class='fine' style='margin-top:6px'>{per}</p>"
    body = f"{bar}{tp}{tbl}{q3}{q4}{_b_the_read(ctx, c + 2, False)}"
    return [a, _b_page(ctx, idx + 1, 'Turning points', body)]


def _b_strengths(ctx, idx):
    p, wt, n = ctx['p'], ctx['wt'], ctx['n']
    T, ms, c = ctx['T'], ctx['ms'], ctx['c']
    gl = _b_Gl()
    ctx['gl'] = gl
    where = {}
    for h, cs in p['kundli'].items():
        for x in cs:
            where[_b_CODE[x]] = int(h)
    cand = [r for r in p['planet_table'] if r['planet'] in _b_PL]
    cand.sort(key=lambda r: (_b_RANK.get(r['strength_label'], 1), 0 if where.get(r['planet']) in (1, 4, 5, 7, 9, 10) else 1))
    rows = []
    for r in cand[:3]:
        pl = r['planet']
        if r['strength_label'] == 'Strong':
            why = 'sits in a strong sign (own or high)'
        elif where.get(pl) in (1, 4, 5, 7, 9, 10):
            why = f"sits in the {_b_ordn(where[pl])} box of your chart, a main box"
        else:
            why = 'sits in an average sign, so it is one to build'
        rows.append((f"{pl} in {r['sign']}", f"{why[0].upper() + why[1:]}. Adds {_b_PL[pl][0]}. Do: {_b_PL[pl][1]}"))
    mer = _b__sign_of(p, 'Mercury')
    ml = next((r['strength_label'] for r in p['planet_table'] if r['planet'] == 'Mercury'), 'Average').lower()
    what = dict(job='courses and new skills', business='training for you or your team', student='exams and courses',
                home='a course or a skill to earn from')[wt]
    qn = 'Study months: exams, courses and skills' if wt == 'student' else 'Months for learning: courses and skills'
    why_s = f"Mercury, the learning planet, sits in {mer} ({ml})."
    q1 = _b_topic(ctx, qn, 0, 10, f"Plan {what} for your strong months.", 'Putting off the hardest topic.', why_s, c)
    sr = (f"<p class='exlabel' style='margin-top:14px;text-align:left'>Your three strongest points</p>"
          f"{A.steps(rows)}")
    a = _b_page(ctx, idx, 'The answer', _b_opener(ctx, c) + sr)
    # page B
    act = [m for m in ms if T[m] == 'strong'] or [m for m in ms if T[m] == 'mixed'] or ms
    pick = [act[0], act[len(act) // 2], act[-1]]
    if len(set(pick)) < 3:
        pick = [act[0]] + [m for m in ms if m > act[0]][:2] if len(act) == 1 else pick
    top = next((r for r in cand if r['planet'] in _b_PL), None)
    s1 = _b_PL[top['planet']][1] if top else 'Pick one skill to build.'
    s2 = dict(job=_b_V(['Share one result at work.', 'Ask for one new task.', 'Write down what you learned.'], c, n),
              business=_b_V(['Test one new idea.', 'Review your numbers.', 'Add one skill to the team.'], c, n),
              student=_b_V(['Set a weekly study hour.', 'Review your marks.', 'Teach one topic to a friend.'], c, n),
              home=_b_V(['Set aside one hour a day for yourself.', 'Make one small thing to sell or share.', 'Write down what you learned.'], c, n))[wt]
    s3 = dict(job=_b_V(['Ask a senior for feedback.', 'List the skills your next role needs.', 'Join one group in your field.'], c, n),
              business=_b_V(['Ask three customers what to improve.', 'Write your next three goals.', 'Meet one person who runs a similar business.'], c, n),
              student=_b_V(['Make a revision plan for the hardest subject.', 'Try one past paper under time.', 'Pick one skill beyond the syllabus.'], c, n),
              home=_b_V(['Pick one skill to earn from.', 'Talk to one person who works from home.', 'Plan a small first order.'], c, n))[wt]
    stps = [(f"{A.mname(pick[0])}.", s1), (f"{A.mname(pick[1])}.", s2), (f"{A.mname(pick[2])}.", s3)]
    gl = _b_Gl()
    ctx['gl'] = gl
    skills = dict(job='a skill your next role asks for', business='one skill that grows sales',
                  student='one skill beyond your syllabus', home='one skill you can earn from')[wt]
    fs = [m for m in ms if T[m] == 'strong'][:3] or [m for m in ms if T[m] == 'mixed'][:3]
    q2 = _b_topic(ctx, 'Skills to build first', 3, 8, f"Start {skills}" + (f" in {A.mrange(fs)}." if fs else ' with small steps.'),
               'Collecting courses you never finish.', _b_sky_why(p, gl, ms[0:8], c + n + 1), c + 1)
    body = (f"<p class='exlabel' style='margin-top:6px;text-align:left'>Three growth steps, each tied to a month</p>{A.steps(stps)}"
            f"{q1}{q2}{_b_the_read(ctx, c)}")
    return [a, _b_page(ctx, idx + 1, 'Growth steps', body)]


_b_FN = dict(career=_b_career, money=_b_money, marriage=_b_marriage, luck=_b_luck, strengths=_b_strengths)


def _b__pages(p):
    _b__USED.clear()
    wt = p['work_type'] if p['work_type'] in _b_WT else 'job'
    n = len(p['name'])
    ms = [m['ym'] for m in p['span_months']]
    want = (p.get('first_open_topic') or '').lower().split(' ')[0]
    order = list(_b_KEYS)
    for k in _b_KEYS:
        if _b_TITLES[k].lower().startswith(want):
            order.remove(k)
            order.insert(0, k)
            break
    out = []
    for k in order:
        area = {'career': 'business' if wt == 'business' else 'career', 'money': 'money', 'marriage': 'marriage'}.get(k)
        T = {m: (p['areas'][area] if area else p['tones'])[m] for m in ms}
        cnt = {t: sum(1 for m in ms if T[m] == t) for t in _b_CARE_ORDER}
        ctx = dict(p=p, wt=wt, n=n, ms=ms, T=T, cnt=cnt, lead=_b_lead_of(cnt), key=k, c=_b_KEYS.index(k), gl=None)
        out += _b_FN[k](ctx, len(out))
    return out


def _b_pages(p):
    return [A.scope(h, 'm2b') for h in _b__pages(p)]


# ======================================================================
# SECTION 2c: the 12 month cards (cards 30-41)
# Pages 30-41: the 12 month cards (PART 2). Every fact comes from p; wording is picked by an occurrence counter plus the name length, so no pool line is used more than twice per person (pools hold 6+ lines) and two people differ.
# ======================================================================
_c_AREAS = [('money', 'Money'), ('career', 'Career'), ('business', 'Business'), ('family', 'Family'), ('marriage', 'Marriage')]
_c_WORD = {'strong': 'strong', 'mixed': 'mixed', 'careful': 'careful'}
_c_RANK = {'strong': 2, 'mixed': 1, 'careful': 0}
# work_type changes wording only: (work noun, business noun)
_c_WT = {'job': ('your job', 'a side business or business plan'), 'business': ('your work', 'your business'),
      'student': ('your studies', 'a small side project'), 'home': ('your daily work at home', 'a small business idea')}

_c_OPEN = {
    'strong': ['{M} is traditionally read as a strong month, so things you start now can go further.',
               'The chart marks {M} as a strong month, and effort put in shows.',
               'A strong month: {M} gives a good push to what you have held back.',
               '{M} comes up strong, a good time to move on ideas that were waiting.',
               'Strong signs in {M}: work and plans find more support than usual.',
               '{M} is traditionally read as one of the better months, a strong one.'],
    'mixed': ['{M} is traditionally read as a mixed month, with good days and plain days.',
              'A mixed month: {M} has wins and a few things that need a second look.',
              '{M} sits in the middle, so take it week by week.',
              'The chart marks {M} as mixed, so judge the month at its end.',
              'Mixed signs in {M}: some doors open and some wait.',
              '{M} is traditionally read as a mixed month, so keep plans flexible.'],
    'careful': ['{M} is traditionally read as a careful month, so keep plans simple.',
                'A careful month: {M} asks you to check things twice.',
                'The chart marks {M} as careful, and small sure steps beat big moves.',
                '{M} comes up careful, so go step by step and keep some room.',
                'Careful signs in {M}: choose sure steps over quick ones.',
                '{M} is traditionally read as one of your careful months, so think before big choices.']}
_c_MIX_ALL = ['All five areas read {t} together.', 'Money, Career, Business, Family and Marriage all read {t}.',
           'The five areas agree this month, and all read {t}.', 'No area stands apart; each one reads {t}.',
           'Every area, from Money to Marriage, reads {t}.', 'The five areas match the month, and all read {t}.']
_c_MIX = {
    'sc': ['The best marks fall on {S}; take extra care with {C}.', 'Look to {S} first and go gently with {C}.',
           'Lean on {S} this month and give {C} a second look.', 'Most support shows in {S}, and most care is needed in {C}.',
           'Put effort into {S}, and double-check {C}.', 'Use {S} for your big moves and keep {C} simple.'],
    'sm': ['The best marks fall on {S}; the rest read mixed.', 'Look to {S} first; the other areas are mixed.',
           'Lean on {S} this month; the others are mixed.', 'Most support shows in {S}, with mixed marks in the rest.',
           'Put effort into {S}; the others need a second look.', 'Use {S} for your big moves and take the others as they come.'],
    'mc': ['Take extra care with {C}; the other areas are mixed.', 'Go gently with {C}; the rest read mixed.',
           'The careful marks fall on {C}, and the rest are mixed.', 'Keep {C} simple this month; the others are mixed.',
           'Double-check {C}; the other areas sit in the middle.', 'Give {C} a second look, and take the others as they come.']}

_c_LINES = {  # (area, tone) -> 6 lines; {w} work noun, {b} business noun, {B} business noun capitalised
    ('money', 'strong'): ['Money matters move smoothly; a good month to pay bills and plan savings.',
                          'Income and spending line up well, so choices about money come easier.',
                          'A good month to ask for what you are owed or to start a saving habit.',
                          'Money talks go well, and a fair deal is easier to find.',
                          'A good time to sort old payments and set a simple budget.',
                          'Money comes in steadily and choices are clear; compare prices before you buy.'],
    ('money', 'mixed'): ['Money is up and down: some good days, some weeks to watch spending.',
                         'Keep a simple list of what comes in and what goes out.',
                         'Small buys are fine; put off big ones for a stronger month.',
                         'A mixed month for money, so check each bill before you pay it.',
                         'Money can feel uneven; split big costs into smaller steps.',
                         'Gains and costs come close together, so write both down.'],
    ('money', 'careful'): ['Hold back on big money moves and keep a small amount aside.',
                           'Read every money paper twice before you sign it.',
                           'Skip new loans and risks; keep to the plain, needed costs.',
                           'Guard your money: avoid lending and avoid quick deals.',
                           'Costs may come early, so spend only on needs this month.',
                           'Do not lend money or trust a deal that sounds too good.'],
    ('career', 'strong'): ['Good days for {w}: your effort is seen and counts.',
                           'A strong time to ask for a bigger role or a new task in {w}.',
                           'Talks with seniors go well, and {w} moves forward.',
                           'A good month to start the hard task you have put off in {w}.',
                           'New chances can show up in {w}; say yes after reading the details.',
                           'Work moves with less effort; finish the big pieces of {w} early.'],
    ('career', 'mixed'): ['{W} has good days and flat days, so keep to your routine.',
                          'Work in {w} moves ahead in jumps; check at month end.',
                          'Some tasks in {w} stall, so ask early when you are stuck.',
                          'A fair month for {w}: do the plain tasks well.',
                          'Mixed signals around work; confirm each plan in writing.',
                          'Small wins in {w}, with a few delays on the way.'],
    ('career', 'careful'): ['Keep {w} simple: three main tasks a day and no big changes.',
                            'Avoid big moves in {w}; finish what is already open.',
                            'Check each task in {w} twice before you hand it over.',
                            'Choose quiet, steady effort in {w} and save big asks for later.',
                            'Do not quit or switch in a rush; think it over for a week.',
                            'Delays can happen in {w}, so keep some spare time before deadlines.'],
    ('business', 'strong'): ['A good month to start or grow {b}.',
                             'People respond well, and {b} can move forward.',
                             'New deals around {b} are easier to close after you read the terms.',
                             'Plans for {b} gain pace; put the first step in writing.',
                             'A strong time to test a new idea for {b} in small form.',
                             'Good support from others; share the plan for {b} early.'],
    ('business', 'mixed'): ['{B} moves in small steps, so do not expect big jumps.',
                            'Keep costs for {b} low and watch what actually sells.',
                            'Some deals for {b} firm up and others slip; follow up twice.',
                            'A mixed month for {b}: finish old orders before new ones.',
                            'Test before you spend on {b}.',
                            'A few partners are unsure, so ask them plainly.'],
    ('business', 'careful'): ['Hold off on new spending for {b} and protect what you have.',
                              'Do not sign a big deal for {b} without a second opinion.',
                              'Delays and changes can come up for {b}, so keep plans simple.',
                              'Avoid new partners and new loans for {b}.',
                              'Keep {b} small this month and check every number.',
                              'Keep records for {b} tidy; small mistakes can slip in.'],
    ('family', 'strong'): ['A warm month at home; a good time for a family plan or a talk.',
                           'Elders and relatives are supportive, so ask for their view.',
                           'Good moments with family; a small get-together goes well.',
                           'Family matters settle well, and old differences are easier to fix.',
                           'A good month to plan something together, like a trip or a function.',
                           'Home feels easy; share news you have been holding back.'],
    ('family', 'mixed'): ['Family is mixed: warm days and a few short talks that need a softer tone.',
                          'Some family plans move and others wait, so be ready to change your plan.',
                          'Listen first; small matters can grow if answered in a hurry.',
                          'A mixed month at home, so keep the daily routine fixed.',
                          'A relative may need your time; plan it in advance.',
                          'Talks at home go better in the morning than late at night.'],
    ('family', 'careful'): ['Take extra care in family talks; keep your words short and your voice low.',
                            'Avoid old arguments and leave big family decisions for a better month.',
                            'A family matter may need time, so do not force an answer.',
                            'Keep promises to family small and clear.',
                            'Misunderstandings come easily, so check what was meant.',
                            'Give family some time before you reply to a sharp message.'],
    ('marriage', 'strong'): ['Close bonds are warm; a good month for an honest talk.',
                             'A good time to meet, plan, or take a step with a partner.',
                             'Understanding comes easily, so say what you feel.',
                             'Good days for a date, a trip, or a plan for two.',
                             'Talks with a partner go well, and family on both sides is supportive.',
                             'A good month to settle a plan that was waiting.'],
    ('marriage', 'mixed'): ['Close ties are mixed: good days with some quiet ones.',
                            'Say it plainly and do not wait for the other person to guess.',
                            'Keep plans for two flexible, because one may need to move.',
                            'A fair month for the heart; small gestures count more than big ones.',
                            'Talk about money plans together before spending.',
                            'Some distance, some closeness; go day by day.'],
    ('marriage', 'careful'): ['Take care in close talks: pick a quiet time and listen first.',
                              'Do not decide big things about a partner in a rush.',
                              'Small misunderstandings may grow, so clear them the same day.',
                              'Keep plans for two simple and say sorry early if needed.',
                              'Avoid comparing your bond with others; give it time.',
                              'Leave big promises for a better month.']}

_c_DO = {'strong': ['Start the one task that matters most, early in the month.', 'Ask for the thing you have been meaning to ask for.',
                 'Read offers in full, then say yes to a good one.', 'Use the best days for work that needs most effort.',
                 'Plan the next three months on paper while the mood is good.', 'Finish a pending job before you take a new one.'],
      'mixed': ['Do the plain, needed jobs first and leave extras for good days.', 'Split big tasks into small parts.',
                'Keep one fixed hour each day for your main work.', 'Ask early when you are not sure.',
                'Check your list at the end of each week.', 'Write the next step down before you sleep.'],
      'careful': ['Keep each day to three main tasks.', 'Write down each big choice and sleep on it for one night.',
                  'Keep important talks short and clear.', 'Finish what is already open before you take new work.',
                  'Ask someone you trust to look over big papers.', 'Keep a small buffer in your money and your time.']}
_c_DO_TAIL = ['Your best use of the month: {A}.', 'Give {A} your first hour of effort.', 'Start with {A}, where the month is kindest.',
           'Let {A} lead your plans.', 'Put {A} at the top of your list.', 'Spend your best days on {A}.']
_c_WATCH = {'strong': ['Do not spread yourself over too many things.', 'Do not promise more than you can do.',
                    'Do not make big choices in one rush.', 'Easy days can make you skip planning, so keep a short list.',
                    'Do not overspend because the month feels good.', 'Say thanks to those who help, because good months pass fast.'],
         'mixed': ['Mixed messages from others are likely.', 'Your energy may dip on the plainer days.',
                   'Jobs can grow bigger than planned.', 'Choices made only to end a doubt often need a redo.',
                   'Ask once more before you sign or pay.', 'Give it a day before you reply to a hard message.'],
         'careful': ['Hurried money choices can go wrong.', 'Sharp words said in a rush are hard to take back.',
                     'Promises made to please others are hard to keep.', 'Plans that rest on one person only can fall through.',
                     'Pause and read it again before you sign.', 'Keep a record of what was agreed.']}
_c_WATCH_TAIL = ['Look twice at {A}.', 'Keep {A} simple.', 'Go gently with {A}.', 'Do not rush {A}.',
              'Double-check {A}.', 'Give {A} a second look.']
_c_THROUGH = ['Fix a small daily routine and keep to it.', 'Do the hardest task in the morning, while you are fresh.',
           'Say no kindly to extra work.', 'Keep days short on plans and long on finishing.',
           'Talk it over with a friend or family member.', 'Tick off one small win each evening.']
_c_EASE = ['It gets easier from {M}.', 'Things get easier from {M}.', 'The tone lifts from {M}.', 'From {M} the months read better.', 'Easier months start in {M}.', 'A better month comes in {M}.']
_c_LINK = ['Details on p.43.', 'See p.43 for the careful months together.', 'All the careful months are laid out on p.43.',
        'p.43 has the careful months side by side.', 'More on p.43, with dates.', 'Read p.43 for how the careful months link up.']
_c_NEXT = ['Next up, {N}: a {t} month; {x}.', 'Looking ahead, {N} reads as a {t} month, and {x}.',
        'Then comes {N}, a {t} month: {x}.', 'Coming next is {N}, marked as a {t} month; {x}.',
        'After this, {N} is a {t} month, and {x}.', 'The next card is {N}, a {t} month: {x}.']
_c_LAST = 'This card closes the 12 months. {M} and after are not covered here, and a new report can pick up from this point.'
_c_NEXT_ALL = ['all five areas read {t}', 'every area reads {t}', 'the five areas agree on {t}']

_c_SIGN = ['On {D}, {X}. {P} (p.47).', 'Sign change, {D}: {X}. {P} (p.47).', '{D} brings a sign change: {X}. {P} (p.47).',
        'The sky shifts on {D}: {X}. {P} (p.47).', '{X} on {D}. {P} (see p.47).', 'Mark {D}: {X}. {P} (p.47).']
_c_PERIOD = ['On {D} the planet period changes: {X} (see p.48).', 'Planet period change, {D}: {X} (p.48).',
          '{D} starts a new part of your planet period: {X} (p.48).', 'The planet period moves on {D}: {X} (see p.48).',
          'On {D}, {X}. This changes the timing chapter, not the sky (p.48).', 'Mark {D} for a planet period change: {X} (p.48).']
_c_DH_END = ["Saturn's Dhaiya ends on {D}, as Saturn leaves the {K} sign from your Moon sign (p.49).",
          'On {D} the Dhaiya stage ends; Saturn leaves the {K} sign from your Moon sign (p.49).',
          'Dhaiya ends on {D}: Saturn moves off the {K} sign from your Moon sign (p.49).',
          '{D} closes the Dhaiya, which sat on the {K} sign from your Moon sign (p.49).',
          'The Dhaiya stage finishes on {D}, once Saturn leaves the {K} sign (p.49).',
          'Mark {D}: Dhaiya ends, with Saturn off the {K} sign from your Moon sign (p.49).']
_c_DH_START = ["Saturn's Dhaiya starts again on {D}, with Saturn back on the {K} sign from your Moon sign (p.49).",
            'On {D} the Dhaiya stage begins again; Saturn is on the {K} sign from your Moon sign (p.49).',
            'Dhaiya returns on {D}: Saturn is back on the {K} sign from your Moon sign (p.49).',
            '{D} reopens the Dhaiya on the {K} sign from your Moon sign (p.49).',
            'The Dhaiya stage starts again on {D}, as Saturn returns to the {K} sign (p.49).',
            'Mark {D}: Dhaiya starts again, with Saturn on the {K} sign from your Moon sign (p.49).']
_c_SADE = ["Sade Sati moves into its {G} on {D}, Saturn's long stay near your Moon sign (p.49).",
        'On {D} a new Sade Sati stage begins: the {G} (p.49).',
        'Sade Sati reaches its {G} on {D} (see p.49).',
        'The {G} of Sade Sati starts on {D} (p.49).',
        '{D} marks the {G} of Sade Sati (see p.49).',
        'Mark {D}: Sade Sati changes to its {G} (p.49).']
_c_NONE = ['No sign change this month: {S}.', 'No sign change this month, so {S}.', 'No sign change this month; {S}.',
        'No sign change this month, which means {S}.', 'No sign change this month, and {S}.', 'No sign change this month: in the sky, {S}.']


_c_TIGHT = ('<style>.page .k-ar{padding:5px 9px;font-size:11px;line-height:1.3}.page .nbox{margin-top:7px;padding:8px 12px}'
         '.page .nbox p,.page .callout p{font-size:11.5px;line-height:1.4}.page .callout{margin-top:8px;padding:8px 12px}'
         '.page .k-area{margin-top:7px}.page .head{margin-bottom:0}</style>')


def _c__d(ds):
    return f'{int(ds[8:10])} {A.mshort(ds[:7])}'


def _c__join(xs):
    xs = list(xs)
    return xs[0] if len(xs) == 1 else ', '.join(xs[:-1]) + ' and ' + xs[-1]


def _c__sky_state(p, ym):
    """Saturn / Jupiter sign at the end of ym, from the p['sign_changes'] list only."""
    out = []
    for pl in ('Saturn', 'Jupiter'):
        ch = sorted((s for s in p.get('sign_changes') or [] if s['planet'] == pl), key=lambda s: s['date'])
        if not ch:
            continue
        sign = ch[0]['from']
        for s in ch:
            if s['date'][:7] <= ym:
                sign = s['to']
        out.append((pl, sign))
    if not out:
        return 'the main planets keep their signs'
    (a, sa), rest = out[0], out[1:]
    return f'{a} stays in {sa}' + ''.join(f' and {pl} in {sg}' for pl, sg in rest)


_c_DIFF = {'up': ['Overall this is a {t} month, but {G}, so some areas can move ahead.',
               'Overall {t}; {G}, so use those areas first.',
               'The month as a whole reads {t}, while {G}; lean on those areas.'],
        'down': ['Overall this is a {t} month, but {G}, so keep big steps for later.',
                 'Overall {t}; {G}, so go gently with big choices.',
                 'The month as a whole reads {t}, while {G}; keep big steps small.'],
        'both': ['Overall this is a {t} month, and the areas differ: {G}.',
                 'Overall {t}; {G}.',
                 'The month as a whole reads {t}, while {G}.']}


def _c__groups(at, t):
    """'Money, Career and Family read strong and Marriage reads mixed' for every area that differs from the overall tone t."""
    parts = []
    for tone in ('strong', 'mixed', 'careful'):
        if tone == t:
            continue
        xs = [l for a, l in _c_AREAS if at[a] == tone]
        if len(xs) == 5:
            parts.append(f'all five areas read {_c_WORD[tone]}')
        elif xs:
            parts.append(f"{_c__join(xs)} {'reads' if len(xs) == 1 else 'read'} {_c_WORD[tone]}")
    if len(parts) == 2 and not any(v == t for v in at.values()):
        last = [l for a, l in _c_AREAS if at[a] == [x for x in ('strong', 'mixed', 'careful') if x != t][1]]
        if len(last) > 1:
            parts[1] = f"the other {['','','two','three','four'][len(last)]} read " + parts[1].rsplit(' ', 1)[1]
    return ' and '.join(parts)


def _c__mix(at, tpl_pick, t):
    S = [l for a, l in _c_AREAS if at[a] == 'strong']
    M = [l for a, l in _c_AREAS if at[a] == 'mixed']
    C = [l for a, l in _c_AREAS if at[a] == 'careful']
    same = sum(1 for v in at.values() if v == t)
    if same == 5:
        return tpl_pick('all', _c_MIX_ALL).format(t=_c_WORD[t])
    if same < 3:  # areas mostly differ from the month's own overall tone: say so plainly, never "move as one"
        hi = any(_c_RANK[v] > _c_RANK[t] for v in at.values())
        lo = any(_c_RANK[v] < _c_RANK[t] for v in at.values())
        return tpl_pick('diff', _c_DIFF['both' if hi and lo else 'up' if hi else 'down']).format(t=_c_WORD[t], G=_c__groups(at, t))
    if S and C:
        return tpl_pick('sc', _c_MIX['sc']).format(S=_c__join(S), C=_c__join(C))
    if S:
        return tpl_pick('sm', _c_MIX['sm']).format(S=_c__join(S))
    return tpl_pick('mc', _c_MIX['mc']).format(C=_c__join(C))


def _c__lead_trail(at):
    best = max(_c_RANK[v] for v in at.values())
    worst = min(_c_RANK[v] for v in at.values())
    L = [l for a, l in _c_AREAS if _c_RANK[at[a]] == best]
    T = [l for a, l in _c_AREAS if _c_RANK[at[a]] == worst]
    return (None if best == worst else _c__join(L)), (None if best == worst else _c__join(T)), best, worst


def _c__next_x(at, t):
    L, T, best, worst = _c__lead_trail(at)
    if L is None:
        a = list(at.values())[0]
        return _c_NEXT_ALL[len(_c_WORD[t]) % 3].format(t=_c_WORD[a]) if _c_WORD[a] == _c_WORD[t] else f'its five areas all read {_c_WORD[a]}'
    one = lambda x: ' and ' not in x and ',' not in x
    if best == 2 and worst == 0:
        return f"{L} {'leads' if one(L) else 'lead'} and {T} {'needs' if one(T) else 'need'} care"
    if best == 2:
        return f"{L} {'leads' if one(L) else 'lead'} the way"
    return f"{T} {'needs' if one(T) else 'need'} care"


def _c__pages(p):
    n = len(p['name'])
    cnt = {}

    def pick(key, pool):
        c = cnt.get(key, 0)
        cnt[key] = c + 1
        return pool[(c + n) % len(pool)]

    yms = [m['ym'] for m in p['span_months']]
    tones_span = {y: p['tones'][y] for y in yms}
    w, b = _c_WT.get(p.get('work_type'), _c_WT['job'])
    B = b[0].upper() + b[1:]
    out = []
    for i, ym in enumerate(yms):
        t = p['tones'][ym]
        M = A.mname(ym)
        at = {a: p['areas'][a][ym] for a, _ in _c_AREAS}
        L, T, best, worst = _c__lead_trail(at)
        # lead paragraph: tone sentence + area mix sentence
        lead = pick('open-' + t, _c_OPEN[t]).format(M=M) + ' ' + _c__mix(at, pick, t)
        rows = []
        for a, lab in _c_AREAS:
            line = pick(a + t[0] + at[a], _c_LINES[(a, at[a])]) if False else pick((a, at[a]), _c_LINES[(a, at[a])])
            rows.append((lab, at[a], line.format(w=w, W=w[0].upper() + w[1:], b=b, B=B)))
        # In the sky
        ev = []
        by_date = {}
        for s in p.get('sign_changes') or []:
            if s['date'][:7] == ym:
                by_date.setdefault(s['date'], []).append(s)
        for d in sorted(by_date):
            X = _c__join(f"{s['planet']} moves from {s['from']} to {s['to']}" for s in by_date[d])
            P = f"From your Moon sign ({p['moon_sign']}): " + _c__join(
                f"{s['planet']} is in sign {(SIGNS.index(s['to']) - SIGNS.index(p['moon_sign'])) % 12 + 1}" for s in by_date[d])
            ev.append(pick('sign', _c_SIGN).format(D=_c__d(d), X=X, P=P))
        pp = p.get('planet_period') or {}
        if pp.get('next_start') and pp['next_start'][:7] == ym and pp.get('next_sub'):
            nm, _, ns = pp['next_sub'].partition('/')
            ns = ns or nm
            if nm != pp.get('main'):
                X = f"the main period changes from {pp.get('main')} to {nm}"
            else:
                X = f"the sub-period changes from {pp.get('sub')} to {ns} inside your {pp.get('main')} period"
            ev.append(pick('period', _c_PERIOD).format(D=_c__d(pp['next_start']), X=X))
        dh = p.get('dhaiya') or {}
        K = (str(dh.get('kind') or '').split() or ['4th'])[0]
        if dh.get('ends') and dh['ends'][:7] == ym:
            ev.append(pick('dhe', _c_DH_END).format(D=_c__d(dh['ends']), K=K))
        if dh.get('restarts') and dh['restarts'][:7] == ym:
            ev.append(pick('dhs', _c_DH_START).format(D=_c__d(dh['restarts']), K=K))
        for c in (p.get('sade_sati') or {}).get('change_dates') or []:
            d, st = (c['date'], c.get('stage')) if isinstance(c, dict) else (c, None)
            if d[:7] == ym:
                g = str(st or 'next stage')
                g = g if 'stage' in g else g + ' stage'
                ev.append(pick('sade', _c_SADE).format(D=_c__d(d), G=g))
        if not ev:
            ev.append(pick('none', _c_NONE).format(S=_c__sky_state(p, ym)))
        # Do / Watch
        do = pick('do' + t, _c_DO[t])
        if L and best == 2:
            do += ' ' + pick('dot', _c_DO_TAIL).format(A=L)
        watch = pick('wa' + t, _c_WATCH[t])
        if T and worst < 2:
            watch += ' ' + pick('wat', _c_WATCH_TAIL).format(A=T)
        # next month
        if i + 1 < len(yms):
            nx = yms[i + 1]
            nat = {a: p['areas'][a][nx] for a, _ in _c_AREAS}
            nxt = pick('next', _c_NEXT).format(N=A.mname(nx), t=_c_WORD[p['tones'][nx]], x=_c__next_x(nat, p['tones'][nx]))
        else:
            _y, _m = int(yms[-1][:4]), int(yms[-1][5:7])
            nxt = _c_LAST.format(M=A.mname(f'{_y + (_m == 12)}-{_m % 12 + 1:02d}'))
        body = (_c_TIGHT + f'<div style="margin-top:8px">{A.chip(t, _c_WORD[t].upper() + " MONTH")}</div>'
                f'<p class="lead" style="font-size:12.5px;margin-top:6px">{lead}</p>'
                f'{A.mini_strip(tones_span, highlight=ym, months=yms)}'
                f'{A.area_table(rows)}'
                f'{A.box("In the sky", " ".join(ev))}'
                f'{A.box("Do and Watch", "<b>Do:</b> " + do + " <b>Watch:</b> " + watch)}')
        if t == 'careful':
            later = [y for y in yms[i + 1:] if p['tones'][y] != 'careful']
            ease = ' ' + pick('ease', _c_EASE).format(M=A.mname(later[0])) if later else ''
            body += A.callout('Get through it', pick('thr', _c_THROUGH) + ease + ' ' + pick('link', _c_LINK), 'careful')
        body += f'<p class="fine" style="margin-top:8px">{nxt}</p>'
        out.append(A.card(body, 30 + i, A.part_label(2, 'Month by month'), M))
    return out


def _c_pages(p):
    return [A.scope(h, 'm2c') for h in _c__pages(p)]


# ======================================================================
# SECTION 2d: big decisions, careful months, quarter plan (cards 42-44)
# Annual Report mock, pages 41 to 43 (PART 2 details): big decisions, careful months, quarter plan. pages(p) -> 3 html strings. All person facts come from p. Act-months rule: a strong month outside a Dhaiya stage or a dated Sade Sati stage. Sade Sati on with no stage dates: no month is removed for it, and the page says so.
# ======================================================================
_d_MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
_d_AREA_NAME = {'money': 'money', 'career': 'career', 'business': 'business', 'family': 'family', 'marriage': 'marriage'}
_d_PART = A.part_label(2, 'Details')


def _d__d(s):
    return f'{int(s[8:10])} {_d_MON[int(s[5:7]) - 1]} {s[:4]}'


def _d__seed(p):
    return sum(ord(c) for c in p['first_name'])


def _d__nxt(ym):
    y, m = int(ym[:4]), int(ym[5:])
    return f'{y + (m == 12)}-{m % 12 + 1:02d}'


def _d__order(p):
    return [m['ym'] for m in p['span_months']]


def _d__ss_end(p):
    """Last Sade Sati stage date as 'YYYY-MM-DD', or None when the data has no dates."""
    ss = p.get('sade_sati') or {}
    if not ss.get('active'):
        return None
    ds = [(x.get('date') if isinstance(x, dict) else x) for x in (ss.get('change_dates') or [])]
    ds = [x for x in ds if x]
    return max(ds) if ds else None


def _d__inside(p, ym):
    s, e = ym + '-01', _d__nxt(ym) + '-01'
    spans = []
    se = _d__ss_end(p)
    if se:
        spans.append(('0000-00-00', se))
    dh = p.get('dhaiya') or {}
    if dh.get('active'):
        spans.append(('0000-00-00', dh.get('ends') or '9999-99-99'))
    if dh.get('restarts'):
        spans.append((dh['restarts'], '9999-99-99'))
    return any(s < b and e > a for a, b in spans)


def _d__area_bad(p, area, ym):
    ar = (p.get('areas') or {}).get(area)
    return bool(ar) and ar.get(ym) == 'careful'


def _d__months(p, tone, area=None):
    return [y for y in _d__order(p) if p['tones'][y] == tone and not _d__inside(p, y) and not (area and _d__area_bad(p, area, y))]


_d_ACT_AREA = {'gold': None, 'property': 'family', 'vehicle': 'money', 'move': 'family'}
_d_RANKS = {'strong': 0, 'mixed': 1, 'careful': 2}


def act_months(p, kind):
    """ONE rule for pages 10 and 42: strong months outside Dhaiya or Sade Sati stages (family or money not careful, by kind)."""
    return _d__months(p, 'strong', _d_ACT_AREA[kind])


def act_any(p):
    return sorted({y for k in _d_ACT_AREA for y in act_months(p, k)})


def left_out(p):
    """Strong months dropped only because a Dhaiya or Sade Sati stage covers them."""
    return [y for y in _d__order(p) if p['tones'][y] == 'strong' and _d__inside(p, y)]


def stage_months(p):
    return [y for y in _d__order(p) if _d__inside(p, y)]


def _d_act_chip_text(n):
    return f'{n} STRONG {"MONTH" if n == 1 else "MONTHS"} TO ACT'


def _d_tone_of(vals):
    """ONE quarter/topic tone rule: the tone most months have; on a tie the more careful tone."""
    vals = list(vals)
    if not vals:
        return 'mixed'
    return max(_d_RANKS, key=lambda k: (vals.count(k), _d_RANKS[k]))


def _d_tie_note(vals):
    vals = list(vals)
    c = {k: vals.count(k) for k in _d_RANKS}
    top = max(c.values()) if vals else 0
    tied = [k for k in _d_RANKS if c[k] == top]
    if len(tied) == 3:
        return 'three-way tie, the more careful tone is shown'
    return ('tie: ' + ', '.join(f'{c[k]} {k}' for k in tied)) if len(tied) > 1 else ''


def _stage_line(p):
    dh = p.get('dhaiya') or {}
    ss = p.get('sade_sati') or {}
    bits = []
    if ss.get('active'):
        se = _d__ss_end(p)
        stg = f' ({ss["stage"]} stage)' if ss.get('stage') else ''
        if se:
            bits.append(f'Your Sade Sati{stg} runs until {_d__d(se)}, so earlier months were left out.')
        else:
            bits.append(f'Your Sade Sati{stg} is on, but we have no stage dates for it, so no month was left out for it.')
    if dh.get('active') and dh.get('ends'):
        t = f'Your Dhaiya stage ends on {_d__d(dh["ends"])}'
        t += f' and comes back on {_d__d(dh["restarts"])}.' if dh.get('restarts') else '.'
        bits.append(t + ' Months inside it were left out.')
    elif dh.get('active'):
        bits.append('Your Dhaiya stage is on through this whole report, so every month is inside it and none could fit the rule.')
    elif dh.get('restarts'):
        bits.append(f'Your Dhaiya stage starts on {_d__d(dh["restarts"])}. Months from then were left out.')
    return ' '.join(bits) or 'No Dhaiya or Sade Sati stage touches this report for you, so no month was left out.'


def _d__hstrip(p, act):
    """Mini strip, one box per month, rule months outlined."""
    cells = ''
    for y in _d__order(p):
        hl = ' k-hl' if y in act else ''
        cells += f'<div class="k-mc{hl}"><i class="k-{p["tones"][y]}"></i><span>{A.mshort(y)}</span></div>'
    return f'<div class="k-mini" style="grid-template-columns:repeat(12,1fr)">{cells}</div>'


# ---------------------------------------------------------------- page 41
_d_LEAD41 = ['{n}, outlined boxes show the months that fit each rule.', '{n}, the outlined months fit the rule for each decision.',
          '{n}, your best months to act are outlined below.', '{n}, outlined boxes are the months where the rule is met.']
_d_NOFIT = ['No month fits this rule.', 'No month meets this rule now.', 'None of your months fit this rule.', 'This rule finds no month now.']
_d_FALLBACK = ['Next best: {m}.', 'Nearest, mixed: {m}.', 'If urgent: {m}.', 'Mixed months: {m}.']
_d_NOFALL = ['Nothing near fits.', 'No near fit either.', 'No mixed month fits.', 'Nothing close fits.']
_d_TOPICS = [('Gold', 'gold', 'Rule: a strong month outside your stages.',
           'Check the hallmark. Get the making charge in writing.'),
          ('Property', 'property', 'Rule: strong, outside your stages, family not careful.',
           'Check the papers with a lawyer before you pay.'),
          ('Vehicle', 'vehicle', 'Rule: strong, outside your stages, money not careful.',
           'Check the insurance and the total cost.'),
          ('A move', 'move', 'Rule: strong, outside your stages, family not careful.',
           'Fix dates in writing and give notice on time.')]


def _d_p41(p):
    i = _d__seed(p)
    blocks = ''
    for k, (name, kind, rule, buy) in enumerate(_d_TOPICS):
        area = _d_ACT_AREA[kind]
        act = act_months(p, kind)
        if act:
            chip = A.chip('strong', _d_act_chip_text(len(act)))
            when = f'<b>Best</b> {A.mrange(act)}.'
            tone = 'strong'
        else:
            fb = _d__months(p, 'mixed', area)
            chip = A.chip('note', 'NO MONTH FITS')
            when = _d_NOFIT[(i + k) % 4] + ' ' + (_d_FALLBACK[(i + k) % 4].format(m=A.mrange(fb)) if fb else _d_NOFALL[(i + k) % 4])
            tone = 'note'
        blocks += (f'<div class="k-q k-q-{tone}" style="margin-top:6px;padding:6px 10px"><div class="k-qh"><span>{name}</span>{chip}</div>'
                   f'{_d__hstrip(p, act)}'
                   f'<div class="k-ql"><span>{when}</span></div>'
                   f'<div class="k-ql"><span>{rule}</span></div>'
                   f'<div class="k-ql"><span><b>Before</b> {buy}</span></div></div>')
    note = A.callout('Your stages', _stage_line(p) + ' Both are Saturn stages (see p.49).')
    body = (f'<p class="lead" style="font-size:12.5px;line-height:1.4;margin-top:6px">{_d_LEAD41[i % 4].format(n=p["first_name"])}</p>' + blocks
            + note.replace('margin-top:15px', 'margin-top:6px'))
    return A.card(body, 42, _d_PART, 'Big decisions in detail')


# ---------------------------------------------------------------- page 42
_d_LEAD42 = ['{n}, each careful month: what, when it gets easier, what to do.', '{n}, one block per careful month, with when it gets easier.',
          '{n}, these months are read as asking for more care.', '{n}, go step by step in these months.']
_d_WHAT = ['Keep plans simple.', 'Leave big moves for later.', 'Finish old tasks, start few.', 'Double check dates and papers.',
        'Keep spending and promises small.', 'Go easy on big choices.']
_d_DO = ['Read every paper twice before you sign it.', 'Keep big spending for a later month.', 'Finish old tasks before you start new ones.',
      'Check dates and bookings twice.', 'Talk to someone you trust before a big choice.', 'Keep your plans short and clear.',
      'Write down your three main tasks each week.', 'Put big purchases on a list for next month.']
_d_GOODNEWS = ['Good news: no month in this report is a careful month.', 'No careful months this time. Every month is strong or mixed.',
            'Nothing in this report is marked careful. That helps with planning.', 'No month here is careful, so you have room to plan.']
_d_HABITS = [('Read before you sign.', 'Take a day with every paper, even in a strong month.'),
          ('Plan the spend.', 'Write down big costs a week before you pay.'),
          ('Keep one list.', 'Three main tasks a day is enough.'),
          ('Check the dates.', 'Confirm bookings and deadlines in writing.')]


def _d__events(p, ym):
    out = [f'{c["planet"]} moves into {c["to"]} on {_d__d(c["date"])}' for c in p.get('sign_changes', []) if c['date'][:7] == ym]
    dh = p.get('dhaiya') or {}
    if dh.get('ends') and dh['ends'][:7] == ym:
        out.append(f'your Dhaiya stage ends on {_d__d(dh["ends"])}')
    if dh.get('restarts') and dh['restarts'][:7] == ym:
        out.append(f'your Dhaiya stage comes back on {_d__d(dh["restarts"])}')
    return out


_d_EVERY = ['Careful for every topic.', 'Every topic reads careful.', 'All topics read careful this month.']


def _d__areas_bad(p, ym):
    drop = 'career' if p.get('work_type') == 'business' else 'business'
    ar = {a: v for a, v in (p.get('areas') or {}).items() if a != drop}
    bad = [_d_AREA_NAME[a] for a, v in ar.items() if v.get(ym) == 'careful']
    return ['every topic'] if ar and len(bad) == len(ar) else bad


def _d__eases(p, run):
    nx = _d__nxt(run[-1])
    if nx in _d__order(p):
        return f'from {A.mname(nx)}, which is a {p["tones"][nx]} month'
    return f'after {A.mname(run[-1])}, when this report ends'


def _d_p42(p):
    i = _d__seed(p)
    order = _d__order(p)
    care = [y for y in order if p['tones'][y] == 'careful']
    mixed = [y for y in order if p['tones'][y] == 'mixed']
    runs, cur = [], []
    for y in order:
        if y in care:
            cur.append(y)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    if not care:
        body = f'<p class="lead" style="margin-top:12px">{_d_GOODNEWS[i % 4]}</p>'
        if mixed:
            rows = [(A.mname(y), ', '.join(_d__areas_bad(p, y)) or 'no single topic stands out; read papers twice') for y in mixed[:8]]
            body += ('<p class="lead" style="font-size:14px;margin-top:8px">Mixed months still ask for normal care. Here are the ones to watch:</p>'
                     + A.table(['Mixed month', 'Topics to watch'], rows, small=True))
            if len(mixed) > 8:
                body += f'<p class="fine" style="margin-top:6px">{len(mixed) - 8} more mixed months: {A.mrange(mixed[8:])}.</p>'
        else:
            body += '<p class="lead" style="font-size:14px;margin-top:8px">Every month in this report is strong, so there are no mixed months to watch either.</p>'
            body += A.counts({y: p['tones'][y] for y in order})
        body += A.steps(_d_HABITS)
        body += A.callout('Good habits for any month', 'These four habits help in strong months too. They cost nothing and keep choices clear.')
        return A.card(body, 43, _d_PART, 'Careful months in detail')
    body = f'<p class="lead" style="font-size:12.5px;line-height:1.4;margin-top:6px">{_d_LEAD42[i % 4].format(n=p["first_name"])}</p>'
    if len(care) <= 5:
        for k, y in enumerate(care):
            run = next(r for r in runs if y in r)
            bad = _d__areas_bad(p, y)
            watch = ('' if len(care) >= 4 else _d_WHAT[(i + k) % 6] + ' ') + (((_d_EVERY[(i + k) % 3] if bad[0] == 'every topic' else 'Careful for ' + ', '.join(bad) + '.')) if bad else 'No single topic stands out.')
            left = len(run) - 1 - run.index(y)
            if len(run) == 1:
                when = f'Gets easier {_d__eases(p, run)}.'
            elif left:
                when = f'Month {run.index(y) + 1} of {len(run)} in a row ({A.mrange(run)}). {left} more careful {"month follows" if left == 1 else "months follow"}.'
            else:
                when = f'Last of {len(run)} careful months in a row. Gets easier {_d__eases(p, run)}.'
            lines = {'Watch': watch, 'When': when, 'Do': _d_DO[(i + 2 * k) % 8]}
            ev = _d__events(p, y)
            if ev:
                lines['Why'] = 'Sign change: ' + '; '.join(ev) + '.'
            body += A.qblock(A.mname(y), 'careful', lines).replace('class="k-q k-q-careful"', 'class="k-q k-q-careful" style="margin-top:6px;padding:7px 12px"')
    else:
        rows = [(A.mname(y), ', '.join(_d__areas_bad(p, y)) or 'all topics') for y in care]
        body += A.table(['Careful month', 'Careful for'], rows, small=True)
        body += ''.join(f'<p class="fine" style="margin-top:6px;text-align:left"><b>{A.mrange(r)}:</b> gets easier {_d__eases(p, r)}. {_d_DO[(i + j) % 8]}</p>'
                        for j, r in enumerate(runs))
    return A.card(body, 43, _d_PART, 'Careful months in detail')


# ---------------------------------------------------------------- page 43
_d_THEME = {'strong': ['A quarter with room to move ahead', 'A quarter that opens doors', 'A quarter to start what you have put off', 'A quarter to act with confidence'],
         'careful': ['A quarter to keep things simple', 'A quarter for clear plans', 'A quarter to go step by step', 'A quarter to finish, not start'],
         'mixed': ['A mixed quarter: choose with care', 'A quarter of ups and downs', 'A quarter to pick your moves', 'A quarter to keep options open']}
_d_STEP = {'strong': ['Start the task you have put off.', 'Ask, apply or propose now.', 'Meet people who matter to your plans.', 'Save a part of what you earn.',
                   'Make the big decision you have been weighing.', 'Share your plan with someone who can help.'],
        'careful': ['Check every paper twice.', 'Keep big spending for later.', 'Finish old tasks first.', 'Keep plans short and clear.',
                    'Write dates down and confirm them.', 'Ask for advice before a big choice.'],
        'mixed': ['Do one thing at a time.', 'Keep your options open.', 'Make a short list and stick to it.', 'Choose people and plans with care.',
                  'Test a small step before a big one.', 'Review your list every Sunday.']}
_d_LEAD43 = ['{n}, your 12 months in four blocks of three.', '{n}, your plan quarter by quarter from {S}.',
          '{n}, four quarters: look for strong months first.', '{n}, each quarter has a theme and two steps.']


def _d__qnote(p, g):
    ev = []
    for y in g:
        ev += _d__events(p, y)
    return ('<b>Dates:</b> ' + '; '.join(ev[:2]) + '.') if ev else ''


def _d_p43(p):
    i = _d__seed(p)
    ms = _d__order(p)
    body = f'<p class="lead" style="font-size:12.5px;line-height:1.4;margin-top:6px">{_d_LEAD43[i % 4].format(n=p["first_name"], S=A.mname(ms[0]))}</p>'
    body += A.mini_strip({y: p['tones'][y] for y in ms}, months=ms)
    for q in range(4):
        g = ms[q * 3:q * 3 + 3]
        t = [p['tones'][y] for y in g]
        dom = _d_tone_of(t)
        st = [y for y in g if p['tones'][y] == 'strong']
        ca = [y for y in g if p['tones'][y] == 'careful']
        s2 = 'careful' if ca else 'strong' if st else 'mixed'
        a = _d_STEP[dom][(i + 2 * q) % 6]
        b = _d_STEP[s2][(i + 2 * q + 1) % 6] if s2 != dom else _d_STEP[dom][(i + 2 * q + 3) % 6]
        label = f'{A.mshort(g[0])} to {A.mname(g[-1])}' if g[0][:4] == g[-1][:4] else f'{A.mname(g[0])} to {A.mname(g[-1])}'
        lines = [f'<div class="k-ql"><span><b>Strong</b> {A.mrange(st) or "none"}. <b style="margin-left:6px">Careful</b> {A.mrange(ca) or "none"}.'
                 + (f' <i>({_d_tie_note(t)})</i>' if _d_tie_note(t) else '') + '</span></div>',
                 f'<div class="k-ql"><span><b>Try</b> 1. {a} 2. {b}</span></div>']
        n = _d__qnote(p, g)
        if n:
            lines.append(f'<div class="k-ql"><span>{n}</span></div>')
        body += (f'<div class="k-q k-q-{dom}" style="margin-top:6px;padding:6px 10px"><div class="k-qh"><span>{label}: {_d_THEME[dom][(i + q) % 4]}</span>'
                 f'{A.chip(dom)}</div>{"".join(lines)}</div>')
    return A.card(body, 44, _d_PART, 'Quarter-by-quarter plan')


def _d__pages(p):
    return [_d_p41(p), _d_p42(p), _d_p43(p)]



_d_TIGHT = ('<style>.page .head{margin-top:5px}.page .rule{margin:8px 0 0}.page .lead{font-size:13.5px;line-height:1.42;margin-top:8px}'
         '.page .exlabel{margin-top:8px!important}.page .callout{margin-top:8px;padding:8px 12px}.page .callout p{font-size:11.5px;line-height:1.4}'
         '.page .callout .ch{margin-bottom:3px}.page .nbox{margin-top:7px;padding:8px 12px}.page .nbox p{font-size:11.5px;line-height:1.4}'
         '.page .k-cnt{padding:5px 6px}.page .k-tiles,.page .k-cnts{margin-top:5px}.page .k-mini{margin-top:6px}.page .k-tile{padding:6px 10px}'
         '.page .k-tv{font-size:14.5px}.page .tw.k-sm td{padding:2px 7px}.page .tw.k-sm{margin-top:6px}.page .k-sm,.page .k-sm td{font-size:11px}.page .k-ql{margin-top:3px;font-size:11px;line-height:1.35}.page .k-qh{font-size:13.5px}</style>')


def _d_pages(p):
    return [A.scope(_d_TIGHT + h, 'm2d') for h in _d__pages(p)]


def page_titles(p):
    """PAGE_TITLES_P2 with the 12 month-card titles taken from this report's span."""
    t = list(PAGE_TITLES_P2)
    t[17:29] = [A.mname(m['ym']) for m in p['span_months']]
    return t


# ====================================================================
# PUBLIC ENTRY
# ====================================================================
def pages(p):
    """The 32 card HTML strings, base cards 13 to 44, in order."""
    out = _a_pages(p) + _b_pages(p) + _c_pages(p) + _d_pages(p)
    assert len(out) == 32
    return out


if __name__ == '__main__':
    import json, sys
    assert len(PAGE_TITLES_P2) == 32
    if len(sys.argv) > 1:
        assert len(pages(json.load(open(sys.argv[1])))) == 32
    print('annual_report_p2: 32 titles ok')
