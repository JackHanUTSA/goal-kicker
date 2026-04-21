from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "data" / "university_schema.json"
REQUIRED_SOURCE_GROUPS = ["admissions", "majors"]
CRITICAL_FIELDS = [
    ("majors.count", lambda r: r.get("majors", {}).get("count") not in (None, "unknown")),
    ("admissions.testing_policy", lambda r: str(r.get("admissions", {}).get("testing_policy", "")).strip() not in ("", "None", "unknown")),
    ("admissions.gpa_policy", lambda r: str(r.get("admissions", {}).get("gpa_policy", "")).strip() not in ("", "None", "unknown")),
]


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text())


def _get_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split('.'):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def verify_record(record: dict[str, Any]) -> dict[str, Any]:
    schema = load_schema()
    problems: list[str] = []
    warnings: list[str] = []

    for field in schema.get("required_fields", []):
        if field not in record:
            problems.append(f"missing required top-level field: {field}")

    for group in REQUIRED_SOURCE_GROUPS:
        urls = record.get("source_urls", {}).get(group, [])
        if not urls:
            problems.append(f"missing official source URLs for {group}")

    for field_name, checker in CRITICAL_FIELDS:
        try:
            ok = checker(record)
        except Exception:
            ok = False
        if not ok:
            problems.append(f"missing critical field: {field_name}")

    for item in record.get("evidence", []):
        classification = item.get("classification")
        source_url = item.get("source_url")
        if classification == "inference" and not source_url:
            problems.append("inference evidence without citation")

    unknown_fields = record.get("verification", {}).get("unknown_fields", [])
    if unknown_fields:
        warnings.append(f"unknown fields remain: {', '.join(unknown_fields)}")

    confidence = record.get("verification", {}).get("confidence", "unknown")
    status = "pass" if not problems else "fail"
    return {
        "slug": record.get("slug"),
        "name": record.get("name"),
        "status": status,
        "confidence": confidence,
        "problems": problems,
        "warnings": warnings,
    }


def verify_record_file(path: Path) -> dict[str, Any]:
    return verify_record(json.loads(path.read_text()))
