# Numerology: verify the Razorpay configuration in AWS (owner checklist, no secrets exposed)

For the person with AWS and Razorpay Dashboard access. The app reads its Razorpay settings from the **Elastic Beanstalk environment** (`AxtroShastraProd`, region `ap-south-1`), not from GitHub Secrets. No workflow in this repository references a `RAZORPAY_*` secret. Numerology reuses the same three variables as the other paid reports; no new names are needed.

**Rules while doing this:** never paste a key or secret into chat, email, a ticket, a screenshot or git. Check that a value is *set* and what *kind* it is; do not read it out. Never use live keys for localhost testing.

## 1. Confirm the three variables exist (names only)
AWS Console: Elastic Beanstalk, `AxtroShastraProd`, Configuration, Updates / Monitoring / Software, Environment properties. Or, with the EB CLI, `eb printenv` (it prints values, so run it where nobody can see the screen, and do not copy the output anywhere).

| Variable | Expected | Check |
|---|---|---|
| `RAZORPAY_KEY_ID` | starts with `rzp_live_` for production | [ ] present, [ ] live (not `rzp_test_`) |
| `RAZORPAY_KEY_SECRET` | the secret that pairs with that key id | [ ] present |
| `RAZORPAY_WEBHOOK_SECRET` | the same string entered on the Razorpay webhook | [ ] present |
| `PUBLIC_BASE_URL` | `https://www.axtroshastra.com` | [ ] present |
| `DEMO_MODE` | **must be unset** (it enables a fake payment route) | [ ] unset |

If any are missing, set them on the environment (`eb setenv NAME=value`, run privately) and let the environment restart. GitHub Secrets alone do not reach the running app.

## 2. Confirm the key pair is real and matching
Razorpay Dashboard, switch to **Live Mode**, Account and Settings, API Keys. Check that the key id shown there is the one configured in step 1 (compare the first and last few characters only). If the secret was ever pasted somewhere public, regenerate the key pair and update Elastic Beanstalk.

## 3. Webhook
Razorpay Dashboard (Live Mode), Webhooks. Confirm a webhook exists for `https://www.axtroshastra.com/api/mulank/webhook` with event `payment.captured` and the same secret as `RAZORPAY_WEBHOOK_SECRET`. Add it if missing. The existing shared webhook for the other reports stays as it is; Numerology orders are handled by the new route, and anything that is not a Numerology order is passed on to the shared handler.

## 4. After the deploy (with the owner's go-ahead)
- [ ] `/en/numerology` shows the new preview and the Unlock button for an approved combination only.
- [ ] The Razorpay popup opens and shows 299 INR.
- [ ] One small real purchase: the full 15-page report appears at once with a Download button; refresh and download again without a second charge.
- [ ] Razorpay Dashboard shows the payment as captured and the webhook delivery as 200.
- [ ] Refund that test payment from the Dashboard.
- [ ] `/api/pdf_health` is healthy on the server (fonts and Chrome).

## 5. Before any of the above
Test Mode first: set Test Mode keys on a local machine only, run `python tools/check_razorpay.py` (must print `RESULT: PASS`) and `python tools/local_test_mode.py`, and run the PASS/FAIL checklist in `docs/numerology-razorpay-test-mode.md`.
