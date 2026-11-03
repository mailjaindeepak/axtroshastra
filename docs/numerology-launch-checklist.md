# Mulank numerology: prioritised launch checklist (revised 4 Nov 2026)

Change of plan: external numerologist verification is no longer required. Content is released by the business owner after internal editorial review. The code now supports this: a content entry is **approved** if it is `verified` (external expert) OR `owner_approved` (a named editor + a named owner + a date), and a pair is sold only when every entry it needs is approved AND its drafted text exists (**complete**). Nothing incomplete, sample or substituted can be sold or delivered (`mulank_content.py`, `mulank_qc.py`, `numerology_report.py`).

Status key: DONE = built and tested locally. OWNER = needs the owner. ME = engineering/drafting work I can do now.

## Launch-now sequence (management priority, 4 Nov 2026)
Three gates, in this order. Each is independent; later ones never block earlier ones.
- **Gate A: public free preview** (Track 1 below). Needs: approved legal text, PR merged, deploy. No payment of any kind.
- **Gate B: Rs 299 pre-order** (`docs/numerology-preorder.md`). Built and tested, closed by default. Needs everything in Gate A plus: the owner's exact delivery promise, the approved refund page, Razorpay test and then live keys, the dedicated webhook, a decision on how customers are told, and the owner's go-ahead on the payment flow.
- **Gate C: instant purchase** for combinations whose content is approved and complete (Track 2 below). Switches on automatically per combination as the owner approves content; nothing else to deploy.
Optional: `MULANK_LIST_PRICE_CONFIRMED=1` shows the struck-through Rs 499 once the owner confirms it is a genuine regular price (`docs/numerology-landing-pricing.md`).
Optional nav entry "Numerology Report": set `NAV_NUMEROLOGY=1` once the owner approves it (default off).

## Track 1: free preview live (no purchase button). Shortest path.
| # | Task | Who | Status | Est. |
|---|---|---|---|---|
| 1.1 | Approve privacy/terms additions, consent and marketing opt-in wording, refund page (drafts: `docs/numerology-legal-drafts.md`) | OWNER | drafts ready | 0.5-2 days |
| 1.2 | Decide: keep current preview, or the richer page 2 / "glimpse" page 3 (proposal pack, piece7). Keep or drop the Rs 499 strike-through | OWNER | waiting | 0.5 day |
| 1.3 | Put approved text into `privacy.html`, `terms.html`, new `refund.html`; update tests | ME | blocked by 1.1 | 0.5 day |
| 1.4 | (if redesign accepted) build page 2/3 changes, visual QA, tests | ME | blocked by 1.2 | 1-1.5 days |
| 1.5 | Open PR `mokshi24:mokshi-numerology` -> `aws-mysql`, owner reviews, CI green on Python 3.12 (`test`, `e2e`) | OWNER | branch pushed | 0.5-1 day (CI-only failures possible) |
| 1.6 | Deploy: CI "Run workflow" on `aws-mysql` (protected `production` environment) | OWNER | waiting | 0.5 day |
| 1.7 | Post-deploy smoke on mobile + desktop, PDF fonts on the server, DEMO_MODE unset | ME + OWNER | waiting | 0.5 day |
| 1.8 | Optional: remove noindex, add to sitemap and `ops/robot_customer`, homepage card (owner decision, CLAUDE.md sections 2-4) | OWNER | decision | 0.5 day |

Until the paid product is ready, visitors get the preview and an honest "not available yet" message (the landing page shows it automatically while nothing is sellable).

## Track 2: paid product (Rs 299). Critical path = content.
| # | Task | Who | Status | Est. |
|---|---|---|---|---|
| 2.1 | Decide the content model for the 80 missing pairs. Recommended: compose from per-number blocks instead of 80 authored pairs (`docs/numerology-content-gap-and-plan.md`) | OWNER | waiting | 0.5 day |
| 2.2 | Decide the content rules still open: compatibility-list basis (card 10), lucky-reference rule (card 13), Rahu/Ketu planet for numbers 4 and 7, how to treat Bhagyank 2/5/9 (no source) | OWNER | waiting | 0.5-1 day |
| 2.3 | Name the internal editor and the approving owner for `owner_approved` entries | OWNER | waiting | minutes |
| 2.4 | Draft Y3-Y9 year blocks (blocks EVERY pair: today only 11% of birthdays have both personal years drafted) | ME | ready to start | 0.5 day |
| 2.5 | Draft the per-number content (personality, dials, strengths table, bonds, lucky lookups) | ME | blocked by 2.1-2.2 | 1.5-2 days |
| 2.6 | Data-model and renderer change to number-keyed content; tests | ME | blocked by 2.1 | 3-4 days |
| 2.7 | Run `mulank_qc` on all content; internal editorial review; owner approves entries in `mulank_registry.json` (about 27 approval units, not 400) | OWNER + editor | blocked by 2.5 | 2-4 days |
| 2.8 | Render and visually check all 81 pairs x year combinations (overflow, clipping) | ME | blocked by 2.6 | 1-1.5 days |
| 2.9 | Owner supplies Razorpay TEST keys as environment variables (`eb setenv`; never in chat or git) | OWNER | waiting | 0.5 day |
| 2.10 | Razorpay test-mode end to end: preview > checkout > report > PDF; webhook; recovery; failed/pending/duplicate cases | ME + OWNER | blocked by 2.9 | 0.5-1 day |
| 2.11 | Register `https://<domain>/api/mulank/webhook` (event `payment.captured`) in the Razorpay dashboard and resend/tamper tests | OWNER | blocked by 2.9 | 0.5 day |
| 2.12 | Production-readiness checks (below), then switch live keys, small real purchase and refund | OWNER + ME | last | 0.5 day |

## Production-readiness checks (before any live payment)
- [ ] CI green on Python 3.12 incl. Diwali tests and e2e; all other products unaffected (shared guards tested).
- [ ] `DEMO_MODE` unset in production; `RAZORPAY_*` mode matches intent (test vs live).
- [ ] PDF generation and fonts verified on the deployment host (`/api/pdf_health`); report PDF opens on a phone.
- [ ] Customer data: only the new fields are stored; none in logs or URLs (tested); report links are private ids; headers no-store/noindex.
- [ ] Unpaid reports never serve the PDF; another customer's link returns 404 (tested).
- [ ] Every sold pair passes `lint_bank` and renders 15 cards with no fallback or sample marker (enforced at render time).
- [ ] Privacy, terms, consent and refund text approved and live. Payment recovery and retry verified against Razorpay test mode.
- [ ] Delivery is the website link + PDF only. WhatsApp sending stays off until a provider and template are approved.

## How approval works now (no external expert)
1. Content passes `mulank_qc.lint_bank` (flagged words, placeholders, empty fields, no paragraph reused across pairs).
2. A named internal editor reviews it; the owner approves it.
3. Add the entry to `mulank_registry.json`: `{"status": "owner_approved", "editor": "<name>", "approved_by": "<name>", "approved_on": "<date>"}` through a normal PR, so every approval is dated and in git history.
4. `sample_ok`, `needs_review` and `pending` never count. An approved entry without drafted text still blocks the sale.