import re

from diwali_readings_past import PAST, PAST_HEADINGS

BANNED = (
    r"stretch|window|phase|tendency|tended|tends|steadier|notable|favourable|pivotal|culminate|auspicious|"
    r"pressure|karma|dasha|house|bhav|transit|dues|patient|year|astrosage|"
    r"health\w*|stress\w*|worry|worried|calm|relief|remed\w+|cure|doctor|medical|cancer|anxi\w+|heal\w*|"
    r"illness|disease|depress\w*|panic|trauma|therapy|burnout|at your age|energy was low|"
    r"sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu|"
    r"job offer|gold|marriage|wedding|children|death|accident|legal"
)
BANNED_RE = re.compile(r"\b(?:%s)\b" % BANNED, re.I)
EASE = ("help", "helped", "gave advice", "kind", "small gain", "went fine", "support")


def _all():
    return [(w, t, i, p) for w, d in PAST.items() for t, vs in d.items() for i, p in enumerate(vs)]


def _sents(p):
    return [s for s in re.split(r"(?<=\.) ", p.strip()) if s]


def test_structure():
    assert set(PAST) == {"job", "business", "student", "home"}
    for d in PAST.values():
        assert set(d) == {"good", "steady", "careful"}
        for vs in d.values():
            assert len(vs) == 3 and all(isinstance(v, str) for v in vs)
    assert PAST_HEADINGS == {"good": "A good time", "steady": "A mixed time", "careful": "A slower, costlier time"}
    assert len(_all()) == 36


def test_sentences_and_words():
    for w, t, i, p in _all():
        ss = _sents(p)
        assert len(ss) == 7, (w, t, i, len(ss))
        assert all(s.endswith(".") and "." not in s[:-1] for s in ss), (w, t, i)
        for s in ss:
            assert len(s.split()) <= 18, (w, t, i, s)


def test_soft_words_and_banned():
    for w, t, i, p in _all():
        low = p.lower()
        assert low.count("probably") + low.count("may have") <= 1, (w, t, i)
        assert not BANNED_RE.search(p), (w, t, i, BANNED_RE.search(p).group(0))
        assert "–" not in p and "—" not in p


def test_no_repeated_sentence():
    seen = {}
    for w, t, i, p in _all():
        for s in _sents(p):
            assert s not in seen, (s, seen.get(s), (w, t, i))
            seen[s] = (w, t, i)


def test_careful_easing_and_not_gloomy():
    for w, t, i, p in _all():
        if t == "careful":
            assert any(c in p.lower() for c in EASE), (w, i)
            assert "asked more than they gave" not in p.lower()
