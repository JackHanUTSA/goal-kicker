from __future__ import annotations

from typing import Any

from src.agent.math_recommender import recommend_math_schools, score_math_school


SUBJECT_CONFIG: dict[str, dict[str, Any]] = {
    "math": {
        "label": "math",
        "subject_bonus_reason": "math mode uses the base structured math-school recommender",
    },
    "cs": {
        "label": "computer science",
        "slug_bonus": {
            "mit": 0.08,
            "stanford": 0.08,
            "uc-berkeley": 0.1,
            "carnegie-mellon": 0.14,
            "caltech": 0.04,
            "georgia-tech": 0.12,
            "uiuc": 0.1,
            "purdue": 0.07,
            "ut-austin": 0.08,
            "uwashington": 0.08,
        },
        "name_keywords": {
            "technology": 0.05,
            "tech": 0.04,
            "engineering": 0.03,
            "computer": 0.04,
        },
        "research_multiplier": 0.05,
        "breadth_multiplier": 0.04,
        "subject_bonus_reason": "cs mode boosts schools with stronger technical/computing signals and broad program depth",
    },
    "physics": {
        "label": "physics",
        "slug_bonus": {
            "mit": 0.1,
            "stanford": 0.07,
            "harvard": 0.05,
            "princeton": 0.08,
            "caltech": 0.16,
            "uchicago": 0.09,
            "uc-berkeley": 0.08,
            "cornell": 0.05,
            "columbia": 0.05,
            "yale": 0.04,
        },
        "name_keywords": {
            "institute of technology": 0.08,
            "technology": 0.04,
            "science": 0.03,
        },
        "research_multiplier": 0.08,
        "breadth_multiplier": 0.02,
        "subject_bonus_reason": "physics mode boosts research-intensive science and technology schools",
    },
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _subject_bonus(record: dict[str, Any], subject: str) -> tuple[float, list[str]]:
    cfg = SUBJECT_CONFIG.get(subject, SUBJECT_CONFIG["math"])
    if subject == "math":
        return 0.0, [cfg["subject_bonus_reason"]]

    slug = str(record.get("slug") or "").lower()
    name = str(record.get("name") or "").lower()
    majors_count = record.get("majors", {}).get("count")
    projects_research = record.get("competitive_signals", {}).get("projects_research", []) or []

    bonus = 0.0
    reasons: list[str] = [cfg["subject_bonus_reason"]]

    slug_bonus = float(cfg.get("slug_bonus", {}).get(slug, 0.0))
    if slug_bonus:
        bonus += slug_bonus
        reasons.append(f"{subject} bonus applied for a school with a strong heuristic {subject} reputation")

    keyword_bonus = 0.0
    for keyword, value in cfg.get("name_keywords", {}).items():
        if keyword in name:
            keyword_bonus += float(value)
    if keyword_bonus:
        bonus += keyword_bonus
        reasons.append(f"{subject} bonus applied from school-name technical/science keywords")

    if majors_count is not None:
        breadth_bonus = min(float(majors_count) / 160.0, 1.0) * float(cfg.get("breadth_multiplier", 0.0))
        bonus += breadth_bonus
        if breadth_bonus:
            reasons.append(f"{subject} bonus applied for broad academic/program depth")

    if projects_research:
        research_bonus = min(len(projects_research) / 4.0, 1.0) * float(cfg.get("research_multiplier", 0.0))
        bonus += research_bonus
        if research_bonus:
            reasons.append(f"{subject} bonus applied for research/project signals in the current record")

    return bonus, reasons


def score_subject_school(record: dict[str, Any], profile: dict[str, Any], subject: str = "math") -> dict[str, Any]:
    if subject == "math":
        scored = score_math_school(record, profile)
        scored["subject"] = "math"
        scored["subject_bonus"] = 0.0
        scored["reasons"] = scored.get("reasons", []) + [SUBJECT_CONFIG["math"]["subject_bonus_reason"]]
        return scored

    scored = score_math_school(record, profile)
    bonus, subject_reasons = _subject_bonus(record, subject)
    scored["fit_score"] = round(_clamp(float(scored["fit_score"]) + bonus), 4)
    scored["subject"] = subject
    scored["subject_bonus"] = round(bonus, 4)
    scored["reasons"] = subject_reasons + scored.get("reasons", [])
    return scored


def recommend_subject_schools(
    records: list[dict[str, Any]],
    profile: dict[str, Any],
    *,
    subject: str = "math",
    top_n: int = 5,
    include_placeholder: bool = False,
) -> list[dict[str, Any]]:
    if subject == "math":
        base = recommend_math_schools(records, profile, top_n=top_n, include_placeholder=include_placeholder)
        for row in base:
            row["subject"] = "math"
            row["subject_bonus"] = 0.0
            row["reasons"] = row.get("reasons", []) + [SUBJECT_CONFIG["math"]["subject_bonus_reason"]]
        return base

    ranked = []
    for record in records:
        if not include_placeholder and str(record.get("verification", {}).get("confidence") or "").lower() == "placeholder":
            continue
        ranked.append(score_subject_school(record, profile, subject))
    ranked.sort(key=lambda row: (-row["fit_score"], row.get("rank") or 999, row.get("name") or ""))
    return ranked[:top_n]
