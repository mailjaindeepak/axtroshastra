"""
Axtroshastra API — production wiring.

POST /api/kundli      : compute FULL report server-side, store, return TEASER only
POST /api/order       : create LIVE Razorpay order bound to report_id
POST /api/webhook     : payment.captured -> mark paid (HMAC-verified, source of truth)
GET  /api/report/{id} : full JSON only if paid
GET  /                : landing page ; GET /report/{id} : report view

Env vars (set in Railway/Render dashboard, never in code or git):
  RAZORPAY_KEY_ID          rzp_live_xxx
  RAZORPAY_KEY_SECRET      xxx
  RAZORPAY_WEBHOOK_SECRET  from Dashboard > Settings > Webhooks
  DB_PATH                  default ./data/reports.db (mount a volume here)
  DEMO_MODE                unset in production. "1" enables /api/_demo_pay for local testing.

Razorpay dashboard prerequisites:
  1. Settings > Payment capture -> AUTO capture (else payment.captured never fires)
  2. Settings > Webhooks -> https://<your-domain>/api/webhook , event: payment.captured
"""
import hashlib, hmac, json, logging, os, secrets, sqlite3, threading
import dbcompat
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse,
                               PlainTextResponse, RedirectResponse, Response)
from pydantic import BaseModel, field_validator

from engine import compute_report
from report_view import render_report, render_milan, render_blueprint, render_vidyarthi, north_chart_svg
from products import compute_milan, compute_blueprint
from vidyarthi import compute_vidyarthi_report
from geocoding import resolve as geocode          # (#1) accurate, cached geocoding
from geocoding import resolve_detailed             # (#1) with resolved/source provenance
import payments, delivery, extensions
import users                 # account layer: create/link a user at payment time
import auth                  # OTP login + session layer (Twilio Verify)
import gazetteer             # (#6) payments, (#7) delivery, endpoints
from ratelimit import RateLimitMiddleware, captcha_ok   # (#4) rate limit + bot defense

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("axtroshastra")

app = FastAPI(title="Axtroshastra API", docs_url=None, redoc_url=None)
app.add_middleware(RateLimitMiddleware)   # (#4)
BASE = os.path.dirname(os.path.abspath(__file__))

@app.on_event("startup")
def _warm_gazetteer():
    try:
        gazetteer.suggest("mumbai", 1)
    except Exception:
        pass


@app.on_event("startup")
def _log_db_target():
    """Log which storage backend the app actually connected to, and prove the
    connection works, at boot. This makes a misconfig obvious in `eb logs`
    instead of silent: e.g. our RDS listens on the NON-default port 1232, so if
    DB_PORT is ever dropped from the env the app would try :3306, and this line
    prints the wrong target + CONNECT FAILED right at startup. Password is never
    logged — only backend and host:port/db (or the sqlite path)."""
    if dbcompat.using_mysql():
        backend = "mysql"
        target = (f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '3306')}"
                  f"/{os.getenv('DB_NAME')}")
    else:
        backend = "sqlite"
        target = os.getenv("DB_PATH", os.path.join(BASE, "data", "reports.db"))
    try:
        with db() as c:
            c.execute("SELECT 1")
        logger.info("[db] connected OK  backend=%s  target=%s", backend, target)
    except Exception as e:
        logger.error("[db] CONNECT FAILED  backend=%s  target=%s  err=%s",
                     backend, target, e)


PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")   # e.g. https://axtroshastra.com

# ---- Twilio WhatsApp delivery (all optional; no-op until env vars set) ----
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "")     # 'whatsapp:+14155238886' (sandbox) or your sender
TWILIO_CONTENT_SID = os.getenv("TWILIO_CONTENT_SID", "")  # approved template SID for production

PRODUCT_LABEL = {"marriage": "Marriage Timing", "milan": "Kundli Milan",
                  "blueprint": "Life Blueprint", "vidyarthi": "Career & Academic Timing"}

def send_whatsapp_report(phone: str, rid: str, name: str, product: str = "marriage"):
    """Fire-and-forget WhatsApp delivery after payment. Never raises."""
    if not (TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM and phone and PUBLIC_BASE_URL):
        return
    try:
        from twilio.rest import Client
        to = phone if phone.startswith("+") else "+91" + phone[-10:]
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        link = f"{PUBLIC_BASE_URL}/report/{rid}"
        label = PRODUCT_LABEL.get(product, "Marriage Timing")
        if TWILIO_CONTENT_SID:                       # production: approved template
            client.messages.create(
                from_=TWILIO_FROM, to=f"whatsapp:{to}",
                content_sid=TWILIO_CONTENT_SID,
                content_variables=json.dumps({"1": name, "2": link}))
        else:                                        # sandbox / 24h session freeform
            client.messages.create(
                from_=TWILIO_FROM, to=f"whatsapp:{to}",
                body=(f"Namaste {name}! 🙏 Aapki Axtroshastra {label} "
                      f"Report ready hai:\n{link}\n\nPDF download button report "
                      f"ke andar hai. Koi bhi sawaal ho — reply kijiye."))
    except Exception as e:                            # delivery must never break the webhook
        logger.error("[twilio] send failed for %s: %s", rid, e)

def _render_for(product, payload):
    if product == "milan":
        return render_milan(payload)
    if product == "blueprint":
        return render_blueprint(payload)
    if product == "vidyarthi":
        return render_vidyarthi(payload)
    return render_report(payload)


def email_report(to_addr, rid, payload):        # (#7) fire-and-forget; never raises
    try:
        html = _render_for(payload.get("product", "marriage"), payload)
        pdf = delivery.html_to_pdf(html)
        link = f"{PUBLIC_BASE_URL}/report/{rid}" if PUBLIC_BASE_URL else ""
        body = f"Namaste! Aapki Axtroshastra report ready hai: {link}"
        delivery.send_email(to_addr, "Your Axtroshastra Report", body, pdf)
    except Exception as e:
        logger.error("email_report failed for %s: %s", rid, e)


RZP_KEY = os.getenv("RAZORPAY_KEY_ID", "")
RZP_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RZP_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
DEMO_MODE = os.getenv("DEMO_MODE") == "1"
STATS_KEY = os.getenv("STATS_KEY", "")    # gates /api/stats and /api/make_pass admin routes
PRICE_PAISE = 49900                       # ₹499 — server-side only, never trust client
MILAN_PRICE_PAISE = 29900                 # ₹299 — milan landing price (/milan and /match funnels)


def _valid_admin_key(key: str) -> bool:
    """Constant-time check for the admin key; always False when unset."""
    return bool(STATS_KEY) and hmac.compare_digest(key or "", STATS_KEY)

_rzp = None
def rzp_client():
    global _rzp
    if _rzp is None:
        if not (RZP_KEY and RZP_SECRET):
            raise HTTPException(503, "Payment not configured")
        import razorpay
        _rzp = razorpay.Client(auth=(RZP_KEY, RZP_SECRET))
    return _rzp

# ----------------------------------------------------------------- storage
DB_PATH = os.getenv("DB_PATH", os.path.join(BASE, "data", "reports.db"))
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
_lock = threading.Lock()

def db():
    conn = dbcompat.connect()
    conn.execute("""CREATE TABLE IF NOT EXISTS reports(
        id TEXT PRIMARY KEY, payload TEXT NOT NULL, paid INTEGER DEFAULT 0,
        order_id TEXT, payment_id TEXT, phone TEXT, created_at TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS passes(
        token TEXT PRIMARY KEY, used INTEGER DEFAULT 0, created_at TEXT)""")
    return conn

def save_report(rid, payload):
    with _lock, db() as c:
        c.execute("INSERT INTO reports(id,payload,created_at) VALUES(?,?,?)",
                  (rid, json.dumps(payload), datetime.utcnow().isoformat()))

def get_report(rid):
    with db() as c:
        row = c.execute("SELECT payload,paid,order_id FROM reports WHERE id=?",
                        (rid,)).fetchone()
    if not row: return None
    return {"payload": json.loads(row[0]), "paid": bool(row[1]), "order_id": row[2]}

def set_order(rid, order_id):
    with _lock, db() as c:
        c.execute("UPDATE reports SET order_id=? WHERE id=?", (order_id, rid))

def mark_paid(rid, payment_id=None, phone=None):
    with _lock, db() as c:
        c.execute("UPDATE reports SET paid=1,payment_id=?,phone=? WHERE id=?",
                  (payment_id, phone, rid))

# ----------------------------------------------------------------- geocode
# geocoding lives in geocoding.py: cache -> CITIES_IN -> external -> Delhi fallback (#1)
payments.ensure_tables(db)   # (#6) webhook_events + refunds tables
users.ensure_tables(db)      # users + user_mobiles tables + reports.user_id link
auth.ensure_tables(db)       # sessions + login_otps (OTP login)

# ----------------------------------------------------------------- models
class KundliIn(BaseModel):
    name: str
    dob: str
    tob: str | None = None
    time_quality: str = "T0"
    time_band: str | None = None
    place: str
    lat: float | None = None
    lon: float | None = None
    tz: str | None = None
    gender: str | None = None
    variant: str | None = None
    email: str | None = None
    captcha_token: str | None = None
    product: str = "marriage"          # marriage | blueprint | vidyarthi
    stage: str | None = None           # vidyarthi only: 10th | 12th | college | postgrad
    field: str | None = None           # vidyarthi only: set when stage is college/postgrad

    @field_validator("time_quality")
    @classmethod
    def _tq(cls, v):
        if v not in ("T0", "T1", "T2", "T3"): raise ValueError("bad time_quality")
        return v

BAND_MID = {"subah": "07:00", "din": "13:00", "shaam": "19:00", "raat": "01:00"}

# ----------------------------------------------------------------- routes
PAGES_DIR = os.path.join(BASE, "pages")

# ----------------------------------------------------------------- site nav
# A self-contained hamburger menu injected into every served HTML page. Classes
# are `axs-nav-` prefixed and all styles are scoped/inline so it cannot clash with
# any page's own CSS. Injected right after <body> by _inject_nav().
NAV_LINKS = [
    ("Login / My Account", "/account"),
    ("About Us", "/about"),
    ("Privacy Policy", "/privacy"),
    ("Terms of Use", "/terms"),
    ("Blogs", "/blog"),
]

def _nav_html() -> str:
    items = "".join(
        f'<a href="{href}" class="axs-nav-item">{label}</a>' for label, href in NAV_LINKS
    )
    return (
        '<div id="axs-nav">'
        '<button class="axs-nav-btn" aria-label="Menu" '
        'onclick="document.getElementById(\'axs-nav\').classList.toggle(\'open\')">'
        '<span></span><span></span><span></span></button>'
        '<div class="axs-nav-backdrop" '
        'onclick="document.getElementById(\'axs-nav\').classList.remove(\'open\')"></div>'
        '<nav class="axs-nav-panel">'
        '<div class="axs-nav-head">Menu</div>'
        + items +
        '</nav></div>'
        '<style>'
        '#axs-nav .axs-nav-btn{position:fixed;top:14px;right:14px;z-index:9998;'
        'width:44px;height:44px;border:0;border-radius:11px;background:rgba(21,28,57,.92);'
        'display:flex;flex-direction:column;justify-content:center;align-items:center;'
        'gap:4px;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.18)}'
        '#axs-nav .axs-nav-btn span{width:20px;height:2px;background:#E4B04A;border-radius:2px}'
        '#axs-nav .axs-nav-backdrop{position:fixed;inset:0;z-index:9998;background:rgba(10,12,24,.5);'
        'opacity:0;pointer-events:none;transition:opacity .2s}'
        '#axs-nav.open .axs-nav-backdrop{opacity:1;pointer-events:auto}'
        '#axs-nav .axs-nav-panel{position:fixed;top:0;right:0;z-index:9999;height:100%;width:270px;'
        'max-width:82vw;background:#151C39;color:#F3EFE4;transform:translateX(100%);'
        'transition:transform .22s ease;box-shadow:-8px 0 24px rgba(0,0,0,.25);'
        'padding:22px 0;font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif}'
        '#axs-nav.open .axs-nav-panel{transform:translateX(0)}'
        '#axs-nav .axs-nav-head{font-size:12px;letter-spacing:.16em;text-transform:uppercase;'
        'color:#E4B04A;font-weight:700;padding:6px 24px 14px}'
        '#axs-nav .axs-nav-item{display:block;padding:14px 24px;color:#F3EFE4;text-decoration:none;'
        'font-size:15.5px;border-top:1px solid rgba(255,255,255,.07)}'
        '#axs-nav .axs-nav-item:active{background:rgba(255,255,255,.06)}'
        '@media print{#axs-nav{display:none}}'
        '</style>'
    )

def _inject_nav(html: str) -> str:
    """Insert the hamburger nav right after the opening <body> tag. If for some
    reason there's no <body>, return the html unchanged (never break a page)."""
    import re
    nav = _nav_html()
    new_html, n = re.subn(r"(<body[^>]*>)", lambda m: m.group(1) + nav,
                          html, count=1, flags=re.IGNORECASE)
    return new_html if n else html

def _serve_page_with_nav(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return HTMLResponse(_inject_nav(f.read()))
    except Exception as e:
        logger.error("[nav] failed to serve %s: %s", path, e)
        return FileResponse(path)


@app.get("/healthz", include_in_schema=False)
def healthz():
    """Liveness probe: 200 if the DB is *reachable*. Kept cheap on purpose — this
    is the high-frequency ALB/EB probe, so it only opens a connection and runs a
    trivial query. For the deeper write-durability check use /healthz/db."""
    try:
        with db() as c:
            c.execute("SELECT 1")
        return {"status": "ok"}
    except Exception as e:
        logger.error("healthz db check failed: %s", e)
        raise HTTPException(503, "db unavailable")


@app.get("/healthz/db", include_in_schema=False)
def healthz_db():
    """Deep readiness probe: proves the DB accepts a write AND that the write is
    *durable across connections* — the exact failure we hit once (writes returned
    200, committed, but a later read on a new connection 404'd). A plain SELECT 1
    or a same-connection read-after-write would NOT catch that, so we:
      1. INSERT a sentinel row and let the connection commit + close (via `with`),
      2. re-open a SEPARATE connection and read the row back,
      3. delete it.
    Any mismatch raises 503 loudly instead of the app silently accepting writes
    that never persist. Intended for monitoring/alerting + a scheduled check, NOT
    for the high-frequency ALB probe (that's /healthz)."""
    token = secrets.token_hex(8)
    now = datetime.utcnow().isoformat()
    try:
        # (1) write on one connection; `with` commits and closes on exit.
        with _lock, db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS health_check(
                token TEXT PRIMARY KEY, ts TEXT)""")
            c.execute("INSERT INTO health_check(token, ts) VALUES(?,?)", (token, now))
        # (2) read back on a FRESH connection — this is what proves durability.
        with db() as c:
            row = c.execute("SELECT token FROM health_check WHERE token=?",
                            (token,)).fetchone()
        if not row or row[0] != token:
            raise RuntimeError("write not durable: sentinel missing on re-read")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("healthz/db write self-check FAILED: %s", e)
        raise HTTPException(503, "db write self-check failed")
    finally:
        # (3) best-effort cleanup so the table stays tiny; never fails the probe.
        try:
            with _lock, db() as c:
                c.execute("DELETE FROM health_check WHERE token=?", (token,))
        except Exception as e:
            logger.warning("healthz/db cleanup failed for %s: %s", token, e)
    return {"status": "ok", "db": "write-read-verified"}


@app.get("/", include_in_schema=False)
def landing():
    """Homepage serves the main funnel page (pages/home.html overrides if present)."""
    for candidate in ("home.html", "shaadi.html"):
        path = os.path.join(PAGES_DIR, candidate)
        if os.path.exists(path):
            return _serve_page_with_nav(path)
    return HTMLResponse("<h3 style='font-family:sans-serif;padding:40px'>Axtroshastra</h3>")


@app.get("/api/city-suggest", include_in_schema=False)
def city_suggest(q: str = ""):
    return {"results": gazetteer.suggest(q, 8)}


@app.post("/api/kundli")
def create_kundli(inp: KundliIn):
    if not captcha_ok(inp.captcha_token or "", ""):   # (#4)
        raise HTTPException(400, "captcha_failed")
    if inp.time_quality in ("T0", "T1"):
        if not inp.tob: raise HTTPException(422, "tob required")
        tob = inp.tob
    elif inp.time_quality == "T2":
        tob = BAND_MID.get(inp.time_band or "", "13:00")
    else:
        tob = "12:00"
    local_dt = datetime.fromisoformat(f"{inp.dob}T{tob}:00")
    geo_source = "gazetteer"
    if inp.lat is not None and inp.lon is not None and inp.tz:
        lat, lon = inp.lat, inp.lon
        _off = gazetteer.tz_offset_hours(inp.tz, local_dt); tz = _off if _off is not None else 5.5
    else:
        _hit = gazetteer.suggest(inp.place or "", 1)
        if _hit and _hit[0]["name"].lower() == (inp.place or "").strip().lower():
            lat, lon = _hit[0]["lat"], _hit[0]["lon"]
            _off = gazetteer.tz_offset_hours(_hit[0]["tz"], local_dt); tz = _off if _off is not None else 5.5
            geo_source = "gazetteer-text"
        else:
            raise HTTPException(422, "city_not_selected")
    if inp.product == "blueprint":
        report = compute_blueprint(inp.name, inp.dob, tob, tz, lat, lon,
                                   time_quality=inp.time_quality)
    elif inp.product == "vidyarthi":
        report = compute_vidyarthi_report(inp.name, inp.dob, tob, tz, lat, lon,
                                          female=(inp.gender == "female"),
                                          time_quality=inp.time_quality,
                                          stage=inp.stage, field=inp.field)
    else:
        report = compute_report(name=inp.name, dob=inp.dob, tob=tob,
                                tz_offset_hours=tz, lat=lat, lon_geo=lon,
                                female=(inp.gender == "female"),
                                time_quality=inp.time_quality)
    report["meta"]["variant"] = (inp.variant or "direct")[:64]
    report["meta"]["geo_source"] = geo_source
    try:
        if report.get("chart"):
            report["teaser"]["chart_svg"] = north_chart_svg(report)
    except Exception:
        pass         # (#1) provenance

    report["meta"]["_birth"] = {"dob": inp.dob, "tob": tob, "tz": tz,
                                "lat": lat, "lon": lon}   # (#8) for /api/deep
    if inp.email:
        report["meta"]["_email"] = inp.email             # (#7)
    rid = secrets.token_urlsafe(12)
    save_report(rid, report)
    return {"report_id": rid, "teaser": report["teaser"]}


@app.post("/api/order")
def create_order(body: dict):
    rid = body.get("report_id")
    rec = get_report(rid)
    if not rec: raise HTTPException(404, "report not found")
    if rec["paid"]:                              # already paid -> skip checkout
        return {"already_paid": True}
    tok = (body.get("pass") or "").strip()
    if tok:
        with _lock, db() as conn:
            row = conn.execute("SELECT used FROM passes WHERE token=?", (tok,)).fetchone()
            if row and row[0] == 0:
                conn.execute("UPDATE passes SET used=1 WHERE token=?", (tok,))
                conn.execute("UPDATE reports SET paid=1, payment_id=? WHERE id=?",
                             ("free_pass:" + tok, rid))
                return {"free": True}
        return {"error": "invalid_pass"}
    variant = ((rec.get("payload") or {}).get("meta") or {}).get("variant") or ""
    amount_paise = MILAN_PRICE_PAISE if variant in ("/milan", "/match") else PRICE_PAISE
    order = rzp_client().order.create({
        "amount": amount_paise, "currency": "INR",
        "receipt": rid, "notes": {"report_id": rid}})
    set_order(rid, order["id"])
    return {"razorpay_order_id": order["id"], "amount": order["amount"],
            "currency": "INR", "key_id": RZP_KEY}


@app.post("/api/webhook")
async def razorpay_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    sig = request.headers.get("X-Razorpay-Signature", "")
    if not RZP_WEBHOOK_SECRET:
        raise HTTPException(503, "webhook secret not configured")
    expected = hmac.new(RZP_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(400, "bad signature")
    event = json.loads(body)
    eid = payments.event_id_of(event)
    if payments.already_processed(db, eid):     # (#6) idempotency
        return {"ok": True, "duplicate": True}
    rid = None
    if event.get("event") == "payment.captured":
        ent = event["payload"]["payment"]["entity"]
        rid = (ent.get("notes") or {}).get("report_id")
        if rid:
            rec = get_report(rid)
            if rec:
                phone = ent.get("contact") or ""
                mark_paid(rid, payment_id=ent.get("id"), phone=phone)
                background_tasks.add_task(
                    send_whatsapp_report, phone, rid,
                    rec["payload"]["meta"]["name"],
                    rec["payload"].get("product", "marriage"))
                form_email = rec["payload"]["meta"].get("_email")
                # Account: create/link a user from the Razorpay payment (mobile +
                # email). Prefer the email Razorpay collected; fall back to the one
                # typed into the form. Never let account creation break the webhook.
                pay_email = ent.get("email") or form_email or ""
                try:
                    uid = users.upsert_user_from_payment(
                        db, mobile=phone, email=pay_email,
                        name=rec["payload"]["meta"].get("name"))
                    if uid:
                        users.link_report(db, rid, uid)
                except Exception as e:
                    logger.error("[users] account upsert failed for %s: %s", rid, e)
                if form_email:                   # (#7) email + PDF delivery
                    background_tasks.add_task(email_report, form_email, rid, rec["payload"])
    payments.mark_processed(db, eid, event.get("event", ""), rid or "")
    return {"ok": True}


def _refresh_current_period(payload: dict) -> dict:
    """Recompute the time-dependent \"current period\" (current MD/AD + end date)
    from stored birth data so it is accurate as of *now*, not frozen at the time
    the report was created. No-op if birth data is missing (e.g. milan)."""
    birth = (payload.get("meta") or {}).get("_birth")
    if not birth:
        return payload
    try:
        from engine import compute_chart, current_period
        local = datetime.fromisoformat(f"{birth['dob']}T{birth['tob']}:00")
        dt_utc = local - timedelta(hours=birth["tz"])
        ch = compute_chart(dt_utc, birth["lat"], birth["lon"])
        cp = current_period(ch["grahas"]["Moon"].lon, dt_utc)
        if cp["md"] and cp["ad"]:
            payload.setdefault("teaser", {})["current_dasha"] = (
                f"{cp['md']} Mahadasha \u2014 {cp['ad']} Antardasha")
            payload["teaser"]["dasha_till"] = cp["ad_end"].strftime("%b %Y")
            payload["current_period"] = {"md": cp["md"], "ad": cp["ad"],
                                         "ad_end": cp["ad_end"].strftime("%Y-%m-%d")}
    except Exception as e:
        logger.error("current-period refresh failed: %s", e)
    return payload


@app.get("/api/report/{rid}")
def get_report_api(rid: str):
    rec = get_report(rid)
    if not rec: raise HTTPException(404, "report not found")
    payload = _refresh_current_period(rec["payload"])
    if not rec["paid"]:
        return {"paid": False, "teaser": payload["teaser"]}
    account = None
    try:                                 # saved mobile + email, shown post-payment
        account = users.get_user_for_report(db, rid)
    except Exception as e:
        logger.error("[users] account lookup failed for %s: %s", rid, e)
    return {"paid": True, "report": payload, "account": account}


def _fmt_mobile(m: str) -> str:
    """Display '+919650973345' as '+91 96509 73345'; raw fallback for anything else."""
    if m and m.startswith("+91") and len(m) == 13 and m[3:].isdigit():
        d = m[3:]
        return f"+91 {d[:5]} {d[5:]}"
    return m


def _account_banner(rid: str) -> str:
    """English 'Account created' card shown on a paid report with the saved mobile
    (+ email when we have one). A neutral band wraps a white card so it reads as a
    deliberate confirmation on any product's hero colour. Empty string when no
    account is linked, so it can never break the page. Injected at the top of
    <body> (report HTML ends its head with '</head><body>')."""
    try:
        u = users.get_user_for_report(db, rid)
    except Exception as e:
        logger.error("[users] banner lookup failed for %s: %s", rid, e)
        return ""
    if not u or not (u.get("mobile") or u.get("email")):
        return ""
    import html as _html

    def _row(label, value):
        return ('<div style="display:flex;align-items:center;gap:10px;font-size:13.5px;'
                'color:#2b2521">'
                f'<span style="color:#8a7d72;width:58px;font-size:12px">{label}</span>'
                f'<span style="font-weight:600;letter-spacing:.2px">{value}</span></div>')

    rows = ""
    if u.get("mobile"):
        rows += _row("Mobile", _html.escape(_fmt_mobile(u["mobile"])))
    if u.get("email"):
        rows += _row("Email", _html.escape(u["email"]))

    return (
        '<div style="background:#f3ece0;padding:14px;font-family:system-ui,'
        "-apple-system,'Segoe UI',Roboto,sans-serif\">"
        '<div style="max-width:520px;margin:0 auto;background:#fff;border:1px solid '
        '#ece3d6;border-radius:14px;box-shadow:0 2px 10px rgba(70,50,30,.05);'
        'padding:15px 16px 13px">'
        '<div style="display:flex;align-items:center;gap:11px;margin-bottom:12px">'
        '<span style="width:34px;height:34px;border-radius:50%;background:#eef7f1;'
        'border:1px solid #cfe8dc;color:#157a52;display:inline-flex;align-items:center;'
        'justify-content:center;font-size:16px;flex:0 0 auto">&#10003;</span>'
        '<div><div style="font-size:15px;font-weight:700;color:#2b2521">Account created'
        '</div><div style="font-size:12px;color:#8a7d72;margin-top:1px">Saved from this '
        'purchase</div></div></div>'
        '<div style="border-top:1px solid #ece3d6;padding-top:11px;display:grid;gap:8px">'
        + rows +
        '</div>'
        '<div style="margin-top:12px;font-size:11.5px;color:#8a7d72;display:flex;'
        'align-items:center;gap:6px;flex-wrap:wrap">'
        '<span style="font-size:10px;letter-spacing:.6px;text-transform:uppercase;'
        'background:#fbeeeb;color:#c93b2e;border-radius:20px;padding:3px 8px;'
        'font-weight:700">Coming soon</span> Log in with your mobile to see all your '
        'reports.</div>'
        '</div></div>')


@app.get("/report/{rid}", include_in_schema=False)
def report_page(rid: str):
    rec = get_report(rid)
    if not rec or not rec["paid"]:
        return HTMLResponse("<h3 style='font-family:sans-serif;padding:40px'>"
                            "Report not found ya payment pending hai. "
                            "<a href='/'>Wapas jaayein</a></h3>", status_code=404)
    payload = _refresh_current_period(rec["payload"])
    payload.setdefault("meta", {})["report_id"] = rid
    html = _render_for(payload.get("product", "marriage"), payload)
    banner = _account_banner(rid)
    if banner:
        html = html.replace("</head><body>", "</head><body>" + banner, 1)
    return HTMLResponse(html)


@app.get("/report/{rid}/pdf", include_in_schema=False)
def report_pdf(rid: str):
    rec = get_report(rid)
    if not rec or not rec["paid"]:
        raise HTTPException(404, "report not found")
    payload = _refresh_current_period(rec["payload"])
    payload.setdefault("meta", {})["report_id"] = rid
    html = _render_for(payload.get("product", "marriage"), payload)
    pdf = delivery.html_to_pdf(html)
    if not pdf:
        return HTMLResponse(
            f"<p style='font-family:sans-serif;padding:40px'>PDF banane ke liye report "
            f"kholiye aur 'Download PDF' (print) dabaiye. <a href='/report/{rid}'>Report</a></p>")
    name = (payload.get("meta", {}).get("name") or "report").replace(" ", "_")[:40]
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition":
                             f'attachment; filename="Axtroshastra_{name}.pdf"'})


if DEMO_MODE:                                    # never set DEMO_MODE=1 in production
    @app.post("/api/_demo_pay/{rid}")
    def demo_pay(rid: str):
        if not get_report(rid): raise HTTPException(404, "report not found")
        mark_paid(rid, payment_id="demo")
        return {"ok": True}



class MilanIn(BaseModel):
    p1_name: str; p1_dob: str; p1_tob: str | None = None; p1_place: str
    p2_name: str; p2_dob: str; p2_tob: str | None = None; p2_place: str
    variant: str | None = None
    email: str | None = None
    captcha_token: str | None = None

@app.post("/api/milan")
def create_milan(inp: MilanIn):
    if not captcha_ok(inp.captcha_token or "", ""):   # (#4)
        raise HTTPException(400, "captcha_failed")
    lat1, lon1, tz1 = geocode(inp.p1_place)
    lat2, lon2, tz2 = geocode(inp.p2_place)
    report = compute_milan(
        {"name": inp.p1_name, "dob": inp.p1_dob, "tob": inp.p1_tob,
         "tz": tz1, "lat": lat1, "lon": lon1},
        {"name": inp.p2_name, "dob": inp.p2_dob, "tob": inp.p2_tob,
         "tz": tz2, "lat": lat2, "lon": lon2})
    report["meta"]["variant"] = (inp.variant or "direct")[:64]
    if inp.email:
        report["meta"]["_email"] = inp.email             # (#7)
    rid = secrets.token_urlsafe(12)
    save_report(rid, report)
    return {"report_id": rid, "teaser": report["teaser"]}


@app.get("/static/{fname}", include_in_schema=False)
def static_file(fname: str):
    if not fname.replace("-", "").replace(".", "").replace("_", "").isalnum():
        raise HTTPException(404, "not found")
    path = os.path.join(BASE, "static", fname)
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(404, "not found")


@app.get("/blog", include_in_schema=False)
def blog_index():
    return FileResponse(os.path.join(BASE, "pages", "blog", "index.html"))


@app.get("/blog/{slug}", include_in_schema=False)
def blog_post(slug: str):
    if not slug.replace("-", "").isalnum():
        raise HTTPException(404, "not found")
    path = os.path.join(BASE, "pages", "blog", f"{slug}.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(404, "not found")


BLOG_SLUGS = ["shaadi-kab-hogi-marriage-timing", "manglik-dosha-cancellation",
              "kundli-milan-36-gun", "birth-time-nahi-pata-chandra-lagna",
              "vimshottari-dasha-life-phases"]

@app.get("/sitemap.xml", include_in_schema=False)
def sitemap():
    base_url = PUBLIC_BASE_URL or "https://www.axtroshastra.com"
    urls = ["/", "/shaadi", "/milan", "/jeevan", "/match", "/career", "/blog",
            "/about", "/login", "/privacy", "/terms", "/refunds"
            ] + [f"/blog/{s}" for s in BLOG_SLUGS]
    body = "".join(f"<url><loc>{base_url}{u}</loc></url>" for u in urls)
    return Response(content='<?xml version="1.0" encoding="UTF-8"?>'
                    f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>',
                    media_type="application/xml")


@app.get("/robots.txt", include_in_schema=False)
def robots():
    base_url = PUBLIC_BASE_URL or "https://www.axtroshastra.com"
    return PlainTextResponse(f"User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /report/\nDisallow: /account\nSitemap: {base_url}/sitemap.xml")


@app.get("/api/count")
def public_count():
    """Honest aggregate report count for the live counter. Hidden below 50."""
    with db() as c:
        n = c.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    return {"count": (n // 10) * 10 if n >= 50 else 0}


@app.get("/api/make_pass")
def make_pass(key: str = "", n: int = 5):
    """Generate one-time free-unlock tokens for the soft launch."""
    if not _valid_admin_key(key):
        raise HTTPException(403, "forbidden")
    n = max(1, min(n, 30))
    toks = []
    with _lock, db() as conn:
        for _ in range(n):
            t = secrets.token_urlsafe(8)
            conn.execute("INSERT INTO passes(token, created_at) VALUES(?,?)",
                         (t, datetime.utcnow().isoformat()))
            toks.append(t)
    base = PUBLIC_BASE_URL or ""
    return {"passes": toks,
            "example_links": [f"{base}/shaadi?pass={toks[0]}",
                              f"{base}/milan?pass={toks[0]}",
                              f"{base}/match?pass={toks[0]}",
                              f"{base}/jeevan?pass={toks[0]}",
                              f"{base}/career?pass={toks[0]}"],
            "note": "Each token unlocks exactly ONE report, on any product page."}


@app.get("/api/backfill_users")
def backfill_users(key: str = "", limit: int = 5000):
    """One-time (idempotent) admin action: create + link accounts for reports that
    were paid before the accounts code shipped — paid, with a phone on file, but no
    linked user. Safe to re-run. Gated by STATS_KEY."""
    if not _valid_admin_key(key):
        raise HTTPException(403, "forbidden")
    return users.backfill(db, limit)


@app.get("/api/stats")
def stats(key: str = ""):
    """Per-variant funnel counts. Protect with STATS_KEY env var."""
    if not _valid_admin_key(key):
        raise HTTPException(403, "forbidden")
    with db() as c:
        rows = c.execute(
            """SELECT COALESCE(json_extract(payload,'$.meta.variant'),'direct') v,
                      COUNT(*), SUM(paid) FROM reports GROUP BY v"""
        ).fetchall()
    return {"variants": [{"page": r[0], "kundlis_created": r[1],
                          "paid_reports": r[2] or 0,
                          "revenue_inr": (r[2] or 0) * 499} for r in rows]}


# ----------------------------------------------------------------- auth (OTP)
def _render_account(user: dict, reports: list) -> str:
    """Server-rendered post-login dashboard: saved account details from the DB +
    a card per past paid report. Styled inline in the site's design system so it
    needs no template file and is safe to gate entirely server-side."""
    import html as _html
    name = _html.escape(user.get("name") or "there")
    mobile = _html.escape(_fmt_mobile(user.get("mobile") or ""))
    email = _html.escape(user.get("email") or "")
    city = _html.escape(user.get("city") or "")

    def _detail(label, value):
        if not value:
            return ""
        return (f'<div class="row"><span class="k">{label}</span>'
                f'<span class="v">{value}</span></div>')

    details = (_detail("Name", name if name != "there" else "")
               + _detail("Mobile", mobile) + _detail("Email", email)
               + _detail("City", city)) or \
        '<div class="row"><span class="v" style="color:#8a7d72">No extra details on ' \
        'file yet.</span></div>'

    if reports:
        cards = ""
        for r in reports:
            label = _html.escape(PRODUCT_LABEL.get(r["product"], "Report"))
            subject = _html.escape(r.get("subject") or "")
            date = _html.escape((r.get("created_at") or "")[:10])
            sub = f'<div class="rp-sub">{subject}</div>' if subject else ""
            cards += (f'<a class="rp-card" href="/report/{r["id"]}">'
                      f'<div class="rp-top"><span class="rp-label">{label}</span>'
                      f'<span class="rp-date">{date}</span></div>{sub}'
                      f'<span class="rp-cta">View report &rarr;</span></a>')
        reports_block = f'<div class="rp-list">{cards}</div>'
    else:
        reports_block = ('<div class="empty">You have no reports yet. '
                         '<a href="/">Get your first report &rarr;</a></div>')

    return f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>My Account — Axtroshastra</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 24 24%27%3E%3Crect width=%2724%27 height=%2724%27 rx=%275%27 fill=%27%23151C39%27/%3E%3Cpath d=%27M12 3 L14.2 9.8 L21 12 L14.2 14.2 L12 21 L9.8 14.2 L3 12 L9.8 9.8 Z%27 fill=%27%23E4B04A%27/%3E%3C/svg%3E">
<meta name="robots" content="noindex">
<style>
:root{{--ink:#23253B;--midnight:#151C39;--paper:#FAF6ED;--sindoor:#C93B2E;
--haldi:#E4B04A;--muted:#6B6D82;--line:#E7E0D2;
--body:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:var(--body);background:var(--paper);color:var(--ink);line-height:1.55}}
.wrap{{max-width:620px;margin:0 auto;padding:0 20px 60px}}
.hero{{background:radial-gradient(900px 460px at 50% -10%,#1D2547,var(--midnight) 60%);
color:#F3EFE4;padding:40px 0 30px}}
.hero .wrap{{padding-bottom:0}}
.eyebrow{{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--haldi);
font-weight:700}}
.hero h1{{font-size:28px;margin-top:8px;color:#fff}}
.hero p{{color:#B9BBD0;margin-top:6px;font-size:15px}}
.card{{background:#fff;border:1px solid var(--line);border-radius:14px;padding:18px 18px 14px;
margin-top:20px;box-shadow:0 2px 10px rgba(70,50,30,.05)}}
.card h2{{font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);
margin-bottom:12px;font-weight:700}}
.row{{display:flex;gap:12px;padding:9px 0;border-top:1px solid #f0eadd;font-size:15px}}
.row:first-of-type{{border-top:0}}
.row .k{{color:var(--muted);width:70px;flex:0 0 auto;font-size:13px;padding-top:1px}}
.row .v{{font-weight:600}}
.rp-list{{display:grid;gap:12px;margin-top:14px}}
.rp-card{{display:block;background:#fff;border:1px solid var(--line);border-radius:14px;
padding:15px 16px;text-decoration:none;color:var(--ink);box-shadow:0 2px 10px rgba(70,50,30,.05)}}
.rp-card:active{{transform:scale(.995)}}
.rp-top{{display:flex;justify-content:space-between;align-items:center}}
.rp-label{{font-weight:700;font-size:15.5px}}
.rp-date{{color:var(--muted);font-size:12.5px}}
.rp-sub{{color:var(--muted);font-size:13.5px;margin-top:2px}}
.rp-cta{{display:inline-block;margin-top:8px;color:var(--sindoor);font-weight:700;font-size:14px}}
.empty{{margin-top:14px;color:var(--muted);font-size:15px}}
.empty a,.rp-cta{{color:var(--sindoor)}}
.section-title{{margin-top:26px;font-size:13px;letter-spacing:.08em;text-transform:uppercase;
color:var(--muted);font-weight:700}}
.logout{{display:inline-block;margin-top:24px;background:none;border:1px solid var(--line);
color:var(--muted);border-radius:10px;padding:10px 16px;font-size:14px;cursor:pointer;
font-family:inherit}}
</style></head><body>
<div class="hero"><div class="wrap">
<div class="eyebrow">My Account</div>
<h1>Namaste, {name} 🙏</h1>
<p>Your saved details and reports, all in one place.</p>
</div></div>
<div class="wrap">
<div class="card"><h2>Your Details</h2>{details}</div>
<div class="section-title">Your Reports</div>
{reports_block}
<button class="logout" onclick="logout()">Log out</button>
</div>
<script>
async function logout(){{
  try{{ await fetch('/api/auth/logout',{{method:'POST'}}); }}catch(e){{}}
  location.href='/';
}}
</script>
</body></html>"""


class OtpRequestIn(BaseModel):
    mobile: str
    captcha_token: str | None = None

class OtpVerifyIn(BaseModel):
    mobile: str
    code: str


def _set_session_cookie(resp, token: str):
    resp.set_cookie(auth.SESSION_COOKIE, token, max_age=auth.SESSION_TTL_DAYS * 86400,
                    httponly=True, samesite="lax", secure=auth.cookie_secure(), path="/")


def _current_user(request: Request):
    return auth.user_for_session(db, request.cookies.get(auth.SESSION_COOKIE, ""))


@app.post("/api/auth/request-otp")
def auth_request_otp(body: OtpRequestIn, request: Request):
    """Send a login OTP to the given mobile (WhatsApp via Twilio Verify by default).
    Always returns ok for a plausible number so we don't leak who has an account;
    a real delivery failure is the only thing that flips ok to False."""
    if not captcha_ok(body.captcha_token):
        raise HTTPException(400, "captcha failed")
    res = auth.send_otp(db, body.mobile)
    if not res.get("ok"):
        raise HTTPException(400 if res.get("error") == "invalid_mobile" else 503,
                            res.get("error", "send_failed"))
    out = {"ok": True, "channel": res.get("channel")}
    if "dev_code" in res:          # only present in DEMO_MODE + dev fallback
        out["dev_code"] = res["dev_code"]
    return out


@app.post("/api/auth/verify-otp")
def auth_verify_otp(body: OtpVerifyIn):
    """Verify the OTP, create/fetch the account, mint a session cookie."""
    token, user = auth.login(db, body.mobile, body.code)
    if not token:
        raise HTTPException(401, "invalid or expired code")
    resp = JSONResponse({"ok": True, "user": user})
    _set_session_cookie(resp, token)
    return resp


@app.post("/api/auth/logout")
def auth_logout(request: Request):
    auth.destroy_session(db, request.cookies.get(auth.SESSION_COOKIE, ""))
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(auth.SESSION_COOKIE, path="/")
    return resp


@app.get("/api/me")
def auth_me(request: Request):
    """Current logged-in user + their paid reports, or 401 if no valid session."""
    user = _current_user(request)
    if not user:
        raise HTTPException(401, "not logged in")
    return {"user": user, "reports": users.get_user_reports(db, user["id"])}


@app.get("/login", include_in_schema=False)
def login_page(request: Request):
    if _current_user(request):
        return RedirectResponse("/account", status_code=302)
    path = os.path.join(PAGES_DIR, "login.html")
    if os.path.exists(path):
        return _serve_page_with_nav(path)
    raise HTTPException(404, "not found")


@app.get("/account", include_in_schema=False)
def account_page(request: Request):
    """Post-login dashboard: the user's saved details + their past reports.
    Redirects to /login when there's no valid session."""
    user = _current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    reports = users.get_user_reports(db, user["id"])
    return HTMLResponse(_inject_nav(_render_account(user, reports)))


extensions.install(app, {                      # (#6)(#7)(#8)(#9) feature endpoints
    "db": db, "get_report": get_report,
    "render": _render_for, "valid_admin_key": _valid_admin_key,
})


@app.get("/padhai", include_in_schema=False)
def padhai_redirect(request: Request):
    """Legacy /padhai → /career (301 permanent). Preserves query string so
    already-issued unlock links like /padhai?pass=<token> keep working."""
    q = request.url.query
    return RedirectResponse("/career" + (f"?{q}" if q else ""), status_code=301)


@app.get("/hinglish/{slug}", include_in_schema=False)
def serve_page_hinglish(slug: str):
    """Serve the Hinglish variant pages/<slug>.hinglish.html (e.g. /hinglish/career).
    English is the default at /<slug>; this is the parallel Hinglish route."""
    if not slug.replace("-", "").isalnum():
        raise HTTPException(404, "not found")
    path = os.path.join(PAGES_DIR, f"{slug}.hinglish.html")
    if os.path.exists(path):
        return _serve_page_with_nav(path)
    raise HTTPException(404, "not found")


@app.get("/{slug}", include_in_schema=False)
def serve_page(slug: str):
    """Serve pages/<slug>.html — every file in pages/ becomes a landing page."""
    if not slug.replace("-", "").isalnum():
        raise HTTPException(404, "not found")
    path = os.path.join(PAGES_DIR, f"{slug}.html")
    if os.path.exists(path):
        return _serve_page_with_nav(path)
    raise HTTPException(404, "not found")
