"""
Axtroshastra API — production wiring.

POST /api/kundli      : compute FULL report server-side, store, return TEASER only
POST /api/order       : create LIVE Razorpay order bound to report_id
POST /api/webhook     : payment.captured -> mark paid (HMAC-verified, source of truth)
POST /api/verify      : client-side fallback — verify Razorpay signature & mark paid
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
import hashlib, hmac, json, logging, os, secrets, sqlite3, threading, time
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
import dbcompat
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse,
                               PlainTextResponse, RedirectResponse, Response)
from pydantic import BaseModel, Field, field_validator

from engine import compute_report
from report_view import render_report, render_milan, render_blueprint, render_vidyarthi, north_chart_svg
from report_view_v2 import render_report_v2   # marriage report v2 (4-tier, LLM-narrated)
from products import compute_milan, compute_blueprint
from vidyarthi import compute_vidyarthi_report
from geocoding import resolve as geocode          # (#1) accurate, cached geocoding
from geocoding import resolve_detailed             # (#1) with resolved/source provenance
import payments, delivery, extensions
import pdfgen                # browser-quality PDF: pre-generated at payment, cached
import users                 # account layer: create/link a user at payment time
import auth                  # OTP login + session layer (Twilio Verify)
import narrative             # optional LLM prose layer (Claude/OpenAI), off by default
import tracking              # server-side Purchase -> Meta CAPI + GA4 MP, env-gated OFF
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
TWILIO_CONTENT_SID = os.getenv("TWILIO_CONTENT_SID", "")  # approved MEDIA template (PDF attached)
TWILIO_CONTENT_SID_TEXT = os.getenv("TWILIO_CONTENT_SID_TEXT", "")  # approved TEXT template — fallback when the PDF isn't ready

PRODUCT_LABEL = {"marriage": "Marriage Timing", "milan": "Compatibility Report",
                  "blueprint": "Life Blueprint", "vidyarthi": "Career & Academic Timing"}

# Visual identity per product for the account dashboard cards. Minimal gold
# line-art SVGs (one consistent set, stroke #E4B04A, weight ~1.5), sitting on a
# unified navy header — products differ by ICON, not by band colour. Inlined so
# there are no external files/deps and no heavy PDF-thumbnail work.
_SVG_OPEN = ('<svg viewBox="0 0 32 32" fill="none" stroke="#E4B04A" '
             'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" '
             'aria-hidden="true">')
PRODUCT_SVG = {
    # marriage — a solitaire band: ring hoop with a diamond above.
    "marriage": _SVG_OPEN + '<circle cx="16" cy="20.5" r="7"/>'
                '<path d="M12 12 L16 6 L20 12 L16 15 Z"/>'
                '<path d="M12 12 H20"/></svg>',
    # compatibility (milan) — two interlocking rings.
    "milan": _SVG_OPEN + '<circle cx="12.5" cy="16" r="6.5"/>'
             '<circle cx="19.5" cy="16" r="6.5"/></svg>',
    # life blueprint (jeevan) — a lit diya: bowl with a flame.
    "blueprint": _SVG_OPEN + '<path d="M6 20 H26 Q16 27 6 20 Z"/>'
                 '<path d="M16 19 C12.5 15 16 12 16 8 C16 12 19.5 15 16 19 Z"/></svg>',
    # career (vidyarthi) — a graduation cap with tassel.
    "vidyarthi": _SVG_OPEN + '<path d="M4 13 L16 8 L28 13 L16 18 Z"/>'
                 '<path d="M9 15 V21 Q16 24 23 21 V15"/>'
                 '<path d="M28 13 V20.5"/><circle cx="28" cy="21.5" r="1"/></svg>',
}

def _display_name(payload: dict) -> str:
    """Safe display name for any product. Milan reports have meta.p1/p2 and NO
    meta.name — indexing meta['name'] crashed the webhook mid-way for every
    milan payment (paid got marked, but user creation / WhatsApp / email never
    ran). Always use this instead of meta['name']."""
    meta = (payload or {}).get("meta") or {}
    if meta.get("name"):
        return meta["name"]
    if meta.get("p1") and meta.get("p2"):
        return f"{meta['p1']} & {meta['p2']}"
    return "ji"


def _pdf_is_fetchable(rid: str) -> bool:
    """Is the report PDF actually downloadable from the PUBLIC url right now?

    Twilio fetches the media URL ITSELF when sending a media template. A PDF
    cached on this server instance does NOT prove the public url serves it (a
    cold/other instance, or a renderer hiccup, makes the fetch fail) — and when
    it fails, the WhatsApp media message fails asynchronously with Twilio 63019
    ("media failed to download") and the customer receives NOTHING. So probe the
    same public .pdf url the approved media template builds before betting the
    whole message on the attachment. Never raises → False on any doubt."""
    if not PUBLIC_BASE_URL:
        return False
    url = f"{PUBLIC_BASE_URL}/report/{rid}.pdf"
    try:
        import urllib.request
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=8) as r:
            ctype = (r.headers.get("Content-Type") or "").lower()
            return getattr(r, "status", 200) == 200 and "pdf" in ctype
    except Exception as e:
        logger.warning("[twilio] PDF not publicly fetchable for %s (%s) — "
                       "sending the link template instead", rid, e)
        return False


def _mark_sent(rid: str):
    """Auto-record 'sent' in dash_delivery so the dashboard doesn't show 'pending'
    for reports that Twilio actually accepted."""
    try:
        from dashboard.store import set_status
        set_status(db, rid, "sent", "auto: Twilio accepted")
    except Exception:
        pass


def send_whatsapp_report(phone: str, rid: str, name: str, product: str = "marriage"):
    """Fire-and-forget WhatsApp delivery after payment. Never raises.

    One message, three things (owner spec): the report PDF attached (when the
    pre-generated file exists — see _pregenerate_pdf_task), account-created
    confirmation, and the login URL. Falls back to the report link when the
    PDF isn't ready so account info always reaches the user."""
    if not (TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM and phone and PUBLIC_BASE_URL):
        return
    try:
        from twilio.rest import Client
        to = phone if phone.startswith("+") else "+91" + phone[-10:]
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        link = f"{PUBLIC_BASE_URL}/report/{rid}"
        login = f"{PUBLIC_BASE_URL}/login"
        label = PRODUCT_LABEL.get(product, "Marriage Timing")
        # Attach the pre-generated PDF when it exists. Twilio fetches media by
        # URL; /report/{rid}/pdf serves the cached file (report is paid here).
        media = [f"{PUBLIC_BASE_URL}/report/{rid}/pdf"] if pdfgen.get_cached(rid) else None
        # A cached PDF is NOT enough to attach it: Twilio downloads the media url
        # itself, and a cache that isn't publicly downloadable makes the media
        # template fail asynchronously (63019) with the customer getting NOTHING.
        # Only attach when the public .pdf url actually serves the file; otherwise
        # fall through to the reliable link template. The PDF stays on-site either
        # way. (media is falsy already when no PDF was generated → skip the probe.)
        media_ok = bool(media) and _pdf_is_fetchable(rid)
        if TWILIO_CONTENT_SID and media_ok:          # production: approved MEDIA template
            # Approved media template (document header):
            #   {{1}} customer name
            #   {{2}} login URL
            #   {{3}} report id ONLY — the template's media url is
            #         https://www.axtroshastra.com/report/{{3}}.pdf (the trailing
            #         .pdf is required: Twilio rejects a media url with no file
            #         extension, and Meta rejects a variable at the very end).
            #         So pass ONLY the rid here, never a path.
            #   NOTE: TWILIO_CONTENT_SID must point at this .pdf-shaped template.
            client.messages.create(
                from_=TWILIO_FROM, to=f"whatsapp:{to}",
                content_sid=TWILIO_CONTENT_SID,
                content_variables=json.dumps(
                    {"1": name, "2": login, "3": rid}))
        elif TWILIO_CONTENT_SID_TEXT:                # approved TEXT template (report link)
            # No media-download risk → delivery is guaranteed; the PDF stays
            # available on-site. This is the default whenever the PDF can't be
            # verified as publicly downloadable (the 63019 fix).
            client.messages.create(
                from_=TWILIO_FROM, to=f"whatsapp:{to}",
                content_sid=TWILIO_CONTENT_SID_TEXT,
                content_variables=json.dumps({"1": name, "2": link}))
        elif TWILIO_CONTENT_SID:                      # only the media template is configured
            # Last resort: nothing else to fall back to. Attach only if verified
            # fetchable, else send the media template without betting on the PDF.
            client.messages.create(
                from_=TWILIO_FROM, to=f"whatsapp:{to}",
                content_sid=TWILIO_CONTENT_SID,
                content_variables=json.dumps(
                    {"1": name, "2": login, "3": rid}))
        else:                                        # sandbox / 24h session freeform
            kwargs = {"media_url": media} if media_ok else {}
            body = (f"Namaste {name}! 🙏 Aapki Axtroshastra {label} Report "
                    + ("attached hai (PDF) 📄" if media_ok else f"ready hai:\n{link}")
                    + f"\n\n✅ Aapka account ban gaya hai is number par."
                    + f"\nLogin anytime → {login}"
                    + "\n\nKoi bhi sawaal ho — bas reply kijiye.")
            client.messages.create(from_=TWILIO_FROM, to=f"whatsapp:{to}",
                                   body=body, **kwargs)
        _mark_sent(rid)
    except Exception as e:                            # delivery must never break the webhook
        logger.error("[twilio] send failed for %s: %s", rid, e)


def _full_report_html(payload: dict) -> str:
    """The exact HTML a user sees at /report/{rid} (milan v2 when applicable) —
    used for PDF rendering so the print output matches the on-screen report
    (action bars are print-hidden via CSS)."""
    if payload.get("product") == "milan":
        try:
            import milan_v2
            html = milan_v2.render_milan_v2(payload)
            if (payload.get("meta") or {}).get("lang") == "hi":
                import milan_hi
                html = milan_hi.localize(html)
            return html
        except Exception as e:
            logger.error("[v2] render failed for pdf: %s", e)      # fall through
    return _render_for(payload.get("product", "marriage"), payload)


def _pregenerate_pdf_task(rid: str):
    """Background task after payment: render the browser-quality PDF once and
    cache it, so the download button and the WhatsApp attachment are instant.
    Never raises; on failure the client falls back to the print dialog."""
    try:
        rec = get_report(rid)
        if not rec or not rec["paid"]:
            return
        payload = _refresh_current_period(rec["payload"])
        payload.setdefault("meta", {})["report_id"] = rid
        data = pdfgen.get_or_generate(rid, _full_report_html(payload))
        logger.info("[pdf] pregenerate %s -> %s", rid, "ok" if data else "FAILED")
    except Exception as e:
        logger.error("[pdf] pregenerate task failed for %s: %s", rid, e)

def _render_for(product, payload):
    if product == "milan":
        html = render_milan(payload)
        # v1 fallback path (?v2=0 or a v2 render failure): a Hindi buyer must
        # still get Devanagari — the v1 base is Hinglish and used to ship raw.
        if (payload.get("meta") or {}).get("lang") == "hi":
            try:
                import milan_hi
                html = milan_hi.localize(html)
            except Exception as e:
                logger.error("[milan_hi] v1 localize failed: %s", e)
        return html
    if product == "blueprint":
        return render_blueprint(payload)
    if product == "vidyarthi":
        return render_vidyarthi(payload)
    html = render_report_v2(payload)
    # Devanagari marriage report for the /hi/marriage funnel (deterministic localizer)
    if (payload.get("meta") or {}).get("lang") == "hi":
        try:
            import shaadi_hi
            html = shaadi_hi.localize(html)
        except Exception as e:
            logger.error("[shaadi_hi] localize failed: %s", e)
    return html


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
MILAN_PRICE_PAISE = 49900                 # ₹499 — milan landing price (/milan and /match funnels)
_MILAN_VARIANTS = ("/milan", "/match", "/en/compatibility", "/hi/compatibility")


def _order_amount_paise(rec: dict) -> int:
    """The price actually charged for a report, by funnel variant. Single source
    for both order creation and the server-side purchase-tracking value."""
    variant = ((rec.get("payload") or {}).get("meta") or {}).get("variant") or ""
    return MILAN_PRICE_PAISE if variant in _MILAN_VARIANTS else PRICE_PAISE


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
        row = c.execute(
            "SELECT payload,paid,order_id,phone,user_phone FROM reports WHERE id=?",
            (rid,)).fetchone()
    if not row: return None
    return {"payload": json.loads(row[0]), "paid": bool(row[1]), "order_id": row[2],
            "phone": row[3] or "", "user_phone": row[4] or ""}

def set_order(rid, order_id):
    with _lock, db() as c:
        c.execute("UPDATE reports SET order_id=? WHERE id=?", (order_id, rid))

def mark_paid(rid, payment_id=None, phone=None):
    with _lock, db() as c:
        c.execute("UPDATE reports SET paid=1,payment_id=?,phone=? WHERE id=?",
                  (payment_id, phone, rid))

def store_user_contact(rid, phone=None, email=None):
    """Persist the contact typed into the pre-payment popup.

    * reports.user_phone <- normalised popup mobile: this is the user's
      WhatsApp/account number, used for report delivery + OTP login. It is
      deliberately SEPARATE from reports.phone, which stays whatever contact
      Razorpay reports for the payment (mark_paid, unchanged).
    * meta._email <- popup email, only when the report doesn't already carry
      one (that key is what email delivery reads)."""
    user_phone = users._norm_mobile(phone or "")
    email = (email or "").strip()
    with _lock, db() as c:
        if user_phone:
            c.execute("UPDATE reports SET user_phone=? WHERE id=?",
                      (user_phone, rid))
        if email:
            row = c.execute("SELECT payload FROM reports WHERE id=?",
                            (rid,)).fetchone()
            if row:
                payload = json.loads(row[0])
                meta = payload.setdefault("meta", {})
                if not meta.get("_email"):
                    meta["_email"] = email
                    c.execute("UPDATE reports SET payload=? WHERE id=?",
                              (json.dumps(payload), rid))
    return user_phone

def _store_attribution(rid, fbc=None, fbp=None, ua="", ip=""):
    """Persist Meta attribution cookies + request context in the report payload
    so the server-side CAPI fire (webhook / verify) can forward them."""
    fbc = (fbc or "").strip()
    fbp = (fbp or "").strip()
    ua = (ua or "").strip()
    ip = (ip or "").strip()
    if not (fbc or fbp or ua or ip):
        return
    with _lock, db() as c:
        row = c.execute("SELECT payload FROM reports WHERE id=?", (rid,)).fetchone()
        if not row:
            return
        payload = json.loads(row[0])
        meta = payload.setdefault("meta", {})
        if fbc:
            meta["_fbc"] = fbc
        if fbp:
            meta["_fbp"] = fbp
        if ua:
            meta["_ua"] = ua
        if ip:
            meta["_ip"] = ip
        c.execute("UPDATE reports SET payload=? WHERE id=?",
                  (json.dumps(payload), rid))

def save_narrative(rid, narr: dict):
    """Merge the LLM-written prose into the stored report payload so the renderer
    can read it (payload['narrative']). Re-reads the row under the lock so we don't
    clobber a concurrent update, and is a no-op for empty output."""
    if not narr:
        return
    with _lock, db() as c:
        row = c.execute("SELECT payload FROM reports WHERE id=?", (rid,)).fetchone()
        if not row:
            return
        payload = json.loads(row[0])
        payload["narrative"] = narr
        c.execute("UPDATE reports SET payload=? WHERE id=?",
                  (json.dumps(payload), rid))

def _generate_narrative_task(rid):
    """Background: turn the computed report into creative prose and cache it on the
    payload. Env-gated inside narrative.generate_narrative (no-op when disabled);
    never raises, so it can't affect payment/delivery."""
    try:
        rec = get_report(rid)
        if rec:
            save_narrative(rid, narrative.generate_narrative(rec["payload"]))
            if narrative.last_generation:
                try:
                    from dashboard.store import llm_log_add
                    llm_log_add(db, rid, narrative.last_generation)
                except Exception:
                    pass
    except Exception as e:
        logger.error("[narrative] task failed for %s: %s", rid, e)

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
    ("Home", "/"),
    ("Login / My Account", "/account"),
    ("About Us", "/about"),
    ("Privacy Policy", "/privacy"),
    ("Terms of Use", "/terms"),
    ("Blogs", "/blog"),
]
# Devanagari nav for /hi/* pages. Only "Home" changes destination (-> /hi, the
# Hindi homepage) so navigation stays in-language; the support pages are
# English-only for now, so their links still point at the English versions.
NAV_LINKS_HI = [
    ("होम", "/hi"),
    ("लॉगिन / मेरा अकाउंट", "/account"),
    ("हमारे बारे में", "/about"),
    ("प्राइवेसी पॉलिसी", "/privacy"),
    ("नियम व शर्तें", "/terms"),
    ("ब्लॉग", "/blog"),
]

def _nav_html(lang: str = "en") -> str:
    links = NAV_LINKS_HI if lang == "hi" else NAV_LINKS
    menu = "मेन्यू" if lang == "hi" else "Menu"
    items = "".join(
        f'<a href="{href}" class="axs-nav-item">{label}</a>' for label, href in links
    )
    return (
        '<div id="axs-nav">'
        '<button class="axs-nav-btn" aria-label="Menu" '
        'onclick="document.getElementById(\'axs-nav\').classList.toggle(\'open\')">'
        '<span></span><span></span><span></span></button>'
        '<div class="axs-nav-backdrop" '
        'onclick="document.getElementById(\'axs-nav\').classList.remove(\'open\')"></div>'
        '<nav class="axs-nav-panel">'
        f'<div class="axs-nav-head">{menu}</div>'
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

def _inject_nav(html: str, lang: str = "en") -> str:
    """Insert the hamburger nav right after the opening <body> tag. If for some
    reason there's no <body>, return the html unchanged (never break a page)."""
    import re
    nav = _nav_html(lang)
    new_html, n = re.subn(r"(<body[^>]*>)", lambda m: m.group(1) + nav,
                          html, count=1, flags=re.IGNORECASE)
    return new_html if n else html


# Single source for the GA4 + Meta Pixel + Microsoft Clarity <head> block. The
# static marketing pages under pages/*.html embed this exact snippet by hand;
# the pages we build/serve in Python (the report page, /account, /login) never
# had it, so those were invisible to all three trackers. _inject_tracking below
# adds it to those — idempotently, so a page that already carries it is skipped
# and never double-fires. Keep the three IDs in sync with the pages/*.html copy.
_TRACKING_HEAD = """
<!-- Analytics (injected server-side for pages without the hardcoded block) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-NKRQM1HJ97"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', 'G-NKRQM1HJ97');
</script>
<script>
!function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;
n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,
document,'script','https://connect.facebook.net/en_US/fbevents.js');
fbq('init', '2417544725436982');
fbq('track', 'PageView');
</script>
<script type="text/javascript">
(function(c,l,a,r,i,t,y){
    c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
    t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
    y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
})(window, document, "clarity", "script", "xkbm56cwzh");
</script>
"""


def _inject_tracking(html: str) -> str:
    """Add GA4 + Meta Pixel + Clarity to a page's <head> when it isn't already
    there. Idempotent: skips any page already loading the Clarity tag, so the
    hardcoded pages/*.html copies are left untouched (no double page_view /
    PageView). Inserts before </head>; if a page somehow has no </head>, falls
    back to just after <body> so tracking still loads. Never raises."""
    try:
        if not html or "clarity.ms/tag" in html:
            return html
        import re
        new_html, n = re.subn(r"(</head>)", lambda m: _TRACKING_HEAD + m.group(1),
                              html, count=1, flags=re.IGNORECASE)
        if n:
            return new_html
        new_html, n = re.subn(r"(<body[^>]*>)", lambda m: m.group(1) + _TRACKING_HEAD,
                              html, count=1, flags=re.IGNORECASE)
        return new_html if n else html
    except Exception as e:
        logger.error("[tracking] injection failed: %s", e)
        return html


def _serve_page_with_nav(path: str, lang: str = "en"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return HTMLResponse(_inject_tracking(_inject_nav(f.read(), lang)))
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


@app.get("/api/otp/health", include_in_schema=False)
def otp_health(key: str = ""):
    """Admin: verify the active OTP provider's credentials WITHOUT sending an SMS.
    For Message Central this mints (or reuses) an auth token, proving customerId +
    password/token are accepted; 503 if they aren't. Gated by STATS_KEY. Returns no
    secrets — safe to hit after a deploy to confirm the login OTP path is live."""
    if not _valid_admin_key(key):
        raise HTTPException(403, "forbidden")
    status = auth.provider_health()
    return JSONResponse(status, status_code=200 if status.get("ok") else 503)


@app.get("/", include_in_schema=False)
def landing():
    """English homepage."""
    for candidate in ("home.html", "shaadi.html"):
        path = os.path.join(PAGES_DIR, candidate)
        if os.path.exists(path):
            return _serve_page_with_nav(path, lang="en")
    return HTMLResponse("<h3 style='font-family:sans-serif;padding:40px'>Axtroshastra</h3>")


@app.get("/hi", include_in_schema=False)
def landing_hi():
    """Hindi (Devanagari) homepage — nav Home points back here to stay in-language."""
    path = os.path.join(PAGES_DIR, "home.hi.html")
    if os.path.exists(path):
        return _serve_page_with_nav(path, lang="hi")
    return RedirectResponse("/", status_code=302)


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
    # per-locale report language (Devanagari for /hi/* funnels); mirrors milan.
    report["meta"]["lang"] = "hi" if (inp.variant or "").startswith("/hi/") else "english"
    report["meta"]["geo_source"] = geo_source
    try:
        if report.get("chart"):
            report["teaser"]["chart_svg"] = north_chart_svg(report)
    except Exception:
        pass         # (#1) provenance

    report["meta"]["_birth"] = {"dob": inp.dob, "tob": tob, "tz": tz,
                                "lat": lat, "lon": lon,
                                "place": inp.place}   # (#8) for /api/deep + report cover
    # note: birth details live under the underscore-prefixed _birth so narrative.py's
    # PII scrub keeps them out of the LLM payload; the report cover reads them here.
    if inp.email:
        report["meta"]["_email"] = inp.email             # (#7)
    rid = secrets.token_urlsafe(12)
    save_report(rid, report)
    return {"report_id": rid, "teaser": report["teaser"]}


class OrderIn(BaseModel):
    """Body of POST /api/order. `phone`/`email` come from the pre-payment
    contact popup: phone is the buyer's WhatsApp/account number (stored in
    reports.user_phone), email feeds meta._email for the PDF copy.
    `fbc`/`fbp` are the Meta click/browser cookies forwarded by the checkout
    JS so the server-side CAPI Purchase can attribute to the right ad click."""
    report_id: str | None = None
    pass_token: str | None = Field(default=None, alias="pass")
    phone: str | None = None
    email: str | None = None
    fbc: str | None = None
    fbp: str | None = None
    model_config = {"populate_by_name": True, "extra": "ignore"}


@app.post("/api/order")
def create_order(body: OrderIn, request: Request, background_tasks: BackgroundTasks):
    rid = body.report_id
    rec = get_report(rid)
    if not rec: raise HTTPException(404, "report not found")
    # Persist the popup contact FIRST — even for retries/free passes — so the
    # webhook/verify can prefer the typed WhatsApp number over the Razorpay
    # payment contact. Never let it break order creation.
    user_phone = rec.get("user_phone") or ""
    if body.phone or body.email:
        try:
            user_phone = store_user_contact(rid, body.phone, body.email) or user_phone
        except Exception as e:
            logger.error("[contact] persist failed for %s: %s", rid, e)
    # Persist Meta attribution data (fbc/fbp cookies + UA/IP) so the CAPI
    # Purchase fired from the webhook/verify path can attribute to the ad click.
    try:
        _store_attribution(rid, body.fbc, body.fbp,
                           request.headers.get("user-agent", ""),
                           request.headers.get("x-forwarded-for", "").split(",")[0].strip()
                           or request.client.host)
    except Exception as e:
        logger.error("[attribution] persist failed for %s: %s", rid, e)
    if rec["paid"]:                              # already paid -> skip checkout
        return {"already_paid": True}
    tok = (body.pass_token or "").strip()
    if tok:
        freed = False
        with _lock, db() as conn:
            row = conn.execute("SELECT used FROM passes WHERE token=?", (tok,)).fetchone()
            if row and row[0] == 0:
                conn.execute("UPDATE passes SET used=1 WHERE token=?", (tok,))
                conn.execute("UPDATE reports SET paid=1, payment_id=?, amount_paise=0 WHERE id=?",
                             ("free_pass:" + tok, rid))
                freed = True
        if freed:
            # free-pass unlock is a real paid report -> generate prose too
            background_tasks.add_task(_generate_narrative_task, rid)
            # Mirror the paid path (webhook/verify): PDF first so the WhatsApp
            # message can attach it, then the SAME approved template a paying
            # customer gets. Only this request flipped used 0->1 / paid 0->1
            # (guarded above), so the send fires exactly once per pass.
            if user_phone:
                background_tasks.add_task(_pregenerate_pdf_task, rid)
                background_tasks.add_task(
                    send_whatsapp_report, user_phone, rid,
                    _display_name(rec["payload"]),
                    rec["payload"].get("product", "marriage"))
            # The popup collected the buyer's number before this unlock, so a
            # free pass still creates the account (no Razorpay webhook will
            # ever fire for it). Runs AFTER the unlock transaction closed —
            # never let it break the unlock.
            if user_phone:
                try:
                    # No auto-set name — account name is user-editable on
                    # /account. Email is the popup email typed at checkout.
                    uid = users.upsert_user_from_payment(
                        db, mobile=user_phone,
                        email=(body.email or "").strip())
                    if uid:
                        users.link_report(db, rid, uid)
                except Exception as e:
                    logger.error("[users] free-pass account upsert failed "
                                 "for %s: %s", rid, e)
            return {"free": True}
        return {"error": "invalid_pass"}
    amount_paise = _order_amount_paise(rec)
    order = rzp_client().order.create({
        "amount": amount_paise, "currency": "INR",
        "receipt": rid, "notes": {"report_id": rid}})
    set_order(rid, order["id"])
    with _lock, db() as c:
        c.execute("UPDATE reports SET amount_paise=? WHERE id=?",
                  (amount_paise, rid))
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
                # TWO numbers: reports.phone keeps whatever contact Razorpay
                # reports for the PAYMENT (mark_paid, unchanged), while the
                # account + WhatsApp delivery PREFER user_phone — the number
                # the buyer typed into the pre-payment popup ("your report,
                # OTP & account will be created on this number").
                pay_phone = ent.get("contact") or ""
                # Account keeps the pre-existing fallback (popup number, else
                # the Razorpay contact). But the REPORT is delivered ONLY to
                # the popup number — NEVER the Razorpay number, not even as a
                # fallback (the popup mobile is a mandatory field).
                phone = rec.get("user_phone") or pay_phone
                wa_phone = rec.get("user_phone") or ""
                # ATOMIC CLAIM — the single idempotency gate, shared with the
                # verify + poll paths. Deliver ONLY if this webhook is the caller
                # that flips paid 0->1; if verify or a poll cycle already
                # delivered, claim_paid returns False and we skip (no double
                # WhatsApp). This sits on top of the event-id dedup
                # (already_processed) above, which only guards the webhook
                # re-sending the SAME event, not webhook-vs-verify races.
                if payments.claim_paid(db, rid, ent.get("id"), pay_phone):
                    rzp_amount = ent.get("amount")
                    if rzp_amount is not None:
                        with _lock, db() as _c:
                            _c.execute("UPDATE reports SET amount_paise=? WHERE id=?",
                                       (int(rzp_amount), rid))
                    # PDF first, then WhatsApp: background tasks run in order, so
                    # the message can attach the freshly cached PDF.
                    background_tasks.add_task(_pregenerate_pdf_task, rid)
                    if wa_phone:
                        background_tasks.add_task(
                            send_whatsapp_report, wa_phone, rid,
                            _display_name(rec["payload"]),
                            rec["payload"].get("product", "marriage"))
                    # Optional creative prose (Claude/OpenAI). No-op unless
                    # NARRATIVE_ENABLED=1; runs before WhatsApp/email are opened by
                    # the user since delivery links point at /report/{id}.
                    background_tasks.add_task(_generate_narrative_task, rid)
                    form_email = rec["payload"]["meta"].get("_email")
                    # Account: create/link a user on the popup number (fallback:
                    # Razorpay contact). The ACCOUNT email must prefer the POPUP
                    # email the buyer typed (fallback: the Razorpay contact email).
                    # pay_email stays the Razorpay/transaction email for tracking.
                    # Never auto-set the account NAME from the report — a milan
                    # report's name is a couple ("A & B"), wrong as a person's
                    # account name; the user edits it on /account instead.
                    pay_email = ent.get("email") or form_email or ""
                    try:
                        uid = users.upsert_user_from_payment(
                            db, mobile=phone, email=form_email or pay_email)
                        if uid:
                            users.link_report(db, rid, uid)
                    except Exception as e:
                        logger.error("[users] account upsert failed for %s: %s", rid, e)
                    if form_email:                   # (#7) email + PDF delivery
                        background_tasks.add_task(email_report, form_email, rid, rec["payload"])
                    # Server-side Purchase -> Meta CAPI + GA4 MP (dormant unless the
                    # keys are set). The reliable backstop for the browser Pixel/gtag
                    # fire, which is lost to ad-blockers / closed tabs. event_id/
                    # transaction_id = rid dedups it against the client fire.
                    _meta = rec["payload"].get("meta", {})
                    background_tasks.add_task(
                        tracking.track_purchase, rid, _order_amount_paise(rec) / 100,
                        "INR", phone, pay_email,
                        fbc=_meta.get("_fbc"), fbp=_meta.get("_fbp"),
                        client_user_agent=_meta.get("_ua"),
                        client_ip_address=_meta.get("_ip"))
    payments.mark_processed(db, eid, event.get("event", ""), rid or "")
    return {"ok": True}


@app.post("/api/verify")
def verify_payment(body: dict, background_tasks: BackgroundTasks):
    """Client-side fallback: after Razorpay checkout succeeds, the handler sends
    payment_id + order_id + signature here. We verify the HMAC and mark paid.
    The webhook remains the primary path, but this ensures payment goes through
    even if the webhook is delayed or misconfigured."""
    pid = (body.get("razorpay_payment_id") or "").strip()
    oid = (body.get("razorpay_order_id") or "").strip()
    sig = (body.get("razorpay_signature") or "").strip()
    if not (pid and oid and sig):
        raise HTTPException(400, "missing payment fields")
    if not RZP_SECRET:
        raise HTTPException(503, "payment not configured")
    expected = hmac.new(RZP_SECRET.encode(),
                        f"{oid}|{pid}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(400, "invalid signature")
    with db() as c:
        row = c.execute("SELECT id FROM reports WHERE order_id=?", (oid,)).fetchone()
    if not row:
        raise HTTPException(404, "order not found")
    rid = row[0]
    rec = get_report(rid)
    if rec and not rec["paid"]:               # cheap pre-check, NOT the gate
        # Fetch the payment entity from Razorpay server-side — it carries the
        # contact + email the customer typed into checkout. That contact stays
        # the PAYMENT number (reports.phone); the account and WhatsApp delivery
        # prefer user_phone from the pre-payment popup.
        pay_phone = body.get("phone") or ""
        pay_email = ""
        try:
            ent = rzp_client().payment.fetch(pid)
            pay_phone = ent.get("contact") or pay_phone
            pay_email = ent.get("email") or ""
        except Exception as e:
            logger.error("[verify] payment fetch failed for %s: %s", pid, e)
        # ATOMIC CLAIM — the real idempotency gate (the `not rec["paid"]` read
        # above is only a cheap optimization that can race). Deliver ONLY if this
        # verify call flips paid 0->1; if the webhook (or another verify) already
        # did, claim_paid returns False and we skip — no double delivery.
        # claim_paid also stores payment_id + the Razorpay contact, so there is
        # no separate mark_paid here.
        if payments.claim_paid(db, rid, pid, pay_phone):
            try:
                rzp_amount = ent.get("amount") if ent else None
            except NameError:
                rzp_amount = None
            if rzp_amount is not None:
                with _lock, db() as _c:
                    _c.execute("UPDATE reports SET amount_paise=? WHERE id=?",
                               (int(rzp_amount), rid))
            # Account keeps the fallback; the REPORT goes only to the popup number.
            phone = rec.get("user_phone") or pay_phone
            wa_phone = rec.get("user_phone") or ""
            # Mirror the webhook: PDF first so the WhatsApp message can attach it.
            background_tasks.add_task(_pregenerate_pdf_task, rid)
            background_tasks.add_task(_generate_narrative_task, rid)
            if wa_phone:
                background_tasks.add_task(
                    send_whatsapp_report, wa_phone, rid,
                    _display_name(rec["payload"]),
                    rec["payload"].get("product", "marriage"))
            form_email = rec["payload"]["meta"].get("_email")
            try:
                # ACCOUNT email prefers the POPUP email (fallback: Razorpay contact
                # email). No auto-set name — the user edits it on /account.
                uid = users.upsert_user_from_payment(
                    db, mobile=phone, email=form_email or pay_email or "")
                if uid:
                    users.link_report(db, rid, uid)
            except Exception as e:
                logger.error("[users] account upsert failed for %s: %s", rid, e)
            if form_email:
                background_tasks.add_task(email_report, form_email, rid, rec["payload"])
            # Mirror the webhook: server-side Purchase backstop (env-gated OFF).
            _meta = rec["payload"].get("meta", {})
            background_tasks.add_task(
                tracking.track_purchase, rid, _order_amount_paise(rec) / 100,
                "INR", phone, pay_email or form_email or "",
                fbc=_meta.get("_fbc"), fbp=_meta.get("_fbp"),
                client_user_agent=_meta.get("_ua"),
                client_ip_address=_meta.get("_ip"))
    return {"ok": True, "report_id": rid}


# ---------------------------------------------------------------- recovery net
# "No paid customer is ever left without their report." If a browser closes
# mid-payment AND the Razorpay webhook is missed, the report is never delivered
# (an "orphaned payment"). This backstop does not depend on the webhook: a
# lightweight in-process poll (and the admin /api/reconcile sweep) asks Razorpay
# which unpaid-in-our-DB reports were actually captured and runs the SAME
# delivery the webhook does. Idempotency is airtight because a report is
# delivered ONLY by the caller that atomically flips paid 0->1
# (payments.claim_paid), so neither the webhook nor two overlapping poll cycles
# can double-deliver.
RECONCILE_INTERVAL_SEC = int(os.getenv("RECONCILE_INTERVAL_SEC", "300"))
_reconcile_lock = threading.Lock()      # guards against overlapping poll cycles
_reconcile_thread_started = False


def _deliver_report(rid: str):
    """Run the webhook's delivery for one just-recovered report, SYNCHRONOUSLY —
    reconcile can run in a daemon thread with no FastAPI request / BackgroundTasks
    around it, so we call the task functions directly. Order mirrors the webhook:
    cache the PDF first (so the WhatsApp message can attach it), then narrative,
    then the report WhatsApp to the POPUP number ONLY (never the Razorpay
    contact), then the optional email copy. Never raises."""
    rec = get_report(rid)
    if not rec:
        return
    _pregenerate_pdf_task(rid)            # sees paid=1 (claim already flipped it)
    _generate_narrative_task(rid)
    wa_phone = rec.get("user_phone") or ""   # popup number ONLY — see webhook rule
    if wa_phone:
        send_whatsapp_report(wa_phone, rid, _display_name(rec["payload"]),
                             rec["payload"].get("product", "marriage"))
    else:
        # Old orphan whose popup number was never captured: it is now paid and
        # the report is generated (viewable / in the account), but we cannot
        # deliver WhatsApp to a number we do not have. Skip gracefully.
        logger.info("[reconcile] %s recovered without a popup number — marked "
                    "paid + report generated, WhatsApp skipped", rid)
    form_email = (rec["payload"].get("meta") or {}).get("_email")
    if form_email:                        # (#7) email + PDF copy, like the paid path
        email_report(form_email, rid, rec["payload"])


def _reconcile_and_deliver(limit: int = 200) -> dict:
    """The webhook-independent backstop. Find reports Razorpay reports as captured
    but still paid=0 in our DB, and for each: atomically CLAIM it (deliver only if
    THIS path flipped paid 0->1), then run the full webhook delivery + account
    upsert/link. Safe no-op when Razorpay is unconfigured; skips cleanly if another
    cycle is already running. Callable synchronously (poll thread or admin)."""
    if not payments.configured():
        return {"checked": 0, "recovered": 0, "note": "razorpay not configured"}
    if not _reconcile_lock.acquire(blocking=False):
        return {"checked": 0, "recovered": 0, "note": "already running"}
    try:
        candidates = payments.find_recoverable(db, limit)
        recovered = 0
        for cand in candidates:
            rid = cand["rid"]
            # ATOMIC CLAIM — the single idempotency gate. If the webhook (or an
            # overlapping cycle) already flipped this report, claim_paid returns
            # False and we skip: NO re-delivery.
            if not payments.claim_paid(db, rid, cand["payment_id"], cand["contact"]):
                continue
            rzp_amount = cand.get("amount")
            if rzp_amount is not None:
                with _lock, db() as _c:
                    _c.execute("UPDATE reports SET amount_paise=? WHERE id=?",
                               (int(rzp_amount), rid))
            try:
                _deliver_report(rid)
            except Exception as e:
                logger.error("[reconcile] delivery failed for %s: %s", rid, e)
            # Account creation/link, mirroring the webhook: the account keeps its
            # fallback (popup number, else the Razorpay contact); the popup email
            # is preferred over the Razorpay email.
            try:
                rec = get_report(rid)
                popup = rec.get("user_phone") if rec else ""
                form_email = ((rec or {}).get("payload", {}).get("meta") or {}).get("_email")
                uid = users.upsert_user_from_payment(
                    db, mobile=popup or cand["contact"],
                    email=form_email or cand["email"])
                if uid:
                    users.link_report(db, rid, uid)
            except Exception as e:
                logger.error("[users] reconcile account link failed for %s: %s", rid, e)
            recovered += 1
        return {"checked": len(candidates), "recovered": recovered}
    finally:
        _reconcile_lock.release()


def _reconcile_loop():
    """Daemon loop: sweep every RECONCILE_INTERVAL_SEC, never crashing the app."""
    while True:
        try:
            _reconcile_and_deliver()
        except Exception as e:            # a bug here must not kill the backstop
            logger.error("[reconcile] poll cycle error: %s", e)
        time.sleep(max(RECONCILE_INTERVAL_SEC, 1))


@app.on_event("startup")
def _start_reconcile_poll():
    """Start the in-process recovery poll once at boot. Single-instance EB
    deployment, so an in-process daemon thread is the right tool. No-op cleanly
    when Razorpay is unconfigured or the thread is already running."""
    global _reconcile_thread_started
    if _reconcile_thread_started:
        return
    if not payments.configured():
        logger.info("[reconcile] razorpay not configured — recovery poll disabled")
        return
    _reconcile_thread_started = True
    threading.Thread(target=_reconcile_loop, name="reconcile-poll",
                     daemon=True).start()
    logger.info("[reconcile] recovery poll started (every %ss)", RECONCILE_INTERVAL_SEC)


@app.post("/api/reconcile")
def reconcile_admin(key: str = ""):
    """Admin: force a deliver-capable recovery sweep. Registered here (before
    extensions.install) so it SHADOWS the older non-delivering /api/reconcile in
    extensions.py — Starlette serves the first matching route. Gated by STATS_KEY."""
    if not _valid_admin_key(key):
        raise HTTPException(403, "forbidden")
    return _reconcile_and_deliver()


@app.get("/api/pdf_health", include_in_schema=False)
def pdf_health(key: str = ""):
    """Diagnostic: is the PDF-maker (headless Chrome) working ON THIS INSTANCE?

    The report PDF is what Twilio downloads for the WhatsApp attachment; when it
    can't be produced/served, delivery falls back to the link (see
    send_whatsapp_report) and Twilio logs error 63019. This renders a tiny test
    page and reports the resolved browser binary, timing and any error, so the
    live PDF pipeline's health is visible from a URL — no SSH needed. A
    load-balanced env serves a RANDOM instance per call, so hit it a few times to
    sample every instance. Gated by STATS_KEY."""
    if not _valid_admin_key(key):
        raise HTTPException(403, "forbidden")
    import platform, socket, time
    out = {
        "host": socket.gethostname(),
        "arch": platform.machine(),
        "browsers_path": os.getenv("PLAYWRIGHT_BROWSERS_PATH", ""),
        "chrome_bin": pdfgen.chrome_bin(),
        "render_ok": False,
    }
    if not out["chrome_bin"]:
        out["error"] = ("no chrome binary found on this instance — the PDF-maker "
                        "is not installed here (check that .ebextensions/"
                        "02_chromium.config ran; ls $PLAYWRIGHT_BROWSERS_PATH)")
        return out
    t0 = time.monotonic()
    try:
        data = pdfgen.generate(
            "<!doctype html><html><body style='font-family:sans-serif'>"
            "<h1>Axtroshastra PDF health check</h1></body></html>")
        out["render_ms"] = int((time.monotonic() - t0) * 1000)
        out["pdf_bytes"] = len(data) if data else 0
        out["render_ok"] = bool(data and data[:4] == b"%PDF")
        if not out["render_ok"]:
            out["error"] = "chrome is present but the render produced no valid PDF"
    except Exception as e:
        out["render_ms"] = int((time.monotonic() - t0) * 1000)
        out["error"] = f"{type(e).__name__}: {e}"
    return out


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
    """Display '+919599827297' as '+91 95998 27297'; raw fallback for anything else."""
    if m and m.startswith("+91") and len(m) == 13 and m[3:].isdigit():
        d = m[3:]
        return f"+91 {d[:5]} {d[5:]}"
    return m


# --- one-tap PDF download wiring (all report templates) -------------------
# Every report's "Download PDF" anchor is `onclick="window.print();return false;"`.
# _wire_pdf_download() swaps that for axPdfDl(): fetch /report/{rid}/pdf ->
# blob -> a[download] (file saves, USER STAYS ON THE PAGE). If the endpoint
# 503s (Chrome unavailable), a toaster explains and the print dialog opens as
# the fallback — which still yields the browser-quality PDF (owner-approved).
_AXDL_SNIPPET = """<style>@media print{.ax-toast{display:none!important}}</style><script>
function axToastPdf(msg){var t=document.createElement('div');t.setAttribute('role','status');t.className='ax-toast';
t.style.cssText='position:fixed;left:50%;top:14px;transform:translateX(-50%) translateY(-24px);z-index:99999;background:#151C39;color:#F3EFE4;border:1px solid #E4B04A;border-radius:12px;padding:12px 16px;font:600 13.5px/1.45 system-ui,sans-serif;max-width:92vw;width:430px;box-shadow:0 10px 30px rgba(0,0,0,.35);opacity:0;transition:opacity .3s ease,transform .3s ease';
t.textContent=msg;document.body.appendChild(t);
requestAnimationFrame(function(){t.style.opacity='1';t.style.transform='translateX(-50%) translateY(0)';});
setTimeout(function(){t.style.opacity='0';t.style.transform='translateX(-50%) translateY(-24px)';
setTimeout(function(){if(t.parentNode)t.parentNode.removeChild(t);},320);},3200);}
function axPdfDl(ev){if(ev&&ev.preventDefault)ev.preventDefault();
if(window.axInApp&&window.axInApp()){var pu=location.pathname.replace(/\\/+$/,'')+'/pdf';
window.open(pu,'_blank');
axToastPdf('Opening your PDF\\u2026 use the in-app menu to save or share it \\u2014 or open this page in your browser for a direct download.');
return false;}
var b=ev&&ev.currentTarget;if(b)b.style.opacity='.55';
function done(){if(b)b.style.opacity='';}
function attempt(retriesLeft){
fetch(location.pathname.replace(/\\/+$/,'')+'/pdf').then(function(r){
if(!r.ok||((r.headers.get('Content-Type')||'').indexOf('pdf')<0))throw 0;
var m=(r.headers.get('Content-Disposition')||'').match(/filename="([^"]+)"/);
return r.blob().then(function(bl){var u=URL.createObjectURL(bl);
var a=document.createElement('a');a.href=u;a.download=m?m[1]:'Axtroshastra_Report.pdf';
document.body.appendChild(a);a.click();
setTimeout(function(){URL.revokeObjectURL(u);if(a.parentNode)a.parentNode.removeChild(a);},4000);
axToastPdf('PDF downloaded \\u2713 check your Downloads / Files app.');done();});
}).catch(function(){
if(retriesLeft>0){axToastPdf('Preparing your PDF \\u2014 one moment\\u2026');
setTimeout(function(){attempt(retriesLeft-1);},3000);return;}
done();
axToastPdf('Preparing your PDF \\u2014 choose "Save as PDF" in the window that opens, or grab it from WhatsApp: we\\u2019ve sent it there too.');
setTimeout(function(){window.print();},1700);});
}
attempt(1);
return false;}
</script>"""


# Devanagari twins for the user-visible toast strings inside _AXDL_SNIPPET.
# The chrome is injected AFTER shaadi_hi/milan_hi.localize runs, so any English
# it carries would ship untranslated on a Hindi report — swap it here instead.
_AXDL_HI = [
    ("Opening your PDF\\u2026 use the in-app menu to save or share it \\u2014 "
     "or open this page in your browser for a direct download.",
     "आपकी PDF खुल रही है\\u2026 इसे सेव या शेयर करने के लिए इन-ऐप मेनू का उपयोग करें \\u2014 "
     "या सीधे डाउनलोड के लिए इस पेज को अपने ब्राउज़र में खोलें।"),
    ("PDF downloaded \\u2713 check your Downloads / Files app.",
     "PDF डाउनलोड हो गई \\u2713 अपने Downloads / Files ऐप में देखें।"),
    ("Preparing your PDF \\u2014 one moment\\u2026",
     "आपकी PDF तैयार हो रही है \\u2014 बस एक पल\\u2026"),
    ('Preparing your PDF \\u2014 choose "Save as PDF" in the window that opens, '
     'or grab it from WhatsApp: we\\u2019ve sent it there too.',
     'आपकी PDF तैयार हो रही है \\u2014 खुलने वाली विंडो में "Save as PDF" चुनें, '
     'या WhatsApp से ले लीजिए: हमने वहाँ भी भेज दी है।'),
]


def _wire_pdf_download(html: str, lang: str = "en") -> str:
    """Swap print-dialog PDF buttons for the one-tap download (never raises)."""
    try:
        if "window.print();return false;" not in html:
            return html
        html = html.replace("window.print();return false;", "return axPdfDl(event);")
        snip = _AXDL_SNIPPET
        if lang == "hi":
            for en, hi in _AXDL_HI:
                snip = snip.replace(en, hi)
        if "</body>" in html:
            return html.replace("</body>", snip + "</body>", 1)
        return html + snip
    except Exception:
        return html


# Account-created toast (once per report, localStorage-guarded) + best-effort
# back-button redirect to /account (once per tab session, no loops — the
# visible hamburger nav is the primary navigation; this is a supplement).
_REPORT_NAV_SNIPPET = """<script>
(function(){
  var rid="__RID__", hasAcct=("__HASACCT__"==="1");
  try{
    if(hasAcct && !localStorage.getItem('axs_acct_toast_'+rid)){
      localStorage.setItem('axs_acct_toast_'+rid,'1');
      var t=document.createElement('div');t.setAttribute('role','status');t.className='ax-toast';
      t.style.cssText='position:fixed;left:50%;top:14px;transform:translateX(-50%) translateY(-24px);z-index:99999;background:#151C39;color:#F3EFE4;border:1px solid #E4B04A;border-radius:12px;padding:12px 16px;font:600 13.5px/1.5 system-ui,sans-serif;max-width:92vw;width:450px;box-shadow:0 10px 30px rgba(0,0,0,.35);opacity:0;transition:opacity .3s ease,transform .3s ease';
      t.innerHTML='\\u2705 Account created \\u2014 login anytime with your mobile number. <a href="/login?next=%2Faccount" style="color:#E4B04A;font-weight:700;text-decoration:none">Log in \\u2192</a>';
      document.body.appendChild(t);
      requestAnimationFrame(function(){t.style.opacity='1';t.style.transform='translateX(-50%) translateY(0)';});
      setTimeout(function(){t.style.opacity='0';t.style.transform='translateX(-50%) translateY(-24px)';
        setTimeout(function(){if(t.parentNode)t.parentNode.removeChild(t);},320);},3500);
    }
  }catch(e){}
  try{
    if(!sessionStorage.getItem('axs_back_'+rid)){
      sessionStorage.setItem('axs_back_'+rid,'1');
      history.pushState({axs:1},'',location.href);
      window.addEventListener('popstate',function h(){
        window.removeEventListener('popstate',h);
        location.replace('/account');
      });
    }
  }catch(e){}
})();
</script>"""


# Devanagari account-created toast (see _REPORT_NAV_SNIPPET). "Log in" keeps its
# arrow; the link target is unchanged.
_ACCT_TOAST_EN = ('\\u2705 Account created \\u2014 login anytime with your mobile number. '
                  '<a href="/login?next=%2Faccount" style="color:#E4B04A;font-weight:700;'
                  'text-decoration:none">Log in \\u2192</a>')
_ACCT_TOAST_HI = ('\\u2705 अकाउंट बन गया \\u2014 अपने मोबाइल नंबर से कभी भी लॉगिन करें। '
                  '<a href="/login?next=%2Faccount" style="color:#E4B04A;font-weight:700;'
                  'text-decoration:none">लॉगिन \\u2192</a>')


# --- in-app browser (Instagram / FB / TikTok / …) handling ----------------
# Reports are opened a lot from Instagram/Facebook links, which force a
# restricted WebView. There the blob-based PDF download silently fails and
# wa.me / external links throw "Page can't be loaded". This snippet:
#   * defines window.axInApp() -> the app name (or null) from the UA;
#   * on a match, shows a dismissible, on-brand "open in your browser" banner
#     with platform-aware steps (Android ⋮ menu / iOS ••• menu);
#   * exposes the direct /pdf link as a tappable fallback;
#   * wraps window.axShare so, when native share is unavailable in the WebView,
#     it copies the report link to the clipboard with a toast.
# The download button itself branches on axInApp() inside axPdfDl (see above):
# in-app it opens the direct /pdf URL in a new tab instead of the blob.
_INAPP_SNIPPET = """<script>
(function(){
window.axInApp=function(){var u=navigator.userAgent||'';
if(/Instagram/i.test(u))return'Instagram';
if(/FBAN|FBAV|FB_IAB|FBIOS/i.test(u))return'Facebook';
if(/Snapchat/i.test(u))return'Snapchat';
if(/musical_ly|BytedanceWebview|TikTok/i.test(u))return'TikTok';
if(/\\bLine\\//i.test(u))return'LINE';
if(/Twitter|TwitterAndroid/i.test(u))return'Twitter/X';
return null;};
var app=window.axInApp();if(!app)return;
var TX={head:'Open in your browser for the best experience',
introPre:'You\\u2019re viewing this inside ',
introPost:'. To download your PDF and open WhatsApp reliably:',
stepA:'Tap the \\u22ee menu (top-right), then choose \\u201cOpen in Chrome\\u201d / your browser.',
stepI:'Tap the \\u2022\\u2022\\u2022 (or browser) icon, then choose \\u201cOpen in browser\\u201d.',
pdflbl:'or open the PDF directly',
dismiss:'Dismiss',
copied:'Report link copied \\u2014 paste it into WhatsApp to share.'};
try{if(sessionStorage.getItem('axs_inapp_dismiss'))var _dismissed=1;}catch(e){}
if(!_dismissed){
var u=navigator.userAgent||'';var ios=/iPhone|iPad|iPod/i.test(u);
var steps=ios?TX.stepI:TX.stepA;
var pu=location.pathname.replace(/\\/+$/,'')+'/pdf';
var b=document.createElement('div');b.className='ax-inapp';b.setAttribute('role','region');
b.style.cssText='position:relative;z-index:9997;margin:10px 12px;padding:14px 16px 14px 18px;'+
'background:#FFF7E8;border:1px solid #E4B04A;border-left:5px solid #C93B2E;border-radius:12px;'+
'color:#3A2F1B;font:400 13.5px/1.5 -apple-system,BlinkMacSystemFont,\\'Segoe UI\\',Roboto,sans-serif;'+
'box-shadow:0 4px 14px rgba(21,28,57,.12);max-width:640px';
b.innerHTML='<div style="font-weight:800;color:#151C39;font-size:14.5px;margin:0 44px 4px 0">'+TX.head+'</div>'+
'<div style="margin-bottom:8px">'+TX.introPre+app+TX.introPost+' <b>'+steps+'</b></div>'+
'<a class="ax-inapp-pdf" href="'+pu+'" target="_blank" rel="noopener" '+
'style="color:#C93B2E;font-weight:700;text-decoration:none">'+TX.pdflbl+' \\u2192</a> '+
'<button type="button" class="ax-inapp-x" '+
'style="float:right;background:none;border:0;color:#7A6A4A;font-weight:700;cursor:pointer;'+
'font-size:12.5px;padding:2px 4px">'+TX.dismiss+'</button>';
var host=document.body;host.insertBefore(b,host.firstChild);
b.querySelector('.ax-inapp-x').onclick=function(){
try{sessionStorage.setItem('axs_inapp_dismiss','1');}catch(e){}
if(b.parentNode)b.parentNode.removeChild(b);};
}
var _origShare=window.axShare;
window.axShare=function(){
try{if(navigator.share&&_origShare)return _origShare.apply(this,arguments);}catch(e){}
var url=location.href;
if(navigator.clipboard&&navigator.clipboard.writeText){
navigator.clipboard.writeText(url).then(function(){
if(window.axToastPdf)axToastPdf(TX.copied);},function(){if(_origShare)_origShare();});
}else if(_origShare){_origShare();}
return false;};
})();
</script>"""


# Devanagari twins for the user-visible copy inside _INAPP_SNIPPET (injected
# after the shaadi_hi/milan_hi localizers run, so English here would ship
# untranslated on a Hindi report — swap it in Python instead).
_INAPP_HI = [
    ("Open in your browser for the best experience",
     "बेहतर अनुभव के लिए अपने ब्राउज़र में खोलें"),
    ("You\\u2019re viewing this inside ",
     "आप इसे "),
    (". To download your PDF and open WhatsApp reliably:",
     " ऐप में देख रहे हैं। PDF डाउनलोड करने और WhatsApp सही से खोलने के लिए:"),
    ("Tap the \\u22ee menu (top-right), then choose \\u201cOpen in Chrome\\u201d / your browser.",
     "ऊपर-दाईं ओर \\u22ee मेनू पर टैप करें, फिर \\u201cChrome में खोलें\\u201d / अपना ब्राउज़र चुनें।"),
    ("Tap the \\u2022\\u2022\\u2022 (or browser) icon, then choose \\u201cOpen in browser\\u201d.",
     "\\u2022\\u2022\\u2022 (या ब्राउज़र) आइकन पर टैप करें, फिर \\u201cब्राउज़र में खोलें\\u201d चुनें।"),
    ("or open the PDF directly",
     "या PDF सीधे खोलें"),
    ("dismiss:'Dismiss'",
     "dismiss:'बंद करें'"),
    ("Report link copied \\u2014 paste it into WhatsApp to share.",
     "रिपोर्ट लिंक कॉपी हो गया \\u2014 शेयर करने के लिए WhatsApp में पेस्ट करें।"),
]


def _wire_inapp(html: str, lang: str = "en") -> str:
    """Inject the in-app-browser banner + axShare fallback (never raises)."""
    try:
        snip = _INAPP_SNIPPET
        if lang == "hi":
            for en, hi in _INAPP_HI:
                snip = snip.replace(en, hi)
        if "</body>" in html:
            return html.replace("</body>", snip + "</body>", 1)
        return html + snip
    except Exception:
        return html


def _wire_report_chrome(html: str, rid: str, lang: str = "en") -> str:
    """Everything a served report page gets on top of the raw template:
    one-tap PDF button, hamburger nav, account toast and the back-button
    supplement. `lang` keeps this chrome in-language: it is injected AFTER the
    shaadi_hi/milan_hi localizers run, so English here would ship untranslated
    on a Hindi report. Never raises — worst case the raw page ships."""
    try:
        html = _inject_tracking(html)
        html = _wire_pdf_download(html, lang)
        html = _wire_inapp(html, lang)
        has_acct = False
        try:                            # toast fires only when an account exists
            u = users.get_user_for_report(db, rid)
            has_acct = bool(u and (u.get("mobile") or u.get("email")))
        except Exception as e:
            logger.error("[users] account lookup failed for %s: %s", rid, e)
        html = _inject_nav(html, lang)
        snip = (_REPORT_NAV_SNIPPET.replace("__RID__", rid)
                .replace("__HASACCT__", "1" if has_acct else "0"))
        if lang == "hi":
            snip = snip.replace(_ACCT_TOAST_EN, _ACCT_TOAST_HI)
        if "</body>" in html:
            html = html.replace("</body>", snip + "</body>", 1)
        else:
            html += snip
        return html
    except Exception as e:
        logger.error("[report] chrome wiring failed for %s: %s", rid, e)
        return html


@app.get("/report/{rid}.pdf", include_in_schema=False)
def report_pdf_dotext(rid: str):
    """Same file as /report/{rid}/pdf, reachable at a dot-extension address.
    WhatsApp template media fields must end in a recognised file extension
    (Twilio rejects a bare path segment like '/pdf' at submission time), so
    the approved delivery template points here instead of the folder-style
    route. Must be registered before /report/{rid} below — that route's
    plain {rid} converter matches any slash-free string including
    "xyz.pdf", so if it came first it would swallow this one and 404."""
    return report_pdf(rid)


@app.get("/report/{rid}", include_in_schema=False)
def report_page(rid: str, v2: int = 1):
    rec = get_report(rid)
    if not rec or not rec["paid"]:
        return HTMLResponse("<h3 style='font-family:sans-serif;padding:40px'>"
                            "Report not found ya payment pending hai. "
                            "<a href='/'>Wapas jaayein</a></h3>", status_code=404)
    payload = _refresh_current_period(rec["payload"])
    payload.setdefault("meta", {})["report_id"] = rid
    lang = "hi" if (payload.get("meta") or {}).get("lang") == "hi" else "en"
    if payload.get("product") == "milan" and v2 != 0:
        try:
            import milan_v2
            html = milan_v2.render_milan_v2(payload)
            if lang == "hi":
                import milan_hi
                html = milan_hi.localize(html)
            return HTMLResponse(_wire_report_chrome(html, rid, lang))
        except Exception as e:
            logger.error("[v2] render failed for %s: %s", rid, e)   # fall through to v1
    html = _render_for(payload.get("product", "marriage"), payload)
    return HTMLResponse(_wire_report_chrome(html, rid, lang))


@app.get("/report/{rid}/pdf", include_in_schema=False)
def report_pdf(rid: str):
    """Browser-quality PDF download. Serves the pre-generated cached file
    (created at payment); regenerates on demand if the cache is cold (fresh
    deploy). On failure returns 503 JSON — the report page's download button
    then shows a toaster and falls back to the print dialog (owner-approved:
    the print dialog still yields the beautiful PDF)."""
    rec = get_report(rid)
    if not rec or not rec["paid"]:
        raise HTTPException(404, "report not found")
    payload = _refresh_current_period(rec["payload"])
    payload.setdefault("meta", {})["report_id"] = rid
    pdf = pdfgen.get_or_generate(rid, _full_report_html(payload))
    if not pdf:
        return JSONResponse({"error": "pdf_unavailable"}, status_code=503)
    meta = payload.get("meta", {})
    name = meta.get("name") or (f"{meta['p1']}_{meta['p2']}" if meta.get("p1") and meta.get("p2")
                                else "report")
    name = name.replace(" ", "_")[:40]
    # HTTP headers are latin-1 only, but a Hindi report's name can be Devanagari
    # (e.g. "आशा शर्मा"). Building the header with the raw name raised
    # UnicodeEncodeError -> 500 -> the browser fell back to the print dialog
    # (this was the real cause of "Hindi PDF only gives the fallback"). Emit an
    # ASCII-safe filename plus an RFC 5987 UTF-8 variant for modern browsers.
    from urllib.parse import quote as _urlquote
    ascii_name = name.encode("ascii", "ignore").decode("ascii").strip("_") or "Report"
    utf8_name = _urlquote(f"Axtroshastra_{name}.pdf")
    disposition = (f'attachment; filename="Axtroshastra_{ascii_name}.pdf"; '
                   f"filename*=UTF-8''{utf8_name}")
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": disposition,
                             "Cache-Control": "private, max-age=3600"})


if DEMO_MODE:                                    # never set DEMO_MODE=1 in production
    @app.post("/api/_demo_pay/{rid}")
    def demo_pay(rid: str, background_tasks: BackgroundTasks):
        if not get_report(rid): raise HTTPException(404, "report not found")
        mark_paid(rid, payment_id="demo")
        background_tasks.add_task(_generate_narrative_task, rid)
        return {"ok": True}



class MilanIn(BaseModel):
    p1_name: str; p1_dob: str; p1_tob: str | None = None; p1_place: str
    p2_name: str; p2_dob: str; p2_tob: str | None = None; p2_place: str
    p1_gender: str | None = None; p2_gender: str | None = None
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
         "tz": tz1, "lat": lat1, "lon": lon1, "gender": inp.p1_gender},
        {"name": inp.p2_name, "dob": inp.p2_dob, "tob": inp.p2_tob,
         "tz": tz2, "lat": lat2, "lon": lon2, "gender": inp.p2_gender})
    report["meta"]["variant"] = (inp.variant or "direct")[:64]
    report["meta"]["lang"] = "hi" if (inp.variant or "").startswith("/hi/") else "en"
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
    # served through the nav injector so the hamburger shows on blog pages too
    return _serve_page_with_nav(os.path.join(BASE, "pages", "blog", "index.html"))


@app.get("/blog/{slug}", include_in_schema=False)
def blog_post(slug: str):
    if not slug.replace("-", "").isalnum():
        raise HTTPException(404, "not found")
    path = os.path.join(BASE, "pages", "blog", f"{slug}.html")
    if os.path.exists(path):
        return _serve_page_with_nav(path)
    raise HTTPException(404, "not found")


BLOG_SLUGS = ["shaadi-kab-hogi-marriage-timing", "manglik-dosha-cancellation",
              "kundli-milan-36-gun", "birth-time-nahi-pata-chandra-lagna",
              "vimshottari-dasha-life-phases"]

@app.get("/sitemap.xml", include_in_schema=False)
def sitemap():
    base_url = PUBLIC_BASE_URL or "https://www.axtroshastra.com"
    urls = ["/", "/en/marriage", "/hi/marriage", "/en/compatibility", "/hi/compatibility", "/jeevan", "/career", "/blog",
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
                              f"{base}/en/compatibility?pass={toks[0]}",
                              f"{base}/jeevan?pass={toks[0]}",
                              f"{base}/career?pass={toks[0]}"],
            "note": "Each token unlocks exactly ONE report, on any product page."}


def _backfill_narrative_task(rid: str):
    """Background per-report backfill: (re)generate the LLM narrative, store it,
    then invalidate + re-warm the cached PDF so downloads/WhatsApp attachments
    pick up the new prose. Never raises."""
    try:
        rec = get_report(rid)
        if not rec or not rec["paid"]:
            return
        narr = narrative.generate_narrative(rec["payload"])
        if not narr:
            logger.warning("[narrative] backfill produced no sections for %s", rid)
            return
        save_narrative(rid, narr)
        pdfgen.invalidate(rid)
        _pregenerate_pdf_task(rid)
    except Exception as e:
        logger.error("[narrative] backfill failed for %s: %s", rid, e)


@app.post("/api/backfill_narrative")
def backfill_narrative(background_tasks: BackgroundTasks, key: str = "",
                       rid: str = "", limit: int = 25):
    """Admin: (re)generate + save the LLM narrative for already-paid reports.

    Old Hindi marriage reports were paid while the 30s narrative timeout was
    silently failing, so they carry no narrative and render the English banks
    forever — generation only ever ran at payment time. This queues it again.

      ?rid=<id>   backfill exactly that paid report (any product/language)
      (no rid)    scan for paid marriage reports with meta.lang='hi' and no
                  stored narrative, oldest first, up to `limit`

    Each report is queued as a background task (a marriage generation can take
    ~3 minutes); the task stores the prose and invalidates + re-warms the cached
    PDF. Gated by STATS_KEY. Requires NARRATIVE_ENABLED=1 (+ API key) to have
    any effect — reported in the response so a no-op run is obvious."""
    if not _valid_admin_key(key):
        raise HTTPException(403, "forbidden")
    if rid:
        rec = get_report(rid)
        if not rec or not rec["paid"]:
            raise HTTPException(404, "report not found or unpaid")
        rids = [rid]
    else:
        with db() as c:
            rows = c.execute(
                """SELECT id FROM reports
                   WHERE paid=1
                     AND json_extract(payload,'$.meta.lang')='hi'
                     AND COALESCE(json_extract(payload,'$.product'),'marriage')='marriage'
                     AND json_extract(payload,'$.narrative') IS NULL
                   ORDER BY rowid LIMIT ?""", (int(limit),)).fetchall()
        rids = [r[0] for r in rows]
    for r in rids:
        background_tasks.add_task(_backfill_narrative_task, r)
    return {"queued": rids, "count": len(rids),
            "narrative_enabled": narrative.enabled()}


@app.get("/api/backfill_users")
def backfill_users(key: str = "", limit: int = 5000):
    """One-time (idempotent) admin action: create + link accounts for reports that
    were paid before the accounts code shipped — paid, with a phone on file, but no
    linked user. Safe to re-run. Gated by STATS_KEY."""
    if not _valid_admin_key(key):
        raise HTTPException(403, "forbidden")
    return users.backfill(db, limit)


@app.post("/api/resend_wa/{rid}")
def resend_whatsapp(rid: str, key: str = ""):
    """Admin: re-deliver the post-payment WhatsApp for an already-paid report
    (used when the original send failed — e.g. the missing-Chromium window or
    the milan webhook crash). Re-runs PDF pre-generation first so the message
    can attach the file. Gated by STATS_KEY."""
    if not _valid_admin_key(key):
        raise HTTPException(403, "forbidden")
    rec = get_report(rid)
    if not rec or not rec["paid"]:
        raise HTTPException(404, "report not found or unpaid")
    # Prefer the WhatsApp number typed in the pre-payment popup; fall back to
    # the Razorpay payment contact.
    phone = rec.get("user_phone") or ""   # never the Razorpay number
    if not phone:
        return {"ok": False, "error": "no_phone_on_report"}
    _pregenerate_pdf_task(rid)                     # sync: admin call, fine to wait
    send_whatsapp_report(phone, rid, _display_name(rec["payload"]),
                         rec["payload"].get("product", "marriage"))
    return {"ok": True, "pdf_cached": bool(pdfgen.get_cached(rid))}


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
    raw_name = (user.get("name") or "").strip()
    greeting = _html.escape(raw_name or "there")
    name_attr = _html.escape(raw_name, quote=True)   # safe as an input value=""
    mobile = _html.escape(_fmt_mobile(user.get("mobile") or ""))
    email = _html.escape(user.get("email") or "")
    city = _html.escape(user.get("city") or "")

    def _detail(label, value):
        if not value:
            return ""
        return (f'<div class="row"><span class="k">{label}</span>'
                f'<span class="v">{value}</span></div>')

    # Name is user-editable (never auto-set from the report). Empty -> a
    # placeholder prompts the user to add it, rather than showing blank.
    name_hint = ("" if raw_name else
                 '<div class="name-hint">Add your name so we can address you '
                 'properly.</div>')
    name_row = (
        '<div class="row name-row">'
        '<span class="k">Name</span>'
        '<form class="name-form" id="nameForm" onsubmit="return saveName(event)">'
        f'<input id="nameInput" name="name" type="text" value="{name_attr}" '
        'placeholder="Your name" autocomplete="name" maxlength="80">'
        '<button type="submit" class="name-save">Save</button>'
        '</form></div>' + name_hint)

    details = (name_row + _detail("Mobile", mobile) + _detail("Email", email)
               + _detail("City", city))

    if reports:
        cards = ""
        for r in reports:
            product = r["product"]
            label = _html.escape(PRODUCT_LABEL.get(product, "Report"))
            icon = PRODUCT_SVG.get(product, PRODUCT_SVG["marriage"])
            subject = _html.escape(r.get("subject") or "")
            date = _html.escape((r.get("created_at") or "")[:10])
            sub = f'<div class="rp-sub">{subject}</div>' if subject else ""
            date_row = f'<span class="rp-date">{date}</span>' if date else ""
            cards += (
                f'<a class="rp-card" href="/report/{r["id"]}">'
                f'<div class="rp-band"><span class="rp-icon">{icon}</span></div>'
                f'<div class="rp-body"><span class="rp-label">{label}</span>{sub}'
                f'<div class="rp-meta">{date_row}'
                f'<span class="rp-cta">View report &rarr;</span></div>'
                f'</div></a>')
        reports_block = f'<div class="rp-grid">{cards}</div>'
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
.row .k{{color:var(--muted);width:70px;flex:0 0 auto;font-size:13px;padding-top:9px}}
.row .v{{font-weight:600}}
.name-row{{align-items:center}}
.name-form{{display:flex;gap:8px;flex:1 1 auto;align-items:center}}
.name-form input{{flex:1 1 auto;min-width:0;font:inherit;font-size:15px;font-weight:600;
color:var(--ink);background:#fbf8f1;border:1px solid var(--line);border-radius:10px;
padding:8px 11px}}
.name-form input::placeholder{{color:#a99f8f;font-weight:500}}
.name-form input:focus{{outline:none;border-color:var(--haldi);background:#fff}}
.name-save{{flex:0 0 auto;background:var(--midnight);color:#fff;border:0;border-radius:10px;
padding:8px 15px;font:inherit;font-size:14px;font-weight:700;cursor:pointer}}
.name-save:disabled{{opacity:.55;cursor:default}}
.name-hint{{color:#8a7d72;font-size:12.5px;padding:2px 0 6px 82px}}
.name-msg{{color:#2E7D64;font-size:12.5px;padding:2px 0 4px 82px;display:none}}
.rp-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));
gap:16px;margin-top:16px}}
.rp-card{{display:flex;flex-direction:column;background:#fff;border:1px solid var(--line);
border-radius:16px;overflow:hidden;text-decoration:none;color:var(--ink);
box-shadow:0 2px 12px rgba(70,50,30,.06);transition:transform .16s ease,box-shadow .16s ease}}
.rp-card:hover{{transform:translateY(-3px);box-shadow:0 12px 26px rgba(21,28,57,.14)}}
.rp-card:active{{transform:scale(.996)}}
/* Unified premium navy header + a soft blurred gold glow behind the icon;
   a thin gold hairline separates it from the white body. */
.rp-band{{position:relative;height:78px;display:flex;align-items:center;
justify-content:center;background:linear-gradient(135deg,#151C39,#1D2547);
overflow:hidden;border-bottom:1px solid var(--haldi)}}
.rp-band::before{{content:"";position:absolute;width:130px;height:130px;border-radius:50%;
background:radial-gradient(circle,rgba(228,176,74,.40),rgba(228,176,74,0) 70%);
filter:blur(16px);pointer-events:none}}
.rp-icon{{position:relative;width:32px;height:32px}}
.rp-icon svg{{display:block;width:100%;height:100%}}
.rp-body{{padding:16px 18px 17px;display:flex;flex-direction:column;flex:1 1 auto}}
.rp-label{{font-weight:700;font-size:16px;letter-spacing:-.01em;color:var(--ink)}}
.rp-date{{color:var(--muted);font-size:12px;letter-spacing:.02em}}
.rp-sub{{color:var(--muted);font-size:13.5px;margin-top:4px}}
.rp-meta{{display:flex;justify-content:space-between;align-items:center;
margin-top:auto;padding-top:14px}}
.rp-cta{{color:var(--sindoor);font-weight:700;font-size:14px}}
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
<h1>Namaste, {greeting} 🙏</h1>
<p>Your saved details and reports, all in one place.</p>
</div></div>
<div class="wrap">
<div class="card"><h2>Your Details</h2>{details}<div class="name-msg" id="nameMsg">Saved.</div></div>
<div class="section-title">Your Reports</div>
{reports_block}
<button class="logout" onclick="logout()">Log out</button>
</div>
<script>
async function saveName(e){{
  e.preventDefault();
  var inp=document.getElementById('nameInput');
  var btn=document.querySelector('.name-save');
  var msg=document.getElementById('nameMsg');
  var hint=document.querySelector('.name-hint');
  btn.disabled=true;
  try{{
    var r=await fetch('/api/account/name',{{method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body:JSON.stringify({{name:inp.value}})}});
    if(r.ok){{
      msg.style.display='block';
      if(hint) hint.style.display='none';
      setTimeout(function(){{msg.style.display='none';}},2500);
    }}
  }}catch(err){{}}
  btn.disabled=false;
  return false;
}}
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


def _safe_next(nxt: str) -> str:
    """Allowlist for post-login redirects: same-origin path only. Anything
    else (full URLs, protocol-relative //evil.com, backslash tricks) falls
    back to /account."""
    nxt = (nxt or "").strip()
    if nxt.startswith("/") and not nxt.startswith("//") and "\\" not in nxt:
        return nxt
    return "/account"


@app.get("/login", include_in_schema=False)
def login_page(request: Request):
    if _current_user(request):
        return RedirectResponse(_safe_next(request.query_params.get("next", "")),
                                status_code=302)
    path = os.path.join(PAGES_DIR, "login.html")
    if os.path.exists(path):
        return _serve_page_with_nav(path)
    raise HTTPException(404, "not found")


class AccountNameIn(BaseModel):
    name: str


@app.post("/api/account/name")
def account_set_name(body: AccountNameIn, request: Request):
    """Let the logged-in user set/edit their own account name. Session-gated —
    only the owner of the session can edit their own name. The account name is
    NOT auto-set at payment time (a milan report's name is a couple), so this is
    how a user gives their account a personal name."""
    user = _current_user(request)
    if not user:
        raise HTTPException(401, "not logged in")
    users.set_user_name(db, user["id"], body.name)
    return {"ok": True, "name": (body.name or "").strip()[:80]}


@app.get("/account", include_in_schema=False)
def account_page(request: Request):
    """Post-login dashboard: the user's saved details + their past reports.
    Redirects to /login when there's no valid session."""
    user = _current_user(request)
    if not user:
        # carry the destination so the OTP page can bounce straight back here
        return RedirectResponse("/login?next=%2Faccount", status_code=302)
    reports = users.get_user_reports(db, user["id"])
    return HTMLResponse(_inject_tracking(_inject_nav(_render_account(user, reports))))


extensions.install(app, {                      # (#6)(#7)(#8)(#9) feature endpoints
    "db": db, "get_report": get_report,
    "render": _render_for, "valid_admin_key": _valid_admin_key,
})

# Admin dashboard plugin (self-contained; /admin + /api/admin/*). Wrapped so an
# import/registration error can NEVER take down the rest of the app — the site
# works exactly as before if this fails or STATS_KEY is unset.
try:
    import dashboard
    dashboard.install(app, {"db": db, "get_report": get_report,
                            "valid_admin_key": _valid_admin_key,
                            "order_amount_paise": _order_amount_paise})
except Exception as _e:  # pragma: no cover - defensive guard
    logging.getLogger("api").warning("dashboard plugin not loaded: %s", _e)


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


@app.get("/api/narrative_preview/{rid}", include_in_schema=False)
def narrative_preview(rid: str, key: str = ""):
    """Admin: preview the LLM narrative for an existing report without paying.
    Returns the config being used + the generated prose (or {} if the layer is
    off / the model call failed). Gate: ?key=<STATS_KEY>. Create a report via
    /hi/compatibility, take its report_id, then GET this with your admin key."""
    if not _valid_admin_key(key):
        raise HTTPException(403, "forbidden")
    rec = get_report(rid)
    if not rec:
        raise HTTPException(404, "report not found")
    payload = rec["payload"]
    return {
        "report_id": rid,
        "product": payload.get("product"),
        "meta_lang": (payload.get("meta") or {}).get("lang"),
        "enabled": narrative.enabled(),
        "provider": narrative._provider(),
        "model": narrative._model(),
        "resolved_lang": narrative._resolve_lang(payload),
        "narrative": narrative.generate_narrative(payload),
    }


@app.get("/en/compatibility", include_in_schema=False)
def compatibility_en():
    """English love-compatibility (milan) landing at /en/compatibility."""
    return _serve_page_with_nav(os.path.join(PAGES_DIR, "milan.html"))


@app.get("/hi/compatibility", include_in_schema=False)
def compatibility_hi():
    """Hindi (Devanagari) love-compatibility landing at /hi/compatibility."""
    return _serve_page_with_nav(os.path.join(PAGES_DIR, "milan.hi.html"), lang="hi")


@app.get("/en/marriage", include_in_schema=False)
def marriage_en():
    """English marriage-timing (shaadi) landing at /en/marriage."""
    return _serve_page_with_nav(os.path.join(PAGES_DIR, "shaadi.html"))


@app.get("/hi/marriage", include_in_schema=False)
def marriage_hi():
    """Hindi (Devanagari) marriage-timing landing at /hi/marriage."""
    return _serve_page_with_nav(os.path.join(PAGES_DIR, "shaadi.hi.html"), lang="hi")


@app.get("/en/marriage-v2", include_in_schema=False)
def marriage_v2_en():
    """English marriage-timing landing — direct-to-payment A/B variant (v2) at
    /en/marriage-v2. Runs ALONGSIDE /en/marriage (shaadi.html); does not replace
    it. Funnel: form -> Razorpay -> WhatsApp, with an on-page benefit preview and
    a full sample report in a modal."""
    return _serve_page_with_nav(os.path.join(PAGES_DIR, "marriage-v2.html"))


@app.get("/hi/marriage-v2", include_in_schema=False)
def marriage_v2_hi():
    """Hindi (Devanagari) counterpart of /en/marriage-v2."""
    return _serve_page_with_nav(os.path.join(PAGES_DIR, "marriage-v2.hi.html"), lang="hi")


@app.get("/en/marriage-v3", include_in_schema=False)
def marriage_v3_en():
    """English marriage-timing landing — parent-voice variant (v3) at
    /en/marriage-v3. Same direct-to-payment funnel as /en/marriage-v2, copy
    rewritten for a parent asking about their child's marriage timing."""
    return _serve_page_with_nav(os.path.join(PAGES_DIR, "marriage-v3.html"))


@app.get("/hi/marriage-v3", include_in_schema=False)
def marriage_v3_hi():
    """Hindi (Devanagari) counterpart of /en/marriage-v3."""
    return _serve_page_with_nav(os.path.join(PAGES_DIR, "marriage-v3.hi.html"), lang="hi")


@app.get("/shaadi", include_in_schema=False)
def shaadi_redirect(request: Request):
    """Legacy /shaadi → /en/marriage (301 permanent). Preserves query string
    so already-issued unlock links like /shaadi?pass=<token> keep working."""
    q = request.url.query
    return RedirectResponse("/en/marriage" + (f"?{q}" if q else ""), status_code=301)


@app.get("/milan", include_in_schema=False)
def milan_redirect(request: Request):
    """Legacy /milan → /en/compatibility (301 permanent). Preserves query string
    so already-issued unlock links like /milan?pass=<token> keep working."""
    q = request.url.query
    return RedirectResponse("/en/compatibility" + (f"?{q}" if q else ""), status_code=301)


@app.get("/match", include_in_schema=False)
def match_redirect(request: Request):
    """Legacy /match (Hinglish milan funnel) → /en/compatibility (301 permanent).
    Mirrors /milan above; older reports/PDFs carried links pointing here, so
    they keep working. Preserves query string so already-issued unlock links
    like /match?pass=<token> keep working."""
    q = request.url.query
    return RedirectResponse("/en/compatibility" + (f"?{q}" if q else ""), status_code=301)


@app.get("/{slug}", include_in_schema=False)
def serve_page(slug: str):
    """Serve pages/<slug>.html — every file in pages/ becomes a landing page."""
    if not slug.replace("-", "").isalnum():
        raise HTTPException(404, "not found")
    path = os.path.join(PAGES_DIR, f"{slug}.html")
    if os.path.exists(path):
        return _serve_page_with_nav(path)
    raise HTTPException(404, "not found")
