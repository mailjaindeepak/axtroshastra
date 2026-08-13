# Ops System Architecture

## The Three Testing Layers

| Layer | What | Runs against | When | Question it answers |
|-------|------|-------------|------|-------------------|
| **Pytest** (458 tests) | Python backend logic | Local SQLite, DEMO_MODE | Before deploy (CI) | "Is the code correct?" |
| **E2E Playwright** (21 tests) | Browser experience | Local server, DEMO_MODE | Before deploy (CI) | "Does the website work?" |
| **Robot Customer** | Live site availability | Production (real data) | 3x/day + after deploy | "Is the live site healthy NOW?" |

```
════════════════════════════════════════════════════════════════
                    THE COMPLETE OPS SYSTEM
════════════════════════════════════════════════════════════════

UNIT 1: Monitor Bot (ops-monitor.yml — one workflow, one button)
  Schedule: 3x/day (06:00, 14:00, 22:00 IST)
  Cost: ~$0/day (no LLM generation, no paid actions)
  Database impact: Zero (cleans up after itself)

  PHASE A — Health checks (fast, cheap, 5 seconds total)
  ┌──────────────────────────────────────────────────────────┐
  │ Check 1: DB write-durability     /healthz/db             │
  │ Check 2: PDF renderer            /api/pdf_health          │
  │ Check 3: OTP provider            /api/otp/health          │
  │ Check 4: LLM reachability        /api/admin/llm_health    │
  │ Check 5: Razorpay creds          /api/admin/razorpay_health│
  │ Check 6: Wallet balances         (low-balance warnings)   │
  └──────────────────────────────────────────────────────────┘
  If ANY check fails → skip Phase B (site is broken, no point
  running the robot) → go straight to Phase C.

  PHASE B — Robot customer (browser-based, ~3 minutes)
  ┌──────────────────────────────────────────────────────────┐
  │                                                          │
  │  B1. Page health — ALL pages (hardcoded list in spec)     │
  │      For every page on the site:                         │
  │      ✓ Returns HTTP 200                                  │
  │      ✓ No JavaScript errors                              │
  │      ✓ No horizontal overflow (responsive)               │
  │      ✓ Loads in < 5 seconds                              │
  │      Page list is in robot.spec.js ALL_PAGES — update it │
  │      when you add a new page.                            │
  │                                                          │
  │  B2. Funnel smoke — each product (manual list)           │
  │      For each funnel (marriage-v1, marriage-v2, compat,  │
  │      career, and future v3/parents):                     │
  │      ✓ Form loads and submit button is visible+enabled   │
  │      ✓ Fill form with fake data, submit                  │
  │      ✓ Teaser/preview renders                            │
  │      ✓ window.REPORT_ID is set (backend processed it)    │
  │      ✗ NO free-pass unlock (no /api/order call)          │
  │      ✗ NO LLM generation (no narrative created)          │
  │      ✗ NO PDF generation                                 │
  │      This list is manual — when you add a new funnel,    │
  │      add it to the FUNNELS array with a fill function.   │
  │                                                          │
  │  B3. SEO checks — all pages (same hardcoded list)         │
  │      For every page:                                     │
  │      ✓ Has a <title> tag                                 │
  │      ✓ Has a <meta name="description">                   │
  │      ✓ Has an <h1>                                       │
  │      ✓ Has canonical URL                                 │
  │      ✓ Images have alt text                              │
  │      Uses the same ALL_PAGES list as B1.                 │
  │                                                          │
  │  B4. Cleanup (after all tests)                           │
  │      Calls /api/admin/robot_cleanup                      │
  │      Deletes all reports + users created by the robot    │
  │      during this run. Database stays clean.              │
  │                                                          │
  └──────────────────────────────────────────────────────────┘

  PHASE C — Report results
  ┌──────────────────────────────────────────────────────────┐
  │ If everything passed:                                    │
  │   → POST result to dashboard (/api/admin/ops_event)      │
  │   → Record to local history (ops_history.jsonl)          │
  │                                                          │
  │ If anything failed:                                      │
  │   → Alert via email + WhatsApp                           │
  │   → POST failure to dashboard                            │
  │   → Check: was the PREVIOUS run also a failure?          │
  │     → YES (2 consecutive): call Mechanic (Unit 2)        │
  │     → NO (first failure): alert only, wait for next run  │
  └──────────────────────────────────────────────────────────┘


════════════════════════════════════════════════════════════════

UNIT 2: Mechanic (toolbox — called by Unit 1 or Unit 3)
  NOT scheduled. Has no eyes. Just tools that other code calls.

  Tool 1: Remediate (light touch, HTTP nudge)
  ┌──────────────────────────────────────────────────────────┐
  │ Problem: Paid reports stuck in delivery queue            │
  │ Fix: POST /api/reconcile — tells app to retry delivery   │
  │ Blast radius: Low — just retries, doesn't change code    │
  │ Always safe to run.                                      │
  └──────────────────────────────────────────────────────────┘

  Tool 2: Rollback (big hammer, AWS CLI)
  ┌──────────────────────────────────────────────────────────┐
  │ Problem: Bad deploy broke the site                       │
  │ Fix: aws elasticbeanstalk update-environment             │
  │      --version-label <last-good-version>                 │
  │ Blast radius: HIGH — replaces the running code           │
  │                                                          │
  │ Safety switch: OPS_ROLLBACK_ARMED                        │
  │   OFF (default): alert only, don't touch server          │
  │   ON (you set it): actually rollback                     │
  │                                                          │
  │ Exception: when called by CI Deploy Guard (Unit 3),      │
  │ rollback is ALWAYS armed because the previous version    │
  │ was captured 5 minutes ago — guaranteed safe.            │
  └──────────────────────────────────────────────────────────┘

  Both tools: ALWAYS alert (email+WhatsApp) with what they did.
  Both tools: NEVER raise exceptions — return True/False.


════════════════════════════════════════════════════════════════

UNIT 3: CI + Deploy Guard (ci.yml — one workflow, one button)
  Trigger: "Run workflow" from Actions tab on aws-mysql branch
  Also runs: pytest + E2E on every push/PR (but NO deploy)

  ┌──────────────────────────────────────────────────────────┐
  │ STAGE 1 — CI (pre-deploy verification)                   │
  │                                                          │
  │   Job A: Run pytest (458 tests) ──┐                      │
  │          local SQLite, DEMO_MODE  │                      │
  │                                   ├─ both must pass      │
  │   Job B: Run E2E (21 tests) ─────┘                      │
  │          local uvicorn, DEMO_MODE                        │
  │                                                          │
  │   If ANY test fails → STOP. Deploy job never starts.     │
  │                                                          │
  ├──────────────────────────────────────────────────────────┤
  │ STAGE 2 — Guarded Deploy (deploy job, workflow_dispatch) │
  │                                                          │
  │   Step 1: Snapshot current live version                   │
  │           "What's running now?" → rollback target         │
  │                                                          │
  │   Step 2: Deploy to AWS (eb deploy, versioned label)     │
  │                                                          │
  │   Step 3: Wait for Green (up to 10 min)                  │
  │           Poll AWS health every 15 seconds                │
  │                                                          │
  │   Step 4: Robot smoke test on live site (Playwright)     │
  │           Page health + funnel smoke, no LLM              │
  │                                                          │
  │   If Steps 3-4 pass:                                     │
  │     → Record success to dashboard + ops history          │
  │     → Alert: "Deploy OK, smoke test passed"              │
  │                                                          │
  │   If ANY of Steps 3-4 fail:                              │
  │     → Rollback to Step 1 snapshot (ALWAYS armed)         │
  │     → Record failure + rollback to dashboard             │
  │     → Alert: "Deploy FAILED, rolled back to <version>"   │
  │                                                          │
  └──────────────────────────────────────────────────────────┘


════════════════════════════════════════════════════════════════
                    WHAT RUNS WHEN
════════════════════════════════════════════════════════════════

  Every 5 min:   UptimeRobot (free, external)
                 → "Is the homepage responding?"

  3x/day:        Unit 1 — Monitor Bot (ops-monitor.yml)
                 → "Is everything healthy + working?"

  On deploy:     Unit 3 — CI + Deploy Guard (ci.yml)
                 → "Tests pass? Deploy. Still works? Keep. Broken? Rollback."

  On failure:    Unit 2 — Mechanic (ops/mechanic.py)
                 → Called by Unit 1 or 3 to fix things.


════════════════════════════════════════════════════════════════
                    COST SUMMARY
════════════════════════════════════════════════════════════════

  Old system:  ~$14/month  (robot generates 9 LLM reports/day)
  New system:  ~$0.01/month (one tiny LLM ping 3x/day)

  Old system:  ~270 fake reports/month in the database
  New system:  Zero (cleanup endpoint deletes robot data)

  Old system:  3 pages tested (hardcoded)
  New system:  ALL pages tested (hardcoded list in robot.spec.js)


════════════════════════════════════════════════════════════════
                    MANUAL vs AUTOMATIC
════════════════════════════════════════════════════════════════

  AUTOMATIC (zero work when you add/change):
  ✓ Health endpoints (DB, PDF, OTP, LLM, Razorpay)
  ✓ Cleanup of robot data
  ✓ Wallet low-balance warnings

  MANUAL (update needed when you change these):
  ✗ Page list — add new pages to ALL_PAGES in robot.spec.js
  ✗ SEO checks — tested on the same hardcoded page list
  ✗ Funnel form-fill tests — add a new fill function when you
    add a new product (marriage-v3, parents, etc.)
  ✗ Form field selectors — if you rename #f-name to #f-fullname,
    update the fill function
  ✗ CTA assertions — if you change the unlock button ID
  ✗ E2E tests — when you add new UI behavior to test

  The manual parts are unavoidable. If your form has a field
  called #f-name and the robot types into #f-name, there's no
  way for the robot to "discover" that you renamed it to
  #f-fullname. The test failure IS the discovery mechanism —
  it tells you "this changed, update the test."
```

## Workflow Files (after merge)

| File | Purpose | Status |
|------|---------|--------|
| `.github/workflows/ci.yml` | Unit 3: CI + Deploy Guard (one button) | **Active** |
| `.github/workflows/ops-monitor.yml` | Unit 1: Watcher + Robot (one button) | **Active** |
| `.github/workflows/eb-rollback.yml` | Manual rollback to any saved version | **Active** |
| `.github/workflows/ops-deploy-guard.yml` | Emergency deploy-only (skips tests) | Superseded by ci.yml |

## Python Modules

| File | Runs on | Purpose |
|------|---------|---------|
| `ops/config.py` | GitHub | All settings from env vars |
| `ops/alerts.py` | GitHub | Email (SMTP) + WhatsApp (Twilio) |
| `ops/watcher.py` | GitHub | Health checks over HTTP |
| `ops/mechanic.py` | GitHub | Remediate or rollback |
| `ops/history.py` | GitHub | Append-only event log |
| `ops/robot_customer/` | GitHub | Playwright browser tests against live site |
| `api.py` (health endpoints) | Server | `/healthz/*`, `/api/*_health` |

## Design Rules

1. **Never raises** — every function catches its own errors and returns a value
2. **Always alerts** — every action (success or failure) notifies humans
3. **No new dependencies** — stdlib only (urllib, smtplib, subprocess) + optional twilio
