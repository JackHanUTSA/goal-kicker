from __future__ import annotations

from typing import Any


def _clamp_unit(value: float | None, *, allow_none: bool = False) -> float | None:
    if value is None:
        if allow_none:
            return None
        raise ValueError("value cannot be None")
    value = float(value)
    if value < 0.0 or value > 1.0:
        raise ValueError(f"value must be between 0 and 1, got {value}")
    return value


def build_profile(
    *,
    slug: str,
    name: str,
    gpa_strength: float,
    course_rigor: float,
    research_interest: float,
    leadership: float,
    prefers_test_optional: bool,
    test_strength: float | None = None,
    notes: str = "",
    target_competitiveness: float = 0.85,
    needs_large_math_program: bool = True,
) -> dict[str, Any]:
    return {
        "slug": slug,
        "name": name,
        "gpa_strength": _clamp_unit(gpa_strength),
        "course_rigor": _clamp_unit(course_rigor),
        "research_interest": _clamp_unit(research_interest),
        "leadership": _clamp_unit(leadership),
        "prefers_test_optional": bool(prefers_test_optional),
        "test_strength": _clamp_unit(test_strength, allow_none=True),
        "target_competitiveness": _clamp_unit(target_competitiveness),
        "needs_large_math_program": bool(needs_large_math_program),
        "notes": notes,
    }


def preset_student_profiles() -> list[dict[str, Any]]:
    return [
        build_profile(
            slug="elite-math-researcher",
            name="Elite math researcher",
            gpa_strength=0.99,
            test_strength=0.98,
            course_rigor=0.98,
            research_interest=1.0,
            leadership=0.72,
            prefers_test_optional=False,
            target_competitiveness=0.98,
            needs_large_math_program=True,
            notes="Ideal for highly selective math and theory-heavy schools with strong research culture.",
        ),
        build_profile(
            slug="high-achieving-test-optional",
            name="High-achieving test-optional student",
            gpa_strength=0.96,
            test_strength=None,
            course_rigor=0.93,
            research_interest=0.74,
            leadership=0.7,
            prefers_test_optional=True,
            target_competitiveness=0.9,
            needs_large_math_program=True,
            notes="Strong student who wants top schools without relying on SAT/ACT submission.",
        ),
        build_profile(
            slug="balanced-builder",
            name="Balanced builder",
            gpa_strength=0.92,
            test_strength=0.84,
            course_rigor=0.9,
            research_interest=0.82,
            leadership=0.86,
            prefers_test_optional=False,
            target_competitiveness=0.82,
            needs_large_math_program=True,
            notes="Strong academic with projects, leadership, and solid testing.",
        ),
        build_profile(
            slug="research-forward-collaborator",
            name="Research-forward collaborator",
            gpa_strength=0.94,
            test_strength=0.88,
            course_rigor=0.95,
            research_interest=0.95,
            leadership=0.62,
            prefers_test_optional=False,
            target_competitiveness=0.9,
            needs_large_math_program=False,
            notes="Best for students who care more about research opportunity than breadth alone.",
        ),
        build_profile(
            slug="strong-generalist-math",
            name="Strong generalist for math",
            gpa_strength=0.9,
            test_strength=0.82,
            course_rigor=0.88,
            research_interest=0.68,
            leadership=0.78,
            prefers_test_optional=True,
            target_competitiveness=0.78,
            needs_large_math_program=True,
            notes="Qualified student looking for strong math options with a balanced admissions fit.",
        ),
    ]
