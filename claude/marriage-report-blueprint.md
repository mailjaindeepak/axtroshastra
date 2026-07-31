# Marriage Report Blueprint — LOCKED v1

Definitive build spec for the LLM-narrated marriage report. Ordering = payoff first
(modern voice), classical Jyotish authenticity last. Every page except Manglik gets an
LLM slot with a deterministic bank fallback.

## Locked decisions

- **Length:** ~38 pages, front-loaded. Pillars land by ~p24; astrology tier is the back third.
- **Voice arc:** modern/GenZ (p1–24) → classical Jyotish (p25–38). Terms introduced gently early, defined fully late.
- **LLM:** provider Claude, model `claude-sonnet-5` (code default). Enabled in prod (`NARRATIVE_ENABLED=1` + `ANTHROPIC_API_KEY`). Per-report language via `meta.lang` (`_resolve_lang`).
- **Manglik = fully deterministic.** No LLM slot (sensitive phrasing; bank text is already careful/non-fatalistic).
- **Facts are never authored by the LLM.** The template renders every chart/score/date/table; the LLM writes only the interpretive prose *beside* them. This is the primary guardrail.
- **Three-layer guardrail** (all live in `narrative.py`):
  1. structural — template owns facts;
  2. numeric — `_numbers_ok` drops any section with a score/%/year not in the facts;
  3. qualitative — `_claims_ok` drops any section asserting a planet placement/dignity that contradicts D1 or D9.

## Page flow (grouped)

### THE ANSWER · SUMMARY (p1–6)
| p | Page | Slot | Deterministic facts shown |
|---|------|------|---------------------------|
| 1 | The Answer | `top_summary` | `windows[0]` core range + grade badge |
| 2 | At a Glance (dashboard) | *(none — tiles)* | 3-window mini-timeline, D9 "will it last" badge, Manglik verdict, archetype |
| 3 | Your Windows | `windows_intro` | horizon timeline strip + 3 quick cards |
| 4 | You, in a line | `you_teaser` | nakshatra + moon sign |
| 5 | Your Person, in a line | `partner_teaser` | 7th sign / darakaraka |
| 6 | The Big Questions | *(none)* | Manglik verdict + D9 band |

### WHEN (p7–12)
| p | Page | Slot | Facts |
|---|------|------|-------|
| 7 | Window 1 | `window_1` | window 1: range, grade, peak months, dasha driver |
| 8 | Window 2 | `window_2` | window 2 (conditional) |
| 9 | Window 3 | `window_3` | window 3 (conditional) |
| 10 | Why It Hasn't Happened Yet | `past_pattern` | `extras.past[]` |
| 11 | The Next 3 Years | `outlook` | `extras.year_outlook[]` |
| 12 | Your Move | `action_intro` | `GRADE_ACTION` per window |

### YOU (p13–16)
| p | Page | Slot | Facts |
|---|------|------|-------|
| 13 | Who You Are | `persona` | moon sign + `NAK_PROFILE` nature |
| 14 | How You Love | `love_pattern` | `NAK_PROFILE` relationship line |
| 15 | Your Love Language | `venus_style` | `VENUS_STYLE` + modifiers |
| 16 | Your Timing Temperament | `timing_temperament` | `checks.late_marriage_influence` |

### PARTNER (p17–20)
| p | Page | Slot | Facts |
|---|------|------|-------|
| 17 | Their Personality | `partner_personality` | `SIGN_PARTNER[7th sign]` |
| 18 | Their Background & Nature | `partner_background` | `DK_PARTNER[darakaraka]` |
| 19 | How You'll Meet | `meeting_context` | 7th-lord house + `checks.love_leaning` + `checks.foreign_or_intercommunity` |
| 20 | Portrait | `partner` | synthesis of 17–19 |

### MANGLIK — deterministic (p21–22)
| p | Page | Slot | Facts |
|---|------|------|-------|
| 21 | The Verdict + What It Is | — | `manglik.status`, myth-bust |
| 22 | What It Means For Your Decisions | — | `manglik.cancellations[]` |

### SUPPORT — opt-in (p23–24)
| p | Page | Slot | Facts |
|---|------|------|-------|
| 23 | Sade Sati | `sade_sati_note` | `extras.sade_sati` |
| 24 | Remedies | `remedies_note` | `extras.remedies` |

### THE ASTROLOGY — classical (p25–38)
| p | Page | Slot | Facts (code-rendered) |
|---|------|------|------------------------|
| 25 | The Method & Foundations | `method_intro` | ayanamsa, house system, Lagna vs Chandra, time tier (`meta`) |
| 26 | Your Birth Chart (D1) | `chart_reading` | N-Indian SVG + all placements |
| 27 | Lagna & Moon | `lagna_moon` | lagna sign, moon sign |
| 28 | The Nine Planets | `planet_strengths` | dignity table for all 9 |
| 29 | Nakshatra & Pada | `nakshatra_deep` | nakshatra, pada, lord |
| 30 | The 7th House | `seventh_house` | 7th sign, occupants |
| 31 | The 7th Lord | `seventh_lord` | lord, dignity, house, combust |
| 32 | Marriage Karakas | `karakas` | karakas + placements |
| 33 | Darakaraka (Jaimini) | `darakaraka` | darakaraka planet + sign |
| 34 | Rahu/Ketu on the 7th Axis | `node_axis` | `node_on_7th_axis` |
| 35 | The Vimshottari Dasha System | `dasha_system` | Moon-nakshatra → start lord |
| 36 | Your Dasha Periods | `dasha_periods` | MD/AD table + `rules_fired` |
| 37 | Gochar (Transits) | `transits` | Jupiter/Saturn transit results |
| 38 | The Navamsa (D9) + Closing | `navamsa_reading`, `closing_note` | D9 SVG, vargottama, strength band |

## `SECTION_SPECS["marriage"]` — the slot briefs (build sheet)

Drop-in writing briefs (mirror the existing milan style). ~34 slots.

```
top_summary        "2-3 warm sentences answering 'when will marriage happen' from the strongest window."
windows_intro      "2 sentences framing the 1-3 windows ahead as a timeline, encouraging."
you_teaser         "1 vivid sentence capturing this person's core nature from their nakshatra."
partner_teaser     "1 intriguing sentence hinting at the kind of partner indicated."
window_1           "3-4 sentences on what the strongest window means and why it lights up, plain language."
window_2           "2-3 sentences on the second window; how it differs from the first."
window_3           "2-3 sentences on the third window or the longer outlook beyond it."
past_pattern       "3-4 reassuring sentences on why past periods did/didn't convert - timing, not failure."
outlook            "2-3 sentences on the shape of the next 3 years and the months to watch."
action_intro       "2-3 encouraging, non-fatalistic sentences on what to do now."
persona            "3-4 sentences painting who this person is, from Moon sign and nakshatra."
love_pattern       "3-4 sentences on how this person loves, from their nakshatra and Venus."
venus_style        "2-3 sentences on their love language, from Venus."
timing_temperament "2-3 sentences reframing any late-marriage / maturity indication as wisdom, not delay."
partner_personality "2-3 sentences on the partner's likely personality, from the 7th sign."
partner_background "2-3 sentences on the partner's likely background/nature, from the darakaraka."
meeting_context    "2-3 sentences on how/where they may meet, and love-vs-arranged leaning."
partner            "3-4 sentences synthesising the partner picture; end with 'indications, not a portrait'."
sade_sati_note     "2-3 calm, non-fatalistic sentences on the Saturn cycle's current phase."
remedies_note      "2-3 sentences framing remedies as optional support, agency first, zero pressure."
method_intro       "2-3 sentences on why this sidereal/whole-sign method is authentic and trustworthy."
chart_reading      "2-3 sentences reading the overall shape of the birth chart, plainly."
lagna_moon         "2-3 sentences on the two lenses - ascendant and Moon - and what each governs."
planet_strengths   "3-4 sentences on what the planetary dignities mean for this person, in plain terms."
nakshatra_deep     "3-4 sentences on the classical character of this birth star."
seventh_house      "2-3 sentences on the 7th house as the seat of marriage in this chart."
seventh_lord       "3-4 sentences on the 7th lord as the 'marriage switch' and what its condition implies."
karakas            "2-3 sentences on Venus (and Jupiter) as the natural significators of union."
darakaraka         "2-3 sentences explaining the Jaimini spouse-indicator and what it adds."
node_axis          "2-3 sentences on any Rahu/Ketu link to the 7th axis - the karmic dimension."
dasha_system       "3-4 sentences explaining how the Moon's nakshatra seeds the whole timeline."
dasha_periods      "3-4 sentences on what the active and upcoming periods bring for marriage."
transits           "2-3 sentences on Jupiter and Saturn transits as the 'go' and 'slow' signals."
navamsa_reading    "3-4 sentences on the D9 as the marriage-promise chart and what its strength band says."
closing_note       "A warm 3-4 sentence closing note to the reader."
```

## Implementation notes

1. **Bump max tokens for marriage.** ~34 slots of prose can exceed the 4096 default (`NARRATIVE_MAX_TOKENS`). Set the marriage call to ~8000, or make it product-aware.
2. **`navamsa` now flows to the LLM** — added to `_facts_for_llm` (needed by D9 slots + `_claims_ok`).
3. **Conditional windows.** Engine returns 1–3 windows. When <3, drop `window_2`/`window_3` slots and reallocate the page(s) to a "best months, ranked" deep-dive on the strongest window; log the reallocation, never leave a blank page.
4. **Renderer wiring.** In `report_view.py → render_report`, each slot is `narr(p, "<slot>") or <existing bank text>`. New pages (astrology tier) need bank defaults authored alongside the LLM slot.
5. **Manglik pages stay templated** — do not add a slot.

## Cost (Sonnet 5, real-time)

~$0.15–0.20 per report at intro pricing ($2/$10 per MTok through 2026-08-31); output scales with the ~34 slots, input is a fixed floor. One background call per report, cached on `payload["narrative"]` — never per-view. Batch API (−50%) is a *future* option, not for the initial build (paid users wait; extra plumbing).
