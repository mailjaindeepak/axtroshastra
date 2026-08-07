# Operator RUNBOOK — Axtroshastra ops framework (T6)

Plain-English guide for running the monitoring + safe-deploy kit. No coding
needed to operate it. If something breaks, this is the page to open.

The kit has **three layers of watching** plus a **guarded deploy**:

1. **UptimeRobot** (free, external) — the fast "is the site up?" pulse, every 5 min.
2. **The Watcher** (GitHub) — a DEEP health check a few times a day.
3. **The Robot Customer** (GitHub) — pretends to be a real buyer and checks the
   whole journey works.
4. **The Deploy Guard** (GitHub) — deploys new code and auto-reverts a bad deploy.

Alerts always go out on **two channels**: **email** (the reliable one) and
**WhatsApp** (best-effort). If WhatsApp is down, email still arrives.

---

## 1. Set up the FREE UptimeRobot monitor (do this first)

UptimeRobot pings the site every 5 minutes so we don't spend GitHub minutes on a
shallow "is it up" check. Free tier is plenty.

1. Go to **uptimerobot.com** and create a free account (or log in).
2. **+ Add New Monitor**.
3. **Monitor Type:** `HTTP(s)`.
4. **Friendly Name:** `Axtroshastra – healthz`.
5. **URL:** `https://www.axtroshastra.com/healthz`.
6. **Monitoring Interval:** `5 minutes`.
7. Under **Alert Contacts To Notify**, add contacts and tick them:
   - **Email** — the dev email (same one in `OPS_ALERT_EMAILS`).
   - Optionally **SMS / WhatsApp / Telegram** — add your phone as an alert
     contact so a phone alert also fires.
8. **Create Monitor.**

That's it — UptimeRobot now watches the front door for free and emails/texts you
the moment `/healthz` stops returning 200. Its ping lands on the `:30` of each
5-minute slot; our GitHub watcher is deliberately offset from that.

---

## 2. What the three GitHub workflows do, and when

All three live in `.github/workflows/`. Each can also be run on demand from the
**Actions** tab → pick the workflow → **Run workflow** (this is "manual
dispatch"). Secrets they need are listed in `ops/SECRETS.md`.

### a) `ops-watcher.yml` — the DEEP health check
- **When:** 3×/day at **01:00, 09:00, 17:00 UTC** (≈ 06:30 / 14:30 / 22:30 IST),
  plus manual.
- **What:** probes the deeper things UptimeRobot's shallow ping can't see:
  - `/healthz/db` — the database can actually **write and read back** (durability).
  - `/api/pdf_health?key=…` — the **PDF renderer** produces output (`render_ok`).
  - `/api/otp/health` — the **OTP / SMS provider** is reachable.
- **On failure:** any one of these red → sends a **`critical`** alert (email +
  WhatsApp) and the workflow run itself goes red. It does NOT touch the deploy.
- **Why not more often:** the fast pulse is UptimeRobot's job (free). Running a
  deep check hourly would burn GitHub minutes for no benefit.

### b) `ops-robot-customer.yml` — the end-to-end customer journey
- **When:** 3×/day — **6 AM / 2 PM / 10 PM IST** (cron `30 0,8,16 * * *`), plus manual.
- **What:** drives a real browser (desktop + mobile) against the LIVE site: fills
  the birth form, unlocks with a **free test pass** (no real payment), and
  confirms the paid report + PDF actually render.
- **On failure:** sends a **`critical`** alert (email + WhatsApp) with a link to
  the failed run. A failure here means "something broke on a running site." It
  does **NOT** roll back — routine failures are not deploy problems.

### c) `ops-deploy-guard.yml` — guarded deploy with auto-rollback
- **When:** **manual only** (opt-in). Use this instead of a plain `eb deploy`
  when you want a bad deploy to revert itself.
- **What:** (1) records the version live right now as "last-good", (2) deploys
  the new version, (3) waits for the environment to go **Green**, (4) runs the
  robot-customer smoke test, (5) if the env never goes Green OR the smoke test
  fails → **rolls back to last-good** and alerts. Otherwise the new version stays.
- The rollback here targets the version that was live *before this deploy*, so it
  is safe regardless of the `OPS_ROLLBACK_ARMED` switch.

> Also present, for manual use: `eb-list-versions.yml` (list saved versions) and
> `eb-rollback.yml` (roll PRODUCTION back to ANY chosen past version — paste the
> label + type `AxtroShastraProd` to confirm).

---

## 3. FIRE DRILL — run this BEFORE arming auto-rollback

**Auto-rollback stays DISARMED until this drill passes.** The switch is the
GitHub secret `OPS_ROLLBACK_ARMED` — default (unset / `'0'`) = **disarmed**:
routine failures only alert, they never redeploy on their own. Do not set it to
`'1'` until every step below is green.

### Step 0 — confirm the secrets are in place
Check `ops/SECRETS.md` and confirm all the required GitHub secrets exist
(especially `SMTP_*`, `TWILIO_*`, `OPS_ALERT_EMAILS`, `OPS_ALERT_WHATSAPP`, and
the AWS keycard for the deploy guard).

### Step 1 — prove the happy path
- **Actions → `ops-watcher` → Run workflow.** It should finish **green** and
  send **no** alert.
- **Actions → `ops-robot-customer` → Run workflow.** It should finish **green**
  and send **no** alert.

### Step 2 — force a failure and confirm the alert reaches BOTH channels
The goal is to see a real alert land in **email AND WhatsApp**. Pick one:
- **Easiest:** temporarily set the `OPS_TARGET_URL` secret to a URL that will
  fail (e.g. `https://www.axtroshastra.com/definitely-not-real`) and manually run
  `ops-watcher`. It should go **red** and fire a `critical` alert.
- **OR** manually dispatch `ops-robot-customer` against a broken staging URL.

Confirm:
- [ ] The **email** alert arrived (subject starts with `🚨 [Axtroshastra ops]`).
- [ ] The **WhatsApp** alert arrived on the dev phone.

Then **restore `OPS_TARGET_URL`** to the real site and re-run the workflow to
confirm it goes green again.

### Step 3 — prove a rollback actually works (by hand, once)
Before trusting *automatic* rollback, prove the *manual* rollback path end-to-end:
- **Actions → `eb-list-versions`** → copy the current known-good version label.
- **Actions → `eb-rollback`** → paste that label, type `AxtroShastraProd` to
  confirm, run it. Watch it verify the version, redeploy, and wait for **Green**.
- Confirm the site is healthy afterwards (run `ops-watcher` again → green).

This proves the AWS keycard, the version history, and the Green-wait logic all
work — the same machinery the deploy guard's auto-rollback relies on.

### Step 4 — ONLY NOW arm auto-rollback
Once Steps 1–3 all pass:
- Set the GitHub secret **`OPS_ROLLBACK_ARMED` = `1`**.

Until then, leave it unset/`0`. Disarmed is the safe default: you still get every
alert; you just don't let a bot redeploy production on its own until you've seen
the whole chain work with your own eyes.

---

## Quick reference — where things live

| Thing | File |
|---|---|
| Deep health check logic | `ops/watcher.py` |
| Alert fan-out (email + WhatsApp) | `ops/alerts.py` |
| Config / safety switches | `ops/config.py` |
| GitHub secrets checklist | `ops/SECRETS.md` |
| Watcher schedule | `.github/workflows/ops-watcher.yml` |
| Robot customer | `.github/workflows/ops-robot-customer.yml` |
| Guarded deploy + auto-rollback | `.github/workflows/ops-deploy-guard.yml` |
| Manual rollback to any version | `.github/workflows/eb-rollback.yml` |
