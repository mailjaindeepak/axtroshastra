# T6 ops framework — one-time setup (GitHub secrets)

The bots run in **GitHub Actions** and talk to the live site from the outside.
They carry no secrets in code — everything comes from **GitHub repository secrets**.
Set these once: **GitHub → repo → Settings → Secrets and variables → Actions → New repository secret.**

> Deepak sets these. They are never pasted into chat or committed to code.

## Required for the Watcher + Robot-customer (health checks + alerts)

| Secret | What it is | Example |
|---|---|---|
| `OPS_TARGET_URL` | The live site the bots watch | `https://www.axtroshastra.com` |
| `STATS_KEY` | The existing admin key (unlocks `/api/make_pass`, `/api/reconcile`, `/api/pdf_health`) | *(same value as prod `STATS_KEY`)* |
| `OPS_ALERT_EMAILS` | Who gets email alerts (comma-separated) | `mail.jain.deepak@gmail.com,dev2@x.com` |
| `OPS_ALERT_WHATSAPP` | Who gets WhatsApp alerts (comma-separated, +country) | `+9199...,+9198...` |
| `SMTP_HOST` `SMTP_PORT` `SMTP_USER` `SMTP_PASSWORD` `SMTP_FROM` | Email account the alerts are sent **from** (the same SMTP the app uses) | `smtp.gmail.com` / `587` / … |
| `TWILIO_ACCOUNT_SID` `TWILIO_AUTH_TOKEN` `TWILIO_WHATSAPP_FROM` | Twilio creds for WhatsApp alerts (best-effort — email is the reliable channel) | `AC…` / … / `whatsapp:+…` |

## Additionally required for the guarded deploy + auto-rollback (`ops-deploy-guard.yml`)

| Secret | What it is |
|---|---|
| `AWS_ACCESS_KEY_ID` `AWS_SECRET_ACCESS_KEY` | A **limited** AWS key that can ONLY read + update the Beanstalk environment (the "keycard" — see below) |
| `AWS_REGION` | `ap-south-1` |
| `OPS_EB_ENV` | `AxtroShastraProd` |

**The limited AWS keycard** — create an IAM user with a policy allowing only:
`elasticbeanstalk:DescribeEnvironments`, `elasticbeanstalk:UpdateEnvironment`,
plus the read permissions `eb deploy` needs (S3 put for the app bundle,
`elasticbeanstalk:CreateApplicationVersion`, `autoscaling:*`/`ec2:*` as EB
requires). Give it nothing else. This is the key the rollback uses.

## The free 5-minute heartbeat (external — not GitHub)

To stay inside GitHub's free minutes, the **5-minute uptime ping is NOT GitHub** —
set up a **free UptimeRobot monitor** (uptimerobot.com, free tier):
- Monitor type: **HTTP(s)** → URL `https://www.axtroshastra.com/healthz`
- Interval: **5 minutes**
- Alert contacts: the same dev email + (optionally) WhatsApp/Telegram.

GitHub runs the *deeper* hourly watcher and the 4-hourly robot; UptimeRobot covers
the fast "is it up" pulse for free.

## What runs, and when

| Workflow | Trigger | Cost |
|---|---|---|
| `ops-watcher.yml` | hourly + manual | ~free (short) |
| `ops-robot-customer.yml` | every 4 hours + manual | within GitHub's free minutes |
| `ops-deploy-guard.yml` | **manual** (opt-in; deploy + auto-rollback) | only when you deploy |

After the secrets are set, do one **fire drill**: run `ops-watcher` manually (should
pass), then temporarily break something in a staging deploy and run
`ops-deploy-guard` to watch it roll back and alert.
