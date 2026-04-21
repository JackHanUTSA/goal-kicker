from __future__ import annotations

from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "knowledgebase" / "universities"


def render_university_markdown(record: dict[str, Any]) -> str:
    admissions_urls = "\n".join(f"- {u}" for u in record["source_urls"]["admissions"])
    majors_urls = "\n".join(f"- {u}" for u in record["source_urls"]["majors"])
    warnings = "\n".join(f"- {w}" for w in record["verification"]["warnings"])
    unknowns = "\n".join(f"- {u}" for u in record["verification"]["unknown_fields"])
    return f"""---
name: {record['name']}
short_name: {record['short_name']}
slug: {record['slug']}
rank: {record['rank']}
official_domain: {record['official_domain']}
status: scaffold
---

# {record['name']}

## Official domain
- {record['official_domain']}

## Candidate admissions sources
{admissions_urls}

## Candidate majors sources
{majors_urls}

## Current status
- Placeholder record generated
- No live extraction completed yet

## Unknown fields
{unknowns}

## Warnings
{warnings}
"""


def write_university_markdown(record: dict[str, Any]) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{record['slug']}.md"
    path.write_text(render_university_markdown(record))
    return path
