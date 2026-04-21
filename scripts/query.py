#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.query import (  # noqa: E402
    admissions_policy_summary,
    compare_records,
    load_records,
    majors_by_school,
    project_research_emphasis,
    summarize_record,
    find_record,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 5 query layer for Goal Kicker")
    sub = parser.add_subparsers(dest="command", required=True)

    show = sub.add_parser("show", help="Show one school summary")
    show.add_argument("school")

    majors = sub.add_parser("majors", help="List majors counts by school")
    majors.add_argument("--top", type=int, default=None, help="limit output rows")

    sub.add_parser("projects", help="Rank schools by project/research signals")
    sub.add_parser("policies", help="Show testing/GPA/course-rigor summaries")

    compare = sub.add_parser("compare", help="Compare 2-3 schools side by side")
    compare.add_argument("schools", nargs="+", help="two or three schools")

    args = parser.parse_args()
    records = load_records()

    if args.command == "show":
        print(json.dumps(summarize_record(find_record(records, args.school)), indent=2))
    elif args.command == "majors":
        rows = majors_by_school(records)
        if args.top is not None:
            rows = rows[: args.top]
        print(json.dumps(rows, indent=2))
    elif args.command == "projects":
        print(json.dumps(project_research_emphasis(records), indent=2))
    elif args.command == "policies":
        print(json.dumps(admissions_policy_summary(records), indent=2))
    elif args.command == "compare":
        if not 2 <= len(args.schools) <= 3:
            raise SystemExit("compare requires 2 or 3 schools")
        print(json.dumps(compare_records(records, args.schools), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
