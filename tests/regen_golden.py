"""Regenerate golden snapshots after an INTENTIONAL engine change.
Run from the repo root:  python tests/regen_golden.py
Review the git diff carefully before committing — this is the regression baseline.
"""
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DB_PATH", "/tmp/regen.db")

from engine import compute_report, compute_chart  # noqa: E402
import divisional  # noqa: E402

GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden")
ASOF = datetime(2025, 1, 1)


def main():
    os.makedirs(GOLDEN, exist_ok=True)
    rep = compute_report(name="Golden", dob="1990-03-21", tob="08:15",
                         tz_offset_hours=5.5, lat=28.61, lon_geo=77.21,
                         female=True, time_quality="T0", as_of=ASOF)
    snap = {"meta": rep["meta"], "chart": rep["chart"], "manglik": rep["manglik"],
            "significators": rep["significators"], "current_period": rep["current_period"],
            "windows": rep["windows"], "teaser_moon": rep["teaser"]["moon_sign"]}
    json.dump(snap, open(os.path.join(GOLDEN, "marriage_T0.json"), "w"),
              indent=1, sort_keys=True, default=str)

    local = datetime.fromisoformat("1990-03-21T08:15:00")
    chart = compute_chart(local - timedelta(hours=5.5), 28.61, 77.21)
    json.dump(divisional.analyze(chart), open(os.path.join(GOLDEN, "divisional.json"), "w"),
              indent=1, sort_keys=True, default=str)
    print("Golden snapshots regenerated in", GOLDEN)


if __name__ == "__main__":
    main()
