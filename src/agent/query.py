from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
UNI_DIR = ROOT / "knowledgebase" / "universities"


def load_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(UNI_DIR.glob("*.json")):
        records.append(json.loads(path.read_text()))
    return records


def find_record(records: list[dict[str, Any]], needle: str) -> dict[str, Any]:
    key = needle.strip().lower()
    exact_fields = ("slug", "short_name", "name")
    for record in records:
        for field in exact_fields:
            if str(record.get(field, "")).lower() == key:
                return record
    for record in records:
        hay = " ".join(
            [str(record.get("slug", "")), str(record.get("short_name", "")), str(record.get("name", ""))]
        ).lower()
        if key in hay:
            return record
    raise ValueError(f"School not found: {needle}")


def summarize_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": record["name"],
        "slug": record["slug"],
        "rank": record.get("rank"),
        "majors_count": record.get("majors", {}).get("count"),
        "majors_count_method": record.get("majors", {}).get("count_method"),
        "testing_policy": record.get("admissions", {}).get("testing_policy"),
        "gpa_policy": record.get("admissions", {}).get("gpa_policy"),
        "course_rigor": record.get("admissions", {}).get("course_rigor"),
        "recommendations": record.get("admissions", {}).get("recommendations"),
        "essays": record.get("admissions", {}).get("essays"),
        "projects_research": record.get("competitive_signals", {}).get("projects_research", []),
        "warnings": record.get("verification", {}).get("warnings", []),
        "unknown_fields": record.get("verification", {}).get("unknown_fields", []),
        "confidence": record.get("verification", {}).get("confidence"),
    }


def majors_by_school(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        {
            "rank": record.get("rank"),
            "slug": record["slug"],
            "name": record["name"],
            "majors_count": record.get("majors", {}).get("count"),
            "count_method": record.get("majors", {}).get("count_method"),
            "confidence": record.get("majors", {}).get("confidence"),
        }
        for record in records
    ]
    return sorted(rows, key=lambda row: (row["majors_count"] is None, -(row["majors_count"] or -1), row["rank"] or 999))


def project_research_emphasis(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        signals = record.get("competitive_signals", {}).get("projects_research", [])
        rows.append(
            {
                "rank": record.get("rank"),
                "slug": record["slug"],
                "name": record["name"],
                "signal_count": len(signals),
                "signals": signals,
                "confidence": record.get("verification", {}).get("confidence"),
            }
        )
    return sorted(rows, key=lambda row: (-row["signal_count"], row["rank"] or 999, row["name"]))


def admissions_policy_summary(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in sorted(records, key=lambda r: (r.get("rank") or 999, r["name"])):
        rows.append(
            {
                "rank": record.get("rank"),
                "slug": record["slug"],
                "name": record["name"],
                "testing_policy": record.get("admissions", {}).get("testing_policy"),
                "gpa_policy": record.get("admissions", {}).get("gpa_policy"),
                "course_rigor": record.get("admissions", {}).get("course_rigor"),
                "confidence": record.get("verification", {}).get("confidence"),
                "unknown_fields": record.get("verification", {}).get("unknown_fields", []),
            }
        )
    return rows


def compare_records(records: list[dict[str, Any]], schools: list[str]) -> dict[str, Any]:
    picked = [find_record(records, school) for school in schools]
    fields = {
        "majors_count": lambda r: r.get("majors", {}).get("count"),
        "testing_policy": lambda r: r.get("admissions", {}).get("testing_policy"),
        "gpa_policy": lambda r: r.get("admissions", {}).get("gpa_policy"),
        "course_rigor": lambda r: r.get("admissions", {}).get("course_rigor"),
        "recommendations": lambda r: r.get("admissions", {}).get("recommendations"),
        "essays": lambda r: r.get("admissions", {}).get("essays"),
        "projects_research": lambda r: r.get("competitive_signals", {}).get("projects_research", []),
        "unknown_fields": lambda r: r.get("verification", {}).get("unknown_fields", []),
        "confidence": lambda r: r.get("verification", {}).get("confidence"),
    }
    comparison: dict[str, dict[str, Any]] = {}
    for field_name, getter in fields.items():
        comparison[field_name] = {record["slug"]: getter(record) for record in picked}
    return {
        "schools": [record["name"] for record in picked],
        "comparison": comparison,
    }
