# Axtroshastra — Codebase Understanding (Project Memory)

_Last reviewed: 2026-07-12. Python 3.11 FastAPI app, ~2,800 lines across 7 Python modules + HTML pages._

## What it is
Axtroshastra is a **computational Vedic astrology (Jyotish) web product** targeting an Indian audience. Users enter birth details, get a **free teaser**, pay **₹499 via Razorpay**, and unlock a full mobile-first report (also delivered on WhatsApp). Copy is bilingual Hindi-English ("Hinglish"). Positioning: "Jyotish, calculated — no opinion, only calculation."

Three products, all built on one deterministic astronomy engine:
1. **Marriage timing** (`marriage`) — predicts marriage windows over a 10-year horizon.
2. **Kundli Milan** (`milan`) — Ashtakoota 36-guna couple compatibility.
3. **Life Blueprint** (`blueprint`) — personality, career, wealth, health, dasha roadmap.

## Architecture / request flow
- **`api.py`** — FastAPI app (the only web layer). Key routes:
  - `POST /api/kundli` → geocode place, compute FULL report server-side, store in SQLite, return **teaser only**.
  - `POST /api/milan` → compatibility report, teaser only.
  - `POST /api/order` → create a LIVE Razorpay order bound to `report_id` (also handles free-unlock `pass` tokens).
  - `POST /api/webhook` → Razorpay `payment.captured`, **HMAC-SHA256 verified**, is the source of truth for marking a report paid; fires WhatsApp delivery as a background task.
  - `GET /api/report/{id}` → full JSON only if paid, else teaser.
  - `GET /report/{id}` → renders HTML report (marriage/milan/blueprint) only if paid.
  - Static/SEO/content: `/`, `/{slug}` (serves `pages/*.html`), `/blog`, `/blog/{slug}`, `/sitemap.xml`, `/robots.txt`, `/static/{fname}`.
  - Admin (gated by `STATS_KEY` env): `/api/stats` (per-variant funnel + revenue), `/api/make_pass` (one-time free-unlock tokens), `/api/count` (public honest counter, hidden below 50).
  - `DEMO_MODE=1` exposes `/api/_demo_pay/{rid}` for local testing (never set in prod).
- **`engine.py`** — the core **marriage-timing Jyotish engine**. No LLM anywhere. Uses `pyswisseph` (Moshier model, no ephemeris files), **sidereal zodiac + Lahiri ayanamsa**, **whole-sign houses**. Pipeline: `compute_chart` (planets/lagna/nakshatras, dignity, combustion) → `vimshottari_tree` (Mahadasha/Antardasha timeline from Moon nakshatra) → `marriage_significators` (7th lord, Venus/Jupiter karakas, darakaraka, nodes) → `score_ad` (rule-based scoring of each antardasha, see RULES table) → `transit_gate` (monthly-sampled Jupiter/Saturn transits) → grade (Strong/Moderate/Building) → merge adjacent windows, cap 3, never-zero fallback. Also `manglik()` detection + cancellations, and a deterministic **REPORT EXTRAS** section (sade sati, past-period analysis, per-year outlook, nakshatra profile, Venus love-style, remedies).
- **`products.py`** — the other two product engines, reusing `compute_chart` from engine.py. `compute_milan` implements the 8 Ashtakoota kootas (Varna, Vashya, Tara, Yoni, Graha Maitri, Gana, Bhakoot, Nadi) with classical dosha **cancellation rules** and couple-voiced interpretation. `compute_blueprint` produces persona, career direction (10th lord), strengths/lessons, 3-mahadasha roadmap, elements, wealth (2nd/11th lord), health (6th house), relationship, year-ahead.
- **`jyotish_maps.py`** — pure data: 27 nakshatra profiles, Venus styles, wealth/health text, element pair dynamics, couple-voiced koota text, remedies keyed to 7th lord. No logic.
- **`report_view.py`** — largest file (~740 lines). Deterministic HTML template renderers: `render_report` (9-page marriage report incl. North-Indian chart SVG), `render_milan`, `render_blueprint`. Every fact comes from the payload; comments note an LLM narrative layer could later swap section text via the same slots.
- **`cities_in.py`** — auto-generated dict of top Indian cities → (lat, lon, 5.5 IST). `api.geocode()` checks a small hardcoded `CITY_CACHE`, then `CITIES_IN`, then falls back to Delhi coords (latitude only affects lagna, not dasha timeline). A prod upgrade note suggests wiring Google Geocoding.
- **`backtest.py`** — validation harness. Takes a CSV of known people + actual marriage dates, computes windows as-of (marriage − 5y), reports hit-rate, grade breakdown, and **lift over chance baseline** (window coverage). Warns if lift < 1.3x.
- **`pages/`** — landing/funnel pages (`home.html`, `shaadi.html`, `milan.html`, `jeevan.html`, `match.html`), legal (`privacy`, `terms`, `refunds`), and `blog/` (5 Hinglish SEO articles). Include Google Analytics + Meta Pixel. Multiple funnel variants tracked via a `variant` field for A/B attribution.

## Key design decisions & conventions
- **Trust boundary is server-side.** Price (`PRICE_PAISE = 49900`) and the full report never leave the server before payment; only the teaser is exposed. Payment truth = HMAC-verified webhook, not the client.
- **Determinism is a core value.** The astrology is pure calculation (Swiss Ephemeris + classical tables); LLMs are explicitly excluded from the engine. Content maps are hand-authored data.
- **Birth-time uncertainty is modeled** via time_quality tiers: `T0` exact, `T1` approx ±45m, `T2` time-band, `T3` unknown. Lower confidence falls back to **Chandra lagna** (Moon sign) instead of ascendant, widens window padding, and caps grades at "Moderate".
- **Storage:** SQLite (`DB_PATH`, default `./data/reports.db`, mount a volume). Two tables: `reports` and `passes`. Thread-locked writes.
- **Deploy:** `Procfile` runs `uvicorn api:app`; Railway/Render style. Secrets (Razorpay keys, webhook secret, Twilio, STATS_KEY, PUBLIC_BASE_URL) via env vars only.
- **Dependencies** (`requirements.txt`): fastapi, uvicorn, pyswisseph 2.10, pydantic 2, razorpay 1.4, twilio.

## Notable code smells / TODOs spotted
- `api.py` has a duplicated `PAGES_DIR = ...` line and defines `STATS_KEY` **after** the `make_pass` route that uses it (works because it's read at call time, but fragile ordering).
- `geocode` silently falls back to Delhi for unknown towns — acceptable per comment (latitude only shifts lagna) but affects T0/T1 accuracy.
- `compute_milan` Bhakoot-bad logic (`{dist, rev} & {(2, 12) and 2, 12, 5, 9, 6, 8}`) is convoluted; correctness rests on the following `{dist,rev} in [...]` membership check.
- `compute_chart` builds Graha with a slightly awkward `*nak_of(lo)[0:1]` unpack plus a second `nak_of` call.

## How to run locally
- `pip install -r requirements.txt`, then `uvicorn api:app --reload`. Set `DEMO_MODE=1` to bypass real payment via `/api/_demo_pay/{rid}`.
- Engine smoke test: `python engine.py` (T0 chart for 1995-08-15, Delhi).
- Backtest: `python backtest.py charts.csv` (template columns in `backtest_template.csv`).

---

## 2026-07-12 — Production hardening + world-class feature pass

**Commit 1 (f9404e2) — production readiness (no behaviour changes):**
- Added `.gitignore`, `.gitattributes` (normalize CRLF→LF; the working tree had been
  CRLF-ified on upload while HEAD was LF), `README.md`, `.env.example`, `requirements-dev.txt`.
- `api.py`: added `GET /healthz` DB probe; moved `STATS_KEY` into the config block with a
  constant-time `_valid_admin_key()`; consolidated imports; removed the duplicate `PAGES_DIR`;
  `logging` instead of `print`.
- `report_view.py`: **HTML-escaped** user-supplied `name`/`p1`/`p2` (fixed a stored-XSS hole;
  `from html import escape`).
- Added a pytest suite (`tests/`): engine determinism, teaser gating, webhook signature,
  admin gating, XSS escaping.

**Commit 2 — 7 approved enhancements (all new modules, minimal api.py wiring):**
- **#1 geocoding.py** — `resolve(place)`: CITY_CACHE → CITIES_IN → SQLite `geocache` →
  external (Nominatim default / Google via key) → Delhi fallback. IST for India; optional
  `timezonefinder` elsewhere. api.py now does `from geocoding import resolve as geocode`.
- **#8 divisional.py** — D9 Navamsa, D10 Dasamsa, classical yogas (Gajakesari, Budha-Aditya,
  Chandra-Mangala, Pancha Mahapurusha, Neecha Bhanga, Dharma-Karmadhipati), and
  **ashtakavarga** (bhinna per planet + sarva). Invariant enforced in tests: SAV total = 337.
  Exposed at `GET /api/deep/{rid}` (paid-gated); needs birth data, so create_kundli now stores
  `meta._birth = {dob,tob,tz,lat,lon}`.
- **#4 ratelimit.py** — per-IP token-bucket `RateLimitMiddleware` (path policies; payment/compute
  routes stricter, webhook lenient) + `captcha_ok()` (hCaptcha/reCAPTCHA, env-gated, off by
  default). Wired: `app.add_middleware`, captcha checked in create_kundli/create_milan.
- **#6 payments.py** — webhook idempotency via `webhook_events` table (dedupe by payment id),
  `reconcile()` (recovers missed webhooks vs Razorpay), `refund()`. Admin routes
  `POST /api/reconcile`, `POST /api/refund` (STATS_KEY-gated). Webhook now dedupes + records.
- **#7 delivery.py** — `html_to_pdf()` (WeasyPrint→xhtml2pdf fallback) + SMTP `send_email()`.
  `GET /report/{rid}/pdf` (paid-gated); optional `email` field on kundli/milan triggers
  email+PDF on payment. `xhtml2pdf` added to requirements.
- **#9 i18n.py** — dict catalogs (hi_en/hi/en authored; mr/ta/te/bn/gu/kn inherit Hinglish),
  `t(key,lang)`, `normalize_lang`, `coverage`. `GET /api/i18n?lang=` returns catalog + langs.
- **#3 regression** — `tests/test_regression.py` golden snapshots (`tests/golden/`,
  regen via `tests/regen_golden.py`) pinned with `as_of=2025-01-01`; `.github/workflows/ci.yml`
  runs pytest on push/PR.
- New endpoints live in **extensions.py** (`install(app, ctx)`) to keep api.py churn small.
- Full suite: **29 tests passing**.

**Remaining approved-but-not-yet-built roadmap items:** #2 Postgres migration,
#5 observability (Sentry/metrics), #10 admin dashboard + Docker/CI image. (User chose
"no preference" on the scale/ops group this session.)

**Env added** (see `.env.example`): GEOCODER, GOOGLE_GEOCODING_KEY, GEOCODER_USER_AGENT,
RATE_LIMIT_ENABLED, CAPTCHA_PROVIDER, CAPTCHA_SECRET, SMTP_* , LOG_LEVEL.

**Infra note (Cowork mount):** the connected Windows folder blocks `unlink`, so git index/lock
writes corrupt; commits here were made with `GIT_INDEX_FILE=/tmp/...`. Large existing files are
size-capped by the Write tool — edit them via shell `truncate`+append. Pushing must be done by
the user (no GitHub creds in the sandbox).
