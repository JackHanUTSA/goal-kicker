from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
KB_DIR = ROOT / "knowledgebase" / "universities"
DATA_DIR = ROOT / "data"
SUBDIRS = {
    "enrollment": DATA_DIR / "enrollment",
    "testing": DATA_DIR / "testing",
    "gpa": DATA_DIR / "gpa",
    "rigor": DATA_DIR / "rigor",
}

UNKNOWN_VALUES = {
    None,
    "",
    "unknown",
    "Unknown",
    "null",
    "None",
}

LOW_SIGNAL_PHRASES = (
    "could not be confidently extracted",
    "used in this auto-enrichment pass",
    "not yet extracted",
    "not completed in this pass",
)


def load_record(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def norm_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def is_meaningful(value: Any) -> bool:
    text = norm_text(value)
    if text in UNKNOWN_VALUES:
        return False
    lower = text.lower()
    return not any(phrase in lower for phrase in LOW_SIGNAL_PHRASES)


def first_url(*values: Any) -> str | None:
    for value in values:
        if not value:
            continue
        if isinstance(value, str):
            text = norm_text(value)
            if text:
                return text
            continue
        if isinstance(value, list):
            for item in value:
                text = norm_text(item)
                if text:
                    return text
    return None


def unique_urls(urls: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for url in urls:
        text = norm_text(url)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def evidence_for_field(record: dict[str, Any], field: str) -> list[dict[str, Any]]:
    matches = []
    for item in record.get("evidence", []):
        if item.get("field") == field:
            matches.append(item)
    return matches


def major_source_url(record: dict[str, Any]) -> str | None:
    majors_sources = record.get("source_urls", {}).get("majors", [])
    evidence_sources = [item.get("source_url") for item in evidence_for_field(record, "majors.count")]
    return first_url(majors_sources, evidence_sources, record.get("source_urls", {}).get("general", []))


def admissions_source_urls(record: dict[str, Any], field: str, fallback_group: str | None = None) -> list[str]:
    urls = [item.get("source_url") for item in evidence_for_field(record, field)]
    if fallback_group:
        urls.extend(record.get("source_urls", {}).get(fallback_group, []))
    urls.extend(record.get("source_urls", {}).get("admissions", []))
    urls.extend(record.get("source_urls", {}).get("general", []))
    return unique_urls(urls)


def build_enrollment_payload(record: dict[str, Any]) -> dict[str, Any]:
    majors = record.get("majors", {})
    titles = [norm_text(title) for title in (majors.get("titles") or []) if norm_text(title)]
    payload = {
        "university": record["name"],
        "slug": record["slug"],
        "retrieved_at": str(date.today()),
        "mode": "majors-list",
        "source_url": major_source_url(record),
        "scope_note": "This school does not yet have a source-backed per-major enrollment breakdown in Goal Kicker. This panel shows the structured undergraduate majors inventory currently stored in the knowledgebase.",
        "summary": {
            "majors_count": majors.get("count"),
            "titles_count": len(titles),
            "count_method": norm_text(majors.get("count_method")),
            "confidence": majors.get("confidence"),
        },
        "titles": titles,
        "notes": norm_text(majors.get("notes")),
    }
    return payload


def build_testing_payload(record: dict[str, Any]) -> dict[str, Any] | None:
    admissions = record.get("admissions", {})
    policy = norm_text(admissions.get("testing_policy"))
    urls = admissions_source_urls(record, "admissions.testing_policy", "testing_policy")
    if not policy and not urls:
        return None
    claims = []
    for item in evidence_for_field(record, "admissions.testing_policy"):
        claim = norm_text(item.get("claim"))
        if claim:
            claims.append({"claim": claim, "source_url": item.get("source_url")})
    payload = {
        "university": record["name"],
        "slug": record["slug"],
        "retrieved_at": str(date.today()),
        "scope": "policy-summary",
        "scope_note": "Goal Kicker currently exports testing-policy summaries for this school. If official score distributions were not captured, the panel stays policy-only rather than inventing ranges.",
        "source_url": first_url(urls),
        "source_urls": urls,
        "policy": policy or "No testing-policy summary has been captured yet.",
        "claims": claims,
    }
    return payload


def build_gpa_payload(record: dict[str, Any]) -> dict[str, Any] | None:
    admissions = record.get("admissions", {})
    policy = norm_text(admissions.get("gpa_policy"))
    urls = admissions_source_urls(record, "admissions.gpa_policy")
    if not policy and not urls:
        return None
    claims = []
    for item in evidence_for_field(record, "admissions.gpa_policy"):
        claim = norm_text(item.get("claim"))
        if claim:
            claims.append({"claim": claim, "source_url": item.get("source_url")})
    payload = {
        "university": record["name"],
        "slug": record["slug"],
        "retrieved_at": str(date.today()),
        "scope": "policy-summary",
        "scope_note": "Goal Kicker currently exports GPA-policy notes for this school. Where the school does not publish a hard GPA cutoff or admitted-student GPA distribution, the panel says that directly instead of inventing a threshold.",
        "source_urls": urls,
        "policy_summary": policy or "No GPA-policy summary has been captured yet.",
        "what_mit_does_say": claims,
    }
    return payload


def build_rigor_areas(record: dict[str, Any]) -> list[dict[str, Any]]:
    admissions = record.get("admissions", {})
    areas = []
    course_rigor = norm_text(admissions.get("course_rigor"))
    if is_meaningful(course_rigor):
        areas.append(
            {
                "key": "course-rigor",
                "name": "Course rigor",
                "level": "school-guidance",
                "summary": course_rigor,
                "detail": course_rigor,
                "color": "#60a5fa",
            }
        )
    recommendations = norm_text(admissions.get("recommendations"))
    if is_meaningful(recommendations):
        areas.append(
            {
                "key": "recommendations",
                "name": "Recommendations",
                "level": "application-material",
                "summary": recommendations,
                "detail": recommendations,
                "color": "#34d399",
            }
        )
    essays = norm_text(admissions.get("essays"))
    if is_meaningful(essays):
        areas.append(
            {
                "key": "essays",
                "name": "Essays",
                "level": "application-material",
                "summary": essays,
                "detail": essays,
                "color": "#fbbf24",
            }
        )
    return areas


def build_rigor_payload(record: dict[str, Any]) -> dict[str, Any] | None:
    urls = admissions_source_urls(record, "admissions.course_rigor")
    if not urls:
        urls = admissions_source_urls(record, "admissions.recommendations")
    if not urls:
        urls = admissions_source_urls(record, "admissions.essays")
    areas = build_rigor_areas(record)
    if not areas and not urls:
        return None
    return {
        "university": record["name"],
        "slug": record["slug"],
        "retrieved_at": str(date.today()),
        "scope": "application-guidance",
        "scope_note": "This panel summarizes the structured course-rigor and application-guidance notes currently exported for this school. It remains source-backed and does not infer missing requirements.",
        "source_url": first_url(urls),
        "source_urls": urls,
        "areas": areas,
    }


def write_json(path: Path, payload: dict[str, Any], force: bool) -> bool:
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Export site panel JSON files for Goal Kicker schools.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing panel JSON files instead of only filling missing schools.")
    parser.add_argument("--start-rank", type=int, default=2, help="Lowest ranking position to export. Default: 2 (extend beyond MIT).")
    parser.add_argument("--end-rank", type=int, default=100, help="Highest ranking position to export. Default: 100.")
    args = parser.parse_args()

    counters: Counter[str] = Counter()
    for record_path in sorted(KB_DIR.glob("*.json")):
        record = load_record(record_path)
        rank = record.get("rank")
        if not isinstance(rank, int) or rank < args.start_rank or rank > args.end_rank:
            continue
        slug = record["slug"]

        enroll_payload = build_enrollment_payload(record)
        if write_json(SUBDIRS["enrollment"] / f"{slug}.json", enroll_payload, args.force):
            counters["enrollment_written"] += 1
        else:
            counters["enrollment_skipped"] += 1

        testing_payload = build_testing_payload(record)
        if testing_payload:
            if write_json(SUBDIRS["testing"] / f"{slug}.json", testing_payload, args.force):
                counters["testing_written"] += 1
            else:
                counters["testing_skipped"] += 1

        gpa_payload = build_gpa_payload(record)
        if gpa_payload:
            if write_json(SUBDIRS["gpa"] / f"{slug}.json", gpa_payload, args.force):
                counters["gpa_written"] += 1
            else:
                counters["gpa_skipped"] += 1

        rigor_payload = build_rigor_payload(record)
        if rigor_payload:
            if write_json(SUBDIRS["rigor"] / f"{slug}.json", rigor_payload, args.force):
                counters["rigor_written"] += 1
            else:
                counters["rigor_skipped"] += 1

    print(json.dumps(counters, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
