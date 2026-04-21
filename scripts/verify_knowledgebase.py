#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.verify_record import verify_record_file  # noqa: E402

UNI_DIR = ROOT / "knowledgebase" / "universities"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Goal Kicker university records for missing critical fields")
    parser.add_argument("--school", action="append", default=None, help="verify only these school slugs")
    args = parser.parse_args()

    paths = sorted(UNI_DIR.glob("*.json"))
    if args.school:
        wanted = {item.strip().lower() for item in args.school}
        paths = [path for path in paths if path.stem.lower() in wanted]

    results = [verify_record_file(path) for path in paths]
    summary = {
        "total": len(results),
        "pass": sum(1 for r in results if r["status"] == "pass"),
        "fail": sum(1 for r in results if r["status"] == "fail"),
    }
    print(json.dumps({"summary": summary, "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
