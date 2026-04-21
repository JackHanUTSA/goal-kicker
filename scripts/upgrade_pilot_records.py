#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNI_DIR = ROOT / "knowledgebase" / "universities"
REQ_DIR = ROOT / "knowledgebase" / "requirements"
MAJ_DIR = ROOT / "knowledgebase" / "majors"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_record(slug: str) -> dict:
    return json.loads((UNI_DIR / f"{slug}.json").read_text())


def save_record(record: dict) -> None:
    (UNI_DIR / f"{record['slug']}.json").write_text(json.dumps(record, indent=2))
    md_lines = [
        "---",
        f"name: {record['name']}",
        f"short_name: {record['short_name']}",
        f"slug: {record['slug']}",
        f"rank: {record['rank']}",
        f"official_domain: {record['official_domain']}",
        "status: structured-pilot",
        "---",
        "",
        f"# {record['name']}",
        "",
        "## Official sources",
    ]
    for kind in ["admissions", "majors"]:
        md_lines.append(f"### {kind.title()}")
        for url in record["source_urls"][kind]:
            md_lines.append(f"- {url}")
        md_lines.append("")
    md_lines += [
        "## Structured extraction",
        f"- Majors count: {record['majors']['count']}",
        f"- Count method: {record['majors']['count_method']}",
        f"- Testing policy: {record['admissions']['testing_policy']}",
        f"- GPA policy: {record['admissions']['gpa_policy']}",
        f"- Course rigor: {record['admissions']['course_rigor']}",
        f"- Recommendations: {record['admissions']['recommendations']}",
        f"- Essays: {record['admissions']['essays']}",
        "",
        "## Competitive signals",
    ]
    for k, vals in record["competitive_signals"].items():
        if vals:
            md_lines.append(f"### {k}")
            for v in vals:
                md_lines.append(f"- {v}")
    md_lines += ["", "## Warnings"]
    for warning in record["verification"]["warnings"]:
        md_lines.append(f"- {warning}")
    (UNI_DIR / f"{record['slug']}.md").write_text("\n".join(md_lines))


def add_evidence(record: dict, field: str, claim: str, classification: str, source_url: str, source_excerpt: str) -> None:
    record.setdefault("evidence", []).append({
        "field": field,
        "claim": claim,
        "classification": classification,
        "source_url": source_url,
        "source_excerpt": source_excerpt,
        "retrieved_at": now_iso(),
    })


PILOT_FACTS = {
    "mit": {
        "majors_count": 109,
        "majors_method": "counted unique undergraduate degree-chart links on MIT Course Catalog Degree Charts page",
        "testing_policy": "MIT requires the SAT or the ACT.",
        "testing_excerpt": "Testing requirement We require the SAT or the ACT.",
        "testing_url": "https://mitadmissions.org/apply/firstyear/tests-scores/",
        "gpa_policy": "MIT does not publish a minimum or recommended score cutoff on the cited testing page; GPA not extracted yet from official source.",
        "course_rigor": "unknown",
        "recommendations": "MIT requires letters of recommendation, but the exact structured wording has not been extracted yet from the pilot sources.",
        "essays": "MIT has an official essays, activities, and academics application section.",
        "projects": [
            "MIT explicitly evaluates essays, activities, and academics as part of the first-year application process."
        ],
        "majors_url": "https://catalog.mit.edu/degree-charts/",
        "majors_excerpt": "Degree Charts > Undergraduate Degrees with multiple undergraduate degree chart links.",
        "essay_url": "https://mitadmissions.org/apply/firstyear/essays-activities-academics/",
        "essay_excerpt": "Essays, activities & academics | MIT Admissions",
    },
    "stanford": {
        "majors_count": 200,
        "majors_method": "counted text-only 'Majors and Offerings' opportunity links on Stanford Explore Majors page; this is offerings count, not a pure major-only count",
        "testing_policy": "ACT or SAT scores are required for first-year and transfer students.",
        "testing_excerpt": "Testing Requirements ACT or SAT scores are required for first-year and transfer students.",
        "testing_url": "https://admission.stanford.edu/apply/first-year/testing.html",
        "gpa_policy": "No explicit minimum GPA found in the pilot sources.",
        "course_rigor": "No structured course-rigor quote extracted yet; Stanford has a separate 'Preparing for Stanford Academics' page.",
        "recommendations": "Stanford requires a school report form and counselor letter plus letters of recommendation from two teachers.",
        "recommendations_excerpt": "School Report form and counselor letter of recommendation ... Letters of recommendation from two teachers.",
        "recommendations_url": "https://admission.stanford.edu/apply/first-year/index.html",
        "essays": "Stanford requires the Common Application and additional application materials; separate Application and Essays guidance exists.",
        "projects": [],
        "majors_url": "https://majors.stanford.edu/majors/text-only-lists-majors-and-offerings",
        "majors_excerpt": "Text-Only Lists of Majors and Offerings ... counted opportunity links on the official page.",
    },
    "harvard": {
        "majors_count": 50,
        "majors_method": "official Harvard Liberal Arts & Sciences page states 50 undergraduate fields of study",
        "testing_policy": "Harvard requires SAT or ACT, with alternative exams accepted in exceptional cases when those tests are not accessible.",
        "testing_excerpt": "$90 fee ... SAT or ACT - In exceptional cases when those tests are not accessible, one of the following can meet the requirement: AP, IB, GCSE/A-Level, or national leaving exam results.",
        "testing_url": "https://college.harvard.edu/admissions/apply/first-year-applicants",
        "gpa_policy": "Harvard does not state a simple minimum GPA in the pilot page; academic accomplishment is important but not the only factor.",
        "course_rigor": "Harvard emphasizes academic accomplishment plus broad liberal arts and sciences study; structured minimum course-rigor wording not yet isolated.",
        "recommendations": "Harvard requires a school report with counselor letter and two teacher recommendations.",
        "recommendations_excerpt": "School Report (which includes a counselor letter) and high school transcript; Teacher Recommendations (2).",
        "recommendations_url": "https://college.harvard.edu/admissions/apply/first-year-applicants",
        "essays": "Harvard requires a personal essay plus five required short-answer Harvard supplement questions.",
        "essays_excerpt": "Personal essay ... There are five required short-answer questions with 150 word limits for each.",
        "essays_url": "https://college.harvard.edu/admissions/apply/first-year-applicants",
        "projects": [
            "Harvard says students can participate in hands-on research projects from the moment they arrive.",
            "Harvard admissions says many factors matter beyond academic accomplishment, including special talents and potential contributions to the community."
        ],
        "majors_url": "https://college.harvard.edu/academics/liberal-arts-sciences",
        "majors_excerpt": "We offer more than 3,700 courses in 50 undergraduate fields of study, which we call concentrations.",
    },
    "uc-berkeley": {
        "majors_count": 237,
        "majors_method": "official Berkeley undergraduate catalog programs page reports 237 results; this includes majors, minors, joint programs, and dual degrees, so pure majors count remains unresolved",
        "testing_policy": "unknown from the Berkeley-specific pilot source",
        "gpa_policy": "Satisfying Berkeley's minimum requirements is often not enough to be competitive for selection.",
        "gpa_excerpt": "Since Berkeley is a competitive campus, satisfying the minimum requirements is often not enough to be competitive for selection.",
        "gpa_url": "https://admissions.berkeley.edu/apply-to-berkeley/first-year-applicants-uc-berkeley/",
        "course_rigor": "Berkeley uses a holistic review and considers the full record of achievement in college preparatory courses.",
        "course_rigor_excerpt": "Using a broad concept of merit ... the applicant's full record of achievement in college preparatory courses.",
        "course_rigor_url": "https://admissions.berkeley.edu/apply-to-berkeley/first-year-applicants-uc-berkeley/",
        "recommendations": "unknown from the Berkeley-specific pilot source",
        "essays": "unknown from the Berkeley-specific pilot source",
        "projects": [
            "Berkeley considers accomplishments in a field of intellectual or creative endeavor.",
            "Berkeley considers accomplishments in extracurricular activities, leadership, employment, and volunteer service."
        ],
        "projects_excerpt": "accomplishments in a field of intellectual or creative endeavor; accomplishments in extracurricular activities ... leadership ... employment; and volunteer service.",
        "projects_url": "https://admissions.berkeley.edu/apply-to-berkeley/first-year-applicants-uc-berkeley/",
        "majors_url": "https://undergraduate.catalog.berkeley.edu/programs",
        "majors_excerpt": "237 results found.",
    },
    "michigan": {
        "majors_count": None,
        "majors_method": "blocked by bot protection during pilot ingestion",
        "testing_policy": "unknown",
        "gpa_policy": "unknown",
        "course_rigor": "unknown",
        "recommendations": "unknown",
        "essays": "unknown",
        "projects": [],
        "warnings": [
            "University of Michigan admissions and majors pages were blocked by bot protection in this environment."
        ]
    }
}


def update_record(slug: str) -> dict:
    record = load_record(slug)
    facts = PILOT_FACTS[slug]
    record["majors"]["count"] = facts["majors_count"]
    record["majors"]["count_method"] = facts["majors_method"]
    record["majors"]["notes"] = facts["majors_method"]
    record["majors"]["confidence"] = "medium" if facts["majors_count"] is not None else "low"

    record["admissions"]["testing_policy"] = facts["testing_policy"]
    record["admissions"]["gpa_policy"] = facts["gpa_policy"]
    record["admissions"]["course_rigor"] = facts["course_rigor"]
    record["admissions"]["recommendations"] = facts["recommendations"]
    record["admissions"]["essays"] = facts["essays"]
    record["competitive_signals"]["projects_research"] = facts.get("projects", [])

    if facts.get("majors_url") and facts.get("majors_count") is not None:
        add_evidence(record, "majors.count", f"Majors/program count recorded as {facts['majors_count']}", "official_recommendation", facts["majors_url"], facts["majors_excerpt"])
    if facts.get("testing_url") and facts.get("testing_policy") != "unknown":
        add_evidence(record, "admissions.testing_policy", facts["testing_policy"], "official_requirement", facts["testing_url"], facts["testing_excerpt"])
    if facts.get("gpa_url"):
        add_evidence(record, "admissions.gpa_policy", facts["gpa_policy"], "reported_profile", facts["gpa_url"], facts["gpa_excerpt"])
    if facts.get("course_rigor_url"):
        add_evidence(record, "admissions.course_rigor", facts["course_rigor"], "reported_profile", facts["course_rigor_url"], facts["course_rigor_excerpt"])
    if facts.get("recommendations_url") and facts.get("recommendations") != "unknown":
        add_evidence(record, "admissions.recommendations", facts["recommendations"], "official_requirement", facts["recommendations_url"], facts["recommendations_excerpt"])
    if facts.get("essays_url") and facts.get("essays") != "unknown":
        add_evidence(record, "admissions.essays", facts["essays"], "official_requirement", facts["essays_url"], facts["essays_excerpt"])
    if facts.get("projects_url") and facts.get("projects"):
        add_evidence(record, "competitive_signals.projects_research", "; ".join(facts["projects"]), "reported_profile", facts["projects_url"], facts["projects_excerpt"])

    unknown = []
    for field_path, value in [
        ("majors.count", record["majors"]["count"]),
        ("admissions.testing_policy", record["admissions"]["testing_policy"]),
        ("admissions.gpa_policy", record["admissions"]["gpa_policy"]),
        ("admissions.course_rigor", record["admissions"]["course_rigor"]),
        ("admissions.recommendations", record["admissions"]["recommendations"]),
        ("admissions.essays", record["admissions"]["essays"]),
    ]:
        if value in (None, "unknown", [], ""):
            unknown.append(field_path)
    if not record["competitive_signals"]["projects_research"]:
        unknown.append("competitive_signals.projects_research")

    warnings = [w for w in record["verification"]["warnings"] if "source validation only" not in w]
    warnings.append("Structured pilot extraction completed using curated official-source rules for accessible schools.")
    warnings.extend(facts.get("warnings", []))

    record["verification"]["last_verified_at"] = now_iso()
    record["verification"]["confidence"] = "structured-pilot"
    record["verification"]["unknown_fields"] = unknown
    record["verification"]["warnings"] = warnings
    save_record(record)
    return record


def build_rollups(records: list[dict]) -> None:
    REQ_DIR.mkdir(parents=True, exist_ok=True)
    MAJ_DIR.mkdir(parents=True, exist_ok=True)
    testing = []
    majors = []
    for r in records:
        testing.append({
            "slug": r["slug"],
            "name": r["name"],
            "testing_policy": r["admissions"]["testing_policy"],
            "confidence": r["verification"]["confidence"],
        })
        majors.append({
            "slug": r["slug"],
            "name": r["name"],
            "majors_count": r["majors"]["count"],
            "count_method": r["majors"]["count_method"],
        })
    (REQ_DIR / "testing_policy_pilot.json").write_text(json.dumps(testing, indent=2))
    (MAJ_DIR / "majors_counts_pilot.json").write_text(json.dumps(majors, indent=2))


def main() -> int:
    records = [update_record(slug) for slug in ["mit", "stanford", "harvard", "uc-berkeley", "michigan"]]
    build_rollups(records)
    print(json.dumps([
        {
            "slug": r["slug"],
            "majors_count": r["majors"]["count"],
            "testing_policy": r["admissions"]["testing_policy"],
            "unknown_fields": r["verification"]["unknown_fields"],
        }
        for r in records
    ], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
