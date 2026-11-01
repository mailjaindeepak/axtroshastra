# Mulank Numerology Report (Career Intelligence theme) — DRAFT build spec

**STATUS: DRAFT, PENDING APPROVAL.** The section list below is NOT finalised. Per
`CLAUDE.md` §8 and §18, no mock, renderer or pipeline code is written until this spec is
approved. Once approved, this doc becomes the anti-drift source of truth; until then, edit
it freely.

## Product meta

| Field | Decision |
|---|---|
| Product key (internal) | `numerology_mulank` (proposed) |
| Name (customer-facing) | TBD (working title: AxtroShastra Numerology Report) |
| Slug / route | TBD (proposed `/en/numerology`) |
| Language | English only for now; Hindi twin deferred (see Open decisions) |
| Theme | Career Intelligence theme, reused as-is: light Business-Growth (`_VYAPAR_CSS`) palette, one card per page, 430 x 830 px cards, per `docs/career-intelligence-report-recipe.md` |
| What changes | Section content only. Format, CSS, decoration system and the three fixed pages are frozen. |
| Fixed pages | Cover, "A Note for You", Thank-you stay identical in format to the Career Intelligence report; only the name/birth line changes. |
| Price / funnel | TBD. Default funnel per `CLAUDE.md` §1: form, teaser, contact popup, payment, report + PDF + WhatsApp. Teaser must be real computed data. |
| Homepage | Undecided (see Open decisions, `CLAUDE.md` §4) |

## Computed data (deterministic engine, not the LLM)

- **Mulank (root number, 1-9):** reduced from the birth *day* of the month (e.g. 28 becomes 2+8=10 becomes 1). Ruling planet follows the standard mapping (1 Sun, 2 Moon, 3 Jupiter, 4 Rahu, 5 Mercury, 6 Venus, 7 Ketu, 8 Saturn, 9 Mars).
- **Bhagyank (destiny number, 1-9):** reduced from the sum of all digits of the full date of birth.
- **Personal year:** reduced from birth day + birth month + the target calendar year.
- Derived lookups (lucky numbers, colours, days, gemstone, compatibility table) are fixed tables keyed by Mulank/Bhagyank, authored once and reviewed.

## Language & tone rules (apply to every section)

- Modern, plain English. Insight first, the numerological reason after (optional small "Numerological basis" box).
- Strictly non-deterministic: "your number indicates", "this year may favour", "you may find". Never "you will", never guaranteed outcomes, never a money figure.
- Voice: mature, respectful, steady, optimistic.
- **Vocabulary rule (`CLAUDE.md` §5b):** every word in the §5b Health & Wellness flagged list is banned from all ad-facing text (page, report, reviews, ads). That covers the mental-health, medical and body/fitness groups and the borderline words (pressure, calm, relief, tension, worry, and similar). Run the §5b substring scan before any publish and mind false positives. Preferred framing: "growth areas", "steady", "clarity", "composed", "high stakes", "unsure", "friction". Section 10 is framed as growth, never as flaws.

## Personalisation rule (`CLAUDE.md` §22)

Every section that states a finding (numbers, traits, rankings, prose) must be generated from the buyer's own computed data. No sample persona name, number, trait or ranking may survive into a real report. Generic text is allowed only on the chart-independent pages: Cover, A Note for You, Thank-you. Gate should include a persona-leakage check, as in the recipe's §09.

## The sections (DRAFT, one card per page, order not final)

Layout card types are drawn from the recipe's component library (§08) and exhibit format (§05). Exhibit cards follow a content card only where "a picture beats the paragraph" (recipe rule of thumb).

### 1. Cover (fixed page)
- Purpose: brand, title, name and birth line.
- Data: name, date of birth, report date only.
- Card: welded cover template (constellation). Generic, identical for all.

### 2. A Note for You (fixed page)
- Purpose: warm one-page introduction setting the tone.
- Data: first name only.
- Card: welded flower-tile mandala + framed note. Generic.

### 3. Your Mulank
- Purpose: introduce the core number and its ruling planet in plain language.
- Data: Mulank (from birth day), ruling planet table.
- Card: hero number card (large numeral, planet icon, one-line theme) with a small "Numerological basis" box. Optional exhibit: number-on-1-to-9 spectrum dial.
- Content generated from the buyer's own Mulank; no sample number.

### 4. Core personality and strengths
- Purpose: who they are day to day, with 5-7 strengths, insight first.
- Data: Mulank (and Bhagyank only as a light secondary tint).
- Card: prose card + strength list; exhibit: ranked strength bars.
- Generated per buyer; strengths vary by Mulank table.

### 5. Career and money
- Purpose: work styles that may suit, how they relate to earning and saving, suitable fields. Non-deterministic; no amounts.
- Data: Mulank, Bhagyank.
- Card: prose card; exhibit: comparison bars (employee vs independent inclination) or 2x2 matrix.
- Generated per buyer.

### 6. Relationships and Mulank compatibility
- Purpose: relationship style, plus which Mulanks tend to pair easily and which need more attention.
- Data: Mulank; fixed compatibility table for all 9 numbers.
- Card: prose card + compatibility grid highlighting the buyer's row.
- Generated per buyer. Gender branching not assumed (see Open decisions).

### 7. Lucky numbers, colours, days and gemstone
- Purpose: practical, shareable quick-reference.
- Data: Mulank (and Bhagyank for secondary numbers) via fixed lookup tables.
- Card: four-tile icon card (numbers, colours with swatches, days, gemstone). Gemstone wording must stay non-medical and non-deterministic ("traditionally associated with").
- Generated per buyer from tables.

### 8. Bhagyank and how it works with Mulank
- Purpose: explain the destiny number and the interplay of the two numbers (supportive, neutral, or contrasting).
- Data: Mulank, Bhagyank, pairing table.
- Card: venn or paired-number card; exhibit: 2-circle venn or balance matrix.
- Generated per buyer.

### 9. Personal year forecast
- Purpose: theme of the current personal year (1-9 cycle) and what it may favour; optional light view of the next year.
- Data: birth day + birth month + target year, reduced.
- Card: year-on-cycle timeline card (9-step cycle with the buyer's year highlighted); exhibit: cycle timeline.
- Dated content: computed from the report date, never hardcoded.

### 10. Growth areas
- Purpose: honest but encouraging areas to develop. Framed as growth, never as weaknesses or flaws.
- Data: Mulank (plus Bhagyank interplay).
- Card: two-column "Strength / Growth area" paired card in the recipe's balance layout.
- Generated per buyer; copy reviewed against the §5b word list.

### 11. Thank-you (fixed page)
- Purpose: closing, cross-sell, constellation.
- Data: first name only.
- Card: welded closing mandala template. Generic.

## Open decisions (unresolved, need the user's answer before build)

1. **Inputs:** date of birth only, or also a name number (Namank, via name-to-number mapping)? Draft assumes DOB only. Birth time and place are likely not needed (numerology does not use them), which would also let the form be slimmer than Career Intelligence's five fields.
2. **Gender branching:** if any content branches on gender, `CLAUDE.md` §12 requires a test per branch for every section. Draft assumes no gender input and no branching.
3. **Hindi twin:** deferred? If later, §7 build order (English first, then Hindi dictionary, leakage gate) applies.
4. **Homepage card (§4):** does this product get a homepage card and homepage review entries? Needs an explicit yes or no.
5. **Reviews (§5):** 5-8 on-page reviews to be written later, in the site voice, no em-dashes (§5c), scanned against §5b.
6. **DOB inline-error validation (§1):** proposed rule is to block submission with a clear inline message for an out-of-range, impossible (e.g. 31 Feb) or partial date, and never silently default to a guessed value. Exact range limits (earliest year, no future dates) to be confirmed.
7. **Final section list, page count and exhibits:** the 11 sections above are a draft; confirm, add or drop sections, and which get an exhibit card.
8. **Name, price, slug, and personal-year coverage** (current year only vs current plus next year).
9. **Master numbers (11, 22) and reduction convention:** use the plain 1-9 reduction only, or acknowledge compound numbers on the Mulank page.

## Build order (per `CLAUDE.md` §8 and §18)
1. Approve this spec.
2. Engine: Mulank, Bhagyank, personal year, lookup tables, with tests (including edge dates).
3. Mock in the Career Intelligence theme, print to PDF, get it approved.
4. Only then wire the pipeline, route, pricing and landing page; then reviews, sitemap and gates.
