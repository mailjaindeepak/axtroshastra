"""Annual Report, PART 3 (Astrology guide), base cards 45 to 54. pages(p) -> list of html cards.
Generic text is fixed; every Yours line and table cell that depends on the chart is read from p (annual.compute_annual()["facts"]).
Card numbers and every see-p.NN reference are BASE 54-card numbers; the assembler remaps."""
import datetime as _dt
import math
import re as _re
import annual_assets as A

SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
OWNER = ['Mars', 'Venus', 'Mercury', 'Moon', 'Sun', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Saturn', 'Jupiter']
PLANET = {'Su': 'Sun', 'Mo': 'Moon', 'Ma': 'Mars', 'Me': 'Mercury', 'Ju': 'Jupiter', 'Ve': 'Venus', 'Sa': 'Saturn', 'Ra': 'Rahu', 'Ke': 'Ketu'}
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
PARTS = [('Self and looks', 'you, your looks and how you start things'),
         ('Money and speech', 'savings, family and the way you speak'),
         ('Courage and siblings', 'effort, courage, brothers and sisters'),
         ('Home and mother', 'home, mother and feeling settled'),
         ('Children and study', 'study, children and creative work'),
         ('Daily work and obstacles', 'daily tasks, rivals and loans'),
         ('Partners', 'marriage and business partners'),
         ('Sudden change, shared money', 'surprises, shared money, hidden things'),
         ('Luck and father', 'luck, teachers, father, long journeys'),
         ('Career and name', 'your job, status and how people see you'),
         ('Gains and friends', 'income, goals and friends'),
         ('Rest and far places', 'sleep, spending and living far away')]
SHORT = ['Self', 'Money', 'Courage', 'Home', 'Study,\nchildren', 'Daily\nwork', 'Partners', 'Sudden\nchange', 'Luck', 'Career', 'Gains', 'Rest']
EYEBROW = A.part_label(3, 'Astrology guide')
STYLE = ('<style>.g3r{width:100%;display:grid;grid-template-columns:84px 1fr;gap:8px;text-align:left;padding:3px 2px;border-bottom:1px solid var(--line)}'
         '.g3t{font-family:var(--serif);font-size:11.5px;font-weight:600;color:var(--ink);line-height:1.25}'
         '.g3d{font-size:10px;line-height:1.32;color:var(--body)}'
         '.g3y{color:var(--ink)}.g3y b,.g3p{font:700 8px/1.4 var(--sans);letter-spacing:.1em;text-transform:uppercase;color:var(--gold)}'
         '.g3p{white-space:nowrap}'
         '.g3l{font:700 9px/1 var(--sans);letter-spacing:.12em;color:var(--gold);margin-top:5px;padding-left:2px}'
         '.pb{width:100%;text-align:left;margin-top:6px;background:var(--box-fill);border:1px solid var(--box-line);border-radius:11px;padding:5px 10px}'
         '.pb h3{font-family:var(--serif);font-size:13px;font-weight:600;color:var(--ink);display:flex;justify-content:space-between;align-items:center;gap:8px}'
         '.pb p{font-size:10.5px;line-height:1.38;color:var(--body);margin-top:2px}.pb p.y{color:var(--ink)}'
         '.pb p b,.pb em{font:700 8px/1.4 var(--sans);letter-spacing:.1em;text-transform:uppercase;color:var(--gold);font-style:normal}'
         '.qa{width:100%;text-align:left;margin-top:7px}.qa h3{font-family:var(--serif);font-size:13px;font-weight:600;color:var(--ink)}'
         '.qa p{font-size:11px;line-height:1.4;color:var(--body);margin-top:1px}'
         '.dt2 td{vertical-align:top}.dt2 small{display:block;font-size:9.5px;color:var(--muted);margin-top:1px}'
         '.t3 td{padding:3px 6px!important}.t3 small{font-size:8.5px!important}.t3{font-size:10.5px!important}.mo td{background:var(--gold-callout)}</style>')


def _d(s):
    return f'{int(s[8:10])} {MON[int(s[5:7]) - 1]} {s[:4]}'


def _ds(s):
    return f'{int(s[8:10])} {MON[int(s[5:7]) - 1]}'


def _start(p):
    return p.get('rising_sign') or p['moon_sign']


def _box_of(p, code):
    return next((h for h, v in p['kundli'].items() if code in v), None)


def _cap(s):
    return s[:1].upper() + s[1:]


def _plist(names):
    return ', '.join(names[:-1]) + ' and ' + names[-1] if len(names) > 1 else (names[0] if names else '')


def _stage(p):
    """Sade Sati stage as plain words, '' when off. Accepts 1/2/3, 'first'.. or 'rising/peak/setting'."""
    ss = p.get('sade_sati') or {}
    if not ss.get('active'):
        return ''
    s = str(ss.get('stage') or '').lower()
    for k, w in (('1', 'first'), ('first', 'first'), ('rising', 'first'), ('2', 'second'), ('second', 'second'), ('peak', 'second'),
                 ('3', 'third'), ('third', 'third'), ('setting', 'third')):
        if k in s:
            return w
    return 'on'


def _sade_yours(p):
    st = _stage(p)
    if not st:
        return 'not on in your 12 months.'
    return 'on now.' if st == 'on' else f'on now, in the {st} stage.'


def _dhaiya_yours(p):
    dh = p.get('dhaiya') or {}
    if dh.get('active'):
        t = f'on now. Saturn is in the {str(dh["kind"]).split(" (")[0]} sign from your Moon sign.'
        if dh.get('ends'):
            t += f' It pauses on {_d(dh["ends"])}'
            t += f' and starts again on {_d(dh["restarts"])}.' if dh.get('restarts') else '.'
        return t
    if dh.get('restarts'):
        return f'not on now. It starts on {_d(dh["restarts"])}.'
    return 'not on in your 12 months.'


def _dhaiya_short(p):
    dh = p.get('dhaiya') or {}
    if dh.get('active'):
        return f'on now, until {_d(dh["ends"])}.' if dh.get('ends') else 'on now.'
    return f'starts {_d(dh["restarts"])}.' if dh.get('restarts') else 'not on in your 12 months.'


def _manglik(p):
    m = p.get('manglik') or {}
    st = str(m.get('status') or '').lower()
    on = bool(m.get('from_moon') or (p.get('rising_sign') and m.get('from_lagna')))
    if 'not' in st or st in ('none', 'no'):
        on = False
    note = (m.get('note') or '').replace('aspects', 'looks at').replace('aspect', 'look at')
    return on, bool(m.get('cancelled')), note or None


def _manglik_yours(p):
    on, canc, note = _manglik(p)
    if not on:
        return 'not present.'
    if canc:
        return 'present, and a cancellation applies' + (f': {note.rstrip(".")}.' if note else '.')
    return 'present, with no cancellation.'


def _has(p, *keys):
    return [y['name'] for y in p.get('yogas') or [] if any(k in y['name'].lower() for k in keys)]


def _yoga_yours(p, *keys):
    return 'present.' if _has(p, *keys) else 'not in your chart.'


def _wealth_names(p):
    """Same rule as p23 (pages_2b_chapters): Raj or Dhana yogas, Lakshmi yoga left out."""
    try:
        try:
            from annual_report_p2 import wealth_found
        except ImportError:
            wealth_found = _wealth_found_local
        r = wealth_found(p)
        if isinstance(r, (list, tuple)):
            return [str(x).split(' (')[0] for x in r]
        if isinstance(r, str) and r:
            return [r.split(' (')[0]]
    except Exception:
        pass
    ys = [y['name'].split(' (')[0] for y in p.get('yogas') or []]
    ys = [y for y in ys if 'laks' not in y.lower()]
    return [y for y in ys if any(k in y.lower() for k in ('raja', 'raj ', 'dhana'))]


def _wealth_found_local(p):
    ys = [y['name'].split(' (')[0] for y in p.get('yogas') or []]
    ys = [y for y in ys if 'laks' not in y.lower()]
    return [y for y in ys if any(k in y.lower() for k in ('raja', 'raj ', 'dhana'))]


def _wealth_yours(p):
    w = _wealth_names(p)
    return f'found: {_plist(w[:2])}.' if w else 'not in your chart.'


def _sign_of(p, planet):
    return next((r['sign'] for r in p['planet_table'] if r['planet'] == planet), '')


def _counts(p):
    t = [p['tones'][m['ym']] for m in p['span_months']]
    return t.count('strong'), t.count('mixed'), t.count('careful')


# ---------- page 44: how a chart is read ----------
def _diagram(p):
    ctr = [(150, 75), (75, 25), (25, 75), (75, 150), (25, 225), (75, 275), (150, 225), (225, 275), (275, 225), (225, 150), (275, 75), (225, 25)]
    moon_box = _box_of(p, 'Mo')
    g = ('<rect x="2" y="2" width="296" height="296" fill="#FFFDF8" stroke="#C9A34E" stroke-width="1.6"/>'
         '<polygon points="150,2 298,150 150,298 2,150" fill="none" stroke="#C9A34E" stroke-width="1.2"/>'
         '<line x1="2" y1="2" x2="298" y2="298" stroke="#C9A34E" stroke-width="1.2"/><line x1="298" y1="2" x2="2" y2="298" stroke="#C9A34E" stroke-width="1.2"/>'
         '<polygon points="150,2 225,75 150,150 75,75" fill="#F3E6C8" stroke="#C9A34E" stroke-width="1.2"/>')
    for i, (x, y) in enumerate(ctr, 1):
        lab = SHORT[i - 1].split('\n')
        t = f'<text x="{x}" y="{y - 7 - 5 * (len(lab) - 1)}" text-anchor="middle" font-size="13" font-weight="700" fill="#2B2622" font-family="Georgia,serif">{i}</text>'
        for k, w in enumerate(lab):
            t += f'<text x="{x}" y="{y + 4 + 9 * k}" text-anchor="middle" font-size="8.2" fill="#6B6258" font-family="sans-serif">{w}</text>'
        g += t
    if moon_box:
        x, y = ctr[moon_box - 1]
        g += f'<circle cx="{x + 30 if moon_box in (1, 4, 7, 10) else x + 22}" cy="{y - 12}" r="6.5" fill="#fff" stroke="#B4572B" stroke-width="1.3"/><text x="{x + 30 if moon_box in (1, 4, 7, 10) else x + 22}" y="{y - 9}" text-anchor="middle" font-size="7.5" font-weight="700" fill="#B4572B" font-family="sans-serif">Mo</text>'
    return f'<div class="k-gx" style="height:auto;padding:6px"><svg viewBox="0 0 300 300" width="100%" style="max-height:200px" role="img" aria-label="The 12 boxes of a chart">{g}</svg></div>'


def p44(p):
    rs, mn = p.get('rising_sign'), p['moon_sign']
    mb = _box_of(p, 'Mo')
    if rs:
        yours = (f'Your birth time was given, so box 1 is your rising sign, <b>{rs}</b>. Your Moon sign is <b>{mn}</b> '
                 f'and your Moon sits in box {mb}.')
    else:
        yours = (f'Your birth time is not sure, so we count from your Moon sign, <b>{mn}</b>. Box 1 is {mn}. '
                 'This is the Moon-sign path. Read this way, the Moon is always in box 1.')
    body = ('<p class="lead">Every word in this report, in one place.</p>'
            '<p class="fine" style="margin-top:2px">A birth chart is a map of the sky at the minute you were born. It has 12 boxes. '
            'Each box is one part of life.</p>'
            + _diagram(p)
            + '<p class="fine" style="margin-top:4px">Boxes are counted from box 1 and go round to the left.</p>'
            + A.tiles([('Rising sign', 'The sign coming up in the east', 'It sets box 1. It needs your exact birth time.'),
                           ('Moon sign', 'The sign your Moon was in', 'It stays the same for about two days, so a small time error rarely moves it.')])
            + A.callout('Why birth time matters', 'The rising sign changes about every two hours. A wrong time can move every sign in the 12 boxes. '
                            'When the time is not sure, we count from the Moon sign instead.')
            + A.callout('In your chart', yours, 'good'))
    return A.card(STYLE + body, 45, EYEBROW, 'How a chart is read')


# ---------- page 45: the nine planets ----------
JOBS = {'Sun': ('Sun', 'Your sense of self, name and confidence', 'Career', 19),
        'Moon': ('Moon', 'Your mind, moods and feelings', 'Marriage', 24),
        'Mars': ('Mars', 'Drive, courage and push', 'Career', 19),
        'Mercury': ('Mercury', 'Talking, learning, trade and thinking', 'Money, Strengths', '21, p.28'),
        'Jupiter': ('Jupiter', 'Growth, learning and good advice', 'Luck', 26),
        'Venus': ('Venus', 'Love, comfort and nice things', 'Marriage, Money', 24),
        'Saturn': ('Saturn', 'Effort, time and work that pays off later', 'Career', 19),
        'Rahu': ('Rahu', 'A strong pull toward something new', 'Sign changes', 18),
        'Ketu': ('Ketu', 'A pull to let go and look inward', 'Sign changes', 18)}


def p45(p):
    rows = []
    for r in p['planet_table']:
        j = JOBS.get(r['planet'])
        if not j:
            continue
        s = r.get('strength_label')
        tag = {'Strong': 'strong here', 'Needs care': 'needs care here'}.get(s, '')
        rows.append([f'<b>{j[0]}</b>', j[1], f'{r["sign"]}' + (f'<small>{tag}</small>' if tag else ''), f'{j[2]}<small>p.{j[3]}</small>'])
    body = ('<p class="lead">Nine planets, nine jobs.</p>'
            '<p class="fine" style="margin-top:2px">Rahu and Ketu are two points in the sky, always opposite each other.</p>'
            + A.table(['Planet', 'Its job in plain words', 'Yours: sign', 'Chapter it touches'], rows, small=True).replace('<table class="tw k-sm">', '<table class="tw k-sm dt2">')
            + A.callout('How planet strength is read', 'A planet is strong in its home sign or best sign. It needs care in its worst sign. Other signs are ordinary.'))
    return A.card(STYLE + body, 46, EYEBROW, 'The nine planets')


# ---------- page 46: sign by sign ----------
def p46(p):
    base = _start(p)
    s0 = SIGNS.index(base)
    mb = _box_of(p, 'Mo')
    rows = ''
    for n in range(1, 13):
        sg = (s0 + n - 1) % 12
        pls = ', '.join(PLANET[c] for c in p['kundli'].get(n, [])) or '-'
        cls = ' class="mo"' if n == mb else ''
        rows += (f'<tr{cls}><td><b style="color:var(--ink);font-weight:500">{n}. {PARTS[n - 1][0]}</b><small>{PARTS[n - 1][1]}</small></td>'
                 f'<td>{SIGNS[sg]}<small>owner {OWNER[sg]}</small></td><td>{pls}</td></tr>')
    head = ''.join(f'<th>{h}</th>' for h in ('Box and part of life', 'Sign', 'Planets there'))
    fine = (f'Counting starts from your rising sign, {base}.' if p.get('rising_sign')
            else f'Your birth time is not sure, so counting starts from your Moon sign, {base}.')
    body = ('<p class="lead">The 12 parts of a chart, sign by sign.</p>'
            f'<table class="tw k-sm dt2 t3"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>'
            f'<p class="fine" style="margin-top:8px">{fine} The shaded row holds your Moon. '
            'Boxes 1, 4, 7 and 10 are the corner boxes, also called key spots. To use the table, find a part of life, then see which planets sit there.</p>')
    return A.card(STYLE + body, 47, EYEBROW, 'Sign by sign')


# ---------- page 47: how timing is read ----------
def _timeline(p):
    sm = p['span_months']
    d0 = _dt.date(int(sm[0]['ym'][:4]), int(sm[0]['ym'][5:]), 1)
    ly, lm = int(sm[-1]['ym'][:4]), int(sm[-1]['ym'][5:])
    d1 = _dt.date(ly + (lm == 12), lm % 12 + 1, 1)
    X0, X1, W = 84, 384, 390
    span = (d1 - d0).days

    def x(s):
        d = _dt.date.fromisoformat(s)
        return X0 + (X1 - X0) * max(0, min(span, (d - d0).days)) / span

    G, Y, R, T = '#3E7D5A', '#C9A34E', '#B4572B', '#E8DFCB'
    rows = ['Planet period', 'Rahu', 'Ketu', 'Jupiter', 'Saturn', 'Shani Dhaiya', 'Sade Sati']
    H = 30 + 24 * len(rows)
    s = ''
    for i, m in enumerate(sm):
        xx = X0 + (X1 - X0) * i / 12
        s += (f'<line x1="{xx:.1f}" y1="22" x2="{xx:.1f}" y2="{H - 4}" stroke="#E8DFCB" stroke-width="1"/>'
              f'<text x="{xx + 12.5:.1f}" y="15" text-anchor="middle" font-size="9" fill="#6B6258" font-family="sans-serif">{MON[int(m["ym"][5:]) - 1][0]}</text>')
    for i, r in enumerate(rows):
        y = 30 + 24 * i
        s += f'<text x="2" y="{y + 15}" font-size="9.5" fill="#2B2622" font-family="sans-serif" font-weight="600">{r}</text>'
        s += f'<rect x="{X0}" y="{y + 6}" width="{X1 - X0}" height="14" rx="3" fill="{T}" opacity=".45"/>'

    def bar(i, a, b, col, label, dash=False):
        y = 30 + 24 * i + 6
        xa, xb = x(a), x(b)
        st = f'stroke="{R}" stroke-dasharray="3 2" stroke-width="1.3" fill="#F8E6DB"' if dash else f'fill="{col}"'
        s_ = f'<rect x="{xa:.1f}" y="{y}" width="{max(2, xb - xa):.1f}" height="14" rx="3" {st}/>'
        if xb - xa > 34:
            s_ += f'<text x="{(xa + xb) / 2:.1f}" y="{y + 10}" text-anchor="middle" font-size="8.5" fill="{"#B4572B" if dash else "#fff"}" font-family="sans-serif">{label}</text>'
        return s_
    end = d1.isoformat()
    first = d0.isoformat()
    pp = p['planet_period']
    if pp['until'] > first and pp['until'] < end:
        s += bar(0, first, pp['until'], Y, f'{pp["main"]} / {pp["sub"]}')
        s += bar(0, pp['until'], end, '#9C8447', pp['next_sub'].replace('/', ' / '))
    else:
        s += bar(0, first, end, Y, f'{pp["main"]} / {pp["sub"]}')
    for i, pl in enumerate(('Rahu', 'Ketu', 'Jupiter', 'Saturn'), 1):
        y = 30 + 24 * i
        for c in p['sign_changes']:
            if c['planet'] == pl and first <= c['date'] < end:
                cx = x(c['date'])
                s += (f'<circle cx="{cx:.1f}" cy="{y + 13}" r="4.6" fill="{G}" stroke="#fff" stroke-width="1.2"/>'
                      f'<text x="{min(cx, X1 - 12):.1f}" y="{y + 24}" text-anchor="middle" font-size="7" fill="#6B6258" font-family="sans-serif">{_ds(c["date"])}</text>')
    dh = p.get('dhaiya') or {}
    if dh.get('active'):
        e = dh.get('ends') or end
        s += bar(5, first, e if e < end else end, R, 'on', True)
        if dh.get('restarts') and dh['restarts'] < end:
            s += bar(5, dh['restarts'], end, R, 'on', True)
    elif dh.get('restarts') and dh['restarts'] < end:
        s += bar(5, dh['restarts'], end, R, 'on', True)
    if _stage(p):
        s += bar(6, first, end, R, 'Sade Sati on', True)
    else:
        s += f'<text x="{X0 + 6}" y="{30 + 24 * 6 + 16}" font-size="8.5" fill="#6B6258" font-family="sans-serif">not on in these 12 months</text>'
    return (f'<div class="k-gx" style="height:auto;padding:6px"><svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Timeline of planet periods, sign changes, Shani Dhaiya and Sade Sati">{s}</svg></div>')


def p47(p):
    pp = p['planet_period']
    sc = [c for c in p['sign_changes']]
    yp = (f'a <b>{pp["main"]}</b> main period with a <b>{pp["sub"]}</b> sub-period until <b>{_d(pp["until"])}</b>.'
          + (f' Then the {pp["next_sub"].replace("/", " / ")} sub-period starts.' if pp.get('next_sub') else ''))
    ys = (f'{len(sc)} sign changes fall in your 12 months, the first on {_d(sc[0]["date"])}.' if sc else 'no sign changes fall in your 12 months.')
    blocks = ''.join(f'<div class="pb"><h3>{t}</h3><p>{a}</p><p class="y"><b>Yours</b> {b} <em>See {c}</em></p></div>' for t, a, b, c in (
        ('Planet periods', 'Life is read in long runs. Each run is led by one planet and is called a main period. Inside it are shorter runs called sub-periods.', yp, 'p.5, p.14'),
        ('Sign changes', 'A planet moves into the next sign now and then. Each move is a sign change. The topic it lands on takes on that planet\'s mood.', ys, 'p.18'),
        ('Sade Sati and Shani Dhaiya', 'Both are about Saturn. Sade Sati is Saturn in the sign before, on and after your Moon sign: three stages. Shani Dhaiya is Saturn in the 4th or 8th sign from it.',
         f'Sade Sati is {_sade_yours(p)} Shani Dhaiya is {_dhaiya_yours(p)}', 'p.9, p.15')))
    body = ('<p class="lead">Planet periods, sign changes and Saturn on one picture.</p>'
            '<p class="fine" style="margin-top:2px">The picture shows your next 12 months. Green dots are sign changes. Dashed red bars are Saturn patterns.</p>'
            + _timeline(p) + blocks)
    return A.card(STYLE + body, 48, EYEBROW, 'How timing is read')


# ---------- page 48: patterns ----------
def p48(p):
    def row(name, what, present, yours, see):
        c = A.chip('mixed', 'PRESENT') if present else A.chip('note', 'NOT PRESENT')
        return (f'<div class="pb"><h3><span>{name}</span>{c}</h3><p>{what}</p><p class="y"><b>Yours</b> {yours} <em>See {see}</em></p></div>')
    on_m, _c, _n = _manglik(p)
    ys = p.get('yogas') or []
    body = ('<p class="lead">Patterns, in plain words.</p>'
            '<p class="fine" style="margin-top:2px">A pattern shows what is in the chart. It does not decide anything.</p>'
            + row('Sade Sati', 'Saturn passes the sign before your Moon sign, then your Moon sign, then the sign after: three stages. It lasts about seven and a half years.',
                  bool(_stage(p)), _cap(_sade_yours(p)), 'p.9, p.15')
            + row('Shani Dhaiya', 'Saturn is in the 4th or 8th sign from your Moon sign, for about two and a half years.',
                  bool((p.get('dhaiya') or {}).get('active')), _cap(_dhaiya_yours(p)), 'p.9, p.15')
            + row('Manglik', 'Mars sits in box 1, 2, 4, 7, 8 or 12. Read for marriage talks.' + ('' if p.get('rising_sign') else ' Counted from the Moon sign here.'),
                  on_m, _cap(_manglik_yours(p)), 'p.9, p.16')
            + row('Cancellation', 'A rule that softens a pattern, for example when a helpful planet looks at Mars.',
                  on_m and _manglik(p)[1], ('Applies' + (f': {_cap(_manglik(p)[2]).rstrip(".")}.' if _manglik(p)[2] else '.')) if (on_m and _manglik(p)[1]) else 'None applies.', 'p.16')
            + row('Kaal Sarp', 'All seven planets sit on one side, between Rahu and Ketu.', bool(p.get('kaal_sarp')),
                  'Present.' if p.get('kaal_sarp') else 'Not in your chart.', 'p.17')
            + row('Pitra', 'The Sun and Rahu sit in the same sign. Read as a tie with the elders of the family.', bool(p.get('pitra')),
                  'Present.' if p.get('pitra') else 'Not in your chart.', 'p.17')
            + row('Yogas', 'Two or more planets together that help you, such as Gajakesari, Bhadra or Budhaditya.', bool(ys),
                  ('Found: ' + ', '.join(y['name'].split(' (')[0] for y in ys) + '.') if ys else 'None found. Planet periods carry your months.', 'p.17, p.23'))
    return A.card(STYLE + body, 49, EYEBROW, 'Patterns in plain words')



# ---------- A to Z: kept as DATA; glossary_cards() lays it out ----------
def _yg(p):
    """Small facts used by several 'yours' lines."""
    pt = p['planet_table']
    strong = [r['planet'] for r in pt if r.get('strength_label') == 'Strong']
    care = [r['planet'] for r in pt if r.get('strength_label') == 'Needs care']
    sn = f'strong: {_plist(strong)}' if strong else 'none strong'
    if care:
        sn += f'; care: {_plist(care)}'
    return sn


def _corner(p):
    return _plist([PLANET[c] for h in (1, 4, 7, 10) for c in p['kundli'].get(h, [])])


def _cancel_y(p):
    on_m, canc, note = _manglik(p)
    return ('applies' + (f': {note.rstrip(".")}.' if note else '.')) if (on_m and canc) else 'none applies.'


def _strongmixed(p):
    ns, nm, nc = _counts(p)
    return f'{ns} strong, {nm} mixed, {nc} careful.'


def _stages_y(p):
    st = _stage(p)
    return (st + ' stage.') if st in ('first', 'second', 'third') else 'none on now.'


def _pl(name, what, pages):
    return (name, what, lambda p, n=name: f'{_sign_of(p, n)}.', pages)


# (term, plain meaning, yours(p) -> str, 'p.NN, p.NN' base pages). Pages are BASE 54-card numbers.
_RAW = [
    ('Birth chart', 'A map of the sky at your birth, in 12 boxes.', lambda p: f'{"rising sign, " + p["rising_sign"] if p.get("rising_sign") else "Moon sign, " + p["moon_sign"]}.', 'p.13, p.45'),
    ('Birth star', 'The star group your Moon sat in. There are 27.', lambda p: f'{p["nakshatra"]}.', 'p.1, p.5'),
    ('Bhadra Yoga', 'A strength yoga: Mercury strong in a corner box. Read as a sharp mind.', lambda p: _yoga_yours(p, 'bhadra'), 'p.49'),
    ('Budhaditya Yoga', 'Sun and Mercury in one sign. Read as a sharp mind.', lambda p: _yoga_yours(p, 'budh'), 'p.49'),
    ('Cancellation', 'A rule that softens a pattern, such as Jupiter looking at Mars.', _cancel_y, 'p.16, p.49'),
    ('Corner box', 'Box 1, 4, 7 or 10 (a key spot). Planets here act most.', lambda p: f'{_corner(p)}.' if _corner(p) else 'no planet sits in a corner box.', 'p.28, p.47'),
    ('Gajakesari Yoga', 'Jupiter in a corner box from the Moon. Read as a good name.', lambda p: _yoga_yours(p, 'gaj'), 'p.49'),
    ('Hamsa Yoga', 'A strength yoga: Jupiter strong in a corner box. Read as wisdom.', lambda p: _yoga_yours(p, 'hamsa'), 'p.49'),
    ('In the sky', 'A line on each month card naming a sign or period change.', lambda p: '', 'p.30'),
    _pl('Jupiter', 'The planet of growth, learning and advice.', 'p.18, p.46'),
    ('Kaal Sarp', 'All seven planets sit on one side, between Rahu and Ketu.', lambda p: 'present.' if p.get('kaal_sarp') else 'not in your chart.', 'p.17, p.49'),
    _pl('Ketu', 'A point in the sky that pulls toward letting go.', 'p.18, p.46'),
    ('Looks at', 'A planet also affects the box across from it.', lambda p: '', 'p.49'),
    ('Luck part of the chart', 'Box 9: luck, teachers and long journeys.', lambda p: f'{SIGNS[(SIGNS.index(_start(p)) + 8) % 12]}.', 'p.26, p.47'),
    ('Main period', 'A long block of years led by one planet.', lambda p: f'{p["planet_period"]["main"]}.', 'p.5, p.14'),
    ('Manglik', 'Mars in box 1, 2, 4, 7, 8 or 12. Read for marriage talks.', _manglik_yours, 'p.16, p.24'),
    _pl('Mars', 'The planet of drive, courage and push.', 'p.13, p.46'),
    _pl('Mercury', 'The planet of talking, learning and trade.', 'p.13, p.46'),
    ('Months to act', 'Strong months outside Shani Dhaiya and Sade Sati.', lambda p: '', 'p.10, p.42'),
    _pl('Moon', 'The planet of mind, moods and feelings.', 'p.13, p.46'),
    ('Moon sign', 'The sign your Moon was in at birth. Your main sign here.', lambda p: f'{p["moon_sign"]}.', 'p.5, p.13'),
    ('Moon-sign reading', 'Counting from your Moon sign when birth time is not sure.', lambda p: 'not used.' if p.get('rising_sign') else 'used.', 'p.45'),
    ('Neecha Bhanga Raja Yoga', 'A weak planet helped by another. Read as a rise after effort.', lambda p: _yoga_yours(p, 'neecha'), 'p.49'),
    ('Owner planet', 'Each sign has one owner planet. Mars owns Aries.', lambda p: 'in your sign table.', 'p.47'),
    ('Pancha Mahapurusha', 'Five strength yogas, such as Bhadra and Hamsa: a strong planet in a corner box.', lambda p: _yoga_yours(p, 'bhadra', 'hamsa', 'ruchaka', 'malavya', 'shasha'), 'p.49'),
    ('Part of a birth star', 'Each birth star has 4 parts.', lambda p: f'part {p["pada"]}.', 'p.1, p.5'),
    ('Pitra', 'Sun and Rahu in one sign. Read as a tie with family elders.', lambda p: 'present.' if p.get('pitra') else 'not in your chart.', 'p.17, p.49'),
    ('Planet period', 'A long block led by one planet, with sub-periods inside.', lambda p: f'{p["planet_period"]["main"]}, then {p["planet_period"]["sub"]}, until {_d(p["planet_period"]["until"])}.', 'p.14, p.48'),
    ('Planet strength', 'Strong in its home or best sign; needs care in its worst.', lambda p: _yg(p) + '.', 'p.28, p.46'),
    ('Quarter', 'A block of 3 months.', lambda p: '4 in your 12 months.', 'p.7, p.44'),
    ('Raj-type yoga', 'A yoga read as a rise in position and money.', lambda p: 'present.' if _has(p, 'raj') else 'not in your chart.', 'p.17, p.23'),
    _pl('Rahu', 'A point in the sky that pulls toward something new.', 'p.18, p.46'),
    ('Rising sign', 'The sign coming up in the east when you were born.', lambda p: f'{p["rising_sign"]}.' if p.get('rising_sign') else 'not used.', 'p.5, p.45'),
    ('Sade Sati', 'Saturn passes the sign before, on and after your Moon sign: 7.5 years.', _sade_yours, 'p.9, p.15'),
    ('Sade Sati stages', 'Saturn before your Moon sign, on it, then after it.', _stages_y, 'p.15'),
    _pl('Saturn', 'The planet of effort, time and rules.', 'p.15, p.46'),
    ('Shani Dhaiya', 'Saturn in the 4th or 8th sign from your Moon sign: 2.5 years.', _dhaiya_short, 'p.9, p.15'),
    ('Sign', 'One of 12 equal parts of the sky.', lambda p: f'Moon in {p["moon_sign"]}.', 'p.13, p.47'),
    ('Sign change', 'The day a planet moves into the next sign.', lambda p: f'{len(p["sign_changes"])} in your 12 months.', 'p.18, p.48'),
    ('Strong, mixed and careful months', 'Strong: most support. Mixed: some of each. Careful: go step by step.', _strongmixed, 'p.6, p.43'),
    ('Sub-period', 'A smaller block inside a main period.', lambda p: f'{p["planet_period"]["sub"]}, until {_d(p["planet_period"]["until"])}.', 'p.5, p.14'),
    _pl('Sun', 'The planet of self, name and confidence.', 'p.13, p.46'),
    ('The 12 parts of a chart', 'The 12 boxes, each read for one area of life.', lambda p: f'counted from {_start(p)}.', 'p.13, p.47'),
    ('The five topics', 'Career, Money, Marriage, Luck, Strengths: the five chapters of Part 2.', lambda p: '', 'p.6'),
    _pl('Venus', 'The planet of love and comfort.', 'p.13, p.46'),
    ('Wealth combination', 'A planet pairing read for money, like Raj-type yoga.', _wealth_yours, 'p.23'),
    ('Yoga', 'Two or more planets together that help you.', lambda p: (f'{len(p.get("yogas") or [])} found.' if p.get('yogas') else 'none found.'), 'p.17, p.49'),
]
_RAW.sort(key=lambda e: e[0].lower())
GLOSSARY_TERMS = [{'term': t, 'letter': t[0].upper(), 'plain': w, 'yours': y,
                   'used_on': [int(n) for n in _re.findall(r'p\.(\d+)', pg)], 'pages': pg} for t, w, y, pg in _RAW]


def _entries(p):
    return [(g['term'], g['plain'], g['yours'](p), g['pages']) for g in GLOSSARY_TERMS]


def _grow(e):
    t, what, yours, pg = e
    y = f' <span class="g3y"><b>Yours</b> {_cap(yours)}</span>' if yours else ''
    return f'<div class="g3r"><div class="g3t">{t}</div><div class="g3d">{what}{y} <span class="g3p">{pg}</span></div></div>'


_INTRO = '<p class="fine" style="margin-top:2px"><b>Find a word.</b> Each has a meaning, a Yours line and pages.</p>'
# the mock (3 pages) breaks before these terms
_BREAKS = ('Manglik', 'Raj-type yoga')


def _gloss_card(ch, i, n, first_no, p):
    a, b = ch[0][0][0].upper(), ch[-1][0][0].upper()
    rows, last = '', ''
    for e in ch:
        L = e[0][0].upper()
        if L != last:
            rows += f'<div class="g3l">{L}</div>'
            last = L
        rows += _grow(e)
    return A.card(STYLE + (_INTRO if i == 0 else '') + rows, first_no + i, EYEBROW, f'Words A to Z ({i + 1} of {n}): {a} to {b}')


def _gloss_pages(p, first_no, n=3):
    chunks, cur = [], []
    for e in _entries(p):
        if e[0] in _BREAKS:
            chunks.append(cur)
            cur = []
        cur.append(e)
    chunks.append(cur)
    return [_gloss_card(ch, i, len(chunks), first_no, p) for i, ch in enumerate(chunks)]


def glossary_cards(p, entries_per_page=12, first_no=50):
    """Glossary laid out in order, balanced over ceil(N/entries_per_page) cards (short card first, it carries the intro).
    A letter marker is only written in front of a row, so no card ends on a lone marker. Unscoped html cards."""
    E = _entries(p)
    nP = -(-len(E) // entries_per_page)
    sizes = [len(E) // nP + (1 if i >= nP - len(E) % nP else 0) for i in range(nP)]
    out, i = [], 0
    for k, sz in enumerate(sizes):
        out.append(_gloss_card(E[i:i + sz], k, nP, first_no, p))
        i += sz
    return [A.scope(h, 'm3') for h in out]


# ---------- page 52: doubts and method ----------
def p52(p):
    rs = p.get('rising_sign')
    qa = [('Why can a date differ by a day from another source?', 'A sign change happens at one exact minute. Near midnight, other sources may show the day before or after. Our dates are in India time.'),
          ('What if my birth time is wrong?', 'It can change the rising sign. The Moon sign rarely changes, so we read from it when the time is not sure.'),
          ('How are months chosen as strong, mixed or careful?', 'We look at where the planets sit and which planet period is running. Fixed rules give each month one word.'),
          ('Is this a prediction?', 'It does not say what is coming. It is a way of reading the sky. A pattern gives the mood of a month, like warm or cool weather.'),
          ('Who is this for, and is it advice?', 'It is for you, from your birth details, to help you plan your months. Do not use it to decide about money, law or your job.'),
          ('What are the pattern blocks?', 'They say if a pattern is in your chart. They do not decide anything.')]
    steps = [('Sky map.', 'From your birth details we work out where the planets sat, using the sign system used in India.'),
             ('The 12 boxes.', f'We place them in 12 boxes, counting from your {"rising sign" if rs else "Moon sign"}.'),
             ('Patterns and months.', 'We check a fixed rule for each pattern, then give each month one word.')]
    note = (f'Your birth time was given, so the chart is counted from your rising sign, {rs}.' if rs
            else f'Your birth time is not sure, so the chart is counted from your Moon sign, {p["moon_sign"]}.')
    body = ('<p class="lead">Your doubts answered.</p>'
            + ''.join(f'<div class="qa"><h3>{q}</h3><p>{a}</p></div>' for q, a in qa)
            + '<div class="qa" style="margin-top:12px"><h3 style="color:var(--gold)">The method, in plain words</h3></div>'
            + A.steps(steps) + f'<p class="fine" style="margin-top:6px">{note}</p>')
    return A.card(STYLE + body, 53, EYEBROW, 'Doubts and method')


# ---------- last page ----------
def last(p, no):
    sm = [m['ym'] for m in p['span_months']]
    body = (f'<p class="lede-c" style="margin-top:70px;font-size:19px;overflow-wrap:anywhere">Thank you, {p["first_name"]}.</p>'
            '<p class="lead" style="text-align:center">We hope this report helps you plan your months with a clear head.</p>'
            '<p class="fine" style="text-align:center;margin-top:10px">Read this report again when a new month begins.</p>'
            '<div style="width:100%;margin-top:26px">' + A.strip_big({k: p['tones'][k] for k in sm}) + '</div>')
    return A.card(body, no, 'Thank you', 'Until next time')


PAGE_TITLES_P3 = {45: 'How a chart is read', 46: 'The nine planets', 47: 'Sign by sign', 48: 'How timing is read',
                  49: 'Patterns in plain words', 50: 'Words A to Z', 53: 'Doubts and method', 54: 'Until next time'}


def pages(p, entries_per_page=None):
    """Base cards 45..54 scoped to m3. entries_per_page None = mock layout (3 glossary cards); else glossary re-laid."""
    gl = _gloss_pages(p, 50, 3) if entries_per_page is None else glossary_cards(p, entries_per_page)
    pre = [p44(p), p45(p), p46(p), p47(p), p48(p)]
    cards = [A.scope(h, 'm3') for h in pre] + ([A.scope(h, 'm3') for h in gl] if entries_per_page is None else gl)
    return cards + [A.scope(h, 'm3') for h in (p52(p), last(p, 54))]


if __name__ == '__main__':
    assert len(GLOSSARY_TERMS) == len({g['term'] for g in GLOSSARY_TERMS})
    print(len(GLOSSARY_TERMS), 'terms')
