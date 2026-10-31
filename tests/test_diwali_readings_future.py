import re

from diwali_readings_future import FUTURE

WORK = ("job", "business", "student", "home")
TONES = ("good", "steady", "careful")
ALL = [(w, t, i, p) for w in WORK for t in TONES for i, p in enumerate(FUTURE[w][t])]
BANNED = (
    "stretch window phase tendency tended tends steadier notable favourable pivotal culminate "
    "auspicious pressure karma dasha house bhav transit dues patient year sun moon mars mercury "
    "jupiter venus saturn rahu ketu astrosage health stress worry calm relief remedy cure doctor "
    "medical cancer anxiety heal illness disease depress panic trauma therapy burnout"
).split()
MONTHS = ("january february march april june july august september october november december "
          "jan feb mar apr jun jul aug sep sept oct nov dec").split()


def sentences(p):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", p.strip()) if s.strip()]


def test_structure():
    assert set(FUTURE) == set(WORK)
    for w in WORK:
        assert set(FUTURE[w]) == set(TONES)
        assert all(len(FUTURE[w][t]) == 3 for t in TONES)
    assert len(ALL) == 36


def test_sentences():
    for w, t, i, p in ALL:
        ss = sentences(p)
        assert len(ss) == 7, (w, t, i, len(ss))
        for s in ss:
            assert len(s.split()) <= 18, (w, t, i, s)


def test_words():
    for w, t, i, p in ALL:
        low = p.lower()
        assert "will " not in low and "probably" not in low, (w, t, i)
        assert "—" not in p and "–" not in p and " - " not in p
        words = set(re.findall(r"[a-z]+", low))
        assert not words & set(BANNED), (w, t, i, words & set(BANNED))
        assert not re.search(r"\d", p), (w, t, i)
        assert not words & set(MONTHS), (w, t, i)


def test_no_repeated_sentence():
    seen = {}
    for w, t, i, p in ALL:
        for s in sentences(p):
            assert s not in seen, (s, seen.get(s), (w, t, i))
            seen[s] = (w, t, i)


def test_careful_easing_and_ending():
    for w in WORK:
        for i, p in enumerate(FUTURE[w]["careful"]):
            ss = sentences(p)
            body = " ".join(ss[1:-1]).lower()
            assert re.search(r"elder|small gain|friend|support|lend a hand|helping hand|help|neighbour", body), (w, i)
            assert re.search(r"handled|managed|get through", ss[-1]), (w, i)
            assert not re.search(r"\b(bad|worst|terrible|gloom)", p.lower())
