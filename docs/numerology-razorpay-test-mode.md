# Numerology: real Razorpay Test Mode on localhost, and what production needs

The Numerology page opens the genuine Razorpay Standard Checkout (`https://checkout.razorpay.com/v1/checkout.js`, the same script tag every other report page uses).
The order is created on our server with Razorpay's API, the amount (₹299, 29900 paise, INR) is set by the server, and the browser only ever receives the **public** key id.
There is no demo or simulated gateway in the repository. (Earlier local screenshots used a throwaway stand-in outside the repo; it has been stopped and is not part of the code.)

## What the owner must provide (cannot be done from this machine: no Razorpay account access or credentials here)
1. A Razorpay account in **Test Mode**: Dashboard, Account and Settings, API Keys, Generate Test Key. This gives `rzp_test_…` (key id) and a secret.
2. A **webhook secret** you choose (any long random string).
3. For the webhook to reach a laptop: a public tunnel URL (for example ngrok or Cloudflare Tunnel) pointing at `http://127.0.0.1:8000`.
   Razorpay Dashboard, Webhooks, Add: URL `https://<tunnel-host>/api/mulank/webhook`, secret = the webhook secret above, event **payment.captured** (add `payment.failed` if you want it logged).
4. A local MySQL (the project's docker MySQL on port 3307 works) with the schema loaded, as for the test suite.

## Run it (nothing here is committed or sent anywhere)
Put these in a local `.env` (git-ignored) or in your shell. Never paste them into chat:
```
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
PUBLIC_BASE_URL=https://<tunnel-host>
DB_HOST=127.0.0.1  DB_PORT=3307  DB_USER=root  DB_PASSWORD=root  DB_NAME=axtroshastra_v2
```
1. `python tools/check_razorpay.py` : preflight. Creates one real Test Mode order for ₹299 and reads it back; checks keys, webhook secret and our signature checks. Must print `RESULT: PASS`. It never prints a secret and refuses to create anything with live keys.
2. `python tools/local_test_mode.py` : starts the real app on `http://127.0.0.1:8000`. It refuses non-test keys. Because no content is owner-approved yet, it treats content as approved **in memory for this process only** so the unlock button appears; nothing is written to the repository.
3. Open `http://127.0.0.1:8000/en/numerology`, submit the form, open the preview, click **Unlock My Full Numerology Report**. The real Razorpay popup opens showing ₹299.

Razorpay's documented test payments: card `4111 1111 1111 1111` with any future expiry, any CVV and OTP; UPI id `success@razorpay` (success) or `failure@razorpay` (failure). Use the netbanking/wallet test options in the popup for those methods.

## PASS / FAIL checklist for the Test Mode run
| # | Check | How |
|---|---|---|
| 1 | Real popup opens, shows ₹299 and the available methods | click Unlock |
| 2 | Successful test payment unlocks the 15-page report at once, with the Download button | pay with the test card |
| 3 | Failed payment (`failure@razorpay`) leaves it locked with a clear message, retry works | pay with the failing UPI id |
| 4 | Closing the popup leaves it locked, no charge, retry works | dismiss the popup |
| 5 | Server verification: a signature, order id, ₹299 and currency are checked and the payment is `captured` | covered by tests; confirm one row in `payments` for the report |
| 6 | Webhook: Razorpay Dashboard shows `payment.captured` delivered with a 200 to `/api/mulank/webhook` | Dashboard, Webhooks, recent deliveries |
| 7 | Download again after a reload, no second charge | reload, View report, Download; one captured payment only |
| 8 | Mobile: repeat at phone width (browser device mode, or the tunnel URL on a phone) | |

## Required for production (owner)
- Owner approves the content (`tools/approve_mulank_content.py`, reviewed PR). Until then **no customer can be offered checkout**.
- `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` (live) and `RAZORPAY_WEBHOOK_SECRET` set as Elastic Beanstalk environment variables, plus `PUBLIC_BASE_URL=https://www.axtroshastra.com`.
- Live webhook added in the Razorpay Dashboard: `https://www.axtroshastra.com/api/mulank/webhook`, event `payment.captured`, same secret.
- Run `python tools/check_razorpay.py` with test keys first; then a Test Mode purchase on the deployed site before switching to live keys.
- Optional WhatsApp delivery needs `TWILIO_*` and the approved text template.
- Deploy only through the guarded workflow, after the owner approves.
