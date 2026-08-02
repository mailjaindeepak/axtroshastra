# Marriage Report — Build Plan (v2 blueprint)

Phased implementation of `marriage-report-blueprint.md` (LOCKED v2). Each phase is
shippable: after every phase the report renders correctly with `NARRATIVE_ENABLED`
both on and off. No phase leaves the product broken.

Guiding constraints:
- Facts stay deterministic; LLM writes prose only (3-layer guardrail unchanged).
- English + Hindi only. English is the deterministic base; Hindi = LLM Devanagari
  prose + a slim English→Devanagari label localizer.
- Golden tests (`tests/golden/marriage_T0.json`) are regenerated once structure lands.

---

## Phase 0 — Foundations (no visual change) ✅ low risk
Files: `narrative.py`

1. Expand `SECTION_SPECS["marriage"]` from 6 → ~30 slots (build sheet in blueprint).
2. Product-aware `NARRATIVE_MAX_TOKENS`: ~8000 for marriage, keep 4096 default otherwise.
3. Confirm `_facts_for_llm` already includes `navamsa`, `extras`, `chart` (it does).
4. Confirm `_resolve_lang` returns only `english` | `hi` (it does). Remove any Hinglish path assumptions.

Exit check: `generate_narrative` returns the new keys for a sample payload (unit test);
renderer still ignores them → report byte-identical. Goldens unaffected.

## Phase 1 — English bank rewrite ⚠ large content task, low code risk
Files: `report_view.py` (render_report banks), `report_addons.py`, `jyotish_maps.py`
(`PLANET_IN_7TH`, `VENUS_STYLE` suffixes, `REMEDY_7L` notes), engine Hinglish strings.

1. Rewrite every deterministic Hinglish string to clean English. Inventory of Hinglish
   sources to convert:
   - `render_report` section copy (answer box, chart snapshot, method, manglik body,
     quiet periods, past, year outlook, partner, actions, summary, disclaimer).
   - `report_addons.py`: `d9_section_html`, `occupants_html`, `planet_table_html`,
     `scoring_box_html`, `PLANET_IN_7TH`.
   - `navamsa.py` `reasons`/`band_note` strings (currently Hinglish).
   - `engine.py` `venus_style` suffixes; `marriage_extras` gem_note.
2. Keep numbers/dates/labels rendering identical; only prose language changes.

Exit check: with LLM off, the English report reads coherently end-to-end; snapshot review.

## Phase 2 — Engine additions for the 3 new components ⚠ medium
Files: `engine.py` (+ `jyotish_maps.py` for authored banks)

1. **`extras.dasha_remedies`** (Comp 9): new helper `_dasha_remedies(chart, tree, windows, today)`
   → list of `{period, lord, reason, fast_day, mantra, gem|gem_note}` for weak lords in the
   active + next ~3y periods (AD_WEAK, debilitated/combust MD/AD lord, Saturn/Ketu dry).
   Reuse a planet-keyed remedy map (generalize `REMEDY_7L`). Add to `marriage_extras`.
2. **Manglik Dos & Don'ts** (Comp 6): authored `{status: {do:[...], dont:[...]}}` map
   (deterministic, careful/non-fatalistic). Rendered on D8.
3. **Weak-period actions** (Comp 5): authored action text keyed to quiet-phase reason;
   rendered on D5 over existing `_weak_periods()`.

Exit check: new fields present in payload; unit tests assert shape; goldens regenerated.

## Phase 3 — Renderer restructure into 4 tiers 🔴 largest code change
Files: `report_view.py` (`render_report` rewrite), `report_addons.py`

1. Refactor `render_report` from one long f-string into per-page builders following the
   33-page flow (Main → Summary S1–S6 → Detailed D1–D13 → Astrology A1–A13).
2. Wire every prose slot as `narr(p, "<slot>") or <english bank>`.
3. New pages: D5 (weak actions), D8 (manglik dos/don'ts), D10 (per-dasha remedies).
4. Conditional windows: when <3, drop `window_2/3` pages and render a ranked
   best-months deep-dive on window 1; never a blank page.
5. Keep print/PDF CSS working (page breaks per `.pg`); verify PDF pipeline.

Exit check: full report renders in English (LLM on and off); PDF pregenerate works;
visual pass on T0/T1/T2/T3 fixtures.

## Phase 4 — Hindi (Devanagari) localizer rebuild ⚠ medium
Files: `shaadi_hi.py`, `shaadi_hi_data.py`, `api.py` (`_render_for` already wired)

1. Repurpose `shaadi_hi.localize` to translate only deterministic **labels/headers/
   tokens** (signs, planets, nakshatras, grades, months, table headers, UI labels) —
   keep the existing token/grade/month maps; drop the obsolete Hinglish prose dict.
2. LLM Devanagari prose passes through unchanged (pure-Devanagari runs resolve to self).
3. For `meta.lang == "hi"`, narrative is generated in Devanagari (`_resolve_lang`).

Exit check: Hindi report — prose is Devanagari (LLM) or English bank fallback if LLM
off; all labels/tables/headers Devanagari; no stray Hinglish.

## Phase 5 — Tests, goldens, enablement
Files: `tests/*`, deploy config

1. Regenerate `tests/golden/marriage_T0.json`; add goldens for a window-count<3 case.
2. Extend `test_narrative.py`: marriage product returns all slots; english + hi; token bump.
3. Unit tests for `extras.dasha_remedies`, manglik dos/don'ts, weak actions.
4. Verify via `/api/narrative_preview/{rid}` in staging before `NARRATIVE_ENABLED=1`.

---

## Sequencing & risk

- Phases 0–2 are additive and safe (report unchanged or only prose-language change).
- Phase 3 is the high-risk restructure — do it behind the existing renderer until parity,
  then switch. Consider a `render_report_v2` built alongside, swapped in `_render_for`
  once verified, old one deleted after.
- Biggest effort is **content** (Phase 1 English banks + Phase 2 authored lists +
  ~30 slot briefs), not code.

## Open items to confirm before Phase 3
- Keep transparency pages (scoring scorecard A11, full planet table A2) — yes per v2.
- Upsell/CTA placement in the new flow (career upsell, rectification hook) — carry over.
- Exact page count tolerance (33 ± a few as content dictates).
