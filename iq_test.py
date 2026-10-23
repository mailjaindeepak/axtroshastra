"""IQ Test — scoring engine.

compute_iq_report() is the single entry point. It takes quiz answers and
demographics, scores them, and returns a report dict in the same shape
every Axtroshastra product uses (product / meta / teaser / full payload).
"""

import math
from datetime import datetime, timezone

from iq_test_questions import (
    QUESTIONS, TOTAL_QUESTIONS, CATEGORY_ORDER, CATEGORY_LABELS,
    CATEGORY_COUNT, IQ_TABLE, CLASSIFICATION_MAP, PERFORMANCE_LABELS,
    PROFILE_TEXT, RECOMMENDATION_MAP, LEARNING_STYLE_MAP,
    DEFAULT_LEARNING_STYLE, STRENGTH_CARDS, GROWTH_CARDS,
)

# ── helpers ──────────────────────────────────────────────────────────────

def _interpolate_iq(raw: int) -> float:
    """Linear interpolation on the IQ_TABLE calibration curve."""
    if raw <= IQ_TABLE[0][0]:
        return float(IQ_TABLE[0][1])
    if raw >= IQ_TABLE[-1][0]:
        return float(IQ_TABLE[-1][1])
    for i in range(len(IQ_TABLE) - 1):
        r0, iq0 = IQ_TABLE[i]
        r1, iq1 = IQ_TABLE[i + 1]
        if r0 <= raw <= r1:
            t = (raw - r0) / (r1 - r0)
            return iq0 + t * (iq1 - iq0)
    return 100.0


def _classify(iq: int) -> str:
    for threshold, label in CLASSIFICATION_MAP:
        if iq >= threshold:
            return label
    return "Below Average"


def _performance_label(pct: float) -> str:
    for threshold, label in PERFORMANCE_LABELS:
        if pct >= threshold:
            return label
    return "Developing"


def _percentile(iq: float, mean: float = 100.0, sd: float = 15.0) -> int:
    """CDF of the normal distribution → percentile (1–99, clamped)."""
    z = (iq - mean) / sd
    p = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return max(1, min(99, round(p * 100)))


def _pick_learning_style(ranked_cats: list[str]) -> dict:
    """Pick learning style from the top-2 scoring categories."""
    if len(ranked_cats) < 2:
        return DEFAULT_LEARNING_STYLE
    key = tuple(sorted(ranked_cats[:2]))
    return LEARNING_STYLE_MAP.get(key, DEFAULT_LEARNING_STYLE)


# ── main entry point ────────────────────────────────────────────────────

def compute_iq_report(
    name: str,
    age: int,
    gender: str | None,
    answers: list[int],
    time_taken_seconds: int,
) -> dict:
    """Score a completed IQ quiz and return the full report payload.

    answers: list of 20 ints (0-3 for chosen option, -1 for unanswered).
    """
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # ── score per category ───────────────────────────────────────────
    cat_correct: dict[str, int] = {c: 0 for c in CATEGORY_ORDER}
    total_correct = 0
    total_wrong = 0

    for i, q in enumerate(QUESTIONS):
        chosen = answers[i] if i < len(answers) else -1
        if chosen == q["correct"]:
            cat_correct[q["category"]] += 1
            total_correct += 1
        elif chosen >= 0:
            total_wrong += 1

    cat_scores = {}
    for cat in CATEGORY_ORDER:
        total = CATEGORY_COUNT[cat]
        correct = cat_correct[cat]
        pct = round(correct / total * 100) if total else 0
        label = _performance_label(pct)
        cat_scores[cat] = {
            "correct": correct,
            "total": total,
            "pct": pct,
            "label": label,
        }

    # ── IQ score: (correct * 4) - wrong ─────────────────────────────
    raw_score = total_correct * 4 - total_wrong
    base_iq = _interpolate_iq(raw_score)

    age_adj = 2 if age <= 20 else (1 if age >= 50 else 0)

    time_adj = 0
    if time_taken_seconds < 120:
        time_adj = 2
    elif time_taken_seconds < 150:
        time_adj = 1

    final_iq = round(base_iq + age_adj + time_adj)
    pctile = _percentile(final_iq)
    classification = _classify(final_iq)

    # ── rank categories for profile generation ───────────────────────
    ranked = sorted(CATEGORY_ORDER,
                    key=lambda c: cat_scores[c]["pct"], reverse=True)
    strengths_cats = [c for c in ranked if cat_scores[c]["pct"] >= 60][:3]
    growth_cats = [c for c in reversed(ranked) if cat_scores[c]["pct"] < 80][:3]

    # highlights for teaser
    highlight_1 = ""
    if strengths_cats:
        top = strengths_cats[0]
        highlight_1 = f"{cat_scores[top]['label']} {CATEGORY_LABELS[top].lower()} skills"

    highlight_2 = ""
    if len(strengths_cats) >= 2:
        sec = strengths_cats[1]
        highlight_2 = f"Strong {CATEGORY_LABELS[sec].lower()}"
    elif total_correct >= 10:
        highlight_2 = "Well-rounded cognitive profile"
    else:
        highlight_2 = "Significant room for growth across areas"

    # ── cognitive strengths ──────────────────────────────────────────
    cognitive_strengths = []
    for cat in strengths_cats:
        card = STRENGTH_CARDS[cat]
        interpretation = PROFILE_TEXT[cat].get(cat_scores[cat]["label"], "")
        cognitive_strengths.append({
            "category": cat,
            "title": card["title"],
            "body": card["body"],
            "interpretation": interpretation,
        })

    # ── growth areas ─────────────────────────────────────────────────
    areas_for_growth = []
    for cat in growth_cats:
        card = GROWTH_CARDS[cat]
        interpretation = PROFILE_TEXT[cat].get(cat_scores[cat]["label"], "")
        tip = RECOMMENDATION_MAP[cat]["growth"]
        areas_for_growth.append({
            "category": cat,
            "title": card["title"],
            "body": card["body"],
            "interpretation": interpretation,
            "tip": tip,
        })

    # ── recommendations ──────────────────────────────────────────────
    recommendations = []
    for cat in ranked:
        key = "strong" if cat_scores[cat]["pct"] >= 60 else "growth"
        recommendations.append({
            "category": cat,
            "label": CATEGORY_LABELS[cat],
            "text": RECOMMENDATION_MAP[cat][key],
        })

    # ── learning style ───────────────────────────────────────────────
    learning_style = _pick_learning_style(ranked)

    # ── assemble ─────────────────────────────────────────────────────
    teaser = {
        "iq_score": final_iq,
        "classification": classification,
        "percentile": pctile,
        "highlight_1": highlight_1,
        "highlight_2": highlight_2,
    }

    return {
        "product": "iq_test",
        "meta": {
            "name": name,
            "age": age,
            "gender": gender or "unspecified",
            "generated": now_str,
        },
        "teaser": teaser,
        "scores": {
            "raw": total_correct,
            "total": TOTAL_QUESTIONS,
            "iq": final_iq,
            "percentile": pctile,
            "classification": classification,
            "time_taken_seconds": time_taken_seconds,
            "age_adjustment": age_adj,
            "time_bonus": time_adj,
            "categories": cat_scores,
        },
        "profile": {
            "cognitive_strengths": cognitive_strengths,
            "areas_for_growth": areas_for_growth,
            "learning_style": learning_style,
            "recommendations": recommendations,
        },
    }
