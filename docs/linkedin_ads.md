# LinkedIn Ads — Funnel Conversion Tracking

Tracks the paid-ads funnel end to end:

```
Click  ->  Landing  ->  Form Filled  ->  Checkout Initiated  ->  Purchase
```

Every conversion is **inert until its id is configured**, so this code is safe to
ship before any of the setup below is done. This document is that setup checklist.

> **Deploying is a separate, manual step.** Merging to `aws-mysql` does not ship
> anything — the deploy job in `ci.yml` is `workflow_dispatch` only. Triggering
> it deploys whatever `aws-mysql` currently points at, so an open PR is NOT
> picked up. Confirm what is actually live with:
>
> ```bash
> curl -s https://www.axtroshastra.com/en/marriage-v3 | grep -c snap.licdn.com
> ```
>
> `1` = the tag is serving; `0` = this code is not live yet, whatever the CI
> checkmarks say.

---

## 1. How it is wired

### Browser — the Insight Tag

Injected server-side into every served page by `_inject_linkedin()` in `api.py`,
immediately after the Meta Pixel block. No `pages/*.html` file was edited.

The four funnel points are **not** hand-coded per page. Every landing page
already fires the Meta Pixel at exactly those points, so `_linkedin_head()`
wraps `window.fbq` once and re-emits the matching LinkedIn conversion:

| Funnel step        | Meta event the page already fires | LinkedIn conversion env var |
| ------------------ | --------------------------------- | --------------------------- |
| Landing            | (page load)                       | `LINKEDIN_CONV_LANDING`     |
| Form Filled        | `Lead`                            | `LINKEDIN_CONV_LEAD`        |
| Checkout Initiated | `InitiateCheckout`                | `LINKEDIN_CONV_CHECKOUT`    |
| Purchase           | `Purchase`                        | `LINKEDIN_CONV_PURCHASE`    |

> **Trade-off to know about.** LinkedIn conversions ride on the Meta Pixel
> calls. Remove the Pixel from a page and that page silently stops reporting to
> LinkedIn too. If Meta is ever dropped site-wide, replace the bridge with
> explicit `lintrk()` calls at the same four points — the map above is the spec.

### Server — the Conversions API

`tracking._linkedin_purchase()` re-fires **Purchase** from the Razorpay webhook,
exactly like the existing Meta CAPI backstop. This is what keeps revenue
reporting honest when the browser fire is lost to an ad-blocker or a buyer who
closes the tab the moment payment succeeds.

### Deduplication

LinkedIn requires **one conversion rule per data source**. That is why Purchase
needs *two* rules — the browser fire and the server fire are counted separately,
then reconciled:

- browser sends `lintrk('track', {conversion_id: <tag rule>, event_id: <report id>})`
- server sends `{"conversion": "urn:lla:llaPartnerConversion:<capi rule>", "eventId": "<report id>"}`
- same `eventId` seen twice -> LinkedIn **keeps the Insight Tag copy** and
  discards the CAPI one.

In reporting you will see both rules. The Insight Tag one having the higher
count is the sign dedup is working correctly.

---

## 2. Create the conversion rules

Campaign Manager -> **Analyze -> Conversion tracking -> Create conversion**.

Create **five** rules. The first four are the Insight Tag funnel; the fifth is
the server-side Purchase.

| # | Name (suggested)      | Conversion type | Source          |
| - | --------------------- | --------------- | --------------- |
| 1 | Landing view          | `OTHER`         | Insight Tag     |
| 2 | Form filled           | `LEAD`          | Insight Tag     |
| 3 | Checkout initiated    | `ADD_TO_CART`   | Insight Tag     |
| 4 | Purchase              | `PURCHASE`      | Insight Tag     |
| 5 | Purchase (CAPI)       | `PURCHASE`      | Conversions API |

Rules 1–4 and rule 5 are created through **different flows**. This is the step
that is easiest to get wrong, and getting it wrong means the four browser
conversions never receive anything:

- **Rules 1–4** — *Create conversion* → the website / **Insight Tag** option.
  When asked how the conversion is triggered, pick **event-specific** rather
  than a URL rule: the code fires these directly via `lintrk()`.
- **Rule 5** — *Create Conversions API conversion* → at the **Sources** step
  choose **Direct API**. Not Zapier, not Google Tag Manager — the app posts to
  `/rest/conversionEvents` itself from `tracking.py`. (Zapier / HubSpot /
  Marketo / Salesforce are CRM relays; GTM needs a server-side container.)

Purchase deliberately has one rule in each flow. That is what deduplication
reconciles — see section 1.

**Associate every rule with your campaigns.** A conversion that is not attached
to a campaign is never attributed, and this is the single most common reason a
correctly-instrumented funnel still reports zero.

Each saved rule shows a numeric **conversion ID** — that is what goes in the env
vars below.

### Attribution windows

Set these on the rules, not in code. `PURCHASE` and `LEAD` support a 365-day
post-click window; `OTHER` and `ADD_TO_CART` are capped at 90.

---

## 3. Set the environment variables

On Elastic Beanstalk (same place as the Twilio and Meta keys):

```
LINKEDIN_CONV_LANDING=30342705
LINKEDIN_CONV_LEAD=30342713
LINKEDIN_CONV_CHECKOUT=30342721
LINKEDIN_CONV_PURCHASE=30342729

LINKEDIN_CONV_PURCHASE_CAPI=30342737
LINKEDIN_CAPI_TOKEN=<access token, see below>
```

Those are the live rules on ad account `559009160`, created 2026-08-25. The
conversion ids are **not secrets** — they are rendered into the page HTML and
visible in view-source. `LINKEDIN_CAPI_TOKEN` **is** a secret: it belongs in the
Elastic Beanstalk environment only, never in the repo.

To re-read the ids later (and prove the token works at the same time):

```bash
curl -s -X GET 'https://api.linkedin.com/rest/conversions?q=account&account=urn%3Ali%3AsponsoredAccount%3A559009160' \
  -H 'Authorization: Bearer $LINKEDIN_CAPI_TOKEN' \
  -H 'LinkedIn-Version: 202608' \
  -H 'X-Restli-Protocol-Version: 2.0.0'
```

401 means a bad/expired token; 403 means the token is missing the
`rw_conversions` / `r_ads` scopes. The CAPI rule is the element with
`"conversionMethod": "CONVERSIONS_API"`.

Optional overrides:

| Var                     | Default    | Notes                                        |
| ----------------------- | ---------- | -------------------------------------------- |
| `LINKEDIN_PARTNER_ID`   | `10777105` | Set to `""` to disable LinkedIn entirely.    |
| `LINKEDIN_API_VERSION`  | `202608`   | `YYYYMM`. Bump when a sunset warning appears. |

Every id is independently dormant. Set only `LINKEDIN_CONV_LEAD` and only Form
Filled reports; the rest stay silent. The base Insight Tag loads regardless, so
retargeting audiences and click data start building the moment this deploys.

### The access token

Only the CAPI Purchase needs this. The four Insight Tag conversions work with no
token at all, so **do not let this block the deploy** — ship the four ids and add
the token whenever it is convenient.

**Use the advertiser path, in Campaign Manager. Do NOT create a developer app.**
LinkedIn lets advertisers sending their own conversion data generate a token
straight from the ad account: no developer application, no Advertising API
product request, no business-entity review — and **the token does not expire**.

1. Campaign Manager -> left menu **Data -> Signals Manager**.
2. Click **Direct API**, then **Generate access token**.
3. Sign in and follow the prompts.
4. **Copy the token immediately.** Campaign Manager does not store it; closing
   the dialog without copying means generating a fresh one.
5. Verify it with the `GET /rest/conversions` call above before relying on it.
   401 = bad token, 403 = missing ad-account role.

The member generating it needs one of `ACCOUNT_BILLING_ADMIN`,
`ACCOUNT_MANAGER`, `CAMPAIGN_MANAGER` or `CREATIVE_MANAGER` on ad account
`559009160`.

> **Do not follow the developer-portal / OAuth token-generator route.** It
> exists for *partner platforms* integrating on behalf of many advertisers. It
> requires an approved app, Company Page verification, a verified business email
> and legal-entity vetting — and its tokens expire every 60 days with no
> programmatic refresh outside partner programs. None of that applies to a
> first-party advertiser sending its own sales. If someone later "fixes" this
> section back to the OAuth flow, they have signed the site up for a manual
> token rotation every two months for no benefit.

Whatever the source, `LINKEDIN_CAPI_TOKEN` is a secret: Elastic Beanstalk
environment only, never the repo.

> If the CAPI numbers ever go flat, grep the app log for
> `[li-capi] purchase ... 401`. Expiry/revocation is a SILENT, PARTIAL failure
> by design — the browser Purchase keeps firing, so revenue still reports, just
> without the ad-blocker/closed-tab backstop.

---

## 4. Enable click IDs — do not skip this

Campaign Manager -> ad account -> **Insight Tag -> enable enhanced conversion
tracking** (first-party cookies).

LinkedIn then appends `li_fat_id` to landing-page URLs. The Insight Tag block
parks it in an `ax_li_fat` cookie, `/api/order` reads it server-side, and the
webhook forwards it as `LINKEDIN_FIRST_PARTY_ADS_TRACKING_UUID`.

This matters more here than on most sites: **LinkedIn's Conversions API has no
hashed-phone identifier.** Meta matches buyers on phone; LinkedIn cannot. Most
buyers on this site pay with a phone number and never give an email, so without
the click ID a large share of real sales have nothing to match on and are
dropped before they are ever sent (logged as `no LinkedIn-usable identifier`).

Identifiers actually sent, when available: `SHA256_EMAIL`,
`LINKEDIN_FIRST_PARTY_ADS_TRACKING_UUID`, `PLAINTEXT_IP_ADDRESS`.

---

## 5. Verify

**Browser** — load any landing page and check:

- Network tab shows a request to `snap.licdn.com/li.lms-analytics/insight.min.js`.
- Console: `window.lintrk.q` lists the landing conversion.
- The LinkedIn Insight Tag browser extension reports the tag as active.

**Funnel** — walk one report through form -> checkout -> payment and confirm
three more entries appear in `window.lintrk.q`, each with the expected
`conversion_id`, and `event_id` equal to the report id on Lead and Purchase.

**Server** — after a real payment, look for the absence of `[li-capi]` errors in
the app log. A rejected event logs the LinkedIn validation message verbatim.

**Reporting lag** — up to 24h for ingestion and a further 48h for reporting.
Do not judge a fresh setup for three days.

---

## 6. Regression coverage

`tests/test_linkedin.py` — 20 tests covering injection order (LinkedIn must land
after Meta), idempotency, per-id dormancy, the CAPI request schema, the
never-send-a-phone rule, and the `li_fat_id` cookie round-trip through
`/api/order` to the webhook.
