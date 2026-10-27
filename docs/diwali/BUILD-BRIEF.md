# Diwali report: BUILD BRIEF (shared contract for every build agent)

Branch `feat/diwali-report` (worktree `/Users/shreyanshjain/Desktop/axtroshastra/axtro-diwali`), based on
`upstream/aws-mysql` @ 6896200. Source of truth for WHAT to build: [diwali-report-spec.md](diwali-report-spec.md)
(read §3 inputs, §4 funnel, §5 sections + area order, §6/§6a topics + questions, §7 engine work E1–E12,
§9 bug work + lints, §11 tests). This file fixes HOW the pieces fit so agents can work in parallel.

## Owner decisions that override older text anywhere
- Slug **`/en/diwali`**, file `pages/diwali.html`; legacy `/diwali` → 301 `/en/diwali`. Hindi later.
- Price **₹499** (`DIWALI_PRICE_PAISE = 49900`), chosen on the server **by product**, stored as `amount_paise`.
- **No life-stage input.** Marriage + Family & children = ONE general version that never assumes status (spec §5/§6).
  Marriage = the 5 approved questions + Manglik facts box. Family Q4 = "Which months may bring happy news in your family?"
- **Self / Gift toggle** (default Self). Gift → optional giver's name + optional message (placeholder example;
  empty message → our ready-written message; no name → "A Diwali gift for you"). Delivery identical for both, to the
  form's WhatsApp number. No receiver number. In Gift mode, name + birth details are the receiver's.
- Gender Male/Female only. `as_of` = **2026-11-08**; span **Nov 2026 – Oct 2027**, also after 8 Nov.
- Puja-time cities (9): Delhi, Mumbai, Bengaluru, Chennai, Ahmedabad, Kolkata, Pune, Hyderabad, Jaipur.
- The **sample report** on the page = Mock 3C v2 page images (`static/diwali-sample-NN.jpg`, 58 images, already added).
- The **landing page / free preview look** = `docs/diwali/mock/diwali-preview-vikram-v1.html` (CI preview layout + Diwali skin
  + story-style Wrapped with months LOCKED). Report look = `docs/diwali/mock/mock3c-v2.html` (kit in `docs/diwali/mock/kit-3c/`).
- Reviews: write 5–8 in house style (CLAUDE.md §5, §5c). Homepage card: yes (CLAUDE.md §4).
- AI: 4 parallel calls (O-10): A = front answers + Wrapped words; B = Money + Career + Business; C = Family + Marriage + Better luck;
  D = 12 months + end plan. After payment: progress screen (progress bar, ticks, Diwali fireworks), WhatsApp text immediately,
  "still on its way" after 2 min. Bug #1 fix for Diwali only: AI text → PDF → WhatsApp.

## Safety rules (hard)
- Never import `api.py` against a real DB. Tests use the conftest throwaway MySQL (127.0.0.1:3307, docker container
  `axtro-test-mysql`, already running). Never set DB_HOST to anything else. No `.env` exists in this worktree; keep it that way.
- No real network side effects: no Razorpay, Twilio/WhatsApp, Meta, Anthropic calls. `NARRATIVE_ENABLED=0` in tests (the
  deterministic bank must make a complete report on its own). No secrets anywhere.
- **No git commit, push, merge, branch delete, deploy.** Leave changes uncommitted in the worktree.
- Only edit the files you own (table below). Need a change elsewhere? Say so in your report; don't do it.
- Everything visible obeys CLAUDE.md §5b (banned Meta words + dosha, curse, danger, guaranteed, cure, bad luck, will happen)
  and the R3 rules (spec §2/§9: no brackets in prose; month names only inside pictures, the 2 date pages, the 12 months, the
  Wrapped card and fixed date tables; never "year" alone; "best/good/careful time", never "stretch"/"window"; plain name OR
  house number, never both; "Karka" never "Cancer"; never mention AstroSage to buyers). §22: nothing from the mock persona
  (Vikram, Priya, Pune-specific prose) may be hard-coded.

## Files and owners
| File | Owner | What |
|---|---|---|
| `diwali_assets.py` | (done) | `DIWALI_CSS`, `DIWALI_DEFS`, `FONTS_LINK`, verbatim from kit-3c. Do not edit. |
| `diwali.py` + `tests/test_diwali_engine.py` | ENGINE | `compute_diwali(...)` → payload below. E1–E10, E12. Through `engine.compute_chart`/`compute_report` only (CLAUDE.md §21); don't edit engine.py — wrap. |
| `diwali_bank.py` + `tests/test_diwali_bank.py` | CONTENT | `NARR_KEYS`, `bank(payload)`, `lint_text()` (below). All deterministic prose for every branch. |
| `diwali_report.py` + `tests/test_diwali_render.py` | RENDER-A | `render_diwali(payload) -> str` full HTML doc; assembler, page numbers, contents; front pages; Part 1 areas. |
| `diwali_report_back.py` | RENDER-B | `cards_back(payload, prose) -> list[str]`: Better luck, strengths, Sade Sati, slow planets, 12 months, Part 2 Your Diwali (days, puja times, gold months, practices, blessing + gift sign-off, Wrapped card), end plan (priorities, 30/90/365, 5 takeaways), back pages (houses table, methodology, glossary, FAQ, Thank you). |
| `pages/diwali.html` + `tests/e2e/diwali.spec.js` | FRONTEND | Landing page: hero, form, preview, locked answers, unlock, progress screen, sample modal, FAQ, reviews, sticky bar. |
| `api.py`, `narrative.py`, `pages/home.html`, `ops/robot_customer/robot.spec.js`, `tests/test_diwali_api.py`, sitemap | CONNECT (runs after the 4 above) | Wiring (below). |

## Payload contract (`compute_diwali` output) — ENGINE produces, CONTENT + RENDER consume
`ym` strings are `"YYYY-MM"`. States: answers/areas use `good|steady|careful`; month tones `best|good|steady|careful`.
```
{ "product": "diwali",
  "meta": { name, first_name, dob, tob, place, gender: "male"|"female",
            work_type: "job"|"business"|"student"|"home",
            steering: "money"|"career"|"business"|"family"|"marriage"|"luck"|null,
            time_quality: "T0"|"T1"|"T2"|"T3", basis: "lagna"|"moon", lang: "en", variant: "/en/diwali",
            age, age_band: "u25"|"25_40"|"40_60"|"60p", as_of: "2026-11-08", span: "Nov 2026 – Oct 2027",
            gift: { on: bool, giver_name: str, message: str } },
  "chart":  { lagna: {sign}, moon: {sign, nakshatra, pada},
              planets: [ {name, sign, house, dignity, retro, nakshatra} ×9 ],
              houses: { "1": {sign, lord}, … "12": {...} } },
  "period": { md, ad, ad_end: ym, next_ad: {lord, from: ym}|null, turning_points: [ {ym, kind} ] },
  "sade_sati": { active, phase: "rising"|"peak"|"setting"|null, phases: [ {phase, from: ym, to: ym} ] },
  "months": [ 12 × { ym, label: "Nov", year, tone, care_reason: "reactions"|"spending"|null,
                     transits: {Sun|Moon-less …: {sign, house, retro}}, tags: ["gold","loans","deals","family","travel",…] } ],
  "area_order": [5 of money|career|business|family|marriage], "first_reason": "picked"|"situation", "scores": {area: 0-3},
  "areas": { <area>: { state, windows: {best: [ym], good: [ym], careful: [ym]},
                       topics: [ {key: "<area>.t<n>", state, when: "best"|"good"|"careful"|"steady", months: [ym], why: <fact str>} ],
                       picture: [ {label, state: "best"|"good"|"careful", months_label} ] } },
  "money_extra": { dhana_yoga: {present, rule_text, lords: [...]}, gold_months: [ym], loan_months: [ym] },
  "marriage_extra": { manglik: {lagna_rule, moon_rule, cancelled, reason}, seventh: {sign, lord, lord_dignity} },
  "strengths": [3 × {planet, sign, house, dignity}],
  "lookback": { good: [ym], hard: [ym] },
  "luck": { bright_spots: [ {area, fact} ], ninth: {sign, lord} },
  "timeline": [4 × {from: ym, to: ym, tone, theme}], "best_time": {from: ym, to: ym},
  "diwali": { days: [ {name, date} ×5 ], puja_times: [ {city, start, end, source} ×9 ] },
  "answers": [5 × {q, state}],              // the 5 §6a questions of area_order[0] (or Better luck when picked)
  "wrapped": { strongest_area, best: {from, to}, careful: {from, to}, move, words: [3 × {word, line}] },
  "teaser": { … }                           // see below; NEVER contains a month/date
}
```
Topic order per area = spec §6. Puja times: hand-check vs Drik Panchang is a human step — put the values you have with
`source` and flag any not verified in your report (never invent precision silently).

**`teaser`** (sent to the browser BEFORE payment; spec §4 O-9): `{ name, moon_sign, nakshatra, lagna_sign, basis,
period: "Mercury – Jupiter", sade_sati: {active, phase}, planets: [{name, sign, dignity}], kundli: {sign: [planet abbrs]},
strongest_area, move, words: [3 × {word, line_masked}], emphasis_area, questions: [5 str], teasers: [5 str] }`.
`line_masked` replaces month text with `"●●●–●●●"`. A test must prove no month name/year/ym is anywhere in `teaser`.

## Prose contract — CONTENT owns, RENDER + CONNECT consume
- `diwali_bank.NARR_KEYS`: ordered `list[tuple[key, brief, group]]`, group in `A|B|C|D` (the 4 AI calls). Keys:
  `answers.q1..q5`, `wrapped.words`, `<area>.opener`, `<area>.t<n>.what|do|watch|why`, `<area>.read`, `luck.*`, `months.<ym>.do|watch`,
  `plan.*`, `takeaways.1..5`, `note.*` as needed. Briefs are the AI instructions (spec §2 rules, R2/R3).
- `diwali_bank.bank(payload) -> dict[key, str]`: a complete deterministic value for EVERY key, branch-aware
  (work_type ×4, gender ×2, steering ×7, age band ×4, basis lagna/moon, gift on/off), built only from payload facts.
- `diwali_bank.lint_text(text) -> list[str]` problems (banned words + R3 + status phrases "your wife/husband/spouse/marriage/
  children", "the right person", "marry again", "when children may come"). Used by tests and by narrative validation.
- Renderer: `prose(key) = (payload.get("narrative") or {}).get(key) or bank[key]`.

## Render contract
- `render_diwali(payload)` returns a complete `<!DOCTYPE html>` doc: `FONTS_LINK`, `<style>DIWALI_CSS</style>`, `DIWALI_DEFS`,
  cards. One card = `<section class="page …">…</section>`, 430×830, nothing may overflow (overflow is silently clipped).
- Same markup/classes/pictures as kit-3c fragments; only data/text differ. Card ids as in kit-3c (`contents`, `s-1-months`, `a-<area>`, `e-3` …).
- Page references: write `p.@@<card-id>@@`; the assembler replaces them after ordering (gift page and area order shift pages).
- Gift page only when `meta.gift.on`. Area order from `payload.area_order`; opener line "You picked X, so it comes first" only when picked.
- Report chrome (download/share buttons, toggles) is added later by `_wire_report_chrome`; include `@media print` hides for anything non-report.

## Connect contract
- `KundliIn` gains `work_type`, `steering`, `gift_mode`, `giver_name`, `gift_message` (validated; message length limit, plain text, never sent to AI or ad tracking).
- `/api/kundli` `product=="diwali"` → `diwali.compute_diwali(...)`, store, return `{report_id, teaser}` only.
- `_render_for("diwali")` → `diwali_report.render_diwali`. `_order_amount_paise` → 49900 for product diwali.
- Routes `/en/diwali` via `_serve_page_with_nav`, `/diwali` → 301; sitemap; robot list; homepage card + review entries.
- Narrative: SECTION_SPECS built from `diwali_bank.NARR_KEYS`; 4 group calls in parallel; MAX_TOKENS/TIMEOUT for diwali;
  validate each value with `lint_text` + the existing number/claim guards, drop bad values (bank fills).
- Delivery (Diwali only): narrative → invalidate/build PDF → WhatsApp (both templates), to the popup/form number only.
- `tests/test_diwali_api.py`: real path end-to-end with TestClient: kundli → order → demo pay/verify → report HTML → PDF route.
