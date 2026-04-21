#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.student_profiles import preset_student_profiles  # noqa: E402


def main() -> int:
    print(json.dumps({"profiles": preset_student_profiles()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
