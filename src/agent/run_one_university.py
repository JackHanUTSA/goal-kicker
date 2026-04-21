from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.discovery.find_sources import guess_official_urls
from src.kb.write_json import write_university_json
from src.kb.write_markdown import write_university_markdown
from src.normalize.university_record import build_placeholder_record


ROOT = Path(__file__).resolve().parents[2]
SEEDS_PATH = ROOT / "data" / "top50_universities.json"


def load_seeds() -> list[dict[str, Any]]:
    return json.loads(SEEDS_PATH.read_text())


def find_seed(name_or_slug: str) -> dict[str, Any]:
    query = name_or_slug.strip().lower()
    for seed in load_seeds():
        if query in {seed["slug"].lower(), seed["name"].lower(), seed["short_name"].lower()}:
            return seed
    raise ValueError(f"University not found in seed list: {name_or_slug}")


def run_one_university(name_or_slug: str) -> dict[str, str]:
    seed = find_seed(name_or_slug)
    sources = guess_official_urls(seed)
    record = build_placeholder_record(seed, sources)
    md_path = write_university_markdown(record)
    json_path = write_university_json(record)
    return {
        "school": seed["name"],
        "markdown": str(md_path),
        "json": str(json_path),
    }
