from __future__ import annotations

from typing import Any


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _normalize_rank(rank: int | None) -> float:
    if rank is None:
        return 0.35
    if rank <= 1:
        return 1.0
    return _clamp(1.0 - ((rank - 1) / 99.0))


def _normalize_majors_count(value: int | None) -> float:
    if value is None:
        return 0.25
    return _clamp(value / 120.0)


def _projects_score(record: dict[str, Any]) -> float:
    signals = record.get("competitive_signals", {}).get("projects_research", []) or []
    return _clamp(len(signals) / 3.0)


def _testing_category(policy: str | None) -> str:
    text = str(policy or "unknown").lower()
    if text == "unknown" or not text.strip():
        return "unknown"
    if "test-optional" in text or "no harm" in text:
        return "optional"
    if "test-flexible" in text:
        return "flexible"
    if "does not require sat/act" in text or "does not require sat" in text or "does not require act" in text:
        return "optional"
    if "require" in text and "not require" not in text and "optional" not in text:
        return "required"
    return "unknown"


def _testing_fit(record: dict[str, Any], profile: dict[str, Any]) -> tuple[float, str]:
    category = _testing_category(record.get("admissions", {}).get("testing_policy"))
    test_strength = profile.get("test_strength")
    prefers_optional = bool(profile.get("prefers_test_optional"))

    if category == "required":
        if test_strength is None:
            return -0.55, "penalized because the school currently requires testing and this student has no test profile"
        return 0.08 + (0.16 * float(test_strength)), "boosted because the student can satisfy the current testing requirement"
    if category == "optional":
        if prefers_optional:
            return 0.22, "boosted because the school is test-optional and the student prefers that path"
        if test_strength is not None:
            return 0.1 + (0.05 * float(test_strength)), "slightly boosted because testing is optional and the student can still submit strong scores"
        return 0.12, "slightly boosted because testing is optional"
    if category == "flexible":
        if test_strength is None:
            return -0.12, "slightly penalized because the school still expects some form of testing evidence"
        return 0.12, "boosted because the student can use a flexible testing policy"
    if prefers_optional:
        return -0.05, "slightly penalized because the testing policy is unclear for a test-optional preference"
    return 0.0, "neutral because the testing policy is unclear"


def _confidence_penalty(record: dict[str, Any]) -> tuple[float, str]:
    verification = record.get("verification", {})
    confidence = str(verification.get("confidence") or "").lower()
    unknowns = len(verification.get("unknown_fields", []) or [])
    warnings = len(verification.get("warnings", []) or [])
    penalty = (0.03 * unknowns) + (0.015 * warnings)
    if confidence == "placeholder":
        penalty += 0.45
        return penalty, "heavy penalty because this school is still a placeholder record"
    if unknowns:
        return penalty, "penalized for unresolved unknown fields in the current record"
    return penalty, "minimal penalty because the record is relatively complete"


def _math_focus_signal(record: dict[str, Any]) -> float:
    name = str(record.get("name") or "").lower()
    slug = str(record.get("slug") or "").lower()
    bonus = 0.0
    if "institute of technology" in name or slug in {"mit", "caltech", "georgia-tech"}:
        bonus += 0.2
    if "technology" in name:
        bonus += 0.08
    return _clamp(bonus)


def _student_strength(profile: dict[str, Any]) -> float:
    test_strength = profile.get("test_strength")
    testing_component = 0.75 if test_strength is None else float(test_strength)
    return _clamp(
        (0.35 * float(profile.get("gpa_strength", 0.0)))
        + (0.3 * float(profile.get("course_rigor", 0.0)))
        + (0.2 * testing_component)
        + (0.15 * float(profile.get("research_interest", 0.0)))
    )


def score_math_school(record: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    rank_score = _normalize_rank(record.get("rank"))
    majors_score = _normalize_majors_count(record.get("majors", {}).get("count"))
    projects_score = _projects_score(record)
    math_focus = _math_focus_signal(record)
    student_strength = _student_strength(profile)
    target = float(profile.get("target_competitiveness", 0.8))
    competitiveness_fit = 1.0 - abs(student_strength - rank_score)
    testing_fit, testing_reason = _testing_fit(record, profile)
    penalty, penalty_reason = _confidence_penalty(record)

    score = (
        0.3 * rank_score
        + 0.16 * competitiveness_fit
        + 0.14 * majors_score
        + 0.12 * (projects_score * float(profile.get("research_interest", 0.0)))
        + 0.16 * math_focus
        + 0.06 * float(profile.get("leadership", 0.0))
        + testing_fit
    )

    if profile.get("needs_large_math_program"):
        score += 0.1 * majors_score
    if student_strength + 0.08 < rank_score:
        score -= 0.14
    if abs(target - rank_score) < 0.12:
        score += 0.06

    score -= penalty
    score = _clamp(score)

    return {
        "name": record.get("name"),
        "short_name": record.get("short_name"),
        "slug": record.get("slug"),
        "rank": record.get("rank"),
        "fit_score": round(score, 4),
        "math_focus_signal": round(math_focus, 4),
        "competition_score": round(rank_score, 4),
        "majors_score": round(majors_score, 4),
        "projects_score": round(projects_score, 4),
        "student_strength": round(student_strength, 4),
        "testing_category": _testing_category(record.get("admissions", {}).get("testing_policy")),
        "reasons": [
            testing_reason,
            penalty_reason,
            f"competition fit score={competitiveness_fit:.2f} based on student strength versus school selectivity",
        ],
        "record_confidence": record.get("verification", {}).get("confidence"),
        "unknown_fields": record.get("verification", {}).get("unknown_fields", []),
        "warnings": record.get("verification", {}).get("warnings", []),
        "testing_policy": record.get("admissions", {}).get("testing_policy"),
        "majors_count": record.get("majors", {}).get("count"),
    }


def recommend_math_schools(records: list[dict[str, Any]], profile: dict[str, Any], top_n: int = 5, include_placeholder: bool = False) -> list[dict[str, Any]]:
    ranked = []
    for record in records:
        if not include_placeholder and str(record.get("verification", {}).get("confidence") or "").lower() == "placeholder":
            continue
        ranked.append(score_math_school(record, profile))
    ranked.sort(key=lambda row: (-row["fit_score"], row.get("rank") or 999, row.get("name") or ""))
    return ranked[:top_n]
