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
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, Response
from pydantic import BaseModel, field_validator

from engine import compute_report
from report_view import render_report, render_milan, render_blueprint, north_chart_svg
from products import compute_milan, compute_blueprint
from geocoding import resolve as geocode          # (#1) accurate, cached geocoding
from geocoding import resolve_detailed             # (#1) with resolved/source provenance
import payments, delivery, extensions
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


PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")   # e.g. https://axtroshastra.com

# ---- Twilio WhatsApp delivery (all optional; no-op until env vars set) ----
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "")     # 'whatsapp:+14155238886' (sandbox) or your sender
TWILIO_CONTENT_SID = os.getenv("TWILIO_CONTENT_SID", "")  # approved template SID for production

def send_whatsapp_report(phone: str, rid: str, name: str):
    """Fire-and-forget WhatsApp delivery after payment. Never raises."""
    if not (TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM and phone and PUBLIC_BASE_URL):
        return
    try:
        from twilio.rest import Client
        to = phone if phone.startswith("+") else "+91" + phone[-10:]
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        link = f"{PUBLIC_BASE_URL}/report/{rid}"
        if TWILIO_CONTENT_SID:                       # production: approved template
            client.messages.create(
                from_=TWILIO_FROM, to=f"whatsapp:{to}",
                content_sid=TWILIO_CONTENT_SID,
                content_variables=json.dumps({"1": name, "2": link}))
        else:                                        # sandbox / 24h session freeform
            client.messages.create(
                from_=TWILIO_FROM, to=f"whatsapp:{to}",
                body=(f"Namaste {name}! 🙏 Aapki Axtroshastra Marriage Timing "
                      f"Report ready hai:\n{link}\n\nPDF download button report "
                      f"ke andar hai. Koi bhi sawaal ho — reply kijiye. "
                      f"100% refund within 7 days."))
    except Exception as e:                            # delivery must never break the webhook
        logger.error("[twilio] send failed for %s: %s", rid, e)

def _render_for(product, payload):
    if product == "milan":
        return render_milan(payload)
    if product == "blueprint":
        return render_blueprint(payload)
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
    product: str = "marriage"          # marriage | blueprint

    @field_validator("time_quality")
    @classmethod
    def _tq(cls, v):
        if v not in ("T0", "T1", "T2", "T3"): raise ValueError("bad time_quality")
        return v

BAND_MID = {"subah": "07:00", "din": "13:00", "shaam": "19:00", "raat": "01:00"}

# ----------------------------------------------------------------- routes
PAGES_DIR = os.path.join(BASE, "pages")


@app.get("/healthz", include_in_schema=False)
def healthz():
    """Liveness/readiness probe: 200 only if the database is reachable."""
    try:
        with db() as c:
            c.execute("SELECT 1")
        return {"status": "ok"}
    except Exception as e:
        logger.error("healthz db check failed: %s", e)
        raise HTTPException(503, "db unavailable")


@app.get("/", include_in_schema=False)
def landing():
    """Homepage serves the main funnel page (pages/home.html overrides if present)."""
    for candidate in ("home.html", "shaadi.html"):
        path = os.path.join(PAGES_DIR, candidate)
        if os.path.exists(path):
            return FileResponse(path)
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
    order = rzp_client().order.create({
        "amount": PRICE_PAISE, "currency": "INR",
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
                    rec["payload"]["meta"]["name"])
                email = rec["payload"]["meta"].get("_email")
                if email:                        # (#7) email + PDF delivery
                    background_tasks.add_task(email_report, email, rid, rec["payload"])
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
    return {"paid": True, "report": payload}


@app.get("/report/{rid}", include_in_schema=False)
def report_page(rid: str):
    rec = get_report(rid)
    if not rec or not rec["paid"]:
        return HTMLResponse("<h3 style='font-family:sans-serif;padding:40px'>"
                            "Report not found ya payment pending hai. "
                            "<a href='/'>Wapas jaayein</a></h3>", status_code=404)
    payload = _refresh_current_period(rec["payload"])
    payload.setdefault("meta", {})["report_id"] = rid
    product = payload.get("product", "marriage")
    if product == "milan":
        return HTMLResponse(render_milan(payload))
    if product == "blueprint":
        return HTMLResponse(render_blueprint(payload))
    return HTMLResponse(render_report(payload))


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
    urls = ["/", "/shaadi", "/milan", "/jeevan", "/match", "/blog",
            "/privacy", "/terms", "/refunds"] + [f"/blog/{s}" for s in BLOG_SLUGS]
    body = "".join(f"<url><loc>{base_url}{u}</loc></url>" for u in urls)
    return Response(content='<?xml version="1.0" encoding="UTF-8"?>'
                    f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>',
                    media_type="application/xml")


@app.get("/robots.txt", include_in_schema=False)
def robots():
    base_url = PUBLIC_BASE_URL or "https://www.axtroshastra.com"
    return PlainTextResponse(f"User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /report/\nSitemap: {base_url}/sitemap.xml")


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
                              f"{base}/jeevan?pass={toks[0]}"],
            "note": "Each token unlocks exactly ONE report, on any product page."}


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


extensions.install(app, {                      # (#6)(#7)(#8)(#9) feature endpoints
    "db": db, "get_report": get_report,
    "render": _render_for, "valid_admin_key": _valid_admin_key,
})


@app.get("/{slug}", include_in_schema=False)
def serve_page(slug: str):
    """Serve pages/<slug>.html — every file in pages/ becomes a landing page."""
    if not slug.replace("-", "").isalnum():
        raise HTTPException(404, "not found")
    path = os.path.join(PAGES_DIR, f"{slug}.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(404, "not found")
