"""annual_assets.py: theme + component kit for the Annual Report (pure strings, no I/O, no api.py import)."""
import hashlib
import html as _h
import math
import os
import re
import shutil
import subprocess
import tempfile
from html.parser import HTMLParser
from urllib.parse import unquote

import pytest

import annual_assets as A

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
FESTIVAL = 'diwali lantern kandil toran diya rangoli firework puja muhurat lakshmi garland marigold'.split()
VOID = {'br', 'img', 'hr', 'input', 'meta', 'link'}
TONES = {'2026-12': 'strong', '2027-01': 'mixed', '2027-02': 'careful', '2027-03': 'strong'}
FULL = {f'2027-{m:02d}': t for m, t in zip(range(1, 13), ['strong', 'mixed', 'careful'] * 4)}


class Balanced(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.errors = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f'unexpected </{tag}> with stack {self.stack[-3:]}')
        else:
            self.stack.pop()


def assert_balanced(s):
    p = Balanced()
    p.feed(s)
    p.close()
    assert not p.errors and not p.stack, (p.errors, p.stack)


# ---------- import, words, CSS rules ----------
def test_import_is_pure():
    assert isinstance(A.ANNUAL_CSS, str) and isinstance(A.ANNUAL_DEFS, str)
    assert 'import api' not in open(os.path.join(ROOT, 'annual_assets.py')).read()


def test_no_festival_words():
    everything = [A.ANNUAL_CSS, A.ANNUAL_DEFS, A.document('<p>x</p>', 't'),
                  A.card('<p>b</p>', 1, 'e', 't'), A.wheel_svg({1, 2}, 3), A.chapter_graphic('luck', FULL)]
    for s in everything:
        low = unquote(s).lower()
        for w in FESTIVAL:
            assert w not in low, w


def test_print_and_page_number_rules():
    css = A.ANNUAL_CSS
    assert '@page{size:430px 830px;margin:0}' in css
    rule = re.search(r'@media print\{.*?(\.page\{width:430px!important[^}]*\})', css, re.S).group(1)
    for frag in ('height:830px', 'overflow:hidden', 'break-after:page'):
        assert frag in rule, frag
    assert 'print-color-adjust:exact' in css
    pgn = re.search(r'\.ar \.page \.pgn\{([^}]*)\}', css).group(1)
    for frag in ('position:absolute!important', 'left:50%!important', 'bottom:18px!important', 'translateX(-50%)',
                 'font:400 11px/1 var(--sans)', 'color:#b9ae96!important'):
        assert frag in pgn, frag
    assert 'font-size:26px' in css and 'line-height:1.2' in css and 'line-height:1.45!important' in css
    assert '#axlang' in A.CHROME_CSS and '@media print' in A.CHROME_CSS and A.CHROME_CSS in css
    assert '.ar .page{padding:46px 26px 64px}' in css
    assert 'dashed' in css and '.ar .col [style*="dashed"]{border:0!important}' in css  # dashed borders flattened


def test_mandalas_match_report_view():
    src = open(os.path.join(ROOT, 'report_view.py')).read()
    for name, n in (('_SUN', 37131), ('_FLOWER', 28461)):
        s = getattr(A, name)
        assert len(s) == n and s in src
    assert [hashlib.sha256(x.encode()).hexdigest()[:16] for x in (A._SUN, A._FLOWER)] == ['b0652375b4f236d8', 'a927a92dd136a175']
    assert A._SUN in A.ANNUAL_CSS and A._FLOWER in A.ANNUAL_CSS


# ---------- components ----------
def test_month_helpers():
    assert A.mrange(['2026-12', '2027-01', '2027-02', '2027-04']) == 'Dec 2026 to Feb 2027, Apr 2027'
    assert A.mrange(['2026-12', '2027-02', '2027-03', '2027-04']) == 'Dec 2026, Feb to Apr 2027'
    assert A.mrange([]) == ''
    assert A.mrange(['2027-05']) == 'May 2027'
    assert (A.mname('2027-01'), A.mshort('2027-01'), A.mletter('2027-01'), A.mletters) == ('Jan 2027', 'Jan', 'J', 'JFMAMJJASOND')


def _all_components():
    t = TONES
    lines = {'Do': 'a', 'Watch': 'b', 'Why': 'c', 'When': 'd'}
    return {
        'part_label': A.part_label(1, 'Short version'), 'part_band': A.part_band(2, 'Patterns', 'sub'),
        'part_band0': A.part_band(2, 'Patterns'), 'chip': A.chip('strong'), 'chip_odd': A.chip('weird', 'x'),
        'tile': A.tile('L', 'V', 'S'), 'tile0': A.tile('L', 'V'),
        'tiles1': A.tiles([('a', 'b')]), 'tiles3': A.tiles([('a', 'b', 'c')] * 3), 'tiles_empty': A.tiles([]),
        'mini': A.mini_strip(t, highlight='2027-01'), 'mini_empty': A.mini_strip({}), 'mini_months': A.mini_strip(t, months=['2027-05', '2027-01']),
        'big': A.strip_big(FULL, highlight='2027-02'), 'big_empty': A.strip_big({}), 'big_gap': A.strip_big({'2027-01': 'strong'}, months=['2027-01', '2027-02']),
        'counts': A.counts(t), 'counts_empty': A.counts({}),
        'answer': A.answer_row('Money', 'mixed', 'lead', 'Jan', '', t), 'answer_empty': A.answer_row('', 'x', '', '', '', {}),
        'qblock': A.qblock('Q?', 'careful', lines), 'qblock_empty': A.qblock('Q?', 'x', {}),
        'callout': A.callout('T', 'x'), 'callout_good': A.callout('T', 'x', 'good'), 'callout_bad': A.callout('T', 'x', 'nope'),
        'tl': A.tl_bar([('a', 'Jan', 'Mar', 'strong'), ('b', 'Mar', 'Jun', 'mixed', 2)]), 'tl_empty': A.tl_bar([]),
        'area': A.area_table([('Work', 'strong', 'ok')]), 'area_empty': A.area_table([]),
        'gl': A.gloss_term('t', 'p', 'y', 5), 'gl_min': A.gloss_term('t', 'p'),
        'gl2': A.gloss_two_col([('a', 'b'), A.gloss_term('c', 'd')]), 'gl2_empty': A.gloss_two_col([]),
        'table': A.table(['a', 'b'], [['1', '2']], small=True), 'table_empty': A.table([], []),
        'steps': A.steps(['a', ('b', 'c')]), 'steps_empty': A.steps([]),
        'box': A.box('L', 't'), 'pill': A.tone_pill('careful'), 'strip': A.strip(t), 'strip_empty': A.strip({}),
        'card': A.card('<p>x</p>', 3, 'eb', 'Title', 'fx tt'), 'card_min': A.card('', 1),
        'wheel': A.wheel_svg({1, 2, 4, 7, 8, 12}, 6), 'wheel_none': A.wheel_svg(set(), None),
        'scope': A.scope(A.card('<p class="z">x</p>', 1), 'm1', '.z{color:red}.page{padding:0}'),
        **{f'gx_{k}_{n}': A.chapter_graphic(k, d) for k in ('career', 'money', 'marriage', 'luck', 'strengths', 'other')
           for n, d in (('empty', {}), ('one', {'2027-01': 'strong'}), ('full', FULL))},
    }


def test_components_well_formed():
    for name, h in _all_components().items():
        assert isinstance(h, str), name
        assert_balanced(h)


def test_edge_outputs():
    assert A.tiles([]) == '' and A.mini_strip({}) == '' and A.strip_big({}) == '' and A.area_table([]) == '' and A.steps([]) == ''
    assert 'k-c2' in A.tiles([('a', 'b')] * 4) and 'k-c3' in A.tiles([('a', 'b')] * 5)
    assert 'Jul to Nov' in A.strip_big({f'2027-{m:02d}': ('strong' if 7 <= m <= 11 else 'careful') for m in range(1, 13)})
    assert 'strong month<' in A.counts({'2027-01': 'strong'}) and 'strong months<' in A.counts({})
    assert 'class="page fx tt" id="p3"' in A.card('', 3, cls='fx tt') and '<div class="pgn">3</div>' in A.card('', 3)


def test_scope_isolates_module_css():
    out = A.scope(A.card('<p>x</p>', 1) + '<style>.a,.page.b{x:1}</style>', 'm2a', '.z{y:2}')
    assert '<section class="page m2a"' in out
    assert '<style>.m2a .z{y:2}</style>' in out and '.m2a .a,.page.m2a.b{x:1}' in out
    with pytest.raises(ValueError):
        A.scope('<section class="page"></section>', 'm1', '@media print{a{b:c}}')


def test_document_is_complete():
    d = A.document(A.card('<p>x</p>', 1), 'A & B <t>', 'hi')
    assert d.startswith('<!DOCTYPE html>') and '<html lang="hi">' in d and 'name="viewport"' in d
    assert '<title>A &amp; B &lt;t&gt;</title>' in d and A.ANNUAL_CSS in d
    assert d.index('<body class="ar">') < d.index(A.ANNUAL_DEFS) < d.index('<section')
    assert_balanced(d)


# ---------- inline SVG audit: nothing outside the viewBox ----------
NUM = re.compile(r'-?\d*\.?\d+(?:e-?\d+)?')


def _attr(tag, name, default=None):
    m = re.search(r'(?<![\w-])' + name + r'="([^"]*)"', tag) or re.search(r"(?<![\w-])" + name + r"='([^']*)'", tag)
    return m.group(1) if m else default


def _path_points(d):
    pts, cx, cy, sx, sy = [], 0.0, 0.0, 0.0, 0.0
    for cmd, args in re.findall(r'([MmLlHhVvCcAaZzSsQq])([^MmLlHhVvCcAaZzSsQq]*)', d):
        nums = [float(x) for x in NUM.findall(args)]
        rel = cmd.islower()
        c = cmd.upper()
        if c == 'Z':
            cx, cy = sx, sy
            continue
        step = {'M': 2, 'L': 2, 'H': 1, 'V': 1, 'C': 6, 'A': 7, 'S': 4, 'Q': 4}[c]
        for i in range(0, len(nums) - step + 1, step):
            a = nums[i:i + step]
            if c == 'H':
                cx = a[0] + (cx if rel else 0)
            elif c == 'V':
                cy = a[0] + (cy if rel else 0)
            else:
                ex, ey = a[-2], a[-1]
                cx, cy = (cx + ex, cy + ey) if rel else (ex, ey)
            pts.append((cx, cy))
            if c == 'M' and i == 0:
                sx, sy = cx, cy
    return pts


def svg_overflow(svg, tol=0.0):
    """Return a list of elements whose extent leaves the viewBox (stroke included, text width estimated)."""
    vb = [float(x) for x in NUM.findall(_attr(svg, 'viewBox'))]
    x0, y0, x1, y1 = vb[0], vb[1], vb[0] + vb[2], vb[1] + vb[3]
    bad = []

    def chk(what, xa, ya, xb, yb):
        if xa < x0 - tol or ya < y0 - tol or xb > x1 + tol or yb > y1 + tol:
            bad.append((what, round(xa, 1), round(ya, 1), round(xb, 1), round(yb, 1), (x0, y0, x1, y1)))
    for m in re.finditer(r'<(circle|rect|line|polyline|path|text)\b([^>]*?)(/?)>(?:([^<]*)</text>)?', svg):
        tag, attrs, _, txt = m.groups()
        g = lambda n, dflt='0': float(_attr(attrs, n, dflt) or dflt)
        sw = float(_attr(attrs, 'stroke-width', '0') or 0) if _attr(attrs, 'stroke', 'x') != 'none' and 'fill' in attrs else 0
        sw = max(sw, 0)
        h = sw / 2
        if tag == 'circle':
            chk('circle', g('cx') - g('r') - h, g('cy') - g('r') - h, g('cx') + g('r') + h, g('cy') + g('r') + h)
        elif tag == 'rect':
            chk('rect', g('x') - h, g('y') - h, g('x') + g('width') + h, g('y') + g('height') + h)
        elif tag == 'line':
            chk('line', min(g('x1'), g('x2')) - h, min(g('y1'), g('y2')) - h, max(g('x1'), g('x2')) + h, max(g('y1'), g('y2')) + h)
        elif tag == 'polyline':
            n = [float(v) for v in NUM.findall(_attr(attrs, 'points'))]
            xs, ys = n[0::2], n[1::2]
            chk('polyline', min(xs) - h, min(ys) - h, max(xs) + h, max(ys) + h)
        elif tag == 'path':
            pts = _path_points(_attr(attrs, 'd', ''))
            if pts:
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                chk('path', min(xs) - h, min(ys) - h, max(xs) + h, max(ys) + h)
        elif tag == 'text' and txt:
            fs, w = g('font-size', '10'), len(_h.unescape(txt)) * g('font-size', '10') * .55
            x = g('x')
            anchor = _attr(attrs, 'text-anchor', 'start')
            xa = x - w / 2 if anchor == 'middle' else (x - w if anchor == 'end' else x)
            chk('text ' + txt, xa, g('y') - fs * .8, xa + w, g('y') + fs * .3)
    return bad


def _svgs(html):
    return re.findall(r'<svg\b.*?</svg>', html, flags=re.S)


def test_wheel_never_clips_extreme_inputs():
    cases = [({1, 2, 4, 7, 8, 12}, 6), (set(), None), (set(range(1, 13)), 1), ({12}, 12), ({1}, 7), (None, 0), ({1, 2, 4, 7, 8, 12}, 99)]
    for parts, mars in cases:
        out = A.wheel_svg(parts, mars)
        svgs = _svgs(out)
        assert len(svgs) == 1
        assert svg_overflow(svgs[0]) == [], (parts, mars)
        assert out.count('<circle') == 12
    assert 'Gold circles:' in out and 'the 6 parts where' in out and 'Mars counts.' in out and 'Red: Mars' in out
    assert 'the 6 parts where Mars counts. Red: Mars' not in out  # 4 short lines, not 2 long ones
    # the bug: with Mars on the far-left/right circle the old fixed box clipped it; the new box must hold r=13 everywhere
    for mars in range(1, 13):
        assert svg_overflow(_svgs(A.wheel_svg(set(), mars))[0]) == []


def test_chapter_graphics_never_clip_extreme_inputs():
    datas = [{}, {'2027-01': 'strong'}, FULL, {k: 'strong' for k in FULL}, {k: 'careful' for k in FULL},
             {f'2027-{m:02d}': 'bogus' for m in range(1, 13)}, {f'{2020 + i}-01': 'mixed' for i in range(30)}]
    for kind in ('career', 'money', 'marriage', 'luck', 'strengths', 'unknown'):
        for d in datas:
            out = A.chapter_graphic(kind, d)
            for s in _svgs(out):
                assert svg_overflow(s, tol=.01) == [], (kind, d)


def test_decoration_art_inside_viewbox():
    for k in ('wheel', 'leaf', 'clock', 'spark', 'sunrise', 'ribbon', 'confetti', 'stars', 'consts'):
        svg = unquote(A._U[k].split(',', 1)[1])
        assert svg_overflow(svg, tol=1.5) == [], k  # tolerance = stroke / rotated confetti bars


def test_svg_audit_catches_a_clipped_svg():
    assert svg_overflow('<svg viewBox="0 0 10 10"><circle cx="9" cy="5" r="3"/></svg>')


# ---------- print smoke test ----------
@pytest.mark.skipif(not os.path.exists(CHROME), reason='Chrome not installed: print smoke test skipped')
def test_prints_three_pages_at_430x830():
    cards = ''.join(A.card(f'<p>Page {n} body</p>', n, 'Eyebrow', f'Title {n}', 'fx' if n in (1, 3) else '') for n in (1, 2, 3))
    d = tempfile.mkdtemp()
    try:
        src, pdf = os.path.join(d, 'a.html'), os.path.join(d, 'a.pdf')
        open(src, 'w').write(A.document(cards, 'Smoke'))
        subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-pdf-header-footer', f'--print-to-pdf={pdf}', 'file://' + src],
                       capture_output=True, timeout=120)
        raw = open(pdf, 'rb').read()
        pages = re.findall(rb'/Type\s*/Page(?![s\w])', raw)
        assert len(pages) == 3, len(pages)
        boxes = re.findall(rb'/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]', raw)
        assert boxes and all(abs(float(w) - 323.04) < .1 and abs(float(h) - 623.04) < .1 for w, h in boxes), boxes
        try:
            import fitz
        except ImportError:
            return  # page-number y check needs pymupdf: skipped
        doc = fitz.open(pdf)
        ys = []
        for pg in doc:
            nums = [b for b in pg.get_text('words') if b[4] in ('1', '2', '3') and b[1] > 500]
            assert nums
            ys.append(round(nums[-1][3], 1))
        assert len(set(ys)) == 1, ys
    finally:
        shutil.rmtree(d, ignore_errors=True)
