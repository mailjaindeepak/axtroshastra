"""Write docs/numerology-content-review-pack.md: every drafted block, for the owner to read before approving."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bank = json.load(open(os.path.join(ROOT, "mulank_bank.json"), encoding="utf-8"))
PL = {1: "Sun", 2: "Moon", 3: "Jupiter", 4: "Rahu", 5: "Mercury", 6: "Venus", 7: "Ketu", 8: "Saturn", 9: "Mars"}

def dump(v, ind=0):
    pad = "  " * ind
    if isinstance(v, dict):
        return "".join(f"{pad}- **{k}**:" + (" " + dump(x, 0).strip() + "\n" if not isinstance(x, (dict, list)) else "\n" + dump(x, ind + 1)) for k, x in v.items())
    if isinstance(v, list):
        return "".join(f"{pad}- " + (str(x) + "\n" if not isinstance(x, (dict, list)) else "\n" + dump(x, ind + 1)) for x in v)
    return f"{pad}{v}\n"

out = ["# Mulank content review pack (DRAFT, nothing approved)\n",
       "Everything below is drafted text that a customer would read, assembled per number. Read it, change what you want changed, then approve with "
       "`tools/approve_mulank_content.py`. Numerology is presented as a belief system for reflection, not science.\n"]
for name, title in (("M", "Mulank (M1-9)"), ("B", "Bhagyank (B1-9)"), ("PM", "Personality by Mulank (PM1-9)"), ("PG", "Personality overlay by Bhagyank (PG1-9)"),
                    ("CB", "Bonds by Mulank (CB1-9)"), ("Y", "Personal years (Y1-9)")):
    out.append(f"\n## {title}\n")
    for n, blk in sorted(bank[name].items(), key=lambda kv: int(kv[0])):
        out.append(f"\n### {name}{n} ({PL[int(n)]})\n\n" + dump(blk))
out.append("\n## Lucky references by planet (LK)\n\n" + dump(bank["LP"]))
out.append("\n## Wording rows (already approved wording)\n\n" + dump(bank["rows"]))
open(os.path.join(ROOT, "docs", "numerology-content-review-pack.md"), "w", encoding="utf-8", newline="\n").write("".join(out))
print("ok")
