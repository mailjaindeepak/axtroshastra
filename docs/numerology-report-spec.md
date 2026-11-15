# Mulank Numerology Report (Career Intelligence theme) — build spec (structure APPROVED)

**STATUS: structure APPROVED by the owner (structure "B" below).** The visual mock
(`docs/mockups/mulank-report-mock.html` and `docs/mockups/mulank-preview-mock.html`) is built
strictly against the card list in this doc and is still pending owner approval. Per
`CLAUDE.md` §8 and §18, no renderer, pipeline, route or `narrative.py` code is written until the
mock is approved. This doc is the anti-drift source of truth: the build is checked against it
card by card; update it deliberately, never let the build drift silently.

## Product meta

| Field | Decision |
|---|---|
| Product key (internal) | `numerology_mulank` (proposed) |
| Name (customer-facing) | TBD (working title: AxtroShastra Numerology Report) |
| Slug / route | TBD (proposed `/en/numerology`) |
| Language | English only for now; Hindi twin deferred (see Open decisions) |
| Theme | Career Intelligence theme, reused as-is (`CI_CSS` / `CI_DEFS`), one card per page, 430 x 830 px cards, per `docs/career-intelligence-report-recipe.md` |
| What changes | Section content only. Format, CSS, decoration system and the three fixed pages are frozen. |
| Fixed pages | Cover, "A Note for You", Thank-you stay identical in format to the Career Intelligence report; only the name/birth line changes. Their trust/system lines say "numerology", not "Swiss Ephemeris / Lahiri" (those are chart-reading claims and would be false here). |
| Price / funnel | Price TBD. Default funnel per `CLAUDE.md` §1: form, preview, contact popup, payment, report + PDF + WhatsApp. See "Funnel preview" below. |
| Homepage | Undecided (see Open decisions, `CLAUDE.md` §4) |

## Approved decisions (owner-confirmed)

1. **Input: date of birth only.** No name number, no birth time, no place, no gender. All wording is
   gender-neutral; there is no gender branching, so `CLAUDE.md` §12 branch tests do not apply.
2. **Invalid or partial DOB shows an explicit inline error, never a silent default** (`CLAUDE.md` §1):
   blocks submission for an incomplete date, an impossible date (e.g. 31 Feb) or an out-of-range
   date (no future dates; earliest year to be confirmed, see Open decisions).
3. **Method, stated explicitly inside the report** (Core Numbers card 1 and the personal-year card):
   - **Mulank** = the birth day reduced to a single digit. Example: 29 -> 2 + 9 = 11 -> 1 + 1 = 2.
   - **Bhagyank** = all digits of the full date of birth added, then reduced to a single digit.
   - **11 and 22 are ALWAYS reduced to a single digit** (no master-number carve-out). The working
     is shown on the page every time, including the intermediate step.
   - **Personal year** = birth day + birth month + the digits of the calendar year, reduced to a
     single digit (11 and 22 reduced as above). Cycle runs January to December.
   - Ruling planets (traditional mapping): 1 Sun, 2 Moon, 3 Jupiter, 4 Rahu, 5 Mercury, 6 Venus,
     7 Ketu, 8 Saturn, 9 Mars.
4. **Personal year is computed DYNAMICALLY from today's date, never hardcoded.** The renderer takes
   `today` (the report-generation date), computes the personal year for `today.year` (current year)
   AND `today.year + 1` (next year), and shows both side by side. The year labels on the page are
   those two years. The mock shows the sample persona's working for 2026 and 2027 only because the
   mock was prepared on 1 November 2026.
5. **Personalisation keyed to the Mulank + Bhagyank PAIR**, not Mulank alone. Interpretation text for
   Core Numbers (pair), Personality, Strengths & Challenges and Career & Relationships comes from a
   pair table (9 x 9 = 81 authored entries) plus per-number tables; personal-year text is keyed to
   the year number (1-9) and tinted by the pair. Avoid repetitive or generic predictions: two
   different pairs must never produce the same paragraph.
6. **Belief, not science.** Every interpretation is presented as traditional numerological belief,
   not scientific prediction: (a) disclaimer in "A Note for You", (b) a short line under each
   interpretation section (on its last card), (c) in the Thank-you page.

## Computed data (deterministic engine, not the LLM)

- `mulank`, `bhagyank`, `personal_year(today.year)`, `personal_year(today.year + 1)`, each with the
  step-by-step working strings that the report prints (including the intermediate sums).
- Derived lookups (lucky numbers, colours, days, gemstone, compatibility table) are fixed tables
  keyed by Mulank / Bhagyank, authored once and reviewed. Gemstone wording is always "traditionally
  associated with", never a recommendation, never medical.
- The LLM (if used at all) writes prose only and never computes a number.

## Language & tone rules (apply to every section)

- Modern, plain English. Insight first, the numerological reason after (optional small "Numerological basis" box).
- Strictly non-deterministic: "your number indicates", "this year may favour", "you may find". Never "you will", never guaranteed outcomes, never a money figure.
- Voice: mature, respectful, steady, optimistic. Gender-neutral throughout.
- **Vocabulary rule (`CLAUDE.md` §5b):** every word in the §5b Health & Wellness flagged list is banned from all ad-facing text (page, report, preview, reviews, ads). Run the §5b substring scan before any publish and mind false positives. Preferred framing: "growth areas", "steady", "clarity", "composed", "high stakes", "unsure", "friction". "Challenges" is allowed; challenges are framed as growth, never as flaws.

## Personalisation rule (`CLAUDE.md` §22)

Every section that states a finding (numbers, traits, rankings, prose) must be generated from the buyer's own computed data. Generic text is allowed only on the cover, A Note for You, Thank-you and the methodology wording. **The mock persona is MOCK-ONLY**: sample DOB 29 July 1990, first name "Kiran Mehta", Mulank 2, Bhagyank 1, personal years 1 (2026) and 2 (2027). No persona name, date or number may survive into a real report; the gate must include a persona-leakage check (grep a real render for the persona name, "29 July 1990" and the working strings).

Hand-verified persona arithmetic (mod-9 cross-check in brackets):
- Mulank: 29 -> 2 + 9 = 11 -> 1 + 1 = 2 [29 mod 9 = 2].
- Bhagyank: 29 / 07 / 1990 -> 2+9+0+7+1+9+9+0 = 37 -> 3 + 7 = 10 -> 1 + 0 = 1 [37 mod 9 = 1].
- Personal year 2026: day 29 -> 2+9 = 11; month 07 -> 7; year 2026 -> 2+0+2+6 = 10; 11 + 7 + 10 = 28 -> 2 + 8 = 10 -> 1 [2+7+1 = 10 -> 1].
- Personal year 2027: 11 + 7 + (2+0+2+7 = 11) = 29 -> 2 + 9 = 11 -> 1 + 1 = 2 [2+7+2 = 11 -> 2].

## The structure (APPROVED "B") and the exact card list

Sections: Cover | A Note for You | Core Numbers | Personality | Strengths & Challenges |
Career & Relationships | Personal-Year Analysis | Practical Guidance | Thank-you.
A section may span several cards; one card = one 430 x 830 page.

**Paid report = 15 cards exactly.** The mock is built against this list and the print gate asserts 15 pages.

| # | Section | Card | Type |
|---|---|---|---|
| 1 | Cover | Cover | fixed (welded) |
| 2 | A Note for You | Note, includes the belief-not-science disclaimer | fixed (welded) |
| 3 | Core Numbers | Your two numbers: Mulank + Bhagyank hero cards, the calculation working for each, the method box (11 and 22 reduced) | content |
| 4 | Core Numbers | Ruling planets and how the pair works together (Mulank planet, Bhagyank planet, the pair reading), numerological-basis box, disclaimer line | content |
| 5 | Personality | How you come across (4 pair-keyed points) | content |
| 6 | Personality | Exhibit: four spectrum dials for the pair, legend, "the read", disclaimer line | exhibit |
| 7 | Strengths & Challenges | Strength / growth-area paired table (5 rows, pair-keyed) | content |
| 8 | Strengths & Challenges | Exhibit: balance bars (strength and its matching growth edge), disclaimer line | exhibit |
| 9 | Career & Relationships | Work: styles and fields traditionally associated with the pair | content |
| 10 | Career & Relationships | Relationships: how you bond, plus Mulank compatibility (easy / neutral / needs attention), disclaimer line | content |
| 11 | Personal-Year Analysis | Current year and next year side by side, with the working for each | content |
| 12 | Personal-Year Analysis | Exhibit: the nine-year cycle with the two years marked, disclaimer line | exhibit |
| 13 | Practical Guidance | Lucky numbers, colours, days, gemstone ("traditionally associated with") | content |
| 14 | Practical Guidance | Specific actions for the two years (start / continue / ease off), disclaimer line | exhibit/blocks |
| 15 | Thank-you | Thank-you, cross-sell, disclaimer | fixed (welded) |

Card contents (all generated from the buyer's computed pair; none generic except 1, 2, 15 and the method box):

- **3. Your two numbers.** Two hero tiles (Mulank n with its ruling planet; Bhagyank n with its ruling planet), then a working table: birth day -> digits -> sum -> reduced (showing any 11 / 22 step) and full DOB digits -> sum -> reduced. A callout states the method and the 11 / 22 rule in plain words.
- **4. Ruling planets and the pair.** Three icon points: Mulank planet reading, Bhagyank planet reading, how the two work together (supportive, neutral or contrasting, from the pair table). Numerological-basis callout (planet friendship). Short belief-not-science line.
- **5. Personality.** Verdict line plus four points (first impressions, inner drive, decisions, behaviour when attention turns to you), each keyed to the pair.
- **6. Personality dials.** Four dials with dot positions taken from the pair table; legend rows; "the read".
- **7. Strengths & Challenges.** Five strength / growth-area rows from the pair table; a callout that frames challenges as growth areas.
- **8. Balance bars.** Three strengths each followed by its growth edge (terracotta "watch" bar); legend; "the read".
- **9. Work.** Verdict line, three or four points (work style, fields traditionally associated, working with others, a watch-point), numerological-basis callout. No money figures, no outcomes.
- **10. Relationships.** Points on closeness, independence, communication, a pattern to watch; compatibility table for the buyer's Mulank (easy / neutral / needs more attention; traditional tables vary by school).
- **11. Personal years.** Two tiles (year label, personal-year number, one-line working), a comparison table (theme, pace, best used for), and a callout with both workings written out. Year labels and numbers come from `today`.
- **12. Cycle exhibit.** Nine-step cycle drawn as an SVG with the two computed years highlighted and labelled; legend; "the read".
- **13. Quick reference.** Four tiles: lucky numbers, colours (with swatches), days, gemstone ("traditionally associated with"); a gentle-note callout that these are optional traditional associations.
- **14. Actions.** Start / continue / ease-off blocks for the current year and for the next year, each a specific action; "the read".
- **Cards 1, 2, 15.** Welded pages, identical format to Career Intelligence; only the name / birth line / report date change.

## Funnel preview (free / locked state) — `CLAUDE.md` §1

Mocked separately in `docs/mockups/mulank-preview-mock.html` (2 cards). Mirrors the Career
Intelligence teaser pattern: real computed data free, remaining content shown as blurred locked rows
with a lock icon and a pill CTA.

- **Free part (real, computed from the buyer's DOB):** the buyer's real Mulank and Bhagyank with the
  calculation working shown, the ruling planet of each, and one or two personalised lines about the pair.
- **Locked / blurred:** rest of Core Numbers (how the pair works together), Personality,
  Strengths & Challenges, Career & Relationships, both personal years, Practical Guidance.
- **Must NOT be given away free:** any personal-year number or forecast, and any lucky number,
  colour, day or gemstone. The blurred text behind the locks must be neutral filler, never the real
  paragraph (a blurred real paragraph is still in the DOM).
- **Contact popup placement:** after the preview is shown, tapping the unlock CTA opens the contact
  popup (name + phone, optional email) BEFORE payment; its phone number is what WhatsApp delivery
  uses (`CLAUDE.md` §1). Spec note only: no funnel code is built at the mock stage.
- The EN/HI toggle, if added later, clears the name and the preview on switch (`CLAUDE.md` §7).

## Gates for the mock (recipe §09) and what the renderer must later do

- Paid mock: 15 `<section class="page` cards; preview mock: 2.
- Headless Chrome `--print-to-pdf` of the standalone file: pages 323 x 623 pt, page count == card count, no card's last element clipped by `overflow:hidden`.
- Leak gate: zero hits for the source report's text (its product name, job / role / salary prose, source persona name). Meta §5b flagged-word substring scan: zero real hits.
- Renderer (later, after mock approval): reuses `CI_CSS` / `CI_DEFS` and the welded pages as constants, computes `today`, current and next personal year from the DOB, string-replaces per-person values; adds a persona-leakage test.

## Open decisions (still need the owner's answer)

1. **Hindi twin:** deferred? If later, `CLAUDE.md` §7 build order applies.
2. **Homepage card (§4):** yes or no, plus homepage review entries.
3. **Reviews (§5):** 5-8 on-page reviews to be written later, site voice, no em-dashes (§5c), scanned against §5b.
4. **DOB range limits:** earliest accepted year (proposal: 1900) and rejection of future dates; confirm.
5. **Name, price, slug.**
6. **Fixed-page wording:** the cover and thank-you trust lines were changed from "Swiss Ephemeris / Lahiri ayanamsa" to a numerology line; confirm.

(Resolved by the owner and recorded above: inputs, gender branching, master-number convention,
personal-year coverage (current + next), structure, belief-not-science framing, preview scope.)

## Build order (per `CLAUDE.md` §8 and §18)
1. Structure approved (this doc).
2. Visual mocks (paid report + preview) built against this card list, printed to PDF, reviewed and approved.
3. Engine: Mulank, Bhagyank, personal year (dynamic from today), lookup tables, with tests including edge dates (e.g. day 29 / 11 / 22 reductions, year rollover on 31 Dec / 1 Jan).
   Status: compute engine done (`numerology.py`, `tests/test_numerology.py`); renderer waiting on mock approval.
4. Only then wire the pipeline, route, pricing and landing page; then reviews, sitemap and gates.
