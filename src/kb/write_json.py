from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "knowledgebase" / "universities"


def write_university_json(record: dict[str, Any]) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{record['slug']}.json"
    path.write_text(json.dumps(record, indent=2))
    return path
