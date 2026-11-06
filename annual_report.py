"""Annual Report assembler: render_annual(report) -> one standalone HTML string (58 printed pages, 430x830 each).

Production twin of docs/annual/mock/_build/build_v8_anjali.py (which chains build_v3..v7), minus every Chrome
measurement: the page layout is a FIXED map by base card number, so every buyer gets the same 58 pages.

Pure function: no network, no DB, no randomness, no clock. Stdlib + annual_assets + annual_report_p1/p2/p3.

PIPELINE
  1. base cards: p1.pages (1-12) + p2.pages (13-44) + p3.pages (45-54, the 3-card glossary 50-52). BASE numbering.
  2. font floor on every card (A.floor_fonts, v8 did the same).
  3. fixed layout (ANNUAL_SPLIT_MAP): keep / tighten (adds class tt or tt2; the CSS lives in annual_assets) /
     split at a block / glossary re-laid as 4 pages (p3.glossary_cards).
  4. renumber: section id, page number, every 'p.NN' / 'page NN' / 'pp NN to MM' / '#pNN' link and the Part ranges.
     A reference to a base card points to that card's FIRST final page. A reference to the glossary (base 50-52)
     points to the final glossary page whose entries contain the term (term taken from the tile label, item
     heading or dotted word just before the link, exactly as v4..v8 did).
  5. the contents card (base 4) gets 4 glossary lines instead of 3.
  6. A.document(...) with the title 'Annual Report - <first name>' plus the print fit-to-page safety net.
"""
import copy
import html as _html
import re

import annual_assets as A
import annual_report_p1 as P1
import annual_report_p2 as P2
import annual_report_p3 as P3

FINAL_PAGE_COUNT = 58
GLOSS = (50, 51, 52)                 # base glossary cards
FIXED = (1, 2, 54)                   # cover, note, thank-you: class fx (stay vertically centred)

# Base card -> action. Everything not listed is 'keep'.  Splits cut BEFORE the body block that starts with the hint
# (fallback: the body block index, counted after eyebrow, h2, rule and a style that follows them); 'row' cuts inside the first table
# of the second part after that many rows.  'tt'/'tt2' = local tightening (v8: tt = line 1.4, tt2 = line 1.38 and
# less padding; the CSS is in annual_assets._FINAL_LAYER and is scoped to that class, so no other card moves).
ANNUAL_SPLIT_MAP = {
    6: ('tight', 'tt'),      # Your 5 answers
    13: ('tight', 'tt'),     # Your chart in detail
    14: ('tight', 'tt'),     # Your planet period
    15: ('tight', 'tt2'),    # Shani Dhaiya and Sade Sati
    16: ('split', {'hint': 'Is it cancelled', 'index': 4}),            # Manglik: cut before "Is it cancelled"
    19: ('tight', 'tt'),     # Career and work (first page)
    21: ('tight', 'tt'),     # Money and savings (first page)
    27: ('split', {'hint': 'Months for choices', 'index': 4}),         # Luck: cut before the "Months for choices" question
    47: ('split', {'hint': None, 'index': 1, 'row': 6}),               # Sign by sign: 6 rows | 6 rows of the table
    49: ('tight', 'tt'),     # Patterns in plain words
    GLOSS[0]: ('gloss', 4),  # glossary: 47 terms on 4 pages (base 50-52 -> final 53-56)
    53: ('tight', 'tt2'),    # Doubts and method
}

_VOID = {'br', 'img', 'hr', 'input', 'meta', 'link'}
_TAG = re.compile(r'<!--.*?-->|<(/?)([a-zA-Z][a-zA-Z0-9]*)((?:[^>"\']|"[^"]*"|\'[^\']*\')*)>', re.S)
_SEG = re.compile(r'(<style.*?</style>|<svg.*?</svg>|<[^>]+>)', re.S)


# ---------------------------------------------------------------- card splitter
def _parse(card):
    """card -> (prefix up to and including <div class="col">, [top-level blocks of .col], suffix from the .col close)."""
    i = card.index('<div class="col">') + len('<div class="col">')
    depth, blocks, start = 0, [], i
    for m in _TAG.finditer(card, i):
        if m.group(0).startswith('<!--'):
            continue
        close, name, attrs = m.group(1), m.group(2).lower(), m.group(3)
        if name in _VOID or attrs.rstrip().endswith('/'):
            if depth == 0:
                blocks.append(card[start:m.end()]); start = m.end()
            continue
        if close:
            if depth == 0:
                if card[start:m.start()].strip():
                    blocks.append(card[start:m.start()])
                return card[:i], blocks, card[m.start():]
            depth -= 1
            if depth == 0:
                blocks.append(card[start:m.end()]); start = m.end()
        else:
            depth += 1
    raise ValueError('annual_report: .col not closed')


def _text(h):
    h = re.sub(r'<style.*?</style>|<script.*?</script>|<svg.*?</svg>|<!--.*?-->', ' ', h, flags=re.S)
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', _html.unescape(h))).strip()


def _elems(blocks):
    """Real elements only: a comment or blank text sticks to the element after it."""
    out, carry = [], ''
    for b in blocks:
        if _TAG.search(re.sub(r'<!--.*?-->', '', b, flags=re.S)):
            out.append(carry + b); carry = ''
        else:
            carry += b
    if carry and out:
        out[-1] += carry
    return out


def split_card(card, hint=None, index=None, row=None):
    """Split one card in two at a block boundary inside .col. Page 1 keeps the header (eyebrow, h2, rule and a style
    that directly follows); page 2 repeats eyebrow + h2 + rule with '(continued)' added to the heading.
    The cut is before the first body block whose text starts with hint (else body block number index).
    row: also cut the table of that block (the first block after the cut point's predecessor) after row rows."""
    pre, bl, suf = _parse(card)
    eb = _elems(bl)
    if not ('class="eyebrow"' in eb[0][:60] and '<h2 class="head"' in eb[1][:40] and 'class="rule"' in eb[2][:40]):
        raise ValueError('annual_report: card header not eyebrow/h2/rule')
    hl = 3 + (1 if eb[3].lstrip().startswith('<style') else 0)
    body = []
    for b in eb[hl:]:                       # a stray <style> mid-card rides with the block before it
        if b.lstrip().startswith('<style') and body:
            body[-1] += b
        else:
            body.append(b)
    if hint:
        k = next((i for i, b in enumerate(body) if _text(b).startswith(hint)), index)
    else:
        k = index
    if row:                                 # cut inside the first table of body[k:]
        t = next(i for i in range(k, len(body)) if body[i].lstrip().startswith('<table'))
        tb = body[t]
        m = re.search(r'<tbody>(.*)</tbody>', tb, re.S)
        rows = re.findall(r'<tr.*?</tr>', m.group(1), re.S)
        head, tail = tb[:m.start(1)], tb[m.end(1):]
        a = ''.join(body[:t]) + head + ''.join(rows[:row]) + tail
        b = head + ''.join(rows[row:]) + tail + ''.join(body[t + 1:])
    else:
        a, b = ''.join(body[:k]), ''.join(body[k:])
    h2b = ''.join(eb[:3])
    if '(continued)' not in h2b:
        h2b = h2b.replace('</h2>', ' (continued)</h2>', 1)
    return pre + ''.join(eb[:hl]) + a + suf, pre + h2b + b + suf


# ---------------------------------------------------------------- numbering and references
def _set_class_and_no(card, n, extra=''):
    card = re.sub(r'(<section class="page [^"]*)(" id=")p\d+(")', rf'\1{extra}\2p{n}\3', card, count=1)
    return re.sub(r'<div class="pgn">[^<]*</div>', f'<div class="pgn">{n}</div>', card, count=1)


_GL_ALIAS = {'Planet period now': 'Planet period', 'Sign changes': 'Sign change', 'Yogas found': 'Yoga'}
_GL_CTX = [re.compile(r'<div class="k-tl">([^<]*)</div>'),
           re.compile(r'<div class="k-qh"[^>]*><span>([^<]*)</span>'),
           re.compile(r'underline dotted">([^<]*)</span>')]
_GL_REF = re.compile(r'href="#p(5[0-2])"|(?<![\w.-])p\.(5[0-2])\b|\bpage (5[0-2])\b')


def _gl_term(prefix, rest=''):
    """The glossary term a link belongs to: the link's own text when it is a term ('<a>Moon sign</a>'), else the
    nearest tile label / item heading / dotted word before it. Compared case-insensitively."""
    own = re.match(r'[^>]*>([^<]+)</a>', rest)
    if own and re.search(r'<a [^>]*$', prefix) and own.group(1).lower() in {g['term'].lower() for g in P3.GLOSSARY_TERMS}:
        return _GL_ALIAS.get(own.group(1), own.group(1))
    best = None
    for rx in _GL_CTX:
        for m in rx.finditer(prefix):
            if best is None or m.start() > best[0]:
                best = (m.start(), m.group(1))
    if best is None:
        raise ValueError('annual_report: glossary link without a term: ' + prefix[-120:])
    return _GL_ALIAS.get(best[1], best[1])


def _gl_pass(card, links):
    """Replace every link to the base glossary pages (50-52) by a placeholder; the term travels with it."""
    def f(m):
        links.append(_gl_term(card[:m.start()], card[m.end():]))
        return m.group(0).replace(next(g for g in m.groups() if g), '@@G%d@@' % (len(links) - 1), 1)
    return _GL_REF.sub(f, card)


def _remap(card, first, last):
    """Renumber base references to final pages: link text and href of one <a> move together."""
    def text(seg, anchor):
        if anchor is not None:
            m = re.fullmatch(r'(\d+) to (\d+)', seg.strip())
            if m:
                return f'{first[int(m.group(1))]} to {last[int(m.group(2))]}'
            if re.fullmatch(r'\d+', seg.strip()):
                return str(anchor)
        seg = re.sub(r'\bpp (\d+) to (\d+)', lambda m: f'pp {first[int(m.group(1))]} to {last[int(m.group(2))]}', seg)
        seg = re.sub(r'\bpage (\d+)\b', lambda m: 'page %d' % (anchor if anchor is not None else first[int(m.group(1))]), seg)
        return re.sub(r'(?<![\w.-])p\.(\d+)\b', lambda m: 'p.%d' % (anchor if anchor is not None else first[int(m.group(1))]), seg)

    out, anchor = [], None
    for tok in _SEG.split(card):
        if tok.startswith('<a ') and 'href="#p' in tok:
            m = re.search(r'href="#p(\d+)"', tok)
            if m:
                anchor = first[int(m.group(1))]
                tok = re.sub(r'href="#p\d+"', f'href="#p{anchor}"', tok, count=1)
        elif tok == '</a>':
            anchor = None
        elif not tok.startswith('<'):
            tok = text(tok, anchor)
        out.append(tok)
    return ''.join(out)


# ---------------------------------------------------------------- print safety net
# A printed card is a fixed 430x830 box with overflow hidden. The approved layout keeps every page's lowest text
# above 790px; a buyer's chart can make a text longer (long place name, many yogas). Owner rule: body text never goes
# under 10px, so the net is STAGED and zoom (which shrinks the text) is the very last resort. A card whose lowest text
# passes FIT_BOTTOM gets, in this order, until it fits: tt (line 1.4, gaps 7), tt2 (1.38, gaps 6), tt3 (below: line 1.25, gaps 3, strips 32px, top padding 38px),
# and only then zoom on its .col. A card that already carries tt or tt2 starts from the next stage. The same fit()
# runs on load, when fonts are ready and on beforeprint; it only adds/removes classes and a CSS variable (never text).
# The stage that fired is written to the section's data-fit attribute (tt, tt2, tt3 or zoom) for the tests.
FIT_TOP, FIT_BOTTOM = 46, 790
_T3 = '.ar .page.tt3:not(.fx)'
_T3_LINES = ('p,td,li,.lead,.fine,.k-ts,.k-lead,.k-al,.k-ql,.k-gd,.k-gy,.win .wd,.tli .td,.sr .st,.pt .tx span,'
             '.callout p,.nbox p,.pb p,.k-cnt span')
FIT_CSS = ('<style>section.page>.col{zoom:var(--fit,1)}'
           f'{_T3} .col :is({_T3_LINES}){{line-height:1.25!important}}'
           f'{_T3} .col>*:not(.eyebrow):not(.rule):not(h2):not(style):not(.k-q):not(.k-ans):not(.win){{margin-top:3px!important}}'
           f'{_T3} .col>.rule+*{{margin-top:3px!important}}'
           f'{_T3} h2.head,{_T3} h2.action{{margin-top:3px!important}}'
           f'{_T3} .col :is(.pb,.k-q,.k-ans,.win,.k-gl,.k-tile,.k-cnt,.blk,.wr .wt.care,.wr .whero){{padding:1px 0!important}}'
           f'{_T3} .col :is(.callout,.nbox,.verdict,.k-band,.herocard){{padding:2px 10px!important}}'
           f'{_T3} .col .k-ar{{padding:0!important}}'
           f'{_T3} .col .tw td{{padding:1px 9px}}'
           f'{_T3} .col :is(.k-cnts){{gap:3px}}'
           f'{_T3} .col :is(.k-q,.k-ans) :is(.k-ql,.k-al,.k-lead){{margin-top:0!important}}'
           f'{_T3} .col [style*="height:46px"]{{height:32px!important}}'
           f'{_T3}{{padding-top:38px;padding-bottom:26px}}</style>')
FIT_JS = ("<script>(function(){var ST=['tt','tt2','tt3'];"
          "function low(s){var w=document.createTreeWalker(s.querySelector('.col'),NodeFilter.SHOW_TEXT),n,m=0,r,q;"
          "while(n=w.nextNode()){if(!n.textContent.trim()||n.parentElement.closest('style,script'))continue;"
          "r=document.createRange();r.selectNodeContents(n);q=r.getBoundingClientRect();if(q.height)m=Math.max(m,q.bottom);}return m;}"
          "function bot(s){return low(s)-s.getBoundingClientRect().top;}"
          "function fit(){document.querySelectorAll('section.page').forEach(function(s){"
          "if(s.dataset.c0===undefined)s.dataset.c0=s.className;s.className=s.dataset.c0;"
          "s.style.removeProperty('--fit');s.removeAttribute('data-fit');"
          f"var b=bot(s),L={FIT_BOTTOM},i=s.classList.contains('tt2')?2:s.classList.contains('tt')?1:0;"
          "while(b>L&&i<3){s.classList.remove('tt','tt2','tt3');s.classList.add(ST[i]);s.dataset.fit=ST[i];b=bot(s);i++;}"
          f"if(b>L){{s.style.setProperty('--fit',(({FIT_BOTTOM}-{FIT_TOP})/(b-{FIT_TOP})).toFixed(3));s.dataset.fit='zoom';}}}});}}"
          "fit();if(document.fonts&&document.fonts.ready)document.fonts.ready.then(fit);"
          "window.addEventListener('load',fit);window.addEventListener('beforeprint',fit);})();</script>")


# ---------------------------------------------------------------- assembler
def _base_cards(p):
    cards = [A.floor_fonts(c) for c in P1.pages(p) + P2.pages(p) + P3.pages(p)]
    if len(cards) != 54:
        raise ValueError(f'annual_report: {len(cards)} base cards, expected 54')
    return cards


def _layout(p, cards):
    """-> (final cards in order with their base number, extra class)."""
    new = []                                          # (base no, html, extra class)
    for n in range(1, 55):
        act = ANNUAL_SPLIT_MAP.get(n, ('keep',))
        if n in GLOSS and n != GLOSS[0]:
            continue
        c = cards[n - 1]
        if act[0] == 'tight':
            new.append((n, c, ' ' + act[1]))
        elif act[0] == 'split':
            a, b = split_card(c, **act[1])
            new += [(n, a, ''), (n, b, '')]
        elif act[0] == 'gloss':
            new += [(n, A.floor_fonts(g), ' gloss') for g in P3.glossary_cards(p, 12)]
        else:
            new.append((n, c, ' fx' if n in FIXED else ''))
    return new


def normalise_facts(p):
    """Pure copy of the facts dict with JSON-lossy shapes restored: kundli keys back to int 1..12 (JSON turns int keys
    into strings). No-op for facts that are already normal. Tuples that became lists need no fix (the modules only
    iterate them; the round-trip test proves byte-identical HTML)."""
    q = copy.deepcopy(p)
    k = q.get('kundli')
    if isinstance(k, dict):
        q['kundli'] = {int(a): b for a, b in k.items()}
    return q


def render_annual(report):
    """report = annual.compute_annual(...) result (uses report['facts'], report['meta']['lang']). -> HTML string."""
    p = normalise_facts(report['facts'])
    lang = (report.get('meta') or {}).get('lang') or 'en'
    new = _layout(p, _base_cards(p))
    if len(new) != FINAL_PAGE_COUNT:
        raise ValueError(f'annual_report: {len(new)} pages, expected {FINAL_PAGE_COUNT}')
    first, last = {}, {}
    for i, (n, _, _) in enumerate(new, 1):
        first.setdefault(n, i); last[n] = i
    for n in GLOSS:
        first[n], last[n] = first[GLOSS[0]], last[GLOSS[0]]
    gfirst = first[GLOSS[0]]
    gl_page = {}                                      # term -> final glossary page holding its entry
    for i, (n, c, _) in enumerate(new, 1):
        if n == GLOSS[0]:
            for t in re.findall(r'g3t">(.*?)<', c):
                gl_page[_html.unescape(t).lower()] = i
    gl_pages = sorted(set(gl_page.values()))
    final = []
    for i, (n, c, extra) in enumerate(new, 1):
        links = []
        if n not in (4, GLOSS[0]):
            c = _gl_pass(c, links)
        if i in (1, 2, FINAL_PAGE_COUNT):
            extra += ' fx' if ' fx' not in extra else ''
        c = _set_class_and_no(c, i, extra)
        c = _remap(c, first, last)
        for k, term in enumerate(links):
            if term.lower() not in gl_page:
                raise ValueError('annual_report: glossary term not found: ' + term)
            c = c.replace('@@G%d@@' % k, str(gl_page[term.lower()]))
        final.append(c)
    gl_lines = ''.join(f'<a class="xr" href="#p{g}"><span>Words A to Z ({k + 1} of {len(gl_pages)})</span><span>{g}</span></a>'
                       for k, g in enumerate(gl_pages))
    final[3], hit = re.subn(r'(?:<a class="xr" href="#p\d+"><span>Words A to Z \(\d of 3\)</span><span>\d+</span></a>){3}',
                            lambda m: gl_lines, final[3])
    if hit != 1:
        raise ValueError('annual_report: contents glossary lines not found')
    title = 'Annual Report - ' + str(p.get('first_name') or '').strip()
    doc = A.document(''.join(c + '\n' for c in final), title, lang)
    doc = re.sub(r'<!--\s*DRAFT[^>]*-->\s*', '', doc)
    return doc.replace('</head>', FIT_CSS + '</head>', 1).replace('</body>', FIT_JS + '</body>', 1)
