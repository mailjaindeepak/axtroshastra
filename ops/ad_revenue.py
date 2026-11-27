"""
ad_revenue.py — Pull daily ad-attributed leads, purchases, and revenue from the
events DB, grouped by UTM campaign (source + medium + campaign + product).

Usage (run from codebase/axtroshastra/ with DB env vars set):

    python ops/ad_revenue.py                          # last 30 days, CSV to stdout
    python ops/ad_revenue.py --days 90                # last 90 days
    python ops/ad_revenue.py --source twitter          # only Twitter-attributed rows
    python ops/ad_revenue.py --csv revenue.csv        # write to file
    python ops/ad_revenue.py --sheet SPREADSHEET_ID   # push to Google Sheet

Google Sheets mode requires:
  - pip install gspread
  - A service-account JSON key file at GOOGLE_SA_KEY env var (or ./sa_key.json)
  - The Sheet shared with the service account's email address

Env: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME (same as the app).

ROAS Tracker Sheet: https://docs.google.com/spreadsheets/d/1cu-SUSgTnze9jwIpWyqaKl3S25yt2NbEu4j7bYuzJvY/edit
"""
import argparse
import csv
import io
import os
import sys
from datetime import datetime, timedelta

import pymysql


def get_conn():
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ.get("DB_NAME", "axtroshastra_v2"),
        charset="utf8mb4",
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )


REVENUE_SQL = """\
SELECT
    DATE(e.created_at)                                        AS report_date,
    vs.utm_source,
    vs.utm_medium,
    vs.utm_campaign,
    COALESCE(r.product, e.product, 'unknown')                 AS product,
    SUM(e.event_name = 'generate_lead')                       AS leads,
    SUM(e.event_name = 'purchase' AND e.is_free_unlock = 0)   AS purchases,
    COALESCE(SUM(CASE
        WHEN e.event_name = 'purchase' AND e.is_free_unlock = 0
        THEN COALESCE(e.value_paise, 0) ELSE 0
    END), 0) / 100.0                                          AS revenue_inr
FROM events e
JOIN visit_sessions vs ON e.visit_id = vs.visit_id
LEFT JOIN reports r    ON e.report_id = r.id
WHERE e.event_name IN ('generate_lead', 'purchase')
  AND vs.utm_source IS NOT NULL
  AND e.created_at >= %s
  {source_filter}
GROUP BY report_date, vs.utm_source, vs.utm_medium, vs.utm_campaign, product
ORDER BY report_date DESC, vs.utm_campaign, product
"""

COLUMNS = [
    "report_date", "utm_source", "utm_medium", "utm_campaign",
    "product", "leads", "purchases", "revenue_inr",
]


def pull_revenue(days: int, source: str | None = None) -> list[dict]:
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    params = [since]
    if source:
        source_filter = "AND LOWER(vs.utm_source) LIKE %s"
        params.append(f"%{source.lower()}%")
    else:
        source_filter = ""
    sql = REVENUE_SQL.format(source_filter=source_filter)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    finally:
        conn.close()
    for r in rows:
        r["report_date"] = str(r["report_date"])
        r["leads"] = int(r["leads"])
        r["purchases"] = int(r["purchases"])
        r["revenue_inr"] = float(r["revenue_inr"])
    return rows


def print_summary(rows: list[dict]):
    total_leads = sum(r["leads"] for r in rows)
    total_purchases = sum(r["purchases"] for r in rows)
    total_revenue = sum(r["revenue_inr"] for r in rows)
    campaigns = len({(r["utm_source"], r["utm_medium"], r["utm_campaign"]) for r in rows})
    dates = sorted({r["report_date"] for r in rows})
    print(f"\n--- Summary ---", file=sys.stderr)
    if dates:
        print(f"Date range:  {dates[0]} to {dates[-1]}", file=sys.stderr)
    print(f"Campaigns:   {campaigns}", file=sys.stderr)
    print(f"Total leads: {total_leads}", file=sys.stderr)
    print(f"Purchases:   {total_purchases}", file=sys.stderr)
    print(f"Revenue:     ₹{total_revenue:,.0f}", file=sys.stderr)


def to_csv(rows: list[dict], dest=None):
    buf = open(dest, "w", newline="", encoding="utf-8") if dest else io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS)
    w.writeheader()
    w.writerows(rows)
    if dest:
        buf.close()
        print(f"Wrote {len(rows)} rows to {dest}", file=sys.stderr)
    else:
        print(buf.getvalue())


def push_to_sheet(rows: list[dict], spreadsheet_id: str, tab_name: str = "Ad Revenue"):
    import gspread
    sa_path = os.getenv("GOOGLE_SA_KEY", "sa_key.json")
    gc = gspread.service_account(filename=sa_path)
    sh = gc.open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=tab_name, rows=1000, cols=len(COLUMNS))
    header = ["Date", "UTM Source", "UTM Medium", "UTM Campaign",
              "Product", "Leads", "Purchases", "Revenue (INR)"]
    data = [header] + [[r[c] for c in COLUMNS] for r in rows]
    ws.clear()
    ws.update(range_name="A1", values=data)
    ws.format("A1:H1", {"textFormat": {"bold": True}})
    print(f"Pushed {len(rows)} rows to sheet tab '{tab_name}'", file=sys.stderr)


def main():
    p = argparse.ArgumentParser(description="Pull daily ad revenue by UTM campaign")
    p.add_argument("--days", type=int, default=30, help="lookback window (default 30)")
    p.add_argument("--source", help="filter by utm_source substring (e.g. 'twitter')")
    p.add_argument("--csv", metavar="FILE", help="write CSV to file (default: stdout)")
    p.add_argument("--sheet", metavar="SPREADSHEET_ID", nargs="?",
                   const="1cu-SUSgTnze9jwIpWyqaKl3S25yt2NbEu4j7bYuzJvY",
                   help="push to Google Sheet (default: ROAS Tracker sheet)")
    p.add_argument("--tab", default="Ad Revenue", help="Sheet tab name (default: 'Ad Revenue')")
    args = p.parse_args()

    rows = pull_revenue(args.days, source=args.source)
    label = f" (source~'{args.source}')" if args.source else ""
    print(f"Pulled {len(rows)} rows (last {args.days} days{label})", file=sys.stderr)
    print_summary(rows)

    if args.sheet:
        push_to_sheet(rows, args.sheet, tab_name=args.tab)
    else:
        to_csv(rows, dest=args.csv)


if __name__ == "__main__":
    main()
