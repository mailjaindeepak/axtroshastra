# Career Intelligence Report — finalised build spec (source of truth)

**This is the anti-drift spec.** The report is built strictly against this document and
cross-checked section by section. If the build and this doc disagree, this doc wins —
or the doc is updated deliberately, never the build silently. Extracted from the
manager's brief; do not re-interpret from memory while building.

## Product meta

| Field | Decision |
|---|---|
| Product key (internal) | `career_intelligence` |
| Name (customer-facing) | **AxtroShastra Career Intelligence Report™️** |
| Subheadline | A Personalised Roadmap for Your Next Professional Chapter |
| Tagline | Powered by personalised Vedic astrological analysis |
| Slug / route | `/en/career-intelligence` (English only — see below) |
| **Language** | **ENGLISH ONLY for now** — Hindi twin explicitly on hold (deliberate, documented exception to `CLAUDE.md` §7). No `.hi.html`, no `career_intelligence_hi.py`, Hindi-leakage gate N/A. |
| **Theme (APPROVED)** | **LIGHT — the Business-Growth (`_VYAPAR_CSS`) palette**: cream/sand cards, gold accents, dark serif ink. Reuses Business-Growth design elements — `_VYAPAR_DEFS` icon set (via `<use href="#i-…">`), the cover **constellation**, the **fan** ornament. (A charcoal/dark variant was built and rejected; light is the one to ship. Approved output = `career-intelligence report - v5.pdf`, 55 pages, 323×623 pt.) |
| **Report shape (APPROVED)** | 55 pages: each content card followed by its McKinsey **exhibit** card (radar, 2×2 matrices, roadmap/journey arcs, donut, venn, ranked/comparison bars, life-stage bars, priority matrix, spectrum dials, timelines). The approved static mock is the visual target the renderer must reproduce per-person. |
| Audience | 40–60, LinkedIn professionals (NOT the Meta/₹499 audience) |
| Price | **Display: ~~₹4,999~~ ₹1,999.** Actual amount charged = **₹1,999** (`amount_paise = 199900`). (Supersedes the earlier ₹1,999/₹999 from the brief — ₹4,999 is the struck-through anchor, ₹1,999 is the real selling price.) |
| Length | 38 pages (36–40 target) |
| Form / funnel | Reuse the **career-growth** funnel (form → teaser → contact popup → payment → report + PDF + WhatsApp), but a **slimmed form: exactly 5 fields — Name, Date of birth, Time of birth, Gender, Place of birth (city)**. Drop career-growth's two extra fields (employment situation, experience) — they never affected scoring, and this premium product doesn't ask them. The `compute_career_intelligence()` call passes only these 5 (+ derived tz/lat/lon from the geocoded city, + time_quality when TOB is unknown). |
| Homepage | NOT listed on homepage for now. Reviews DO go on its own landing page. |
| career-growth product | Stays live alongside this — this is a separate, new product |

## Format & theme — the hard constraint

- **Structure/format = Business Growth (Vyapar) exactly: ONE CARD PER PAGE.** Reuse the
  `_VYAPAR_CSS` / `_VYAPAR_DEFS` card-per-page system. Same structural discipline: every
  page is one filled card, **no empty/blank page areas ("no whitespace" = no unfilled
  gaps), no section bleeding into the next, no content leaking in from business-growth.**
- **Theme/colours = the manager's premium palette** applied over that structure:
  charcoal/black + subtle gold; large elegant serif headline + clean sans-serif body;
  minimal astrology graphics (no zodiac wheel on every page, no crystal balls, no
  temples/planets everywhere). Executive-intelligence look, not "astrology PDF".
- Reconciliation note: the manager wrote "lots of white space" (a *clean, uncluttered*
  aesthetic); the dev's "no whitespace" means *no empty/unfinished page regions*. Both
  are satisfied by the Business-Growth card model: clean, content-complete cards — never
  sparse pages.

## Language & tone rules (apply to every section)

- 80% modern English / 20% accessible Vedic terminology.
- Put the **insight first, the astrological reason after** — optionally in a small
  "**Astrological basis:**" box. Never lead with "Jupiter in the 10th house gives…".
- **Strictly non-deterministic.** Use "your chart indicates / this period may favour /
  you may find / the stronger theme appears to be". NEVER "you will", "guaranteed",
  "you will earn ₹X". No deterministic financial or life predictions, ever.
- Voice: mature, intelligent, respectful, calm, optimistic, non-deterministic.

## Signature deterministic features (new engine logic — do not fake with the LLM)

1. **Career Archetype** — every report classifies the person into exactly ONE of these 7,
   computed from the chart (shareable identity, appears on the Executive Snapshot):
   THE STRATEGIC BUILDER · THE INDEPENDENT LEADER · THE VISIONARY · THE SPECIALIST ·
   THE ENTREPRENEURIAL MIND · THE CONSOLIDATOR · THE REINVENTOR.
2. **Executive Snapshot — 6 rated dimensions**, each computed to High / Moderate / Low
   (or a band like Moderate–High) from the chart:
   Leadership · Entrepreneurial inclination · Risk appetite · Strategic thinking ·
   Independence · Stability orientation.
3. **Decision-Making Style** (§7) — classify into one of: The Analyst · The Instinctive
   Decision Maker · The Risk Taker · The Conservative Builder (+ room for more).
4. **Current Career Phase** (§14) — derived from the dasha timeline, named in plain
   language (e.g. "Consolidation & Repositioning") with a small astrological-basis box.

---

## The 38 sections (finalised — build in this order, one card per page)

### INTRODUCTION (pages 1–3)
1. **Cover** — AXTROSHASTRA / CAREER INTELLIGENCE REPORT / "A Personalised Roadmap for Your Next Professional Chapter" / Name · Date of Birth · Report Date.
2. **A Note to You** — one-page warm introduction that sets the tone (career at this stage isn't about climbing higher, it's about what deserves your time/experience/energy next; the report reads your professional journey through your birth chart).
3. **Executive Career Snapshot** — one-page dashboard: the 6 rated dimensions + the person's **Career Archetype** (e.g. THE STRATEGIC BUILDER).

### PART I — UNDERSTANDING YOU (pages 4–7)
4. **Your Professional Personality** — who they are at work: approach to responsibility, pressure, independence, authority, competition, recognition. Very accessible language.
5. **Your Natural Strengths** — 5–7 strengths, insight-first (e.g. "Strategic Thinking — you perform best given a complex problem rather than a routine task…"), astrological reasoning after.
6. **Your Leadership Signature** — leadership style, authority, delegation, people management, decision-making, influence. (Especially relevant to 40–60.)
7. **Your Decision-Making Style** — classify: The Analyst / The Instinctive Decision Maker / The Risk Taker / The Conservative Builder / etc.

### PART II — YOUR CAREER JOURNEY (pages 8–12)
8. **Your Career Pattern** — a defining arc, e.g. "Build → Consolidate → Reinvent" or "Experiment → Specialise → Lead". Make it visually interesting.
9. **Recurring Career Patterns** — themes that may have repeated: sudden changes, delayed recognition, strong responsibility, career reinvention, independent work, authority conflicts. (Where it feels uncannily personalised.)
10. **Your Relationship With Work** — what motivates them: money / status / freedom / purpose / security / recognition / impact.
11. **What Can Hold You Back** — blind spots (don't only flatter): staying too long in familiar environments, excessive caution, impatience with hierarchy, difficulty delegating, taking on too much responsibility. (Builds credibility.)
12. **Your Career Strengths vs Challenges** — a simple two-column visual (Strength ↔ Potential challenge, e.g. Strategic thinking ↔ Over-analysis).

### PART III — YOUR NEXT CHAPTER (hero section, pages 13–22)
13. **The Big Question: What's Next?** — the emotional centre. "Your next chapter may not require you to work harder. It may require you to work differently." Then explain their current phase.
14. **Your Current Career Phase** — derived from dasha, named in plain language (e.g. "CURRENT PHASE: CONSOLIDATION & REPOSITIONING") + a small "Astrological basis" box.
15. **Year 1 — Positioning** — part of "The Next 3 Years"; interpretation from the chart.
16. **Year 2 — Expansion**.
17. **Year 3 — Transition**.
18. **Career Opportunities** — which types may suit: leadership / consulting / entrepreneurship / independent practice / international / specialised expertise.
19. **Job vs Entrepreneurship** — entrepreneurial inclination **X / 10** + explanation. Killer section for this audience. Avoid deterministic claims.
20. **Leadership & Senior Roles** — could they thrive in senior management / advisory / ownership / independent leadership / specialist positions.
21. **Reinvention Potential** — "Is this a phase for reinvention?" Directly hits 45–55.
22. **Your Professional Sweet Spot** — the big takeaway: "WHERE YOU ARE MOST LIKELY TO THRIVE" (e.g. high-autonomy roles combining strategy, decision-making and people influence).

### PART IV — MONEY & PROFESSIONAL SUCCESS (pages 23–27)
23. **Your Relationship With Financial Growth** — wealth orientation / risk / accumulation / stability / entrepreneurial tendencies. NEVER "you will earn ₹X".
24. **Wealth Through Career vs Enterprise** — the distinction.
25. **Risk & Opportunity** — when they tend to benefit from Expansion vs Consolidation.
26. **Professional Recognition** — potential periods/themes around authority, visibility, recognition, responsibility.
27. **Your Long-Term Professional Potential** — bands: 40–45 / 45–50 / 50–55 / 55–60.

### PART V — YOUR PERSONAL ROADMAP (insight → action, pages 28–34)
28. **Your Top 5 Career Priorities** — personalised.
29. **What To Pursue** — 3–5 recommendations.
30. **What To Avoid** — psychologically powerful.
31. **Decisions That Deserve Thought** — e.g. "Consider whether your current role is giving you enough autonomy."
32. **Your 12-Month Career Focus** — STOP / START / CONTINUE. LinkedIn-friendly.
33. **Your Career Action Plan** — Next 30 days / Next 90 days / Next 12 months.
34. **Your Career Intelligence Summary** — one page, "YOUR 5 KEY TAKEAWAYS" (1–5). The page people screenshot/share.

### PART VI — ASTROLOGICAL FOUNDATION (pages 35–38)
35. **Your Birth Chart** — beautifully presented.
36. **Key Planetary Influences** — only the planets relevant to the career analysis.
37. **Your Career Houses & Indicators** — 10th, 6th, 2nd, 11th etc., explained simply.
38. **Methodology & Disclaimer** — "…based on traditional Vedic astrological principles, intended for personal reflection and guidance. Not a guarantee of future events or a substitute for professional financial, legal or career advice."

---

## Landing page copy (from the brief — use verbatim as the base)

> **AXTROSHASTRA**
> **CAREER INTELLIGENCE REPORT**
> You've spent years building your career. Now understand your next professional chapter.
> A personalised analysis of your career strengths, professional patterns, leadership
> style, opportunities and upcoming phases — based on your individual birth chart.
> **38 pages • Personalised • Private**
> ~~₹1,999~~ **₹999** — *Founding Launch Price*
> **[ GET MY CAREER INTELLIGENCE REPORT ]**

## Open engine-design questions (resolve before/at build, don't guess)
- Exact chart-feature → Archetype mapping (which placements decide each of the 7).
- Exact chart-feature → each of the 6 snapshot dimensions (High/Mod/Low thresholds).
- Which dasha state maps to which named "Current Career Phase".
- Entrepreneurial inclination X/10 scoring formula (§19).

## McKinsey-exhibit layer (added 28 Aug — page count NO LONGER capped at 38)

Decision: the report is visual-first (audience reads less, looks more). **Each major
content card is followed by its own McKinsey-style EXHIBIT card** — the takeaway drawn,
not written. This roughly doubles the strong sections; total ≈ 52–56 pages, and the
38-page cap is removed. Exhibit cards use the same charcoal/gold theme + one-card-per-page
format, an **action-title** (states the conclusion, not the topic) and a "What this
shows / The read" takeaway line. Proven exhibit components (see the exhibit-samples
artifact): radar, 2×2 matrix, roadmap arc, gauge, ranked bars, timeline, spectrum-dot,
donut, venn, life-stage bars.

Exhibit follows each of these sections (content card → exhibit card):
| After § | Content section | Exhibit |
|---|---|---|
| 3 | Executive Snapshot | Radar (6 dimensions) |
| 3 | (archetype) | 2×2 archetype-positioning matrix |
| 5 | Natural Strengths | Ranked strength bars |
| 6 | Leadership Signature | Leadership spectrum/dial |
| 7 | Decision-Making Style | Decision 2×2 (speed × basis) |
| 8 | Career Pattern | Journey arc (Build→Consolidate→Reinvent) |
| 10 | Relationship With Work | Motivator donut |
| 12 | Strengths vs Challenges | Balance / paired matrix |
| 14 | Current Career Phase | Phase-on-timeline |
| 17 | The Next 3 Years | 3-year roadmap arc |
| 19 | Job vs Entrepreneurship | (gauge already in content) |
| 22 | Professional Sweet Spot | Venn (strategy ∩ decisions ∩ people) |
| 24 | Career vs Enterprise | Comparison bars |
| 27 | Long-Term Potential | Life-stage bar chart (40–60) |
| 28 | Top 5 Priorities | Priority matrix (impact × effort) |
| 32 | 12-Month Focus | Stop/Start/Continue visual |
| 33 | Action Plan | 30/90/365 horizontal timeline |
| 36 | Key Planetary Influences | Planet-strength bars |

Emotional/framing pages (Cover, Note, Big Question, Disclaimer) and pure-list pages
(What to Pursue/Avoid, Decisions) stay prose — an exhibit there would be padding.
**Rule of thumb: an exhibit earns its card only when a picture beats the paragraph.**

## Build order (per CLAUDE.md §8 mock-first)
1. Finalise this spec (done — this doc).
2. Build the engine logic: archetype + 6 dimensions + phase + entrepreneurial score.
3. **Mock the report visually** (HTML/artifact) in the Vyapar card format + charcoal/gold
   theme; print to PDF, eyeball, fix — get it approved.
4. Only then wire the real pipeline: `compute_career_intelligence` → `narrative.py`
   SECTION_SPECS → `render_career_intelligence` (in the reskinned Vyapar system) →
   `api._render_for` + `create_kundli` dispatch → routes + pricing + landing page.
5. Reviews (professional voice), sitemap + robot registration, gates.
