# Diwali Wealth & Prosperity Report: build spec (source of truth)

**Status (26 Oct 2026): BUILD STARTED (owner: real page + backend, slug /en/diwali). Earlier: spec updated 26 Oct with the re-order hybrid; LATER 26 Oct: life-stage question DROPPED (owner + uncle), Marriage and Family & children now have one general version; build still ON HOLD until the owner approves; next = new mock (Mock 3).** No production code yet. Mock 1.2 and Mock 2 v2 show the OLD shape (Part 2 deep dive) and are kept as history; the change map is [changes-vs-mocks-2026-10-25.md](changes-vs-mocks-2026-10-25.md).

This is the anti-drift spec (CLAUDE.md §18). The report is built strictly against this
document and checked section by section. If the build and this doc disagree, this doc
wins, or the doc is changed on purpose. It is never silently drifted.

- Decisions come from [README.md](README.md) "Decisions so far" and "Open questions", and from
  [changes-vs-mocks-2026-10-25.md](changes-vs-mocks-2026-10-25.md) §5 (items 1–9). They are cited as
  **(Owner, date)**. Where two decisions conflict, the later one wins.
- Code citations are `file:line` on `upstream/aws-mysql` @ `b437be0` (fetched 23 Oct 2026),
  re-opened for this spec. Some line numbers in [../bugs.md](../bugs.md) were taken at
  `c955a0c` and have moved; the current lines are given here.
- Anything not decided in the README is **not** decided here. It is listed in §13 Open items
  and marked **PROPOSED** wherever this spec suggests an answer.

Plain words used below (for the spec reader; the report itself follows R3 in §2):
- **house** = one of the 12 parts of the birth chart, each about one area of life.
- **planet period (dasha)** = the long stretch of years one planet "runs" in your life.
  The **main period (MD, mahadasha)** lasts years; the **sub-period (AD, antardasha)** lasts
  months to a few years.
- **transit** = where a planet is moving in the sky now, compared with your birth chart.
- **rising sign (lagna)** = the sign rising in the east at birth; needs an exact birth time.
- **Moon-sign chart (Chandra lagna)** = reading the houses from the Moon's sign instead.
  It works without an exact birth time.
- **area** = one of the 5 life areas: Money, Career, Business, Family & children, Marriage.
- **situation** = the work type input (student / job / business owner / home).
- **exhibit** = a chart page in the recipe's fixed layout (recipe §05).
- **mock** = a hand-built HTML preview of the PDF, made before any real code (CLAUDE.md §8).

---

## 1. Product meta

| Field | Decision |
|---|---|
| Name (customer-facing) | **Diwali Wealth & Prosperity Report** (Owner, 23 Oct) |
| Covers | From this Diwali to the next (Nov 2026 – Oct 2027) |
| Product key (internal) | `diwali`: **PROPOSED, owner to confirm** |
| Route / slug | `/en/diwali`: **PROPOSED, owner to confirm.** `/diwali-report` → 301 to `/en/diwali` (CLAUDE.md §11.6). `/hi/diwali` only when Hindi ships. |
| Price | **₹499** (Owner, 23 Oct; switched from ₹299/₹399 to the uncle's price). Shown on the page before checkout (CCPA). `amount_paise = 49900` stored on the order (CLAUDE.md §13). |
| Gift price | **DECIDED (Owner, 26 Oct: Self / Gift toggle): same ₹499 as a self purchase.** No separate second-order offer. |
| Language | **English first. Hindi ships after the English version is approved** (Owner, 23 Oct). A written exception to CLAUDE.md §7 "both together". No Hinglish (CLAUDE.md §7). |
| Homepage | **Yes**: a card plus tagged reviews in `pages/home.html` (Owner, 23 Oct; CLAUDE.md §4). See open item O-14 on reviews. |
| After 8 Nov | Keep selling as a **"Year Ahead"** report. Only the Diwali dates page changes (Owner, 23 Oct). |
| Delivery | Report page + PDF + WhatsApp to the number typed **in the form** (Owner, 23 Oct). WhatsApp delivery fixes (bug #4) are handled by the owner (23 Oct). |
| Launch | Target Sun 1 Nov 2026. Last possible day Thu 5 Nov. Full scope, risk accepted (Owner, 23 Oct). |
| Shape | **Re-order hybrid** (Owner, 25 Oct): every buyer gets every area section in full, plus a short Better luck section; only the ORDER changes. No separate deep-dive Part. See §5. |
| Length | Set by the section list (Owner, 23 Oct). Each area needs enough content that the buyer has no doubt (Owner, 25 Oct), about 3 pages each. **Estimate: about 55–62 pages** (§5 page budget; owner to confirm per-section budget, O-29). |
| Template to clone | Business Growth (vyapar) for the pipeline shape. **Not** Career Intelligence, which never calls the AI (README round 1; bugs.md #2). CI is a model for the reading rhythm only ("The read", end plan). |

## 2. Rules for every page

**Content rules**
1. **Only the structure is fixed. All chart content comes from the buyer's data** (Owner, 23 Oct;
   CLAUDE.md §22). Fixed = which sections exist and what kind of material each holds. Every
   chart-derived word, month, planet or house comes from this buyer's computed chart.
   Generic text is allowed only on chart-independent pages: How to read this report, Diwali across
   India, the city puja table, the gold fact box, Astrology made simple, FAQ, Methodology, Thank you,
   Contents.
2. **No data leakage** (Owner, 23 Oct). No mock-persona name, number, date or sentence may reach
   a real buyer. Enforced by the leak grep in §9.
3. **Everyday English** that Indians whose first language isn't English understand (Owner,
   20 and 23 Oct). No vague phrases like "heavy stretch".
4. **Writing pattern R2, every topic** (Owner, 25 Oct):
   1. one-word answer: **Good / Steady / Careful**
   2. what it means for you: 2–3 plain sentences with real-life examples (savings, gold, a raise,
      hiring, a family trip)
   3. do / watch
   4. one short "why" line (the only place a chart reason appears)
   5. when (best time / good time / careful time)

   Each area section closes with CI's one-line **"The read"** (Owner, 25 Oct).
5. **Clutter rules R3** (Owner, 25 Oct). These replace the 23 Oct rule "astrology terms in brackets
   after the everyday words" and the TIMING.md round-2 "nickname (Nth house)" rule:
   - No astrology reasons in brackets inside sentences. The reason lives only in the "why" line.
   - Written date ranges appear only in **"Your year at a glance"** and **"Your 12 months"**.
     Elsewhere the text says "your best time / good time / careful time" plus a jump link to the
     timeline. **DECIDED (Owner, 26 Oct, O-30): month names MAY appear inside data pictures** (kandils,
     gold-month diyas, the Sade Sati strip, the Wrapped card); **written text never lists date ranges.**
   - The plain name OR the house number, **never both** ("the money part of your chart" or "2nd
     house", not "money part (2nd house)").
   - "How to read this report" sits up front.
   - No page that only points to other pages.
6. **Timing words** (Owner, 25 Oct): "best time", "good time", "careful time". Never "stretch" or
   "window".
7. **Never "year" alone** (Owner, 25 Oct). The span is always "from this Diwali to the next
   (Nov 2026 – Oct 2027)", so nobody thinks a good "year" ends in Jan 2027. Fixed section titles that
   the owner approved with the word ("Your year at a glance", "Your year gone by") keep it and carry
   the span as a subtitle.
8. **CLAUDE.md §5b word list applies to the report AND the landing page.** Plus: dosha, curse,
   danger, bad luck, guaranteed, cure, prevent, will happen (README D; structure check §1).
   Fixed swaps: "calm facts" → "plain facts"; "medical advice" → "professional advice";
   "how everyone at home will be keeping" → "how home life will go" (structure check §1).
   **PROPOSED:** avoid the word "remedy" (flagged by §5b in its medical sense) and say "practice"; the
   extra words "bad luck" and "will happen" come from the superseded plan and also need confirming.
9. **Dates rule:** no single "lucky days". Month ranges calculated from the chart are allowed
   (planet-period changes, the year timeline, the 12 months, good months for gold) (Owner, 23 Oct),
   inside the R3 limit in rule 5.
10. **No scores.** No fortune score, no guna score, no "X/10" (uncle's research; structure check §1).
    Engine grades are turned into the one-word answers. **PROPOSED mapping:** Strong → Good,
    Moderate → Steady, Building or a careful transit → Careful; with an unsure birth time (T2/T3) the
    engine cap means no "Best time" label.
11. **No guarantees, no investment advice.** Money and career timing are "good times", never
    promises (ASCI). No stock tips, no Muhurat-trading picks, no gold-price forecasts. Keep CI's
    honesty line: "This report never predicts a figure."
12. **Drugs and Magic Remedies Act 1954:** no practice is ever tied to health, illness or having
    children. Practices cover money and luck only, with no promised result (structure check §1).
13. **Never predict** death, illness, divorce, accidents or infertility (README D).
14. **Every caution has 4 parts:** what, when, what to do, and from when it gets better (README D;
    approved "Months to go slow" job). Under R3 the "when" is a careful-time pointer to the timeline.
15. **CCPA (dark patterns, 2023):** ₹499 shown before checkout; no add-ons appear later in the
    flow; no fake countdown; no struck-out "was" price; no hard-coded trust numbers (bugs.md #6, #7).
16. **No gemstones, yantras, colours to wear, paid pujas, Kaal Sarp, Manglik-as-doom, lucky-rashi
    lists, long puja guides** (Owner; README "Leave out"). **No archetype / identity name** (Owner,
    25 Oct).
17. **Never mention the AstroSage accuracy check to buyers**, on the Methodology page or anywhere
    else (Owner, 25 Oct). The check stays as an internal test (CLAUDE.md §21).

**Design rules**

18. **Keep the mocks' SVGs and visual design** (Owner, 25 Oct; the owner and uncle love them):
    recipe mandalas, garland, rangoli corner, the Diwali skin.
19. **Pictures and their jobs** (Owner, 25 Oct). Sources: [design/overview-options-v2-gallery.html](design/overview-options-v2-gallery.html)
    (numbered No. 1–11; page images `design/overview-v2a-p1..4.png`, `design/overview-v2b-p1..4.png`)
    and [design/state-marks-v3.html](design/state-marks-v3.html) (`design/state-marks-v3-p1..5.png`).

    | Picture | Job | Shows data? |
    |---|---|---|
    | No. 8 diya path (with Lakshmi's footprints) | Front overview of all areas (Best / Good / Careful time per area) | yes |
    | No. 9 door garland v2 | Family & children and Marriage sections. **No glow:** full bloom = Best, half-open = Good, bud = Careful (as in `design/overview-v2b-p2.png`; the glowing v3 flower, state-marks-v3 p5, is NOT used) | yes |
    | No. 6 akash kandils | Time, e.g. the 12 months | yes |
    | No. 1 diyas | Time / areas on other pages, e.g. gold months | yes |
    | No. 5 anar fountains | Better luck and best-time highlights. Jain sensitivity noted; owner accepted it | yes |
    | No. 4 mithai box | Decoration only, e.g. blessing / gift page | no |
    | No. 11 rangoli tiles | Decoration only, art across pages | no |
    | No. 10 kalash, No. 7 thali, No. 2/3 | **Not used** | — |

20. **State marks v3** (approved, Owner, 25 Oct) for the kandil, the diya (No. 1 / No. 8) and the anar:
    - **Best** = biggest, filled glow, rays all round, gold body, solid green tag.
    - **Good** = medium, one thin ring, no rays, cream body, outlined tag.
    - **Careful** = unlit, dashed outline, grey-sand fill, dashed tag.

    The states must read in black-and-white print too. The overview must not look like Life
    Blueprint's wheel (no same or similar SVG) (Owner, 25 Oct).

## 3. Inputs and what each one changes

| Input | Required? | Options | What it changes |
|---|---|---|---|
| Name | yes | text | Cover, Note, Thank you, blessing |
| Date of birth | yes | date (out-of-range → inline error, CLAUDE.md §1) | Everything chart-based; age band |
| Birth time | yes, or tick "Don't know your exact birth time?" | **Same pattern as the marriage and CI pages (Owner, 26 Oct; replaces the "How sure are you?" question):** hour/min/AM-PM boxes + the "Don't know your exact birth time? … It's our specialty." checkbox, which swaps the boxes for "Approximate time": Morning / Day / Evening / Night / No idea at all. Exact → T0; a part of the day → T2 with that band; No idea → T3. A partial time → inline error, never a silent guess (CLAUDE.md §1) | House reference, grade cap, the "less precise" note |
| Birth place | yes | city (geocoded to lat/lon/timezone) | Chart maths |
| Gender | yes | **options PENDING, see O-7** (engine takes `female: bool`, `engine.py:343`) | Marriage reading (`marriage_significators`, `engine.py:206`) |
| Work type (situation) | yes | job / business / student / home | Career and Business wording; **the default area order when the choice is skipped** (Owner, 25 Oct) |
| ~~Life stage~~ | **DROPPED** (Owner + uncle, 26 Oct: life-stage question dropped, keep it general) | – | Nothing. Marriage and Family & children have one general version for everyone; the "not married and 25+" order rule is removed |
| WhatsApp number | yes | **in the form** (PROPOSED: Indian mobile only, like today's pages) | Delivery only. **Self and Gift are delivered the same way, to this number (the person filling the form)** (Owner, 26 Oct: Self / Gift toggle). A giver downloads the PDF and passes it on themselves; we never collect or message the receiver's number |
| Steering choice | **optional** | Money · Career · Business · Family happiness (= the "Family & children" section) · Marriage · Better luck and a fresh beginning | **Which area comes first** (opener line "You picked X, so it comes first"), the 5 Diwali answers, the fresh-start plan. If skipped: order by situation, then the chart fine-tunes (§5 "Area order"; Owner, 25 Oct). Choosing Better luck: see O-31 |
| **Self / Gift toggle** | yes (default Self) | Self · Gift | (Owner, 26 Oct: Self / Gift toggle) **Gift** shows two optional boxes: **giver's name** and **gift message**. The message box placeholder shows an example message (PROPOSED: "Wishing you a bright Diwali and good months ahead. Here is what your chart says till next Diwali. With love."). Empty message → we print that ready-written message; empty name → "A Diwali gift for you". In Gift mode the name and birth details are the **receiver's**. Gift page = p2 right after the cover, Note moves to p3; the giver's name also goes in the blessing |

**Birth-time tiers** (reuse `engine.compute_report`, `engine.py:342-380`; Owner, 23 Oct):
- T0 exact → rising-sign chart.
- T1 about ±45 min → rising-sign chart, but falls back to the Moon-sign chart if the rising sign
  changes within ±45 min (`engine.py:361-367`).
- T2 a ±3-hour band, T3 unknown → Moon-sign chart (`engine.py:358`). T3 also checks whether the
  Moon changes birth star during the day (`engine.py:370-378`).
- T2/T3 cap good periods at "Moderate" (`engine.py:445`).
- When the Moon-sign chart is used, the report says plainly that it is less precise
  (a one-line note on "Your Diwali answers" + one FAQ entry + the Methodology page). **Not on the
  cover**: the cover stays locked.

**Not asked:**
- **No tradition field** (Owner, 23 Oct). Reasons on record: tradition doesn't change chart content;
  where you live isn't your tradition; a longer form; asking about community can feel personal.
  Revisit only if sales show strong demand from one community.
- No email, gotra, current city, typed question (README "Skip"). The "who is it for" choice is the **Self / Gift toggle** (26 Oct).

**Age bands** (from date of birth, no extra field) change **examples and tone only**, never which
sections appear (Owner, 23 + 25 Oct). Odd age + life-stage combinations are not questioned.

| Band | Examples to use |
|---|---|
| under 25 | first salary, studies, first job |
| 25–40 | growth, switching jobs, home loan |
| 40–60 | expansion, children's future, building wealth |
| 60+ | steady income, family money, passing things on; never "first job" |

**Combinations:** the section list is the same for everyone, so the inputs change only order and
wording: steering 6 choices + skipped (skipped → 4 situation orders and
the chart fine-tune) × time 2 (rising-sign / Moon-sign) × work type 4 × gender 2 (O-7)
× gift 2 × age band 4 = **896 order/wording versions** (2,688 before life stage was dropped, 26 Oct). The old "576 combinations" count (6 deep-dive outcomes) no longer applies. Test
every branch of every input (CLAUDE.md §12), not every combination.

## 4. Funnel

**Form → free preview → Razorpay ₹499 → delivery.** The popup is removed (Owner, 23 Oct). This is a
written exception to CLAUDE.md §1, where a popup captures the number before payment.

1. **Form** (all inputs in §3). The WhatsApp number is sent to `/api/order` exactly as the popup
   number is today, so it is stored as `user_phone` before payment (`api.py:1902-1905`
   `attach_user`) and delivery keeps using "the typed number only, never Razorpay's"
   (`api.py:1858`, CLAUDE.md §1).
2. **Free preview**: real computed data from `compute_diwali()` (no AI). The same 5 "Diwali
   answers" questions as the front page are shown **locked** (Owner, 23 Oct). They follow the chosen
   area, or, if skipped, the **first area in the report's order** (§5 "Area order").
   - **DECIDED (O-9, Owner, 23 Oct): the CI pattern.** FREE (real data from their chart): birth chart
     drawing, Moon sign, birth star, current planet period (name only), Sade Sati yes/no, the **Wrapped card**
     (see O-33), and the uncle's emphasis line ("Your report starts with [area]: ..."). LOCKED: the 5 answers
     (one teaser line each) and every month and date.
   - Price ₹499 visible here, before checkout (CCPA).
3. **Razorpay ₹499.** Price chosen on the server by product, not from the browser's page path
   (add a `product == "diwali"` branch in `_order_amount_paise`, `api.py:447-468`; avoids bugs.md #5).
4. **Delivery** (after bug #1 fix, §9): AI text → PDF → WhatsApp (both templates,
   `TWILIO_CONTENT_SID` + `TWILIO_CONTENT_SID_TEXT`, CLAUDE.md §1).

**Ad tracking** (Owner, 23 Oct): the funnel events fire at the usual points (CLAUDE.md §9). The only
new field sent is **the chosen category** (or "skipped"). Birth date, time, place, name, gender
and the gift note are **never** sent. The purchase value is the real server amount, not a
hard-coded ₹499 (bugs.md #8). Note: the existing server-side purchase event already sends the phone
and email as match keys (`api.py:1883-1887`); whether that stays is O-12.

## 5. Sections

Data sources: **EXISTS** = code already computes it; **WRAP** = small new wrapper over existing code;
**NEW** = no code yet. From [structure-check-2026-10-23.md](structure-check-2026-10-23.md) §2, re-checked
for this spec. "Inputs" = which inputs change the section (all chart sections also change with the chart).

Every data page uses the recipe §05 exhibit grammar: eyebrow → claim headline → subtitle → rule →
SVG → legend. **"The read" closes each AREA SECTION once, not every page** (Owner, 25 Oct). Prose pages use the recipe §08 page skeleton. Exhibit names are
**PROPOSED**; Mock 3 settles them.

**Report order (Owner, 25–26 Oct):** Front pages → Part 1 opener → Year gone by → the 5 areas in
order → Better luck → Sade Sati → 3 strengths → Months to go slow → 12 months → Part 2 Diwali pages →
End plan → Back pages. The old Part 2 (deep dive) is **deleted**; its question lists merged into
the area sections. **DECIDED (Owner, 26 Oct): printed part names are "Part 1 · From this Diwali to the next"** (all
areas and year pages) **and "Part 2 · Your Diwali"** (dates, puja, practices, blessing).

### Front pages

| # | Section | One-line job | What differs per buyer | Source | Exhibit | Inputs |
|---|---|---|---|---|---|---|
| 0.1 | Cover | Locked recipe cover: name, birth details, Moon sign, birth star, "Diwali 2026 to Diwali 2027" | Name, birth line, Moon sign, birth star | EXISTS `engine.py:117` | (cover) | name |
| 0.2 | Gift page | "A Diwali gift from [giver]" (or "A Diwali gift for you" when no name) + the gift message (or our ready-written one when empty). **Gift mode only; right after the cover** (Owner, 23 + 26 Oct). No. 4 mithai box as decoration | Giver name, message | form | (prose) | gift |
| 0.3 | A Note for You | Locked recipe page; first name only changes. **Page 2 normally, page 3 in gift mode** (Owner, 23 Oct). Diwali text needs owner approval (O-13) | First name | fixed copy | (note page) | name, gift |
| 0.4 | How to read this report | **NEW, 1 page** (Owner, 25 Oct, R3): what Good / Steady / Careful mean, what the Best / Good / Careful marks look like, the span "from this Diwali to the next (Nov 2026 – Oct 2027)", where the dates live (timeline + 12 months), "we never predict a figure" | Nothing (chart-independent) | fixed | (prose + mark legend) | none |
| 0.5 | Your Diwali answers | **5 questions** (Owner, 25 Oct) for the chosen area or the first area (§6a sets). Each answer = **one word (Good / Steady / Careful) + one plain line, no brackets** (R2/R3). Carries the one-line "read from your Moon sign, less precise" note when T2/T3 | Area, every answer | WRAP from area results | prose list | steering, work type, life stage, tier |
| 0.6 | Your year at a glance | **The ONE timeline** (from the old 4-part page): Nov–Jan, Feb–Apr, May–Jul, Aug–Oct, a theme name + one line each, plus the single best time. **One of only 2 places with written dates** (Owner, 25 Oct). Subtitle names the span | Theme names, lines, best time | WRAP `vimshottari_tree` `engine.py:149` + month transits (E2) | 4-segment timeline | tier |
| 0.7 | Your areas at a glance | **No. 8 diya path**: 6 diyas, one per area (5 areas + Better luck; Owner, 26 Oct, O-34), each marked Best / Good / Careful time with one plain line. Replaces the 2 old pointer "at a glance" pages (Owner, 25 Oct) | Every state and line | WRAP (built from area results) | No. 8 diya path | all |
| 0.8 | Contents | Contents with renderer-computed page numbers; **jump links kept** (owner asked for them). Shorter, because Part 2 is gone | Page numbers, area order, gift page | renderer | (contents) | gift, steering |

### Part 1 · From this Diwali to the next (everyone gets every section)

| # | Section | One-line job | What differs per buyer | Source | Exhibit | Inputs |
|---|---|---|---|---|---|---|
| 1.0 | Part 1 opener | Opener + mini-contents in this buyer's area order, with the line **"You picked [area], so it comes first"**; if skipped, a line naming the order by situation (PROPOSED wording: "As a [business owner], your report starts with [Business]") | Order, line | WRAP E4 | (opener) | steering, work type |
| 1.1 | Your year gone by | Diwali 2025 → 2026: hard and good months and why, chart only; **never names an event**; ends "from [month] it gets better" (Owner, 20 Oct). R2 style, plain words, no brackets | Months, areas, reasons | WRAP `_past_analysis` `engine.py:635`; vyapar last-3-years `products.py:1018-1060` | 12-month look-back strip | tier |
| 1.A–1.E | **The 5 area sections**, in the buyer's order (see "Area order" below) | Each area in full, about 3 pages: an R2 block per topic (the topic list is §6), closing with "The read" | See the area table below | per area | per area | steering, work type, life stage, gender, age band, tier |
| 1.F | Better luck and a fresh beginning | **Short, positives only, for everyone, always right after the 5 areas** (Owner, 25 Oct). Topics in §6. **No. 5 anar** for the best-time highlights. Cautions stay in 1.9 | Bright spots, turning points, luck part | WRAP (built from area results + 9th house + period changes) | No. 5 anar | (chart) |
| 1.7 | Sade Sati check | Saturn's 7½-year phase near the Moon sign, shown in phases across Nov 2026 – Oct 2027 incl. the 2027 move back and re-entry; free steps. R2 style | Active/not, phases | WRAP `_sade_sati` `engine.py:612` + E3 | phase timeline | (Moon sign) |
| 1.8 | Your 3 strengths | Always 3, each with an action from this Diwali to the next. R2 style | Which 3, reasons, actions | WRAP + E5 | ranked list (rank only, no numbers) | (chart) |
| 1.9 | Months to go slow | Short. 4-part cautions (what, when, what to do, from when better); **the dates point to the timeline** (R3) | Cautions, steps | WRAP vyapar careful `products.py:1069`; `_dasha_remedies` `engine.py:705` | (prose, 4-part cards) | tier |
| 1.10 | Your 12 months | **12 akash kandils (No. 6)**, one per month, marked Best / Good / Careful time + a short Do / Watch per month. Slow planets + fast planets (Sun, Mars, Venus) so months differ (Owner, 23 Oct). **The second of only 2 places with written dates.** Likely 2 cards | Every month | NEW-ish WRAP E2 | No. 6 kandil row | tier |

**The 5 area sections (each about 3 pages, R2 per topic, "The read" at the end):**

| Area | What it covers (old sections merged) | Branches inside | Source | Picture | Inputs |
|---|---|---|---|---|---|
| **Money** | Old 1.2 money picture + 1.3 money timing + Money deep dive. The money part (2nd), gains (11th), wealth combination (Dhana Yoga, one fixed definition, E6; kind wording if absent); good times to save, spend, clear loans, recover from a loss; where money comes from | Age-band examples | EXISTS Dhana Yoga `products.py:1175-1202`; vyapar strong window `products.py:962`, `year_by_year` `products.py:1144`; blueprint `_ad_phases` | No. 1 diyas | tier, age band |
| **Career** | Old 1.4 + Career deep dive. Work (10th), daily work and rivals (6th), income (11th): big break, switch or stay, raise, after a job loss, work that suits you, work travel | **Job:** promotion, switch, raise, after a layoff. **Student:** "Career (studies & first job)": studies, first job, study abroad (`vidyarthi.py:70`). **Home:** returning to work, home-run income. **Business owner:** career read of the owner's own role (PROPOSED). Never an empty page | EXISTS `compute_career_growth` `career_growth_report.py:298` (takes `as_of`); 6th house small WRAP | No. 1 diyas | work type, tier, age band |
| **Business** | Old 1.5 + Business deep dive. Partners (7th), work (10th), gains (11th): business or job leaning, start or expand, partner or alone, deals and new account books, when to go slow on spending | **Business owner:** growth, partnership, months to expand. **Job:** business vs job, and side income. **Student:** future business-or-job leaning. **Home:** small home ventures and the family money picture. Never an empty page (Owner, 23 Oct) | EXISTS `compute_vyapar` `products.py:785` (no `as_of`, fix in E1) | job↔business spectrum dot + No. 1 diyas | work type, tier |
| **Family & children** | Old 1.6 + Family deep dive. "How home life will go" (Owner, 20–23 Oct): family events, house move or property, moving city | **One version for everyone** (Owner + uncle, 26 Oct: life-stage question dropped, keep it general): home life, family events, house move or property, moving city; the children part (5th) as a soft general line (children, the younger generation, or a creative project). Never assumes the buyer has, or wants, children; never "when children may come". Never a parent's health or any health reading | WRAP blueprint `HOME_4`/`CHILDREN_5` `products.py:591-592`, `_ad_phases` | No. 9 door garland v2 | tier |
| **Marriage** | Old 1.7 + Marriage deep dive | **One version for everyone** (Owner + uncle, 26 Oct: life-stage question dropped, keep it general): the relationship tone from this Diwali to the next, good months for important relationship decisions and plans, careful months for conversations, partnership traits (7th), Manglik facts with the rule stated, **no guna score**. Never assumes status: no "your wife / husband / spouse", "your marriage", "the right person", "marry again", "new" or "first". Gender still changes the reading. Helpline line if conflict is serious stays general (O-11) | EXISTS/WRAP `compute_report` `engine.py:342`, `manglik` `engine.py:312`, `marriage_extras` `engine.py:757` | No. 9 door garland v2 | gender, tier |

New risk to guard (comparison doc §4): 5 full sections can repeat the same months and reasons. Each
area must lead with its own houses and planets; the 5-buyer test and the "same sentence" gate (§9)
also run across sections of one report.

### Area order (Owner, 25 Oct)

1. **Chosen area first**, with the opener line "You picked X, so it comes first". The other 4 follow
   the situation order below, minus the chosen one.
2. **If skipped, order by situation:**

   | Situation | Default order |
   |---|---|
   | Student | Career (studies & first job) → Money → Marriage → Family → Business |
   | Job | Career → Money → Family → Marriage → Business |
   | Business owner | Business → Money → Career → Family → Marriage |
   | Home | Family → Money → Marriage → Career → Business |

3. ~~Not married and over 25 → Marriage 2nd~~ **REMOVED (26 Oct)**: without the life-stage question we
   cannot know who is unmarried, so Marriage keeps its situation-order place.
4. **The chart fine-tunes (DECIDED, Owner, 26 Oct, O-28): rule B, "light touch".**
   - **Area houses:** Money = 2nd + 11th; Career = 10th + 6th; Business = 7th + 10th + 11th;
     Family & children = 4th + 5th; Marriage = 7th.
   - **Score each area 0–3, one point per signal** (never shown to the buyer):
     (1) the main planet period (mahadasha) lord rules or sits in that area's houses;
     (2) the sub-period (antardasha) lord rules or sits in those houses;
     (3) Jupiter passes over or aspects those houses at any point from this Diwali to the next.
   - **One pass from the top: swap two neighbours only if the lower one scores 2 or more points
     higher.** Ties and 1-point gaps keep the situation order.
   - **Pinned (never moved):** 1st place (the chosen area, or the situation's first area when skipped;
     Better luck when picked).
   - **Applies the same way when the buyer picked an area:** the chosen area stays 1st and the other
     4 follow the situation order with this fine-tune.
   - **Worked example (Vikram, business owner, skipped):** scores Business 2, Family 2, Money 1,
     Marriage 1, Career 0. Situation order Business → Money → Career → Family → Marriage becomes
     **Business → Money → Family → Career → Marriage** (Family 2 vs Career 0 = swap).
5. **Better luck** is the short section after the 5 areas. **If the buyer PICKS Better luck** (Owner,
   26 Oct, O-31): the Better luck section moves to the top, the 5 areas follow the situation order (as if
   skipped), and the 5 front answers and the end plan follow Better luck.

This REPLACES "the chart picks the first area" (Owner, 23 Oct; and the 25 Oct §5 item 3 answer, both
superseded by item 7).

### Part 2 · Your Diwali (printed label; called "Part 3" in drafts before 26 Oct)

| # | Section | One-line job | What differs per buyer | Source | Exhibit | Inputs |
|---|---|---|---|---|---|---|
| 3.0 | Part 2 opener ("Part 2 · Your Diwali") | Divider | Nothing | fixed | (opener) | none |
| 3.1 | Diwali across India | Same for everyone: each community's day (table below); "dates for New Delhi; your city may differ by a day"; general greeting | Nothing (chart-independent) | fixed, hand-checked | table | none |
| 3.2 | Lakshmi Puja time in your city | Hand-checked top-cities table vs Drik Panchang, same for everyone (Owner, 23 Oct) | Nothing | fixed (README key dates has 6 cities) | table | none |
| 3.3 | Good months for gold and big buys | **Our rule, labelled "our method"** (Owner, 23 Oct), shown with **No. 1 diyas** (the kalash is not used) + gold fact box (hallmark check, making charge in writing). No price forecasts. R2/R3 wording | Months, reasons | NEW E7 | No. 1 diya strip | tier |
| 3.4 | Lakshmi and prosperity practices | Name keeps "Lakshmi" (Owner, 23 Oct). Pairs: tradition + the habit behind it + a household step. Money and luck only. Nothing to buy. Gemstones stripped | Which planets get practices | WRAP `REMEDY_7L`/`REMEDY_NODE`, `_biz_remedy_line` `products.py:772-783` (strip the gem field) | (prose, paired cards) | (chart) |
| 3.5 | Your fresh-start plan | "If this, then I will" plans for the chosen area, or the first area if skipped (covers the uncle's "personal action plan"). PROPOSED: 3 plans | Plans tied to area + best times | WRAP | (prose) | steering |
| 3.6 | Blessing | Family blessing (with giver's name in gift mode) and the **Wrapped card** (O-33). **No. 4 mithai box as decoration.** No separate WhatsApp-status share card (Owner, 23 Oct); the Wrapped card is part of the page | 3 words, name, giver | WRAP | (prose) | gift |

**Diwali across India table (fixed text):**

| Day | Date |
|---|---|
| Dhanteras | Fri 6 Nov |
| Kali Chaudas; Tamil Deepavali | Sat 7 Nov (Tamil date: confirm, O-4) |
| Lakshmi Puja; Chopda Pujan | Sun 8 Nov |
| Kali Puja | night of Sun 8 Nov |
| Govardhan; Gujarati New Year (Samvat 2083); Padwa | Tue 10 Nov |
| Bhai Dooj | Wed 11 Nov |

After 8 Nov this page is the only page that changes (Owner, 23 Oct). What it changes to is O-8.

### End plan (CI; Owner, 25 Oct)

| # | Section | One-line job | What differs per buyer | Source | Exhibit | Inputs |
|---|---|---|---|---|---|---|
| E.1 | Your top priorities | The top priorities from this buyer's areas, with **"if you do only one"** | Priorities, the one | WRAP (from area results) | (prose, ranked) | steering, chart |
| E.2 | 30 / 90 / 365 days | Steps for the next 30, 90 and 365 days, tied to the buyer's best and careful times | Steps | WRAP | 3-column plan | chart |
| E.3 | 5 takeaways | 5 lines, each written once, from the chart (never repeating "The read" lines word for word) | All 5 | WRAP | (prose list) | chart |

**No archetype** (Owner, 25 Oct).

### Back pages

| # | Section | One-line job | What differs per buyer | Source | Exhibit |
|---|---|---|---|---|---|
| B.1 | Your birth chart | **South-Indian chart** (fixed sign boxes), the same grid as Career Intelligence and Business Growth, plus one line for North-Indian readers ("The same chart, drawn the South-Indian way: each sign keeps its own box.") (owner asked Claude to choose, 23 Oct; reasons: Karnataka and Tamil Nadu buyers, consistency across products, stable boxes for everyday labels) | Chart | EXISTS: the `.kundli` grid component in `career_intelligence_assets.py` / the vyapar kundli | chart grid |
| B.2 | Your planets | Planet table: sign, house, strength in words | Values | EXISTS blueprint `chart.planets` | planet table / bars (no numbers) |
| B.3 | Houses used in this report | 2nd, 4th, 5th, 6th, 7th, 9th, 10th, 11th in everyday words. The one place where house numbers and plain names sit side by side, as a table (PROPOSED; R3 applies to sentences) | Signs and lords | EXISTS blueprint `houses_1_12` | table |
| B.4 | Astrology made simple | Short course (PROPOSED: 2 pages): houses, planet periods, transits, Sade Sati, rising sign vs Moon sign. Stays at the back; the short "How to read" is up front (R3) | Nothing | fixed | (prose) |
| B.5 | Your doubts answered | FAQ incl. "nothing is guaranteed", why birth time matters, why reports differ, how to read the timeline, the "less precise" note | Nothing (T2/T3 entry shown only when used) | fixed | (prose) |
| B.6 | Methodology and disclaimer | "Not financial, legal or professional advice"; Lahiri; our gold rule explained. **No AstroSage line** (Owner, 25 Oct) | Tier note | fixed | (prose) |
| B.7 | Thank you | Locked recipe page; name only changes | Name | fixed | (end page) |

### Page budget (ESTIMATE, owner to confirm, O-29)

| Block | Pages |
|---|---|
| Front: cover 1, gift 0–1, note 1, how to read 1, answers 1, timeline 1, diya path 1, contents 1–2 | 7–9 |
| Part 1 opener 1 + year gone by 2 | 3 |
| 5 areas × about 3 | 15 |
| Better luck | 1–2 |
| Sade Sati 2, strengths 1, months to go slow 1–2, 12 months 2 | 6–7 |
| Part 2 · Your Diwali: opener 1, dates 1, puja 1, gold 1, practices 1–2, fresh start 1, blessing 1 | 7–8 |
| End plan | 2–3 |
| Back: chart 1, planets 1, houses 1, astrology made simple 2, FAQ 2, methodology 1, thank you 1 | 9 |
| **Total** | **about 50–56 at the low end; about 55–62 with fuller areas (target)** |

At about 110–130 words per page, every page a reading page (comparison doc, Part 2).

### The uncle's 12 questions: where each is answered

| Q | Question (short) | Answered in |
|---|---|---|
| 1 | Will money improve after Diwali? | Money, 0.5 (Money set) |
| 2 | When does the next money-growth period begin? | Money, 0.6 timeline |
| 3 | Stronger wealth-building chances this year? | Money (Dhana Yoga) |
| 4 | Planet patterns for money obstacles or chances? | Money, 1.9 |
| 5 | A major career breakthrough? | Career |
| 6 | Which periods suit professional growth? | Career, 1.10 |
| 7 | Business vs job? | Business |
| 8 | Is after-Diwali a turning point? | 0.6, Better luck (turning points = planet-period changes) |
| 9 | Which months are favourable? | 1.10, 0.6 |
| 10 | Strengths and challenges? | 1.8, 1.9 |
| 11 | Lakshmi practices that fit my chart? | 3.4 |
| 12 | Dates and practices for new beginnings? | 3.1, 3.2, 3.3, 3.5 (month ranges and festival dates only, no single lucky days) |

The uncle's 4 dimensions map to: Wealth → Money, 3.3; Career and business → Career, Business;
Fortune (favourable periods) → 0.6, 0.7, 1.10, Better luck; Personalised Diwali guidance → Part 2 +
B.1–B.3.

The uncle's 7 sections map to: Prosperity overview → Money; Wealth timing → Money + 0.6; Career and
income → Career; Business outlook → Business; Diwali-to-Diwali timeline → 0.6 + 1.10; Lakshmi practices
→ 3.4; Personal action plan → 3.5 + End plan. The father's need (family's and children's future,
20 Oct) → Family & children.

## 6. Topics inside each area section

Each area section answers its topic list below, each topic as one R2 block (§2 rule 4). These lists
were the old "deep-dive question lists"; they now live inside the area sections for every buyer
(Owner, 25 Oct). Sources: research-round2-raw.md Team 2, the 3 council proposals, the uncle's
questions, README decisions. Wording is a draft for Mock 3.

**Money**
1. Will my money get better after this Diwali?
2. When does my next good money time start, and how long does it last?
3. Which months suit saving, and which can take bigger spending?
4. When is a good time to clear loans? (Step: clear the highest-interest loan first.)
5. If I had a loss, from when do things recover?
6. Where does my money most easily come from: salary, business, family or savings growing over time?
7. My wealth combination (Dhana Yoga): present or not, in plain words.

**Career** (wording by work type)
1. When could my next big break or promotion come?
2. Should I switch or stay, and which months suit a move?
3. When is a good time to ask for a raise?
4. If I lost my job, from when do things pick up, and what do I do now? (CV, 3 contacts, savings.)
5. What kind of work suits me most?
6. Work abroad or travel for work: which months suit a move? (Good times only, not visa advice.)
- Student ("Career: studies & first job"): when studies go best, when the first job might come, good times for study abroad (`vidyarthi.py`).
- Home: when is a good time to return to work or start home-run income?

**Business** (wording by work type)
1. Does my chart lean to business or a job?
2. When is a good time to start or expand? (Step: check 6 months of savings first.)
3. Partner or alone?
4. Which months suit new deals, hiring and new account books?
5. Which months to go slow on new spending?
- Job holders: business vs job, and side income: when and how small to start.
- Student: a future business-or-job leaning.
- Home: small home ventures and the family money picture.

**Family & children** (one version for everyone, (Owner + uncle, 26 Oct: life-stage question dropped, keep it general))
1. How will home life go from this Diwali to the next?
2. Which months suit family events, a house move, or buying or registering property?
3. Moving city or abroad: which months suit it?
- The children part (5th) as a soft general line only; never assumes the buyer has or wants children.
- Never a parent's health or any health reading.

**Marriage** (one version for everyone, by gender only, (Owner + uncle, 26 Oct: life-stage question dropped, keep it general))
1. How do relationships look from this Diwali to the next? (Tone + the good and careful months.)
2. Which months suit important relationship decisions and plans?
3. Which months need care in conversations, and what helps? (Communication steps.)
4. What does the chart say about partnership in your life? (7th house traits, tendency only.)
5. Am I Manglik, by which rule, and does it matter? (Plain facts box; no paid fix.)
- Never assumes married or unmarried. Serious conflict: a general helpline line (O-11). Never predict divorce.

**Better luck and a fresh beginning** (short, positives only, everyone; Owner, 23 + 25 Oct)
1. Bright spots: the strongest point from each area.
2. Turning points: planet-period changes from this Diwali to the next.
3. What the months before this Diwali were building toward.
4. Luck and blessings (9th house, bhagya).
5. Small fresh-start habits.

(Strengths with actions live in 1.8; Better luck does not repeat them.)

## 6a. The 5 questions per area (front page "Your Diwali answers" + locked on the free preview)

**DECIDED (Owner, 23 Oct; count of 5 confirmed 25 Oct).** These are in the uncle's style:
- second person ("your")
- a soft verb (could / may / suggest / appear)
- tied to Diwali or the coming months
- one idea per question, at most 12 words
- no §5b words and no hype words

**Answer format (Owner, 25 Oct, R2/R3):** one word (**Good / Steady / Careful**) + one plain line.
No brackets, no chart reason, no written date range (the dates live in the timeline). Example shape:
"Good. Money looks steadier after Diwali, and your best time is marked on your timeline." (Owner,
26 Oct, O-30: no written date ranges in answers.)

**Word fixes DECIDED (Owner, 26 Oct, O-32): the swaps below are applied in the lists themselves.**
- "the coming year" / "this year" → "the months after Diwali" or "from this Diwali to the next"
- Career Q3 "When could your next good window for a job change open?" → "When could a good time for a job change begin?"
- Marriage (not married) Q1 "When could a favourable period for your marriage begin?" → "When may the right person come into your life?" (matches "Love and companionship ahead") **Superseded 26 Oct** by the one general Marriage set.

**Money**
1. Will your financial fortunes improve after this Diwali?
2. When could your next period of financial growth begin?
3. Does your birth chart suggest stronger wealth-building opportunities from this Diwali to the next?
4. Which months may call for more care with spending?
5. Which months may be favourable for buying gold or property?

**Career**
1. Could a career breakthrough come from this Diwali to the next?
2. Which periods may be more favourable for professional growth?
3. When could a good time for a job change begin?
4. Which months may favour asking for a raise or promotion?
5. Which months may call for steady effort, not sudden moves?

**Business**
1. Could new growth come for your business from this Diwali to the next?
2. When could your next period of business profit begin?
3. Which months may be favourable for launching or expanding?
4. What does your birth chart suggest about partnerships?
5. Which months may call for more care with loans and credit?

**Family happiness**
1. Could more harmony come to your home from this Diwali to the next?
2. Which months may suit family functions and celebrations?
3. When could a good period for buying or moving home begin?
4. Which months may bring happy news in your family? (One version for everyone, 26 Oct.)
5. Which months may call for more care in family conversations?

**Marriage** (one version for everyone; **APPROVED, Owner 26 Oct**, incl. the Manglik facts box)
1. Could more warmth come to your relationships from this Diwali to the next?
2. Which months may be favourable for important relationship decisions?
3. Which months may call for more care in talks with the people closest to you?
4. What does your birth chart suggest about partnership in your life?
5. Does your birth chart show Manglik, and does it matter?

**Better luck and a fresh beginning** (positives only)
1. Is the period after Diwali a potential turning point in your life?
2. Which months appear relatively favourable in your outlook?
3. When could a fresh chapter begin for you after this Diwali?
4. Which personal strengths could shape your next life phase?
5. Which small habits may support your fresh start after this Diwali?

## 7. Engine work list

All new code goes through the shared engine (`compute_chart` `engine.py:117`, `compute_report`
`engine.py:342`), never a fork of the astro maths, and must pass the AstroSage gate (CLAUDE.md §21;
`tests/birth_accuracy.json`, `tests/test_birth_accuracy.py`). Pipeline per CLAUDE.md §11:
`compute_diwali()` (facts only, no AI) → `narrative.py` (AI prose only) → `render_diwali()`.

| # | Work | Why / where | Size |
|---|---|---|---|
| E1 | **Pin `as_of` to Diwali 2026** for every call | `compute_vyapar` and `compute_blueprint` use `datetime.utcnow()` (`products.py:804`, `products.py:521`). Add an `as_of` argument. `compute_report` (`engine.py:345`) and `compute_career_growth` already take it. Exact date and post-8-Nov behaviour: O-8 | small |
| E2 | **Month-by-house transits incl. fast planets** (Sun, Mars, Venus + Jupiter, Saturn, Rahu/Ketu) for Nov 2026 – Oct 2027 | No such function exists. Build on `sidereal_lon`/`sign_of`/`houses_from` (`engine.py:79/86/99`). Feeds 0.6, 0.7, 1.10, every area's "when", 3.3 | ~10-30 lines |
| E3 | **Sade Sati 2-way scan + re-entry** | `_sade_sati` (`engine.py:612-632`) has no start month when active, no end when not active, and stops at the first exit, so it misses Saturn moving back (Aries 3 Jun 2027 → Pisces 20 Oct 2027 → Aries 23 Feb 2028). Scan back for the start, forward across the whole span, list every phase | ~15 lines |
| E4 | **Area order** (replaces the old strongest-area picker) | Returns the 5 areas in order: chosen area first; else the situation order (§5 "Area order"); Better luck picked → Better luck section first, areas in situation order; then the chart fine-tune between unpinned neighbours. Area score = the old O-6 signal (WRAP blueprint `wheel` and `_phase_read`). **Fine-tune = rule B (Owner, 26 Oct, O-28):** 0–3 points per area, swap only on a 2+ point gap, 1st place pinned. Better luck is never in this list; it always follows | ~25 lines |
| E5 | **Strengths, always 3** | Blueprint strengths (`products.py:531`) only count own/exalted planets and can be empty. Rank by planet dignity (own sign, exalted, friendly, house); ashtakavarga totals (`bhinnashtakavarga` `divisional.py:166`) only break ties; always return the top 3; no numbers shown (Owner, 23 Oct, O-6) | small |
| E6 | **Dhana Yoga, one definition** | Today (`products.py:1175-1202`): present if the 2nd and 11th lords are the same planet, sit in one sign, or swap houses. **DECIDED (O-5): widen to the classical definition**, a link (conjunction, exchange or aspect) between the lords of houses 1, 2, 5, 9 and 11; state the rule on the page; kind wording when absent; test against known charts | small-medium |
| E7 | **Gold-months rule** (NEW, "our method") | **DECIDED (O-5):** the months Jupiter or Venus moves through the 2nd/11th house, or the current sub-period lord rules the 2nd/11th; labelled "our method" | small |
| E8 | **Look-back slice** Diwali 2025 → 2026 | WRAP `_past_analysis` (`engine.py:635`, default 3 years back) to one year, month resolution | small |
| E9 | **Marriage "never-zero" honesty** | When nothing is strong, the engine lifts weak periods to "Building" (`engine.py:416-418`). Report must say so | wording |
| E10 | **Practices without gemstones** | `REMEDY_7L` returns `(fast, mantra, gem)` (`products.py:776`): drop `gem` for this product; no fasting tied to health | small |
| E11 | **Wire the product** | `SECTION_SPECS` entry (`narrative.py:139`), `MAX_TOKENS_BY_PRODUCT` / `TIMEOUT_BY_PRODUCT` (`narrative.py:104,121`), `_render_for` (`api.py:360`), `_order_amount_paise` (`api.py:447`). Token budget grows: every buyer now gets 5 full areas + end plan (estimate, measure in Mock 3) | medium |
| E12 | **One-word answers + states** | Map engine grades and month tones to Good / Steady / Careful (answers) and Best / Good / Careful time (pictures), with the T2/T3 cap (§2 rule 10, PROPOSED mapping) | small |

## 8. Written exceptions to the recipe and CLAUDE.md

| Rule | Exception | Decided |
|---|---|---|
| CLAUDE.md §1 (popup captures the number) | **Popup removed.** WhatsApp number taken in the form; flow is form → preview → Razorpay | Owner, 23 Oct |
| CLAUDE.md §7 (both languages together) | **Hindi after English approval** | Owner, 23 Oct |
| Recipe §01/§07 (3 welded pages) | **Gift page added** right after the cover, only in gift mode, so the Note moves from p2 to p3 in gift mode. Cover, Note and Thank you keep their locked content | Owner, 23 Oct |
| Recipe §01/§07 (welded copy) | The cover title stack, the Note copy and the Thank-you cross-sell are CI's text. Diwali needs its own fixed copy for each, written once, same for every buyer. Only the name changes after that. See O-13 | follows from the name decision |
| Recipe §01/§03/§06 (theme frozen; re-skin via `:root` only) | **Diwali skin:** light base (recipe cream and sand) + Diwali accents + reuse the recipe SVGs verbatim. The approved Diwali pictures (§2 rules 19–20) are new art. Recipe §06 opacity values only cover cream/sand | Owner, 23 + 25 Oct |
| Recipe §12.3 (string-replace into one approved body) | **Pipeline:** the recipe for design; CLAUDE.md §11 compute → narrative → render for content, because this report re-orders, branches and uses AI text | structure check §4 |
| Recipe §08 (CSS counter page numbers) | **Page numbers computed by the renderer**, because they change per buyer (area order, gift page) and the contents links need real numbers | structure check §4 |
| Recipe note-tile size | Follow §06A (native 224px), not the "158px" in the §10 log | structure check §4 |

## 9. Bug work inside this build

| Item | What | Ref |
|---|---|---|
| Bug #1 reorder | After payment: **AI text → PDF → WhatsApp**. Today `_deliver_paid_report` runs PDF first, then the AI text (`api.py:1871-1872`); `pdfgen.invalidate` is only called in admin (`api.py:2830`). **Fix for the Diwali product only** (Owner, 23 Oct); the other products stay as they are and are fixed later as a separate task (bugs.md #1 stays open for them). Preview stays without AI; AI cost unchanged (only buyers). If the AI fails: retry automatically; "still on its way" message after 2 minutes (O-10, decided 26 Oct: 4 parallel AI calls, progress page + instant WhatsApp text) | Owner, 23 Oct; bugs.md #1 |
| Banned-word lint | Fails the build/render on any §5b word + dosha, curse, danger, bad luck, guaranteed, cure, prevent, will happen. Applies to AI output and fixed copy; watch false hits (scope→cope, patience→patient) | README D |
| R3 lint (NEW) | Fails the render on: brackets inside sentences above a small limit (PROPOSED: 0 in area prose; the houses table and gold-rule statement exempt); written date ranges outside 0.6 and 1.10 (month labels inside data pictures are allowed, O-30); the words "stretch" and "window"; "year" with no span nearby (PROPOSED: allow only the fixed titles); a plain house name and its number together ("money part (2nd house)"); any mention of AstroSage | Owner, 25 Oct |
| Render queue (PROPOSED: from the superseded "before launch" list; bugs.md #9 is P1) | `pdfgen` runs one Chrome at a time, 5 s lock wait, 45 s timeout (`pdfgen.py:45-50`). Add a retry queue so a Dhanteras rush doesn't send WhatsApp without a PDF. Longer reports (about 55–62 pages) make this more pressing | bugs.md #9 |
| 5-buyer test | **Owner decision 26-27 Oct: applies to AI-on output (real AI run on the server after deploy); the deterministic bank text is only the AI-failure fallback and may be generic, so unit tests only check different charts give different facts and month tables.** Generate 5 reports for 5 different people; **fail if any paragraph is identical** (dates and numbers aside), including strengths, the Wrapped card, blessing, "The read" lines and the end plan. Also: no sentence repeated across the 5 area sections of one report | README (decided 20 Oct "Before launch"); comparison doc §4 |
| Leak grep | Must be 0 hits in every generated report: `vyapar`, `business growth`, `rohit`, `Rajesh Menon`, `Vikram Rao` (mock persona), every §5b word, `dosha`, `curse`, `danger`, `guaranteed`, `cure`, `AstroSage`. Watch for false hits from our own "Business" heading | structure check §4 |
| Don't copy | No 30-min timer (bugs.md #6), no hard-coded "14,200+" (#7), no fixed ₹499 pixel value (#8), no static preview box without an id (#15), price by product on the server (#5), store `amount_paise` (#12). From Life Blueprint / CI (bugs.md #19–#23): no fixed Do/Watch lists shared by everyone, no do-advice that ignores the verdict, no frozen sample text | bugs.md |
| Known risk | `/api/order` can re-assign a paid report to another phone (bugs.md #17). Matters more with gifts | bugs.md #17 |

## 10. Mock plan

Mocks come before any renderer or pipeline code (CLAUDE.md §8). Full standalone HTML document,
430×830 cards, production print CSS, recipe tokens + Diwali accents, **the mocks' existing SVGs and
design kept** (Owner, 25 Oct).

- **History:** Mock 1.2 (catalogue, 84 pages) and Mock 2 v2 (one buyer, 47 pages) were built on the
  old shape (Owner, 23 Oct: 2 mocks). They stay saved; each new mock is a new artifact URL.
- **Mock 3 (owner said "start building", 26 Oct: plan A + B approved):**
  - **A. One real buyer on the new structure.** Suggested: the same sample person (Vikram Rao,
    timings reused from [mock/TIMING.md](mock/TIMING.md); **its WORDING rules are superseded** by R2/R3
    and the 25–26 Oct decisions: "nickname (Nth house)" pairs, bracketed reasons, "every answer gives a
    month range", "best stretch"/"window" and "gold rule stated in full every time" no longer apply), business owner, picked Money (his Marriage and Family pages assume "married with children" and must be rewritten in the one general version, 26 Oct), exact time, gift fields filled.
    Checks the front pages, the order, every area at full depth in R2, Better luck, end plan, page
    count against the §5 budget, the contents links, the gift page and the PDF gate.
  - **B. A catalogue of branches:** only the parts that change by input (life-stage cards are
    obsolete since 26 Oct): the
    student, job and home versions of Career and Business; age-band example swaps; the skipped-choice
    opener for each situation; the unsure-time note. No full second report.
- **Headless-PDF gate on both** (recipe §02, §09): Chrome `--headless=new --print-to-pdf`; pages are
  **323×623 pt** (not 595×842 A4); **page count = card count**; rasterize each page and confirm no
  clipping (`overflow:hidden` deletes silently); leak grep 0; §5b grep empty; R3 lint clean.
- The mock persona's name and any sample sentence go on the leak grep list.

## 11. Test plan

| Test | What it proves | Ref |
|---|---|---|
| Per-branch tests | One test per branch: each work type (4), each gender, each steering choice (6) + skipped, rising-sign vs Moon-sign (T0, T1-stable, T1-unstable, T2, T3 incl. Moon-changes-star), each age band (4, incl. 60+ never says "first job"), Self vs Gift (gift page p2, Note p3 only in Gift); Gift with name + message, with neither (default message, "for you"), with only one; delivery identical for Self and Gift (form number) | CLAUDE.md §12 |
| Area order | Chosen area first with the "You picked X" line (one test per area); skipped → **student, job, business owner, home** each give their table order; fine-tune swaps two unpinned neighbours only when the score gap rule is met; pinned positions never move | Owner, 25 Oct; E4 |
| Every section present | Every report has all 5 area sections and **Better luck right after them**, whatever the choice; no Part 2 / deep-dive page exists; no archetype page | Owner, 25 Oct |
| No assumed status | Marriage and Family text never contains "your wife", "your husband", "your spouse", "your marriage", "your children", "the right person", "marry again", "when children may come" (lint on every generated report) | Owner + uncle, 26 Oct |
| R3 lint | Bracket count in area prose; written date ranges only in 0.6 and 1.10, month labels allowed inside data pictures (O-30); "stretch" / "window" banned; "year" alone banned; nickname + house-number pair banned; AstroSage mention banned (report and landing page) | Owner, 25 Oct; §9 |
| Engine routing + AstroSage | `compute_diwali` routes through `compute_chart`/`compute_report`; birth accuracy 50/50 stays green | CLAUDE.md §21 |
| Engine units | Sade Sati phases incl. 2027 move back; strengths always 3; 12 distinct month rows; `as_of` pinned (same output on any run date); grade → Good / Steady / Careful mapping and the T2/T3 cap | E1-E5, E12 |
| PDF gate | **ESTIMATE, PROPOSED: 10 generated reports** (replaces the 23 Oct figure of about 21 for the old shape): 6 with a chosen area (Money, Career, Business, Family, Marriage, Better luck), spread across the 4 work types and both genders; 4 skipped-choice reports (one per situation); gift on and T3 folded into these. 323×623 pt, page count = cards, no clipping, contents links land on the right page | Owner, 25 Oct; recipe §09 |
| Print hides | Every non-report element (buttons, sticky bar, toggle) hidden by `@media print`; none appears in the PDF | CLAUDE.md §8 |
| Page chrome | Landing page served through `_serve_page_with_nav()` (no hand-rolled nav); report wired by `_wire_report_chrome` | CLAUDE.md §6, §11 |
| Language toggle | `#axlang` is **n/a until Hindi ships**; no link to `/hi/diwali` before that route exists | CLAUDE.md §2, §7, §9 |
| Reviews | No em-dashes or en-dashes in review text (if O-14 says reviews ship) | CLAUDE.md §5c |
| Money data | Real purchases classified through `is_test` / `pay_*` ids like every product; free passes count as testers | CLAUDE.md §13 |
| Boot gates | Import audit vs `requirements.build.txt`, server boot + `/healthz`, auth-gate check | CLAUDE.md §10 |
| 5-buyer test | No identical paragraph across 5 people (AI-on output only; deterministic fallback may be generic); no repeated sentence across one report's area sections | §9 |
| Leak + lint | Leak grep 0; banned-word lint clean on all generated reports and the landing page | §9 |
| Delivery order | AI text saved before the PDF is built; WhatsApp after the PDF; goes to the form number only, never Razorpay's | bugs.md #1; CLAUDE.md §1 |
| Price | Server charges 49900 paise for this product whatever the page path; stored on the order | CLAUDE.md §13 |
| Ad payload | Tracking carries the category (or "skipped") only; no birth data or gift note | Owner, 23 Oct |
| E2E | Playwright: form → preview (5 locked questions for the chosen or first area) → checkout | CLAUDE.md §10 |
| Report buttons | `axPdfDl` + `axShare` present (`tests/test_report_buttons.py`) | CLAUDE.md §9 |
| Test data | Every test phone number unique across the whole suite | CLAUDE.md §12 |
| Audit | §20 **convergent loop**: round 0 self-audit, then a fresh independent reviewer each round; stop only when 2 rounds in a row give the same confirmed set and 0 new bugs; max 4 rounds then diagnose; findings count only if reproduced; written to `docs/audits/` | CLAUDE.md §20 |
| Hand-off | `git fetch upstream` again right before the PR; diff against `upstream/aws-mysql` shows only this change; re-run the real gates on any agent's "done" | CLAUDE.md §14, §15 |
| Rule checklist | End of build: rule-by-rule §16 checklist (checked / n/a / skipped with reason) | CLAUDE.md §16 |

## 12. Build order checklist

| Step | Status |
|---|---|
| 1. Research rounds 1 and 2, uncle's research, structure check | done (19-23 Oct) |
| 2. Write this spec | done (23 Oct) |
| 3. Mock 1.2 + Mock 2 v2 (old shape) | done, kept as history (23-25 Oct) |
| 4. Life Blueprint + CI comparison; owner decisions (hybrid, R2/R3, pictures, order) | done (25 Oct) |
| 5. Spec updated to the re-order hybrid | **done (26 Oct): awaiting owner approval** |
| 6. Owner answers the open items in §13 that block Mock 3 | O-28 and O-30–O-33 **decided (26 Oct)**; O-29 (page budget) is settled after Mock 3 |
| 7. Mock 3 (one buyer + branch catalogue): build, PDF gate, R3 lint, owner approval | not started |
| 8. Engine work E1-E10, E12 + tests | not started |
| 9. Capture approved CSS/SVG as constants; write `render_diwali()` (§11 pipeline) | not started |
| 10. `narrative.py` SECTION_SPECS + lints + 5-buyer test | not started |
| 11. Wiring: `_render_for`, price, routes, 301, delivery reorder (bug #1), render queue | not started |
| 12. Landing page `/en/diwali` + form + preview; head block, sitemap, robot list (CLAUDE.md §2, §3) | not started |
| 13. Reviews on page + homepage card (CLAUDE.md §4, §5; see O-14) | not started |
| 14. Gates: import audit, pytest, `/healthz`, auth gate, E2E, robot, report buttons, PDF gate on ~10 reports, print hides, §20 convergent audit | not started |
| 15. §16 rule-by-rule checklist; fetch upstream; compare-URL hand-off | not started |
| 16. Owner deploys (agent never deploys) | not started |
| 17. Hindi twin, after English approval | later |

## 13. Open items (not decided; nothing here is invented as a decision)

**Still open**

| # | Item | Notes |
|---|---|---|
| O-1 | ~~Gift price~~ **DECIDED (Owner, 26 Oct: Self / Gift toggle)**: same ₹499; no second-order offer |
| O-2 | ~~Slug~~ **DECIDED (Owner, 26 Oct)**: `/en/diwali` (Hindi later `/hi/diwali`); file `pages/diwali.html` |
| O-3 | ~~Does the giver get a copy?~~ **DECIDED (Owner, 26 Oct: Self / Gift toggle)**: the person who fills the form is the only recipient (Self or Gift); the giver forwards it themselves |
| O-4 | **Tamil Deepavali date** | Sat 7 Nov from Hindutone only; confirm against Drik's Tamil calendar. README "Key dates" calls Sun 8 Nov "Choti Diwali (North Indian calendar)"; the Tamil oil-bath day is Sat 7 Nov. Confirm |
| O-7 | ~~Gender options~~ **DECIDED (Owner, 26 Oct)**: Male / Female only; no engine change |
| O-8 | ~~After 8 Nov~~ **DECIDED (Owner, 26 Oct)**: keep selling with the same span Nov 2026 – Oct 2027, `as_of` = Diwali day 8 Nov 2026; the puja-times page stays; revisit mid-Nov |
| O-10 | ~~AI failure handling / waiting time~~ **DECIDED (Owner, 26 Oct)** | (1) AI writing is **split into 4 calls run at the same time**: A = 5 front answers + Wrapped card; B = Money + Career + Business; C = Family + Marriage + Better luck; D = Year gone by, strengths, months to go slow, end plan. The wait is roughly the slowest piece (estimate: under a minute; measure on test reports); cost about the same (~₹10). (2) All maths (chart, dates, order, pictures, gold months) is computed before payment, at the preview. (3) **Right after payment:** a progress page ("Payment received ✓, writing your personal Diwali report now, usually about a minute") with a simple progress bar, ticks for each step, and **Diwali graphics (e.g. fireworks)**; design comes later. **Plus an instant WhatsApp text** ("being prepared") via the existing text-only template (`TWILIO_CONTENT_SID_TEXT`); the PDF follows. (4) Failed pieces retry automatically; **if not ready after 2 minutes**, send a "still on its way" message with the report link. Never send the backup bank text silently. Each Diwali call needs its own token limit (`MAX_TOKENS_BY_PRODUCT`) and timeout entry |
| O-11 | ~~Helpline line~~ | **DECIDED (Owner, 27 Oct): keep it generic, no number, no named organisation.** The report prints: "If a conflict at home feels serious, please talk to someone you trust or a trained helper." |
| O-12 | ~~Ad tracking match keys~~ **DECIDED (Owner, 26 Oct)**: same as other products (existing purchase event unchanged) + the chosen category |
| O-13 | ~~Fixed copy for locked pages~~ | **Note for you page: APPROVED as in Mock 3C (Owner, 27 Oct).** |
| O-14 | ~~Reviews~~ **DECIDED (Owner, 26 Oct)**: write 5–8 in house style (CLAUDE.md §5, §5c) |
| O-16 | **Practices wording** | Habits from the research (sleep, walking, fasting) read as health. **PROPOSED:** keep only money/routine/luck habits (budget, declutter, call 3 people, thank-you letter, donate a book). Confirm |
| O-17 | **Manglik rule for unsure time** | `manglik()` checks from the rising sign OR the Moon (`engine.py:312-333`). With T2/T3 the rising sign is unreliable. Use Moon-only then? |
| O-18 | ~~City list~~ **DECIDED (Owner, 26 Oct)**: Delhi, Mumbai, Bengaluru, Chennai, Ahmedabad, Kolkata, Pune, Hyderabad, Jaipur (9), each hand-checked vs Drik Panchang |
| O-19 | **Gift note handling** | Length limit; is the note ever sent to the AI (PROPOSED: no); escaped as plain text |
| O-22 | **Hindi fields now or later** | CLAUDE.md §11 says `compute_*` returns `_hi` twin fields. Author them now, or when Hindi ships? |
| O-25 | ~~Gift offer vs CCPA drip pricing~~ **RESOLVED (Owner, 26 Oct: Self / Gift toggle)**: the gift is a toggle on the form before checkout at the same price, so no later add-on |
| O-27 | **Sign name "Cancer" vs the §5b word "cancer"** | **Default: "Karka"** everywhere (used in the mocks; the change map lists "the sign Karka" as staying). Still open only if the owner prefers "Karka (Cancer)" or a lint whitelist. Same care for "fate" (contains "fat") and "secure" (contains "cure") in AI text |
| O-28 | ~~Exact chart fine-tune rule~~ **DECIDED (Owner, 26 Oct)** | Rule B, light touch: score each area 0–3 (main period, sub-period, Jupiter over/aspecting its houses); one top-down pass; swap neighbours only on a 2+ point gap; 1st place (and Marriage-2nd for unmarried over 25 when skipped) pinned; same rule when an area is picked. See §5 "Area order" rule 4 |
| O-29 | **NEW: page budget per section** | §5 page budget is an estimate (about 3 pages per area; 55–62 total). Owner to confirm per-section limits after Mock 3 |
| O-30 | ~~Dates outside the 2 date pages~~ **DECIDED (Owner, 26 Oct)** | Month names may appear INSIDE data pictures (kandils, gold-month diyas, Sade Sati strip, Wrapped card). Written text never lists date ranges: each "when" step = Best / Good / Careful time + a jump link to the timeline |
| O-31 | ~~When the buyer picks Better luck~~ **DECIDED (Owner, 26 Oct)** | The Better luck section moves to the top; the 5 areas follow the situation order (as if skipped); the 5 front answers and the end plan follow Better luck |
| O-32 | ~~§6a question wording~~ **DECIDED (Owner, 26 Oct)** | Swaps applied in the §6a lists: "the coming year" → "from this Diwali to the next", "good window" → "good time", "children's year ahead" → "for your children from this Diwali to the next", "this year" → "after this Diwali", Marriage (not married) Q1 → "When may the right person come into your life?" |
| O-33 | ~~"3 words" label~~ **DECIDED (Owner, 26 Oct): the Wrapped card** | Replaces "Your year in 3 words" on the free preview and the blessing page. Top: "Till next Diwali, your chart says" + the span line "From this Diwali to the next (Nov 2026 – Oct 2027)". **4 personal facts** (like Spotify Wrapped's top artist / top song): your strongest area, your best time, your careful time, your one big move. **Then 3 words, each with one plain line** saying what it means for you (e.g. "STEADY: your money grows slowly but surely"). Built from the buyer's chart; months allowed inside the card (O-30). The 5-buyer test covers it |
| O-34 | **Diya path: 6 diyas** | **DECIDED (Owner, 26 Oct):** the front-page diya path shows 6 diyas (Money, Career, Business, Family, Marriage + Better luck) |

**Closed (kept for history)**

| # | Item | Decision |
|---|---|---|
| O-5 | Gold-months rule and Dhana Yoga | **DECIDED (Owner, 23 Oct)**: see E6, E7 |
| O-6 | Strongest-area picker and strengths ranking | Strengths **DECIDED (Owner, 23 Oct)**, see E5. The picker is **replaced** by the area order (Owner, 25 Oct); its scoring signal is reused for the fine-tune (O-28) |
| O-9 | What is free on the preview | **DECIDED (Owner, 23 Oct): the CI pattern**, see §4 |
| O-15 | 5 question wordings per area | **DECIDED (Owner, 23 Oct)**, count of 5 confirmed (Owner, 25 Oct), see §6a (word fixes O-32) |
| O-20 | Diwali motifs | **DECIDED (Owner, 25 Oct)**: pictures and jobs, §2 rules 19–20 |
| O-21 | Exhibit choices | Pictures **DECIDED** (Owner, 25 Oct); remaining exhibit names settle in Mock 3 |
| O-23 | Money vs whole-life balance | **Closed by the hybrid** (Owner, 25 Oct): every area gets a full section, money included; the choice changes only the order |
| O-26 | Chopda Pujan time | Folded into O-18 |
| — | Dynamic vs re-ordered (README Q1) | **DECIDED (Owner, 25 Oct): the re-order hybrid** |
| — | Readability and depth (README Q2) | **DECIDED (Owner, 25 Oct): R2 + R3** |
| — | Front answers count, Better luck, end plan, "The read", archetype | **DECIDED (Owner, 25 Oct)**: 5 questions; short Better luck for everyone; end plan yes; "The read" yes; no archetype |
| — | Skipped choice | **DECIDED (Owner, 25 Oct, revised)**: order by situation, chart fine-tunes (§5) |
| — | Divorced / widowed wording | ~~"Love and companionship ahead"~~ **SUPERSEDED (Owner + uncle, 26 Oct)**: no life-stage question; one general Marriage version that never assumes status covers divorced and widowed buyers too |
