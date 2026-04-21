from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "data" / "university_schema.json"


def load_schema_template() -> dict[str, Any]:
    schema = json.loads(SCHEMA_PATH.read_text())
    return copy.deepcopy(schema["record_template"])


def build_placeholder_record(seed: dict[str, Any], sources: dict[str, Any]) -> dict[str, Any]:
    record = load_schema_template()
    record["name"] = seed["name"]
    record["short_name"] = seed["short_name"]
    record["slug"] = seed["slug"]
    record["rank"] = seed["rank"]
    record["official_domain"] = seed["official_domain"]
    record["source_urls"]["general"] = sources["candidate_urls"]["general"]
    record["source_urls"]["admissions"] = sources["candidate_urls"]["admissions"]
    record["source_urls"]["majors"] = sources["candidate_urls"]["majors"]
    record["verification"]["confidence"] = "placeholder"
    record["verification"]["unknown_fields"] = [
        "majors.count",
        "admissions.testing_policy",
        "admissions.gpa_policy",
        "competitive_signals.projects_research",
    ]
    record["verification"]["warnings"] = [
        "This record is a scaffold only. No live university source has been extracted yet."
    ]
    return record
