#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.fit_summary import build_fit_summary_for_school  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an applicant-fit summary for one Goal Kicker school")
    parser.add_argument("school", help="school slug, short name, or full name")
    args = parser.parse_args()

    summary = build_fit_summary_for_school(args.school)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
