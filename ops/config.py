"""Central config for the ops framework — everything comes from environment
variables so the kit is portable and carries no secrets. Reuses the app's
existing SMTP_* / TWILIO_* names so ONE set of credentials serves both the app
and these bots (Deepak sets them once as GitHub secrets)."""
import os


def _list(name):
    return [x.strip() for x in os.getenv(name, "").split(",") if x.strip()]


# --- Target: the deployment the bots watch (local / staging / prod) ---
TARGET_URL = os.getenv("OPS_TARGET_URL", "https://www.axtroshastra.com").rstrip("/")
STATS_KEY = os.getenv("STATS_KEY", "")          # admin key: /api/make_pass, /api/reconcile, /api/pdf_health, /api/stats
HTTP_TIMEOUT = int(os.getenv("OPS_HTTP_TIMEOUT") or "25")

# --- Who to alert ---
ALERT_EMAILS = _list("OPS_ALERT_EMAILS")        # "dev1@x.com,dev2@x.com"
ALERT_WHATSAPP = _list("OPS_ALERT_WHATSAPP")    # "+9199...,+9198..." (E.164)

# --- Email (same names delivery.py uses; the RELIABLE alert channel) ---
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT") or "587")
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM") or SMTP_USER
SMTP_STARTTLS = os.getenv("SMTP_STARTTLS", "1") == "1"

# --- WhatsApp (Twilio; BEST-EFFORT — email is primary. See alerts.py note) ---
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "")

# --- Elastic Beanstalk (Method B rollback: redeploy last-good version) ---
EB_ENV = os.getenv("OPS_EB_ENV", "AxtroShastraProd")
AWS_REGION = os.getenv("AWS_REGION") or os.getenv("OPS_AWS_REGION", "ap-south-1")

# --- History store (append-only JSON-lines; the admin dashboard reads it) ---
OPS_HISTORY_PATH = os.getenv("OPS_HISTORY_PATH", "ops_history.jsonl")

# --- Auto-rollback safety switch -------------------------------------------- #
# Auto-rollback is DISARMED by default: the robot-customer failure path is
# allowed to alert but must NOT redeploy on its own until Deepak explicitly
# arms it (OPS_ROLLBACK_ARMED=1). The post-deploy guard rolls back to a known
# pre-deploy label and is safe regardless of this flag.
OPS_ROLLBACK_ARMED = os.getenv("OPS_ROLLBACK_ARMED", "0") == "1"
# Optional known-good version label to fall back to when no target is given.
OPS_LAST_GOOD = os.getenv("OPS_LAST_GOOD", "")


def alerts_configured():
    return bool((ALERT_EMAILS and SMTP_HOST) or (ALERT_WHATSAPP and TWILIO_SID))
