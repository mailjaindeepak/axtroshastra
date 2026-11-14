# Mulank pre-order: operating guide (OFF until the owner approves)

A pre-order lets a customer pay Rs 299 now for a report that cannot be produced yet, with the delivery promise and refund terms shown before they pay. It is built and tested but **closed by default**. It never unlocks an incomplete report and never claims an instant download.

## What the owner must supply to open it (all three, as environment variables via `eb setenv`)
| Variable | Meaning | Example (owner to decide) |
|---|---|---|
| `MULANK_PREORDER=1` | the switch | `1` |
| `MULANK_DELIVERY_PROMISE` | the exact phrase that finishes "we will deliver it ...". 8-160 characters, no HTML, must not say "instant" | `within 21 days of your order` |
| `MULANK_REFUND_URL` | the owner-approved refund and cancellation page (site path or https URL) | `/refund` |

If any is missing or unsafe, pre-order stays closed (tested). The refund page itself (`pages/refund.html`) must exist and be approved before the URL is set; draft wording is in `docs/numerology-legal-drafts.md`.
Also needed: Razorpay keys and the dedicated webhook (`docs/numerology-launch-checklist.md`, Track 2).

## What a customer sees
- **Landing page:** "your free preview is ready now... you may be offered a pre-order for Rs 299, delivered <promise>".
- **Preview page 4 and the purchase bar** (only for combinations that cannot be sold yet): "Pre-order Your Complete Report", Rs 299, "<promise>", "This is a pre-order, not an instant download", a link to the refund policy, button "Pre-order My Report for Rs 299". No strike-through price and no "unlock". Combinations that CAN be sold still get the normal purchase page.
- **After paying:** "Pre-order received... This is not an instant download... delivered <promise>... keep this page address... you will not be charged again", with the refund link and a "Check if my report is ready" button. No PDF button until the report exists.
- **When the report is ready:** the same private link shows the 15-page report and the PDF download.

## What is recorded
- The payment, verified like any other Mulank payment (signature, order id, amount 29900, INR, captured, not refunded).
- A snapshot on the report of exactly what was promised: the promise text, the refund link and a version, with a timestamp (`report_data.meta.preorder`). Changing the wording later never rewrites what earlier customers were shown.
- The report date is frozen when the report is first fulfilled, so the web page and PDF never change afterwards (personal years do not roll over on 1 January).

## Fulfilling orders (ops)
Both endpoints need the existing admin key in the `X-Stats-Key` header and return no names, phone numbers, dates of birth or private links.
- `GET /api/mulank/admin/orders`: counts by state (`awaiting_content`, `ready`, `failed`), and for each order its pair, paid time and whether it can be fulfilled right now.
- `POST /api/mulank/admin/fulfil`: fulfils every paid order whose content is now approved and complete (generates and caches the PDF). Safe to repeat.
Customers are NOT notified automatically: no WhatsApp provider or email is configured and none is collected (only a WhatsApp number). **The owner must decide how customers are told** (approve a WhatsApp provider and template, or accept that customers return to their saved link). The pre-order page asks them to keep it.

## Honest limits and risks
- The promise must be achievable. Writing and approving the content for all combinations is estimated at 10-14 working days after the owner's decisions (`docs/numerology-content-gap-and-plan.md`); set the promise with margin.
- Refunds are done by the owner in the Razorpay dashboard; there is no refund screen in the app.
- Terms, refund policy and the promise should be checked by the owner or counsel (consumer-protection rules for pre-orders). Nothing here is legal advice.