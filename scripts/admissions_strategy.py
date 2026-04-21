#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.admissions_strategy import admissions_landscape_2026, build_admissions_strategy  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Goal Kicker admissions strategy knowledge layer")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("landscape", help="Show the shared 2026 admissions landscape knowledge")

    plan = sub.add_parser("plan", help="Build a simple student admissions strategy")
    plan.add_argument("--round", default="regular-decision", choices=["early-decision", "early-action", "regular-decision"])
    plan.add_argument("--testing", default="unclear", choices=["required", "test-optional", "test-flexible", "unclear"])
    plan.add_argument("--aid", action="store_true", help="student needs to compare or maximize financial aid")
    plan.add_argument("--region", default="domestic", choices=["domestic", "international"])

    args = parser.parse_args()

    if args.command == "landscape":
        print(json.dumps(admissions_landscape_2026(), indent=2))
    elif args.command == "plan":
        print(
            json.dumps(
                build_admissions_strategy(
                    application_round=args.round,
                    testing_category=args.testing,
                    needs_financial_aid=args.aid,
                    student_region=args.region,
                ),
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
