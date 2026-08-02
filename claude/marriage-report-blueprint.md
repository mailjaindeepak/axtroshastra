# Marriage Report Blueprint — LOCKED v2

Definitive build spec for the LLM-narrated marriage report. Supersedes v1.
Ordering = payoff first (modern voice), classical Jyotish authenticity last.
Structured into the four delivery tiers the product owner defined.

## Locked decisions (v2)

- **Structure = 4 tiers, ~33 pages, front-loaded:**
  1. **Main page** (1 p) — the narrowest wedding-timing prediction.
  2. **Summary** (6 pp) — the whole report, digestible.
  3. **Detailed report** (13 pp) — full depth on timing, partner, remedies.
  4. **Astrology details** (13 pp) — every classical calculation, one topic per page.
- **Language: English + Hindi (Devanagari) only. No Hinglish.** Chosen per report by
  funnel (`meta.lang`: `/hi/*` → `hi`, else `english`). Deterministic bank text is
  rewritten to clean **English**; the LLM writes English or Devanagari per report.
- **Hindi path:** LLM prose comes back in Devanagari and passes through unchanged; a
  slim **English→Devanagari localizer** (rebuilt `shaadi_hi`) translates only the
  deterministic labels/headers/tables/tokens (signs, planets, nakshatras, grades,
  months, UI labels) — not prose (prose is now LLM-authored).
- **LLM:** provider Claude, model `claude-sonnet-5`. Enabled in prod
  (`NARRATIVE_ENABLED=1` + `ANTHROPIC_API_KEY`). ~30 prose slots; bump
  `NARRATIVE_MAX_TOKENS` to ~8000 for the marriage call (product-aware).
- **Manglik = fully deterministic.** No LLM slot (S5 + D8). Sensitive framing;
  hand-authored English, careful and non-fatalistic. Includes an authored Dos & Don'ts list.
- **Facts are never authored by the LLM.** Template renders every chart/score/date/table;
  the LLM writes only interpretive prose beside them. Three-layer guardrail stays
  (structural + `_numbers_ok` + `_claims_ok`).

## Component coverage (owner's 11 components)

| # | Component | Tier/pages | Data | New work? |
|---|-----------|------------|------|-----------|
| 1 | Birth chart (Kundli) | S2, A2 | `chart` D1, `north_chart_svg`, planet table | — |
| 2 | Marriage windows + grade | Main, S1, D1–D3 | `windows[]` | — |
| 3 | Explanation of windows | D1–D3, A11 | `rules_fired[]`, scoring box | — |
| 4 | Actions in Strong/Moderate windows | S6, D4 | `GRADE_ACTION` | — |
| 5 | Actions in weak periods | S6, **D5** | `_weak_periods()` | **author action bank** |
| 6 | Manglik impact + Dos & Don'ts | S5, **D8** | `manglik.*` | **author dos/don'ts** |
| 7 | Past 3–4 yrs + why + how it changes | S4, D6, D7 | `extras.past`, `year_outlook` | — |
| 8 | Sade Sati impact | S5, D9 | `extras.sade_sati` | — |
| 9 | Remedies for MD/AD issues | **D10** | `REMEDY_7L` + weak dasha lords | **extend to per-dasha lords** |
| 10 | Partner (who/where/context, love vs arranged) | S3, D11–D13 | `significators`, `SIGN_PARTNER`, `DK_PARTNER`, `checks` | — |
| 11 | Astrological details of all calcs | A1–A13 | planet table, D9, scoring, method, dasha tree | — |

## Page flow

### TIER 1 — MAIN PAGE (1 p)
| p | Page | Slot | Deterministic facts |
|---|------|------|---------------------|
| 1 | The Answer | `top_summary` | `windows[0]` core range + peak months + grade; Manglik one-liner; D9 strength one-liner |

### TIER 2 — SUMMARY (6 pp)
| p | Page | Slot | Facts |
|---|------|------|-------|
| S1 | Your Windows | `windows_intro` | horizon timeline + 3 quick cards |
| S2 | Your Kundli at a Glance | `chart_teaser` | D1 SVG + lagna/moon/7th/7th-lord |
| S3 | Your Partner (snapshot) | `partner_teaser` | 7th sign / darakaraka / love-vs-arranged |
| S4 | Your Timing Story | `story_teaser` | past pattern + next-3-yr shape |
| S5 | The Big Questions | *(deterministic)* | Manglik verdict + Sade Sati status + D9 band |
| S6 | What To Do Now | `action_teaser` | strong-window move + quiet-period heads-up |

### TIER 3 — DETAILED REPORT (13 pp)
| p | Page | Slot | Facts |
|---|------|------|-------|
| D1 | Window 1 (deep) | `window_1` | range, grade, peak months, dasha driver |
| D2 | Window 2 | `window_2` | conditional |
| D3 | Window 3 / longer outlook | `window_3` | conditional; reallocate if <3 windows |
| D4 | Strong & Moderate — Your Move | `action_strong` | `GRADE_ACTION` per window |
| D5 | Weak Periods — What To Do (NEW) | `action_weak` | `_weak_periods()` + authored actions |
| D6 | Why It Hasn't Happened | `past_pattern` | `extras.past[]` |
| D7 | The Next 3 Years | `outlook` | `extras.year_outlook[]` |
| D8 | Manglik — Impact + Dos & Don'ts (NEW, deterministic) | — | `manglik.status/cancellations` + do/don't |
| D9 | Sade Sati — Impact | `sade_sati_note` | `extras.sade_sati` |
| D10 | Remedies (Mahadasha/Antardasha) (EXTENDED) | `remedies_note` | per weak MD/AD lord + 7th lord |
| D11 | Your Partner — Personality | `partner_personality` | `SIGN_PARTNER[7th sign]` |
| D12 | Partner — Background & How You'll Meet | `meeting_context` | `DK_PARTNER` + 7th-lord house + `checks` |
| D13 | How You Love | `love_pattern` | `NAK_PROFILE` + `VENUS_STYLE` |

### TIER 4 — ASTROLOGY DETAILS (13 pp) — Component 11
| p | Page | Slot | Facts (code-rendered) |
|---|------|------|-----------------------|
| A1 | Method & Foundations | `method_intro` | ayanamsa, whole-sign, Lagna vs Chandra, time tier |
| A2 | Your Birth Chart (D1) | `chart_reading` | N-Indian SVG + all placements |
| A3 | Lagna & Moon | `lagna_moon` | lagna sign, moon sign |
| A4 | The Nine Planets | `planet_strengths` | dignity/retro/combust table |
| A5 | Nakshatra & Pada | `nakshatra_deep` | nakshatra, pada, lord |
| A6 | The 7th House | `seventh_house` | 7th sign, occupants |
| A7 | The 7th Lord | `seventh_lord` | lord, dignity, house, combust |
| A8 | Marriage Karakas | `karakas` | Venus (+Jupiter) placements |
| A9 | Darakaraka (Jaimini) | `darakaraka` | darakaraka planet + sign |
| A10 | Rahu/Ketu on the 7th Axis | `node_axis` | `node_on_7th_axis` |
| A11 | Dasha System + Your Periods | `dasha_periods` | Vimshottari + MD/AD table + `rules_fired` scorecard |
| A12 | Gochar (Transits) | `transits` | Jupiter/Saturn transit results |
| A13 | Navamsa (D9) + Closing | `navamsa_reading`, `closing_note` | D9 SVG, vargottama, strength band |

## `SECTION_SPECS["marriage"]` — slot briefs (build sheet, ~30 slots)

```
top_summary         "2-3 warm sentences answering 'when will marriage happen' from the strongest window."
windows_intro       "2 sentences framing the 1-3 windows ahead as a timeline, encouraging."
chart_teaser        "2 sentences on what the chart says about marriage at a glance."
partner_teaser      "1-2 intriguing sentences hinting at the kind of partner indicated."
story_teaser        "2 sentences: why it hasn't happened yet and that momentum is turning."
action_teaser       "2 sentences on the single most useful thing to do now."
window_1            "3-4 sentences on what the strongest window means and why it lights up."
window_2            "2-3 sentences on the second window; how it differs from the first."
window_3            "2-3 sentences on the third window or the longer outlook beyond it."
action_strong       "2-3 encouraging, non-fatalistic sentences on making the most of good windows."
action_weak         "2-3 sentences reframing quiet periods: what to do (and not force) now."
past_pattern        "3-4 reassuring sentences on why past periods did/didn't convert - timing, not failure."
outlook             "2-3 sentences on the shape of the next 3 years and the months to watch."
sade_sati_note      "2-3 calm, non-fatalistic sentences on the Saturn cycle's current phase."
remedies_note       "2-3 sentences framing remedies as optional support, agency first, zero pressure."
partner_personality "2-3 sentences on the partner's likely personality, from the 7th sign."
meeting_context     "3-4 sentences on the partner's background and how/where you may meet; love-vs-arranged."
love_pattern        "3-4 sentences on how this person loves, from their nakshatra and Venus."
method_intro        "2-3 sentences on why this sidereal/whole-sign method is authentic and trustworthy."
chart_reading       "2-3 sentences reading the overall shape of the birth chart, plainly."
lagna_moon          "2-3 sentences on the two lenses - ascendant and Moon - and what each governs."
planet_strengths    "3-4 sentences on what the planetary dignities mean for this person, plainly."
nakshatra_deep      "3-4 sentences on the classical character of this birth star."
seventh_house       "2-3 sentences on the 7th house as the seat of marriage in this chart."
seventh_lord        "3-4 sentences on the 7th lord as the 'marriage switch' and what its condition implies."
karakas             "2-3 sentences on Venus (and Jupiter) as the natural significators of union."
darakaraka          "2-3 sentences explaining the Jaimini spouse-indicator and what it adds."
node_axis           "2-3 sentences on any Rahu/Ketu link to the 7th axis - the karmic dimension."
dasha_periods       "3-4 sentences on what the active and upcoming periods bring for marriage."
transits            "2-3 sentences on Jupiter and Saturn transits as the 'go' and 'slow' signals."
navamsa_reading     "3-4 sentences on the D9 as the marriage-promise chart and what its strength band says."
closing_note        "A warm 3-4 sentence closing note to the reader."
```

## New engine/data work

1. **`extras.dasha_remedies`** (Component 9) — for each weak lord in the active/upcoming
   periods (AD_WEAK fired, or debilitated/combust MD/AD lord, or Saturn/Ketu "dry"),
   emit a remedy via a planet-keyed remedy map (reuse `REMEDY_7L` shape). Deterministic.
2. **Manglik Dos & Don'ts** (Component 6) — authored lists keyed by `manglik.status`.
3. **Weak-period actions** (Component 5) — authored action text over `_weak_periods()`.

## Implementation notes

1. `navamsa` already flows to the LLM via `_facts_for_llm`.
2. Product-aware `NARRATIVE_MAX_TOKENS` (~8000 for marriage).
3. Conditional windows: 1–3 returned; drop `window_2`/`window_3` and reallocate to a
   ranked best-months deep-dive on the strongest window; `log()` the reallocation.
4. Renderer wiring: each slot is `narr(p, "<slot>") or <english bank>`.
5. Manglik pages stay templated — no slot.
6. With `NARRATIVE_ENABLED` off, the English banks must render a coherent full report.

## Cost (Sonnet 5)

~$0.15–0.20 per report; one cached background call per report on `payload["narrative"]`.
