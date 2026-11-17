#!/usr/bin/env python3
"""
tracker.py — Daily ad spend from Twitter/X Ads API, broken down to the ad level.

Output: Date | Ad Account | Campaign Name | Ad Set Name | Ad Name | Spend | Currency

Usage (run from codebase/axtroshastra/):

    python ops/twitter_spend/tracker.py discover                # list accessible accounts
    python ops/twitter_spend/tracker.py fetch                   # yesterday's spend
    python ops/twitter_spend/tracker.py fetch --days 7          # last 7 days
    python ops/twitter_spend/tracker.py fetch --start 2026-11-01 --end 2026-11-15
    python ops/twitter_spend/tracker.py report --days 30
    python ops/twitter_spend/tracker.py export --csv spend.csv
    python ops/twitter_spend/tracker.py export --sheet           # → ROAS Tracker sheet

Credentials: config.json (copy config.example.json), or env vars:
    TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET,
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET

Twitter Ads hierarchy mapped to output columns:
    Campaign  → Campaign Name
    Line Item → Ad Set Name     (targeting / bidding unit)
    Promoted Tweet → Ad Name    (shows as "tweet:<id>")

For Google Sheets: same sa_key.json setup as ad_revenue.py.
"""
import argparse
import csv
import io
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from zoneinfo import ZoneInfo

try:
    from requests_oauthlib import OAuth1Session
except ImportError:
    sys.exit("pip install requests-oauthlib")

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "spend.db"
CONFIG_PATH = HERE / "config.json"
API_BASE = "https://ads-api.x.com/12"

USD_TO_INR = 100

COLUMNS = [
    "date", "ad_account", "campaign_name", "adset_name", "ad_name",
    "ad_url", "landing_page", "utm_source", "utm_medium", "utm_campaign", "utm_content",
    "spend", "currency",
    "page_views", "form_starts", "leads", "purchases", "revenue_inr",
]
HEADER = [
    "Date", "Ad Account", "Campaign Name", "Ad Set Name", "Ad Name",
    "Ad URL", "Landing Page", "UTM Source", "UTM Medium", "UTM Campaign", "UTM Content",
    "Spend", "Currency",
    "Page Views", "Form Starts", "Leads", "Purchases", "Revenue (INR)",
]
ROAS_SHEET = "1cu-SUSgTnze9jwIpWyqaKl3S25yt2NbEu4j7bYuzJvY"


# ---- config -----------------------------------------------------------------

def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    env_map = {
        "TWITTER_CONSUMER_KEY": "consumer_key",
        "TWITTER_CONSUMER_SECRET": "consumer_secret",
        "TWITTER_ACCESS_TOKEN": "access_token",
        "TWITTER_ACCESS_TOKEN_SECRET": "access_token_secret",
    }
    missing = [k for k in env_map if not os.getenv(k)]
    if missing:
        sys.exit(f"Missing: {', '.join(missing)}\nSet env vars or create {CONFIG_PATH}")
    return {v: os.environ[k] for k, v in env_map.items()}


def get_session(config: dict) -> OAuth1Session:
    return OAuth1Session(
        config["consumer_key"],
        client_secret=config["consumer_secret"],
        resource_owner_key=config["access_token"],
        resource_owner_secret=config["access_token_secret"],
    )


# ---- API helpers ------------------------------------------------------------

def api_get(session: OAuth1Session, path: str, params: dict | None = None) -> dict:
    url = f"{API_BASE}{path}"
    for _ in range(3):
        resp = session.get(url, params=params)
        if resp.status_code == 429:
            reset = int(resp.headers.get("x-rate-limit-reset", time.time() + 60))
            wait = max(reset - int(time.time()), 5)
            print(f"  rate-limited, waiting {wait}s…", file=sys.stderr)
            time.sleep(wait)
            continue
        if resp.status_code == 200:
            return resp.json()
        print(f"  API {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
        resp.raise_for_status()
    raise RuntimeError(f"3 retries exhausted: {path}")


def paginate(session: OAuth1Session, path: str, params: dict | None = None) -> list:
    params = dict(params or {})
    params.setdefault("count", 1000)
    items = []
    while True:
        data = api_get(session, path, params)
        items.extend(data.get("data", []))
        cursor = data.get("next_cursor")
        if not cursor:
            break
        params["cursor"] = cursor
    return items


def resolve_accounts(session: OAuth1Session, config: dict) -> list[dict]:
    api_map = {a["id"]: a for a in paginate(session, "/accounts")}
    if config.get("accounts"):
        out = []
        for a in config["accounts"]:
            api = api_map.get(a["id"], {})
            out.append({
                "id": a["id"],
                "name": a.get("name", api.get("name", a["id"])),
                "currency": a.get("currency", api.get("currency", "USD")),
                "timezone": api.get("timezone", "UTC"),
            })
        return out
    return [
        {
            "id": a["id"], "name": a.get("name", a["id"]),
            "currency": a.get("currency", "INR"),
            "timezone": a.get("timezone", "UTC"),
        }
        for a in api_map.values()
        if a.get("approval_status") == "ACCEPTED"
    ]


def fetch_billing(
    session: OAuth1Session, account_id: str,
    entity: str, entity_ids: list[str],
    start: datetime, end: datetime,
) -> dict[str, list[int]]:
    """BILLING stats per entity. Returns {entity_id: [micro_per_day, …]}.
    start/end must be timezone-aware (account's local tz, midnight).
    Automatically chunks into 7-day windows (API max)."""
    if not entity_ids:
        return {}
    out: dict[str, list[int]] = {}

    # Break into 7-day windows
    window_start = start
    while window_start < end:
        window_end = min(window_start + timedelta(days=7), end)
        for i in range(0, len(entity_ids), 20):
            batch = entity_ids[i : i + 20]
            data = api_get(session, f"/stats/accounts/{account_id}", {
                "entity": entity,
                "entity_ids": ",".join(batch),
                "start_time": window_start.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "end_time": window_end.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "granularity": "DAY",
                "placement": "ALL_ON_TWITTER",
                "metric_groups": "BILLING",
            })
            for entry in data.get("data", []):
                id_data = entry.get("id_data") or [{}]
                micros = id_data[0].get("metrics", {}).get("billed_charge_local_micro") or []
                chunk = [v or 0 for v in micros]
                if entry["id"] in out:
                    out[entry["id"]].extend(chunk)
                else:
                    out[entry["id"]] = chunk
        window_start = window_end
    return out


# ---- tweet URL resolution ---------------------------------------------------

def _fetch_card_urls(session: OAuth1Session, account_id: str) -> dict[str, str]:
    """Fetch all cards for the account and return {card_id: website_url}."""
    card_urls: dict[str, str] = {}
    try:
        cards = paginate(session, f"/accounts/{account_id}/cards", {"count": 200})
        for c in cards:
            cid = str(c.get("id", ""))
            for comp in c.get("components", []):
                dest = comp.get("destination", {})
                if dest.get("url"):
                    card_urls[cid] = dest["url"]
                    break
    except Exception as e:
        print(f"  cards fetch error: {e}", file=sys.stderr)
    return card_urls


def _resolve_tweet_urls(
    session: OAuth1Session, account_id: str, tweet_ids: list[str],
) -> dict[str, str]:
    """Resolve destination URLs from promoted tweets.
    Strategy: fetch tweet objects via Ads API to get card_uri, then resolve
    card_uri → website_url via the cards endpoints."""
    urls: dict[str, str] = {}
    if not tweet_ids:
        return urls

    # Step 1: fetch card URLs for the account
    card_urls = _fetch_card_urls(session, account_id)
    if card_urls:
        print(f"  {len(card_urls)} card URLs loaded", file=sys.stderr)

    # Step 2: fetch tweet objects to get card_uri and text URLs
    for i in range(0, len(tweet_ids), 200):
        batch = tweet_ids[i : i + 200]
        try:
            data = api_get(session, f"/accounts/{account_id}/tweets", {
                "tweet_ids": ",".join(batch),
                "tweet_type": "PUBLISHED",
            })
            for tw in data.get("data", []):
                tid = str(tw.get("id") or tw.get("id_str") or tw.get("tweet_id", ""))
                if not tid:
                    continue

                # Try card_uri first (most ads use cards for the destination URL)
                card_uri = tw.get("card_uri") or ""
                if card_uri.startswith("card://"):
                    card_id = card_uri.replace("card://", "")
                    card_url = card_urls.get(card_id, "")
                    if card_url:
                        urls[tid] = card_url
                        continue

                # Fallback: URL in tweet text or entities
                for u in (tw.get("entities") or {}).get("urls", []):
                    expanded = u.get("expanded_url") or ""
                    if expanded and "t.co/" not in expanded:
                        urls[tid] = expanded
                        break
                else:
                    text = tw.get("full_text") or tw.get("text") or ""
                    url = _extract_url(text)
                    if url:
                        urls[tid] = url
        except Exception as e:
            print(f"  ads/tweets error: {e}", file=sys.stderr)

    found = sum(1 for v in urls.values() if v)
    print(f"  resolved {found}/{len(tweet_ids)} tweet URLs", file=sys.stderr)
    return urls


# ---- hierarchy builder ------------------------------------------------------

def build_hierarchy(session: OAuth1Session, account_id: str) -> tuple[dict, dict, dict]:
    """
    Fetch the full Campaign → Line Item → Promoted Tweet tree.
    Currency is resolved per campaign via its funding instrument.
    Returns (campaigns, line_items, promoted_tweets) dicts keyed by id.
    """
    fi_currencies = {
        fi["id"]: fi.get("currency", "USD")
        for fi in paginate(session, f"/accounts/{account_id}/funding_instruments")
    }

    campaigns = {}
    for c in paginate(session, f"/accounts/{account_id}/campaigns"):
        fi_id = c.get("funding_instrument_id")
        campaigns[c["id"]] = {
            "name": c.get("name", c["id"]),
            "currency": fi_currencies.get(fi_id, "USD"),
        }

    line_items = {}
    for li in paginate(session, f"/accounts/{account_id}/line_items"):
        camp_id = li.get("campaign_id")
        camp = campaigns.get(camp_id, {})
        line_items[li["id"]] = {
            "name": li.get("name", li["id"]),
            "campaign_id": camp_id,
            "currency": camp.get("currency", "USD"),
        }

    promoted_raw = paginate(session, f"/accounts/{account_id}/promoted_tweets")
    tweet_ids = [pt.get("tweet_id") for pt in promoted_raw if pt.get("tweet_id")]

    tweet_urls = _resolve_tweet_urls(session, account_id, tweet_ids)

    promoted = {}
    for pt in promoted_raw:
        li_id = pt.get("line_item_id")
        li = line_items.get(li_id, {})
        camp_id = li.get("campaign_id")
        camp = campaigns.get(camp_id, {})
        tweet_id = pt.get("tweet_id", "?")
        promoted[pt["id"]] = {
            "tweet_id": tweet_id,
            "line_item_id": li_id,
            "adset_name": li.get("name", "?"),
            "campaign_id": camp_id,
            "campaign_name": camp.get("name", "?"),
            "currency": camp.get("currency", li.get("currency", "USD")),
            "ad_url": tweet_urls.get(tweet_id, ""),
        }

    return campaigns, line_items, promoted


def _extract_url(text: str) -> str:
    """Pull the first https URL from tweet text."""
    import re
    m = re.search(r"https?://\S+", text)
    return m.group(0) if m else ""


def _parse_utm(url: str) -> dict:
    """Split a URL into landing page (no query) and UTM params."""
    if not url:
        return {"landing_page": "", "utm_source": "", "utm_medium": "",
                "utm_campaign": "", "utm_content": ""}
    p = urlparse(url)
    qs = parse_qs(p.query)
    base = f"{p.scheme}://{p.netloc}{p.path}"
    return {
        "landing_page": base,
        "utm_source": qs.get("utm_source", [""])[0],
        "utm_medium": qs.get("utm_medium", [""])[0],
        "utm_campaign": qs.get("utm_campaign", [""])[0],
        "utm_content": qs.get("utm_content", [""])[0],
    }


# ---- DB ---------------------------------------------------------------------

def init_db() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS ad_spend (
            date           TEXT NOT NULL,
            account_id     TEXT NOT NULL,
            account_name   TEXT,
            campaign_id    TEXT,
            campaign_name  TEXT,
            adset_id       TEXT,
            adset_name     TEXT,
            ad_id          TEXT NOT NULL,
            ad_name        TEXT,
            ad_url         TEXT DEFAULT '',
            landing_page   TEXT DEFAULT '',
            utm_source     TEXT DEFAULT '',
            utm_medium     TEXT DEFAULT '',
            utm_campaign   TEXT DEFAULT '',
            utm_content    TEXT DEFAULT '',
            page_views     INTEGER NOT NULL DEFAULT 0,
            form_starts    INTEGER NOT NULL DEFAULT 0,
            leads          INTEGER NOT NULL DEFAULT 0,
            purchases      INTEGER NOT NULL DEFAULT 0,
            revenue_inr    REAL NOT NULL DEFAULT 0,
            spend_micro    INTEGER NOT NULL DEFAULT 0,
            currency       TEXT NOT NULL DEFAULT 'INR',
            fetched_at     TEXT,
            PRIMARY KEY (date, account_id, ad_id)
        );
        CREATE INDEX IF NOT EXISTS idx_as_date ON ad_spend(date);
        CREATE INDEX IF NOT EXISTS idx_as_acct ON ad_spend(account_id);
    """)
    # migrate older DBs that lack newer columns
    migrations = [
        ("landing_page", "TEXT DEFAULT ''"), ("utm_source", "TEXT DEFAULT ''"),
        ("utm_medium", "TEXT DEFAULT ''"), ("utm_campaign", "TEXT DEFAULT ''"),
        ("utm_content", "TEXT DEFAULT ''"),
        ("page_views", "INTEGER NOT NULL DEFAULT 0"),
        ("form_starts", "INTEGER NOT NULL DEFAULT 0"),
        ("leads", "INTEGER NOT NULL DEFAULT 0"),
        ("purchases", "INTEGER NOT NULL DEFAULT 0"),
        ("revenue_inr", "REAL NOT NULL DEFAULT 0"),
    ]
    for col, typedef in migrations:
        try:
            db.execute(f"ALTER TABLE ad_spend ADD COLUMN {col} {typedef}")
        except sqlite3.OperationalError:
            pass
    return db


# ---- commands ---------------------------------------------------------------

def cmd_discover(session: OAuth1Session):
    accounts = paginate(session, "/accounts")
    if not accounts:
        print("No ad accounts found.", file=sys.stderr)
        return
    print(f"\n{'ID':<22} {'Name':<30} {'Currency':<8} {'Timezone':<20} {'Status'}")
    print("-" * 96)
    for a in accounts:
        cur = a.get("currency", "?")
        tz = a.get("timezone", "?")
        print(
            f"{a['id']:<22} {a.get('name', '?'):<30} "
            f"{cur:<8} {tz:<20} {a.get('approval_status', '?')}"
        )
        if cur == "?":
            keys = [k for k in a if "curr" in k.lower() or "money" in k.lower()
                    or "bill" in k.lower()]
            if keys:
                print(f"  currency-related fields: {', '.join(f'{k}={a[k]}' for k in keys)}")
            else:
                print(f"  no 'currency' field found — set it in config.json")
    print(f"\n{len(accounts)} account(s).", file=sys.stderr)


def cmd_fetch(session: OAuth1Session, config: dict, args):
    accounts = resolve_accounts(session, config)
    if not accounts:
        sys.exit("No accounts. Run 'discover' or add to config.json.")

    db = init_db()
    now_iso = datetime.now(timezone.utc).isoformat()
    total_rows = 0

    for acct in accounts:
        aid, aname = acct["id"], acct["name"]
        tz = ZoneInfo(acct.get("timezone", "UTC"))
        today = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)

        if args.start:
            start = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=tz)
        else:
            start = today - timedelta(days=args.days)
        if args.end:
            end = datetime.strptime(args.end, "%Y-%m-%d").replace(tzinfo=tz)
        else:
            end = today

        num_days = (end - start).days
        if num_days <= 0:
            sys.exit("end must be after start")

        print(f"\n{aname} ({aid}) tz={acct.get('timezone', 'UTC')}", file=sys.stderr)

        campaigns, line_items, promoted = build_hierarchy(session, aid)
        print(
            f"  {len(campaigns)} campaigns, {len(line_items)} ad sets, "
            f"{len(promoted)} ads",
            file=sys.stderr,
        )

        rows: list[tuple] = []

        # --- try ad-level (PROMOTED_TWEET) first ---
        if promoted:
            stats = fetch_billing(session, aid, "PROMOTED_TWEET", list(promoted), start, end)
            for pt_id, micros in stats.items():
                meta = promoted.get(pt_id, {})
                orig_cur = meta.get("currency", "USD")
                utm = _parse_utm(meta.get("ad_url", ""))
                for i, v in enumerate(micros[:num_days]):
                    if v > 0:
                        spend = v * USD_TO_INR if orig_cur == "USD" else v
                        rows.append((
                            (start + timedelta(days=i)).strftime("%Y-%m-%d"),
                            aid, aname,
                            meta.get("campaign_id", ""),
                            meta.get("campaign_name", "?"),
                            meta.get("line_item_id", ""),
                            meta.get("adset_name", "?"),
                            pt_id,
                            f"tweet:{meta.get('tweet_id', '?')}",
                            meta.get("ad_url", ""),
                            utm["landing_page"], utm["utm_source"],
                            utm["utm_medium"], utm["utm_campaign"], utm["utm_content"],
                            spend, "INR", now_iso,
                        ))

        # --- fallback: ad-set level (LINE_ITEM) if no promoted tweets ---
        elif line_items:
            stats = fetch_billing(session, aid, "LINE_ITEM", list(line_items), start, end)
            for li_id, micros in stats.items():
                meta = line_items.get(li_id, {})
                camp_id = meta.get("campaign_id", "")
                camp = campaigns.get(camp_id, {})
                orig_cur = meta.get("currency", camp.get("currency", "USD"))
                for i, v in enumerate(micros[:num_days]):
                    if v > 0:
                        spend = v * USD_TO_INR if orig_cur == "USD" else v
                        rows.append((
                            (start + timedelta(days=i)).strftime("%Y-%m-%d"),
                            aid, aname,
                            camp_id,
                            camp.get("name", "?"),
                            li_id, meta.get("name", "?"),
                            li_id, meta.get("name", "?"),
                            "", "", "", "", "", "",
                            spend, "INR", now_iso,
                        ))

        if rows:
            db.executemany(
                "INSERT OR REPLACE INTO ad_spend "
                "(date, account_id, account_name, campaign_id, campaign_name, "
                "adset_id, adset_name, ad_id, ad_name, ad_url, "
                "landing_page, utm_source, utm_medium, utm_campaign, utm_content, "
                "spend_micro, currency, fetched_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
            db.commit()
            total_rows += len(rows)
            spend = sum(r[15] for r in rows) / 1_000_000
            print(f"  {len(rows)} rows, spend {spend:,.2f}", file=sys.stderr)
        else:
            print("  no spend data", file=sys.stderr)

    db.close()
    print(f"\nStored {total_rows} rows total in {DB_PATH.name}", file=sys.stderr)


# ---- query helper -----------------------------------------------------------

def _query_rows(days: int) -> list[dict]:
    if not DB_PATH.exists():
        sys.exit("No data — run 'fetch' first.")
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = db.execute(
        "SELECT date, account_name, campaign_name, adset_name, ad_name, "
        "ad_url, landing_page, utm_source, utm_medium, utm_campaign, utm_content, "
        "spend_micro, currency, page_views, form_starts, leads, purchases, revenue_inr "
        "FROM ad_spend "
        "WHERE date >= ? ORDER BY date DESC, account_name, campaign_name, adset_name",
        (since,),
    ).fetchall()
    db.close()
    return [
        {
            "date": r["date"],
            "ad_account": r["account_name"],
            "campaign_name": r["campaign_name"],
            "adset_name": r["adset_name"],
            "ad_name": r["ad_name"],
            "ad_url": r["ad_url"] or "",
            "landing_page": r["landing_page"] or "",
            "utm_source": r["utm_source"] or "",
            "utm_medium": r["utm_medium"] or "",
            "utm_campaign": r["utm_campaign"] or "",
            "utm_content": r["utm_content"] or "",
            "spend": round(r["spend_micro"] / 1_000_000, 2),
            "currency": r["currency"],
            "page_views": r["page_views"] or 0,
            "form_starts": r["form_starts"] or 0,
            "leads": r["leads"] or 0,
            "purchases": r["purchases"] or 0,
            "revenue_inr": r["revenue_inr"] or 0,
        }
        for r in rows
    ]


# ---- report -----------------------------------------------------------------

def cmd_report(args):
    rows = _query_rows(args.days)
    if not rows:
        sys.exit(f"No data in the last {args.days} days.")

    # account totals
    acct_totals: dict[str, float] = {}
    for r in rows:
        acct_totals.setdefault(r["ad_account"], 0.0)
        acct_totals[r["ad_account"]] += r["spend"]

    grand = sum(acct_totals.values())
    print(f"\n--- Account totals (last {args.days} days) ---")
    for name, s in sorted(acct_totals.items()):
        print(f"  {name:<30} {s:>12,.2f}")
    print(f"  {'TOTAL':<30} {grand:>12,.2f}")

    # campaign totals
    camp_totals: dict[tuple[str, str], float] = {}
    for r in rows:
        key = (r["ad_account"], r["campaign_name"])
        camp_totals.setdefault(key, 0.0)
        camp_totals[key] += r["spend"]

    print(f"\n--- Campaign totals ---")
    for (acct, camp), s in sorted(camp_totals.items(), key=lambda x: -x[1]):
        print(f"  {acct[:20]:<20} {camp[:35]:<35} {s:>12,.2f}")

    # detail rows (capped for terminal)
    if len(rows) <= 200:
        print(f"\n--- Detail ({len(rows)} rows) ---")
        fmt = "{:<12} {:<18} {:<25} {:<20} {:<22} {} {:>10} {}"
        print(fmt.format(*HEADER))
        print("-" * 180)
        for r in rows:
            print(fmt.format(
                r["date"],
                r["ad_account"][:17],
                r["campaign_name"][:24],
                r["adset_name"][:19],
                r["ad_name"][:21],
                f"{r['ad_url']:<80}",
                f"{r['spend']:,.2f}",
                r["currency"],
            ))
    else:
        print(f"\n{len(rows)} detail rows — use 'export --csv' for full data.",
              file=sys.stderr)

    dates = sorted({r["date"] for r in rows})
    if dates:
        cur = rows[0]["currency"]
        avg = grand / len(dates)
        print(f"\nDaily avg: {cur} {avg:,.2f}  ({len(dates)} days)")


# ---- export -----------------------------------------------------------------

def cmd_export(args):
    rows = _query_rows(args.days)
    if not rows:
        sys.exit(f"No data in the last {args.days} days.")

    if args.sheet:
        _push_sheet(rows, args.sheet, args.tab)
        return

    buf = open(args.csv, "w", newline="", encoding="utf-8") if args.csv else io.StringIO()
    w = csv.writer(buf)
    w.writerow(HEADER)
    for r in rows:
        w.writerow([r[c] for c in COLUMNS])
    if args.csv:
        buf.close()
        print(f"Wrote {len(rows)} rows → {args.csv}", file=sys.stderr)
    else:
        print(buf.getvalue())


def _get_sheets_client():
    import gspread
    sa_path = os.getenv("GOOGLE_SA_KEY") or load_config().get("google_sa_key", "")
    creds_path = HERE / "authorized_user.json"

    if sa_path and Path(sa_path).exists():
        return gspread.service_account(filename=sa_path)
    if creds_path.exists():
        return gspread.oauth(credentials_filename=str(HERE / "oauth_creds.json"),
                             authorized_user_filename=str(creds_path))
    print("First-time Google Sheets setup — a browser will open for you to sign in.", file=sys.stderr)
    oauth_creds = HERE / "oauth_creds.json"
    if not oauth_creds.exists():
        sys.exit(
            f"Place your OAuth client credentials at {oauth_creds}\n"
            "Get them from: Google Cloud Console → APIs & Services → Credentials → "
            "Create Credentials → OAuth client ID → Desktop app → Download JSON"
        )
    return gspread.oauth(credentials_filename=str(oauth_creds),
                         authorized_user_filename=str(creds_path))


def _push_sheet(rows: list[dict], spreadsheet_id: str, tab: str, append: bool = False):
    import gspread
    gc = _get_sheets_client()
    sh = gc.open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet(tab)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=tab, rows=max(len(rows) + 1, 100), cols=len(COLUMNS))
        append = False  # new sheet, do full write

    if append:
        existing = ws.col_values(1)  # dates in column A
        existing_dates = set(existing[1:])  # skip header
        new_rows = [r for r in rows if r["date"] not in existing_dates]
        if not new_rows:
            print(f"  no new dates to append → '{tab}'", file=sys.stderr)
            return
        data = [[r[c] for c in COLUMNS] for r in new_rows]
        next_row = len(existing) + 1
        ws.update(range_name=f"A{next_row}", values=data)
        print(f"Appended {len(new_rows)} rows → '{tab}'", file=sys.stderr)
    else:
        data = [HEADER] + [[r[c] for c in COLUMNS] for r in rows]
        ws.clear()
        ws.update(range_name="A1", values=data)
        ws.format(f"A1:{chr(64 + len(COLUMNS))}1", {"textFormat": {"bold": True}})
        print(f"Pushed {len(rows)} rows → '{tab}'", file=sys.stderr)


# ---- enrich (events DB) -----------------------------------------------------

def _fetch_events_from_api(start_date: str, end_date: str) -> list[dict]:
    """Call the server's /api/events-summary endpoint to get event data remotely."""
    import requests
    cfg = load_config()
    server_url = cfg.get("server_url", "").rstrip("/")
    stats_key = cfg.get("stats_key", "")
    if not server_url or not stats_key:
        sys.exit("Set 'server_url' and 'stats_key' in config.json for remote event enrichment")
    resp = requests.get(
        f"{server_url}/api/events-summary",
        params={"key": stats_key, "start": start_date, "end": end_date},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"events-summary API returned {resp.status_code}: {resp.text[:200]}")
    return resp.json().get("rows", [])


def _normalize_path(url: str) -> str:
    """Extract URL path, strip www. and trailing slash for matching."""
    if not url:
        return ""
    p = urlparse(url)
    return p.path.rstrip("/")


def cmd_enrich(args):
    """Pull page_views / form_starts / leads / purchases / revenue from the
    events DB and update the matching ad_spend rows in SQLite."""
    db = init_db()

    since = (datetime.now(timezone.utc) - timedelta(days=args.days)).strftime("%Y-%m-%d")
    spend_rows = db.execute(
        "SELECT DISTINCT date, landing_page, utm_source, utm_medium, utm_campaign "
        "FROM ad_spend WHERE date >= ?", (since,),
    ).fetchall()
    if not spend_rows:
        sys.exit(f"No ad_spend rows in the last {args.days} days — run 'fetch' first.")

    dates = sorted({r[0] for r in spend_rows})
    start_date = dates[0]
    end_date = (datetime.strptime(dates[-1], "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"Enriching {len(spend_rows)} ad rows ({start_date} to {dates[-1]})…", file=sys.stderr)

    event_rows = _fetch_events_from_api(start_date, end_date)

    # Build lookup: (date, path, utm_source, utm_medium, utm_campaign) → metrics
    lookup: dict[tuple, dict] = {}
    for r in event_rows:
        path = _normalize_path(r["landing_page"] or "")
        key = (
            str(r["event_date"]),
            path,
            (r["utm_source"] or "").lower(),
            (r["utm_medium"] or "").lower(),
            (r["utm_campaign"] or "").lower(),
        )
        lookup[key] = {
            "page_views": int(r["page_views"]),
            "form_starts": int(r["form_starts"]),
            "leads": int(r["leads"]),
            "purchases": int(r["purchases"]),
            "revenue_inr": float(r["revenue_inr"]),
        }

    print(f"  {len(event_rows)} event groups from DB, {len(lookup)} unique keys", file=sys.stderr)

    matched = 0
    for srow in spend_rows:
        date, lp, src, med, camp = srow
        path = _normalize_path(lp or "")
        key = (date, path, (src or "").lower(), (med or "").lower(), (camp or "").lower())
        metrics = lookup.get(key)
        if not metrics:
            continue
        matched += 1
        db.execute(
            "UPDATE ad_spend SET page_views=?, form_starts=?, leads=?, purchases=?, revenue_inr=? "
            "WHERE date=? AND landing_page=? AND utm_source=? AND utm_medium=? AND utm_campaign=?",
            (
                metrics["page_views"], metrics["form_starts"],
                metrics["leads"], metrics["purchases"], metrics["revenue_inr"],
                date, lp, src, med, camp,
            ),
        )

    db.commit()
    db.close()
    print(f"  matched {matched}/{len(spend_rows)} ad rows with events", file=sys.stderr)


# ---- daily (all-in-one) ----------------------------------------------------

def cmd_daily(args):
    """Fetch yesterday's spend, enrich with events, push to Google Sheet."""
    config = load_config()
    session = get_session(config)

    # 1. Fetch (yesterday + today partial)
    fetch_args = argparse.Namespace(days=args.days, start=None, end=None)
    print("=== FETCH ===", file=sys.stderr)
    cmd_fetch(session, config, fetch_args)

    # 2. Enrich from events DB
    print("\n=== ENRICH ===", file=sys.stderr)
    enrich_args = argparse.Namespace(days=args.days)
    try:
        cmd_enrich(enrich_args)
    except SystemExit as e:
        print(f"  enrich skipped: {e}", file=sys.stderr)
    except Exception as e:
        print(f"  enrich failed (DB unreachable?): {e}", file=sys.stderr)
        print("  continuing without event data…", file=sys.stderr)

    # 3. Export to Google Sheet (append only new dates)
    print("\n=== EXPORT → SHEET ===", file=sys.stderr)
    sa_key = config.get("google_sa_key")
    if sa_key:
        os.environ.setdefault("GOOGLE_SA_KEY", sa_key)
    sheet_id = args.sheet or ROAS_SHEET
    rows = _query_rows(args.export_days)
    if rows:
        _push_sheet(rows, sheet_id, args.tab, append=True)
    else:
        print("  no data to export", file=sys.stderr)
    print("\nDaily run complete.", file=sys.stderr)


# ---- CLI --------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description="Twitter/X Ads daily spend tracker (ad-level granularity)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Output: Date | Ad Account | Campaign Name | Ad Set Name | Ad Name | Spend | Currency\n\n"
            "Examples:\n"
            "  %(prog)s discover\n"
            "  %(prog)s fetch --days 7\n"
            "  %(prog)s report --days 30\n"
            "  %(prog)s export --csv spend.csv\n"
            "  %(prog)s export --sheet\n"
        ),
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("discover", help="List accessible ad accounts")

    fp = sub.add_parser("fetch", help="Fetch ad-level daily spend from API")
    fp.add_argument("--days", type=int, default=1, help="lookback days (default: 1)")
    fp.add_argument("--start", help="start date YYYY-MM-DD (overrides --days)")
    fp.add_argument("--end", help="end date YYYY-MM-DD (default: today)")

    rp = sub.add_parser("report", help="Spend summary from stored data")
    rp.add_argument("--days", type=int, default=30, help="lookback days (default: 30)")

    ep = sub.add_parser("export", help="Export to CSV or Google Sheet")
    ep.add_argument("--days", type=int, default=30, help="lookback days (default: 30)")
    ep.add_argument("--csv", metavar="FILE", help="CSV file path (default: stdout)")
    ep.add_argument(
        "--sheet", metavar="ID", nargs="?", const=ROAS_SHEET,
        help="push to Google Sheet (default: ROAS Tracker sheet)",
    )
    ep.add_argument("--tab", default="Twitter Spend", help="sheet tab name")

    np = sub.add_parser("enrich", help="Enrich spend rows with events DB (page views, leads, revenue)")
    np.add_argument("--days", type=int, default=30, help="lookback days (default: 30)")

    dp = sub.add_parser("daily", help="All-in-one: fetch → enrich → push to sheet")
    dp.add_argument("--days", type=int, default=2, help="fetch lookback (default: 2, covers yesterday)")
    dp.add_argument("--export-days", type=int, default=30, help="how many days to push to sheet (default: 30)")
    dp.add_argument("--sheet", metavar="ID", default=None, help="Google Sheet ID (default: ROAS Tracker)")
    dp.add_argument("--tab", default="Twitter Spend", help="sheet tab name")

    args = p.parse_args()

    if args.command in ("report", "export"):
        (cmd_report if args.command == "report" else cmd_export)(args)
        return
    if args.command == "enrich":
        cmd_enrich(args)
        return
    if args.command == "daily":
        cmd_daily(args)
        return

    config = load_config()
    session = get_session(config)

    if args.command == "discover":
        cmd_discover(session)
    elif args.command == "fetch":
        cmd_fetch(session, config, args)


if __name__ == "__main__":
    main()
