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
import hashlib, hmac, json, os, secrets, sqlite3, threading
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, field_validator

from engine import compute_report
from report_view import render_report, render_milan, render_blueprint
from products import compute_milan, compute_blueprint

app = FastAPI(title="Axtroshastra API", docs_url=None, redoc_url=None)
BASE = os.path.dirname(os.path.abspath(__file__))

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
        print(f"[twilio] send failed for {rid}: {e}")

RZP_KEY = os.getenv("RAZORPAY_KEY_ID", "")
RZP_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RZP_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
DEMO_MODE = os.getenv("DEMO_MODE") == "1"
PRICE_PAISE = 49900                       # ₹499 — server-side only, never trust client

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
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS reports(
        id TEXT PRIMARY KEY, payload TEXT NOT NULL, paid INTEGER DEFAULT 0,
        order_id TEXT, payment_id TEXT, phone TEXT, created_at TEXT)""")
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
from cities_in import CITIES_IN
CITY_CACHE = {
    "delhi": (28.61, 77.21, 5.5),      "new delhi": (28.61, 77.21, 5.5),
    "mumbai": (19.08, 72.88, 5.5),     "bangalore": (12.97, 77.59, 5.5),
    "bengaluru": (12.97, 77.59, 5.5),  "hyderabad": (17.38, 78.49, 5.5),
    "chennai": (13.08, 80.27, 5.5),    "kolkata": (22.57, 88.36, 5.5),
    "pune": (18.52, 73.86, 5.5),       "jaipur": (26.91, 75.79, 5.5),
    "lucknow": (26.85, 80.95, 5.5),    "faridabad": (28.41, 77.31, 5.5),
    "gurgaon": (28.46, 77.03, 5.5),    "noida": (28.54, 77.39, 5.5),
    "ahmedabad": (23.02, 72.57, 5.5),  "surat": (21.17, 72.83, 5.5),
    "kanpur": (26.45, 80.33, 5.5),     "patna": (25.59, 85.14, 5.5),
    "indore": (22.72, 75.86, 5.5),     "bhopal": (23.26, 77.41, 5.5),
    "nagpur": (21.15, 79.09, 5.5),     "varanasi": (25.32, 82.99, 5.5),
    "agra": (27.18, 78.01, 5.5),       "meerut": (28.98, 77.71, 5.5),
    "ludhiana": (30.90, 75.86, 5.5),   "chandigarh": (30.73, 76.78, 5.5),
    "amritsar": (31.63, 74.87, 5.5),   "dehradun": (30.32, 78.03, 5.5),
    "ranchi": (23.34, 85.31, 5.5),     "raipur": (21.25, 81.63, 5.5),
    "guwahati": (26.14, 91.74, 5.5),   "kochi": (9.93, 76.27, 5.5),
    "coimbatore": (11.02, 76.96, 5.5), "visakhapatnam": (17.69, 83.22, 5.5),
    "vijayawada": (16.51, 80.65, 5.5), "thiruvananthapuram": (8.52, 76.94, 5.5),
    "mysore": (12.30, 76.64, 5.5),     "jodhpur": (26.24, 73.02, 5.5),
    "udaipur": (24.58, 73.71, 5.5),    "gwalior": (26.22, 78.18, 5.5),
    "allahabad": (25.44, 81.85, 5.5),  "prayagraj": (25.44, 81.85, 5.5),
    "ghaziabad": (28.67, 77.42, 5.5),  "nashik": (19.99, 73.79, 5.5),
    "aurangabad": (19.88, 75.34, 5.5), "rajkot": (22.30, 70.80, 5.5),
    "vadodara": (22.31, 73.19, 5.5),   "srinagar": (34.08, 74.80, 5.5),
    "jammu": (32.73, 74.87, 5.5),      "shimla": (31.10, 77.17, 5.5),
    # extend to ~500 from census CSV
}

def geocode(place: str):
    key = place.lower().split(",")[0].strip()
    if key in CITY_CACHE:
        return CITY_CACHE[key]
    if key in CITIES_IN:
        return CITIES_IN[key]
    # Fallback for unknown Indian towns: use Delhi coords, IST timezone.
    # Latitude affects only lagna (T0/T1); dasha timeline is latitude-free.
    # PROD upgrade: Google Geocoding API here, cache the result into the table.
    return (28.61, 77.21, 5.5)

# ----------------------------------------------------------------- models
class KundliIn(BaseModel):
    name: str
    dob: str
    tob: str | None = None
    time_quality: str = "T0"
    time_band: str | None = None
    place: str
    gender: str | None = None
    variant: str | None = None
    product: str = "marriage"          # marriage | blueprint

    @field_validator("time_quality")
    @classmethod
    def _tq(cls, v):
        if v not in ("T0", "T1", "T2", "T3"): raise ValueError("bad time_quality")
        return v

BAND_MID = {"subah": "07:00", "din": "13:00", "shaam": "19:00", "raat": "01:00"}

# ----------------------------------------------------------------- routes
PAGES_DIR = os.path.join(BASE, "pages")

PAGES_DIR = os.path.join(BASE, "pages")


@app.get("/", include_in_schema=False)
def landing():
    """Homepage serves the main funnel page (pages/home.html overrides if present)."""
    for candidate in ("home.html", "shaadi.html"):
        path = os.path.join(PAGES_DIR, candidate)
        if os.path.exists(path):
            return FileResponse(path)
    return HTMLResponse("<h3 style='font-family:sans-serif;padding:40px'>Axtroshastra</h3>")


@app.post("/api/kundli")
def create_kundli(inp: KundliIn):
    lat, lon, tz = geocode(inp.place)
    if inp.time_quality in ("T0", "T1"):
        if not inp.tob: raise HTTPException(422, "tob required")
        tob = inp.tob
    elif inp.time_quality == "T2":
        tob = BAND_MID.get(inp.time_band or "", "13:00")
    else:
        tob = "12:00"
    if inp.product == "blueprint":
        report = compute_blueprint(inp.name, inp.dob, tob, tz, lat, lon,
                                   time_quality=inp.time_quality)
    else:
        report = compute_report(name=inp.name, dob=inp.dob, tob=tob,
                                tz_offset_hours=tz, lat=lat, lon_geo=lon,
                                female=(inp.gender == "female"),
                                time_quality=inp.time_quality)
    report["meta"]["variant"] = (inp.variant or "direct")[:64]
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
    return {"ok": True}


@app.get("/api/report/{rid}")
def get_report_api(rid: str):
    rec = get_report(rid)
    if not rec: raise HTTPException(404, "report not found")
    if not rec["paid"]:
        return {"paid": False, "teaser": rec["payload"]["teaser"]}
    return {"paid": True, "report": rec["payload"]}


@app.get("/report/{rid}", include_in_schema=False)
def report_page(rid: str):
    rec = get_report(rid)
    if not rec or not rec["paid"]:
        return HTMLResponse("<h3 style='font-family:sans-serif;padding:40px'>"
                            "Report not found ya payment pending hai. "
                            "<a href='/'>Wapas jaayein</a></h3>", status_code=404)
    payload = rec["payload"]
    product = payload.get("product", "marriage")
    if product == "milan":
        return HTMLResponse(render_milan(payload))
    if product == "blueprint":
        return HTMLResponse(render_blueprint(payload))
    return HTMLResponse(render_report(payload))


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

@app.post("/api/milan")
def create_milan(inp: MilanIn):
    lat1, lon1, tz1 = geocode(inp.p1_place)
    lat2, lon2, tz2 = geocode(inp.p2_place)
    report = compute_milan(
        {"name": inp.p1_name, "dob": inp.p1_dob, "tob": inp.p1_tob,
         "tz": tz1, "lat": lat1, "lon": lon1},
        {"name": inp.p2_name, "dob": inp.p2_dob, "tob": inp.p2_tob,
         "tz": tz2, "lat": lat2, "lon": lon2})
    report["meta"]["variant"] = (inp.variant or "direct")[:64]
    rid = secrets.token_urlsafe(12)
    save_report(rid, report)
    return {"report_id": rid, "teaser": report["teaser"]}


from fastapi.responses import Response, PlainTextResponse

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

STATS_KEY = os.getenv("STATS_KEY", "")

@app.get("/api/stats")
def stats(key: str = ""):
    """Per-variant funnel counts. Protect with STATS_KEY env var."""
    if not STATS_KEY or key != STATS_KEY:
        raise HTTPException(403, "forbidden")
    with db() as c:
        rows = c.execute(
            """SELECT COALESCE(json_extract(payload,'$.meta.variant'),'direct') v,
                      COUNT(*), SUM(paid) FROM reports GROUP BY v"""
        ).fetchall()
    return {"variants": [{"page": r[0], "kundlis_created": r[1],
                          "paid_reports": r[2] or 0,
                          "revenue_inr": (r[2] or 0) * 499} for r in rows]}


@app.get("/{slug}", include_in_schema=False)
def serve_page(slug: str):
    """Serve pages/<slug>.html — every file in pages/ becomes a landing page."""
    if not slug.replace("-", "").isalnum():
        raise HTTPException(404, "not found")
    path = os.path.join(PAGES_DIR, f"{slug}.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(404, "not found")
