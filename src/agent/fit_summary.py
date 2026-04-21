from __future__ import annotations

from typing import Any

from src.agent.query import find_record, load_records


def _compact_list(values: list[str]) -> list[str]:
    return [value for value in values if value]


def _practical_academics_takeaway(record: dict[str, Any]) -> str:
    testing = str(record.get("admissions", {}).get("testing_policy") or "unknown")
    gpa = str(record.get("admissions", {}).get("gpa_policy") or "unknown")
    rigor = str(record.get("admissions", {}).get("course_rigor") or "unknown")

    parts: list[str] = []
    lower_testing = testing.lower()
    if "require" in lower_testing and "not require" not in lower_testing and "test-optional" not in lower_testing:
        parts.append("Plan to submit standardized testing under the policy currently described in the official record.")
    elif "test-optional" in lower_testing or "optional" in lower_testing:
        parts.append("Testing is not strictly required under the current policy captured here, so the student should focus on overall fit and strong academics first.")
    elif "test-flexible" in lower_testing:
        parts.append("The student should prepare an accepted testing pathway early, because Yale-style test-flexible policies still require some exam evidence.")

    if "minimum gpa" in gpa.lower() or "does not publish" in gpa.lower() or "unknown" in gpa.lower():
        parts.append("There is no simple published GPA cutoff in this record, so strong grades alone should not be treated as enough.")
    elif "competitive" in gpa.lower() or "minimum requirements" in gpa.lower():
        parts.append("Meeting the minimum academic floor is not enough by itself; the student should aim above baseline expectations.")

    if rigor and rigor.lower() not in {"unknown", "none"}:
        parts.append("The student should take the strongest available curriculum that fits their school context, especially in core academic areas.")

    return " ".join(parts) if parts else "The record does not yet provide a strong practical academic interpretation."


def _practical_projects_takeaway(record: dict[str, Any]) -> str:
    projects = record.get("competitive_signals", {}).get("projects_research", []) or []
    if not projects:
        return "This record does not strongly document a project/research preference yet, so more verification may still be useful."
    if len(projects) >= 2:
        return "This school's record shows that research, initiative, or meaningful engagement outside class can strengthen the application story."
    return "This record contains at least one explicit project or research signal, so authentic work beyond grades may matter."


def build_fit_summary(record: dict[str, Any]) -> dict[str, Any]:
    unknown_fields = record.get("verification", {}).get("unknown_fields", [])
    warnings = record.get("verification", {}).get("warnings", [])
    return {
        "school_overview": {
            "name": record.get("name"),
            "rank": record.get("rank"),
            "majors_count": record.get("majors", {}).get("count"),
            "majors_count_method": record.get("majors", {}).get("count_method"),
            "confidence": record.get("verification", {}).get("confidence"),
        },
        "academics_needed": {
            "testing_policy": record.get("admissions", {}).get("testing_policy"),
            "gpa_policy": record.get("admissions", {}).get("gpa_policy"),
            "course_rigor": record.get("admissions", {}).get("course_rigor"),
            "practical_takeaway": _practical_academics_takeaway(record),
        },
        "essays_and_recommendations": {
            "essays": record.get("admissions", {}).get("essays"),
            "recommendations": record.get("admissions", {}).get("recommendations"),
        },
        "projects_research_extracurriculars": {
            "signals": _compact_list(record.get("competitive_signals", {}).get("projects_research", [])),
            "practical_takeaway": _practical_projects_takeaway(record),
        },
        "gaps_unknowns": {
            "unknown_fields": unknown_fields,
            "warnings": warnings,
            "needs_more_verification": bool(unknown_fields),
        },
    }


def build_fit_summary_for_school(name_or_slug: str) -> dict[str, Any]:
    records = load_records()
    record = find_record(records, name_or_slug)
    return build_fit_summary(record)
