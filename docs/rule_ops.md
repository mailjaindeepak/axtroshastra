# Ops Rules — Developer Checklist for Merge & Deploy

Every developer (human or AI assistant) must follow these rules before
merging code to `aws-mysql` or triggering a deploy. These exist because
we burned multiple deploy cycles learning them the hard way.

---

## 1. Pre-Merge Checklist (run locally, every time)

### 1A. Import Audit

Every `import X` in production code (`api.py`, `dashboard/`, `engine.py`,
`products.py`, `ops/`) must resolve against `requirements.build.txt`.

- Dev-only packages (`pytest`, `httpx`, `pyyaml`, `python-dotenv`) must be
  inside `try/except ImportError` or behind a test/CLI-only code path.
- Run: `grep -rn "^import\|^from" api.py dashboard/ engine.py products.py ops/ | grep -v __pycache__`
  and cross-check each module against `requirements.build.txt`.
- **Lesson:** PR #69 shipped a bare `from dotenv import load_dotenv` that
  crashed both pytest and E2E in CI because `python-dotenv` is not in
  build requirements.

### 1B. Python Tests

```bash
python -m pytest -q
```

All 459+ tests must pass. Zero tolerance for skips or xfails that weren't
there before your change.

### 1C. Server Boot Check

```bash
DEMO_MODE=1 DB_PATH=/tmp/boot_check.db uvicorn api:app --host 127.0.0.1 --port 8099
```

Hit `/healthz` — must return `200`. This catches import crashes that pytest
misses (pytest uses `requirements-dev.txt`; production uses
`requirements.build.txt`).

### 1D. E2E Playwright

```bash
# With server running on :8000
E2E_BASE_URL=http://127.0.0.1:8000 npx playwright test
```

All 42 tests (21 mobile + 21 desktop) must pass. Run this for ANY change
to `pages/*.html`, `api.py` routes, or `dashboard/`.

### 1E. Targeted Auth & SEO Checks (if touching auth, admin, or pages)

- Admin endpoint with STATS_KEY returns 200:
  `curl -sf "http://127.0.0.1:8000/api/admin/robot_cleanup?key=$STATS_KEY"`
- Admin endpoint with wrong key returns 403.
- Every page under `pages/` has `<title>`, `<meta description>`, `<h1>`,
  and `<link rel="canonical">`.

### 1F. Environment Variable Pattern Check

Any `os.getenv("X", "default")` in production/ops code must use the `or`
pattern:

```python
# WRONG — returns "" when CI sets the var from a missing secret
EB_ENV = os.getenv("OPS_EB_ENV", "AxtroShastraProd")

# RIGHT — empty strings fall back to the default
EB_ENV = os.getenv("OPS_EB_ENV", "") or "AxtroShastraProd"
```

GitHub Actions sets `VAR: ${{ secrets.MISSING }}` to `""` (not unset).
Python's `getenv` returns `""` because the var exists, so the default
never activates. The `or` pattern handles both missing and empty.

**Lesson:** `OPS_EB_ENV` was empty in CI, causing the deploy guard to send
an empty environment name to AWS. The deploy crashed before it even
started.

---

## 2. Things a Developer Must Manually Configure

The CI/deploy pipeline cannot function without these being set correctly
in GitHub repo Settings > Secrets and variables > Actions.

### 2A. Required Secrets (deploy will not start without these)

| Secret | Used by | Purpose |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | deploy job | IAM key for EB CLI + AWS CLI |
| `AWS_SECRET_ACCESS_KEY` | deploy job | IAM secret |
| `AWS_REGION` | deploy job, config.py | AWS region (default: `ap-south-1`) |
| `OPS_EB_ENV` | deploy job, config.py | EB environment name (default: `AxtroShastraProd`) |
| `STATS_KEY` | deploy job, robot tests | Admin API key — robot cleanup hard-fails without it |
| `OPS_TARGET_URL` | deploy job, robot tests | Live site URL (default: `https://www.axtroshastra.com`) |

### 2B. Required Secrets (alerts — deploy succeeds but alerts are silent)

| Secret | Used by | Purpose |
|---|---|---|
| `SMTP_HOST` | alerts.py | SMTP server for email alerts (primary channel) |
| `SMTP_PORT` | alerts.py | SMTP port (default: 587) |
| `SMTP_USER` | alerts.py | SMTP username |
| `SMTP_PASSWORD` | alerts.py | SMTP password |
| `SMTP_FROM` | alerts.py | Sender address (default: SMTP_USER) |
| `OPS_ALERT_EMAILS` | alerts.py | Comma-separated recipient emails |
| `OPS_ALERT_WHATSAPP` | alerts.py | Comma-separated E.164 numbers |
| `TWILIO_ACCOUNT_SID` | alerts.py | Twilio SID for WhatsApp alerts |
| `TWILIO_AUTH_TOKEN` | alerts.py | Twilio auth token |
| `TWILIO_WHATSAPP_FROM` | alerts.py | Twilio sender number |

### 2C. When to Update Secrets

- Rotating AWS IAM keys: update both `AWS_ACCESS_KEY_ID` and
  `AWS_SECRET_ACCESS_KEY` at the same time.
- Changing EB environment name: update `OPS_EB_ENV`.
- After Twilio token rotation: update `TWILIO_AUTH_TOKEN`.
- After SMTP password change: update `SMTP_PASSWORD`.

---

## 3. Deploy Pipeline — What Each Step Does and What Breaks

The deploy job runs only on manual `workflow_dispatch` on `aws-mysql`,
after both test suites pass.

```
pytest (459+) ──┐
                ├── all green ──> deploy ──> wait Green ──> smoke test
E2E (21) ──────┘                                              │
                                                     pass <───┤───> fail
                                                      │              │
                                                  record OK    rollback + alert
```

### Step-by-step

| # | Step | What breaks if misconfigured |
|---|---|---|
| 1 | **Record last-good version** — captures the current EB version label as rollback target | Empty `OPS_EB_ENV` or bad AWS creds → returns None → deploy refused (this is correct — the guard is working) |
| 2 | **Deploy to EB** — `eb deploy` with timestamped label | Wrong env name or insufficient IAM permissions → deploy fails, site unchanged |
| 3 | **Wait for Green** — polls EB health every 15s for 10 min | If new version crashes or health check fails → times out → triggers rollback |
| 4 | **Smoke test** — robot customer runs 106 tests against live site | Missing `STATS_KEY` → robot cleanup 403 → smoke fails → triggers rollback |
| 5a | **Report success** — records in history, alerts | Non-fatal if dashboard POST fails |
| 5b | **Roll back on failure** — redeploys last-good version, alerts | If last-good label was empty → alerts "manual rollback needed" |

### Robot Smoke Test Breakdown (106 tests)

| Phase | Count | What it checks |
|---|---|---|
| B1: Page health | 44 | HTTP 200, no JS errors, no overflow, load < 5s |
| B2: Funnel smoke | 16 | Form fill + submit across languages and viewports |
| B3: SEO checks | 44 | title, meta description, h1, canonical, img alt |
| B4: Cleanup | 2 | Admin cleanup endpoint returns 200 with STATS_KEY |

---

## 4. Things You Cannot Simulate Locally — Verify Instead

Some parts of the deploy pipeline require real AWS / live-site access.
You cannot skip them — verify them explicitly.

| What | Cannot simulate because | How to verify instead |
|---|---|---|
| `mechanic.current_version()` | Needs real AWS creds + EB env | Verify `OPS_EB_ENV` resolves correctly in config: `python -c "import os; os.environ['OPS_EB_ENV']=''; from ops import config; assert config.EB_ENV == 'AxtroShastraProd'"` |
| `eb deploy` | Needs real EB environment | Verify EB CLI is installed and env name is valid |
| Robot smoke on live site | Needs the site running | Run robot tests against local server as a proxy: `OPS_TARGET_URL=http://127.0.0.1:8000 ADMIN_KEY=test npx playwright test` (limited — no real Razorpay) |
| Alert delivery (email/WhatsApp) | Needs real SMTP/Twilio | Verify `alerts_configured()` returns True with the secrets set: `from ops.config import alerts_configured` |
| Concurrency guard | Needs GitHub Actions | Nothing to verify locally — just don't trigger two deploys |

---

## 5. Common Mistakes and How to Avoid Them

| Mistake | What happened | Prevention |
|---|---|---|
| Bare import of dev-only package | `from dotenv import load_dotenv` crashed CI | Import audit (1A): wrap in `try/except ImportError` |
| `os.getenv` with default doesn't handle empty | `OPS_EB_ENV=""` bypassed the default | Use `or` pattern (1F) |
| Auth function checks only one key | `_valid_admin_secret()` checked ADMIN_KEY but not STATS_KEY | Test admin endpoints with both keys |
| Missing `<link rel="canonical">` | Robot SEO test failed on `/login` | Check every new page for SEO tags (1E) |
| Test payment IDs too short | `_is_razorpay_id()` requires 18+ chars | Use `pay_TEST` + 14 chars in test fixtures |
| `continue-on-error: true` hides failures | CI step shows green but `outcome` is `failure` | Check `steps.X.outcome` not `steps.X.conclusion` in conditionals |

---

## 6. File Reference

| File | Purpose |
|---|---|
| `requirements.build.txt` | Production/CI dependencies — the ONLY packages available in deploy |
| `requirements-dev.txt` | Includes build + pytest, httpx, pyyaml for local dev |
| `.github/workflows/ci.yml` | CI pipeline: test → e2e → guarded deploy |
| `ops/config.py` | Central config — all env vars with defaults |
| `ops/mechanic.py` | Rollback + remediation engine |
| `ops/alerts.py` | Email + WhatsApp alerting (never raises) |
| `ops/watcher.py` | Deep health probe (5 endpoints + wallet balances) |
| `ops/history.py` | Append-only JSONL event store |
| `ops/robot_customer/` | Playwright smoke tests for the live site |
| `tests/` | Pytest unit/integration tests |
| `tests/e2e/` | Playwright E2E tests (local server) |
