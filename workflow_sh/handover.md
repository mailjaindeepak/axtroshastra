# handover.md — session handover

> **Rule #1 (backend consistency):** every product follows the ONE shared report
> pipeline (see `rule.md` §5). Conform to it; never bolt a page on as a loose
> plug-in. A change to the pattern applies to ALL pages so the site stays one
> coherent system. Do not copy another page's bug/quirk. Before diverging, ask.
> Full rules, gates, and the agent workflow live in **`rule.md`**.

## Current work — Vyapar (business-growth) Hindi version
Branch: `business-growth-hindi` (pushed to fork as a WIP backup — **no PR**, nothing
live). English `/en/business-growth` + Hindi `/hi/business-growth` already merged/live
via earlier PRs (#75/#76/#78); this branch adds the Devanagari funnel.

**Done + verified on localhost (nothing new pushed):**
- Routing: `/en/business-growth` + `/hi/business-growth` + legacy `/business-growth` 301→/en; inline `#axlang` toggle on both pages (compatibility pattern).
- Teaser `_hi`: authored `BIZ_*_HI` tables in `jyotish_maps.py` (agent-drafted, gated: structure parity, tokens preserved, 0 English leaks); `compute_vyapar` emits `_hi` teaser fields (dates→Devanagari, planets→Devanagari); the `.hi` page renders via `hv(_hi, en)`. Preview values now Devanagari.
- Sample hero link text → "रिपोर्ट का नमूना देखें".
- `vyapar_hi.py` + `vyapar_hi_data.py` localizer (fixed shell).

**Remaining (the consistency work, approved, NOT yet started — pending Commander answers):**
1. **`render_vyapar` compose-time Hindi banks** — the ONE real gap: it does `prose(key, bank)=narr(key) or bank` with English-only banks, while `report_view_v2` composes each bank in Devanagari when `meta.lang=='hi'` (the `hi` flag + bank-twin pattern). Apply that same pattern to `render_vyapar`, reusing `BIZ_*_HI`. This is the root cause of every Hindi leak.
2. **Add vyapar to `tests/test_hindi_leakage.py`** — render the Hindi report with the LLM off (worst case) + on; assert zero ≥4-word English runs. This is the CI guarantee that the live product is pure Hindi.
3. **Regenerate the Hindi sample** (29 images + PDF) from the now-pure-Hindi fallback, so the sample matches the product's guaranteed floor. Commander cross-checks.

**Known constraint:** the sample's prose can't use the live LLM locally (prod key, never handled by the assistant) — so the sample is rendered from the compose-time Devanagari **fallback**. It matches the product in facts/structure/language; exact wording differs because the live AI personalizes per person (true of the English sample too).

## Gates that must stay green
pytest · Playwright E2E · ops robot smoke (pending-deploy) · button deploy-gate (`test_report_buttons.py`) · Hindi-leakage gate (`test_hindi_leakage.py`). See `rule.md` §6.
