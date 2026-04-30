#!/usr/bin/env /usr/bin/python3
from __future__ import annotations

import importlib.util
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
UNI_DIR = ROOT / "knowledgebase" / "universities"
STATUS_PATH = ROOT / "data" / "finish_coverage_status.json"
LOG_PATH = ROOT / "data" / "finish_coverage.log"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MAJORS = load_module("populate_major_titles", ROOT / "scripts" / "populate_major_titles.py")
PEOPLE = load_module("enrich_school_people", ROOT / "scripts" / "enrich_school_people.py")


def log(message: str) -> None:
    line = f"[{now_iso()}] {message}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as fh:
        fh.write(line + "\n")


def read_record(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def all_paths() -> list[Path]:
    return sorted(UNI_DIR.glob("*.json"), key=lambda p: (read_record(p).get("rank") or 999, p.name))


def coverage_counts() -> dict[str, int]:
    majors_titles = 0
    professors = 0
    alumni = 0
    total = 0
    for path in UNI_DIR.glob("*.json"):
        total += 1
        record = read_record(path)
        if record.get("majors", {}).get("titles"):
            majors_titles += 1
        if record.get("school_people", {}).get("popular_professors", {}).get("items"):
            professors += 1
        if record.get("school_people", {}).get("successful_alumni", {}).get("items"):
            alumni += 1
    return {
        "schools_total": total,
        "majors_titles": majors_titles,
        "popular_professors": professors,
        "successful_alumni": alumni,
    }


def write_status(extra: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {
        "updated_at": now_iso(),
        "coverage": coverage_counts(),
    }
    if extra:
        payload.update(extra)
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2))


def process_majors_pass(limit: int | None = None) -> dict[str, Any]:
    processed = 0
    gained = 0
    errors: list[dict[str, str]] = []
    for path in all_paths():
        record = read_record(path)
        if record.get("majors", {}).get("titles"):
            continue
        if limit is not None and processed >= limit:
            break
        processed += 1
        slug = record["slug"]
        try:
            updated, has_titles, source_url = MAJORS.update_record(record)
            title_count = len(updated.get("majors", {}).get("titles") or [])
            if has_titles:
                gained += 1
            log(f"majors slug={slug} success={has_titles} titles={title_count} source={source_url}")
        except Exception as exc:
            errors.append({"slug": slug, "error": str(exc)})
            log(f"majors slug={slug} error={exc}")
        write_status({"phase": "majors", "last_slug": slug})
        time.sleep(0.5)
    return {"processed": processed, "gained": gained, "errors": errors}


def enrich_people_record(path: Path) -> dict[str, Any]:
    record = read_record(path)
    had_prof = bool(record.get("school_people", {}).get("popular_professors", {}).get("items"))
    had_alum = bool(record.get("school_people", {}).get("successful_alumni", {}).get("items"))
    updated = PEOPLE.enrich_record(record)
    json_path = PEOPLE.write_university_json(updated)
    md_path = PEOPLE.write_university_markdown(updated)
    prof_count = len(updated.get("school_people", {}).get("popular_professors", {}).get("items") or [])
    alum_count = len(updated.get("school_people", {}).get("successful_alumni", {}).get("items") or [])
    return {
        "slug": record["slug"],
        "had_prof": had_prof,
        "had_alum": had_alum,
        "prof_count": prof_count,
        "alum_count": alum_count,
        "json_name": json_path.name,
        "md_name": md_path.name,
    }


def process_people_pass(limit: int | None = None, workers: int = 1) -> dict[str, Any]:
    gained_prof = 0
    gained_alum = 0
    errors: list[dict[str, str]] = []
    pending_paths: list[Path] = []
    for path in all_paths():
        record = read_record(path)
        has_prof = bool(record.get("school_people", {}).get("popular_professors", {}).get("items"))
        has_alum = bool(record.get("school_people", {}).get("successful_alumni", {}).get("items"))
        if has_prof and has_alum:
            continue
        if limit is not None and len(pending_paths) >= limit:
            break
        pending_paths.append(path)

    processed = len(pending_paths)
    if not pending_paths:
        return {"processed": 0, "gained_prof": 0, "gained_alum": 0, "errors": [], "workers": 0}

    worker_count = max(1, min(int(workers), len(pending_paths)))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_to_path = {executor.submit(enrich_people_record, path): path for path in pending_paths}
        for future in as_completed(future_to_path):
            path = future_to_path[future]
            slug = path.stem
            try:
                result = future.result()
                if result["prof_count"] and not result["had_prof"]:
                    gained_prof += 1
                if result["alum_count"] and not result["had_alum"]:
                    gained_alum += 1
                log(
                    f"people slug={result['slug']} professors={result['prof_count']} alumni={result['alum_count']} "
                    f"json={result['json_name']} md={result['md_name']}"
                )
            except Exception as exc:
                errors.append({"slug": slug, "error": str(exc)})
                log(f"people slug={slug} error={exc}")
            write_status({"phase": "people", "last_slug": slug, "people_workers": worker_count})
            time.sleep(1.0)
    return {"processed": processed, "gained_prof": gained_prof, "gained_alum": gained_alum, "errors": errors, "workers": worker_count}


def main() -> int:
    majors_limit = None
    people_limit = None
    skip_majors = False
    skip_people = False
    people_workers = 3
    if len(sys.argv) > 1:
        try:
            majors_limit = int(sys.argv[1])
        except ValueError:
            majors_limit = None
    if len(sys.argv) > 2:
        try:
            people_limit = int(sys.argv[2])
        except ValueError:
            people_limit = None
    for arg in sys.argv[3:]:
        if arg == "--skip-majors":
            skip_majors = True
        elif arg == "--skip-people":
            skip_people = True
        elif arg.startswith("--people-workers="):
            try:
                people_workers = max(1, int(arg.split("=", 1)[1]))
            except ValueError:
                people_workers = 3

    log("finish coverage runner started")
    before = coverage_counts()
    write_status({"phase": "starting", "people_workers": people_workers})

    majors_result = {"processed": 0, "gained": 0, "errors": [], "skipped": skip_majors}
    people_result = {"processed": 0, "gained_prof": 0, "gained_alum": 0, "errors": [], "skipped": skip_people, "workers": people_workers}
    if not skip_majors:
        majors_result = process_majors_pass(limit=majors_limit)
    if not skip_people:
        people_result = process_people_pass(limit=people_limit, workers=people_workers)

    after = coverage_counts()
    summary = {
        "started_at": now_iso(),
        "before": before,
        "after": after,
        "majors_result": majors_result,
        "people_result": people_result,
        "skip_majors": skip_majors,
        "skip_people": skip_people,
        "people_workers": people_workers,
        "phase": "done",
    }
    write_status(summary)
    log(f"finish coverage runner completed before={before} after={after}")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
