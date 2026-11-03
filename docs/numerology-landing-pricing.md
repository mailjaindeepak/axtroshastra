# Numerology landing page and purchase presentation (feature/mulank-landing-pricing)

## What changed
- **Landing page** (`/en/numerology`): primary button is now "Generate My Free Preview". When something can actually be bought, a "free preview vs complete report" section appears (free card, and a navy-and-gold complete-report card with a large Rs 299 and a list of what the report contains). The form is unchanged: Full Name, Date of Birth, Gender, WhatsApp number.
- **Preview**: the purchase card after page 3 reads "Your Numbers Are Just the Beginning", with the button "Unlock My Full Numerology Report - Rs 299". The same button is repeated on page 5 (locked sections), and a compact bar stays on screen. Payment is the existing Mulank Razorpay flow: no second payment system.

## Three states, chosen on the server (the page never promises what cannot be delivered)
| State | When | Landing page | Preview after page 3 |
|---|---|---|---|
| nothing purchasable | no content approved (today's live state) | no price; "not available yet" notice | availability message, no button |
| instant sale | at least one combination is approved and complete | free vs complete section, Rs 299, "separate purchase after your free preview" | purchase card and Razorpay for ready combinations; others see the availability message (or pre-order if enabled) |
| pre-order | owner sets `MULANK_PREORDER`, `MULANK_DELIVERY_PROMISE`, `MULANK_REFUND_URL` | same, worded as a pre-order with the promise and refund link | "Pre-order My Report for Rs 299", "not an instant download" |

## The Rs 499 regular price
The struck-through Rs 499 and "Save Rs 200" appear everywhere ONLY when the owner sets `MULANK_LIST_PRICE_CONFIRMED=1` (confirming Rs 499 is a genuine regular price). Until then only Rs 299 is shown. No countdowns, stock counters or other urgency (tested).

## Settings (all optional; all default off)
| Variable | Effect |
|---|---|
| `MULANK_LIST_PRICE_CONFIRMED=1` | show Rs 499 struck through and the Rs 200 saving |
| `MULANK_PREORDER=1` + `MULANK_DELIVERY_PROMISE` + `MULANK_REFUND_URL` | open pre-orders (see `docs/numerology-preorder.md`) |

## Razorpay
Unchanged and reused. Rs 299 = 29,900 paise, orders created on the server, signature, order id, amount, currency and captured status verified, duplicates never fulfil twice, access only when the report can be produced. No Razorpay credentials exist in the development environment, so real test-mode payments have NOT been run; the demonstrations use a clearly labelled stub. To run them: set `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` (test keys) as environment variables on the machine running the app, never in chat or git.