# Audit note: Diwali Wealth & Prosperity Report (27 Oct 2026)

Branch `feat/diwali-report`, based on `upstream/aws-mysql` @ 6896200 (re-fetched 27 Oct: unchanged, no conflicts expected).
Spec: `docs/diwali/diwali-report-spec.md`. Approved look: Mock 3C v2 (report), free-preview mock (landing page).

## What was verified (and how)
- **Full CI gate, run as CI runs it, against a local MySQL 8.4:** main suite 1516 passed / 0 failed / 0 skipped (baseline before this work: 603); `db/` suite 51 passed; Playwright e2e 73 passed, 6 flaky (passed on retry), 1 failed.
- **The 1 e2e failure** (`shaadi.spec.js:54`, mobile city autosuggest) is not Diwali code. On clean `upstream/aws-mysql` (separate temporary worktree) shaadi, checkout and padhai specs also flake (2, 5 and 6 flaky specs in three runs, incl. the desktop autosuggest). Only 3 upstream runs were done, so "pre-existing flake" is likely, not proven.
- **Blast radius:** every `api.py` and `narrative.py` hunk was diffed against upstream and is gated on product "diwali" (new KundliIn fields, price 49900 by product, routes, sitemap, delivery branch, narrative functions). Other products' system prompt, placement check and delivery order are unchanged.
- **Real-path tests:** `tests/test_diwali_api.py` drives kundli → order → demo pay → report → PDF; `tests/test_report_buttons.py` now covers Diwali; the engine routes through `compute_chart`/`compute_report` (`test_routes_through_shared_engine`).
- **Product matrix:** `tests/test_diwali_versions.py` (28 buyers across every form option: 425 checks) is green; checks include PDF page size/count and card overflow in headless Chrome, banned words, status-assuming Marriage/Family wording, T2/T3 never saying "best time", no month names in the free preview.
- **Independent verify agents** reviewed the engine, the renderer, the landing page and the AI-value validation in several rounds; each finding was reproduced before fixing.

## What this is NOT
- It is **not** a formally converged §20b audit (two consecutive independent rounds with the same findings). Verification was by independent verify agents per component plus the full gate above; the loop was capped for cost.
- **The AI-on path has only been tested with fake AI replies.** No real Anthropic key was used. A real AI-on report must be generated and read on the server after deploy (≈ ₹6–10).
- The "no identical paragraph across 5 buyers" rule applies to AI-on output only (owner decision, 26–27 Oct); the deterministic fallback is intentionally generic.

## Known open items (none block the PR)
- Puja times for Pune, Hyderabad and Jaipur are computed but not hand-checked against Drik Panchang (a human step).
- Hindi page not built (written exception: Hindi after English approval).
- Fallback wording for front answers/takeaways still has counts ("seven good months are marked"); AI rewrite covers it; polish in a later PR.
- The site-wide footer disclaimer (injected on every page) contains "medical"/"guarantees" (CLAUDE.md §5b); not part of this change.
- Tests added to `tests/test_ops_workflows.py` import-audit: `fitz`→pymupdf mapping and sibling test modules as first-party; `playwright` added to `requirements-dev.txt`.
