# Numerology report spec: v2 amendment (approved in Piece 0; status as built)

> **Status as built (3 Nov 2026).** The text below is the amendment the owner approved before any application code was written (CLAUDE.md sections 8 and 18). Where the build differs, the difference is listed here and wins over the text below:
>
> - **Approval (changed 4 Nov 2026).** External expert verification is no longer required. An entry is approved if `verified` (expert) or `owner_approved` (editor + owner + date) in `mulank_registry.json`, and a pair is sold only if every key is approved AND has drafted text. See `docs/numerology-content-gap-and-plan.md`. Wherever the text below says "verified by a named reviewer", read "approved".
> - **Registry keys.** `PS:<m>-<b>` (pair statements), `PB:<m>-<b>` (cards 5-7), `CMP:<m>-<b>` (card 10), `LK:<m>-<b>` (card 13, pair level, not per number), `M<n>`, `B<n>`, `Y<n>`, `R:<Planet>><Planet>`. Eligibility needs every key `verified` with a named reviewer and review date, AND drafted text in `mulank_bank.json`. Text alone never makes a pair eligible.
> - **Price.** Rs 299 charged (`mulank_pricing.py`); Rs 499 is shown struck through on preview page 4 and the purchase bar. The strike-through is only honest if Rs 499 is a genuine price (owner to confirm).
> - **Ineligible visitors** get five pages: page 4 is the availability message and page 5 is a button-free "What the Report Covers". No price, no checkout script and no checkout button is sent to them; `POST /api/mulank/order` returns 409.
> - **Waitlist.** The box renders only if the owner supplies consent wording (`mulank_routes.WAITLIST_CONSENT_TEXT`, empty today). The waitlist endpoint is NOT built yet.
> - **Phone.** +91 only in v1 (10-digit Indian mobile).
> - **Payment.** Dedicated routes `/api/mulank/order|verify|webhook` verify signature, order id, amount 29900, currency INR, captured status and refunds. Shared paths (`/api/webhook`, `/api/_demo_pay`, `/api/order`, `/api/verify`, the reconcile sweep) refuse Mulank reports. Mulank has its own recovery (`mulank_recovery.py`).
> - **Paid report.** 15 cards in production. Production never prints a fallback or sample line and never substitutes another pair's reading; sample mode exists for labelled test PDFs only and refuses to run with live payment keys.
> - **Open decisions** in section 10 below are still open unless answered in the PR thread.

---
# DRAFT amendment: docs/numerology-report-spec.md -> v2 (Mulank free preview, inputs, funnel, eligibility, security)

STATUS: DRAFT for the owner. Nothing here is applied to the repo. It is written as a diff-style proposal against `docs/numerology-report-spec.md` (line numbers refer to the current file) so it can be applied deliberately per CLAUDE.md section 18. Companion visual mock: `preview-5page-mock.html` (+ `preview-5page-mock-SAMPLE.pdf`, `preview-5page-mock-ineligible-variant.html`). Per CLAUDE.md sections 8 and 18 no renderer, route, pipeline or checkout code starts until this amendment and the mock are approved.

Legend: `-` removed/replaced text, `+` added text. "Spec" = the current doc.

---

## 0. Header (spec lines 3-8)

```
- **STATUS: structure APPROVED by the owner (structure "B" below).** The visual mock
- (`docs/mockups/mulank-report-mock.html` and `docs/mockups/mulank-preview-mock.html`) is built
- strictly against the card list in this doc and is still pending owner approval.
+ **STATUS: structure "B" (paid report) APPROVED; v2 amendments (free preview, inputs, funnel,
+ eligibility, security) PROPOSED, pending owner approval.** The paid-report wording is the Stage B
+ final wording (`STAGE-B-FINAL-WORDING.md`, 15 cards). The five-page free preview mock
+ (`docs/mockups/mulank-preview-5page-mock.html`) replaces the 2-card preview mock and is pending approval.
```

## 1. Product meta (spec lines 12-22)

```
  | Slug / route | TBD (proposed `/en/numerology`) |
- | Language | English only for now; Hindi twin deferred |
+ | Language | English only. No `/hi/` route and no `hreflang hi` until a Hindi twin exists (CLAUDE.md section 7 needs an explicit yes). |
- | Price / funnel | Price TBD. Default funnel per `CLAUDE.md` section 1: form, preview, contact popup, payment, report + PDF + WhatsApp. |
+ | Price | NOT DECIDED. One server-side constant (e.g. `MULANK_PRICE_PAISE`) is the only source. Mocks show the visible token `₹[PRICE]`. No strike-through, discount or countdown. |
+ | Funnel | Form (name, DOB, optional gender, WhatsApp, consents) -> five-page preview -> (eligible pairs only) checkout -> website report + PDF (+ WhatsApp if an approved provider is configured). See section 4: a deliberate deviation from CLAUDE.md section 1. |
- | Homepage | Undecided |
+ | Homepage | No homepage card until the product is sellable (CLAUDE.md section 4, owner may revisit). |
```

## 2. DECISIONS ASSUMED (default adopted unless the owner objects)

1. English only; no `/hi` route until Hindi exists.
2. No testimonials/reviews on the product page (deviation from CLAUDE.md section 5, recorded).
3. No homepage card yet.
4. Preview is an HTML viewer (instant, works on mobile) with a lazily generated PDF from the same HTML (`GET /preview/{rid}` and `GET /preview/{rid}.pdf`); PDF cache key prefixed (`pv_<rid>`) so it can never be served as the paid report.
5. Ineligible pairs still receive preview pages 1-3; page 4 shows an honest availability message and a consented waitlist instead of the purchase CTA and price. Page 5 (the "What you'll unlock" page with the second CTA) is NOT shown to ineligible visitors (it promises a product that cannot be bought). Owner may instead want a CTA-free page 5; open decision 9.
6. The price is not decided; it is read from one server-side constant. The mock uses the placeholder `₹[PRICE]`.
7. Name and WhatsApp are collected on the main form BEFORE the preview. This is a deliberate deviation from CLAUDE.md section 1 (popup before payment); code precedent: milan, career-intelligence, vyapar, marriage-v2 already send `phone` with the create request. Consequences accepted: fewer previews (phone friction), leads exist for people who never pay, phone is unverified (no OTP).
8. Gender is optional with "Prefer not to say"; stored (NULL when not stated) but unused by the calculation and the text. All outputs (numbers, workings, every preview and report byte except the stored field) are identical for every gender value; a test proves it.
9. Phone is India (+91) only in v1 (10-digit national number, honest message for other countries) unless the owner approves international numbers (needs E.164 parsing and a wheelhouse rebuild).
10. Mulank strict payment verification lives in Mulank's own endpoints; the shared payment-path fixes ship as a separate PR.
11. The "price is not decided" and "no reviewer named yet" facts are blockers for charging, not for building.
12. Preview page 2 shows FACTS ONLY for every visitor (see section 5).
13. WhatsApp at launch only if both Twilio templates (PDF media + text fallback) are already approved and configured; the website report is the primary delivery.

## 3. Inputs (replaces "Approved decisions" 1 and 2, spec lines 26-30)

```
- 1. **Input: date of birth only.** No name number, no birth time, no place, no gender. All wording is
-    gender-neutral; there is no gender branching, so CLAUDE.md section 12 branch tests do not apply.
- 2. **Invalid or partial DOB shows an explicit inline error, never a silent default** ...
+ 1. **Inputs (form):**
+    - Full name (required, 2-80 chars after trim; stored; used as the greeting on preview page 1 and the report cover; HTML-escaped wherever rendered; never used in the calculation; no name number).
+    - Date of birth (required; the ONLY calculation input; no birth time or place).
+    - Gender (optional: Female / Male / Other / Prefer not to say; stored as NULL when "Prefer not to say" or untouched). NOT used by the calculation, the pair keys, the selection logic or any text. All wording stays gender-neutral. Test: for each gender value (and none) the computed result and every rendered byte of pages 1-5 and the paid report are identical except the stored field. No section 12 branch tests apply because there is no branching.
+    - WhatsApp number (required; India +91, 10 digits in v1; used for delivery and, only with consent, the waitlist). Delivery always goes to this number, never to Razorpay's contact number (CLAUDE.md section 1 preference order retained).
+    - Consents: (a) required, unchecked by default: Terms and Privacy; (b) a SEPARATE marketing opt-in, UNCHECKED by default, optional, never a condition of the preview or purchase. Both stored with timestamp and policy version. No marketing is sent until the policy text is approved.
+ 2. **Invalid or partial input shows an explicit inline error, never a silent default** (unchanged for DOB: incomplete, impossible e.g. 31 Feb, future, earlier than the minimum year). Same rule for name (empty), WhatsApp (not 10 digits) and the consent box. Server returns 422 with field-level messages; the client never invents a default.
```

Privacy and terms text must be updated for the new fields, the waitlist and the marketing opt-in before launch (owner/legal supplies wording; placeholders only in the mock).

## 4. Funnel shape and the deviation callout (replaces "Funnel preview", spec lines 122-138)

```
+ > **DELIBERATE DEVIATION from CLAUDE.md section 1 (called out up front, per its last bullet):**
+ > name and WhatsApp are collected on the main form BEFORE the preview, not in a popup before payment.
+ > Already practised by milan, career-intelligence, vyapar and marriage-v2 (the create request carries `phone`).
+ > CLAUDE.md section 1 and this spec must be updated together when approved.
- Mocked separately in `docs/mockups/mulank-preview-mock.html` (2 cards). Mirrors the Career Intelligence teaser pattern ...
+ Mocked in `docs/mockups/mulank-preview-5page-mock.html`: exactly FIVE 430 x 830 cards (323 x 623 pt in print).
+ Flow: form -> `POST /api/mulank` (validate, compute, evaluate eligibility server-side, store lead + consents, build the preview) ->
+ preview (HTML viewer, lazy PDF) -> [eligible only] `POST /api/order` (re-checks eligibility) -> Razorpay -> verify/webhook -> report page + PDF (+ WhatsApp).
- **Contact popup placement:** after the preview is shown, tapping the unlock CTA opens the contact popup ...
+ There is no contact popup in this product. The CTA buttons start checkout directly (the number is already on file).
  The EN/HI toggle, if added later, clears the name and the preview on switch (CLAUDE.md section 7).
+ Failure paths: payment failed/cancelled -> the preview stays and retry is possible; paid but render failed -> a "preparing your report" page with retry and no second charge (`already_paid`).
```

## 5. The five-page free preview (replaces "Free part / Locked / Must NOT be given away", spec lines 128-134)

Page size 430 x 830 px, same Version C theme as the paid report (CI_CSS / CI_DEFS), production print CSS. Exactly five cards; one extra variant for page 4. All numbers below come from `compute_mulank` (tested engine); the name is the only other dynamic value.

| # | Card | Contains | Dynamic? |
|---|---|---|---|
| 1 | YOUR CORE NUMBERS | Greeting with the customer's name (HTML-escaped) and DOB; Mulank and Bhagyank tiles with ruling planet; step-by-step workings (incl. the 11/22 intermediate step); "How to read these" box using ONLY approved static wording: 3b "Contemporary Indian numerology writing reads Mulank as how you go about things and Bhagyank as your direction. Neither is ranked here.", 3c "Yours: Mulank {m} (how), Bhagyank {b} (direction).", and, only when a working passes through 11 or 22, 3a "Some numerology writers retain 11 and 22 as special numbers; this report reduces them to single digits, so other readings may differ."; the 14-word-form disclaimer. | yes (engine + name) |
| 2 | YOUR NUMBERS TOGETHER (facts only) | Heading built from the two numbers ("Mulank {m} with Bhagyank {b}"); the two numbers and planets side by side with "How you go about things" / "Where you are headed" and their source (birth day / whole date); the rule-built sentence 4c "Read together, Mulank {m} sets how you go about things and Bhagyank {b} sets where you are headed." + "Neither is ranked."; a static 3x3 table of the nine numbers and their planets with the user's two numbers marked (plus 15d "Planet links follow the scheme used in Indian numerology; some writers assign 4 and 7 differently."); if m == b the calculated fact 4h "Your Mulank and Bhagyank are both {m}, linked with {X}."; ONE reflection question, identical for every visitor (proposed text, needs approval): "Think of a goal you are working toward at the moment. How are you going about it, and how does that sit with where you hope to end up?" | yes (engine) |
| 3 | YOUR QUICK REFERENCE | Four LOCKED cards: Lucky Numbers, Lucky Colours, Lucky Days, Gemstones: category + lock icon + one generic description. No values, no swatches, no blur. | NO: `render_page3()` takes no arguments |
| 4 | PRIMARY CTA | Heading "Your Numbers Are Just the Beginning."; copy "You've discovered your core numbers. Your complete report takes a deeper look at the personality patterns, career themes, relationships and personal-year interpretations associated with them."; stacked miniature report cards (identical for everyone, pure shapes); price block (server constant); button "Unlock My Complete Numerology Report"; disclaimer. | NO (price read server-side at render) |
| 4v | CTA VARIANT (ineligible pair) | "Your complete report is not ready for your numbers yet." + honest explanation (no date promised) + waitlist invitation with the consent checkbox (UNCHECKED, wording supplied by owner/legal, separate from the marketing opt-in) + secondary "Notify me when it is ready". No price, no purchase button. | NO |
| 5 | WHAT YOU'LL UNLOCK | Four locked miniature cards: Personality, strengths and challenges; Career and working style; Relationships and bonds; Personal years and reflection prompts. Each has a lock, a one-line description and synthetic placeholder text under a light veil (never real paid text). Second button "Get My Full Numerology Report"; concise disclaimer. | NO: `render_page5()` takes no arguments |

Page 2 must never contain: pair-keyed prose (PS entries, 4d, 8h), planet friend/neutral/adversary labels or any 4e-4g text, "complement"-style readings, or any sentence selected by the (m, b) pair. The only pair-dependent content is the digits and planet names themselves and the conditional 4h fact.

Preview rules: no text below 9.5 px; no testimonials, guarantees, counts, prices other than the token, discounts or countdowns; every locked/synthetic module (cards 3, 4, 4v, 5) is produced by a function of NO arguments and is byte-identical for every user (test over all 81 pairs, different names and different dates). Disclaimer: "Numerology is a belief system, not a science. Readings follow contemporary writing, for reflection only." on cards 1-4; the longer "Numerology is a belief system, not a science. These readings follow contemporary numerology writing and are offered for reflection, not prediction." on card 5 and 4v. No sentence says "traditional".

Wording claims on cards 4-5 must be checkable against the paid report (section 8). In particular "relationships" and "Relationships and bonds" rest on paid card 10, which is HELD pending expert review (compatibility list and the unreviewed bond points); card 14 is reflection prompts (EXPLORE / CONTINUE / RECONSIDER), not "practical guidance", so card 5 says "reflection prompts". If card 10 is not approved, the Relationships tile and the word "relationships" in the card-4 copy must be removed before launch.

### Free vs locked

```
- **Free part:** ... one or two personalised lines about the pair.
- **Locked / blurred:** rest of Core Numbers (how the pair works together), Personality, ...
- **Must NOT be given away free:** any personal-year number or forecast, and any lucky number, colour, day or gemstone.
+ FREE (computed facts + approved static wording): name, DOB, Mulank, Bhagyank, ruling planets, workings, the how/direction explanation, the nine-number planet table, one generic reflection question.
+ LOCKED (not computed, not sent, not in the DOM or PDF text): every paid-report interpretation: pair statements, planetary-link statements, personality, dials, strengths/growth areas, career, relationships, personal-year numbers and workings, prompts, and the lucky numbers/colours/days/gemstones.
+ Never blurred real text: locked areas contain synthetic placeholders only (the structural guarantee: functions with no arguments; the teaser JSON is built from an allow-list of free fields).
```

## 6. Eligibility (new section; server-side, authoritative)

Rule: a pair is ELIGIBLE for sale only if EVERY content key the paid report would render for that DOB is `verified` with a NAMED reviewer and a review date. `sample_ok`, `needs_review` and `pending` never count; no environment flag can promote them in production. Required keys for a given (m, b, today): M[m], B[b], PS[m-b] (ordered key, never the reversed key), the personality/dials/strengths pair bank for cards 5-7, the career banks used by cards 8-9, the planet-relation cells REL[m.planet][b.planet] and the reverse (or the rule-built fallback that requires none), the compatibility list for card 10 (or its stated fallback), the lucky-reference lookups for card 13, and Y[n1], Y[n2] for the current and next personal year (re-checked every 1 January). Today ZERO pairs satisfy this (no reviewer has signed anything; only M2, B1, PS 2-1, Y1/Y2 and the Moon-Sun cell are `sample_ok`), so every pair is ineligible in production. The build still ships complete; tests use a test-only eligible fixture.

- Registry: `mulank_content.py` (or JSON) keyed M1-M9, B1-B9, Y1-Y9, `P:m-b` (81 ordered), `R:Planet>Planet`, and the card-13 / card-10 lookups, each with `status`, `reviewed_by`, `reviewed_on`, `source_ids`, `content_version`. `pair_readiness(m, b, today)` returns `{eligible, reason_code, content_version}` (missing keys are logged, not sent to the client). Guard tests: no `verified` entry with an empty reviewer; the sample flag cannot be set when `RAZORPAY_KEY_ID` starts with `rzp_live_`.
- Reviewer: NOT YET NAMED (open decision 1). "Verified" must be defined by the owner (which sources, how many).
- Consulted only on the server: `POST /api/mulank` (builds the eligible or availability variant), `POST /api/order` (authoritative: 409 `not_available` before any Razorpay order is created; the hidden button is not the gate), the preview renderer (price and purchase CTAs only when eligible), and the paid render path (renders only verified text).
- Capture is never blocked after payment; if readiness flipped between order and capture, log, flag for manual refund/review, and record `content_version` in `report_data.meta`.
- Fallback availability message (card 4v): see section 5. Honest, no date promised, no price, no purchase button.
- Waitlist: `POST /api/mulank/waitlist`; explicit unchecked consent checkbox; stores `consent_ts`, `consent_version`, `pair_key` (option a: `report.meta.waitlist`, no DDL); rate-limited; no PII in logs; marketing opt-in remains a separate field.
- Internal gap log: one structured log line per ineligible request WITHOUT PII (`[mulank] ineligible pair=2-5 missing=P:2-5,R:Moon>Mercury`) plus a per-pair counter (daily summary). Never log name, phone or rid-with-name.

## 7. Paid report structure (reference; replaces the card table, spec lines 86-104 where they differ)

The paid report stays 15 cards and uses the approved Stage B wording exactly (`mulank-research/stage-b/final/STAGE-B-FINAL-WORDING.md`, QA in `mulank-paid-v4/QA-NOTES-v4.md`). The spec rows change as follows:

```
  | 3 | Core Numbers | numbers + workings + method box, + 3b role split, 3c "Yours: ..." |
- | 4 | Core Numbers | ruling planets and the pair reading, numerological-basis box |
+ | 4 | Core Numbers | role split (4c), per-number lines (4a, 4b), one-source pair statement 4d, "Planetary links" statement 4e-4i (a statement about the Jyotish table, never a reading) |
  | 5 | Personality | pair bank |
  | 6 | Personality | dials (pair bank) |
- | 7 | Strengths & Challenges | table |
- | 8 | Strengths & Challenges | balance bars |
+ | 7 | Strengths & Challenges | MERGED table + bars (old 7+8) |
- | 9 | Career & Relationships | Work |
+ | 8 | Career | working style, strengths at work, wants, pair work statement 8h |
+ | 9 | Career | patterns to notice, reflection questions, at most 3 fields linked with the Mulank |
- | 10 | Relationships | ... compatibility table |
+ | 10 | Relationships and bonds | HELD (pending expert review): bond points and the compatibility list are unchanged and NOT approved |
  | 11 | Personal years | two tiles + table; "Often linked with"; 11b match line (calculated) |
  | 12 | Cycle exhibit | unchanged |
  | 13 | Quick reference | HELD (lucky numbers pending expert review); fallback line when the lookup is undefined |
- | 14 | Practical guidance | Start / Continue / Ease off |
+ | 14 | Reflection prompts | EXPLORE / CONTINUE / RECONSIDER, one prompt per year |
```

Also: 11 and 22 are always reduced; personal year is computed dynamically from `today`; vocabulary rules (CLAUDE.md section 5b) and persona-leakage test (section 22) unchanged. Known gaps carried over from QA-NOTES-v4 that affect "eligible": cards 5-7 have no defined fallback for pairs without authored pair content (the report drops to 12 cards), so those banks are part of the eligibility rule above; the attribution gate (gate 12) fails on 7 approved strings; word "unlock" is in the owner's CTA but is a CLAUDE.md section 5 stock word (reviews context).

## 8. Security requirements (new section)

1. **Price server-side only.** One constant; `/api/order` ignores any client amount; the preview renders the price from the same constant; the PDF cache key includes the price and content version.
2. **Verification (Mulank's own endpoints):** accept payment only if (a) the Razorpay signature verifies (HMAC over `order_id|payment_id`, constant-time compare), (b) the fetched payment/order amount equals the server price in paise, (c) currency is INR, (d) status is `captured` (not `authorized`/`failed`), (e) the order id is bound to this report id. Mismatch -> reject, alert (no PII), do not mark paid.
3. **Webhook:** verify the signature over the RAW request body before parsing; idempotent on payment id (replays are no-ops); bind order to report; return 2xx only after durable write; tampered signature -> 400.
4. **Bearer-link hardening:** the report/preview id is an unguessable token; routes send `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, `X-Robots-Tag: noindex`; no analytics recorders or ad pixels on report pages; `/api/report/{id}` returns the free allow-listed teaser when unpaid and never `account`/PII; no OTP gate in v1 (open decision 12).
5. **No PII in URLs or logs** (no name, phone, DOB in query strings, paths or log lines; rid never logged next to a name). Filenames never contain the raw name; the name is HTML-escaped everywhere it renders.
6. Paid content is never computed, included or sent for unpaid requests; hiding in markup/PDF is not protection. Preview PDF cache key is prefixed and a test proves a paid fetch can never return the preview file.
7. Rate limits on `/api/mulank`, `/api/mulank/waitlist`, `/api/order`; consent timestamps and policy versions stored; refund/cancellation page and privacy/terms updates before charging.
8. Shared payment fixes (all products) are a separate PR; Mulank guards its own path first.

## 9. Gates (extends spec lines 140-145)

- Mock: 5 `<section class="page` cards (+ 1 variant page), Chrome print 323 x 623 pt, last element not clipped, min font 9.5 px, leak scan on HTML and PDF (secrets = lucky values, pair prose, planet-relation labels, personal-year numbers/workings, paid pages 5-14 text), provenance 3-gram check, 5b scan, stock-phrase scan, career-report leak scan, scanner self-test.
- Renderer later: determinism test (pages 3, 4, 5 and the variant byte-identical over 81 pairs and names), no-leak via PyMuPDF text, gender-identical-output test, name HTML-escape test, eligibility tests (all refuse today; fixture passes), unpaid API has no paid keys.

## 10. Open decisions for the owner

1. Named reviewer(s) and the definition of "verified" (blocker for charging).
2. Which pairs open first; whether to launch the free preview + waitlist only until then.
3. Price (and whether any honest offer price exists).
4. Approve the page-2 reflection question wording (options in MOCK-NOTES.md).
5. Is page 2 (facts only) acceptable as a free page, or should it be dropped/merged (MOCK-NOTES critique)?
6. Product name and slug (`/en/numerology` proposed).
7. Marketing opt-in wording, what will be sent and by which provider; waitlist consent wording; refund policy and privacy/terms text.
8. Approve the card-4 supporting copy and the card-5 tile wording, in particular "relationships" while paid card 10 is HELD, and "Personal years and reflection prompts" instead of "practical guidance".
9. For ineligible pairs: omit page 5 (proposed) or show a CTA-free page 5?
10. International phone numbers in v1 (default: no).
11. Show a page count ("15 pages") on card 4? Not shown now because pairs without authored content get fewer cards.
12. Report access: bearer link with hardening (default) vs OTP.
13. Remove Clarity/ad pixels from report pages for this product (default yes).
14. Shared payment-hardening scope: Mulank-only first (default) vs all products.
15. Waitlist storage: report-meta flag now (default) vs a new table (needs manual RDS DDL).

## 11. Out of scope for this amendment

Hindi version, homepage card, testimonials/reviews, international phone, OTP gate, price decision, reviewer sign-off and content verification itself, the paid-report renderer, payment code and shared payment fixes, deployment and Razorpay/Twilio configuration, SEO/sitemap entries (until sellable), any change to other products or to CLAUDE.md beyond the funnel-deviation note proposed in section 4.
