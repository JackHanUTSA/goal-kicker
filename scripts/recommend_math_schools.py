#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.math_recommender import recommend_math_schools  # noqa: E402
from src.agent.query import load_records  # noqa: E402
from src.agent.student_profiles import build_profile, preset_student_profiles  # noqa: E402


def _profile_by_slug(slug: str) -> dict:
    for profile in preset_student_profiles():
        if profile["slug"] == slug:
            return profile
    raise ValueError(f"Unknown profile slug: {slug}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Recommend best-fit math schools for a student profile")
    parser.add_argument("--profile", default="elite-math-researcher", help="preset profile slug")
    parser.add_argument("--top", type=int, default=5, help="number of recommendations")
    parser.add_argument("--include-placeholder", action="store_true", help="include placeholder school records")
    parser.add_argument("--gpa-strength", type=float)
    parser.add_argument("--test-strength", type=float)
    parser.add_argument("--course-rigor", type=float)
    parser.add_argument("--research-interest", type=float)
    parser.add_argument("--leadership", type=float)
    parser.add_argument("--prefers-test-optional", action="store_true")
    parser.add_argument("--target-competitiveness", type=float)
    args = parser.parse_args()

    if any(value is not None for value in [args.gpa_strength, args.test_strength, args.course_rigor, args.research_interest, args.leadership, args.target_competitiveness]) or args.prefers_test_optional:
        base = _profile_by_slug(args.profile)
        profile = build_profile(
            slug="custom-profile",
            name=f"Custom based on {base['name']}",
            gpa_strength=args.gpa_strength if args.gpa_strength is not None else base["gpa_strength"],
            test_strength=args.test_strength if args.test_strength is not None else base["test_strength"],
            course_rigor=args.course_rigor if args.course_rigor is not None else base["course_rigor"],
            research_interest=args.research_interest if args.research_interest is not None else base["research_interest"],
            leadership=args.leadership if args.leadership is not None else base["leadership"],
            prefers_test_optional=args.prefers_test_optional or base["prefers_test_optional"],
            target_competitiveness=args.target_competitiveness if args.target_competitiveness is not None else base["target_competitiveness"],
            notes="customized from CLI",
            needs_large_math_program=base["needs_large_math_program"],
        )
    else:
        profile = _profile_by_slug(args.profile)

    recommendations = recommend_math_schools(load_records(), profile, top_n=args.top, include_placeholder=args.include_placeholder)
    print(json.dumps({"profile": profile, "recommendations": recommendations}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
