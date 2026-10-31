"""Free-preview reading texts, chosen by work type + tone + a small seed.

Data lives in diwali_readings_past.PAST / diwali_readings_future.FUTURE:
    DATA[work_type][tone] = [text1, text2, text3]
Imported lazily; a missing module or key gives a short neutral paragraph, never a crash.
"""
import importlib

_TONE = {"best": "good", "good": "good", "steady": "steady", "careful": "careful"}
_WORK = ("job", "business", "student", "home")
_MOD = {"past": ("diwali_readings_past", "PAST"), "future": ("diwali_readings_future", "FUTURE")}
_FALLBACK = {
    "past": "These two months had their own mix of ups and downs. Some days went smoothly. "
            "Some needed more effort than you expected. You found your way through.",
    "future": "These two months may bring their own mix of ups and downs. Some days are likely to "
              "go smoothly. Others may need a little more effort. Steady choices should help.",
}


def pick(kind, work_type, tone, seed):
    tone = _TONE.get(tone, "steady")
    work_type = work_type if work_type in _WORK else "job"
    try:
        mod, attr = _MOD[kind]
        texts = getattr(importlib.import_module(mod), attr)[work_type][tone]
        return texts[int(seed) % len(texts)]
    except Exception:
        return _FALLBACK.get(kind, _FALLBACK["future"])
