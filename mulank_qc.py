"""Internal editorial quality control for Mulank content. No external expert needed; the owner's approval
(mulank_registry.json, status owner_approved) is only meaningful if content passes these checks first.

lint_bank()          problems in the drafted text (flagged vocabulary, placeholders, empty fields, and the same
                     long paragraph reused under different pairs, i.e. another pair's reading used as a substitute)
lint_report_html()   problems in a rendered customer report (sample or fallback markers, missing disclaimer,
                     flagged vocabulary in the visible text)
INCOMPLETE_MARKERS   phrases that mean "this report is not complete"; a sold report must never contain them
"""
import html as _html
import re

import mulank_bank

# CLAUDE.md section 5b: words that push a page or report into Meta's "Health & Wellness" category.
FLAGGED = (r"anxi", r"stress", r"depress", r"panic", r"trauma", r"therap", r"counsel", r"mental", r"well-?being", r"wellness",
           r"burn-?out", r"overwhelm", r"breakdown", r"spiral", r"coping", r"\bcope\b", r"self-care", r"healing", r"\bheal\b",
           r"peace of mind", r"inner peace", r"diagnos", r"symptom", r"disorder", r"treatment", r"\bcure\b", r"remedy", r"disease",
           r"illness", r"patient", r"clinical", r"medic", r"prescription", r"doctor", r"health", r"cancer", r"chronic", r"disabilit",
           r"adhd", r"weight", r"\bdiet\b", r"calorie", r"nutrition", r"\bfat\b", r"obes", r"detox")
INCOMPLETE_MARKERS = ("does not include", "is not included in this edition", "not included for your numbers", "Sample report",
                      "not production-verified", "PENDING EXPERT REVIEW", "design review copy")
PLACEHOLDER = re.compile(r"\{|\}|\bTODO\b|\bTBD\b|\bXXX\b|lorem|\[\[|\]\]|PLACEHOLDER", re.I)
DISCLAIMER = "belief system, not a science"
_BANKS = ("M", "B", "PS", "PM", "PG", "CB", "LP", "Y")
# Editing notes that once lived inside the wording rows ("NO CHANGE", "(deleted; ...)", "One clause shown: ..."). Customer text
# never contains these; a row or a rendered report that does is a drafting leftover, not wording.
NOTE_MARKERS = re.compile(r"NO CHANGE|\(deleted|^unchanged$|One clause shown|Both clauses shown|\bHeading:|\bText:|stored per pair|"
                          r"Behaviour when|CHANGE-SUMMARY", re.M)


def _leaves(obj, path=""):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _leaves(v, f"{path}/{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from _leaves(v, f"{path}[{i}]")


def flagged_words(text: str) -> list:
    t = text.lower()
    return [w for w in FLAGGED if re.search(w, t)]


def lint_bank(bank=None) -> list:
    """Returns a list of (where, problem). Empty list = passes."""
    data = (bank or mulank_bank.BANK)
    issues, seen = [], {}
    for name in _BANKS:
        for where, text in _leaves(data.get(name, {}), name):
            if not text.strip():
                if not re.search(r"bonds\[\d+\]\[3\]$", where):      # the blank CSS-class slot in a bond tuple is not text
                    issues.append((where, "empty text"))
                continue
            if PLACEHOLDER.search(text):
                issues.append((where, "placeholder or unresolved slot"))
            hits = flagged_words(text)
            if hits:
                issues.append((where, "flagged vocabulary: " + ", ".join(hits)))
            if name in ("PS", "PM", "PG", "CB") and len(text.split()) >= 8:
                owner = where.split("/")[1]
                prev = seen.setdefault(text.strip().lower(), owner)
                if prev != owner:
                    issues.append((where, f"same paragraph also used for {name}:{prev} (another pair's reading)"))
    for key, text in (data.get("rows") or {}).items():           # the approved wording rows: slots like {X} are legitimate here
        where = f"rows/{key}"
        if not text.strip():
            issues.append((where, "empty text"))
            continue
        if NOTE_MARKERS.search(text):
            issues.append((where, "editing note left in the wording"))
        hits = flagged_words(text)
        if hits:
            issues.append((where, "flagged vocabulary: " + ", ".join(hits)))
    return issues


def visible_text(doc: str) -> str:
    t = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", doc, flags=re.S)
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", t)))


def lint_report_html(doc: str, expected_cards: int = 15, vocabulary: bool = True, slots: bool = False) -> list:
    """Problems in a rendered production report. `vocabulary=False` skips the flagged-word scan (the runtime guard
    only refuses incomplete reports; vocabulary is an approval-time check). `slots=True` also fails on a leftover `{` or `}`
    and on editing notes; it is for the release gate (tests), not the runtime guard, because a customer's name may contain a brace."""
    issues = []
    text = visible_text(doc)
    if slots:
        if "{" in text or "}" in text:
            issues.append(("report", "unresolved slot or brace in the visible text"))
        if NOTE_MARKERS.search(text):
            issues.append(("report", "editing note in the visible text"))
    for marker in INCOMPLETE_MARKERS:
        if marker.lower() in text.lower():
            issues.append(("report", f"incomplete or sample marker: {marker}"))
    if DISCLAIMER not in text:
        issues.append(("report", "belief-system disclaimer missing"))
    n = len(re.findall(r'<section class="page', doc))
    if n != expected_cards:
        issues.append(("report", f"{n} cards, expected {expected_cards}"))
    hits = flagged_words(text) if vocabulary else []
    if hits:
        issues.append(("report", "flagged vocabulary: " + ", ".join(hits)))
    return issues
