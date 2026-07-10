"""
Axtroshastra engine back-test.
Usage: python3 backtest.py charts.csv
CSV columns: name,dob,tob,time_quality,place_lat,place_lon,gender,marriage_date
  dob/marriage_date: YYYY-MM-DD | tob: HH:MM (or blank for T2/T3)
For each chart: compute windows AS OF (marriage_date - 5 years) and check
whether the actual marriage lands inside a predicted window.
Reports hit-rate, grade breakdown, and lift over the chance baseline
(baseline = fraction of the horizon covered by windows).
"""
import csv, sys, warnings
from datetime import datetime, timedelta
warnings.filterwarnings("ignore")
from engine import compute_report

def run(path):
    rows = list(csv.DictReader(open(path)))
    hits, results, cover_total = 0, [], 0.0
    for r in rows:
        mdate = datetime.fromisoformat(r["marriage_date"])
        as_of = mdate - timedelta(days=5 * 365)
        rep = compute_report(r["name"], r["dob"], r.get("tob") or "12:00", 5.5,
                             float(r.get("place_lat") or 28.61),
                             float(r.get("place_lon") or 77.21),
                             female=(r.get("gender", "").lower() == "female"),
                             time_quality=r.get("time_quality") or "T0",
                             as_of=as_of)
        hit_grade, cover_days = None, 0
        for w in rep["windows"]:
            ws = datetime.strptime(w["start"], "%Y-%m")
            we = datetime.strptime(w["end"], "%Y-%m")
            cover_days += (we - ws).days
            if ws <= mdate <= we and hit_grade is None:
                hit_grade = w["grade"]
        cover = cover_days / (10 * 365.25)
        cover_total += cover
        if hit_grade: hits += 1
        results.append((r["name"], mdate.strftime("%Y-%m"), hit_grade or "MISS",
                        f"{cover:.0%}",
                        " | ".join(f"{w['grade'][:3]} {w['start']}→{w['end']}" for w in rep["windows"])))
    n = len(rows)
    base = cover_total / n if n else 0
    hr = hits / n if n else 0
    print(f"\n{'name':<16}{'married':<10}{'result':<10}{'coverage':<10}windows")
    for row in results: print(f"{row[0]:<16}{row[1]:<10}{row[2]:<10}{row[3]:<10}{row[4]}")
    print(f"\nHIT RATE: {hits}/{n} = {hr:.0%}   chance baseline (avg window coverage): {base:.0%}"
          f"   LIFT: {hr/base:.1f}x" if base else "")
    if base and hr / base < 1.3:
        print("⚠️  Lift under 1.3x — engine is barely beating chance; weights need tuning before launch.")
    elif base:
        print("✅ Engine is beating chance meaningfully." if hr/base >= 1.5 else "OK but tunable.")

if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "charts.csv")
