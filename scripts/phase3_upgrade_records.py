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

    md = [
        "---",
        f"name: {record['name']}",
        f"short_name: {record['short_name']}",
        f"slug: {record['slug']}",
        f"rank: {record['rank']}",
        f"official_domain: {record['official_domain']}",
        "status: phase-3-structured",
        "---",
        "",
        f"# {record['name']}",
        "",
        "## Official sources",
    ]
    for kind in ["admissions", "majors"]:
        md.append(f"### {kind.title()}")
        for url in record["source_urls"][kind]:
            md.append(f"- {url}")
        md.append("")

    md += [
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
    for field, values in record["competitive_signals"].items():
        if values:
            md.append(f"### {field}")
            for value in values:
                md.append(f"- {value}")
    md += ["", "## Warnings"]
    for warning in record["verification"]["warnings"]:
        md.append(f"- {warning}")
    (UNI_DIR / f"{record['slug']}.md").write_text("\n".join(md))


def upsert_evidence(record: dict, field: str, claim: str, classification: str, source_url: str, source_excerpt: str) -> None:
    evidence = record.setdefault("evidence", [])
    key = (field, claim, source_url)
    filtered = [
        item for item in evidence
        if (item.get("field"), item.get("claim"), item.get("source_url")) != key
    ]
    filtered.append({
        "field": field,
        "claim": claim,
        "classification": classification,
        "source_url": source_url,
        "source_excerpt": source_excerpt,
        "retrieved_at": now_iso(),
    })
    record["evidence"] = filtered


PHASE3_FACTS = {
    "mit": {
        "majors_count": 55,
        "majors_method": "counted official MIT undergraduate SB degree-chart links on the MIT Course Catalog Degree Charts page; count includes named SB degree options and interdisciplinary SB programs",
        "majors_url": "https://catalog.mit.edu/degree-charts/",
        "majors_excerpt": "The undergraduate degree charts page lists undergraduate SB degree-chart links; a phase-3 filtered count of SB charts yielded 55.",
        "testing_policy": "MIT requires the SAT or the ACT.",
        "testing_url": "https://mitadmissions.org/apply/firstyear/tests-scores/",
        "testing_excerpt": "Testing requirement: We require the SAT or the ACT.",
        "gpa_policy": "MIT does not publish a minimum GPA cutoff on the cited first-year pages.",
        "course_rigor": "MIT asks applicants to submit transcripts and evaluates essays, activities, academics, and the overall academic record; no simple minimum course-rigor rule is stated on the cited pages.",
        "recommendations": "MIT requires letters of recommendation as part of the first-year application materials.",
        "recommendations_url": "https://mitadmissions.org/apply/firstyear/",
        "recommendations_excerpt": "First-year applicants page lists application materials including 'Letters of recommendation'.",
        "essays": "MIT requires an essays, activities, and academics section as part of the first-year application.",
        "essays_url": "https://mitadmissions.org/apply/firstyear/essays-activities-academics/",
        "essays_excerpt": "Essays, activities & academics | MIT Admissions",
        "projects_research": [
            "MIT explicitly evaluates essays, activities, and academics as part of the first-year application process."
        ],
        "warnings": [
            "MIT majors count is a curated count of official undergraduate SB degree-chart links, not a registrar-published sentence like 'MIT offers X majors'."
        ],
    },
    "stanford": {
        "majors_count": 100,
        "majors_method": "counted unique Stanford Explore Majors opportunity pages on the official text-only list, excluding the one explicit minor-labeled entry 'Dance (TAPS Minor)'",
        "majors_url": "https://majors.stanford.edu/majors/text-only-lists-majors-and-offerings",
        "majors_excerpt": "The official Stanford text-only list contains 101 unique opportunity pages; excluding the explicit minor-labeled entry leaves 100 major/offering pages.",
        "testing_policy": "ACT or SAT scores are required for first-year and transfer students; Stanford also says there are no minimum test scores required for admission.",
        "testing_url": "https://admission.stanford.edu/apply/first-year/testing.html",
        "testing_excerpt": "ACT or SAT scores are required for first-year and transfer students. There are no minimum test scores required to be admitted to Stanford.",
        "gpa_policy": "No explicit minimum GPA found in the cited Stanford first-year pages.",
        "course_rigor": "Stanford says every component of the application is valuable and that there is no score guaranteeing admission; the cited pages do not state a simple minimum course-rigor formula.",
        "recommendations": "Stanford requires a school report form and counselor letter of recommendation plus letters of recommendation from two teachers.",
        "recommendations_url": "https://admission.stanford.edu/apply/first-year/index.html",
        "recommendations_excerpt": "School Report form and counselor letter of recommendation ... Letters of recommendation from two teachers.",
        "essays": "Stanford's first-year application materials include application and essays guidance, but a structured official essay-count extraction was not completed in this pass.",
        "projects_research": [],
        "warnings": [
            "Stanford majors count comes from the official 'Majors and Offerings' site and likely still includes some offerings that are not standalone majors."
        ],
    },
    "harvard": {
        "majors_count": 50,
        "majors_method": "official Harvard page states 50 undergraduate fields of study (concentrations)",
        "majors_url": "https://college.harvard.edu/academics/liberal-arts-sciences",
        "majors_excerpt": "We offer more than 3,700 courses in 50 undergraduate fields of study, which we call concentrations.",
        "testing_policy": "Harvard requires SAT or ACT, with alternative exams accepted in exceptional cases when those tests are not accessible.",
        "testing_url": "https://college.harvard.edu/admissions/apply/first-year-applicants",
        "testing_excerpt": "$90 fee ... SAT or ACT - In exceptional cases when those tests are not accessible, one of the following can meet the requirement: AP, IB, GCSE/A-Level, or national leaving exam results.",
        "gpa_policy": "Harvard does not state a simple minimum GPA on the cited first-year page.",
        "course_rigor": "Harvard emphasizes academic accomplishment and broad liberal arts and sciences study, but the cited page does not provide a single minimum course-rigor formula.",
        "recommendations": "Harvard requires a school report that includes a counselor letter and two teacher recommendations.",
        "recommendations_url": "https://college.harvard.edu/admissions/apply/first-year-applicants",
        "recommendations_excerpt": "School Report (which includes a counselor letter) and high school transcript; Teacher Recommendations (2).",
        "essays": "Harvard requires a personal essay plus five required short-answer Harvard supplement questions.",
        "essays_url": "https://college.harvard.edu/admissions/apply/first-year-applicants",
        "essays_excerpt": "Personal essay ... There are five required short-answer questions with 150 word limits for each.",
        "projects_research": [
            "Harvard says students can participate in hands-on research projects from the moment they arrive.",
            "Harvard admissions says many factors matter beyond academic accomplishment, including special talents and potential contributions to the community."
        ],
        "warnings": [],
    },
    "uc-berkeley": {
        "majors_count": 113,
        "majors_method": "counted official UC Berkeley Catalog results after enabling the 'Major' filter on the Programs page",
        "majors_url": "https://undergraduate.catalog.berkeley.edu/programs",
        "majors_excerpt": "With the official 'Major' filter selected, the Programs page reports 113 results found.",
        "testing_policy": "UC Berkeley follows the University of California first-year requirements page cited here, which lists A-G coursework and GPA requirements and does not require SAT/ACT scores on that page; this pass does not attach a Berkeley-only test-policy sentence.",
        "testing_url": "https://admission.universityofcalifornia.edu/admission-requirements/freshman-requirements/index.html",
        "testing_excerpt": "The UC first-year requirements page lists A-G coursework and GPA requirements and does not list SAT/ACT as a required step on the page used in this pass.",
        "gpa_policy": "Students applying to Berkeley should meet minimum requirements including a 3.0 GPA in A-G courses taken in the 10th and 11th grades, but Berkeley warns that satisfying minimum requirements is often not enough to be competitive for selection.",
        "gpa_url": "https://admissions.berkeley.edu/apply-to-berkeley/first-year-applicants-uc-berkeley/",
        "gpa_excerpt": "Students who apply to Berkeley should meet the following minimum requirements ... Have a 3.0 GPA in A-G courses taken in the 10th and 11th grades ... satisfying the minimum requirements is often not enough to be competitive for selection.",
        "course_rigor": "Berkeley says it selects first-year students through a holistic review that considers weighted and unweighted UC GPA, planned 12th-grade courses, and the full record of achievement in college preparatory courses.",
        "course_rigor_url": "https://admissions.berkeley.edu/apply-to-berkeley/first-year-applicants-uc-berkeley/",
        "course_rigor_excerpt": "The campus selects its first-year class through an assessment that includes a holistic review of your academic performance ... your weighted and unweighted UC GPA ... planned 12th grade courses ... full record of achievement in college preparatory courses.",
        "recommendations": "unknown from the official Berkeley and UC pages used in this pass",
        "essays": "unknown from the official Berkeley and UC pages used in this pass",
        "projects_research": [
            "Berkeley considers personal qualities including leadership ability, character, motivation, insight, tenacity, initiative, originality, intellectual independence, responsibility, maturity, and demonstrated concern for others and for the community.",
            "Berkeley considers accomplishments in a field of intellectual or creative endeavor, extracurricular activities, leadership, employment, and volunteer service."
        ],
        "projects_url": "https://admissions.berkeley.edu/apply-to-berkeley/first-year-applicants-uc-berkeley/",
        "projects_excerpt": "Personal qualities ... leadership ability ... initiative ... concern for others and for the community ... accomplishments in extracurricular activities ... leadership ... employment; and volunteer service.",
        "warnings": [
            "Berkeley testing policy is still tied to the broader University of California requirements page rather than a Berkeley-only sentence captured in this pass."
        ],
    },
    "michigan": {
        "majors_count": None,
        "majors_method": "blocked by bot protection during phase 3 checks",
        "testing_policy": "unknown",
        "gpa_policy": "unknown",
        "course_rigor": "unknown",
        "recommendations": "unknown",
        "essays": "unknown",
        "projects_research": [],
        "warnings": [
            "University of Michigan pages tested in this environment still returned Cloudflare-style bot protection during phase 3."
        ],
    },
}


def update_record(slug: str) -> dict:
    record = load_record(slug)
    facts = PHASE3_FACTS[slug]

    record["majors"]["count"] = facts["majors_count"]
    record["majors"]["count_method"] = facts["majors_method"]
    record["majors"]["notes"] = facts["majors_method"]
    record["majors"]["confidence"] = "medium" if facts["majors_count"] is not None else "low"

    record["admissions"]["testing_policy"] = facts["testing_policy"]
    record["admissions"]["gpa_policy"] = facts["gpa_policy"]
    record["admissions"]["course_rigor"] = facts["course_rigor"]
    record["admissions"]["recommendations"] = facts["recommendations"]
    record["admissions"]["essays"] = facts["essays"]
    record["competitive_signals"]["projects_research"] = facts.get("projects_research", [])

    if facts.get("majors_url") and facts.get("majors_count") is not None:
        upsert_evidence(record, "majors.count", f"Majors/program count recorded as {facts['majors_count']}", "official_recommendation", facts["majors_url"], facts["majors_excerpt"])
    if facts.get("testing_url") and facts.get("testing_policy") != "unknown":
        upsert_evidence(record, "admissions.testing_policy", facts["testing_policy"], "official_requirement", facts["testing_url"], facts["testing_excerpt"])
    if facts.get("gpa_url"):
        upsert_evidence(record, "admissions.gpa_policy", facts["gpa_policy"], "reported_profile", facts["gpa_url"], facts["gpa_excerpt"])
    if facts.get("course_rigor_url"):
        upsert_evidence(record, "admissions.course_rigor", facts["course_rigor"], "reported_profile", facts["course_rigor_url"], facts["course_rigor_excerpt"])
    if facts.get("recommendations_url") and facts.get("recommendations") != "unknown":
        upsert_evidence(record, "admissions.recommendations", facts["recommendations"], "official_requirement", facts["recommendations_url"], facts["recommendations_excerpt"])
    if facts.get("essays_url") and facts.get("essays") != "unknown":
        upsert_evidence(record, "admissions.essays", facts["essays"], "official_requirement", facts["essays_url"], facts["essays_excerpt"])
    if facts.get("projects_url") and facts.get("projects_research"):
        upsert_evidence(record, "competitive_signals.projects_research", "; ".join(facts["projects_research"]), "reported_profile", facts["projects_url"], facts["projects_excerpt"])

    unknown = []
    checks = [
        ("majors.count", record["majors"]["count"]),
        ("admissions.testing_policy", record["admissions"]["testing_policy"]),
        ("admissions.gpa_policy", record["admissions"]["gpa_policy"]),
        ("admissions.course_rigor", record["admissions"]["course_rigor"]),
        ("admissions.recommendations", record["admissions"]["recommendations"]),
        ("admissions.essays", record["admissions"]["essays"]),
    ]
    for field_path, value in checks:
        if value in (None, "unknown", [], "") or (isinstance(value, str) and value.startswith("unknown")):
            unknown.append(field_path)
    if not record["competitive_signals"]["projects_research"]:
        unknown.append("competitive_signals.projects_research")

    warnings = [
        w for w in record["verification"]["warnings"]
        if "source validation only" not in w.lower() and "structured pilot extraction completed" not in w.lower()
    ]
    warnings.append("Phase 3 structured upgrade completed with improved majors counting, admissions extraction, and query-ready records.")
    warnings.extend(facts.get("warnings", []))

    record["verification"]["last_verified_at"] = now_iso()
    record["verification"]["confidence"] = "phase-3-structured"
    record["verification"]["unknown_fields"] = unknown
    record["verification"]["warnings"] = warnings
    save_record(record)
    return record


def write_rollups(records: list[dict]) -> None:
    REQ_DIR.mkdir(parents=True, exist_ok=True)
    MAJ_DIR.mkdir(parents=True, exist_ok=True)

    testing = []
    majors = []
    for record in records:
        testing.append({
            "slug": record["slug"],
            "name": record["name"],
            "testing_policy": record["admissions"]["testing_policy"],
            "confidence": record["verification"]["confidence"],
            "unknown_fields": record["verification"]["unknown_fields"],
        })
        majors.append({
            "slug": record["slug"],
            "name": record["name"],
            "majors_count": record["majors"]["count"],
            "count_method": record["majors"]["count_method"],
            "confidence": record["majors"]["confidence"],
        })

    (REQ_DIR / "testing_policy_phase3.json").write_text(json.dumps(testing, indent=2))
    (MAJ_DIR / "majors_counts_phase3.json").write_text(json.dumps(majors, indent=2))


def main() -> int:
    slugs = ["mit", "stanford", "harvard", "uc-berkeley", "michigan"]
    records = [update_record(slug) for slug in slugs]
    write_rollups(records)
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
