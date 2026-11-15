# Numerology content model and approval

## What a customer gets (all on the one URL, /en/numerology)
1. The landing page shows the introduction and the form (name, date of birth as day / month / year, optional gender, WhatsApp number). **No price, no payment button.**
2. After submitting, the personalised 5-page preview opens in place (an iframe of `/en/numerology/preview/{id}?embed=1`); the URL does not change.
3. Only then, and only if the customer's complete report is approved and drafted, the page shows the offer (₹499 struck through only when `MULANK_LIST_PRICE_CONFIRMED=1`),
   then ₹299 and **Unlock My Full Numerology Report — ₹299**. If it is not available, nothing is offered and the order route refuses (409).
4. Razorpay checkout opens from the page; payment is verified server side (signature, order, amount 29900, INR, captured). On success the page swaps the preview for
   the "Your full report is ready" banner, a **Download My Full Report** button and the 15 cards, with no redirect and no waiting.
5. The same button downloads the PDF again at any time, with no second payment: after a reload the page restores itself from the opaque report id kept in
   `sessionStorage`, and `/en/numerology/report/{id}` remains a permanent link (shown to the customer as "Keep this link").
No manual delivery, WhatsApp or email is involved. Pre-order stays off (`MULANK_PREORDER` unset) and is not part of the journey.

## Per-number content (81 combinations from nine blocks per kind)
| Key | Meaning | Used on cards |
|---|---|---|
| M1-9, B1-9 | Mulank and Bhagyank themes (existing) | 4, 8, 9 |
| PM1-9 | How a Mulank comes across | 5-7 |
| PG1-9 | Inner drive and direction of a Bhagyank | 5-7 |
| CB1-9 | Relationships block for a Mulank | 10 |
| LK1-9 | Lucky references via the planet table (colour, day, gem) | 13 |
| Y1-9 | Personal Year 1-9 (theme, pace, three prompts) | 11, 14 |
| R:Planet>Planet | Planetary-links wording (existing, 42 cells) | 4 |
| PS:2-1 | Optional sourced pair statement (2-1 only) | 4 |

Each card is composed at render time from these blocks. No number's text is ever substituted for another's, nothing is calculated that the report does not
already derive (digits, reductions, calendar-year personal years), and incomplete content is refused rather than back-filled.

## What blocks a sale
A combination is sellable only if **every key it needs is approved and has drafted text**. Today all 106 keys are `needs_review`, so **no combination
can be bought**: the landing page shows no price and no purchase button, and the paid routes refuse. This is intentional.

## Owner approval (the owner's step)
1. Read `docs/numerology-content-review-pack.md` (regenerate with `python tools/export_mulank_review_pack.py`).
2. Edit `mulank_bank.json` for anything to change; run the tests.
3. `python tools/approve_mulank_content.py --editor "<editor>" --approved-by "<owner>" --date YYYY-MM-DD --all` (or `--keys ...`). `--status` shows progress.
4. Open a PR for the ledger change. After merge and the guarded deploy, live checkout opens for exactly the combinations whose keys are all approved.

## Decisions for the owner to confirm in review
- Compatibility table (card 10) is derived from the planetary-friendship labels; Rahu/Ketu (4 and 7) are listed as "not covered", and a Mulank 4 or 7 shows no table.
- The lucky-reference table assigns Rahu a smoky grey / Saturday / hessonite and Ketu brown / Tuesday / cat's eye; confirm or change.
- Wording for Bhagyank 2, 5 and 9 rests on thinner source material; Personal Year 3-9 text was written to match the style of the approved years 1-2.
- Dial positions on card 6 are illustrative and labelled so.
- The ₹499 regular price appears only when `MULANK_LIST_PRICE_CONFIRMED=1`.

## Tests
`tests/test_mulank_all_pairs.py` proves text completeness, a 15-card production report and clean editorial QC for all 81 combinations in every Personal Year 1-9,
and Chrome PDF generation (15 pages) for a 21-combination spread by default or all 81 with `MULANK_PDF_ALL=1` and `CHROME_BIN` set.
These use a test-only approved registry; they do not approve anything for real customers.

`tests/test_mulank_browser.py` drives the real page in Chrome at 360, 390 and 1280 px (Playwright for Python; skipped where Chrome is missing): same URL throughout,
no horizontal or nested scrolling, failed and dismissed payments, success, 15 cards, a real 15-page PDF downloaded twice and after a reload. Razorpay's checkout is
stubbed in the browser; the server-side verification is the real code. Set `CHROME_BIN` if Chrome is not found.

## Launch requirements (separate, in order)
1. Owner approves content (above). Until then no unlock button can appear for anyone.
2. Set `NAV_NUMEROLOGY=1` (adds "Numerology Report" to the site menu), Razorpay test keys and webhook secret via Elastic Beanstalk environment variables.
3. Run a ₹299 test-mode payment end to end, then switch to live keys.

## Not verified here
Razorpay test-mode checkout with real credentials (none are available in this environment); the payment path is exercised against a faked gateway.
