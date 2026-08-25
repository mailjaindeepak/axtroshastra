#!/usr/bin/env python3
"""Merge built-page rows + researched rows -> data.json, ranked by search volume."""
import json, sys

def main():
    built = json.load(open("_built_pages.json"))
    researched = json.load(open("_researched.json"))   # written after agent results are verified
    by_name = {r["name"]: r for r in researched}
    rows = []
    for b in built:
        r = by_name.pop(b["name"], {})
        rows.append({**r, **b})          # built-page fields win (they're verified)
    rows += list(by_name.values())
    rows.sort(key=lambda r: -r.get("search_volume_monthly", 0))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
        r.setdefault("page_status", "not_built")
        r.setdefault("tob", None)
        r.setdefault("rodden", None)
    order = ["rank","name","category","dob","pob","tob","tob_status","rodden",
             "search_volume_monthly","search_tier","search_evidence","page_status","notes"]
    rows = [{k: r.get(k) for k in order} for r in rows]
    json.dump(rows, open("data.json","w"), indent=1, ensure_ascii=False)
    print(f"data.json written: {len(rows)} rows")

if __name__ == "__main__":
    main()
