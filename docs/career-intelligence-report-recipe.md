# Premium PDF Report — Recipe / Build Playbook

The reusable rules behind the **Career Intelligence Report** (and any card-style premium PDF in this
repo). Follow this instead of re-explaining "add mandala / center the header / fix spacing" each
time. Copy the snippets, change the values, keep the gate.

- **Source of truth (art + layout):** `CareerIntelligence-FINAL.html` (the approved Version C mock).
  The real SVGs also live in `report_view.py`.
- **Visual version of this recipe:** artifact `https://claude.ai/code/artifact/bb2ec847-24ba-4a6a-ad59-3e240c9d9636`
- Sections below mirror that artifact 1:1.

---

## 00 · The 60-second mental model

- The report is **one standalone HTML document**. Each page is a `<section class="page">` — a fixed
  **430 × 830 px card**. `@page{size:430px 830px}` makes each card print as one PDF page.
- You design/approve the **mock** first. The renderer reuses that exact HTML and only swaps the
  person's values. **Never** hand-write per-person HTML.
- **Reuse the Business-Growth DESIGN (CSS + SVG), never its TEXT.** Every build passes a leak gate.
- Aesthetic target (manager's rule): *"Executive intelligence report. Minimal astrology graphics,
  lots of white space. NOT 'I bought an astrology PDF.'"*

---

## 01 · The golden rule — only the content changes, the machine never does

The design system — format, theme, layout, decoration, the three fixed pages — is **frozen**. Per
person, only the **section content and chart-driven values** swap in. If you're re-touching CSS,
mandalas, or spacing for a new person, stop: that belongs to the machine, not the content.

**Welded — identical for everyone:**
- **Cover page** — brand, constellation, title; only the name + birth line change.
- **"A Note for You" (page 2)** — flower-tile mandala + framed note; only the first name changes.
- **"Thank you" (last page)** — closing mandala, cross-sell, constellation; only the name changes.
- **All CSS** — tokens, layout, components.
- **The whole decoration system** — mandalas, positions, opacity, constellations.

**Dynamic — filled per person:**
- Name & birth line (cover, note, thank-you).
- Dimension scores (radar, bars, 2×2 positions), archetype & decision style (which cell highlights).
- Phase, timing, life-stage bands (dated content), and all prose inside the content sections.

**How:** the approved mock's CSS / SVG-defs / body become constants in `*_assets.py`;
`render_*(payload)` does targeted string replacements (e.g. `>Rajesh Menon<` → the real name).

---

## 02 · The physical format (page-break, one-section-one-page, headless print)

There is no manual page break. Each `<section class="page">` **is** a card.

```css
@page{ size:430px 830px; margin:0 }
.page{
  width:min(430px,92vw); min-height:min(830px,192vw);
  padding:46px clamp(22px,5.5vw,30px) 50px;
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  position:relative; overflow:hidden;            /* content past the edge is CLIPPED, silently */
  background:var(--cream); border-radius:22px; border:1px solid #EBE3D2;
  box-shadow:0 14px 38px rgba(48,34,14,.16); text-align:center;
}
*{ -webkit-print-color-adjust:exact; print-color-adjust:exact }   /* keep gold/tints in print */
```

**Headless-print rule** — production *and* verification use the same engine (headless Chrome, not a
PDF library):

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu \
  --no-sandbox --print-to-pdf=out.pdf --no-pdf-header-footer "file://REPORT.html"
```

- Result: **323 × 623 pt** pages. If you get **A4 (595×842pt)** you printed the viewer, not the file
  — open the downloaded `.html` directly, or use the headless command.

---

## 03 · The theme (one token block = the whole palette)

Re-skin by editing `:root` only — nothing hard-codes a colour. Gold = the one accent; terracotta =
"watch out"; green = positive. Headings serif; labels/data sans.

```css
:root{
  --gutter:#CBBDA1; --cream:#FAF5ED; --sand:#E1D1B9; --sand2:#E4D5BE; --card:#FFFFFF;
  --gold-callout:#FBF4E7; --track:#ECE3D3;
  --ink:#1B1D2A; --body:#26282F; --muted:#4C4A57; --faint:#9A8F76;
  --gold:#B9862E; --gold2:#C9A34E; --green:#3E7D5A; --green-bg:#E7F1EA;
  --terra:#B4572B; --terra-bg:#F7E6DC; --line:#E9E1D0; --box-line:#EFE7D6; --box-fill:#F7F1E4;
  --serif:'Fraunces','Cormorant Garamond',Georgia,serif;
  --sans:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
}
```
The 3-step gold ramp used everywhere (legend dots, bars, marks): `#B9862E` → `#C9A34E` → `#C9BFA6`.

---

## 04 · The design rules (what reads "executive")

1. **Headers centered** on every page (`.head`, `.action`, `.subtit`, `.eyebrow`). Body prose, lists,
   legends stay **left-aligned**. Centered title, left body.
2. **Every page vertically centers its content** — equal spacing top and bottom on every card:
   ```css
   .page{ justify-content:center }
   ```
3. **White space is on-brand.** One idea per page; a lean card centered with balanced top/bottom
   margins reads as intentional. Thin page → add a legend/callout, never stretch type.
4. **No coloured left-strip** on any box — it reads as "AI-generated" and lowers trust. Removed
   everywhere on purpose.

---

## 05 · The McKinsey exhibit format (the signature layout)

Every data page follows one grammar, in this order — so the middle of the report reads like one deck:

1. `.exlabel` — small gold eyebrow.
2. `.action` — a **claim as headline** ("Judgement and structure lead"), not a topic.
3. `.subtit` — the axes / what's plotted.
4. `.exrule` — hairline divider.
5. the **inline-SVG chart** (radar, 2×2, bars, donut, timeline).
6. `.leg` — a 2–3 row legend reading the chart.
7. `.take` — "THE READ": the one-line takeaway.

**2×2 winner-cell rule:** highlight the winning quadrant with a soft gold *fill* + a bold gold label;
put any marker dot *below* the label — never a ring on top of the text.

---

## 06 · The decoration system  ← the part you keep re-asking for

> ### ⚠ ANTI-DRIFT RULE — read this before touching any mandala
> **This recipe does not contain the mandala SVGs, on purpose.** The real art lives in exactly one
> place: **`CareerIntelligence-FINAL.html`** (mirrored in `report_view.py`). Identify each by its
> exact character length and **copy the whole `data:image/svg+xml,…` string verbatim** into your CSS.
> **Never redraw, simplify, "optimize," or approximate them** — any hand-drawn version (including the
> thumbnails in the visual recipe) is *schematic only* and will drift the look. Pull them like this:
> ```bash
> python3 - <<'PY'
> import re
> u=sorted(set(re.findall(r"data:image/svg\+xml,[^\"')]+", open("CareerIntelligence-FINAL.html").read())), key=len, reverse=True)
> open("sunburst.txt","w").write(u[0])   # 37131 chars — scatter / watermark / thank-you
> open("flower.txt","w").write(u[1])     # 28461 chars — note-page tile
> print(len(u[0]), len(u[1]))            # must print: 37131 28461
> PY
> ```

Two mandalas, **not interchangeable**:

| SVG (identify by length) | Looks like | Use it for |
|---|---|---|
| **28461-char** (`width='224'` tile) | interlocking **flower-of-life** petal lattice, tiles seamlessly | the **note-page (p2)** repeating background |
| **37131-char** (`viewBox='-172 -172 344 344'`) | radiating **sunburst** mandala | **scattered corners** + **centered watermarks** + **thank-you** |

**A. Note-page repeat tile (p2)** — copy Business-Growth's mechanism EXACTLY: the tile goes
on the `.page.note` **background** at the mandala's **native 224px** (not a rescaled
`::before`), layered over the gradient; the SVG's own 0.3 stroke-opacity is the faint look
(no extra element opacity). Neutralize the pseudo-elements.
```css
.page.note{background:url("<28461 flower tile — verbatim>") repeat center/224px 224px,
           linear-gradient(160deg,#FBF6EC,#F4EBD7)}
.page.note::before{content:none}
.page.note::after{content:none}
```
*(An earlier CI build reimplemented this as a `::before` at `background-size:158px` + `opacity:.6`
— that rescaled the tile and looked "zoomed"/wrong vs Business-Growth. Don't reinvent it; copy
BG's `.page.note` rule verbatim.)*

**B. Scattered corner mandalas** — pseudo-random via `nth-of-type`, never every page, always corner,
always clear of text. Sunburst SVG, opacity ~.26.
```css
.page:not(.end):not(.note):nth-of-type(6n+1)::before  /* top-left */
.page:not(.end):not(.note):nth-of-type(6n+3)::before  /* bottom-right */
.page:not(.end):not(.note):nth-of-type(6n+5)::before  /* top-right */
  /* 6n+2 / 6n+4 / 6n+6 → no mandala = breathing room */
  { width:210px;height:210px; opacity:.26; pointer-events:none; z-index:0;
    background:url("<37131 sunburst — verbatim>") center/contain no-repeat }
```

**C. Corner planet + sparkle** (on `6n+4` / `6n+6`) — small edge accents, opacity ~.28: a ringed
saturn and a 4-point star, tiny inline SVGs, never over text.

**D. Centered watermark** — sunburst as a **CSS class** background (never inline style — gotcha #2):
```css
.mid-mandala{position:absolute;top:46%;left:50%;transform:translate(-50%,-50%);
  width:340px;height:340px;opacity:.28;z-index:0;pointer-events:none;
  background:url("<37131 sunburst — verbatim>") center/contain no-repeat}
```

**E. Thank-you page watermark** — centered sunburst on `.page.end`:
```css
.page.end::before{content:'';position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
  width:300px;height:300px;opacity:.2;z-index:0;pointer-events:none;
  background:url("<37131 sunburst — verbatim>") center/contain no-repeat}
```

**F. Constellation** — inline SVG, dashed polyline through dots with two "sparkle-cross" bright stars,
opacity ~.4. Fills an empty lower third; anchors the cover and thank-you pages.
```html
<svg viewBox="0 0 240 72" style="position:absolute;bottom:66px;left:50%;transform:translateX(-50%);
     width:216px;opacity:.42;z-index:0;pointer-events:none" fill="none" stroke="#b9862e"
     stroke-linecap="round" stroke-linejoin="round">
  <polyline points="18,52 60,28 104,44 152,16 214,34" stroke-width="0.8" stroke-dasharray="3 5"/>
  <g fill="#b9862e" stroke="none"><circle cx="18" cy="52" r="2.2"/><circle cx="60" cy="28" r="2.2"/>
    <circle cx="104" cy="44" r="2.2"/><circle cx="152" cy="16" r="2.6"/><circle cx="214" cy="34" r="2.2"/></g>
  <path d="M152 7 v18 M143 16 h18" stroke-width="1.1"/><path d="M214 26 v16 M206 34 h18" stroke-width="1.1"/>
</svg>
```

**Opacity cheat-sheet** (on cream; text is full-strength at `z-index:1`, decoration at `z-index:0`):

| Element | Opacity (cream) |
|---|---|
| Note repeat tile | .55–.60 |
| Centered watermark (sunburst) | .25–.30 |
| Scattered corner mandala | .22–.28 |
| Planet / sparkle | .25–.30 |
| Constellation | .40 |

On the darker **sand** ground, push every value **+0.10–0.15** (thin gold strokes wash out on tan).

---

## 07 · The three welded pages (templates — do not rebuild per person)

**Cover (p1, `.page.sand`, centered):** sand ground, brand kicker `Axtroshastra`, a constellation, the
serif title stack (`Career / Intelligence / Report`), one-line promise, gold rule, then the person's
**name + birth line**. Only the name/birth line changes.

**A Note for You (p2, `.page.note`, centered):** the **28461 flower-of-life tile** fills the whole
card; a white framed note (`.noteframe` — diamond corners `.crn`, fan crests `.fan`) sits on top with
an eyebrow, serif headline, note copy, and the "— Your Axtroshastra analyst" sign-off. Only the first
name changes.

**Thank you (last page, `.page.end`, centered):** centered **37131 sunburst** watermark + a bottom
constellation; eyebrow "With gratitude", "Thank you, {name}", two lead lines, a `.pts` career
**cross-sell** (Compatibility · Marriage Timing · Career Growth · Life Blueprint), an italic gold
promise line, and the `www.axtroshastra.com` trust line. Meta-safe, no leak. Only the name changes.

---

## 08 · Component library (the building blocks)

**Page skeleton**
```html
<section class="page"><div class="col">
  <div class="eyebrow">SECTION LABEL</div>
  <h2 class="head">The page headline</h2>
  <div class="rule"></div>
  <!-- content -->
<div class="pgn"></div></section>
```
`.col{display:flex;flex-direction:column;align-items:center;position:relative;z-index:1}` — the
`z-index:1` keeps text **above** decoration.

**Eyebrow + headline**
```css
.eyebrow{font-weight:700;font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--gold)}
.head{font-family:var(--serif);font-weight:500;font-size:clamp(24px,5.6vw,29px);line-height:1.08;
      color:var(--ink);letter-spacing:-.01em;text-wrap:balance;margin:9px 0 0}
```

**Exhibit header** (chart pages use these instead of `.head`)
```css
.action{font-family:var(--serif);font-weight:500;font-size:21px;line-height:1.18;color:var(--ink);
        margin:7px 0 2px;text-wrap:balance;text-align:center;width:100%}
.subtit{font-size:11.5px;color:var(--muted);text-align:center;width:100%;margin-top:3px;font-style:italic}
.exrule{width:100%;height:1px;background:var(--line);margin:13px 0 2px}
```
Stop an ugly mid-word break in a headline: `<span style="white-space:nowrap">evidence-led</span>`.

**Legend under a chart (`.leg`)** — the workhorse for filling exhibit pages. Label + text **must** be
inside one `.lt` wrapper or the flexbox splits them into two ragged columns.
```html
<div class="leg" style="margin-top:14px">
  <div class="lr"><span class="dot" style="background:#B9862E"></span>
      <span class="lt"><b>Peak window.</b> The 45–55 bars stand tallest — your highest-leverage decade.</span></div>
  <div class="lr"><span class="dot" style="background:#C9A34E"></span>
      <span class="lt"><b>The build.</b> Depth banked at 40–45 is what makes that peak pay.</span></div>
</div>
```
```css
.leg{width:100%;margin-top:12px;display:flex;flex-direction:column;gap:6px;text-align:left}
.leg .lr{display:flex;align-items:flex-start;gap:9px;font-size:12px;color:var(--body)}
.leg .lt{flex:1;min-width:0}
.leg .dot{width:8px;height:8px;border-radius:50%;flex:0 0 auto;margin-top:5px}
.leg .lr b{color:var(--ink);font-weight:600;font-family:var(--serif)}
```
Dot colours = the 3-step gold ramp: `#B9862E` · `#C9A34E` · `#C9BFA6`.

**Callout box** (astrological basis / the read / worth watching)
```css
.callout{width:100%;margin-top:15px;background:var(--gold-callout);border:1px solid #EAD9AE;
         border-radius:11px;padding:12px 15px;text-align:left}
.callout .ch{font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--gold);font-weight:700;margin-bottom:5px}
.callout.terra{background:var(--terra-bg);border-color:#EAD9AE}   /* red = caution */
```
**"The read" footer** = `.take` with a `<b>` eyebrow label. **No coloured left-strip on any box.**

**Icon lists (`.pts`)** use inline SVG symbols via `<use href="#i-…">`. Symbol set (defined once in a
hidden `<svg>`): i-scales, i-store, i-people, i-clock, i-hourglass, i-trend, i-coins, i-target,
i-alert, i-moon, i-saturn, i-shield, i-gem, i-check, i-book, i-compass.

**Page-number footer** (auto-numbered)
```css
body{counter-reset:pg}
.page{counter-increment:pg}
.pgn{position:absolute;bottom:15px;left:0;right:0;text-align:center;font-family:var(--sans);
     font-size:9px;letter-spacing:.08em;color:#BDB199;z-index:2}
.pgn::before{content:counter(pg,decimal-leading-zero)}     /* 01, 02… */
.page:first-of-type .pgn{display:none}                     /* no number on the cover */
```
Put an empty `<div class="pgn"></div>` just before each `</section>`.

---

## 09 · The gate — run EVERY build before calling it done

Content is persona-driven and must pass two hard filters: **Meta-safe** (no medical/mental-health
words — full list in `docs/meta-flagged-terms.md`) and **no data leak**.

```bash
F=report.html
# 1. structure + leak + meta
grep -c '<section class="page' "$F"                                   # expect page count
grep -ic 'vyapar\|business growth\|rohit\|dear rohit' "$F"            # expect 0
grep -ioE '\b(calm|stress|anxiety|wellness|mental|medical|pressure|relief|burnout|healing|overwhelmed|therapy|depression|panic|trauma)\b' "$F" | sort -u  # expect empty

# 2. render (production path) + size check
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu \
  --no-sandbox --print-to-pdf=/tmp/out.pdf --no-pdf-header-footer "file://$F"
python3 -c "import pypdf;r=pypdf.PdfReader('/tmp/out.pdf');p=r.pages[0];print(len(r.pages),round(float(p.mediabox.width),1),round(float(p.mediabox.height),1))"
# expect: N pages, 323 x 623 pt   (NOT 595x842)

# 3. OVERFLOW — rasterize any changed page and LOOK (nothing clipped at the bottom):
#    split page -> 1-page pdf (pypdf) -> sips -s format png
```
**Pass =** page count right · size 323×623 · leak 0 · meta empty · no page clipped · cross-links
(`href="#…"`) intact. Never trust a build agent's "done" — re-run the gate on its actual output.

---

## 10 · Decisions & corrections log (settled — don't re-argue or revert)

- **Standalone HTML, printed directly.** Printing the claude.ai viewer gave A4. The report is a full
  `<!DOCTYPE html>` doc; open + Cmd+P (or headless print) → correct 323×623 cards.
- **Reuse the Business-Growth design, never its words.** Clone frame/medallions/icons; grep
  `vyapar / business growth / rohit` = 0 every build.
- **Removed the coloured left-strip** from every box — it read as "AI-generated" and lowered trust.
- **Keep the full-detail mandala — don't optimize.** A simplified mandala cheapened the look; full
  37K/28K SVGs restored and kept. (See the anti-drift rule in §06.)
- **The note page uses the flower-of-life tile, not the sunburst** — the reference is the interlocking
  petal lattice, tiled 158px, opacity .6.
- **Backgrounds visible but never fighting text.** Decoration was invisibly faint (and a `%2523`
  encoding bug rendered nothing); raised opacity, fixed encoding, text pinned above at `z-index:1`.
- **Mandalas scatter, not one fixed corner** — rotated across corners via `nth-of-type`, some pages
  left bare.
- **Headers horizontally centered** — fixed the left-aligned exhibit headers.
- **Content vertically centered (equal top/bottom margins) on every card** — the final-review
  preference. (An earlier top-align was tried to stop short pages floating, then reverted on review:
  the client wants balanced centering everywhere.)
- **Auto page numbers** via CSS counter (`01, 02…`), hidden on the cover.
- **Fill empty pages with real substance** — thin cards got 2–3 row legends/callouts (on-topic,
  persona-consistent), to ~85–92% fill.
- **Fixed the legend two-column bug** — a `<b>` that was a direct flex child split label from text;
  wrapped both in one `.lt` span.
- **Added a closing "Thank you" page + constellations/planets** — career cross-sell, Meta-safe,
  centered watermark + constellation.
- **Locked the three welded pages and the "content-only changes" contract** (see §01).

---

## 11 · Gotchas (each cost real time — don't repeat)

1. **Double-encoded `#` kills a data-URI mandala.** `%2523` = literal `%23` = invalid colour → the SVG
   renders **invisible** (looks like opacity, isn't). Must be single-encoded `%23b9862e`.
2. **A data-URI in an inline `style=""` breaks the attribute.** The SVG's own quotes close `style="`
   early, so the background silently never applies. Put mandala/tile backgrounds in a **CSS class**.
3. **Regex-replacing an SVG by its `viewBox` can hit the wrong page.** Two charts shared
   `viewBox="0 0 300 275"`, so a global replace clobbered the radar with the decision matrix. Match by
   the page's unique heading, or give every chart a unique viewBox.
4. **Overflow is silent** — `overflow:hidden` deletes anything past the card bottom. Always rasterize a
   changed page and confirm the last line clears the edge.
5. **`--screenshot` is unreliable in this sandbox** — verify by rasterizing the PDF (pypdf → `sips`).
6. **Don't trust a build agent's "done"** — re-run the gate yourself on its actual output.

---

## 12 · The pipeline (mock → production), one line each

1. **Mock**: build/approve the HTML (this recipe). Artifact = the shareable preview.
2. **Capture**: the approved mock's CSS/DEFS/BODY become constants (`*_assets.py`).
3. **Renderer**: `render_*(payload)` string-replaces persona/chart values into that BODY.
4. **Engine**: computes the numbers (reuses `engine.compute_chart`, vimshottari, dignity scores).
5. **PDF**: `pdfgen.py` → headless Chrome `--print-to-pdf` (same engine as this gate).
6. **Wiring**: route + pricing + landing (still pending for Career Intelligence).

> Status: the Career Intelligence renderer still holds the **older v2** body — re-sync the final
> Version C mock into `career_intelligence_assets.py` before productionizing. See memory
> `career-intelligence-mock-final`.
