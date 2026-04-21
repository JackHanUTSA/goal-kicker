#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.run_batch import run_batch  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Goal Kicker batch ingestion with resumable progress tracking")
    parser.add_argument("--start-rank", type=int, default=None, help="start processing at this ranking position")
    parser.add_argument("--limit", type=int, default=None, help="maximum number of schools to process")
    parser.add_argument("--refresh", action="store_true", help="re-run even if outputs already exist")
    parser.add_argument("--school", action="append", default=None, help="specific school slug/name/short_name; may be repeated")
    args = parser.parse_args()

    results = run_batch(
        start_rank=args.start_rank,
        limit=args.limit,
        refresh=args.refresh,
        school_names=args.school,
    )
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
