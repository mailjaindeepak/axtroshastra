# Axtroshastra

**Computational Vedic astrology (Jyotish), calculated — no opinion, only calculation.**

Axtroshastra is a mobile-first web product for an Indian audience. A user enters
their birth details, gets a free teaser, pays **₹499 via Razorpay**, and unlocks a
full report (also delivered on WhatsApp). All copy is bilingual Hindi-English
("Hinglish"). The astrology is **pure calculation** — Swiss Ephemeris plus classical
tables. No LLM is used anywhere in the engine.

## Products

All three are built on one deterministic astronomy engine:

1. **Marriage Timing** (`marriage`) — marriage windows over a 10-year horizon.
2. **Kundli Milan** (`milan`) — Ashtakoota 36-guna couple compatibility.
3. **Life Blueprint** (`blueprint`) — personality, career, wealth, health, dasha roadmap.

## Architecture

| File | Role |
|------|------|
| `api.py` | FastAPI web layer — all routes, storage, payments, WhatsApp delivery. |
| `engine.py` | Core marriage-timing Jyotish engine (`pyswisseph`, sidereal + Lahiri, whole-sign). |
| `products.py` | Milan (Ashtakoota) and Blueprint engines, reusing `compute_chart`. |
| `jyotish_maps.py` | Pure data: nakshatra profiles, remedies, koota text. No logic. |
| `report_view.py` | Deterministic HTML report renderers (marriage / milan / blueprint). |
| `cities_in.py` | Indian city → (lat, lon, IST) lookup for geocoding. |
| `backtest.py` | Validation harness: hit-rate and lift over baseline vs known marriage dates. |
| `pages/` | Landing/funnel pages, legal pages, and Hinglish SEO blog. |

**Trust boundary is server-side.** The price and the full report never leave the
server before payment; only the teaser is exposed. Payment truth is the
**HMAC-verified Razorpay webhook**, never the client.

## Local development

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then fill in values (set DEMO_MODE=1 for local payment bypass)
uvicorn api:app --reload
```

Visit http://localhost:8000. With `DEMO_MODE=1` you can unlock a report locally via
`POST /api/_demo_pay/{report_id}` instead of paying.

### Smoke test & backtest

```bash
python engine.py                    # prints a sample T0 chart (1995-08-15, Delhi)
python backtest.py charts.csv       # hit-rate & lift; see backtest_template.csv for columns
```

### Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Configuration

All configuration is via environment variables — see [`.env.example`](.env.example)
for the full list. Secrets (Razorpay keys, webhook secret, Twilio, `STATS_KEY`) must
**only** be set via env, never committed.

## Deployment

`Procfile` runs `uvicorn api:app` (Railway / Render style). Before going live:

1. Razorpay **Settings > Payment capture → AUTO capture** (otherwise `payment.captured`
   never fires).
2. Razorpay **Settings > Webhooks →** `https://<your-domain>/api/webhook`, event
   `payment.captured`.
3. Mount a **persistent volume** at the `DB_PATH` directory (SQLite database).
4. Set all secrets in the host dashboard. Never set `DEMO_MODE=1` in production.

Health check for the platform: `GET /healthz`.

## Admin endpoints

Gated by the `STATS_KEY` env var (constant-time compared):

- `GET /api/stats?key=...` — per-variant funnel counts and revenue.
- `GET /api/make_pass?key=...&n=5` — one-time free-unlock tokens for soft launch.

---

Axtroshastra · Computational Vedic Astrology · by Cultnuts
