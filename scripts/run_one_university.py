#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.run_one_university import run_one_university


def main() -> int:
    parser = argparse.ArgumentParser(description="Create scaffold knowledgebase files for one university")
    parser.add_argument("--school", required=True, help="School name, short name, or slug")
    args = parser.parse_args()

    result = run_one_university(args.school)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
