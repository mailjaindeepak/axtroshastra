# Robot Customer

A self-contained Playwright harness that behaves like a **real customer** against
a **live** Axtroshastra deployment and **fails loudly** if any step of the paid
journey breaks. It runs on both a **desktop** and a **mobile** viewport.

It is intentionally separate from `tests/e2e/` (which runs against a local
`uvicorn` in `DEMO_MODE`). This one hits a real URL and walks the whole funnel
for real, using a **free unlock pass** instead of a real card.

## The journey (per funnel)

Run once each for **compatibility** (`/en/compatibility`) and **marriage**
(`/en/marriage`), on both viewports:

1. **Get a free unlock token** — `GET /api/make_pass?key=$STATS_KEY&n=1` →
   `{"passes":["<tok>"]}` (via Playwright's `request` context).
2. **Fill + submit the birth form** in a real browser using the same selectors
   the e2e specs use (`#f-*` on `#kundliForm` for marriage; two people
   `p1-*`/`p2-*` on `#milanForm` for compatibility), picking a city from the
   `#…-place-list` autosuggest. Confirms the free `#teaser` appears.
3. **Unlock without paying** — read `window.REPORT_ID`, then
   `POST /api/order` with `{report_id, pass_token, phone, email}`. Expects a
   `{"free":true}` (fresh) or `{"already_paid":true}` response — the site's
   free-pass redemption path (`api.py` `/api/order` `pass_token` branch).
4. **Load `/report/<rid>`** and assert the **paid** report renders (HTTP < 400,
   not the "payment pending" 404 stub).
5. **Assert the PDF** — `GET /report/<rid>.pdf` returns `200` with a PDF
   content-type.

Any failed step fails the test, so the process exits **non-zero**.

## Run it

```bash
cd ops/robot_customer
npm ci
npx playwright install --with-deps chromium
OPS_TARGET_URL=https://your-deployment.example STATS_KEY=<admin-key> npx playwright test
```

Run a single funnel / viewport:

```bash
OPS_TARGET_URL=... STATS_KEY=... npx playwright test -g compatibility --project=mobile
```

### Required environment

| Var              | Purpose                                                              |
| ---------------- | ------------------------------------------------------------------- |
| `OPS_TARGET_URL` | Base URL of the deployment under test (becomes Playwright baseURL). |
| `STATS_KEY`      | Admin key gating `/api/make_pass` (mints the free unlock token).    |

Missing either aborts the run immediately with a clear error.

## GitHub Action

```yaml
- name: Robot customer smoke
  working-directory: ops/robot_customer
  env:
    OPS_TARGET_URL: ${{ secrets.OPS_TARGET_URL }}
    STATS_KEY: ${{ secrets.STATS_KEY }}
  run: |
    npm ci
    npx playwright install --with-deps chromium
    npx playwright test
```

The step fails (non-zero exit) the moment any journey step breaks. The HTML
report is written to `playwright-report/` when `CI` is set.
