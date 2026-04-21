from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.agent.run_one_university import load_seeds, run_one_university

ROOT = Path(__file__).resolve().parents[2]
PROGRESS_PATH = ROOT / "data" / "progress.json"
UNI_DIR = ROOT / "knowledgebase" / "universities"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_progress() -> dict[str, Any]:
    if not PROGRESS_PATH.exists():
        return {"updated_at": None, "schools": {}}
    data = json.loads(PROGRESS_PATH.read_text())
    data.setdefault("updated_at", None)
    data.setdefault("schools", {})
    return data


def save_progress(progress: dict[str, Any]) -> None:
    progress["updated_at"] = now_iso()
    PROGRESS_PATH.write_text(json.dumps(progress, indent=2))


def school_output_exists(slug: str) -> bool:
    return (UNI_DIR / f"{slug}.json").exists() and (UNI_DIR / f"{slug}.md").exists()


def select_seeds(start_rank: int | None = None, limit: int | None = None, school_names: list[str] | None = None) -> list[dict[str, Any]]:
    seeds = load_seeds()
    if school_names:
        wanted = {name.strip().lower() for name in school_names}
        picked = [
            seed for seed in seeds
            if seed["slug"].lower() in wanted
            or seed["name"].lower() in wanted
            or seed["short_name"].lower() in wanted
        ]
        return picked
    if start_rank is not None:
        seeds = [seed for seed in seeds if int(seed["rank"]) >= int(start_rank)]
    if limit is not None:
        seeds = seeds[:limit]
    return seeds


def run_batch(*, start_rank: int | None = None, limit: int | None = None, refresh: bool = False, school_names: list[str] | None = None) -> list[dict[str, Any]]:
    progress = load_progress()
    results: list[dict[str, Any]] = []

    for seed in select_seeds(start_rank=start_rank, limit=limit, school_names=school_names):
        slug = seed["slug"]
        status = progress["schools"].get(slug, {})
        if not refresh and school_output_exists(slug):
            existing = {
                "slug": slug,
                "name": seed["name"],
                "status": "skipped_existing",
                "markdown": str(UNI_DIR / f"{slug}.md"),
                "json": str(UNI_DIR / f"{slug}.json"),
            }
            progress["schools"][slug] = {
                "name": seed["name"],
                "rank": seed["rank"],
                "status": "done",
                "last_run_at": now_iso(),
                "output_markdown": existing["markdown"],
                "output_json": existing["json"],
                "notes": status.get("notes", "existing outputs preserved"),
            }
            save_progress(progress)
            results.append(existing)
            continue

        progress["schools"][slug] = {
            "name": seed["name"],
            "rank": seed["rank"],
            "status": "in_progress",
            "last_run_at": now_iso(),
            "notes": status.get("notes", ""),
        }
        save_progress(progress)

        try:
            output = run_one_university(seed["slug"])
            progress["schools"][slug] = {
                "name": seed["name"],
                "rank": seed["rank"],
                "status": "done",
                "last_run_at": now_iso(),
                "output_markdown": output["markdown"],
                "output_json": output["json"],
                "notes": "placeholder pipeline completed",
            }
            save_progress(progress)
            results.append({"slug": slug, "name": seed["name"], "status": "done", **output})
        except Exception as exc:
            progress["schools"][slug] = {
                "name": seed["name"],
                "rank": seed["rank"],
                "status": "failed",
                "last_run_at": now_iso(),
                "error": str(exc),
            }
            save_progress(progress)
            results.append({"slug": slug, "name": seed["name"], "status": "failed", "error": str(exc)})

    return results
