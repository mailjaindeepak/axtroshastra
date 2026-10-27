"""Diwali Wealth & Prosperity Report: deterministic prose bank (CONTENT role).

Contract (docs/diwali/BUILD-BRIEF.md "Prose contract"):
  NARR_KEYS          ordered [(key, brief, group)], group A|B|C|D = the 4 AI calls.
  bank(payload)      -> {key: text} for EVERY NARR_KEYS key (+ a few bank-only keys the
                        renderer uses but the AI never rewrites: titles, gift, blessing,
                        Manglik facts).
  lint_text(text, allow_dates=False) -> [problem, ...]

Voice = approved Mock 3C v2 (docs/diwali/mock/kit-3c/m3_*.html). R2 per topic:
one-word state (rendered from payload, not in the text) -> `what` -> `do` / `watch`
-> `why` (the only place a chart reason appears) -> `when`. Values carry NO labels
("Do:", "Why:" ...): the renderer adds them. Every chart-derived sentence is built from
payload facts (planets, houses, signs, month positions, states); nothing from the mock
persona is hard-coded (CLAUDE.md §22).

Multi-line values (`\n` separated): wrapped.words ("WORD: line" x3), plan.d30/d90/d365
(3 steps each), sadesati.steps ("Title: text" x5), marriage.helps is one paragraph.
"""
from __future__ import annotations

import hashlib
import re

# ── fixed vocabulary ──────────────────────────────────────────────────────────
AREAS = ["money", "career", "business", "family", "marriage"]
AREA_NAME = {"money": "Money", "career": "Career", "business": "Business",
             "family": "Family & children", "marriage": "Marriage", "luck": "Better luck"}
TOPIC_COUNTS = {"money": 7, "career": 6, "business": 5, "family": 5, "marriage": 5}
MONTH_YMS = [f"2026-{m:02d}" for m in (11, 12)] + [f"2027-{m:02d}" for m in range(1, 11)]
_MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

HOUSE = {1: "the part for yourself", 2: "the money part", 3: "the effort and courage part",
         4: "the home part", 5: "the children and planning part",
         6: "the loans and competition part", 7: "the partner part",
         8: "the shared-money part", 9: "the luck part", 10: "the work part",
         11: "the gains part", 12: "the spending part"}
AREA_HOUSES = {"money": [2, 11], "career": [10, 6], "business": [7, 10, 11],
               "family": [4, 5], "marriage": [7], "luck": [9]}
# kind of work by the sign on the work part: used once, in "Work that rewards ..."
SIGN_TRAIT = {"Aries": "quick starts and taking charge", "Taurus": "steady building and good taste",
              "Gemini": "talking, writing and trade", "Karka": "caring for people and running a team",
              "Leo": "leading others and being seen", "Virgo": "careful detail, numbers and service",
              "Libra": "fair dealing and working with partners", "Scorpio": "research and quiet, deep work",
              "Sagittarius": "teaching, advice and wide plans", "Capricorn": "hard work, order and long projects",
              "Aquarius": "new ideas, networks and technology", "Pisces": "helping others and creative work"}
# what the partner part's sign values in a close bond
VALUE7 = {"Aries": "honesty and a partner with spirit", "Taurus": "loyalty and a settled, steady home",
          "Gemini": "good talk and a light, friendly bond", "Karka": "care and a close family feel",
          "Leo": "warmth and a bond you can be proud of", "Virgo": "practical help and kept promises",
          "Libra": "fairness and an easy, balanced bond", "Scorpio": "deep trust and privacy",
          "Sagittarius": "honesty and room to grow", "Capricorn": "loyalty and an honest, steady bond",
          "Aquarius": "friendship and room to be yourself", "Pisces": "kindness and a gentle bond"}
# what the Moon sign needs in a close bond (one line, Partnership traits only)
MOON_NEED = {"Aries": "room to act on your own", "Taurus": "steady comfort", "Gemini": "lively talk",
             "Karka": "a close, caring home", "Leo": "warm praise", "Virgo": "practical care", "Libra": "fairness and ease",
             "Scorpio": "deep trust", "Sagittarius": "honesty and space", "Capricorn": "a partner you can rely on",
             "Aquarius": "friendship and space", "Pisces": "gentle kindness"}
# what helps at home, by the sign on the home part (Family & children)
HOME4 = {"Aries": "a quick, honest word", "Taurus": "a slow meal together", "Gemini": "a light chat at the end of the day",
         "Karka": "a warm, caring word", "Leo": "a word of praise", "Virgo": "a small, practical help",
         "Libra": "a fair hearing for everyone", "Scorpio": "trust that stays private", "Sagittarius": "an open, honest talk",
         "Capricorn": "a promise kept", "Aquarius": "room for each person", "Pisces": "a gentle word"}
# how gatherings go well, by the sign on the children and planning part
GATHER5 = {"Aries": "lively and short", "Taurus": "rich in good food", "Gemini": "full of talk and games",
           "Karka": "close and home-cooked", "Leo": "bright and generous", "Virgo": "well planned",
           "Libra": "graceful and balanced", "Scorpio": "small and close", "Sagittarius": "open to many guests",
           "Capricorn": "simple and on time", "Aquarius": "open to friends", "Pisces": "musical and gentle"}
# how shared choices go smoothly, by the sign on the partner part
SHARE7 = {"Aries": "a quick, clear yes or no", "Taurus": "slow, sure steps", "Gemini": "talking every option through",
          "Karka": "thinking of the whole family", "Leo": "a clear lead from one person", "Virgo": "the numbers on paper",
          "Libra": "a fair split of every cost", "Scorpio": "trust and privacy", "Sagittarius": "a shared long-term aim",
          "Capricorn": "a firm plan and a date", "Aquarius": "room for both views", "Pisces": "patience and kindness"}
# what makes close talks easier, by the Moon sign
TALK = {"Aries": "you pause before you answer", "Taurus": "nobody is rushed", "Gemini": "you listen as much as you talk",
        "Karka": "the mood at home is settled", "Leo": "each side feels heard", "Virgo": "small things are not picked at",
        "Libra": "both sides are weighed fairly", "Scorpio": "old hurts stay out of it", "Sagittarius": "you speak plainly but kindly",
        "Capricorn": "feelings are said, not only plans", "Aquarius": "you stay close, not distant", "Pisces": "you say what you need"}
# what people you are drawn to are like, by the sign of the partnership planet (Venus, or Jupiter for women)
PARTNER_SIGN = {"Aries": "direct, brave and quick to act", "Taurus": "steady, loyal and fond of simple comforts",
                "Gemini": "lively, curious and easy to talk to", "Karka": "caring, protective and close to family",
                "Leo": "warm, generous and proud of their work", "Virgo": "practical, careful and helpful",
                "Libra": "fair, gentle and good company", "Scorpio": "deep, loyal and private",
                "Sagittarius": "honest, open and fond of learning", "Capricorn": "serious, hard-working and true to their word",
                "Aquarius": "independent, friendly and full of new ideas", "Pisces": "kind, gentle and giving"}
# topic title -> (the topic in plain words, topic tags); the plain words name a topic in its second wording
TOPIC_META = {
    "Will money get better after this Diwali?": ("your money", {"money", "growth", "savings"}),
    "When does your next good money time start?": ("large money moves", {"money", "plans", "growth"}),
    "Which months suit saving, and which suit spending?": ("saving and spending", {"savings", "buys", "gold", "order"}),
    "When is a good time to clear loans?": ("clearing loans", {"loans", "order", "effort"}),
    "If you had a loss, when do things recover?": ("winning back what was lost", {"money", "effort", "order", "rivals"}),
    "Where does your money come from most easily?": ("how money comes to you", {"money", "trade", "gains", "name"}),
    "Your wealth combination": ("long-term wealth", {"money", "savings", "plans"}),
    "When could your next big break or promotion come?": ("a promotion", {"work", "name", "lead"}),
    "Should you switch or stay?": ("a job move", {"work", "new", "plans"}),
    "When is a good time to ask for a raise?": ("a raise talk", {"work", "talks", "money", "name"}),
    "If you lost your job, when do things pick up?": ("finding new work", {"work", "effort", "people"}),
    "What kind of work suits you most?": ("your choice of work", {"work", "skills", "self"}),
    "Work abroad or travel for work: which months suit a move?": ("work travel", {"abroad", "travel", "new"}),
    "When do your studies go best?": ("your studies", {"study", "learning", "focus"}),
    "How may exams and results go?": ("exams", {"study", "effort", "numbers"}),
    "When might your first job or internship come?": ("a first job", {"work", "new", "effort"}),
    "Study abroad: which months suit it?": ("study abroad", {"abroad", "study", "travel"}),
    "Learning a new skill": ("a new skill", {"skills", "learning", "focus"}),
    "When is a good time to return to work?": ("a return to work", {"work", "effort", "new"}),
    "Can a home-run income work for you?": ("a home-run income", {"side", "trade", "home"}),
    "Fitting work around home": ("balancing work and home", {"home", "order", "family"}),
    "Travel for work or family": ("trips", {"travel", "abroad"}),
    "Leading your people": ("leading your team", {"lead", "staff", "name"}),
    "When to step up": ("a larger step", {"growth", "new", "lead"}),
    "Your name and reputation": ("your good name", {"name", "people"}),
    "Delegation": ("handing work over", {"staff", "order", "focus"}),
    "Work travel": ("work trips", {"travel", "abroad", "new"}),
    "A second line of leaders": ("building a second line", {"staff", "lead", "plans"}),
    "How does your business look from this Diwali to the next?": ("the business", {"business", "trade", "growth"}),
    "When is a good time to start or expand?": ("expansion", {"growth", "new", "plans"}),
    "Partner or alone?": ("partnerships", {"partner", "people"}),
    "When do new deals, hiring and new account books fit?": ("deals and hiring", {"deals", "staff", "trade", "numbers"}),
    "When to go slow on spending and credit?": ("spending and credit", {"savings", "loans", "order"}),
    "Does your chart lean to business or a job?": ("the choice between business and a job", {"business", "work", "trade"}),
    "When is a good time to start a side income?": ("a side income", {"side", "trade", "new"}),
    "Partner or alone for a side plan?": ("a partner for a side plan", {"partner", "people"}),
    "How small to start, and which months suit it?": ("a small start", {"plans", "order", "trade"}),
    "Which months to go slow on new spending?": ("new spending", {"savings", "order", "buys"}),
    "Business or a job: where does your chart lean?": ("the choice between business and a job", {"business", "work"}),
    "When could you try a small project?": ("a small project", {"new", "trade", "skills"}),
    "Which months suit learning trade skills?": ("trade skills", {"skills", "trade", "learning"}),
    "Which months to go slow on spending?": ("your spending", {"savings", "order"}),
    "Could a small home venture suit you?": ("a home venture", {"side", "trade", "home"}),
    "When is a good time to start?": ("a first start", {"new", "plans"}),
    "With a partner or alone?": ("working with a partner", {"partner", "people"}),
    "The family money picture": ("family money", {"money", "family", "savings"}),
    "The whole family": ("family life", {"family", "home", "care"}),
    "Family events and celebrations": ("family events", {"family", "people", "warmth"}),
    "House move or property": ("property steps", {"property", "home", "buys"}),
    "Moving city or abroad": ("a move", {"abroad", "travel", "new", "home"}),
    "Which months may bring happy news in your family?": ("happy family news", {"children", "family", "plans"}),
    "More warmth in your relationships": ("close bonds", {"partner", "warmth", "care"}),
    "Important relationship decisions": ("shared choices", {"partner", "plans", "talks"}),
    "Care in close talks": ("close talks", {"talks", "reactions", "care"}),
    "Your partnership traits": ("partnership", {"partner", "warmth"}),
    "Does your chart show Manglik, and does it matter?": ("a match", {"partner"})}
# a lead phrase that points at the peak of the area (its best months), not at the topic's first month
_PEAK_RE = re.compile(r"\b(most of all|with a lift|best|shines|fastest|warmest|warmer months|firmer months|it comes|"
                      r"to rise|seen more|growth shows|most likely|go best|fits best|larger buys) \{pos\}")
SOURCE_BY_HOUSE = {1: "your own name and effort", 2: "family money and savings that grow",
                   3: "skills you build yourself", 4: "property and the home",
                   5: "planning and long-term savings", 6: "service and regular daily effort",
                   7: "clients and business partners", 8: "shared money and family support",
                   9: "elders, teachers and good fortune", 10: "your work and position",
                   11: "contacts, friends and gains", 12: "clients and trade far away"}
SUN_DO = {1: "put yourself forward", 2: "review your accounts", 3: "make calls and short trips",
          4: "home and family plans", 5: "learning and planning", 6: "clear pending work and dues",
          7: "talks with partners and clients", 8: "sort shared money and papers",
          9: "ask elders for advice", 10: "push your standing at work",
          11: "follow up with contacts", 12: "plan quietly and rest well"}
MARS_WATCH = {1: "quick replies", 2: "sharp words about money", 3: "rushed decisions",
              4: "friction at home", 5: "hasty bets", 6: "arguments at work",
              7: "heated talks with partners", 8: "sudden costs", 9: "arguing with elders",
              10: "clashes at work", 11: "rushed deals with friends", 12: "extra spending"}
LIFE = {1: "how you come across", 2: "talks about money", 3: "messages and short trips", 4: "the home",
        5: "plans and learning", 6: "work and dues", 7: "partner and client talks", 8: "shared money",
        9: "talks with elders", 10: "work", 11: "friends and contacts", 12: "spending"}
TAG_DO = {"gold": "good for gold or a planned buy", "loans": "pay down loans",
          "deals": "new deals and account books", "family": "family plans",
          "travel": "a useful trip", "property": "property steps", "career": "step up at work",
          "study": "focused study", "marriage": "time with loved ones"}
STRENGTH = {"Sun": ("A natural lead", "People tend to look to you when a call has to be made."),
            "Moon": ("A feel for people", "You read moods well, and people open up to you."),
            "Mars": ("Energy and drive", "You put real energy into what you start."),
            "Mercury": ("A sharp head for numbers", "You think quickly and count carefully."),
            "Jupiter": ("Good judgement and planning", "You read people and plans well, and long-term plans suit you."),
            "Venus": ("A warm way with people", "People enjoy working with you, and that opens doors."),
            "Saturn": ("Steady effort", "You tend to keep going when others stop, and slow work adds up for you."),
            "Rahu": ("A push for more", "You are drawn to new ground, and you are not afraid to try."),
            "Ketu": ("Quiet focus", "You can go deep on one thing and shut out the noise.")}
AREA_PHRASE = {"money": "money", "career": "work", "business": "business", "family": "home life",
               "marriage": "close bonds", "luck": "luck"}
STRENGTH_DO = {"Sun": "Take the lead on one task others avoid", "Moon": "Check in with one person who matters each week",
               "Mars": "Start the job you keep putting off", "Mercury": "Review your numbers every Sunday",
               "Jupiter": "Write a one-page plan after Diwali and look at it monthly",
               "Venus": "Meet one useful contact each month", "Saturn": "Give one hard task one fixed hour every week",
               "Rahu": "Try one new thing each month, small and on paper", "Ketu": "Pick one skill and go deep on it"}
ORD = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth", 7: "seventh",
       8: "eighth", 9: "ninth", 10: "tenth", 11: "eleventh", 12: "twelfth"}
NUM = {0: "no", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
       8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}
ROLE_OF = {"job": "your job", "business": "your business", "student": "your studies", "home": "running the home"}
WORK_AS = {"job": "someone with a job", "business": "a business owner",
           "student": "a student", "home": "someone who runs the home"}
SITUATION_ORDER = {"student": ["career", "money", "marriage", "family", "business"],
                   "job": ["career", "money", "family", "marriage", "business"],
                   "business": ["business", "money", "career", "family", "marriage"],
                   "home": ["family", "money", "marriage", "career", "business"]}
EX = {  # age-band examples (spec §3): examples and tone only
    "u25": {"big": "a course fee or a first bike", "loan": "an education loan",
            "work": "a first job or internship", "save": "a small monthly saving",
            "goal": "studies and a first job"},
    "25_40": {"big": "a home loan step or a car", "loan": "a home or car loan",
              "work": "a move to a better company", "save": "a fixed monthly saving",
              "goal": "growth and a home of your own"},
    "40_60": {"big": "a larger home or a property", "loan": "a property loan",
              "work": "a senior role or an expansion", "save": "a fund for the family's future",
              "goal": "building wealth and the family's future"},
    "60p": {"big": "a family property step or a gift to the family", "loan": "an old loan",
            "work": "advising others or a part-time role", "save": "steady monthly income",
            "goal": "steady income and passing things on"},
}
INCOME = {"business": "a new client or a repeat order", "job": "a raise or extra paid work",
          "student": "a stipend or paid project", "home": "household savings or a side income"}
DEFAULT_GIFT_MESSAGE = ("Wishing you a bright Diwali and good months ahead. "
                        "Here is what your chart says till next Diwali. With love.")

# ── lint ──────────────────────────────────────────────────────────────────────
_BANNED = [
    # CLAUDE.md §5b (stems, word-boundary anchored so "scope"/"secure"/"fate" stay clean)
    r"anxi\w*", r"stress\w*", r"depress\w*", r"panic\w*", r"trauma\w*", r"therap\w*",
    r"counsel\w*", r"mental health", r"mental wellbeing", r"well-?being", r"wellness",
    r"burn-?out", r"overwhelm\w*", r"breakdown", r"spirall?ing", r"cop(e|es|ing)",
    r"self-care", r"heal\w*", r"emotional distress", r"peace of mind", r"calm your mind",
    r"inner peace", r"diagnos\w*", r"symptom\w*", r"disorder\w*", r"treatment\w*",
    r"cure[sd]?", r"remed\w*", r"disease\w*", r"illness\w*", r"patients?", r"clinic\w*",
    r"medicat\w*", r"medicine\w*", r"prescri\w*", r"doctor\w*", r"medical\w*",
    r"unhealthy", r"cancer\w*", r"chronic\w*", r"disabilit\w*", r"adhd", r"weight\w*",
    r"diet\w*", r"calorie\w*", r"nutrition\w*", r"fat", r"obes\w*", r"detox\w*",
    r"condition\w*", r"pressure\w*", r"calm\w*", r"relie[fv]\w*", r"exhaust\w*",
    r"tension\w*", r"worr\w*", r"breath\w*",
    # spec §2 rule 8 extras
    r"dosha\w*", r"curse\w*", r"danger\w*", r"bad luck", r"guarantee\w*", r"prevent\w*",
    r"will happen",
    # R3 wording
    r"stretch\w*", r"windows?", r"astro\s*sage",
    # status phrases (Marriage / Family never assume status)
    r"your (wife|husband|spouse|marriage|children)", r"the right person", r"marry again",
    r"when children may come",
]
_BANNED_RE = re.compile(r"\b(" + "|".join(_BANNED) + r")\b", re.I)
_MONTH_RE = re.compile(
    r"\b(January|February|March|April|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b"
    # "May": a month when followed by a date/dash, or mid-sentence after a lowercase word or comma
    # ("around May", "late May"); a sentence-initial "May this Diwali ..." is a wish, not a month.
    r"|\bMay(?=\s*(\d|–|-))|(?<=[a-z,;:] )May\b|(?<=[–-])May\b")
_YEAR_RE = re.compile(r"\b20\d\d\b")
_ORDINAL_HOUSE = re.compile(r"\b(1st|2nd|3rd|[4-9]th|1[0-2]th)\b|\b(first|second|third|fourth|fifth|sixth|seventh|"
                            r"eighth|ninth|tenth|eleventh|twelfth) house\b|\bhouse (\d+|one|two|three|four|five|six|"
                            r"seven|eight|nine|ten|eleven|twelve)\b", re.I)
_NICK_RE = re.compile(r"\bpart for yourself\b|\b(money|effort and courage|home|children and planning|"
                      r"loans and competition|partner|shared-money|luck|work|gains|spending) part\b", re.I)
_YEAR_WORD = re.compile(r"\byear\b", re.I)
_YEAR_OK = re.compile(r"new year|year at a glance|year gone by", re.I)


def lint_text(text: str, allow_dates: bool = False) -> list[str]:
    """Problems in one visible string. allow_dates=True only for the 2 date pages
    (timeline.*, months.*) and the Wrapped card, where month names are allowed (O-30)."""
    if not text:
        return []
    probs = [f"banned word: {m.group(0)!r}" for m in _BANNED_RE.finditer(text)]
    if re.search(r"[()\[\]]", text):
        probs.append("bracket in prose")
    if not allow_dates:
        if _MONTH_RE.search(text):
            probs.append("month name outside the date pages")
        if _YEAR_RE.search(text):
            probs.append("year number outside the date pages")
    if _YEAR_WORD.search(_YEAR_OK.sub("", text)):
        probs.append('"year" alone (say "from this Diwali to the next")')
    for sent in re.split(r"(?<=[.!?])\s+", text):
        if _ORDINAL_HOUSE.search(sent) and _NICK_RE.search(sent):
            probs.append("plain house name and house number together")
            break
    return probs


# ── small helpers ─────────────────────────────────────────────────────────────
SIGNS = ["Aries", "Taurus", "Gemini", "Karka", "Leo", "Virgo", "Libra", "Scorpio",
         "Sagittarius", "Capricorn", "Aquarius", "Pisces"]


def _ordn(n: int) -> str:
    return f"{n}" + ("th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def _lab(ym: str) -> str:
    y, m = ym.split("-")
    return f"{_MON[int(m) - 1]} {y}"


def _rng(yms: list[str]) -> str:
    """'Jun–Jul 2027' style label for a run of months (dates pages only)."""
    if not yms:
        return ""
    a, b = sorted(yms)[0], sorted(yms)[-1]
    if a == b:
        return _lab(a)
    ya, yb = a[:4], b[:4]
    ma, mb = _MON[int(a[5:]) - 1], _MON[int(b[5:]) - 1]
    return f"{ma}–{mb} {yb}" if ya == yb else f"{ma} {ya}–{mb} {yb}"


def _idx(ym: str) -> int:
    return MONTH_YMS.index(ym) if ym in MONTH_YMS else 0


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def has_best(p: dict) -> bool:
    """Spec §2 rule 10: a "best time" exists only with a sure birth time (not T2/T3) and an area that
    marks best months. The engine still fills best_time (top good run); renderers then call it a good time."""
    areas = p.get("areas") or {}
    # best_time is a real best run only when a month in it has tone "best"; else it is the engine's
    # fallback top good run and must never be printed as "your single best time"
    bt = p.get("best_time") or {}
    real = any(m.get("tone") == "best" and (bt.get("from") or "") <= (m.get("ym") or "") <= (bt.get("to") or "")
               for m in p.get("months") or [])
    return real and (p.get("meta") or {}).get("time_quality") not in ("T2", "T3") and any(
        ((areas.get(a) or {}).get("windows") or {}).get("best") for a in AREAS)


# A buyer with no best time (T2/T3, or no month toned best) is never told a time is best, brightest or strongest,
# in any wording: these turn each such claim into plain good-time words.
_NO_BEST = [(r"\bmost of all\b", "mainly"), (r"\s+most\b(?!\s+of)", ""), (r"\b(shows?|grows?|comes?|counts?) most\b(?! easily)", r"\1"),
            (r"\bshines? brightest\b", "firms up"),
            (r"\bshines\b", "shows"), (r"\bshine\b", "show"), (r"\bpeaks?\b", "builds"), (r"\bburns? brightest\b", "glows"),
            (r"\b(shines?|glows?|grows?|moves?) (?:most|brightest)\b", r"\1 well"),
            (r"\b(goe?s?|fits?|works?|grows?|moves?) best\b", r"\1 well"), (r"\bsuits? you best\b", "suits you"),
            (r"\b(?:brightest|strongest) (months?|times?|weeks|days)\b", r"good \1"),
            (r"\blooks? strongest\b", "looks good"),
            (r"\b(?:best|strongest|brightest) (?=(?:in|early|late|after|before|from|around|during|as soon|once|straight"
             r"|soon|right after|at the|near|closer|toward|within|well|fairly|by|about|halfway|just|midway)\b)", "mainly "),
            (r"\b([Bb])est (time|months?)\b", lambda m_: {"B": "G", "b": "g"}[m_.group(1)] + "ood " + m_.group(2))]


def no_best_text(v: str) -> str:
    for pat, rep in _NO_BEST:
        v = re.sub(pat, rep, v)
    return v




def _sent(s: str) -> str:
    s = (s or "").strip()
    return s if not s or s[-1] in ".!?" else s + "."


def _what3(lead: str, body: str, flavor: str) -> str:
    """A topic's 'what' in at most 3 sentences (spec §2 R2): the lead, then the chart's meaning for the
    topic (when there is one), then the advice; spare advice sentences only while the total stays at 3."""
    sp = lambda t: [x for x in re.split(r"(?<=[.!?])\s+", (t or "").strip()) if x]
    ls, bs = sp(lead), sp(body)
    room = 3 - len(ls[:1]) - bool(flavor)
    return " ".join(ls[:1] + ([flavor] if flavor else []) + bs[:max(room, 0)]).strip()


def _pn(name: str) -> str:
    return f"the {name}" if name in ("Sun", "Moon") else name


def _dig(d: str | None) -> str:
    return {"own": ", in its own sign", "exalted": ", in its exalted sign",
            "debilitated": ", in a sign where it has to work harder",
            "friendly": ", in a friendly sign", "friend": ", in a friendly sign"}.get((d or "").lower(), "")


# Where months fall, in plain words: the season (the engine's own seasons, as printed on the Wrapped card:
# winter Nov-Jan, spring Feb-Apr, summer May-Jul, autumn Aug-Oct), keyed by the month's place in the span.
# Two plain wordings per month; a report alternates them. Never more than four words.
SEASON_W = {0: ["right after Diwali", "soon after Diwali", "just after Diwali"],
            1: ["in midwinter", "by midwinter", "as winter deepens"],
            2: ["in late winter", "as winter ends", "near winter's end"],
            3: ["in early spring", "as spring begins", "as spring opens"],
            4: ["in spring", "by mid-spring", "in mid-spring"],
            5: ["in late spring", "as spring ends", "at spring's end"],
            6: ["in early summer", "as summer begins", "as summer starts"],
            7: ["in midsummer", "by midsummer", "in the summer heat"],
            8: ["in late summer", "as summer ends", "as summer closes"],
            9: ["in early autumn", "as autumn begins", "as autumn opens"],
            10: ["in autumn", "by mid-autumn", "in mid-autumn"],
            11: ["near next Diwali", "before next Diwali", "as Diwali nears"]}
# a month as a bare noun, for after a preposition ("the slower months of late winter")
SEASON_BARE = {0: "Diwali", 1: "midwinter", 2: "late winter", 3: "early spring", 4: "spring", 5: "late spring",
               6: "early summer", 7: "midsummer", 8: "late summer", 9: "early autumn", 10: "autumn", 11: "next Diwali"}
SEASON_NAME = {0: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
               6: "summer", 7: "summer", 8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"}
# the same phrases grouped by quarter of the span (0 = first two months ... 3 = last four), for checks
POSV = {b: [w for i, ws in SEASON_W.items() if (0 if i <= 1 else 1 if i <= 4 else 2 if i <= 7 else 3) == b for w in ws]
        for b in range(4)}


class _Chart:
    """Read-only view over the payload's chart + month facts."""

    def __init__(self, p: dict):
        self.p = p
        c = p.get("chart") or {}
        self.planets = {x.get("name"): x for x in c.get("planets") or []}
        self.houses = {int(k): v for k, v in (c.get("houses") or {}).items()}
        self.months = {m.get("ym"): m for m in p.get("months") or []}

    def sign(self, h):
        return (self.houses.get(h) or {}).get("sign", "")

    def lord(self, h):
        return (self.houses.get(h) or {}).get("lord", "")

    def trait(self, h):
        return SIGN_TRAIT.get(self.sign(h), "steady, careful work")

    def pl(self, name):
        return self.planets.get(name) or {}

    def transit(self, ym, planet):
        return ((self.months.get(ym) or {}).get("transits") or {}).get(planet) or {}

    def natal_facts(self, houses: list[int]) -> list["_Fact"]:
        """True birth-chart facts about these parts: where each part's ruler sits, and which planets sit in
        the part. One fact = a _Fact: the plain ways to say it (a long report needs more than one sentence
        shape; the fact itself is said once), its identity, and the part of life it points to."""
        out = []
        for h in houses:
            lord = self.lord(h)
            lp = self.pl(lord)
            L, A = _pn(lord), HOUSE[h]
            if lord and lp.get("house"):
                sg = lp.get("sign") or "its sign"
                if lp["house"] == h:
                    out.append(_Fact((f"{L} rules {A} and sits right there.", f"{A} holds its own ruler, {L}.",
                                      f"{L}, ruler of {A}, stays in its own part, in {sg}."), ("O", lord, h), h))
                else:
                    B = HOUSE[lp["house"]]
                    out.append(_Fact((f"{L}, ruler of {A}, sits in {B}.", f"{L} rules {A} from {B}.",
                                      f"{L} rules {A} and is placed in {B}.", f"{L}, ruler of {A}, is in {sg}.",
                                      f"{A} is ruled by {L}, in {sg}."), ("R", lord, h), lp["house"]))
            for name, x in self.planets.items():
                if x.get("house") == h and name != lord:
                    P, sg = _pn(name), x.get("sign") or "its sign"
                    out.append(_Fact((f"{P} sits in {A}, in {sg}.", f"{A} holds {P}, in {sg}.", f"{P} is placed in {A}.",
                                      f"{P}, in {sg}, sits in {A}.", f"Your chart has {P} in {sg}."), ("O", name, h), h))
        return out

    def ruler_tie(self, h, skip=""):
        """Plain-voice tie (no 'ruler of' wording): where the part's own planet is placed."""
        L = self.lord(h)
        b = self.pl(L).get("house")
        if not L or L == skip or b not in HOUSE:
            return ""
        return f", and {_pn(L)} is " + ("right there" if b == h else
                                           ("placed in", "settled in", "found in", "at home in", "set in", "resting in", "seated in")[(h * 3 + b + len(skip)) % 7]
                                           + f" {self.pl(L).get('sign') or HOUSE[b]}")

    def transit_facts(self, yms, houses, planets=("Jupiter", "Saturn", "Rahu", "Ketu")):
        """Slow planets only: the fast ones pass every part within a few months, so they explain nothing."""
        out, seen = [], set()
        for ym in sorted(yms or []):
            for pl in planets:
                t = self.transit(ym, pl)
                h = t.get("house")
                if h in houses and (pl, h) not in seen:
                    seen.add((pl, h))
                    P, A = _pn(pl), HOUSE[h]
                    f = ((f"{P} turns back in {A} for a while.", f"{P} slows and turns back in {A}.")
                         if t.get("retro") and pl not in ("Rahu", "Ketu") else
                         (f"{P} moves through {A}.", f"{P} passes through {A} at that time.", f"{P} travels through {A}."))
                    tie = self.ruler_tie(h, pl)
                    tied = () if t.get("retro") and pl not in ("Rahu", "Ketu") else tuple(x[:-1] + tie + "." for x in f if tie)
                    out.append(_Fact(tied + f, ("T", pl, h), h))
        return out

    def aspect_facts(self, yms, houses):
        """Jupiter and Saturn also act on the parts they look at (Jupiter: 5th, 7th and 9th from where it
        passes; Saturn: 3rd, 7th and 10th): a true reason for a topic whose part they look at in its months."""
        out, seen = [], set()
        for ym in sorted(yms or []):
            for pl, steps in (("Jupiter", (4, 6, 8)), ("Saturn", (2, 6, 9))):
                b = self.transit(ym, pl).get("house")
                for s in steps if b else ():
                    h = (b - 1 + s) % 12 + 1
                    if h in houses and (pl, h) not in seen:
                        seen.add((pl, h))
                        A, B = HOUSE[h], HOUSE[b]
                        tie = self.ruler_tie(h, pl)
                        out.append(_Fact(((f"{pl} looks at {A}{tie}.", f"{pl}, passing {B}, looks at {A}{tie}.") if tie else ())
                                         + (f"{pl} looks at {A} from {B}.", f"{pl}, passing {B}, looks at {A}.",
                                            f"{A} gets {pl}'s look from {B}.", f"{pl} turns its look on {A}."), ("A", pl, h), h))
        return out


class _Fact(tuple):
    """One chart fact: its wordings (capitalised), an identity (kind, planet, part) and the part it points to."""
    def __new__(cls, texts, key, to):
        self = super().__new__(cls, tuple(_cap(x) for x in texts))
        self.key, self.to = key, to
        return self


def _houses_in(text: str) -> list[int]:
    """The chart parts a sentence names, in the order it names them."""
    hits = []
    for h, nm in HOUSE.items():
        for m in re.finditer(re.escape(nm), text or ""):
            hits.append((m.start(), h))
    # "the money part" also sits inside "the shared-money part": keep the longest name at each place
    hits.sort()
    keep = [x for x in hits if not any(y[0] < x[0] < y[0] + len(HOUSE[y[1]]) for y in hits if y != x)]
    return [h for _, h in keep]


# ── topic text ────────────────────────────────────────────────────────────────
# Each topic: title, leads by state ({pos} = when its months start, {cpos} = when its careful time falls),
# body (plain advice), do, watch, mean.
# do / watch: one string, or a pair (open, quiet): the first when the ruler of the topic's chart part sits in
# an open, strong place (1, 4, 5, 7, 9, 10), the second when it sits in a quieter one or the topic is careful.
# The second Watch never names a careful time, so a buyer with no careful month never reads one.
# mean: what the topic's chart reason (its Why line) means for it, in plain words: {h} = the part of life that
# reason points to (HELP / HELP_P). No planet names: the Why line has them. Printed only when the Why line
# names a part of the chart.
# Placeholders: {pos} {cpos} {cwhy} {big} {loan} {work} {save} {goal} {income} {t10} {src} {lean} {ng}
def _T(title, good, steady, careful, body, do, watch, mean=""):
    return {"title": title, "good": good, "steady": steady, "careful": careful,
            "body": body, "do": do, "watch": watch, "mean": mean}


# the part of life a chart part points to, as a plain noun phrase (money, work and business topics)
HELP = {1: "your own effort and name", 2: "savings and family money", 3: "your own skills and contacts",
        4: "home and property", 5: "long-term plans and learning", 6: "steady daily work",
        7: "partners and clients", 8: "shared money and family support", 9: "elders and mentors",
        10: "your work and standing", 11: "friends and contacts", 12: "work far from home"}
# the same for family and close-bond topics
HELP_P = {1: "your own moods and plans", 2: "family meals and savings", 3: "brothers, sisters and neighbours",
          4: "the home itself", 5: "the younger ones and creative plans", 6: "daily routines and helpers",
          7: "a partner or close companion", 8: "the wider family", 9: "elders and teachers",
          10: "work and standing", 11: "friends and elder siblings", 12: "trips and time away"}

MONEY = [
    _T("Will money get better after this Diwali?",
       "Money looks steadier, and it tends to build {pos}.",
       "Money holds steady, and it firms up {pos}.",
       "Money needs a careful hand at first, and it gets firmer {pos}.",
       "Small, regular gains, like {income}, tend to add up more than one lucky break.",
       ("Chase two old dues {p}.", "Follow up on two old dues {p}, politely and in writing."),
       ("Promising money before it arrives.", "Counting on money before it is in your hand."),
       "Much of the lift is likely to come from {h}."),
    _T("When does your next good money time start?",
       "Your next good money time may begin {pos} and build slowly.",
       "A good money time is on its way, and it may open {pos}.",
       "Your next good money time comes after a careful start, {pos}.",
       "A large move, like {big}, fits a good month better than a rushed one.",
       ("Keep large money moves for your good months, {p}.", "Write down one large money move and keep it until {p}."),
       ("Pulling large moves into the careful months.", "Rushing a large move just because others are."),
       "When it opens, look first to {h}."),
    _T("Which months suit saving, and which suit spending?",
       "Spending looks manageable, and saving works well {pos}.",
       "Saving and spending stay balanced, with a good month for larger buys {pos}.",
       "Your careful time{cwhy} falls {cpos}; it suits saving and planning.",
       "Hold {big} for a good month if it can wait. Large buys suit the months marked for gold on your money picture.",
       ("Put a fixed amount aside each month.", "Move a fixed amount to savings on the day money comes in."),
       ("Festival and travel spends that add up.", "Small daily spends that nobody writes down."),
       "Larger costs tend to gather around {h}, so plan those first."),
    _T("When is a good time to clear loans?",
       "Good months for paying down loans begin {pos}.",
       "Loans can be paid down at a steady pace, with a good month {pos}.",
       "New loans need care for now; paying down old ones goes better {pos}.",
       "Paying down {loan} is a good use of these months, even while new signing needs care.",
       ("Clear the highest-interest loan first.", "Pay a little extra on one loan {p}."),
       ("Signing fresh loan papers in a careful month.", "Taking a new loan to close an old one."),
       "Dues clear more easily with help from {h}."),
    _T("If you had a loss, when do things recover?",
       "Money may start to come back {pos}.",
       "Things may settle {pos}: slow and steady, not one sudden jump.",
       "Recovery takes a little time, and it starts to show {pos}.",
       "List what is owed to you, one line each, and take it back step by step.",
       ("Follow up on dues once a month.", "Ask for one part payment {p}, not the whole sum."),
       ("Trying to win it all back in one deal.", "Lending again before the old money is back."),
       "What was lost may come back through {h}."),
    _T("Where does your money come from most easily?",
       "Your money comes most easily through {src}.",
       "Money comes in steadily through {src}.",
       "Money through {src} needs care at first, then flows better {pos}.",
       "Repeat work, word of mouth and kept promises tend to bring more than lucky breaks.",
       ("Put your name on your work.", "Keep one simple record of who pays you and when."),
       ("Lending where someone else holds your money.", "Letting one source carry all your income."), ""),
    _T("Your wealth combination",
       "", "", "", "", ("Let one savings habit run untouched.", "Start one small savings habit and leave it alone."),
       ("Reading it as a promise; it is a leaning.", "Reading it as a promise; it only shows a leaning."), ""),
]

CAREER = {
    "job": [
        _T("When could your next big break or promotion come?",
           "A step up looks likely {pos}.", "Your role holds steady, with a chance to rise {pos}.",
           "Big moves at work need care at first; a good time comes {pos}.",
           "A larger role, a new project or {work} fits a good month. Until then, build the record that earns it.",
           ("Keep a list of your wins to share at review time.", "Write down one win each week and share them {p}."),
           ("Waiting to be noticed without asking.", "Taking on extra work no one sees."),
           "The step up is likely to come through {h}."),
        _T("Should you switch or stay?",
           "A move can work well {pos}.", "Staying and growing where you are suits you, with a good month to move {pos}.",
           "Hold a switch for now; a better time to move comes {pos}.",
           "If you move, line up the offer before you resign, and pick a good month for it.",
           ("Talk to three people in the field you want before you decide.", "Meet two people in the role you want {p}."),
           ("Resigning in a careful month without an offer in hand.", "Moving only to get away from one person."),
           "New openings may reach you through {h}."),
        _T("When is a good time to ask for a raise?",
           "Asking for a raise fits well {pos}.", "A raise talk can go fine {pos} if your results are clear.",
           "Wait a little on the raise talk; a good time comes {pos}.",
           "Ask when your work has just been seen, like after a finished project or a strong quarter.",
           ("Bring two clear results and one number from your work.", "Ask {p}, with your results on one page."),
           ("Asking in the middle of a heated week.", "Comparing your pay with a colleague's out loud."),
           "A raise talk goes further when it rests on {h}."),
        _T("If you lost your job, when do things pick up?",
           "Things tend to pick up {pos}.", "Things steady step by step, with a lift {pos}.",
           "The first weeks may feel slow; things pick up {pos}.",
           "Update your CV, reach out to three contacts and keep a few months of savings aside.",
           ("Send your updated CV to three contacts this month.", "Apply to a few roles each week, starting {p}."),
           ("Taking the first offer in a hurry.", "Going quiet on your contacts while you wait."),
           "New work may turn up through {h}."),
        _T("What kind of work suits you most?",
           "Work that rewards {t10} suits you, and it pays off {pos}.",
           "Work that rewards {t10} suits you, with steady gains {pos}.",
           "Work that rewards {t10} still suits you; give it time until {pos}.",
           "Roles where you can use this tend to bring both money and a good name.",
           ("Pick one skill that fits this and practise it weekly.", "Ask for one task of this kind {p}."),
           ("Staying long in work that ignores your strengths.", "Saying yes to work that does not use this."), ""),
        _T("Work abroad or travel for work: which months suit a move?",
           "Work trips and moves look useful {pos}.", "Work travel is possible at a steady pace, from {pos}.",
           "Trips and moves may cost more for a while; a better time comes {pos}.",
           "Keep each trip short and clear in its goal. This is about timing, not visa advice.",
           ("Set one goal and one budget for each trip.", "Book the useful trips {p}."),
           ("Extra trips while spending needs care.", "Trips with no clear reason behind them."),
           "Trips pay off when they serve {h}."),
    ],
    "student": [
        _T("When do your studies go best?",
           "Studies look strong {pos}.", "Studies hold steady, with sharper focus {pos}.",
           "Focus may come and go at first; it gets better {pos}.",
           "Use the good months for new topics and the steady ones for revision.",
           ("Fix a daily study hour and keep to it.", "Start the hardest subject {p}."),
           ("Leaving revision for the last week.", "Studying late every night and skipping sleep."),
           "Your studies move faster when they connect to {h}."),
        _T("How may exams and results go?",
           "Results look good {pos}.", "Results follow steady work, with a lift {pos}.",
           "Exams need extra preparation for a while; results feel easier {pos}.",
           "Results tend to follow regular work more than last-minute effort.",
           ("Take one practice test each month.", "Take a full practice paper {p}."),
           ("Comparing your marks with friends.", "Skipping the topics you find dull."),
           "Marks may improve with help from {h}."),
        _T("When might your first job or internship come?",
           "A first job or internship looks likely {pos}.", "A first job or internship may come at a steady pace, from {pos}.",
           "Applications may move slowly at first; replies come more easily {pos}.",
           "Apply early and to more than one place. A small first step can lead to a larger one.",
           ("Apply to five places in your good time.", "Send your first applications {p}."),
           ("Turning down a useful first step for a perfect one.", "Waiting for one dream offer."),
           "A first opening may come via {h}."),
        _T("What kind of work suits you most?",
           "Work that rewards {t10} suits you, and it pays off {pos}.",
           "Work that rewards {t10} suits you, with steady gains {pos}.",
           "Work that rewards {t10} still suits you; give it time until {pos}.",
           "Choose subjects and projects that let you use this, and your interest will carry you.",
           ("Try one project in this kind of work.", "Talk to one person who does this work {p}."),
           ("Choosing only what friends choose.", "Dropping it after one hard week."), ""),
        _T("Study abroad: which months suit it?",
           "Plans to study abroad look good {pos}.", "Study abroad is possible; plan it for {pos}.",
           "Hold big study-abroad payments for now; a better time comes {pos}.",
           "Applications and moves for study tend to go better in a good month. This is about timing, not visa advice.",
           ("Keep your papers and scores ready early.", "Send the main applications {p}."),
           ("Paying fees in a rush in a careful month.", "Choosing a place only for its name."),
           "Plans to study far away lean on {h}."),
        _T("Learning a new skill",
           "A new skill may come easily {pos}.", "A new skill builds steadily, quicker {pos}.",
           "Start small with a new skill; it picks up {pos}.",
           "A short course or a skill outside class may help more than you expect.",
           ("Pick one skill and finish one course.", "Begin the course {p} and finish it."),
           ("Starting many courses at once.", "Paying for a course you will not finish."),
           "A skill linked to {h} may come easiest."),
    ],
    "home": [
        _T("When is a good time to return to work?",
           "A return to work looks good {pos}.", "A return to work can be eased in, from {pos}.",
           "Take your time; a better moment to return comes {pos}.",
           "A first step can be small: a call, a course or a part-time role.",
           ("Write down the hours you can give each week.", "Make the first call about work {p}."),
           ("Saying yes to more hours than home allows.", "Waiting until every home task is done."),
           "A way back into work may open through {h}."),
        _T("Can a home-run income work for you?",
           "A home-run income looks promising {pos}.", "A home-run income can grow slowly, from {pos}.",
           "Keep a home-run income small at first; it grows more easily {pos}.",
           "Small work from home, like tuition, food orders or tailoring, tends to grow by word of mouth.",
           ("Start with three paying customers you know.", "Take your first paid order {p}."),
           ("Spending on stock before you have orders.", "Working for free for too long."),
           "First orders may come through {h}."),
        _T("Learning a new skill",
           "A new skill may come easily {pos}.", "A new skill builds steadily, quicker {pos}.",
           "Start small with a new skill; it picks up {pos}.",
           "A short course, online or nearby, can open the door to paid work later.",
           ("Pick one skill and finish one course.", "Begin the course {p} and finish it."),
           ("Starting many courses at once.", "Paying for a course you will not finish."),
           "A skill linked to {h} may come easiest."),
        _T("What kind of work suits you most?",
           "Work that rewards {t10} suits you, and it pays off {pos}.",
           "Work that rewards {t10} suits you, with steady gains {pos}.",
           "Work that rewards {t10} still suits you; give it time until {pos}.",
           "Work that uses this, even a few hours a week, tends to bring money and a good name.",
           ("Note three things people already ask you for help with.", "Offer this help to one person {p}."),
           ("Doing work you dislike only for the money.", "Giving your top skill away for free."), ""),
        _T("Fitting work around home",
           "A new routine looks easy to set up {pos}.", "Work and home can balance, more easily {pos}.",
           "The balance may feel tight for a while; it eases {pos}.",
           "Your good months suit trying a routine that leaves room for both.",
           ("Plan the week with the family each Sunday.", "Try the new routine {p} for one month."),
           ("Carrying every task yourself.", "Promising more hours than the week holds."),
           "The balance comes easier when you lean on {h}."),
        _T("Travel for work or family",
           "Trips look useful {pos}.", "Trips are fine at a steady pace, from {pos}.",
           "Trips may cost more for a while; a better time comes {pos}.",
           "Keep each trip clear in its goal and its budget.",
           ("Set one budget for each trip.", "Book the needed trips {p}."),
           ("Extra trips while costs run high.", "Trips planned at the last minute."),
           "Trips pay off when they serve {h}."),
    ],
    "business": [
        _T("Leading your people",
           "People tend to follow your lead, more so {pos}.",
           "Your lead holds steady, and it grows {pos}.",
           "Leading may feel harder for a while; it eases {pos}.",
           "Clear goals and regular team meetings could make your lead stronger.",
           ("Set three clear goals for the business and share them.", "Hold one team meeting a week, starting {p}."),
           ("Reacting fast in a careful time; pause before you reply.", "Fixing every problem yourself."),
           "Your lead carries further through {h}."),
        _T("When to step up",
           "A larger step looks good {pos}.",
           "A steady time to prepare; a larger step fits {pos}.",
           "Hold big new steps for now; your time to step up comes {pos}.",
           "A larger step could be a new line of work, a larger client or a new branch. Until then, prepare quietly.",
           ("Lead the important meetings yourself in your good months.", "Take the larger step {p}, with costs on paper."),
           ("New commitments in a careful time.", "Saying yes to every large client at once."),
           "The larger step may open through {h}."),
        _T("Your name and reputation",
           "Work tends to come to you through your own name, more so {pos}.",
           "Your name holds steady, with a chance to be seen more {pos}.",
           "Guard your name for a while; it is seen more {pos}.",
           "People who trust you may send others your way. A trade fair, a talk, a new shop board or a website suits being seen.",
           ("Ask happy clients for a word of thanks you can share.", "Show your work in public {p}."),
           ("Promising more than the team can deliver.", "Arguing with a client in public."),
           "Word about you spreads through {h}."),
        _T("Delegation",
           "Handing work over looks easy {pos}.", "A steady time to hand over day-to-day tasks, easier {pos}.",
           "Hand over slowly; it gets easier {pos}.",
           "Train one trusted person, so your time goes to growth and to your family.",
           ("Pick one task each month and hand it over fully.", "Hand over one daily task {p}."),
           ("Taking back work you have already handed over.", "Checking every small step of a task you handed over."),
           "Handing work over goes easier through {h}."),
        _T("Work travel",
           "Work trips look useful {pos}.", "Trips for work are fine at a steady pace, from {pos}.",
           "Trips may cost more than planned for a while; better {pos}.",
           "Keep trips short and clear in their goal. A trip that opens a new market or a new partner suits a good month.",
           ("Set a budget for each trip and one goal you want from it.", "Plan the trip to a new market {p}."),
           ("Extra trips while costs run high.", "Trips that only repeat a phone call."),
           "Trips pay off when they serve {h}."),
        _T("A second line of leaders",
           "Building a second line looks good {pos}.", "A steady time to grow a second line, from {pos}.",
           "Start small with a second line; it gets easier {pos}.",
           "Pick one or two people who could lead a shop, a branch or a large client, and let them make small calls now.",
           ("Let one person run a full day without you each month.", "Name your second in charge {p}."),
           ("Stepping in on every small call.", "Keeping all the know-how in your own head."),
           "A second line grows out of {h}."),
    ],
}

BUSINESS = {
    "business": [
        _T("How does your business look from this Diwali to the next?",
           "Things look more settled, and growth shows {pos}.",
           "Business holds steady, with a lift {pos}.",
           "Business asks for care at first, and it opens up {pos}.",
           "Clients tend to trust your name more, and steady work tends to bring repeat orders.",
           ("Pick one growth goal for the months ahead.", "Set one growth goal and check it {p}."),
           ("Chasing every new idea at once.", "Cutting prices just to win one order."),
           "Growth is likely to build on {h}."),
        _T("When is a good time to start or expand?",
           "Expansion fits well {pos}.", "Prepare now; expansion fits {pos}.",
           "Hold expansion for now and plan; it fits better {pos}.",
           "A new branch, a second shop or a new product line fits a good month. Use the slower months to plan and save.",
           ("First check you hold 6 months of running costs in savings.", "Put the expansion plan on paper {p}."),
           ("Expanding on borrowed money in a careful time.", "Opening a second place before the first runs well."),
           "Expansion works through {h}."),
        _T("Partner or alone?",
           "A partner can work well for one clear job, {pos}.",
           "A partner can work for one clear job; talks go well {pos}.",
           "Go slowly with partners for now; talks go better {pos}.",
           "Give a partner one clear job, and keep the business itself under your own name.",
           ("Put roles, money shares and an exit plan on paper.", "Hold partner talks {p}, with roles on paper."),
           ("Hard partner talks in a careful time.", "A partnership on a handshake alone."), ""),
        _T("When do new deals, hiring and new account books fit?",
           "New deals and hiring fit well {pos}.", "Deals move at a steady pace, quicker {pos}.",
           "Sign carefully for now; deals and hiring go better {pos}.",
           "Diwali itself is a good start for new account books at Chopda Pujan. Larger deals and hiring fit your good months.",
           ("Hire for one key role, with a trial month.", "Sign the larger deals {p}."),
           ("Hiring in a hurry in a careful month.", "Signing before you read the whole contract."),
           "New deals often start with {h}."),
        _T("When to go slow on spending and credit?",
           "Spending looks manageable; keep it planned {pos}.", "Spending and credit stay steady; review them {pos}.",
           "Your careful time{cwhy} falls {cpos}, and it eases {pos}.",
           "In a careful month, hold new loans, large stock buys and long credit to customers. Finish current orders and collect dues first.",
           ("Collect dues before you give fresh credit.", "Review every credit line {p}."),
           ("Fast replies to a heated client or supplier; give it a day.", "Long credit to a customer who pays late."),
           "Extra costs tend to come from {h}."),
    ],
    "job": [
        _T("Does your chart lean to business or a job?",
           "Your chart {lean}, and side plans look good {pos}.", "Your chart {lean}, with a steady time to test ideas {pos}.",
           "Your chart {lean}; keep any business test small until {pos}.",
           "You do not have to choose at once; a small test tells you more than a guess.",
           ("Write down one business idea and its first cost.", "Test one small idea {p}."),
           ("Leaving a steady job on a hunch.", "Quitting before the idea has a paying customer."), ""),
        _T("When is a good time to start a side income?",
           "A side income can start well {pos}.", "A side income can start small, from {pos}.",
           "Keep side plans on paper for now; they start better {pos}.",
           "Start with something you already know, a few hours a week, without putting your job at risk.",
           ("Check your job contract allows side work.", "Take the first paid side job {p}."),
           ("Spending your savings on a side plan.", "Letting side work eat into your main job."),
           "A side income may start through {h}."),
        _T("Partner or alone for a side plan?",
           "A partner for one clear job looks good {pos}.", "A partner can help; talks go well {pos}.",
           "Go slowly with partners; talks go better {pos}.",
           "Write down who does what before any money changes hands.",
           ("Put roles and money shares on paper.", "Talk roles through with a partner {p}."),
           ("Mixing friendship and money without a plan.", "Giving a partner control of the money."), ""),
        _T("How small to start, and which months suit it?",
           "A small start fits well {pos}.", "A small, steady start fits {pos}.",
           "Keep the start very small; it grows better {pos}.",
           "Start with a few paying customers and one product or service. Grow only from what you earn.",
           ("Set a firm limit on what you will spend to start.", "Sell to your first three customers {p}."),
           ("Buying stock before the first orders.", "Spending more on the look than on the product."),
           "First customers often come via {h}."),
        _T("Which months to go slow on new spending?",
           "Spending looks manageable; keep it planned {pos}.", "Spending stays steady; review it {pos}.",
           "Your careful time{cwhy} falls {cpos}, and it eases {pos}.",
           "In a careful month, hold large buys and new loans. Keep your job income for the home first.",
           ("Keep a separate account for side money.", "Review side costs {p}."),
           ("New loans for a side plan in a careful month.", "Paying side costs from home money."),
           "Extra costs tend to come from {h}."),
    ],
    "student": [
        _T("Business or a job: where does your chart lean?",
           "Your chart {lean}, and ideas look good {pos}.", "Your chart {lean}, with a steady time to explore {pos}.",
           "Your chart {lean}; explore slowly until {pos}.",
           "Try both in small ways before you decide.",
           ("Spend a day with someone who runs a business.", "Try one small paid task {p}."),
           ("Deciding only from what friends choose.", "Deciding before you have tried either."), ""),
        _T("When could you try a small project?",
           "A small project fits well {pos}.", "A small project fits {pos}.",
           "Keep projects on paper for now; they go better {pos}.",
           "A stall at a college fest, an online page or selling something you make teaches a lot.",
           ("Try one small project with a clear end date.", "Run the first project {p}."),
           ("Spending fee money on a project.", "Letting a project eat into exam time."),
           "A first project may start through {h}."),
        _T("Partner or alone?",
           "Working with a partner looks good {pos}.", "A partner can help; plans go well {pos}.",
           "Go slowly with partners; plans go better {pos}.",
           "Pick a partner who works as hard as you.",
           ("Write down who does what.", "Agree on roles with a partner {p}."),
           ("Sharing money without a plan.", "Doing all the work while sharing the credit."), ""),
        _T("Which months suit learning trade skills?",
           "Learning trade skills fits well {pos}.", "Trade skills build steadily, quicker {pos}.",
           "Start small with trade skills; they pick up {pos}.",
           "Selling, accounts and speaking to customers are skills any work needs.",
           ("Learn basic accounts this season.", "Start a short selling or accounts course {p}."),
           ("Skipping the basics for shortcuts.", "Paying for tips instead of learning the basics."),
           "Trade skills come faster through {h}."),
        _T("Which months to go slow on spending?",
           "Spending looks manageable; keep it planned {pos}.", "Spending stays steady; review it {pos}.",
           "Your careful time{cwhy} falls {cpos}, and it eases {pos}.",
           "Hold large buys and borrowing from friends in a careful month.",
           ("Keep a simple list of what you spend.", "Check your spending list {p}."),
           ("Borrowing from friends for wants.", "Buying on credit for a gadget."),
           "Extra costs tend to come from {h}."),
    ],
    "home": [
        _T("Could a small home venture suit you?",
           "Your chart {lean}, and a small venture looks good {pos}.",
           "Your chart {lean}, with a steady time to try something small {pos}.",
           "Your chart {lean}; keep any venture small until {pos}.",
           "Food orders, tuition, tailoring or reselling can start from home.",
           ("List three things people would pay you for.", "Try one paid offer {p}."),
           ("Buying stock before orders come in.", "Pricing too low to cover your time."), ""),
        _T("When is a good time to start?",
           "Starting looks good {pos}.", "A slow start fits {pos}.",
           "Plan now; a start goes better {pos}.",
           "Begin with people you already know and grow by word of mouth.",
           ("Start with three customers you know.", "Take the first orders {p}."),
           ("Starting many things at once.", "Waiting for everything to be perfect."),
           "First orders often come via {h}."),
        _T("With a partner or alone?",
           "A partner for one clear job looks good {pos}.", "A partner can help; talks go well {pos}.",
           "Go slowly with partners; talks go better {pos}.",
           "A relative or friend can help with one clear job.",
           ("Put who does what on paper.", "Agree on roles with a helper {p}."),
           ("Mixing family money without a plan.", "Sharing profits before costs are paid."), ""),
        _T("The family money picture",
           "Family money looks good {pos}.", "Family money holds steady, with a lift {pos}.",
           "Family money needs care for a while; it eases {pos}.",
           "A clear monthly list of what comes in and goes out helps the whole home plan.",
           ("Keep one book for all home money.", "Sit with the family over the money book {p}."),
           ("Large family spends without a plan.", "Lending from the home fund without telling anyone."),
           "Family money builds up through {h}."),
        _T("Which months to go slow on new spending?",
           "Spending looks manageable; keep it planned {pos}.", "Spending stays steady; review it {pos}.",
           "Your careful time{cwhy} falls {cpos}, and it eases {pos}.",
           "In a careful month, hold large buys and new loans. Collect what others owe first.",
           ("Keep a spending limit for each month.", "Review the home budget {p}."),
           ("Lending money without writing it down.", "Large buys on easy monthly payments."),
           "Extra costs tend to come from {h}."),
    ],
}

FAMILY = [
    _T("The whole family",
       "Home life looks warm and settled, more so {pos}.",
       "Home life holds steady, and it warms {pos}.",
       "Home life asks for patience at first, and it gets warmer {pos}.",
       "A small, regular habit, like one shared meal a week, could keep everyone close.",
       ("Fix one family evening each week; share plans with the people at home early.",
        "Plan one family outing {p}."),
       ("Long work days that leave little time at home.", "Leaving the people at home out of big plans."),
       "Much of the warmth may come through {h}."),
    _T("Family events and celebrations",
       "A good time to host begins {pos}.",
       "Family events go smoothly at a steady pace, from {pos}.",
       "Keep large events simple for now; hosting goes better {pos}.",
       "Pujas, birthdays, a family trip or a get-together with relatives tend to go well in your good months.",
       ("Book halls and travel early; keep a simple guest list.", "Hold the larger get-together {p}."),
       ("Planning a large event while family talks need care.", "Spending more on one event than you planned."),
       "Gatherings tied to {h} go especially well."),
    _T("House move or property",
       "Home and property steps look good {pos}.",
       "Property steps are possible at a steady pace, from {pos}.",
       "Hold property signing for now; it goes better {pos}.",
       "Buying a flat, registering land or doing up the house may go well in your large-buy months. Check the papers and the loan plan first.",
       ("Keep the down payment ready; get papers checked by a lawyer.", "Visit the property {p} and check every paper."),
       ("Signing in a rush while spending runs high.", "Paying a token amount before the papers are clear."),
       "Home steps are tied to {h} for you."),
    _T("Moving city or abroad",
       "A move looks possible and useful {pos}.",
       "A move is possible, but the chart does not push for one; if you go, plan it for {pos}.",
       "Hold a move for now; it fits better {pos}.",
       "Visit first, then decide with your family, and take it in steps.",
       ("List the costs of a move, from rent to trips home, before you decide.", "Make a short visit to the new place {p}."),
       ("Moving while spending runs high in a careful time.", "Moving before the family has talked it through."),
       "Any move would touch {h} most."),
    _T("Which months may bring happy news in your family?",
       "Happy news may come {pos}.",
       "A soft good time for happy news comes {pos}.",
       "Happy news may take a little longer, and it comes more easily {pos}.",
       "Happy news could be a younger family member's milestone, a course that goes well, or a creative plan that takes shape.",
       ("Mark the good time for a learning plan or a family celebration.", "Plan a small family celebration {p}."),
       ("Rushing important family choices.", "Pushing others to decide on your timing."),
       "It may well involve {h}."),
]

MARRIAGE = [
    _T("More warmth in your relationships",
       "Warmth could grow in your closest bonds, starting {pos}.",
       "Your closest bonds hold steady, with warmer months from {pos}.",
       "Close bonds ask for care at first, and they warm up {pos}.",
       "Use the good times for a trip, a quiet dinner, a long call with someone dear, or simply more time at home.",
       ("Plan one outing with someone close in each good time.", "Plan a trip or a quiet dinner {p}."),
       ("Letting work fill every evening.", "Keeping plans to yourself until the last minute."),
       "Closeness grows most through {h}."),
    _T("Important relationship decisions",
       "Large shared choices go well {pos}.",
       "Shared choices can be made at a steady pace, from {pos}.",
       "Hold large shared choices for now; they go better {pos}.",
       "Choices like a home, gold or a family plan tend to go well when you make them with the people they touch. Sit down with numbers on paper.",
       ("List each choice, its cost and its timing, and decide side by side.", "Sit down together over the big choice {p}."),
       ("New signatures in a careful time.", "Deciding alone on something that touches others."),
       "Such choices often touch {h}."),
    _T("Care in close talks",
       "Talks with the people closest to you look easy {pos}.",
       "Talks stay steady; take extra care {pos}.",
       "A careful time for close talks falls {cpos}. It passes, and things get easier {pos}.",
       "Small steps help most: listen to the end and keep hard topics for a quiet moment.",
       ("Listen to the end; wait a day on hard topics; say thank you often.", "Keep the hard talk for a quiet day, {p}."),
       ("Deciding anything important right after a quarrel.", "Going silent for days after a hard word."),
       "Talks about {h} need the gentlest touch."),
    _T("Your partnership traits",
       "", "", "", "", ("Say plainly what you need; give the people close to you room to be themselves.",
                        "Say what you need early; leave room for the other person's view."),
       ("Going quiet when something bothers you.", "Expecting others to guess what you need.")),
    _T("Does your chart show Manglik, and does it matter?",
       "", "", "", "Manglik is an old rule about where Mars sits in your birth chart. {mg_sum} Your plain facts are below.",
       "Share the facts with the family if a match is discussed.", "Paying for any fix; it does not need one."),
]
OPEN_HOUSES = {1, 4, 5, 7, 9, 10}

# house each topic is mostly about (None = topic writes its own chart sentence)
TOPIC_HOUSE = {"money": [2, 11, 12, 6, 8, None, None], "career": [10, 10, 11, 6, 1, 12],
               "business": [11, 10, 7, 11, 12], "family": [4, 4, 4, 12, 5],
               "marriage": [7, 7, 3, None, None]}
PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
WRAP_WORD_SWAP = {"PATIENT": "UNHURRIED", "CALM": "UNHURRIED"}


# ── NARR_KEYS ─────────────────────────────────────────────────────────────────
AI_RULES = (
    "Everyday English for Indian readers. Second person. Soft verbs (may, could, tends to). "
    "No brackets. No month names or years except where the key says dates are allowed. "
    "Never the word 'year' alone; say 'from this Diwali to the next'. Say 'best time', 'good time', "
    "'careful time'; never 'stretch' or 'window'. A house is named in plain words OR by number, never both. "
    "Use 'Karka' for the sign. No health, medical or emotional-clinical words, no guarantees, no "
    "investment tips, no figures. Never assume marital or family status: no 'your wife/husband/spouse/"
    "marriage/children', 'the right person', 'marry again'. Chart reasons go only in 'why' lines. "
    "Use only the facts given; never invent a planet, house, month or state. "
    "Voice: short sentences. Plain everyday words. No jargon: never 'ruler of', 'sits in', 'sub-period', "
    "'Jupiter leading', 'dasha'. No trait lists. Hedge with may or tends to. No emojis. Each topic is one word "
    "(Good, Steady or Careful), what it means with ONE concrete everyday example, Do, Watch, one Why line, When. "
    "Why names ONE planet and ONE part of the chart. Never change a fact, number, month or state. "
    "Style examples. Topic: 'Money looks steadier after Diwali. Your own effort and name tend to count for more now, "
    "so a new client may land more easily. Do: chase two old dues soon after Diwali. Watch: promising money before it "
    "arrives. Why: the planet of growth comes to the part of your chart that stands for you.' "
    "Takeaways: 'The careful times are short and they end.' 'Your planet period supports planning.' "
    "Wrapped: 'Your money grows slowly but surely.'"
)

_TOPIC_BRIEF = {"what": "2 short sentences with one concrete everyday example (a new client, a bulk order, the renovation), matching the topic state",
                "do": "one short action line, no label", "watch": "one short line of what to watch, no label",
                "why": "one planet and one part of the chart, no ruler-of chains, one short sentence",
                "when": "best/good/steady/careful time phrase, no dates"}


def _build_narr_keys():
    keys = []
    A = lambda k, b: keys.append((k, b, "A"))
    for i in range(1, 6):
        A(f"answers.q{i}", f"Front answer {i}: ONE plain line under 20 words matching the given state; no reason, no dates")
    A("wrapped.words", "3 lines 'WORD: line', the Wrapped card words; months allowed")
    A("note.order", "One line on the area order: 'You picked X, so it comes first' only when picked, else by situation")
    A("note.answers_intro", "One line above the 5 answers")
    A("note.less_precise", "One line: chart read from the Moon sign is less precise (empty idea if rising sign used)")
    for a in AREAS + ["luck"]:
        A(f"glance.{a}", f"Diya path line for {AREA_NAME[a]}: state + one plain line, no dates")
    for i in range(1, 5):
        A(f"timeline.{i}", f"Year at a glance segment {i}: theme + one line; dates ALLOWED")
    A("timeline.best", "Single best time line; dates ALLOWED")
    groups = {"money": "B", "career": "B", "business": "B", "family": "C", "marriage": "C"}
    for a in AREAS:
        g = groups[a]
        keys.append((f"{a}.opener", f"{AREA_NAME[a]} position line ('You picked X, so it comes first' only when picked)", g))
        keys.append((f"{a}.headline", f"{AREA_NAME[a]} claim headline, one sentence, no dates", g))
        for n in range(1, TOPIC_COUNTS[a] + 1):
            if (a, n) == ("marriage", 5):
                continue  # Manglik facts box: drawn from payload facts, no AI prose (renderer skips marriage.t5)
            for part, b in _TOPIC_BRIEF.items():
                keys.append((f"{a}.t{n}.{part}", f"{AREA_NAME[a]} topic {n} {part}: {b}", g))
        keys.append((f"{a}.read", f"{AREA_NAME[a]} 'The read': one line to remember", g))
    for k, b in [("family.talks", "Careful time for family talks: what, do, when in 2-3 lines"),
                 ("marriage.helps", "What helps most in close relationships, 1-2 lines"),
                 ("note.helpline", "General line: if a conflict feels serious, talk to someone you trust or a trained helper")]:
        keys.append((k, b, "C"))
    for k, b in [("luck.opener", "Better luck position line"), ("luck.headline", "Better luck headline"),
                 ("luck.turning.1", "First turning point, no dates"), ("luck.turning.2", "Second turning point, no dates"),
                 ("luck.built", "What the months before this Diwali built"),
                 *[(f"luck.bright.{a}", f"Bright spot for {AREA_NAME[a]}, positives only") for a in AREAS],
                 ("luck.blessings.what", "Luck and blessings: 2 sentences"), ("luck.blessings.do", "one action"),
                 ("luck.blessings.why", "one chart reason"), ("luck.blessings.when", "time phrase"),
                 ("luck.habits", "Small fresh-start habits, 2-3 sentences"), ("luck.read", "The read for Better luck")]:
        keys.append((k, b, "C"))
    D = lambda k, b: keys.append((k, b, "D"))
    for part in ("good", "hard"):
        for f in ("what", "do", "watch", "why"):
            D(f"lookback.{part}.{f}", f"Look-back {part} months {f}; never name an event")
    D("lookback.from", "From here: one line on what changes from this Diwali")
    for f in ("headline", "what", "means", "why", "when", "steps"):
        D(f"sadesati.{f}", f"Sade Sati {f}" + (" ('Title: text' x5 lines)" if f == "steps" else ""))
    for i in (1, 2, 3):
        for f in ("title", "what", "do", "why"):
            D(f"strengths.{i}.{f}", f"Strength {i} {f}")
    for r in ("reactions", "spending"):
        for f in ("title", "what", "do", "watch", "why", "when"):
            D(f"slow.{r}.{f}", f"Months to go slow, {r}: {f}; 4-part caution, no dates")
    for ym in MONTH_YMS:
        D(f"months.{ym}.do", "12-month table Do cell: under 8 words")
        D(f"months.{ym}.watch", "12-month table Watch cell: under 8 words")
    for i in range(1, 6):
        D(f"plan.p{i}", f"Top priority {i}: bold first clause + one sentence")
    D("plan.one", "If you do only one thing: one line")
    for k in ("d30", "d90", "d365"):
        D(f"plan.{k}", f"{k[1:]}-day steps: 3 lines")
    for i in (1, 2, 3):
        D(f"plan.fresh.{i}", f"Fresh-start plan {i}: 'If ..., then I will ...'")
    D("plan.fresh.when", "When line for the fresh-start plans")
    D("practices.why", "Why these practices suit this chart, one line")
    for i in range(1, 6):
        D(f"takeaways.{i}", f"Takeaway {i}: one line, never repeating a 'The read' line")
    return keys


NARR_KEYS = _build_narr_keys()



# ── bank ──────────────────────────────────────────────────────────────────────
def _state(x, default="steady"):
    s = (x or {}).get("state") if isinstance(x, dict) else x
    return s if s in ("good", "steady", "careful") else default


def _when_text(when, area_best, no_best=False):
    """The 'when' label: three words at most (the renderer adds the 12-months link)."""
    if no_best and when == "best":
        when = "good"
    if when == "good" and area_best and not no_best:
        return "good, then best"
    return {"best": "your best time", "good": "good time", "careful": "careful, then good",
            "steady": "steady time"}.get(when, "steady time")


def _care_runs(months: list) -> list:
    """Fallback for payloads without `summary`: runs of consecutive careful months (engine rule)."""
    tone = {m.get("ym"): m for m in months or []}
    runs, cur = [], []
    for ym in MONTH_YMS + [None]:
        if ym and (tone.get(ym) or {}).get("tone") == "careful":
            cur.append(ym)
        elif cur:
            rs = [(tone.get(y) or {}).get("care_reason") for y in cur]
            runs.append({"from": cur[0], "to": cur[-1],
                         "reason": "spending" if rs.count("spending") >= rs.count("reactions") else "reactions"})
            cur = []
    return runs


_G6 = re.compile(r"[a-z0-9']+")


def grams6(text: str) -> list[str]:
    w = _G6.findall((text or "").lower())
    return [" ".join(w[i:i + 6]) for i in range(len(w) - 5)]


_DATE_TXT = re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December|"
                       r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b|\b20\d\d\b")


def grams4(text: str) -> list[str]:
    """4-word runs inside one clause (month names, years and the 'your 12 months' link cut a run)."""
    t = _DATE_TXT.sub(" | ", text or "").replace("your 12 months", " | ")
    out = []
    for seg in re.split(r"[|\n.;:!?]", t):
        w = _G6.findall(seg.lower())
        out += [" ".join(w[i:i + 4]) for i in range(len(w) - 3)]
    return out


_SEASON_RE = re.compile("|".join(re.escape(w) for w in sorted({w for ws in SEASON_W.values() for w in ws}, key=len, reverse=True)))
_SEASON_OF = {w: ws for ws in SEASON_W.values() for w in ws}


def _polish_seasons(out: dict, skip) -> None:
    """Where a 4-word run is said more than three times and holds a season word, say that month with its
    other plain wording in a later value (same month, same meaning)."""
    def counts():
        c = {}
        for k, v in out.items():
            if not skip(k):
                for g in grams4(v):
                    c[g] = c.get(g, 0) + 1
        return c
    c = counts()
    for k in list(out):
        if skip(k):
            continue
        for m in list(_SEASON_RE.finditer(out[k])):
            v = out[k]
            if v[m.start():m.end()] != m.group(0):
                continue
            mine = set(grams4(v))
            bad = [g for g in mine if c.get(g, 0) > 3 and any(w in g for w in m.group(0).lower().split())]
            if not bad:
                continue
            for alt in _SEASON_OF[m.group(0)]:
                nv = v[:m.start()] + alt + v[m.end():]
                new = set(grams4(nv))
                if alt != m.group(0) and all(c.get(g, 0) + (g not in mine) <= 3 for g in new - mine):
                    for g in grams4(v):
                        c[g] -= 1
                    for g in grams4(nv):
                        c[g] = c.get(g, 0) + 1
                    out[k] = nv
                    break


_FROM_PREP = re.compile(r"\bfrom (?:in|by|at) ")
_FROM_AS = re.compile(r"\bfrom as ")


def _fix_from(v: str) -> str:
    """A season phrase after 'from' never doubles the preposition: 'from in early spring' -> 'from early spring',
    'from as spring begins' -> 'from when spring begins'."""
    return _FROM_AS.sub("from when ", _FROM_PREP.sub("from ", v))


def _fix_after_diwali(v: str) -> str:
    """'after this Diwali' at most once per sentence."""
    def one(sent):
        n = [0]

        def sub(m):
            n[0] += 1
            if n[0] == 1:
                return m.group(0)
            return "soon after" if m.group(1) else "after that"
        return re.sub(r"(right )?after this Diwali", sub, sent)
    return "\n".join(" ".join(one(s) for s in re.split(r"(?<=[.!?])\s+", line)) for line in v.split("\n"))


_TRANSIT_W = re.compile(r"\b(passes|moves through|turns back|moves backward|moves into|moves in|enters|looks at|comes to|travels through)\b")
# area claim headlines: (has a best time inside, no best time) for a good area; one wording otherwise
HEADLINE = {
    "money": {"good": ("Money builds and shines brightest {pos}", "Money builds and firms up {pos}"),
              "steady": "Money holds steady, with {n} good months to use well",
              "careful": "Money asks for care first, then firms up {pos}"},
    "career": {"good": ("Your work and name grow, and shine brightest {pos}", "Your work and name grow, with a lift {pos}"),
               "steady": "Work moves at a steady pace, with {n} good months for a push",
               "careful": "Work asks for patience first, then opens up {pos}"},
    "business": {"good": ("Business looks good, and growth peaks {pos}", "Business looks good, and growth shows {pos}"),
                 "steady": "Business stays steady, with {n} good months for growth",
                 "careful": "Business asks for care with spending first, then grows {pos}"},
    "family": {"good": ("Home and family hold a strong place, and home life is warmest {pos}",
                        "Home and family hold a strong place, and home life warms {pos}"),
               "steady": "Home life stays steady, with {n} warmer months",
               "careful": "Home asks for a gentle hand first, then warms up {pos}"},
    "marriage": {"good": ("Close bonds grow warmer, and are warmest {pos}", "Close bonds grow warmer, starting {pos}"),
                 "steady": "Close bonds stay steady, with {n} warmer months",
                 "careful": "Close bonds ask for care first, then warm up {pos}"}}
HEAD_TAIL = ["over {} good month{}", "{} good month{} in all", "with {} month{} marked good", "through {} good month{}",
             "across {} good month{}"]
# "The read": (with a careful time in the area, without one)
READ = {
    "money": {"good": ("save through the careful months and make large moves {pos}.", "keep the saving habit and make large moves {pos}."),
              "steady": ("keep the saving habit and use the good months, from {pos}.",) * 2,
              "careful": ("make a plan first, hold large buys, and move {pos}.",) * 2},
    "career": {"good": ("build your record and step up {pos}.",) * 2,
               "steady": ("build quietly, and step up {pos}.",) * 2,
               "careful": ("prepare first, and make your move {pos}.",) * 2},
    "business": {"good": ("open the new books at Diwali, keep costs tight while spending needs care, and expand {pos}.",
                          "open the new books at Diwali, keep costs tight, and expand {pos}."),
                 "steady": ("keep the business steady and grow {pos}.",) * 2,
                 "careful": ("hold back on spending, collect dues, and grow {pos}.",) * 2},
    "family": {"good": ("host, plan the home {pos}, and go gently when family talks need care.", "host, and plan the home {pos}."),
               "steady": ("make home plans {pos}, and keep talking.",) * 2,
               "careful": ("go gently at home for now; warmer months come {pos}.",) * 2},
    "marriage": {"good": ("make time for the people close to you {pos}, and go gently when close bonds need care.",
                          "make time for the people close to you {pos}."),
                 "steady": ("keep talking, and plan time together {pos}.",) * 2,
                 "careful": ("go gently in close talks; bonds grow warmer {pos}.",) * 2}}
# a topic text that speaks of a careful time, said plainly for a buyer with no careful month at all
NO_CARE = [("In a careful month, hold", "When money is tight, hold"),
           ("Hold large buys and borrowing from friends in a careful month.",
            "Hold large buys and borrowing from friends when money is tight."),
           (" even while new signing needs care", " before any new signing"),
           ("Plan the larger events for your good times, not your careful time.", "")]


def bank(payload: dict) -> dict:
    p = payload or {}
    meta = p.get("meta") or {}
    ch = _Chart(p)
    work = meta.get("work_type") if meta.get("work_type") in WORK_AS else "job"
    steer = meta.get("steering")
    band = meta.get("age_band") if meta.get("age_band") in EX else "25_40"
    female = meta.get("gender") == "female"
    first = meta.get("first_name") or (meta.get("name") or "").split(" ")[0] or "friend"
    areas_d = p.get("areas") or {}
    order = [a for a in (p.get("area_order") or []) if a in AREAS] or SITUATION_ORDER[work]
    lead_area = "luck" if steer == "luck" else order[0]
    period = p.get("period") or {}
    md, ad = period.get("md") or "", period.get("ad") or ""
    out: dict[str, str] = {}
    mlist = p.get("months") or []
    mon_by = {m.get("ym"): m for m in mlist}
    all_good = [m.get("ym") for m in mlist if m.get("tone") in ("good", "best")]

    # THE overall best / careful times come from payload.summary (engine), never recomputed here
    summ = p.get("summary") or {}
    no_best = not has_best(p)
    bt = dict(summ.get("best") or p.get("best_time") or {})
    if not (bt.get("from") and bt.get("to")):
        bt = {}
    s_care = summ["careful"] if isinstance(summ.get("careful"), list) else _care_runs(mlist)
    bw = "best time" if not no_best else "main good time"   # never "strongest good time": that names a best time too
    wr = p.get("wrapped") or {}
    sa = wr.get("strongest_area") if wr.get("strongest_area") in AREAS else order[0]
    wl = wr.get("lead_area") if wr.get("lead_area") in AREAS else order[0]

    chart = p.get("chart") or {}
    moon_sign = (chart.get("moon") or {}).get("sign") or ch.pl("Moon").get("sign") or ""
    nad = period.get("next_ad") or {}
    care_all = sorted({m for c in s_care for m in MONTH_YMS if (c.get("from") or "") <= m <= (c.get("to") or "")})
    n_care = len(care_all)
    sp_m = [m.get("ym") for m in mlist if m.get("care_reason") == "spending"]
    rx_m = [m.get("ym") for m in mlist if m.get("care_reason") == "reactions"]
    gold = list((p.get("money_extra") or {}).get("gold_months") or [])
    gold_ok = [g for g in gold if (mon_by.get(g) or {}).get("tone") != "careful"]
    loans = list((p.get("money_extra") or {}).get("loan_months") or [])
    n_good = NUM.get(len(all_good), str(len(all_good)))

    def cnt(n, word):
        return f"{NUM.get(n, str(n))} {word}{'s' * (n != 1)}"

    def yh(h):
        return HOUSE[h] if h in (1, 5) else "your " + HOUSE[h][4:]  # never "your children ..." (status rule)

    # One report never says a sentence twice, nor any 4-word run more than three times (spec §9). Every
    # value is registered as it is written; where several TRUE sentences could be said (which chart fact
    # gives a reason, which of two plain season words), the bank picks one that keeps to that rule.
    g4: dict[str, int] = {}
    said: set[str] = set()

    def _sents(t):
        return [s.strip().lower() for s in re.split(r"(?<=[.!?])\s+|\n", t or "") if len(s.split()) >= 5]

    g6: dict[str, int] = {}

    def cost(t):
        """How many times t would break the no-repeat rules: a 4-word run a 4th time, a 6-word run a 3rd time,
        a whole sentence a 2nd time."""
        return (sum(g4.get(g, 0) >= 3 for g in grams4(t)) + sum(g6.get(g, 0) >= 2 for g in grams6(t))
                + 9 * sum(s in said for s in _sents(t)))

    def fits(t):
        return cost(t) == 0

    def first_fit(*options):
        """The first wording that keeps the report fresh; else the last (the plainest) one."""
        return next((o for o in options if o and fits(o)), options[-1] if options else "")

    def opt(base, *tails):
        """base + the first optional tail that keeps the sentence fresh; else base alone (say less, not the same)."""
        for tl_ in tails:
            if fits(base + tl_):
                return base + tl_
        return base + "."

    def put(k, t):
        out[k] = t
        if not k.startswith(("months.", "gift.")) and k != "wrapped.lead":
            for g in grams4(t):
                g4[g] = g4.get(g, 0) + 1
            for g in grams6(t):
                g6[g] = g6.get(g, 0) + 1
            said.update(_sents(t))
        return t

    s_use: dict[str, int] = {}

    def pos(yms, make=None):
        """When a set of months starts, in season words (two plain wordings per month, used in turn).
        make(words) -> the sentence they go in: then the wording that keeps that sentence fresh is taken,
        and the sentence is returned."""
        yms = sorted(y for y in (yms or []) if y in MONTH_YMS)
        opts = sorted(SEASON_W[_idx(yms[0])], key=lambda o: (s_use.get(o, 0), SEASON_W[_idx(yms[0])].index(o))) if yms \
            else ["later on"]
        o = next((o for o in opts if fits(make(o))), opts[0]) if make else opts[0]
        s_use[o] = s_use.get(o, 0) + 1
        return make(o) if make else o

    def span(yms, make=None):
        """Where a run of months falls, in season words (make: as in pos). Months that are not one run are said
        as the first run 'and again' the next one."""
        yms = sorted(set(y for y in (yms or []) if y in MONTH_YMS))
        runs_ = []
        for y in yms:
            if runs_ and _idx(y) == _idx(runs_[-1][-1]) + 1:
                runs_[-1].append(y)
            else:
                runs_.append([y])
        if len(runs_) > 1:
            first_, second_ = span(runs_[0]), pos(runs_[1])
            opts = [f"{first_} {c} {second_}" for c in ("and again", "then once more", "and later")]
            o = next((o for o in opts if fits(make(o) if make else o)), opts[0])
            return make(o) if make else o
        a_, b_ = (_idx(yms[0]), _idx(yms[-1])) if yms else (0, 0)
        sa_, sb_ = SEASON_NAME[a_], SEASON_NAME[b_]
        if len(yms) < 2 or (sa_ == sb_ and b_ - a_ < 2):
            return pos(yms, make)
        _a = "Diwali" if a_ == 0 else sa_
        _mid = len({SEASON_NAME[i] for i in range(a_, b_ + 1)}) > 2   # a middle season lies between the two
        opts = ([f"through {sa_}", f"across {sa_}"] if sa_ == sb_ else
                [f"from {_a} into {sb_}", f"from {_a} right into {sb_}", f"from {_a} on into {sb_}"] if _mid else
                [f"from {_a} into {sb_}", f"across {'the festive weeks' if a_ == 0 else sa_} and {sb_}",
                 f"between {_a} and {sb_}", f"over {'the festive weeks' if a_ == 0 else sa_} and {sb_}",
                 f"through the {'festive' if a_ == 0 else sa_} and {sb_} months"])
        opts = sorted(opts, key=lambda o: s_use.get(o, 0))   # least used first: two spans in one value differ
        o = next((o for o in opts if fits(make(o))), opts[0]) if make else next((o for o in opts if fits(o)), opts[0])
        s_use[o] = s_use.get(o, 0) + 1
        return make(o) if make else o

    def win(a, k):
        return list(((areas_d.get(a) or {}).get("windows") or {}).get(k) or [])

    def run_end(a):
        """How far the area's good months run, in plain wordings (the caller keeps the one that stays fresh)."""
        g_ = sorted(set(win(a, "good") + win(a, "best")))
        if len(g_) < 2:
            return []
        if _idx(g_[-1]) == 11:
            return ["its good months run all the way to next Diwali", "good months last till next Diwali",
                    "it stays good right up to next Diwali"]
        s_ = SEASON_NAME[_idx(g_[-1])]
        return [f"its good months run into {s_}", f"good months last into {s_}", f"it stays good into {s_}"]

    def peak(a, after=""):
        """The area's own high point, in all its plain wordings (the caller keeps the one that stays fresh):
        its best months, else how far its good months run; none when that would only repeat 'after'."""
        b_ = win(a, "best")
        if b_ and not no_best:
            ws = SEASON_W[_idx(min(b_))]
            return [] if after in ws else [f"{v} {w}" for v in ("it is brightest", "it shines most", "its high point comes") for w in ws]
        g_ = sorted(set(win(a, "good")))
        if len(g_) < 2:
            return []
        if _idx(g_[-1]) == 11:
            return ["it stays good right up to next Diwali", "its good months run all the way to next Diwali",
                    "good months last till next Diwali"]
        s_ = SEASON_NAME[_idx(g_[-1])]
        return [f"its good months run into {s_}", f"it stays good into {s_}", f"good months last into {s_}"]

    def topic(a, n):
        for t in (areas_d.get(a) or {}).get("topics") or []:
            if t.get("key") == f"{a}.t{n}":
                return t
        return {}

    def lord_house(h):
        return ch.pl(ch.lord(h)).get("house")

    def named(t):
        return {P for P in PLANETS if re.search(rf"\b{P}\b", t or "")}

    def clean_why(s):
        s = _sent(s)
        return s if s and not lint_text(s) else ""

    # a chart fact is said once per report, in one wording: two sentences about the same planets in the same
    # parts, of the same kind (a transit, or a birth-chart placement), are one fact
    class _Used(set):
        """Facts said so far. A ruler sitting in its own part is one fact, however it is worded."""
        def add(self, k):
            super().add(k)
            if isinstance(k, tuple) and len(k) == 3 and k[0] in ("O", "R") and k[2] in HOUSE and ch.lord(k[2]) == k[1]:
                super().update({("O", k[1], k[2]), ("R", k[1], k[2])})

    used_facts: set = _Used()

    _HN = r"(the [a-z -]+? part|the part for yourself)"

    def fkey(t):
        """A fact's identity, read from a sentence: (kind, planet, part) when the sentence is one plain fact,
        so the engine's wording and the bank's wording of the same fact are one fact."""
        pl, hs = named(t), _houses_in(t)
        hn = {v: k for k, v in HOUSE.items()}
        m = re.search(rf"\b({'|'.join(PLANETS)}),? (?:ruler of|rules) {_HN}", t) or \
            re.search(rf"{_HN}(?: is in [A-Z][a-z]+,)?(?: is)? ruled by (?:the )?({'|'.join(PLANETS)})\b", t, re.I)
        if m:
            p_, h_ = (m.group(1), m.group(2)) if m.group(1) in PLANETS else (m.group(2), m.group(1))
            h_ = h_[:1].lower() + h_[1:]
            if h_ in hn:   # a ruler sitting in its own part is the planet-in-part fact
                own = "right there" in t or "sits in it" in t or t.count(h_) > 1
                return ("O" if own else "R", p_, hn[h_])
        if len(pl) == 1 and len(hs) == 1:
            kind = "A" if re.search(r"\blooks? at\b|'s look\b", t) else "T" if _TRANSIT_W.search(t) else "O"
            return (kind, next(iter(pl)), hs[0])
        return (bool(_TRANSIT_W.search(t)), frozenset(pl), frozenset(hs),
                frozenset(s for s in SIGNS if re.search(rf"\b{s}\b", t)))

    taken_to = [None]   # the part of life the last fact taken points to

    def as_fact(c):
        if isinstance(c, _Fact):
            return c
        g = _Fact(c if isinstance(c, tuple) else (c,), None, None)
        g.key = fkey(g[-1])
        hs = _houses_in(g[0])
        g.to = hs[-1] if hs else None
        return g

    def take(*cands):
        """The first fact not yet said in this report, in the first of its wordings that keeps to the
        no-repeat rule. A candidate is a _Fact, a sentence, or a tuple of ways to say one sentence's fact."""
        groups = [as_fact(c) for c in cands if c]
        for g in groups:
            if g.key in used_facts:
                continue
            for c in g:
                if fits(c):
                    used_facts.add(g.key)
                    taken_to[0] = g.to
                    return c
        # nothing fits fully: the unused fact and wording that repeats least, in the order given
        fresh = [(cost(c), n, c, g) for n, g in enumerate(groups) if g.key not in used_facts for c in g]
        if fresh:
            _, _, c, g = min(fresh, key=lambda x: x[:2])
            used_facts.add(g.key)
            taken_to[0] = g.to
            return c
        taken_to[0] = groups[0].to if groups else None
        return groups[0][0] if groups else ""

    ex = dict(EX[band])
    ex["income"] = "steady income" if band == "60p" else INCOME[work]
    if work == "student":
        ex["save"] = "a small monthly saving, even from pocket money"
    fill = dict(ex, t10=ch.trait(10),
                src=SOURCE_BY_HOUSE.get(ch.pl(ch.lord(2)).get("house"), "steady, regular work"))
    _mg = ((p.get("marriage_extra") or {}).get("manglik") or {})
    _yes = sum(1 for r in ("lagna_rule", "moon_rule") if _mg.get(r) and not (r == "lagna_rule" and meta.get("basis") == "moon"))
    fill["mg_sum"] = f"Your Mars is placed in {ch.pl('Mars').get('sign') or 'its sign'}. " + ("By neither rule does it apply to you." if not _yes else
                      ("By one of the two rules it applies" if _yes == 1 else "By both rules it applies") +
                      (", and a classic exception cancels it." if _mg.get("cancelled") else ", with no classic exception."))
    # business or job: the engine's Job-Business dial (same facts as business topic 1), never recomputed here
    _dial = next((d for d in (areas_d.get("business") or {}).get("dials") or [] if d.get("left") == "Job"), {})
    _v = _dial.get("value")
    _bw1 = next((t.get("why") or "" for t in (areas_d.get("business") or {}).get("topics") or []
                 if t.get("key") == "business.t1"), "")
    if isinstance(_v, (int, float)):
        _lean = "business" if _v > 0.5 else "job" if _v < 0.5 else ""
    else:
        _lean = "business" if "leans to business" in _bw1 else "job" if "leans to a job" in _bw1 else ""
    fill["lean"] = {"business": "leans to business", "job": "leans to a job and leaves room for a side plan"}.get(
        _lean, "sits between a job and business")

    def care_reason(ym):
        r_ = (mon_by.get(ym) or {}).get("care_reason")
        return r_ or next((c.get("reason") for c in s_care if (c.get("from") or "") <= ym <= (c.get("to") or "")), "")

    def no_care(t):
        """Plain words for a buyer with no careful month at all: never speak of a careful time."""
        if n_care:
            return t
        for a_, b_ in NO_CARE:
            t = t.replace(a_, b_)
        return re.sub(r"\s+", " ", t).strip()

    def pick(v, side):
        """One wording of a Do / Watch pair: the open or the quiet one (see the tables), the other one when
        the first was said too often already; a buyer with no careful month never reads one."""
        if isinstance(v, str):
            return v
        if not n_care and "careful" in v[side] and "careful" not in v[1 - side]:
            return v[1 - side]
        if not fits(v[side]) and fits(v[1 - side]) and (n_care or "careful" not in v[1 - side]):
            return v[1 - side]
        return v[side]

    # the Manglik box's reason is where Mars sits: kept for it, so no other line says that fact first
    _mars = ch.pl("Mars")
    m5_fact = _Fact((f"Mars sits in {HOUSE.get(_mars.get('house'), 'your chart')}, in {_mars.get('sign') or 'its sign'}.",
                     f"Mars is in {_mars.get('sign') or 'its sign'}, in {HOUSE.get(_mars.get('house'), 'your chart')}.",
                     f"{_cap(HOUSE.get(_mars.get('house'), 'your chart'))} holds Mars, in {_mars.get('sign') or 'its sign'}.",
                     f"Your chart has Mars in {_mars.get('sign') or 'its sign'}."),
                    ("O", "Mars", _mars.get("house")), _mars.get("house"))
    # the 3 strengths keep their own planet's place as their reason, so no topic takes it first
    strs = (p.get("strengths") or [])[:3]
    str_why = []
    for i in range(3):
        s = strs[i] if i < len(strs) else {}
        nm = s.get("planet") or ["Jupiter", "Saturn", "Venus"][i]
        h = s.get("house") or ch.pl(nm).get("house")
        _sg, _dg = s.get("sign") or ch.pl(nm).get("sign") or "its sign", _dig(s.get("dignity") or ch.pl(nm).get("dignity"))
        # the strength is the planet's dignity in its sign; its part of life is said in the strength's own text
        _hp = HOUSE.get(h)
        _nks = ch.pl(nm).get("nakshatra") or ""
        _nks = f", in the {_nks} star" if len(_nks) > 2 and not lint_text(_nks) else ""
        g = tuple(x for x in ((_cap(f"{_pn(nm)} is in {_sg}{_dg or ', where it does well'}{_nks}, in {_hp}.") if _hp and _nks else ""),
                              (_cap(f"{_pn(nm)} is in {_sg}{_dg or ', where it does well'}, in {_hp}.") if _hp else ""),
                              (_cap(f"{_pn(nm)} sits in {_hp}, in {_sg}{_dg or ', where it does well'}.") if _hp else ""),
                              _cap(f"{_pn(nm)} is in {_sg}{_dg or ', where it does well'}.")) if x)
        str_why.append(g)
        used_facts.add(fkey(g[0]))
    m5_own = m5_fact.key not in used_facts   # a Mars strength already says where Mars sits
    used_facts.add(m5_fact.key)

    all_natal = list(dict.fromkeys(ch.natal_facts(list(range(1, 13)))))
    moon = (chart.get("moon") or {}).get("sign", "")
    # ── Better luck ──────────────────────────────────────────────────────────
    out["luck.opener"] = ("You picked Better luck, so it comes first." if steer == "luck"
                          else "Better luck comes right after your five areas, for everyone.")
    j0 = ch.transit(MONTH_YMS[0], "Jupiter").get("house")
    moves = []   # (ym, planet, house) when Jupiter or Saturn changes part
    prev = {}
    for ym in MONTH_YMS:
        for pl in ("Jupiter", "Saturn"):
            h = ch.transit(ym, pl).get("house")
            if h and prev.get(pl) and h != prev[pl]:
                moves.append((ym, pl, h))
            if h:
                prev[pl] = h
    la = lead_area if lead_area != "luck" else order[0]
    la_good = sorted(set(win(la, "best") + win(la, "good")))
    _t1p = pos(all_good[:1])
    _t1 = [opt(f"First turning point. Jupiter, the planet of growth, comes to {w_}. "
               f"Effort around {LIFE.get(j0, 'that part of life')} tends to count for more {_t1p}",
               ".")
           for w_ in (yh(j0), f"a new part of your chart, the one for {LIFE.get(j0, 'daily life')}")] if j0 else []
    put("luck.turning.1", min(_t1, key=cost) if j0 else
        f"First turning point. This Diwali opens a fresh run of months, and the first good one comes {pos(all_good[:1])}.")
    sat_mv = next((x for x in moves if x[1] == "Saturn"), None)
    jup_mv = next((x for x in moves if x[1] == "Jupiter"), None)
    if sat_mv or jup_mv:
        ym_, pl_, h_ = sat_mv or jup_mv
        _p2 = _cap(pos([ym_]))
        t2 = min(((f"Second turning point. {_p2}, Saturn moves into {w_}, and a new kind of steady work begins there."
                   if pl_ == "Saturn" else
                   f"Second turning point. {_p2}, Jupiter moves on to {w_}, which opens fresh room there.")
                  for w_ in (yh(h_), f"the part of your chart for {LIFE.get(h_, 'daily life')}")), key=cost)
    elif nad.get("lord"):
        t2 = f"Second turning point. Your sub-period moves from {ad or 'its planet'} to {nad['lord']}, which changes the pace."
    else:
        t2 = f"Second turning point. Your {ad or 'current'} sub-period settles in, and plans made now tend to hold."
    _after_mv = [m for m in all_good if (sat_mv or jup_mv) and m >= (sat_mv or jup_mv)[0]]
    put("luck.turning.2", t2[:-1] + (f"; {cnt(len(_after_mv), 'good month')} follow." if _after_mv and (sat_mv or jup_mv) else "."))
    lb = p.get("lookback") or {}
    hard, lgood = lb.get("hard") or [], lb.get("good") or []
    put("luck.built", (f"{_cap(NUM.get(len(hard), str(len(hard))))} of the months before this Diwali asked for patience. "
                       "That slower work was groundwork for the months ahead" + (f", with {ad} now leading your sub-period." if ad else ".")) if hard else
        "The months before this Diwali built a steady base for the months ahead" + (f", with {ad} now leading your sub-period." if ad else "."))
    BRIGHT = {"money": ("money may build slowly but surely", "money holds steady through the months",
                        "money firms up after a careful start"),
              "career": ("your role may rise", "your work moves at an even pace",
                         "your work opens up after a patient start"),
              "business": ("growth shows, step by step", "the business keeps an even keel",
                           "the business grows once spending is in hand"),
              "family": ("a warm, settled home and good times for family events", "home life stays even and close",
                         "home warms up after a gentle start"),
              "marriage": ("good times for warmth with the people closest to you", "close bonds stay steady",
                           "close bonds warm up after a careful time")}
    for a in AREAS:   # one list line (renderer adds the bold label); follows the area's state and its own months
        st_ = _state(areas_d.get(a))
        aft_ = [m for m in win(a, "good") + win(a, "best") if m > min(win(a, "careful") or [""])] if st_ == "careful" else []
        _nb = len(set(win(a, "best") + win(a, "good")))
        _st0 = pos(aft_ or win(a, 'best') or win(a, 'good'))
        _b0 = f"{BRIGHT[a][('good', 'steady', 'careful').index(st_)]}, {_st0}"
        put(f"luck.bright.{a}", opt(_b0, *[f"; {w}." for w in ((peak(a, _st0) or run_end(a)) if not aft_ else run_end(a))],
                                    "."))
    nin = (p.get("luck") or {}).get("ninth") or {"sign": ch.sign(9), "lord": ch.lord(9)}
    out["luck.headline"] = "Good things line up after this Diwali."
    _b9 = ch.pl(ch.lord(9)).get("house")   # where the ruler of the luck part sits: where help tends to come from
    put("luck.blessings.what", f"Support from elders, teachers and long-time contacts may come more easily {pos(la_good[:1])}"
                               + (f", often through {HELP_P[_b9]}" if _b9 in HELP_P and _b9 != 9 else "")
                               + f". A thank-you visit to an old mentor fits well {pos(la_good[-1:])}"
                               + (f", the last good month for {AREA_PHRASE[la]}." if len(la_good) > 1 else "."))
    put("luck.blessings.do", f"Ask one elder for advice {pos(all_good[:1])}, before an important move.")
    _l9h = ch.pl(nin.get("lord")).get("house")
    put("luck.blessings.why", take(*(ch.natal_facts([9]) + ([f"{_cap(_pn(nin['lord']))}, ruler of the luck part, sits in {HOUSE[_l9h]}."]
                                                             if nin.get("lord") and _l9h in HOUSE else []) + all_natal)))
    out["luck.blessings.when"] = "good time"
    # one habit for the planet that runs this buyer's main period
    HABIT = {"Sun": "Make one small decision each day without waiting to be asked.",
             "Moon": "Call one family member every Sunday.", "Mars": "Do the hardest task of the day first.",
             "Mercury": "Check your accounts every Friday.", "Jupiter": "Give twenty minutes a day to learning something.",
             "Venus": "Keep your home and desk neat and bright.", "Saturn": "Keep one fixed hour a week for pending work.",
             "Rahu": "Try one new idea a month, small and on paper.", "Ketu": "Keep one quiet hour a week with no phone."}
    _h1 = {"business": "On the 1st of each month, write down last month's earnings and spends.",
           "job": "On the 1st of each month, note what came in and what went out.",
           "student": "On the 1st of each month, note what you spent.",
           "home": "On the 1st of each month, write down the home's money in and out."}[work]
    _h2 = [HABIT.get(md, "Make one thank-you call a week.")] + ([HABIT[ad]] if ad in HABIT and ad != md else [])
    put("luck.habits", " ".join([_h1] + _h2))
    _bp = pos([bt["from"]] if bt.get("from") else la_good)
    put("luck.read", (first_fit(f"Plan in your {cnt(n_care, 'careful month')}, act in the {bw}, {_bp}.",
                                f"Plan in your {cnt(n_care, 'careful month')}, and act {_bp}.",
                                f"Plan in the slower months, {NUM.get(n_care, str(n_care))} in all, and act {_bp}.") if n_care
                      else first_fit(f"Keep a steady plan, and act in the {bw}, {_bp}.", f"Keep a steady plan, and act {_bp}.")))

    # ── Part 1 extras: look-back, Sade Sati, strengths, slow months ─────────
    put("lookback.good.what", (f"In the {cnt(len(lgood), 'good month')} before this Diwali, " if lgood else
                               "In the better months before this Diwali, ") +
        "income and help tended to come more easily. If a plan moved forward then, "
        + (f"your {md} main period was helping your effort along." if md else "your chart was helping your effort along."))
    put("lookback.good.do", "Note what worked in those months; you can use it again.")
    put("lookback.good.watch", "Expecting every month to feel like that.")
    _ru = " and ".join(HOUSE[h] for h in ch.houses if ch.lord(h) == md)
    _lg = _sent(f"{md or 'Your main period planet'}, your main period planet, rules {_ru}" if _ru else
                f"{md or 'Your main period planet'}, your main period planet, sits in {HOUSE.get(ch.pl(md).get('house'), 'your chart')}")
    _lgs = _sent(f"{md}, your main period planet, is in {ch.pl(md).get('sign')}") if md and ch.pl(md).get("sign") else ""
    put("lookback.good.why", take(_Fact((_lg, _lgs) if _lgs else (_lg,), fkey(_lg), None)) or _lg)
    used_facts.update(("R", md, h) for h in ch.houses if ch.lord(h) == md)   # every part it rules is said there
    put("lookback.hard.what", (f"In the {cnt(len(hard), 'slower month')}, plans may have kept changing, or answers came slowly. "
                               "That was about timing" + (f" in your {md}–{ad} period" if md and ad and md != ad else "") + ", not about you.") if hard else
        "Few months before this Diwali stand out as hard. Steady effort carried you through" + (f" the {md} period." if md else "."))
    put("lookback.hard.do", "Let go of what stayed slow.")
    out["lookback.hard.watch"] = "Judging yourself by those months."
    put("lookback.hard.why", (f"Your sub-period moved to {ad} inside the {md} period, which changes the pace." if ad and md
                              else f"Your sub-period moved to {ad}, which changes the pace." if ad
                              else "A planet sub-period changed, which changes the pace."))
    put("lookback.from", f"From this Diwali, things may get better step by step: your first good month comes {pos(all_good[:1])}"
                         + (first_fit(f", and your {bw} {pos([bt['from']])}.", f", and the main ones {pos([bt['from']])}.")
                            if bt.get("from") and all_good[:1] != [bt["from"]] else
                            f", and the first careful one {pos(care_all)}." if care_all else "."))

    ss = p.get("sade_sati") or {}
    phase = ss.get("phase")
    phase_word = {"rising": "first", "peak": "middle", "setting": "last"}.get(phase, "")
    sat_now = ch.transit(MONTH_YMS[0], "Saturn")
    sat_h = sat_now.get("house")
    rel = ""
    if sat_now.get("sign") in SIGNS and moon in SIGNS:
        d = (SIGNS.index(sat_now["sign"]) - SIGNS.index(moon)) % 12 + 1
        rel = {12: "the sign just before your Moon sign", 1: "your Moon sign", 2: "the sign just after your Moon sign"}.get(d, f"the {ORD.get(d, _ordn(d))} sign from your Moon sign")
    mh = [ch.pl("Moon").get("house") or 4]
    _nk = (chart.get("moon") or {}).get("nakshatra") or ""
    _mw = (moon or "your Moon sign") + (f", in the {_nk} star" if len(_nk) > 2 and not lint_text(_nk) else "")
    rx_life = LIFE.get(ch.transit(rx_m[0], "Mars").get("house"), "day-to-day talks") if rx_m else ""
    mars_life = LIFE.get(ch.pl("Mars").get("house"), "work talks")
    sat_life = LIFE.get(sat_h, "your daily work")
    _b12 = ch.pl(ch.lord(12)).get("house")   # where the ruler of the spending part sits: where costs tend to go
    if ss.get("active"):
        put("sadesati.headline", f"Saturn's long phase over {moon or 'your Moon sign'} is in its {phase_word or 'current'} part, and it asks for order around {sat_life}, not fear.")
        put("sadesati.what", f"Sade Sati is the time Saturn takes to walk past your Moon sign, {_mw}: a long phase in three parts, and yours is in its "
                             f"{phase_word or 'current'} part. It is a time for order and kept promises, not for fear.")
        put("sadesati.means", {"rising": "New costs or duties may appear. Plan them early and keep promises small and firm.",
                               "peak": "Work may ask for more effort for less applause. Steady routines carry you through.",
                               "setting": "Money keeps coming in, but family costs, home bills and money lent to others need a clear plan."}.get(
            phase, "Keep promises, plan costs early and lean on routine.") + f" Its slow work falls mostly on {sat_life}.")
        put("sadesati.why", f"Saturn is in {sat_now.get('sign') or 'its sign'}, {rel or 'a sign near your Moon sign'}"
                            + ".")
        out["sadesati.when"] = "steady time; any pause in the phase is a good time to save ahead"
        steps = ["Write a family budget: list home bills, family costs and money given as help in one book"
                 + (f", and keep to it most closely in your {cnt(len(sp_m), 'month')} of careful spending." if sp_m else
                    f", with a line for costs around {HELP[_b12]}." if _b12 in HELP else "."),
                 "Clear small dues first: pay off small amounts owed before taking on new ones"
                 + (f", ideally {pos(loans)}." if loans else f", one each month from {pos(all_good[:1])}."),
                 first_fit(f"Keep every promised date: pay staff and helpers on time, above all around {sat_life}; Saturn rewards kept promises.",
                           "Keep every promised date: pay staff and helpers on time; Saturn rewards kept promises."),
                 "Lend only on paper: for any large loan to family or friends, write the terms down"
                 + (f", above all in your {cnt(len(rx_m), 'month')} of quick reactions, {span(rx_m)}." if rx_m else f", and settle old ones {pos(loans or all_good[-1:])}."),
                 f"Save ahead in good months: put a little aside in every good month, for the slower ones, {span(care_all) if care_all else 'all through'}."]
    else:
        put("sadesati.headline", f"Saturn's long phase over {moon or 'your Moon sign'} is not running for you, so there is room to build, above all in {sat_life}.")
        put("sadesati.what", f"Sade Sati is the time Saturn takes to walk past your Moon sign, {_mw}: a long phase in three parts. "
                             "Right now Saturn is further away" + (f", passing {yh(sat_h)}" if sat_h in HOUSE and fits(yh(sat_h)) else "")
                             + ", so this phase is not active for you.")
        put("sadesati.means", f"Saturn's slow lessons are lighter for you now; its steady work falls on {sat_life} instead. "
                              f"Use the room to build habits that last, starting {pos(all_good[:1])}.")
        put("sadesati.why", f"Saturn sits in {sat_now.get('sign') or 'its sign'}, {rel or 'a sign away from your Moon sign'}, "
                            "outside the three signs around it.")
        out["sadesati.when"] = "not active from this Diwali to the next"
        steps = ["Keep a monthly budget: one page, money in and money out"
                 + (f", tightest in your {cnt(len(sp_m), 'month')} of careful spending." if sp_m else
                    f", with a line for costs around {HELP[_b12]}." if _b12 in HELP else "."),
                 "Clear small dues: close small amounts owed before new ones"
                 + (f", ideally {pos(loans)}." if loans else f", one each month from {pos(all_good[:1])}."),
                 ("Keep promised dates: Saturn rewards kept promises" + (f", above all around {sat_life}" if fits(sat_life) else ""))
                 + (f", {span(care_all)}." if n_care else "."),
                 "Lend only on paper: write down any large loan"
                 + (f", and take extra care in your {cnt(len(rx_m), 'month')} of quick reactions, {span(rx_m)}." if rx_m else
                    f", and settle old ones {pos(loans or all_good[-1:])}."),
                 "Save a little each month: put more aside when a good month comes" + (f", most of all {pos(bt['from'] and [bt['from']])}." if bt.get("from") and not no_best else
                                                                                       f", before {span(care_all)}." if care_all else ".")]
    put("sadesati.steps", "\n".join(steps))

    # areas with the most good months first: each strength is pointed at one of them
    rank_a = sorted(AREAS, key=lambda a: (-len(set(win(a, "best") + win(a, "good"))), AREAS.index(a)))
    used_titles, said_h = set(), set()
    for i in range(3):
        s = strs[i] if i < len(strs) else {}
        nm = s.get("planet") or ["Jupiter", "Saturn", "Venus"][i]
        h = s.get("house") or ch.pl(nm).get("house")
        title, what = STRENGTH.get(nm, ("A steady hand", "You keep going."))
        if h == 4 and nm == "Mars":
            title, what = "Energy for home", "You put real energy into the home, property and family."
        if title in used_titles:
            title = f"{title}, through {HOUSE.get(h, 'your chart').replace('the ', '', 1)}"
        used_titles.add(title)
        out[f"strengths.{i + 1}.title"] = title
        ar = rank_a[i % len(rank_a)]
        # where it shows: the part of life its house stands for, said once (two strengths in one house share it)
        shows = (["It shows most in {}.", "You see it in {}.", "It comes through in {}."][i].format(HELP[h])
                 if h in HELP and h not in said_h else "")
        said_h.add(h)
        put(f"strengths.{i + 1}.what", " ".join(x for x in (what, shows, f"Use it for {AREA_PHRASE[ar]} above all, "
                                                                       f"{pos(win(ar, 'best') + win(ar, 'good'))}.") if x))
        out[f"strengths.{i + 1}.do"] = STRENGTH_DO.get(nm, "Give your strongest skill one fixed hour a week") + {
            "business": " for the business.", "job": " at work.", "student": " in your studies.", "home": " at home."}[work]
        put(f"strengths.{i + 1}.why", min(str_why[i], key=cost))

    for r in ("reactions", "spending"):
        cm = [m.get("ym") for m in mlist if m.get("care_reason") == r]
        why = ""
        if cm:
            if r == "reactions":
                t = ch.transit(cm[0], "Mars")
                if t.get("house"):
                    _rt = ch.ruler_tie(t["house"], "Mars")
                    why = f"Mars {'moves backward' if t.get('retro') else 'moves'} in {HOUSE[t['house']]}{_rt or ' in those months'}."
            else:
                for pl in ("Jupiter", "Saturn", "Mars", "Venus", "Rahu"):
                    t = ch.transit(cm[0], pl)
                    if t.get("house") in (12, 8, 2):
                        why = _cap(f"{_pn(pl)} moves into {t['sign'] + ', ' if t.get('sign') else ''}{HOUSE[t['house']]} of your chart, for a while.")
                        break
        aft = [y for y in MONTH_YMS if cm and y > max(cm) and y not in cm]
        out[f"slow.{r}.title"] = {"reactions": "Quick reactions", "spending": "Spending"}[r]
        if r == "reactions":
            put(f"slow.{r}.what", (f"You may react fast, in words or decisions, over {cnt(len(cm), 'month')} {span(cm)}. "
                                   f"A sharp reply or a rushed signature could cost more than it seems, above all in "
                                   f"{LIFE.get(ch.transit(cm[0], 'Mars').get('house'), 'day-to-day talks')}.")
                if cm else f"No careful time for quick reactions stands out. Still, sleep on any large reply about {mars_life}.")
            put(f"slow.{r}.do", "Paying down a loan is fine, but wait a day before new signatures and important replies.")
            out[f"slow.{r}.watch"] = f"Small arguments, above all around {MARS_WATCH.get(ch.transit(cm[0], 'Mars').get('house'), 'work and home') if cm else MARS_WATCH.get(ch.pl('Mars').get('house'), 'work and home')}."
        else:
            put(f"slow.{r}.what", (f"Travel, repairs and extra costs may rise over {cnt(len(cm), 'month')} {span(cm)}. "
                                   "A large buy that can wait may wait a little.")
                if cm else f"No careful time for spending stands out. Keep a simple monthly plan all the same, and large buys "
                           f"for a gold month, the first {pos(gold_ok or all_good)}.")
            out[f"slow.{r}.do"] = ((f"Set a spending limit for these {NUM.get(len(cm), 'few')} months" if len(cm) > 1 else "Set a spending limit for this month")
                                   + ", and keep large buys for the gold months.") if cm else "Keep large buys for the gold months."
            put(f"slow.{r}.watch", "Lending money without writing it down.")
        _mr = ch.pl("Mars")
        if r == "reactions":   # quick reactions are Mars's: its own place in the chart is the fallback reason
            _c = [why, _sent(f"Mars sits in {HOUSE.get(_mr.get('house'), 'your chart')}{_dig(_mr.get('dignity'))}"),
                  _sent(f"Mars, the planet of quick action, is in {_mr.get('sign') or 'its sign'}")]
        else:
            _c = [why] + ch.natal_facts([12]) + ([f"The spending part of your chart is in {ch.sign(12)}."] if ch.sign(12) else [])
        put(f"slow.{r}.why", take(*_c) or (as_fact(_c[1])[0] if len(_c) > 1 else "Your chart has a careful time here."))
        out[f"slow.{r}.when"] = (f"careful time; better {pos(aft)}" if cm else "no careful time marked")

    # the last resort reason, when every fitting fact is said: a planet's own sign, said once
    sign_facts = [_Fact((f"Your chart has {_pn(q)} in {ch.pl(q)['sign']}.", f"{_cap(_pn(q))} sits in {ch.pl(q)['sign']} in your chart."),
                        ("SG", q), None) for q in PLANETS if ch.pl(q).get("sign")]

    # ── area sections ────────────────────────────────────────────────────────
    tables = {"money": MONEY, "career": CAREER[work], "business": BUSINESS[work],
              "family": FAMILY, "marriage": MARRIAGE}
    SPECIAL = {("money", 6), ("money", 7), ("marriage", 4), ("marriage", 5)}
    money_said: set = set()
    _b11 = ch.pl(ch.lord(11)).get("house")   # they write their own reason below

    def t_months(a, n):
        t = topic(a, n)
        st = _state(t, _state(areas_d.get(a)))
        best, good, care = win(a, "best"), win(a, "good"), win(a, "careful")
        when = t.get("when") or {"good": "good", "steady": "steady", "careful": "careful"}[st]
        return t, st, when, t.get("months") or {"best": best, "good": good or best, "careful": care}.get(when) or best or good

    def here(g, h):
        """Under a topic, its own part can be called 'this part of your chart': more ways to say one fact."""
        if not (isinstance(g, _Fact) and g.key and len(g.key) == 3 and g.key[2] == h):
            return g
        kind, P = g.key[0], _pn(g.key[1])
        sg = ch.pl(g.key[1]).get("sign") or "its sign"
        B = HOUSE.get(ch.pl(g.key[1]).get("house"), "")
        hs = ch.sign(h) or "its sign"   # the part's own sign keeps each 'this part' sentence its own
        extra = {"R": ([f"This part, in {hs}, has its ruler {P} in {sg}.", f"{P} rules this part, in {hs}, from {sg}.",
                        f"{P}, which rules this part of your chart, sits in {B}."] if B and g.to != h else
                       [f"{P} rules this part of your chart, in {hs}, and sits in it."]),
                 "O": [f"This part, in {hs}, holds {P}.", f"{P} sits in this part of your chart, in {sg}."],
                 "T": [f"{P} is passing this part, in {hs}, now.", f"{P} passes through this part of your chart, in {hs}."],
                 "A": [f"This part, in {hs}, gets {P}'s look.", f"{P} looks at this part of your chart, in {hs}."]}.get(kind, [])
        return _Fact(tuple(g) + tuple(extra), g.key, g.to)

    def rel_cands(a, n):
        """The true reasons that speak to this topic, most fitting first: where the ruler of its own part sits
        (the classic reading), the engine's timing reason, slow planets passing or looking at its part, other
        planets in its part, then the same for the area's other parts."""
        t, _, _, months = t_months(a, n)
        h = TOPIC_HOUSE[a][n - 1] or AREA_HOUSES[a][0]
        fh = list(dict.fromkeys(AREA_HOUSES[a] + [x for x in TOPIC_HOUSE[a] if x]))
        ew = clean_why(t.get("why"))
        if ew and not named(ew):
            ew = ""   # "No slow planet presses hard ...": not a reason a buyer can see
        _m = re.match(r"^(.*\b(?:passes|moves through|moves into|enters) )(the [a-z -]+ part|the part for yourself)\.$", ew or "")
        _eh = next((x for x in HOUSE if _m and HOUSE[x] == _m.group(2)), None)
        _tie = ch.ruler_tie(_eh, (named(ew) or {""}).pop()) if _eh else ""
        ewg = (ew[:-1] + _tie + ".", ew) if _tie else ew
        nf_h = [here(g, h) for g in ch.natal_facts([h])]
        return [as_fact(c) for c in (nf_h[:1] + [ewg] + [here(g, h) for g in ch.transit_facts(months, [h]) + ch.aspect_facts(months, [h])] + nf_h[1:]
                                     + ch.transit_facts(months, fh) + ch.natal_facts(fh) + ch.aspect_facts(months, fh)) if c]

    t6_why = next((here(g, 2) for g in ch.natal_facts([2]) + ch.natal_facts([11]) if g.key not in used_facts), None)
    if t6_why:
        used_facts.add(t6_why.key)

    # Each topic gets its own reason. Topics with the fewest fitting reasons choose first, so a topic late in
    # the report is not left with a fact about some other part of life.
    order_t = [(a, n) for a in AREAS for n in range(1, len(tables[a]) + 1) if (a, n) not in SPECIAL]
    rel = {x: rel_cands(*x) for x in order_t}
    assigned, todo = {}, list(order_t)
    while todo:
        x = min(todo, key=lambda x: (sum(g.key not in used_facts for g in rel[x]), order_t.index(x)))
        g = next((g for g in rel[x] if g.key not in used_facts), None)
        if g:
            assigned[x] = g
            used_facts.add(g.key)
        todo.remove(x)

    for a in AREAS:
        ad_ = areas_d.get(a) or {}
        ast = _state(ad_)
        best, good, care = win(a, "best"), win(a, "good"), win(a, "careful")
        nouns = HELP_P if a in ("family", "marriage") else HELP
        area_said: set = set()
        if a == "money":
            money_said = area_said
        for n, spec in enumerate(tables[a], 1):
            t = topic(a, n)
            st = _state(t, ast)
            when = t.get("when") or {"good": "good", "steady": "steady", "careful": "careful"}[st]
            months = t.get("months") or {"best": best, "good": good or best, "careful": care}.get(when) or best or good
            cpos = cwhy = ""
            tpl = spec[st]
            if st == "careful":  # a caution says where it falls and from when it gets better (spec §2 rule 14)
                cm = (months if when == "careful" else care) or months
                if "{cwhy}" in tpl:   # say which kind of careful time it is (payload.summary / month reason)
                    by_r = {r_: [m for m in cm if care_reason(m) == r_] for r_ in ("spending", "reactions")}
                    r_ = "spending" if by_r["spending"] else "reactions" if by_r["reactions"] else ""
                    cm = by_r.get(r_) or cm
                    cwhy = {"spending": " for spending", "reactions": " for quick reactions"}.get(r_, "")
                after = [m for m in (good + best) if m > (min(cm) if cm else "")]
                if "{cpos}" in tpl:
                    cpos = span(cm)
                lead_yms = after or good or best
                p_yms = after or good or best
            else:
                lead_yms = months
                p_yms = months
            k = f"{a}.t{n}"
            out[f"{k}.title"] = spec["title"]
            h = TOPIC_HOUSE[a][n - 1] or AREA_HOUSES[a][0]
            # Why: the engine's reason, else a transit or birth-chart fact about the topic's own part, then the
            # area's parts, then any part; each fact said once in the report. The classic reading of a topic is
            # where the ruler of its own part sits (that part of life is how the topic works out for you), so
            # that fact comes first, then the engine's reason for the topic's timing.
            ew = clean_why(t.get("why"))
            if ew and not named(ew):
                ew = ""   # "No slow planet presses hard ...": not a reason a buyer can see
            g_ = assigned.get((a, n))
            if g_ and not any(fits(c) for c in g_):
                # its reason can no longer be said without repeating words: another fitting reason, if one is free
                alt = next((g for g in rel[(a, n)] + [as_fact(c) for c in all_natal + ch.transit_facts(months, list(HOUSE))] + sign_facts
                            if g.key not in used_facts and any(fits(c) for c in g)), None)
                if alt:
                    used_facts.discard(g_.key)
                    used_facts.add(alt.key)
                    g_ = alt
            if g_:
                put(f"{k}.why", next((c for c in g_ if fits(c)), min(g_, key=cost)))
                taken_to[0] = g_.to
            elif (a, n) not in SPECIAL:   # no fitting reason left: any true fact not yet said
                put(f"{k}.why", take(*(all_natal + ch.transit_facts(months, list(HOUSE)) + ch.aspect_facts(months, list(HOUSE))
                                       + sign_facts)))
            # What: the lead (state + when), what the reason means for this topic, then the advice
            # the part the reason points to; none when it is the topic's own part (that would say nothing)
            to_ = taken_to[0] if (a, n) not in (("money", 6), ("money", 7), ("marriage", 4), ("marriage", 5)) else None
            mean = spec["mean"].format(h=nouns[to_]) if spec["mean"] and to_ in nouns and to_ != h else ""
            if mean and not fits(mean):
                mean = ""
            if mean and (to_ in area_said):
                mean = ""
            _rh = lord_house(h)   # else: where the ruler of the topic's own part sits, the classic reading of it
            if not mean and spec["mean"] and _rh in nouns and _rh != h and _rh not in area_said \
                    and fits(spec["mean"].format(h=nouns[_rh])):
                mean, to_ = spec["mean"].format(h=nouns[_rh]), _rh
            if mean:
                area_said.add(to_)
            if not mean and spec["mean"] and lead_yms:   # no reason to read out: say how many months suit it
                _nm = len(set(lead_yms))
                _ls = pos(sorted(lead_yms)[-1:]) if _nm > 1 else ""
                _sv = "suit" if _nm != 1 else "suits"
                if _nm >= 10:   # nearly every month: a count says nothing
                    _ls = ""
                _so = "stand out" if _nm != 1 else "stands out"
                mean = next((x for x in (("Nearly every month suits it." if _nm >= 10 else ""),
                                         (f"{_cap(cnt(_nm, 'month'))} {_so} for it, the last {_ls}." if _ls else ""),
                                         f"{_cap(cnt(_nm, 'month'))} {_so} for it.", f"It has {cnt(_nm, 'good month')}.",
                                         f"{_cap(cnt(_nm, 'month'))} {_sv} it.") if x and fits(x)), "")
            if spec["body"] or spec[st]:
                lfmt = lambda o: tpl.format(pos=o, cpos=cpos, cwhy=cwhy, ng=NUM.get(len(set(best + good)), "a few"), **fill)
                lead = pos(lead_yms, lfmt) if "{pos}" in tpl else lfmt("")
                if (a, n) == ("money", 6) and not mean:
                    mean = next((x for x in (_cap(w) + "." for w in peak("money")) if fits(x)), "")
                if (a, n) == ("money", 6) and _b11 in HELP and _b11 != ch.pl(ch.lord(2)).get("house"):
                    _g11 = f"Gains also come through {HELP[_b11]}."   # the ruler of the gains part's place
                    if fits(_g11) and _b11 not in area_said:
                        mean = _g11
                        area_said.add(_b11)
                put(f"{k}.what", no_care(_what3(lead, spec["body"].format(**fill), mean)))
            # Do / Watch: the open or the quiet wording, by where the ruler of the topic's part sits (the quiet
            # one for a careful topic); "{p}" = when this topic's months fall (after the careful time, if careful)
            side = 0 if lord_house(h) in OPEN_HOUSES else 1
            do_, wa_ = pick(spec["do"], side), pick(spec["watch"], side)
            if "{p}" in do_:
                do_ = do_.replace("{p}", pos(p_yms))
            put(f"{k}.do", no_care(do_.format(**fill)))
            put(f"{k}.watch", no_care(wa_.format(**fill)))
            out[f"{k}.when"] = _when_text(when, bool(best), no_best)

        # openers and headlines
        pos_n_ = order.index(a) + (2 if steer == "luck" else 1)
        _n = len(set(best + good))
        if steer == a:
            op = f"You picked {AREA_NAME[a]}, so it comes first."
        elif pos_n_ == 1:
            op = f"{AREA_NAME[a]} opens your report, as fits {ROLE_OF[work]}."
        else:
            _nw = NUM.get(_n, str(_n))
            _op = [f"Its {_nw} good month{'s start' if _n != 1 else ' comes'} {{p}}.", f"It has {_nw} good month{'s' * (_n != 1)}, the first {{p}}.",
                   f"{_cap(_nw)} of your months suit it; the first comes {{p}}.", f"You have {_nw} good month{'s' * (_n != 1)} for it, beginning {{p}}.",
                   f"{_cap(_nw)} good month{'s back' if _n != 1 else ' backs'} it, the first {{p}}."][AREAS.index(a)]
            op = f"{AREA_NAME[a]} comes {ORD.get(pos_n_, 'next')} for you." + (pos(best + good, lambda o: " " + _op.format(p=o)) if _n else "")
            if not care and op.endswith("."):
                op = first_fit(*[op[:-1] + f"; {w}." for w in peak(a)], op)
            if care and op.endswith("."):
                _nc = len(set(care))
                op = first_fit(op[:-1] + f", and {cnt(_nc, 'month')} {'ask' if _nc != 1 else 'asks'} for care.",
                               op[:-1] + f"; {cnt(_nc, 'month')} {'need' if _nc != 1 else 'needs'} a gentler pace.", op)
        if a == "career":
            op += {"business": " As a business owner, this reads your own role: how you lead and when to step up.",
                   "student": " As a student, this covers your studies and a first job.",
                   "home": " This covers returning to work and income you can earn from home.",
                   "job": " This covers your role, a raise and the right time to move."}[work]
            if band == "60p":
                op = op.replace("a first job", "your next role")
        if a == "business":
            op += {"business": " As its owner, this is your day-to-day.",
                   "job": " As someone with a job, this covers business against a job, and side income.",
                   "student": " As a student, this reads your future leaning to business or a job.",
                   "home": " This covers small home ventures and the family money picture."}[work]
        put(f"{a}.opener", op)
        cnw = NUM.get(_n, str(_n))
        hv = HEADLINE[a][ast]
        if ast == "good":
            hv = hv[0] if best and not no_best else hv[1]
            hl = hv.format(pos=pos(best if best and not no_best else good or best), n=cnw)
        else:
            hl = hv.format(pos=pos(([m for m in good + best if m > min(care)] or good or best) if ast == "careful" and care
                                   else good or best), n=cnw)
        if _n and "{n}" not in HEADLINE[a][ast]:
            pass   # a claim headline names no count; the picture below it shows the months
        if ast == "good":
            hl = first_fit(*[f"{hl}; {w}" for w in run_end(a) if not w.startswith("it ")], hl)
        put(f"{a}.headline", f"{hl}.")   # a claim headline, like a title: no chart clause (Mock 3C)
        rd = READ[a][ast][0 if care else 1]
        nc_ = len(set(care))
        _G, _C = _cap(NUM.get(_n, str(_n))), NUM.get(nc_, str(nc_))
        tally = ({"money": f"{_G} good month{'s' * (_n != 1)}" + (f" and {_C} careful, {span(care)}" if nc_ else ""),
                  "career": f"{_G} month{'s' * (_n != 1)} to push" + (f", {_C} to hold back {span(care)}" if nc_ else ""),
                  "business": f"{_G} month{'s' * (_n != 1)} to grow" + (f" against {_C} to go slow" if nc_ else ""),
                  "family": f"{_G} warm month{'s' * (_n != 1)}" + (f" and {_C} to go gently" if nc_ else ""),
                  "marriage": f"{_G} good month{'s' * (_n != 1)} for close bonds" + (f", {_C} for care" if nc_ else "")}[a]
                 if _n else "")
        rd = rd.format(pos=pos(([m for m in good + best if m > min(care or [''])] or good or best) if ast == "careful"
                               else (best if best and not no_best else good or best)))
        put(f"{a}.read", f"{tally}: {rd}" if tally else _cap(rd))

    # Money t6: where money comes from (the ruler of the money part's place), its own chart reason
    _l2 = ch.lord(2)
    put("money.t6.why", min(t6_why, key=cost) if t6_why else take(*(ch.natal_facts([11]) + all_natal)))
    # Money t7: wealth combination
    dy = (p.get("money_extra") or {}).get("dhana_yoga") or {}
    lords = [x for x in dy.get("lords") or [] if x]
    if dy.get("present"):
        _lk = [x for x in dy.get("links") or [] if len(x.get("planets") or []) == 2 and len(x.get("houses") or []) == 2]
        out["money.t7.title"] = "Your wealth combination: present"
        put("money.t7.what", "Your chart has a wealth combination, called Dhana Yoga. "
                             f"It points to wealth built over time, by planning more than by chance"
                             + (_thr if _lk and all(x in HELP for x in _lk[0]['houses']) and not set(_lk[0]['houses']) & money_said
                                and fits(_thr := f", through {HELP[_lk[0]['houses'][0]]} and {HELP[_lk[0]['houses'][1]]}") else "")
                             + first_fit(*[f"; {w}." for w in peak("money") + run_end("money")], "."))
        ly = " and ".join(lords[:2]) if lords else ""
        _d = (f"The classic rule is met: {ly}, rulers of your wealth parts, are linked." if ly
              else "The classic rule is met: the rulers of your wealth parts are linked.")
        _link = ""
        if _lk:
            (p1, p2), (h1, h2) = _lk[0]["planets"], _lk[0]["houses"]
            how = {"same sign": "sit in one sign", "exchange": "swap signs", "aspect": "look at each other",
                   }.get(_lk[0].get("kind"), "are linked")
            _s1, _s2 = ch.pl(p1).get("sign"), ch.pl(p2).get("sign")
            _link = clean_why(_cap(f"{_pn(p1)}{' in ' + _s1 if _s1 else ''} and {_pn(p2)}{' in ' + _s2 if _s2 else ''} {how}, "
                              f"linking {HOUSE.get(h1, 'one wealth part')} and {HOUSE.get(h2, 'another')}"))
        put("money.t7.why", take(_link, clean_why(topic("money", 7).get("why")), _d, clean_why(dy.get("rule_text"))) or _d)
        out["money.t7.when"] = "good time, growing slowly"
    else:
        out["money.t7.title"] = "Your wealth combination: building"
        _l11 = ch.lord(11)
        put("money.t7.what", "Your chart does not show the classic wealth combination, called Dhana Yoga. "
                             f"That is common: wealth tends to build through steady habits, not one strong push, starting {pos(win('money', 'best') + win('money', 'good'))}.")
        _d = (f"The rulers of your money part and gains part, {_pn(_l2) or 'its ruler'} in {HOUSE.get(ch.pl(_l2).get('house'), 'its place')} "
              f"and {_pn(_l11) or 'its ruler'} in {HOUSE.get(ch.pl(_l11).get('house'), 'its place')}, do not join by the classic rule.")
        put("money.t7.why", take(clean_why(dy.get("rule_text")), clean_why(topic("money", 7).get("why")), _d) or _d)
        out["money.t7.when"] = "steady time, built month by month"

    # Marriage t4: traits (gender changes the reading planet)
    sig = "Jupiter" if female else "Venus"
    sp = ch.pl(sig)
    s7, l7 = ch.sign(7), ch.lord(7)
    me = p.get("marriage_extra") or {}
    mt4 = _state(topic("marriage", 4), _state(areas_d.get("marriage")))
    _pt = PARTNER_SIGN.get(sp.get("sign"), "warm, loyal and steady")
    put("marriage.t4.what", f"Your chart suggests you value {VALUE7.get(s7, 'loyalty and a steady bond')}. "
                            f"You may be drawn to people who are {_pt}. " +
                            (f"You also need {MOON_NEED.get(moon_sign, 'steady care')}."
                             if mt4 != "careful" else
                             f"You also need {MOON_NEED.get(moon_sign, 'steady care')}, so give new bonds time."))
    _d = _sent(
        f"The partner part sits in {s7 or 'its sign'}, its ruler {l7 or 'its planet'} sits in {HOUSE.get(ch.pl(l7).get('house'), 'your chart')}, "
        f"and {sig}, a key planet for partnership in your chart, is in {sp.get('sign') or 'its sign'}")
    _ew4 = clean_why(topic("marriage", 4).get("why"))  # keep the gender reading planet in the line (CLAUDE.md §12)
    _d2 = _sent(f"{sig}, a key planet for partnership in your chart, is in {sp.get('sign') or 'its sign'}, "
                f"and the partner part is in {s7 or 'its sign'}")
    _d3 = _sent(f"{sig}, a key planet for partnership in your chart, sits in {sp.get('sign') or 'its sign'}")
    _dF = _Fact((_d,), ("R", l7, 7), ch.pl(l7).get("house"))            # says where the ruler of the partner part sits
    _sF = _Fact((_d3, _d2), ("S", sig), None)                             # the reading planet's sign
    put("marriage.t4.why", (take(_ew4, _dF, _sF) if sig in _ew4 else take(_dF, _sF)) or _d)
    out["marriage.t4.when"] = "a lifelong leaning; use it in good times"
    # Marriage t5: Manglik facts box (bank-only fact lines + R2 keys)
    mg = me.get("manglik") or {}
    mars = ch.pl("Mars")
    lag = (chart.get("lagna") or {}).get("sign", "")
    moon = (chart.get("moon") or {}).get("sign", "")
    _r = lambda v: "By this rule, yes." if v else "By this rule, no."

    def _from(base):
        if mars.get("sign") in SIGNS and base in SIGNS:
            return _ordn((SIGNS.index(mars["sign"]) - SIGNS.index(base)) % 12 + 1) + " from"
        return "counted from"
    put("marriage.manglik.lagna", (_sent(mg["lagna_rule"]) if isinstance(mg.get("lagna_rule"), str) and not lint_text(mg["lagna_rule"])
                                     else f"Rising-sign rule: Mars is {_from(lag)} your rising sign, {lag}. {_r(mg.get('lagna_rule'))}"))
    put("marriage.manglik.moon", (_sent(mg["moon_rule"]) if isinstance(mg.get("moon_rule"), str) and not lint_text(mg["moon_rule"])
                                    else f"Moon rule: Mars is {_from(moon)} your Moon sign, {moon}. {_r(mg.get('moon_rule'))}"))
    if meta.get("basis") == "moon":
        out["marriage.manglik.lagna"] = "Rising-sign rule: not used, because the birth time is not exact."
    out["marriage.manglik.cancel"] = (f"Cancelled: {_sent(mg.get('reason') or 'a classic exception applies')}" if mg.get("cancelled")
                                      else "Not cancelled by the classic exceptions." if (mg.get("lagna_rule") or mg.get("moon_rule"))
                                      else "Nothing to cancel.")
    out["marriage.manglik.means"] = "What it means: a fact to share with the family if a match is discussed. It does not need any paid fix."
    _m5 = f"Mars sits in {HOUSE.get(mars.get('house'), 'your chart')}, in {mars.get('sign') or 'its sign'}."
    put("marriage.t5.why", (next((c for c in m5_fact if fits(c)), m5_fact[-1]) if m5_own else
                            first_fit(f"Your chart has Mars in {mars.get('sign') or 'its sign'}.",
                                      f"In your chart, Mars is in {mars.get('sign') or 'its sign'}.")))
    out["marriage.t5.when"] = "a fixed fact of your chart"

    fam_care = win("family", "careful") or win("marriage", "careful")
    _fgood = win("family", "good") + win("family", "best")
    put("family.talks", (f"Quick words at home may land harder than you mean in your careful time for talks, {span(fam_care)}. "
                         f"Leave hard talks for the next morning; {HOME4.get(ch.sign(4), 'a kind word')} helps. It gets easier "
                         f"{pos([m for m in _fgood if m > min(fam_care)] or _fgood)}."
                         if fam_care else
                         f"No careful time for family talks stands out. Keep the good habits going: {HOME4.get(ch.sign(4), 'a kind word')} "
                         f"helps, and big family talks suit the good months, from {pos(_fgood)}."))
    _mc = win("marriage", "careful")
    _mg_n = len(set(win("marriage", "good") + win("marriage", "best")))
    put("marriage.helps", "A short daily talk with no phones, one shared goal for the months ahead, and kindness about each other's busy days, "
                          + (first_fit(f"above all in your {cnt(len(set(_mc)), 'careful month')} for close bonds, {span(_mc)}.",
                                       f"above all when close bonds need care, {span(_mc)}.") if _mc else
                             f"with one evening together each month, from {pos(win('marriage', 'good') + win('marriage', 'best'))}."))
    out["note.helpline"] = "If a conflict at home feels serious, please talk to someone you trust or a trained helper."
    out["career.label"] = {"student": "Career: studies and first job"}.get(work, "Career")

    # ── front pages ──────────────────────────────────────────────────────────
    out["note.order"] = (f"{AREA_NAME[steer]} comes first, as you picked it. " if steer in AREA_NAME
                         else f"As {WORK_AS[work]}, your report starts with {AREA_NAME[order[0]]}. ")
    rest = [AREA_NAME[a] for a in order if a != steer and (steer or a != order[0])] + ([] if steer == "luck" else ["Better luck"])
    out["note.order"] += ", ".join(rest[:-1]) + f" and {rest[-1]} follow."
    out["note.answers_intro"] = (f"You picked {AREA_NAME[lead_area]}, so your answers start there." if steer
                                 else f"Your answers come from {AREA_NAME[lead_area]}, your first area.")
    out["note.less_precise"] = ("Your birth time is not exact, so this report reads your chart by your Moon sign. "
                                "That is less precise for the houses, so read the timing as a guide."
                                if meta.get("basis") == "moon" else
                                "Your birth time was given exactly, so this report reads your rising sign in full.")

    ans = p.get("answers") or []
    ab_, ag_, ac_ = (win(lead_area, "best"), win(lead_area, "good"), win(lead_area, "careful")) if lead_area != "luck" else (
        [bt["from"]] if bt.get("from") else [], [], [])
    ng = NUM.get(len(gold), str(len(gold)))
    ANSW = {
        "money": [("Money looks steadier after Diwali, and it tends to build {bp}.",
                   "Money holds steady after Diwali, with firmer months {bp}.",
                   "Money needs care at first, and it firms up {gp}."),
                  ("Growth may begin {fp}. Your best time is marked on your timeline.",
                   "Growth may build slowly, with a lift {bp}; see your timeline.",
                   "Growth comes after a careful start, {gp}; see your timeline."),
                  ("Yes. Your chart suggests real room to build wealth, above all {bp}.",
                   "There is room to build wealth slowly, through steady saving.",
                   "Wealth builds through habits more than big moves for now."),
                  ("One careful time asks you to plan large costs; it gets better after. See your timeline.",
                   f"Spending stays fairly even, with {NUM.get(len(ac_), str(len(ac_)))} careful months; plan larger costs {{bp}}.",
                   "A careful time for spending comes {cp}; plan large costs and save."),
                  (f"{_cap(ng)} months are marked for gold or property, by our method, the first {{gd}}" + (f" and the last {pos(gold[-1:])}." if len(gold) > 1 else "."),
                   f"{_cap(ng)} months are marked for gold or property, by our method, the first {{gd}}; buy only what is planned.",
                   f"{_cap(ng)} months are marked by our method, the first {{gd}}; hold large buys until then.")],
        "career": [("A breakthrough looks possible, above all {bp}.", "Steady growth leads, with a chance to rise {bp}.",
                    "Build your record first; a breakthrough fits better {gp}."),
                   ("Professional growth looks good {bp}; see your timeline.", "Growth is steady, with a lift {bp}.",
                    "Growth picks up {gp}, after a careful start."),
                   ("A good time for a change may begin {bp}.", "A change can wait for a good month, {bp}.",
                    "Hold a change for now; a better time begins {gp}."),
                   ("Asking for more fits well {bp}.", "Asking for a raise can go fine {bp}, if your results are clear.",
                    "Wait a little; asking goes better {gp}."),
                   ("Few months need holding back; one careful time is marked on your timeline.",
                    "Some months suit steady effort; your timeline marks them.",
                    "A careful time comes {cp}; keep effort steady and avoid sudden moves.")],
        "business": [("New growth looks likely, above all {bp}.", "Business holds steady, with a lift {bp}.",
                      "Business asks for care first, and it grows {gp}."),
                     ("Profit may pick up {bp}; see your timeline.", "Profit builds slowly, firmer {bp}.",
                      "Profit firms up {gp}, after a careful start."),
                     ("Launching or expanding fits well {bp}.", "Prepare now; expansion fits {bp}.",
                      "Hold expansion and plan; it fits better {gp}."),
                     ("A partner for one clear job could work well.", "A partner can help, with roles on paper.",
                      "Go slowly with partners; keep the business in your own name."),
                     ("Loans and credit look manageable; one careful time is on your timeline.",
                      "Credit stays steady; review it each month.",
                      "A careful time for loans and credit comes {cp}; collect dues first.")],
        "family": [("More harmony looks likely at home, above all {bp}.", "Home life holds steady, warmer {bp}.",
                    "Home asks for patience first, and warms up {gp}."),
                   ("Family events go well {bp}.", "Family events go smoothly, from {bp}.",
                    "Keep events simple for now; hosting goes better {gp}."),
                   ("A good time for home or property may begin {bp}.", "Home steps fit {bp}.",
                    "Hold home moves for now; a better time begins {gp}."),
                   ("Happy family news looks likely {bp}.", "Happy news may come gently, {bp}.",
                    "Happy news may take a little longer, coming more easily {gp}."),
                   ("Family talks look easy; one careful time is on your timeline.",
                    "Family talks stay steady; take care in busy months.",
                    "A careful time for family talks comes {cp}; it gets easier after.")],
        "marriage": [("Warmth could grow in your closest bonds, above all {bp}.", "Bonds hold steady, warmer {bp}.",
                      "Close bonds ask for care first, and warm up {gp}."),
                     ("Important decisions go well {bp}.", "Decisions fit {bp}, made side by side.",
                      "Hold large decisions for now; they go better {gp}."),
                     ("Talks look easy; one careful time is on your timeline.", "Talks stay steady; listen to the end.",
                      "A careful time for close talks comes {cp}; it passes."),
                     (f"You may value people who are {PARTNER_SIGN.get(ch.pl('Jupiter' if female else 'Venus').get('sign'), 'warm and loyal')}.",
                      f"You may value people who are {PARTNER_SIGN.get(ch.pl('Jupiter' if female else 'Venus').get('sign'), 'warm and loyal')}; bonds grow slowly.",
                      f"You may value people who are {PARTNER_SIGN.get(ch.pl('Jupiter' if female else 'Venus').get('sign'), 'warm and loyal')}; give bonds time."),
                     ("Your plain facts are in the Manglik box in the Marriage section.",) * 3],
        "luck": [("Yes. The months after Diwali look like a real turning point.", "A quiet turning point comes, step by step.",
                  "The turn comes after a careful start, {gp}."),
                 ("Your brightest months are marked on your timeline.", "Your good months are marked on your timeline.",
                  "Good months follow the careful ones; see your timeline."),
                 ("A fresh chapter may begin {bp}.", "A fresh chapter opens slowly, {bp}.", "A fresh chapter begins {gp}."),
                 ("Your three strengths are ready to use now.",) * 3,
                 ("Small daily habits around money and order suit you.",) * 3],
    }
    _after = [m for m in ag_ + ab_ if ac_ and m > min(ac_)]
    APM = {"bp": ab_ or ag_, "fp": sorted(ab_ + ag_)[:1],  # fp: first good-or-best month
           "gp": _after or ag_ or ab_, "cp": ac_, "gd": gold}
    for i in range(5):
        st = _state(ans[i] if i < len(ans) else None, _state(areas_d.get(lead_area)))
        tpl_a = ANSW[lead_area][i][("good", "steady", "careful").index(st)]
        a_ = tpl_a.format(**{k_: (span(v_) if k_ == "cp" else pos(v_)) if "{" + k_ + "}" in tpl_a else ""
                             for k_, v_ in APM.items()})
        nl_ = len(set(ab_ + ag_)) if lead_area != "luck" else len(all_good)
        nlw = cnt(nl_, "good month")
        a_ = a_.replace("Your best time is marked on your timeline.", f"Your best time and {nlw} are on your timeline.")
        a_ = a_.replace("see your timeline.", f"your timeline marks {nlw}.")
        if i == 0 and st != "careful" and nl_:
            a_ = a_[:-1] + f"; {nlw} are marked."
        if not n_care:
            a_ = a_.replace("one careful time is marked on your timeline.", "no careful time is marked.").replace(
                "one careful time is on your timeline.", "no careful time is marked.").replace(
                "One careful time asks you to plan large costs; it gets better after. See your timeline.",
                f"No careful time stands out; plan large costs for your {nlw}.")
        put(f"answers.q{i + 1}", a_)

    GLANCE = {"money": ("Money builds step by step", "Money holds steady", "Money asks for a plan first"),
              "career": ("Your role and standing grow", "Work moves at a steady pace", "Work asks for patience first"),
              "business": ("Business has room to grow", "Business stays steady", "Business asks for care first"),
              "family": ("Home life grows warmer", "Home life stays steady", "Home asks for a gentle hand first"),
              "marriage": ("Close bonds grow warmer", "Close bonds stay steady", "Close bonds ask for care first"),
              "luck": ("Good fortune builds", "Good fortune builds slowly", "Good fortune comes after a slow start")}
    GL_TAIL = {"money": "{} ahead", "career": "{} to push at work", "business": "{} to grow it",
               "family": "with {} at home", "marriage": "{} with people close to you", "luck": "{} in all"}
    for a in AREAS + ["luck"]:
        st = _state(areas_d.get(a)) if a != "luck" else "good"
        b = win(a, "best") if a != "luck" else []
        line = {"good": "Best time" if b and not no_best else "Good time", "steady": "Steady time", "careful": "Careful time first"}[st]
        gl = GLANCE[a][("good", "steady", "careful").index(st)]
        # "State. line": the renderer strips the leading state word and prints its own label
        n_ = len(set(b + win(a, "good"))) if a != "luck" else len(all_good)
        top = ("Your strongest area. " if not no_best else "It stands out in your chart. ") if a == sa else ""
        _gm = (b + win(a, "good")) if a != "luck" else all_good
        if st == "careful":   # a careful area: say when it turns good, not when the care falls
            _gm = [m for m in _gm if m > min(win(a, "careful") or [""])] or _gm
        _gt = f", {GL_TAIL[a].format(cnt(n_, 'good month'))}" if n_ else ""
        _gx = (f"; brightest {pos(b)}" if b and not no_best else
               f"; the last {pos(sorted(_gm)[-1:])}" if len(set(_gm)) > 1 and st != "careful" else "")
        # the fullest line that keeps the report fresh: say less rather than the same again
        _gl = [(f"{line}. {top}{gl}" + (f"; good months come {o}" if st == "careful" else f" {o}") + f"{t_}{x_}.")
               for o in [pos(_gm)] for t_, x_ in ((_gt, _gx), (_gt, ""), ("", _gx), ("", ""))]
        put(f"glance.{a}", next((x for x in _gl if fits(x)), _gl[-1]))

    # timeline (dates allowed)
    TONE_LINE = {"best": "Your strongest months for the steps that matter most.",
                 "good": "Good and steady; keep building on what you started.",
                 "steady": "Steady months; keep going as you are.",
                 "careful": "Go slowly and plan large costs."}
    tl = p.get("timeline") or []
    TONE_MORE = {"best": ["More strong months; keep your big steps here.", "Still strong; finish the big steps you began.",
                          "Strong again; use it for the step you held back."],
                 "good": ["More good months; add one new step at a time.", "Good months go on; build on what is working.",
                          "Good again; pick up what you paused."],
                 "steady": ["Quiet months; finish what is open.", "Even months; plan your next step.", "Steady again; keep the routine."],
                 "careful": ["Keep costs small and decisions slow.", "Still go slowly; wait before large steps.",
                             "Careful again; keep to the plan you made."]}
    TAG_NOTE = {"gold": ("a month marked for gold", "a gold month too", "marked for gold as well"),
                "loans": ("a good month to pay down loans", "good for paying down loans", "a loan-clearing month too"),
                "family": ("a month for family plans", "good for family plans", "a family month too"),
                "deals": ("a month for new deals", "good for new deals", "a deal month too"),
                "property": ("a month for property steps", "good for property steps", "a property month too")}
    GOOD_HERE = ("Good here for {}.", "{} stays good here.", "Still good for {}.", "Good for {} again.")
    seen_ga, seen_tag = [], []
    seen_tone = []   # a repeat tone never repeats its legend line (spec §9)
    for i in range(4):
        seg = tl[i] if i < len(tl) else {}
        tone_ = seg.get("tone") if seg.get("tone") in TONE_LINE else "steady"
        if no_best and tone_ == "best":
            tone_ = "good"
        tone_line = ([TONE_LINE[tone_]] + TONE_MORE[tone_])[min(seen_tone.count(tone_), 3)]
        seen_tone.append(tone_)
        yms = [y for y in MONTH_YMS[i * 3:i * 3 + 3]]
        f, t_ = seg.get("from") or yms[0], seg.get("to") or yms[-1]
        seg_yms = [y for y in MONTH_YMS if f <= y <= t_]
        care = [y for y in seg_yms if (mon_by.get(y) or {}).get("tone") == "careful"]
        txt = f"{_rng(seg_yms)} · {seg.get('theme') or 'Months ahead'}. {tone_line}"
        tones_ = [(y, (mon_by.get(y) or {}).get("tone") or "steady") for y in seg_yms]
        if not care and len({t_x for _, t_x in tones_}) > 1:   # mixed months: say which is which (Mock 3C)
            txt += " " + _cap(", ".join(f"{_MON[int(y[5:]) - 1]} {t_x}" for y, t_x in tones_)) + "."
        if care:
            nxt = [y for y in MONTH_YMS if y > max(care) and (mon_by.get(y) or {}).get("tone") != "careful"]
            runs, cur = [], []   # one phrase per contiguous run, so steady months between runs are not called careful
            for y in care:
                if cur and _idx(y) != _idx(cur[-1]) + 1:
                    runs.append(cur)
                    cur = []
                cur.append(y)
            runs.append(cur)
            txt += " Careful in " + " and ".join(_rng(r_) for r_ in runs) + (f", better from {_lab(nxt[0])}." if nxt else ".")
        _ga = max(AREAS, key=lambda a: (sum(y in win(a, "best") + win(a, "good") for y in seg_yms), -AREAS.index(a)))
        if not care and any(y in win(_ga, "best") + win(_ga, "good") for y in seg_yms):
            _gn = AREA_NAME[_ga].lower()
            txt += " " + _cap(GOOD_HERE[min(seen_ga.count(_ga), 3)].format(_gn))
            seen_ga.append(_ga)
        _sh0 = ch.transit(seg_yms[0], "Sun").get("house") if seg_yms else None
        if _sh0 in SUN_DO:
            txt += f" {_MON[int(seg_yms[0][5:]) - 1]} suits this: {SUN_DO[_sh0]}."
        tg = next(((y, t_g) for t_g in TAG_NOTE for y in seg_yms if t_g in ((mon_by.get(y) or {}).get("tags") or [])
                   and (mon_by.get(y) or {}).get("tone") != "careful"), None)
        if tg:
            txt += f" {_lab(tg[0])} is {TAG_NOTE[tg[1]][min(seen_tag.count(tg[1]), 2)]}."
            seen_tag.append(tg[1])
        put(f"timeline.{i + 1}", txt)
    _bl = (summ.get("best") or {}).get("label") or (_rng([bt["from"], bt["to"]]) if bt else "")
    put("timeline.best", ((f"Your single best time: {_bl}" if not no_best else f"Your main good time: {_bl}") if _bl
                          else "Your good months are marked on your 12 months."))

    # wrapped words (months allowed): the engine's three words and lines, each with this buyer's own count
    ww = wr.get("words") or []
    STRONG = {"money": ("STEADY", "Your money grows slowly but surely."),
              "career": ("RISING", "Your work and name tend to grow step by step."),
              "business": ("BUILDER", "Your business has room to grow."),
              "family": ("ROOTED", "Home and family give you your footing."),
              "marriage": ("WARM", "The people closest to you matter most now.")}
    GOOD_THING = {"money": "Your money moves well", "career": "Your work and name grow", "business": "Your business grows",
                  "family": "Home life glows", "marriage": "Warmth with the people closest to you grows"}
    w1 = STRONG.get(sa, STRONG["money"])
    lab = _bl
    _ns = len(set(win(sa, "best") + win(sa, "good")))
    longest = max(s_care, key=lambda c: MONTH_YMS.index(c["to"]) - MONTH_YMS.index(c["from"])
                  if c.get("from") in MONTH_YMS and c.get("to") in MONTH_YMS else 0, default=None)
    after_care = [m for m in all_good if longest and m > (longest.get("to") or "")]
    w3 = "BRIGHT" if w1[0] == "RISING" else "RISING"
    fallback = [f"{w1[0]}: {w1[1]}",
                "PREPARED: The careful months are for planning, not spending." if n_care else
                "GROUNDED: No long careful time; keep a steady pace.",
                f"{w3}: Your {bw} is {lab}." if lab else f"{w3}: Your {bw} is on your timeline."]
    lines = []
    _nb_pre = len([m for m in all_good if bt.get("from") and m < bt["from"]])
    for i in range(3):
        w = ww[i] if i < len(ww) and isinstance(ww[i], dict) and ww[i].get("word") else {}
        if w:
            word = WRAP_WORD_SWAP.get(w["word"].upper(), w["word"].upper())  # engine's 'PATIENT' is a §5b word
            ln = f"{word}: {_sent(w.get('line', ''))}"
            if lint_text(ln, allow_dates=True):
                ln = fallback[i]   # engine text is linted like Why lines
        else:
            ln = fallback[i]
        word, txt = ln.split(": ", 1)
        if i == 2 and no_best:    # never a best claim without a best time (spec §2 rule 10)
            txt = f"{GOOD_THING.get(sa, 'Your money moves well')} in {lab}." if lab else f"Your {bw} is on your timeline."
        txt = txt.rstrip(".")
        # this buyer's own numbers, so no two buyers share a line
        tails = [[f". {_cap(cnt(_ns, 'good month'))} back it.", f", over {cnt(_ns, 'good month')}."] if _ns else ["."],
                 ([f"; then {cnt(len(after_care), 'good month')} follow.", f". After it, {cnt(len(after_care), 'good month')} come."]
                  if after_care else ["."]) if n_care else [f": {n_good} of your 12 months are good.", f". {_cap(n_good)} months ahead are good."],
                 ([f", after {cnt(_nb_pre, 'good month')} of building.", f". {_cap(cnt(_nb_pre, 'good month'))} come before it."]
                  if _nb_pre else [", right from the start.", ": it opens the months ahead."]) if bt.get("from") else ["."]][i]
        txt = next((txt + tl_ for tl_ in tails if fits(txt + tl_)), txt + tails[0])
        for g_ in grams4(txt):
            g4[g_] = g4.get(g_, 0) + 1
        for g_ in grams6(txt):
            g6[g_] = g6.get(g_, 0) + 1
        lines.append(f"{word}: {txt}")
    out["wrapped.words"] = "\n".join(lines)

    # 12-month table: a careful month never gets a gold / planned-buy Do; no Watch line in more than 2 rows,
    # and never the same Watch two rows running when another true one is there
    CARE_MW = {"reactions": ["Quick reactions; sleep on new signatures", "Sharp replies; wait a day", "Rushed decisions in talks",
                             "Heated words; keep replies short"],
               "spending": ["Extra costs; keep the spending list", "Large buys; let them wait", "Spends that add up quietly",
                            "Lending without paper"]}
    SAT_WATCH = {1: "taking on every duty yourself", 2: "family spends without a plan", 3: "putting off hard calls",
                 4: "home repairs that run over", 5: "plans that stay on paper", 6: "dues left to pile up",
                 7: "slow replies from partners", 8: "shared money left unchecked", 9: "skipping advice from elders",
                 10: "long hours with no rest day", 11: "promises from new contacts", 12: "costs far from home"}
    VEN_WATCH = {1: "spending on looks", 2: "treats that add up", 3: "small buys online", 4: "costly home upgrades",
                 5: "costly outings", 6: "lending to colleagues", 7: "gifts beyond the budget", 8: "joint spends left unsaid",
                 9: "costly trips", 10: "office spends", 11: "costly get-togethers", 12: "late-night shopping"}
    w_use: dict = {}
    prev_w = ""
    for m in MONTH_YMS:
        mm = mon_by.get(m) or {}
        careful_m = mm.get("tone") == "careful"
        tags = [TAG_DO[t] for t in mm.get("tags") or [] if t in TAG_DO and not (careful_m and t == "gold")][:2]
        sun = ch.transit(m, "Sun").get("house") or ch.transit(m, "Venus").get("house")
        do = tags + ([SUN_DO[sun]] if sun and len(tags) < 2 else [])
        if mm.get("tone") == "best" and len(do) < 2 and not no_best:
            do.append("act on your main plans")
        cell = []
        for d_ in do:  # the table cell stays under 8 words (fixed 430x830 card)
            if len(" ".join(cell + [d_]).split()) <= 7 or not cell:
                cell.append(d_)
        out[f"months.{m}.do"] = _cap("; ".join(cell) or "steady daily work")
        cands = list(CARE_MW.get(mm.get("care_reason") or "", []))
        for pl_, tbl in (("Mars", MARS_WATCH), ("Saturn", SAT_WATCH), ("Venus", VEN_WATCH)):
            hh = ch.transit(m, pl_).get("house")
            if hh:
                cands.append(_cap(tbl[hh]))
        cands += ["Taking on too much", "Saying yes too fast", "Skipping the monthly money check", "Late nights before big days"]
        w = next((c for c in cands if w_use.get(c, 0) < 2 and c != prev_w), None) or next(c for c in cands if w_use.get(c, 0) < 2)
        w_use[w] = w_use.get(w, 0) + 1
        prev_w = w
        out[f"months.{m}.watch"] = w

    # ── end plan (overall best / careful times from payload.summary) ─────────
    bpos = lambda: pos([bt["from"]] if bt.get("from") else win(la, "best") or win(la, "good"))
    cushion = {"business": "enough to run the business for six months", "job": "six months of home costs",
               "student": "a small cushion for fees and needs", "home": "six months of home costs"}[work]
    _cp = pos(care_all)
    _pre_c = len([m for m in all_good if care_all and m < care_all[0]])   # good months before the first careful one
    _pc = f" {_cap(cnt(_pre_c, 'good month'))} come first." if _pre_c else " It starts at once."
    put("plan.p1", first_fit(*([f"Build a cushion first. Put aside {cushion} before any new spending; your {cnt(n_care, 'careful month')}, "
                                f"the first {_cp}, are the time to add to it.{_pc}",
                                f"Build a cushion first. Put aside {cushion} before any new spending, and add to it while things are slow, "
                                f"from {_cp}.{_pc}"] if n_care else
                               [f"Build a cushion first. Put aside {cushion} before any new spending, and add to it in each good month, "
                                f"from {pos(all_good[:1])}."])))
    put("plan.p2", f"Plan, don't spend, while spending needs care, {span(sp_m)}. Write the numbers for any large step and "
                   "keep them on paper until that time passes."
        if sp_m else f"Keep spending planned. Write down large costs a month ahead, and keep large buys for your {cnt(len(gold_ok), 'gold month')}, "
                     f"the first {pos(gold_ok or all_good)}.")
    MOVE = {"money": "money move", "career": "career move", "business": "business move",
            "family": "step for the family", "marriage": "shared step with someone close"}
    put("plan.p3", f"Make your main {MOVE[la]} {bpos()}, once the cushion is in place.")
    put("plan.p4", f"Slow down your replies. When quick reactions come easily, {span(rx_m)}, sleep on any sharp message or rushed deal, "
                   f"above all in {rx_life}."
        if rx_m else f"Keep your word small and firm, and answer important messages after a night's sleep, above all in {mars_life}.")
    second = order[1] if len(order) > 1 else "family"
    _g2 = win(second, "good") or win(second, "best")
    _c2 = win(second, "careful")
    _pk2 = (f"hold back {span(_c2)}" if _c2 else "")
    put("plan.p5", f"Give {AREA_NAME[second].lower()} its own plan. Put its steps into its good months, "
                   f"starting {pos(_g2)}" + (f", and {_pk2}." if _pk2 else f", with a review {pos(sorted(_g2)[-1:])}." if len(set(_g2)) > 1 else "."))
    _pre_bt = [m for m in all_good if bt.get("from") and m < bt["from"]]
    _bp1 = bpos()
    put("plan.one", first_fit(f"Put money aside now" + (f", through your first {cnt(len(_pre_bt), 'good month')}," if _pre_bt else "")
                              + f" so you are ready to move when your {bw} comes {_bp1}.",
                              f"Put money aside now" + (f", through your first {cnt(len(_pre_bt), 'good month')}," if _pre_bt else "")
                              + f" so you are ready to move {_bp1}."))
    first_tags = (mon_by.get(MONTH_YMS[0]) or {}).get("tags") or []
    first_care = (mon_by.get(MONTH_YMS[0]) or {}).get("tone") == "careful"
    d30 = [("Open new account books" if work == "business" else "Start a money book")
           + f" this Diwali and note every rupee in and out, above all from {fill['src']}; look back over it {pos(care_all[:1] or all_good[-1:])}.",
           f"This first month is one of your {cnt(len(gold), 'month')} marked for gold: a fine time for a planned buy, if your budget allows."
           if "gold" in first_tags and not first_care
           else (f"Hold large buys for the months marked for gold; the first comes {pos(gold_ok)}." if gold_ok
                 else "Hold large buys until a good month."),
           f"Start {ex['save']}, and raise it {bpos()}." if band != "60p"
           else f"Set up a fixed monthly income plan, and add to it in each good month, starting {pos(all_good[:1])}."]
    put("plan.d30", "\n".join(d30))
    d90 = [f"A good time to clear or restructure a loan comes {pos(loans)}, with {cnt(len(loans), 'month')} marked for loans." if loans
           else f"Pay down the highest-interest loan first, before {pos(care_all or all_good[-1:])}.",
           opt(f"When quick reactions run high, wait a day before you answer",
               f", above all in {rx_life}.", f", {span(rx_m)}, above all in {rx_life}.", f": {cnt(len(rx_m), 'month')} {'call' if len(rx_m) != 1 else 'calls'} for it.", f", {span(rx_m)}.") if rx_m else
           f"Keep replies short and clear in busy weeks, above all in {mars_life}.",
           f"Ask a trusted advisor to check your budget before spending tightens, {pos(sp_m)}." if sp_m
           else f"Review your budget with the family once a month, starting {pos(all_good[:1])}, with {cnt(len(gold_ok), 'gold month')} to plan for."]
    put("plan.d90", "\n".join(d90))
    _after_bt = [m for m in all_good if bt.get("to") and m > bt["to"]]
    d365 = [f"Put your next large buy on paper first, and hold it through your {cnt(len(sp_m), 'month')} of careful spending." if sp_m
            else (f"Plan your next large buy on paper first, and make it in one of the {cnt(len(gold_ok), 'gold month')}, from {pos(gold_ok)}." if gold_ok
                  else "Plan your next large buy on paper first."),
            f"{_cap(bpos())}, take your main {MOVE[la]}.",
            (f"In the {cnt(len(_after_bt), 'good month')} after it, grow with a steady hand and keep your cushion.") if _after_bt else
            f"After it, from {pos([m for m in MONTH_YMS if bt.get('to') and m > bt['to']] or all_good[-1:])}, grow with a steady hand and keep your cushion."]
    put("plan.d365", "\n".join(d365))
    _lg_n = cnt(len(la_good), "good month")
    _lc = win(la, "careful")
    _f1 = (bpos() if bt.get("from") else pos(la_good[:1])) + (f", ahead of the slower months of {SEASON_BARE[_idx(_lc_first[0])]}"
                                                             if (_lc_first := win(la, "careful")[:1]) else
                                                             f" or again {pos(la_good[-1:])}" if len(la_good) > 1 else "")
    FRESH = {"money": [f"If money arrives {_f1}, then I will move a fixed share into savings the same week.",
                       (f"If a large buy comes up {span(_lc)}, then I will wait seven days and move it to a month marked for gold." if _lc else
                        (f"If a large buy comes up on impulse, then I will wait seven days and move it to one of my "
                         f"{cnt(len(gold_ok), 'gold month')}, the first {pos(gold_ok)}." if gold_ok else
                         f"If a large buy comes up on impulse, then I will wait seven days and plan it for a good month, like the one {pos(la_good[1:2] or la_good)}.")),
                       "If a new money offer comes {b}, then I will write down the numbers and ask one trusted advisor before I sign."],
             "career": [f"If a new role or project comes up {_f1}, then I will say yes with a clear plan for the first month.",
                        (f"If I feel like quitting {span(_lc)}, then I will wait one week and talk to two people first." if _lc else
                         "If I feel like quitting in a hard week, then I will wait one week and talk to two people first."),
                        "If a good opening comes {b}, then I will ask for the larger role or the raise, with my results on one page."],
             "business": [f"If a new deal arrives {_f1}, then I will put the terms on paper within two days.",
                          (f"If I want to expand {span(_lc)}, then I will plan it on paper and keep six months of costs in hand first." if _lc else
                           "If I want to expand in a hurry, then I will plan it on paper and keep six months of costs in hand first."),
                          "If the business is ready {b}, then I will make the main move I planned, and review it after one month."],
             "family": [f"If a family event comes up {_f1}, then I will plan it early and keep the guest list simple.",
                        (f"If a hard talk comes up {span(_lc)}, then I will leave it for the next morning." if _lc else
                         "If a hard talk comes up late at night, then I will leave it for the next morning."),
                        f"If a home or property step comes up {pos(la_good[-1:])}, then I will check the papers first and decide together."],
             "marriage": [f"If a good month comes {_f1}, then I will plan one outing with someone close to me.",
                          (f"If words get quick {span(_lc)}, then I will wait a day before deciding anything." if _lc else
                           "If words get quick in a busy week, then I will wait a day before deciding anything."),
                          f"If a large shared choice comes up {pos(la_good[-1:])}, then I will write the numbers down and decide side by side."],
             "luck": [f"If a new month starts, then I will write down last month's money in and out on the 1st, from {pos(all_good[:1])}.",
                      f"If an elder or mentor comes to mind {pos(la_good[-1:])}, then I will call them that week to say thank you.",
                      "If a fresh chance comes {b}, then I will take one small step on it within seven days."]}
    for i, s in enumerate(FRESH[lead_area], 1):
        put(f"plan.fresh.{i}", s.replace("{b}", bpos()))
    put("plan.fresh.when", f"Your good{' and careful' if n_care else ''} times for {AREA_NAME[lead_area].lower()} are on your 12 months; "
                           f"the main one comes {bpos()}.")
    ROLE_W = {"money": "money part", "gains": "gains part", "luck": "luck part", "period": "planet that leads these months", "self": "part for yourself"}
    prs = [x for x in p.get("practices") or [] if x.get("planet")]
    # ONE chart clause: which planet each practice follows and the sign it sits in (per buyer), nothing added
    roles = [(x["planet"], ROLE_W.get(x.get("role"), "chart")) for x in prs[:3]] or \
            [(q, w) for q, w in ((ch.lord(2), "money part"), (ch.lord(9), "luck part")) if q]
    _pl = [f"{_pn(q)}{' in ' + ch.pl(q)['sign'] if ch.pl(q).get('sign') else ''} for your {w}" for q, w in roles]
    put("practices.why", ("These practices follow " + (", ".join(_pl[:-1]) + f" and {_pl[-1]}" if len(_pl) > 1 else _pl[0])
                          + ", so steady habits around counting and giving suit you.") if _pl else
        "These practices follow the rulers of your money and luck parts, so steady habits around counting and giving suit you.")
    LN, SN = AREA_NAME.get(wl, "Money"), AREA_NAME.get(sa, "Money")
    strong_w = "is strongest" if not no_best else "stands out"
    if steer == "luck":
        t1 = f"You picked Better luck, so it leads; by your chart, {SN} {strong_w}"
    elif wl == sa:
        t1 = (f"{LN} leads your report, and by your chart it is also your strongest area" if not no_best
              else f"{LN} leads your report, and by your chart it also stands out")
    elif steer == wl:
        t1 = f"You picked {LN}, so it leads; by your chart, {SN} {strong_w}"
    else:
        t1 = f"Your report opens with {LN}, as fits {WORK_AS[work]}; by your chart, {SN} {strong_w}"
    out["wrapped.lead"] = t1 + "."   # bank-only: the Wrapped card's lead-vs-strongest line (same facts as takeaway 1)
    _nsa = len(set(win(sa, "best") + win(sa, "good")))
    _sg1 = pos(win(sa, "best") + win(sa, "good"))
    put("takeaways.1", opt(t1, *([f", with {cnt(_nsa, 'good month')} for it, from {_sg1}.", f": {cnt(_nsa, 'good month')} back it, from {_sg1}.",
                                  f", from {_sg1}."] if _nsa else [])))
    put("takeaways.2", f"The {md} period, with {ad} as its sub-period, sets the pace: well-made plans can pay off before next Diwali."
        if md and ad else "Your planet period sets the pace: well-made plans can pay off before next Diwali.")
    reasons = {c.get("reason") for c in s_care}
    _crw = " and ".join({"reactions": "quick reactions", "spending": "spending"}.get(c, "care") for c in sorted(reasons - {None}))
    put("takeaways.3", first_fit(f"Your {cnt(n_care, 'careful month')}{', for ' + _crw + ',' if _crw else ''} "
                                 "are short and they end. Each one comes with a step, and a good time follows.",
                                 f"Your slower months{', for ' + _crw + ',' if _crw else ''} are short: {NUM.get(n_care, str(n_care))} in all; "
                                 "they end, each comes with a step, and a good time follows.")
        if s_care else f"Few months need extra care. Build steadily: {n_good} good months are on your side.")
    _p4 = pos([bt['from']] if bt.get('from') else [])
    put("takeaways.4", first_fit(f"Your {bw} comes {_p4}: save before it and act in it.",
                                 f"The main good months come {_p4}: save before them and act in them."))
    _fg = win("family", "good") + win("family", "best")
    _fl = pos(sorted(_fg)[-1:]) if len(set(_fg)) > 1 else ""
    put("takeaways.5", pos(_fg, lambda o: opt(f"Give home and family their own plan, starting {o}",
                                              *[f"; {w}." for w in peak("family")],
                                              *([f"; the last good month for it falls {_fl}."] if _fl else []),
                                              f", in the {cnt(len(set(_fg)), 'good month')} for family.")) if _fg
        else "Give home and family their own plan, and keep it simple.")

    # ── gift + blessing (bank-only; never sent to AI) ────────────────────────
    gift = meta.get("gift") or {}
    giver = (gift.get("giver_name") or "").strip()
    sa_name = AREA_PHRASE.get(sa, "money")
    if gift.get("on"):
        out["gift.title"] = f"A Diwali gift from {giver}" if giver else "A Diwali gift for you"
        out["gift.heading"] = f"A Diwali gift for you, {first}"
        out["gift.message"] = (gift.get("message") or "").strip() or DEFAULT_GIFT_MESSAGE
        out["gift.from"] = giver
        out["gift.wish"] = "May this Diwali fill your home with light, and the months ahead with steady steps."
        out["blessing.title"] = f"From {giver}, with love" if giver else "Chosen with love, for you"
        out["blessing.text"] = (f"{first}, {giver + ' chose' if giver else 'someone who cares about you chose'} this report for you this Diwali, "
                                f"so you can step into the months ahead with a clear plan. May the lamps of this festival light your home, "
                                f"keep your family close, and bring steady rewards to your {sa_name}.")
        out["blessing.sign"] = f"{giver}, through Axtroshastra" if giver else "With love, through Axtroshastra"
    else:
        out["gift.title"] = out["gift.heading"] = out["gift.message"] = out["gift.from"] = out["gift.wish"] = ""
        out["blessing.title"] = "Wishes for the months ahead"   # the eyebrow already says "A Diwali blessing"
        out["blessing.text"] = (f"{first}, may the lamps of this festival light your home, keep your family close, "
                                f"and bring steady rewards to your {sa_name} from this Diwali to the next.")
        out["blessing.sign"] = "Your Axtroshastra family"

    for k, v in out.items():
        if k != "gift.message":
            out[k] = _fix_from(_fix_after_diwali(v))
    _polish_seasons(out, lambda k: k.startswith(("months.", "timeline.", "gift.")) or k.endswith(".title") or k == "wrapped.lead")
    if no_best:  # spec §2 rule 10: a safety net; the texts above already say no best time for such a buyer
        for k, v in out.items():
            if k != "gift.message":
                out[k] = no_best_text(v)
    if band == "60p":
        for k, v in out.items():
            out[k] = v.replace("first job", "next role").replace("first salary", "next income")
    return out
