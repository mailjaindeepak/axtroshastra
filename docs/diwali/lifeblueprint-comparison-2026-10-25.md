# Diwali report vs Life Blueprint: comparison (25 Oct 2026)

Why we did this: the owner said the Diwali mocks are "visually okay but very difficult to understand and lack content". The uncle (Deepak) asked how Life Blueprint covers career, marriage, money and more in a way buyers find easy to understand and buy. He proposed one fixed section list for everyone, re-ordered by theme.

Four read-only agents did the work. Code was read at `upstream/aws-mysql` 62f899f and sales came from `docs/db-report/data.json` (snapshot of 14 Oct). Working files are in the session scratchpad (`cmp_bp/`, `cmp_sell/`, `cmp_read/`). A Life Blueprint report was rendered for the same sample buyer (Vikram Rao) from the deployed code, using bank text only.

## 1. Life Blueprint: what the buyer gets
- **Size:** about 46–55 pages (430×830). Part 1 is 10 life areas (career, money, marriage, children, home, foreign, energy and routine, growth, family, "is now the moment"), at about 3 pages and 280–320 words each. Part 2 is about 18 short "how we read it" pages. Then a remedy page and Thank you.
- **Same 9-step pattern in every area** (`report_view.py:2297-2326`):
  1. verdict pill (Thriving / Building / Watch)
  2. headline
  3. "What this means"
  4. "Why it reads this way", then "In simple words…"
  5. what's working for you / worth watching
  6. dated "chapters" (Favorable / Steady / Watch)
  7. Do (3) and Watch (1)
  8. a balance note
  9. a reflection question
- **Plain language:** about 7 astrology terms, each defined once in a glossary. Planet periods are called "chapters". There is a worked example from the buyer's own career reading. Visuals: a 10-area Life Wheel, the kundli, coloured tags.
- **Personal vs fixed:** the tags, headlines, "why" lines, helping and hindering planets, dated periods, kundli and tables are personal. About 50–60% of the words (Do/Watch lists, period notes, explainer pages) are the same for everyone.
- **One fixed section list for everyone:** `compute_blueprint` (products.py:516) takes no gender, work type, life stage or theme. This is the uncle's model.

## 2. Life Blueprint: selling side (data.json)
| | Life Blueprint | Career (CI + Growth) | Marriage |
|---|---|---|---|
| Paid | 88 | 343 | 43 |
| Revenue | ₹46,412 (29.8%) | ₹85,609 (54.9%) | ₹19,057 |
| Preview → paid | 6.4% | 14.2% | 4.1% |
| Average order | ₹527 | ₹250 | ₹443 |

- **X traffic:** 86 of 88 sales came from X ads, which convert at **15.6%** (CI 15.9%). The low overall rate comes from non-X previews.
- **Funnel:** 4,839 visits → 1,385 previews → 117 checkouts → 88 paid. The median time to pay is about 2 minutes.
- **Landing page:**
  - a free preview with the buyer's name on a report "cover"
  - **5 big life questions** up front
  - a **10-area Life Wheel** with traffic-light tags
  - locked questions and tiles
  - the price hidden until the preview appears
  - the phone number taken in the form
- **What not to copy:** no sample report; reviews that look invented; a "25,000+ reports" claim that doesn't match about 4,960 real previews (a trust and legal risk); 0 Hindi sales.

## 3. Readability: our Mock 2 v2 vs Life Blueprint (same buyer)
| | Diwali Mock 2 | Life Blueprint |
|---|---|---|
| Pages / words | 47 / 5,779 | 46 / 5,022 |
| Median words per page | 123 | 111 |
| Average sentence | 10.9 words | 9.8 words |
| **Month mentions per 100 words** | **5.7** | 1.9 |
| **Date ranges per page** | **1.5** (up to 9 on one page) | 1.0, kept in one timeline box |
| **Bracketed asides per page** | **2.8** (131 in total) | 0.2 |
| **Share of words inside brackets** | **12.6%** | 0.6% |
| "What it means / what to do" sentences | 17% | 18% |

**The conclusion:** "lacks content" does not mean too few words; we have more words. It means **too few words that explain**. The causes, with counts:
1. Every claim carries its chart reason in brackets (131 brackets).
2. Too many dates. The same verdicts repeat on about 11 pages: "Nov 2026" ×27, "Jun–Jul" ×20.
3. Paired names like "part for yourself (1st house)" (×22) are longer, and the reader still has to learn both.
4. Thin meaning per claim: about 120 words per page against about 500 per life area in Life Blueprint.
5. About 12 of 47 pages carry no reading: covers, contents, dividers, link pages.
6. "Astrology made simple" comes on p42, after 41 pages of terms.

## 4. Uncle's proposal: dynamic vs (A) "same sections, own chart, re-ordered by theme"
**The owner confirmed it means (A):** text is still computed from each buyer's chart (CLAUDE.md §22 kept).

**Key fact:** our design is already mostly (A). Only the Part 0 answers, the Part 2 deep dive (3 of 47 pages in Mock 2) and the fresh-start plans follow the theme. Every other area gets 1–2 pages. That is why it reads as thin.

| | Current dynamic | (A) re-ordered |
|---|---|---|
| Depth | 1 area deep, 4 as headlines | Every area at full depth |
| Clarity | The chosen topic appears in 2 places (Part 1 + Part 2) | One place per topic (the Life Blueprint model) |
| Pages | 47 | About 55–62 (estimate) |
| Branches (life stage / work / gender) | Needed | **Still needed** inside sections |
| Build / test | 6 deep-dive paths, 18+1 PDF-gate reports | 1 path + sorting, about 9 gate reports (estimate) |
| Launch risk (8 Nov) | Highest | Lower |
| New risk | — | 5 sections can repeat the same months and reasons, so each area needs its own house and planet focus |

## 5. Recommendations (not decided; for the owner)
- **R1. Hybrid (A):**
  - Every area gets a full section, and the chosen area comes first, with an opener line ("You picked Career, so it comes first").
  - The Part 0 5 answers, the locked preview questions and the fresh-start plans still follow the theme.
  - Each area's deep-dive questions merge into its section, and Part 2 is deleted.
  - The life-stage, work-type and gender branches stay inside the sections.
  - Owner calls needed: what happens when the choice is skipped (a fixed default order, or keep the chart picker), and where Better luck goes (one short positives section for everyone).
- **R2. Copy Life Blueprint's per-area pattern:**
  1. one-word verdict
  2. "What this means for you" (2–3 sentences, with real examples such as hiring, a branch, a partner deal, gold)
  3. Do / Watch
  4. one short "Why" line at the end
  5. this year's chapters
- **R3. Fix the density:**
  - Chart reasons go only in the "Why" line, never as brackets inside sentences.
  - Each date range appears in only 2 places (the year timeline and the 12 months); elsewhere write "your best stretch (see p.NN)".
  - Use either the plain name or the house number, not both.
  - Move a short "how to read this" up front.
  - Merge the pointer pages.
- **R4. Copy Life Blueprint's selling patterns:** the name on a preview "cover", 5 big questions, a Life-Wheel-style overview of every area with traffic-light tags, and the price shown after the preview. **Don't copy** the invented reviews or the inflated counts. **Add** a sample report (which CI has).
- **Life Blueprint's own weak points to avoid:**
  - repeated fixed lists (50–60% the same text)
  - do-advice that ignores the verdict
  - sample-persona sentences shown to every buyer
  - dead links
  - AI text that is generated and paid for but never shown in English

  These were added to `docs/bugs.md` as #19–#23.

## Before/after rewrites (readability agent; soft voice, no promises, no §5b words)
1. **Before:** "Likely steadier from Nov 2026 (Jupiter moves into the part for yourself, 1st house, and your current planet period, Mercury–Jupiter dasha, runs all year)."
   **After:** "Yes, things look steadier from November 2026. In simple words: the planet of growth comes to the part of your chart that stands for you, so your own effort tends to count for more this year. A good first step: write down money in and money out each month."
2. **Before:** "The rule we use: a wealth combination is present when the ruler of the 5th house links to the ruler of the 2nd or 11th house…"
   **After:** "Your chart has a wealth combination. What it means for you: money tends to build slowly and steadily through planning and your good name, more than through sudden wins. Savings you leave untouched usually serve you best. (Why: your planning planet supports your money planet.)"
3. **Before:** "Nov – Dec 2026, Apr 2027, Jul – Oct 2027. Jupiter in the part for yourself (1st house) looks on the partner part (7th house)…"
   **After:** "Your bond is a loyal, serious one. This year, the end of 2026 and the second half of 2027 look warm for the two of you, a good time for a family trip or a shared plan. In January–February, give sharp words a day before you reply."

---

# Part 2: Career Intelligence sweep and the "best of three" plan (25 Oct, after owner decisions)

Owner decisions already applied: the re-order hybrid; R2 + R3; keep the Diwali mocks' SVGs and design; say "best time", never "stretch" or "window"; never mention the AstroSage check to buyers.

## Metrics (same scripts, all three reports)
| | Career Intelligence | Diwali Mock 2 | Life Blueprint |
|---|---|---|---|
| Pages / words | 59 / 4,382 | 47 / 5,779 | 46 / 5,022 |
| Median words per page | 69 | 123 | 111 |
| Astrology terms per 100 words | **0.6** | 5.9 | 4.3 |
| Month mentions per 100 words | **0.35** | 5.7 | 1.9 |
| Brackets per page | 0.2 | 2.8 | 0.2 |

**CI is almost free of jargon and dates.** Astrology appears only in boxed "Astrological basis" notes.

## CI strengths (to take)
- **Payoff first:** p2 answers 9 questions with one-line verdicts, and p3 gives one timeline with a single best period.
- **One rhythm all the way through:** a claim headline, then a picture, then "The read" one-liner.
- **Consulting-report structure:** parts, roadmap, "if you do only one", 30/90/365 days, 5 takeaways.
- **Calm and honest:** "This report never predicts a figure"; every strength is paired with its shadow.

## CI negatives (to avoid)
- **Frozen sample text with find-and-replace**, so contradictions show in the public sample itself (bugs #2, #13, #14). Examples: the headline says "Reinventor" but the matrix says "Strategic Builder"; the phase is "repositioning" on one page and "consolidation, ends ~2029" on the next; "Year 2" and "Year 3" disagree; "For two decades" appears whatever the buyer's age.
- **Thin pages and repetition:** a median of 69 words per page, half-empty pages, and the plan shown twice.
- **Score tiles that feel made up:** 5 of 6 say "Mod–High", and the bars all say "present".
- **Vague timing:** multi-year "windows", and "Year 1/2/3" instead of months.
- **Career only**, with abstract consulting words and few real-life examples.

## Best-of-three plan for the Diwali report (proposed)
1. **Front:** CI's verdict page. 6–9 big questions for the chosen theme, each with a one-word answer (Good / Steady / Careful) and one line. Then ONE "Your year at a glance" timeline. Dates appear only there and in the 12-month table.
2. CI's "A note to you", plus a short "how to read this", up front.
3. **Every area is a full section** from the buyer's own chart, chosen area first, with an opener line. Inside each, use the R2 pattern:
   1. one word
   2. what this means for you (real-life examples)
   3. do / watch
   4. one short plain "why" line (CI's "Astrological basis" box)
   5. when ("best time / good time / careful time")
4. **Close each section with CI's "The read" one-liner**, drawn on the existing Diwali SVGs.
5. **CI's archetype idea:** only if it is computed and checked for consistency; otherwise skip it.
6. **End with CI's roadmap:** top priorities with "if you do only one", 30/90/365 days, and 5 takeaways, each written once.
7. Keep the honesty line ("we never predict a figure"). No AstroSage mention.

**Avoid:**
- frozen text (gate: render 2 charts and fail if any sentence matches)
- card + exhibit duplication and half-empty pages
- score words that don't follow the score
- "Year 1/2/3" and multi-year windows
- Life Blueprint's fixed Do/Watch lists and inflated claims
- Mock 2's brackets, repeated dates, paired names, Part 1/Part 2 split and pointer pages

**Target:** about 55–60 pages at about 110–130 words each, every page a reading page.
