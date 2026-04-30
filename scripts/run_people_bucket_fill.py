#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
STATUS_PATH = ROOT / "data" / "people_bucket_fill_status.json"
LOG_PATH = ROOT / "data" / "people_bucket_fill.log"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PEOPLE = load_module("enrich_school_people", ROOT / "scripts" / "enrich_school_people.py")


def log(message: str) -> None:
    line = f"[{now_iso()}] {message}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as fh:
        fh.write(line + "\n")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def load_status() -> dict[str, Any]:
    if not STATUS_PATH.exists():
        return {
            "created_at": now_iso(),
            "completed_slugs": [],
            "failed_slugs": [],
            "history": [],
            "in_progress": [],
            "last_batch": [],
            "updated_at": now_iso(),
        }
    status = read_json(STATUS_PATH)
    if status.get("in_progress"):
        status.setdefault("resume_events", []).append(
            {
                "detected_at": now_iso(),
                "event": "recovered_stale_in_progress_batch",
                "slugs": list(status.get("in_progress", [])),
            }
        )
        status["last_interrupted_batch"] = list(status.get("in_progress", []))
        status["in_progress"] = []
        write_status(status)
    return status


def write_status(status: dict[str, Any]) -> None:
    status["updated_at"] = now_iso()
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, indent=2) + "\n")


def all_paths() -> list[Path]:
    return sorted(UNI_DIR.glob("*.json"), key=lambda p: (read_json(p).get("rank") or 999, p.name))


def bucket_priority(record: dict[str, Any]) -> tuple[int, int, int, int]:
    alumni = record.get("school_people", {}).get("successful_alumni", {})
    per_major_target = alumni.get("per_major_target_count") or 0
    gap_counts = alumni.get("major_gap_counts") or {}
    total_gap = sum(max(0, int(v)) for v in gap_counts.values())
    open_buckets = sum(1 for v in gap_counts.values() if int(v) > 0)
    has_by_major = 1 if alumni.get("by_major") else 0
    rank = int(record.get("rank") or 9999)
    # Sort descending by total gap/open buckets, then prefer records that already have by_major, then by better rank.
    return (-total_gap, -open_buckets, -has_by_major, rank)


def select_candidate_paths(
    limit: int | None,
    completed_slugs: set[str],
    failed_slugs: set[str],
    explicit_schools: set[str],
    include_completed: bool,
    retry_failed: bool,
) -> list[Path]:
    candidates: list[tuple[tuple[int, int, int, int], Path]] = []
    explicit_lower = {value.lower() for value in explicit_schools}
    for path in all_paths():
        record = read_json(path)
        slug = str(record.get("slug") or path.stem)
        name = str(record.get("name") or "")
        short_name = str(record.get("short_name") or "")
        if explicit_lower:
            haystack = {slug.lower(), name.lower(), short_name.lower()}
            if not haystack & explicit_lower:
                continue
        if not include_completed and slug in completed_slugs:
            continue
        if not retry_failed and slug in failed_slugs:
            continue
        candidates.append((bucket_priority(record), path))
    candidates.sort(key=lambda item: item[0])
    selected = [path for _, path in candidates]
    if limit is not None:
        selected = selected[:limit]
    return selected


def summarize_overall_progress(paths: list[Path]) -> dict[str, Any]:
    schools_total = len(paths)
    schools_with_bucket_targets = 0
    schools_with_open_bucket_gaps = 0
    total_bucket_gap = 0
    for path in paths:
        record = read_json(path)
        alumni = record.get("school_people", {}).get("successful_alumni", {})
        if alumni.get("per_major_target_count") is not None:
            schools_with_bucket_targets += 1
        gap_counts = alumni.get("major_gap_counts") or {}
        gap_sum = sum(max(0, int(v)) for v in gap_counts.values())
        if gap_sum > 0:
            schools_with_open_bucket_gaps += 1
        total_bucket_gap += gap_sum
    return {
        "schools_total": schools_total,
        "schools_with_bucket_targets": schools_with_bucket_targets,
        "schools_with_open_bucket_gaps": schools_with_open_bucket_gaps,
        "total_bucket_gap": total_bucket_gap,
    }


def run_batch(
    batch_paths: list[Path],
    worker_count: int,
    status: dict[str, Any],
) -> list[dict[str, Any]]:
    results_by_slug: dict[str, dict[str, Any]] = {}
    status["in_progress"] = [path.stem for path in batch_paths]
    status["last_batch"] = [path.stem for path in batch_paths]
    write_status(status)
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_to_path = {executor.submit(PEOPLE.process_record_path, path): path for path in batch_paths}
        for future in as_completed(future_to_path):
            path = future_to_path[future]
            slug = path.stem
            try:
                result = future.result()
                results_by_slug[slug] = result
                log(
                    "bucket-fill slug={slug} major_buckets_total={majors} below_target={below} total_gap={gap} "
                    "professors={prof} alumni={alum}".format(
                        slug=result.get("slug"),
                        majors=result.get("major_buckets_total"),
                        below=result.get("major_buckets_below_target"),
                        gap=result.get("total_bucket_gap"),
                        prof=result.get("popular_professors"),
                        alum=result.get("successful_alumni"),
                    )
                )
                completed = set(status.get("completed_slugs", []))
                completed.add(slug)
                status["completed_slugs"] = sorted(completed)
            except Exception as exc:
                results_by_slug[slug] = {
                    "slug": slug,
                    "validation_problems": [f"runner_error: {exc}"],
                }
                log(f"bucket-fill slug={slug} error={exc}")
                failed = set(status.get("failed_slugs", []))
                failed.add(slug)
                status["failed_slugs"] = sorted(failed)
            status["in_progress"] = sorted(set(status.get("in_progress", [])) - {slug})
            write_status(status)
            time.sleep(0.1)
    return [results_by_slug[path.stem] for path in batch_paths]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gap-prioritized resumable bucket-fill runner for university people enrichment."
    )
    parser.add_argument("--batch-size", type=int, default=10, help="Number of universities to process per batch (max 10).")
    parser.add_argument("--max-workers", type=int, default=10, help="Concurrent university workers (max 10).")
    parser.add_argument("--limit", type=int, default=None, help="Optional max number of candidate schools to consider this run.")
    parser.add_argument("--school", action="append", default=None, help="Specific school slug/name/short_name; may be repeated.")
    parser.add_argument("--include-completed", action="store_true", help="Re-include already completed schools.")
    parser.add_argument("--retry-failed", action="store_true", help="Retry schools previously marked as failed.")
    parser.add_argument("--reset-status", action="store_true", help="Reset checkpoint state before running.")
    args = parser.parse_args()

    batch_size = max(1, min(args.batch_size, 10))
    max_workers = max(1, min(args.max_workers, 10))
    explicit_schools = set(args.school or [])

    status = load_status()
    if args.reset_status:
        status = {
            "created_at": now_iso(),
            "completed_slugs": [],
            "failed_slugs": [],
            "history": [],
            "in_progress": [],
            "last_batch": [],
        }
        write_status(status)

    completed_slugs = set(status.get("completed_slugs", []))
    failed_slugs = set(status.get("failed_slugs", []))
    candidate_paths = select_candidate_paths(
        limit=args.limit,
        completed_slugs=completed_slugs,
        failed_slugs=failed_slugs,
        explicit_schools=explicit_schools,
        include_completed=args.include_completed,
        retry_failed=args.retry_failed,
    )
    if not candidate_paths:
        summary = {
            "processed": 0,
            "batch_size": batch_size,
            "max_workers": 0,
            "message": "No candidate schools selected for this run.",
            "progress": summarize_overall_progress(all_paths()),
        }
        print(json.dumps(summary, indent=2))
        return 0

    batch_paths = candidate_paths[:batch_size]
    worker_count = min(max_workers, len(batch_paths))
    log(
        f"bucket-fill runner starting batch_size={batch_size} workers={worker_count} selected={[path.stem for path in batch_paths]}"
    )
    results = run_batch(batch_paths=batch_paths, worker_count=worker_count, status=status)

    history_entry = {
        "started_at": now_iso(),
        "requested_batch_size": batch_size,
        "worker_count": worker_count,
        "selected_slugs": [path.stem for path in batch_paths],
        "results": results,
    }
    history = status.get("history", [])
    history.append(history_entry)
    status["history"] = history[-50:]
    status["last_run_summary"] = {
        "processed": len(results),
        "selected_slugs": [path.stem for path in batch_paths],
        "remaining_candidate_slugs": [path.stem for path in candidate_paths[batch_size:batch_size + 25]],
        "progress": summarize_overall_progress(all_paths()),
    }
    status["in_progress"] = []
    write_status(status)

    output = {
        "processed": len(results),
        "batch_size": batch_size,
        "max_workers": worker_count,
        "selected_slugs": [path.stem for path in batch_paths],
        "remaining_candidate_slugs": [path.stem for path in candidate_paths[batch_size:batch_size + 25]],
        "progress": summarize_overall_progress(all_paths()),
        "results": results,
        "status_file": str(STATUS_PATH),
        "log_file": str(LOG_PATH),
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
