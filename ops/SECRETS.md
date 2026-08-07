# T6 ops framework — one-time setup (GitHub secrets)

The bots run in **GitHub Actions** and talk to the live site from the outside.
They carry no secrets in code — everything comes from **GitHub repository secrets**.
Set these once: **GitHub → repo → Settings → Secrets and variables → Actions → New repository secret.**

> Deepak sets these. They are never pasted into chat or committed to code.

## Required for the Watcher + Robot-customer (deep health checks + alerts)

| Secret | What it is | Example |
|---|---|---|
| `OPS_TARGET_URL` | The live site the bots watch | `https://www.axtroshastra.com` |
| `STATS_KEY` | The existing admin key (unlocks `/api/make_pass`, `/api/reconcile`, `/api/pdf_health`) | *(same value as prod `STATS_KEY`)* |
| `OPS_ALERT_EMAILS` | Who gets email alerts (comma-separated) | `mail.jain.deepak@gmail.com,dev2@x.com` |
| `OPS_ALERT_WHATSAPP` | Who gets WhatsApp alerts (comma-separated, +country) | `+9199...,+9198...` |
| `SMTP_HOST` | SMTP server the alert email is sent through (same account the app uses) | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port | `587` |
| `SMTP_USER` | SMTP login / username | `alerts@axtroshastra.com` |
| `SMTP_PASSWORD` | SMTP password / app-password | *(app password)* |
| `SMTP_FROM` | The "From" address on alert emails (defaults to `SMTP_USER` if unset) | `alerts@axtroshastra.com` |
| `TWILIO_ACCOUNT_SID` | Twilio account SID (WhatsApp — best-effort; email is the reliable channel) | `AC…` |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | *(token)* |
| `TWILIO_WHATSAPP_FROM` | Twilio WhatsApp sender | `whatsapp:+14155238886` |

Email is the **reliable** alert channel; WhatsApp is **best-effort**. If the
Twilio secrets are missing or wrong, alerts still go out by email and nothing
raises (see `ops/alerts.py`).

## Additionally required for the guarded deploy + auto-rollback (`ops-deploy-guard.yml`)

| Secret | What it is |
|---|---|
| `AWS_ACCESS_KEY_ID` | A **limited** AWS key that can ONLY read + update the Beanstalk environment (the "keycard" — see below) |
| `AWS_SECRET_ACCESS_KEY` | The secret half of that keycard |
| `AWS_REGION` | `ap-south-1` |
| `OPS_EB_ENV` | `AxtroShastraProd` |

**The limited AWS keycard** — create an IAM user with a policy allowing only:
`elasticbeanstalk:DescribeEnvironments`, `elasticbeanstalk:UpdateEnvironment`,
plus the read permissions `eb deploy` needs (S3 put for the app bundle,
`elasticbeanstalk:CreateApplicationVersion`, `autoscaling:*`/`ec2:*` as EB
requires). Give it nothing else. This is the key the rollback uses.

## Auto-rollback safety switch + history store (owned by `ops/config.py`)

These two are read by `ops/config.py`. They are NOT required for the watcher or
alerts — they gate the **auto-rollback** behaviour and the history log.

| Secret / env | What it is | Default |
|---|---|---|
| `OPS_ROLLBACK_ARMED` | Master safety switch. `'1'` = auto-rollback ARMED; anything else = DISARMED (alert only, never redeploys on its own). **Leave unset / `'0'` until the fire-drill in `RUNBOOK.md` passes.** | `0` (disarmed) |
| `OPS_HISTORY_PATH` | Where the append-only JSON-lines run history is written (the admin dashboard reads it) | `ops_history.jsonl` |

> The post-deploy guard (`ops-deploy-guard.yml`) rolls back to the version that
> was live *before its own deploy* and is safe regardless of `OPS_ROLLBACK_ARMED`.
> The flag only governs whether a *routine* (non-deploy) failure is allowed to
> redeploy on its own.

## The free 5-minute heartbeat (external — not GitHub)

To stay inside GitHub's free minutes, the **5-minute uptime ping is NOT GitHub** —
set up a **free UptimeRobot monitor** (uptimerobot.com, free tier):
- Monitor type: **HTTP(s)** → URL `https://www.axtroshastra.com/healthz`
- Interval: **5 minutes**
- Alert contacts: the same dev email + (optionally) WhatsApp/Telegram.

GitHub runs the *deeper* watcher (a few times a day) and the robot-customer;
UptimeRobot covers the fast "is it up" pulse for free. Full step-by-step setup +
the pre-arming fire drill are in **`ops/RUNBOOK.md`**.

## What runs, and when

| Workflow | Trigger | Cost |
|---|---|---|
| `ops-watcher.yml` | 3×/day (01:00, 09:00, 17:00 UTC) + manual | ~free (short) |
| `ops-robot-customer.yml` | 3&times;/day (6 AM / 2 PM / 10 PM IST) + manual | within GitHub's free minutes |
| `ops-deploy-guard.yml` | **manual** (opt-in; deploy + auto-rollback) | only when you deploy |
