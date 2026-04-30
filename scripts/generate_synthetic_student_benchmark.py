#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.math_recommender import recommend_math_schools  # noqa: E402
from src.agent.query import load_records  # noqa: E402
from src.agent.student_profiles import build_profile  # noqa: E402

DEFAULT_OUTPUT = ROOT.parent / "second-brain-demo" / "public" / "goal-kicker-student-benchmark.json"

ARCHETYPES: list[dict[str, Any]] = [
    {
        "slug": "pure-math",
        "label": "Pure Mathematics",
        "majors": ["Mathematics", "Pure Mathematics", "Number Theory", "Algebra", "Topology"],
        "interest_tags": ["proofs", "abstract reasoning", "olympiad style", "theory"],
        "learning_styles": ["independent", "seminar-heavy", "research-first"],
        "notes": "Wants rigorous proof-based math with strong theory depth.",
        "bases": {"gpa": 0.95, "rigor": 0.95, "research": 0.88, "leadership": 0.58, "test": 0.90, "target": 0.91},
        "large_program_bias": 0.55,
        "optional_bias": 0.28,
    },
    {
        "slug": "applied-math",
        "label": "Applied Mathematics",
        "majors": ["Applied Mathematics", "Computational Mathematics", "Mathematical Modeling", "Industrial Mathematics"],
        "interest_tags": ["modeling", "simulation", "optimization", "real-world systems"],
        "learning_styles": ["project-based", "collaborative", "lab-adjacent"],
        "notes": "Prefers modeling-heavy math linked to engineering and science problems.",
        "bases": {"gpa": 0.91, "rigor": 0.90, "research": 0.72, "leadership": 0.63, "test": 0.83, "target": 0.80},
        "large_program_bias": 0.74,
        "optional_bias": 0.42,
    },
    {
        "slug": "statistics",
        "label": "Statistics",
        "majors": ["Statistics", "Statistical Science", "Probability", "Biostatistics"],
        "interest_tags": ["inference", "uncertainty", "experiments", "quantitative reasoning"],
        "learning_styles": ["collaborative", "research-first", "data-heavy"],
        "notes": "Interested in statistical inference, probability, and modern data analysis.",
        "bases": {"gpa": 0.90, "rigor": 0.89, "research": 0.76, "leadership": 0.66, "test": 0.82, "target": 0.79},
        "large_program_bias": 0.68,
        "optional_bias": 0.49,
    },
    {
        "slug": "data-science",
        "label": "Data Science",
        "majors": ["Data Science", "Computational Data Science", "Machine Learning", "Analytics"],
        "interest_tags": ["data", "machine learning", "coding", "visualization"],
        "learning_styles": ["project-based", "hackathon", "startup-oriented"],
        "notes": "Wants a quantitative path blending math, statistics, and coding.",
        "bases": {"gpa": 0.89, "rigor": 0.88, "research": 0.71, "leadership": 0.72, "test": 0.80, "target": 0.76},
        "large_program_bias": 0.82,
        "optional_bias": 0.58,
    },
    {
        "slug": "cs-theory",
        "label": "CS Theory",
        "majors": ["Computer Science", "Theory of Computation", "Algorithms", "Discrete Mathematics"],
        "interest_tags": ["algorithms", "proofs", "complexity", "systems thinking"],
        "learning_styles": ["fast-paced", "competition", "research-first"],
        "notes": "Likes the proof and algorithm side of computing more than product building.",
        "bases": {"gpa": 0.94, "rigor": 0.95, "research": 0.84, "leadership": 0.64, "test": 0.92, "target": 0.90},
        "large_program_bias": 0.61,
        "optional_bias": 0.26,
    },
    {
        "slug": "quant-econ",
        "label": "Quantitative Economics",
        "majors": ["Economics", "Mathematical Economics", "Econometrics", "Quantitative Social Science"],
        "interest_tags": ["markets", "policy", "modeling", "analytics"],
        "learning_styles": ["discussion-heavy", "applied", "cross-disciplinary"],
        "notes": "Wants math-backed economics with room for policy, finance, or research.",
        "bases": {"gpa": 0.90, "rigor": 0.88, "research": 0.69, "leadership": 0.74, "test": 0.84, "target": 0.77},
        "large_program_bias": 0.66,
        "optional_bias": 0.50,
    },
    {
        "slug": "physics",
        "label": "Mathematical Physics",
        "majors": ["Physics", "Mathematical Physics", "Astrophysics", "Applied Physics"],
        "interest_tags": ["theory", "problem solving", "science", "modeling"],
        "learning_styles": ["research-first", "lab-adjacent", "small-group"],
        "notes": "Drawn to math-rich physics and research environments.",
        "bases": {"gpa": 0.93, "rigor": 0.94, "research": 0.86, "leadership": 0.57, "test": 0.89, "target": 0.86},
        "large_program_bias": 0.52,
        "optional_bias": 0.31,
    },
    {
        "slug": "operations-research",
        "label": "Operations Research",
        "majors": ["Operations Research", "Decision Science", "Optimization", "Systems Engineering"],
        "interest_tags": ["optimization", "logistics", "decision making", "analytics"],
        "learning_styles": ["project-based", "case-based", "industry-facing"],
        "notes": "Interested in optimization, systems, and high-impact quantitative decision making.",
        "bases": {"gpa": 0.88, "rigor": 0.87, "research": 0.67, "leadership": 0.77, "test": 0.79, "target": 0.73},
        "large_program_bias": 0.79,
        "optional_bias": 0.55,
    },
    {
        "slug": "computational-biology",
        "label": "Computational Biology",
        "majors": ["Computational Biology", "Bioinformatics", "Systems Biology", "Quantitative Biology"],
        "interest_tags": ["biology", "coding", "research", "data"],
        "learning_styles": ["lab-adjacent", "research-first", "interdisciplinary"],
        "notes": "Wants an interdisciplinary major using math and computation to study biology.",
        "bases": {"gpa": 0.91, "rigor": 0.90, "research": 0.90, "leadership": 0.62, "test": 0.81, "target": 0.78},
        "large_program_bias": 0.64,
        "optional_bias": 0.44,
    },
    {
        "slug": "engineering-math",
        "label": "Engineering + Math",
        "majors": ["Engineering Mathematics", "Electrical Engineering", "Mechanical Engineering", "Robotics"],
        "interest_tags": ["engineering", "design", "quantitative problem solving", "building"],
        "learning_styles": ["hands-on", "team-based", "design-build"],
        "notes": "Likes mathematically strong engineering programs with room for building projects.",
        "bases": {"gpa": 0.89, "rigor": 0.91, "research": 0.70, "leadership": 0.76, "test": 0.85, "target": 0.79},
        "large_program_bias": 0.83,
        "optional_bias": 0.40,
    },
]

REGIONS = ["Northeast", "Midwest", "South", "West", "International applicant from Asia", "International applicant from Europe"]
AID_NEED = ["low", "medium", "high"]
RISK_TOLERANCE = ["balanced", "reach-heavy", "match-heavy"]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _vary(rng: random.Random, base: float, spread: float) -> float:
    return round(_clamp(base + rng.uniform(-spread, spread)), 2)


def _generate_profile(index: int, archetype: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    bases = archetype["bases"]
    no_test = rng.random() < archetype["optional_bias"] * 0.45
    prefers_optional = no_test or (rng.random() < archetype["optional_bias"])
    test_strength = None if no_test else _vary(rng, bases["test"], 0.12)
    intended_major = rng.choice(archetype["majors"])
    secondary_interest = rng.choice([tag for tag in archetype["interest_tags"] if tag not in intended_major.lower()])
    learning_style = rng.choice(archetype["learning_styles"])
    region = rng.choice(REGIONS)
    aid_need = rng.choice(AID_NEED)
    risk_tolerance = rng.choice(RISK_TOLERANCE)
    first_gen = rng.random() < 0.22
    international = region.startswith("International")
    needs_large = rng.random() < archetype["large_program_bias"]

    profile = build_profile(
        slug=f"synthetic-{index:03d}",
        name=f"Student {index:03d}",
        gpa_strength=_vary(rng, bases["gpa"], 0.08),
        course_rigor=_vary(rng, bases["rigor"], 0.08),
        research_interest=_vary(rng, bases["research"], 0.16),
        leadership=_vary(rng, bases["leadership"], 0.18),
        prefers_test_optional=prefers_optional,
        test_strength=test_strength,
        target_competitiveness=_vary(rng, bases["target"], 0.12),
        needs_large_math_program=needs_large,
        notes=(
            f"Synthetic benchmark student for {archetype['label']}. "
            f"Intended major: {intended_major}. Secondary interest: {secondary_interest}. "
            f"Learning style: {learning_style}."
        ),
    )
    return {
        "student_id": f"student-{index:03d}",
        "archetype": archetype["slug"],
        "archetype_label": archetype["label"],
        "intended_major": intended_major,
        "secondary_interest": secondary_interest,
        "interest_tags": archetype["interest_tags"],
        "learning_style": learning_style,
        "region": region,
        "financial_aid_need": aid_need,
        "risk_tolerance": risk_tolerance,
        "first_generation": first_gen,
        "international": international,
        "profile": profile,
    }


def build_benchmark(count: int = 100, seed: int = 42, top_n: int = 5) -> dict[str, Any]:
    rng = random.Random(seed)
    records = load_records()
    students: list[dict[str, Any]] = []
    top_school_counter: Counter[str] = Counter()
    archetype_counter: Counter[str] = Counter()
    school_hits_by_archetype: dict[str, Counter[str]] = defaultdict(Counter)

    for index in range(1, count + 1):
        archetype = ARCHETYPES[(index - 1) % len(ARCHETYPES)]
        student = _generate_profile(index, archetype, rng)
        recommendations = recommend_math_schools(records, student["profile"], top_n=top_n, include_placeholder=False)
        top_school = recommendations[0]["name"] if recommendations else None
        if top_school:
            top_school_counter[top_school] += 1
            school_hits_by_archetype[student["archetype_label"]][top_school] += 1
        archetype_counter[student["archetype_label"]] += 1
        student["recommendations"] = recommendations
        student["top_recommendation"] = recommendations[0] if recommendations else None
        students.append(student)

    summary = {
        "student_count": len(students),
        "archetype_counts": dict(archetype_counter),
        "top_first_choice_schools": [
            {"school": school, "count": count}
            for school, count in top_school_counter.most_common(12)
        ],
        "top_school_by_archetype": {
            archetype: [{"school": school, "count": count} for school, count in counter.most_common(5)]
            for archetype, counter in sorted(school_hits_by_archetype.items())
        },
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "generate_synthetic_student_benchmark.py",
        "seed": seed,
        "top_n": top_n,
        "description": "Synthetic benchmark set of 100 students with different intended-major interests for Goal Kicker evaluation.",
        "major_interest_families": [
            {
                "slug": archetype["slug"],
                "label": archetype["label"],
                "sample_majors": archetype["majors"],
                "notes": archetype["notes"],
            }
            for archetype in ARCHETYPES
        ],
        "summary": summary,
        "students": students,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a synthetic Goal Kicker benchmark with 100 students and recommendations.")
    parser.add_argument("--count", type=int, default=100, help="number of students to generate")
    parser.add_argument("--seed", type=int, default=42, help="deterministic random seed")
    parser.add_argument("--top", type=int, default=5, help="top recommendations per student")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="output JSON path")
    args = parser.parse_args()

    benchmark = build_benchmark(count=args.count, seed=args.seed, top_n=args.top)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(benchmark, indent=2), encoding="utf-8")
    print(json.dumps({
        "written": str(args.output),
        "student_count": benchmark["summary"]["student_count"],
        "top_first_choice_schools": benchmark["summary"]["top_first_choice_schools"][:5],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
