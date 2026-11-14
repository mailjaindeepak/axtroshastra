# Audit note: Mulank numerology funnel (3 Nov 2026)

Branch `mokshi-numerology`, based on `upstream/aws-mysql` @ 543a823 (re-fetched before push: unchanged, 0 behind, 13 commits ahead, linear).
Specs: `docs/numerology-report-spec.md` and `docs/numerology-report-spec-v2-amendment.md`. Approved look: Career Intelligence Version C (preview and report), existing marketing tokens (landing page).

## What was verified (and how)
- **Mulank tests (local, Python 3.11, real MySQL 8.4):** 237+ pass across `test_mulank_*`, `test_numerology*`, plus the existing `test_verify`, `test_webhook_verify_double_fire` and `test_payment_recovery` suites.
- **Full suite (local, Python 3.11):** 1215 passed, 18 failed, 3 collection errors, all Diwali (`diwali_report.py:687` uses an f-string that only parses on Python 3.12). Local Python 3.12 is not available on this machine (no pyswisseph wheel). **CI runs 3.12 and is the real gate.**
- **Blast radius on shared code:** `api.py` changes are: one `include_router` line, one helper `_is_mulank_report`, and one-line early exits in `/api/order`, `/api/webhook`, `/api/verify`, the reconcile sweep and `/api/_demo_pay`. Each only fires for product `numerology_mulank`; `tests/test_mulank_shared_guards.py` proves each bypass is closed (10 of 15 tests fail without the guards) and that other products behave as before. `db/`, `payments_v2`, `reports_v2`, `pdfgen` and `ratelimit` are untouched.
- **Fidelity:** the paid renderer's text matches the approved v4 sample on all 15 pages (similarity 1.0, footers ignored). Calculations were hand-checked for five birth dates and swept over all 81 pairs.
- **Leak proofing:** preview pages 3-5 are byte-identical for all 81 pairs and any name; PDF text layer and metadata are scanned in tests.
- **Mutation spot-checks:** removing the paid check on the PDF route and the amount check on settle are both caught by tests. Two other mutations survived for good reasons (a redundant second gate; a redundant status pre-filter).
- **Browser run (local, stubbed Razorpay, test-only verified fixture):** landing, form, preview, CTA, stub checkout, paid report and PDF, on a 390px phone and a 1280px desktop; no page errors, no horizontal overflow.

## Change of plan (4 Nov 2026): owner approval instead of external verification
- `mulank_content.py` now separates **approved** (status `verified` = external expert, or `owner_approved` = named editor + named owner + date) from **complete** (drafted text exists in `mulank_bank.json`). A pair is eligible only if both hold; the readiness result reports `approved`, `complete`, `approval_basis` and a precise `reason_code` (`content_incomplete` / `content_not_approved` / `ok`).
- The approval ledger is `mulank_registry.json` (data, reviewed through PRs, strict loader). `sample_ok`, `needs_review` and `pending` never count even if names are filled in.
- Rahu/Ketu pairs and the conflicted Venus/Mars pair use the approved line 4i ("published tables differ") and need no relation-table cell.
- `mulank_qc.py`: bank lint (flagged vocabulary, placeholders, empty fields, paragraphs reused across pairs) and a render-time guard that refuses to deliver a report with any fallback or sample marker, wrong card count or missing disclaimer.
- Still true: no entry is approved, so every pair is ineligible today. Approval is a data change plus drafted text; neither exists for 80 of 81 pairs (see `docs/numerology-content-gap-and-plan.md`).

## What this is NOT
- Not a formally converged section 20b audit. There was no independent reviewer loop; verification was by the tests and checks above.
- **Not run:** Playwright e2e, `ops/robot_customer`, real Razorpay test-mode calls (no test keys), the dedicated webhook against Razorpay, PDF font loading on the deployment host, any staging environment.
- **No content is approved.** `mulank_registry.json` contains no `verified` or `owner_approved` entry, so every pair is ineligible in production: the site can serve the free preview and the "not available yet" message only.

## Known open items
- A named internal editor and approving owner, and approval of drafted content per key (see `docs/numerology-launch-checklist.md`). External expert verification is optional.
- Privacy policy, terms and refund text have NOT been updated for the new fields (name, date of birth, WhatsApp number, optional marketing opt-in). The marketing opt-in wording on the landing page is a proposal, not approved legal text.
- Preview redesign (richer page 2, "glimpse" page 3) is a proposal in the owner's review pack, not built.
- Waitlist endpoint not built. Landing page is `noindex`, not in `sitemap.xml`, not in `ops/robot_customer`'s route list (deliberate until launch).
- Hindi version not built; English only.
- The shared reconcile sweep still polls Razorpay for Mulank orders before skipping them (harmless extra API calls).
- Site-wide footer disclaimer injected on every page contains words on the section 5b list; not part of this change.