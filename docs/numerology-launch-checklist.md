# Mulank numerology: launch checklist

Everything the owner must do or decide before the product is public, and before the Rs 299 button can exist. Nothing here has been done in production.

## A. What is in the PR
Landing page `/en/numerology` (noindex), `POST /api/mulank`, the five-page preview (HTML viewer + PDF), the Mulank-only payment routes, the 15-page paid report with secure PDF download, fulfilment retries, Mulank payment recovery, and the guards that stop every shared payment path from unlocking a Mulank report. No existing product's behaviour changes.

## B. How it gets to production (existing process, owner only)
1. Review and merge the PR into `aws-mysql` (CI must be green on Python 3.12: `test`, `e2e`).
2. GitHub Actions > CI > "Run workflow" on `aws-mysql`. The `deploy` job needs both suites green and the `production` environment approval, then runs `eb deploy`, waits for Green, smoke-tests and auto-rolls back.
3. Merging does not publish anything by itself.

## C. Before deploying the free preview
- [ ] CI green on the PR (3.12), including `tests/test_diwali_*` and the e2e suite.
- [ ] Owner approves the privacy policy, terms and consent wording for the new fields (`pages/privacy.html`, `pages/terms.html`), the optional marketing opt-in wording on the form, and a refund policy page. **Not done; the landing page must not go public without this.**
- [ ] Confirm the landing page slug `/en/numerology` and the product name.
- [ ] Confirm `DEMO_MODE` is unset in production (`/api/_demo_pay` must not exist there).
- [ ] After deploy: open `/en/numerology` on a phone and a desktop; submit a test lead; confirm the preview loads, the PDF downloads, fonts look right (the PDF loads Fraunces/Inter through the same Google Fonts link Career Intelligence uses), and the page says the complete report is not available yet.
- [ ] To make it discoverable: remove `noindex`, add the URL to `sitemap()` in `api.py` and to `ops/robot_customer/robot.spec.js` (CLAUDE.md sections 2 and 3). Decide the homepage card (section 4).

## D. Before the Rs 299 button can appear
1. **Verified content.** A named reviewer signs each key a pair needs (`M<n>`, `B<n>`, `PS`, `PB`, `CMP`, `LK`, `Y<n>` for this and next year, and the planet-relation cells). Record it in `mulank_content.REGISTRY` as `Entry(status="verified", reviewed_by="<name>", reviewed_on="<date>")`. Only pair 2-1 has drafted text for every part today; every other pair also needs its text written in `mulank_bank.json`. Personal-year content (`Y<n>`) must be re-checked every 1 January.
2. **Razorpay TEST mode end to end.** Owner sets `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` as environment variables with `eb setenv` (never in chat or git). Run a real test payment: preview > CTA > checkout > report > PDF.
3. **Register the dedicated webhook** in the Razorpay dashboard (test, then live): URL `https://<domain>/api/mulank/webhook`, event `payment.captured`, same webhook secret. Resend an event from the dashboard and confirm it is idempotent; send a tampered one and confirm a 400.
4. **Recovery and delivery.** Confirm the recovery sweep runs (log lines `[mulank] ...`), a paid report's PDF downloads again without paying, and the retry button works after a forced PDF failure.
5. **Security checks.** Another customer's link returns 404; unpaid reports never serve the PDF; no personal data in logs.
6. **Owner confirms** the Rs 499 strike-through is a genuine price (or removes it from `mulank_pricing.py` and `numerology_preview.py`).
7. Only then switch live keys with `eb setenv` and make a small real purchase and refund.

## E. Until then
Public visitors get the free preview and an honest message that the complete report is not available yet. No purchase button, price or checkout code is sent for any pair that is not fully verified.