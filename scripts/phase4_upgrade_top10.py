#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNI_DIR = ROOT / "knowledgebase" / "universities"
REQ_DIR = ROOT / "knowledgebase" / "requirements"
MAJ_DIR = ROOT / "knowledgebase" / "majors"
PROGRESS_PATH = ROOT / "data" / "progress.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_record(slug: str) -> dict:
    return json.loads((UNI_DIR / f"{slug}.json").read_text())


def load_progress() -> dict:
    if PROGRESS_PATH.exists():
        return json.loads(PROGRESS_PATH.read_text())
    return {"updated_at": None, "schools": {}}


def save_progress(progress: dict) -> None:
    progress["updated_at"] = now_iso()
    PROGRESS_PATH.write_text(json.dumps(progress, indent=2))


def clean_evidence(record: dict) -> None:
    record["evidence"] = [
        item for item in record.get("evidence", [])
        if item.get("field") and item.get("source_url")
    ]


def upsert_evidence(record: dict, field: str, claim: str, classification: str, source_url: str, source_excerpt: str) -> None:
    clean_evidence(record)
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


def save_record(record: dict) -> None:
    clean_evidence(record)
    (UNI_DIR / f"{record['slug']}.json").write_text(json.dumps(record, indent=2))

    md_lines = [
        "---",
        f"name: {record['name']}",
        f"short_name: {record['short_name']}",
        f"slug: {record['slug']}",
        f"rank: {record['rank']}",
        f"official_domain: {record['official_domain']}",
        "status: phase-4-top10-structured",
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
    for field, values in record["competitive_signals"].items():
        if values:
            md_lines.append(f"### {field}")
            for value in values:
                md_lines.append(f"- {value}")
    md_lines += ["", "## Warnings"]
    for warning in record["verification"]["warnings"]:
        md_lines.append(f"- {warning}")
    (UNI_DIR / f"{record['slug']}.md").write_text("\n".join(md_lines))


FACTS = {
    "princeton": {
        "source_urls": {
            "admissions": [
                "https://admission.princeton.edu/apply/application-checklist",
                "https://admission.princeton.edu/apply/standardized-testing",
                "https://admission.princeton.edu/apply/princeton-specific-questions",
            ],
            "majors": [
                "https://admission.princeton.edu/academics/degrees-departments",
            ],
        },
        "majors_count": 37,
        "majors_method": "official Princeton Admission Degrees & Departments page states students can choose from among 37 concentrations",
        "majors_excerpt": "Within these degree programs, students can choose from among 37 concentrations (computer science offers both A.B. and B.S.E.) and over 50 minors and interdepartmental certificate programs.",
        "majors_url": "https://admission.princeton.edu/academics/degrees-departments",
        "testing_policy": "Princeton is test-optional for first-year applicants applying for fall 2026 and fall 2027 entry; Princeton says it will once again require testing for students applying for fall 2028 entry.",
        "testing_excerpt": "Our test optional policy continues to be in place for first-year applicants applying for fall 2026 and fall 2027 entry. We will once again require testing for students applying for fall 2028 entry.",
        "testing_url": "https://admission.princeton.edu/apply/application-checklist",
        "gpa_policy": "Princeton does not publish a minimum GPA on the cited admissions pages.",
        "course_rigor": "No simple minimum course-rigor formula is stated on the cited Princeton pages, but Princeton asks for teacher recommendations from higher level courses in core academic areas.",
        "recommendations": "Princeton requires a counselor recommendation plus two teacher recommendations from higher level courses in different academic areas.",
        "recommendations_excerpt": "Counselor Recommendation ... Two (2) Teacher Recommendations. Please ask two of your teachers who have taught you in higher level courses ... in different academic areas of study.",
        "recommendations_url": "https://admission.princeton.edu/apply/application-checklist",
        "essays": "Princeton requires Princeton-specific questions and a graded written paper for first-year applicants.",
        "essays_excerpt": "Princeton University requires you to answer Princeton-specific questions ... Princeton also requires you to submit a graded written paper as part of your application.",
        "essays_url": "https://admission.princeton.edu/apply/princeton-specific-questions",
        "projects_research": [
            "Princeton describes itself as a research institution that also prides itself on its liberal arts curriculum."
        ],
        "projects_url": "https://admission.princeton.edu/apply/princeton-specific-questions",
        "projects_excerpt": "As a research institution that also prides itself on its liberal arts curriculum, Princeton allows students to explore areas across the humanities and the arts, the natural sciences, and the social sciences.",
        "warnings": [],
    },
    "yale": {
        "source_urls": {
            "admissions": [
                "https://admissions.yale.edu/requirements",
                "https://admissions.yale.edu/standardized-testing",
                "https://admissions.yale.edu/essay-topics",
            ],
            "majors": [
                "https://admissions.yale.edu/majors",
                "https://catalog.yale.edu/ycps/majors-in-yale-college/",
            ],
        },
        "majors_count": 81,
        "majors_method": "counted unique Yale College major entries (B.A./B.S.) on the official Yale catalog page 'Majors in Yale College'",
        "majors_excerpt": "A phase-4 count of unique B.A./B.S. entries on Yale's official 'Majors in Yale College' page yielded 81 majors; the Yale admissions page also says students can choose from over 80 majors.",
        "majors_url": "https://catalog.yale.edu/ycps/majors-in-yale-college/",
        "testing_policy": "Yale uses a test-flexible policy that requires first-year applicants to submit scores from one or more of the following: ACT, AP, IB, or SAT.",
        "testing_excerpt": "Yale's test-flexible policy requires applicants to submit scores from one or more of the following exams: ACT, AP, IB, or SAT.",
        "testing_url": "https://admissions.yale.edu/standardized-testing",
        "gpa_policy": "Yale does not publish a minimum GPA on the cited admissions pages.",
        "course_rigor": "The cited Yale admissions pages do not provide a single minimum course-rigor formula.",
        "recommendations": "Yale requires letters of recommendation from two teachers and one counselor, plus a school report with transcript.",
        "recommendations_excerpt": "Letters of recommendation from two teachers and one counselor School Report with transcript Standardized test results (ACT, AP, IB or SAT).",
        "recommendations_url": "https://admissions.yale.edu/requirements",
        "essays": "Yale requires Yale-specific short essays for first-year applicants.",
        "essays_excerpt": "First-year applicants complete Yale-specific short essays. Review the 2025-2026 essay topics for all applications.",
        "essays_url": "https://admissions.yale.edu/essay-topics",
        "projects_research": [
            "Yale allows applicants to submit supplementary material showcasing STEM research."
        ],
        "projects_url": "https://admissions.yale.edu/apply",
        "projects_excerpt": "Supplements Applicants may submit supplementary material showcasing Visual Art, Dance, Music, Film, or STEM research.",
        "warnings": [],
    },
    "caltech": {
        "source_urls": {
            "admissions": [
                "https://www.admissions.caltech.edu/apply/first-year-applicants/application-requirements",
                "https://www.admissions.caltech.edu/apply/first-year-applicants/standardized-tests",
                "https://www.admissions.caltech.edu/apply/first-year-applicants/academic-requirements-for-first-year-applicants",
                "https://www.admissions.caltech.edu/apply/first-year-applicants/letters-of-recommendation",
                "https://www.admissions.caltech.edu/apply/first-year-applicants/supplemental-application-essays",
            ],
            "majors": [
                "https://www.admissions.caltech.edu/why-caltech/academics/majors-minors",
            ],
        },
        "majors_count": 31,
        "majors_method": "counted unique program pages linked from the official Caltech 'Majors & Minors' page",
        "majors_excerpt": "A phase-4 count of unique major/minor program pages linked from Caltech's official 'Majors & Minors' page yielded 31 programs.",
        "majors_url": "https://www.admissions.caltech.edu/why-caltech/academics/majors-minors",
        "testing_policy": "Caltech requires first-year applicants to submit either the SAT or the ACT.",
        "testing_excerpt": "Caltech requires first-year applicants to submit either the SAT or the ACT for admissions to Caltech.",
        "testing_url": "https://www.admissions.caltech.edu/apply/first-year-applicants/standardized-tests",
        "gpa_policy": "Caltech does not publish a minimum GPA on the cited admissions pages.",
        "course_rigor": "Caltech expects mastery in four years of math including calculus, one year each of physics and chemistry, one year of biology recommended, four years of English, and two years of history and/or social sciences with three or more years recommended.",
        "course_rigor_excerpt": "Four years of math, including one year of calculus ... One year of physics ... One year of chemistry ... One year of biology (recommended) ... Four years of English ... Two years of history and/or social sciences courses (3+ years recommended).",
        "course_rigor_url": "https://www.admissions.caltech.edu/apply/first-year-applicants/academic-requirements-for-first-year-applicants",
        "recommendations": "Caltech requires two teacher or instructor recommendations, one STEM and one humanities/social sciences.",
        "recommendations_excerpt": "Caltech requires letters of recommendation from two teachers or instructors ... One letter each from the subjects below: STEM ... Humanities/Social Sciences ...",
        "recommendations_url": "https://www.admissions.caltech.edu/apply/first-year-applicants/letters-of-recommendation",
        "essays": "Caltech requires multiple supplemental essay responses, including a required STEM academic interest question, one STEM experience prompt, a creativity in action question, and two required short-answer questions.",
        "essays_excerpt": "Required STEM Academic Interest Question ... Select one of the following two STEM Experience prompts ... Creativity in Action Question ... Required Short Answer Questions ... Choose two of the four questions below and answer both.",
        "essays_url": "https://www.admissions.caltech.edu/apply/first-year-applicants/supplemental-application-essays",
        "projects_research": [
            "Caltech highlights undergraduate research as a core part of the undergraduate experience."
        ],
        "projects_url": "https://www.admissions.caltech.edu/why-caltech/research/undergraduate-research",
        "projects_excerpt": "Undergraduate Research - Undergraduate Admissions",
        "warnings": [],
    },
    "uchicago": {
        "source_urls": {
            "admissions": [
                "https://collegeadmissions.uchicago.edu/apply/application/required-materials/",
            ],
            "majors": [
                "https://collegeadmissions.uchicago.edu/academics/areas-of-study/",
            ],
        },
        "majors_count": 70,
        "majors_method": "official UChicago Areas of Study page says the College includes nearly 70 majors and 60 minors",
        "majors_excerpt": "All of the University of Chicago's nearly 70 majors and 60 minors, as well as dozens of areas of specialized study and pre-professional preparation, are part of one undergraduate College.",
        "majors_url": "https://collegeadmissions.uchicago.edu/academics/areas-of-study/",
        "testing_policy": "UChicago is test-optional and says submitting an SAT or ACT is optional and not required for admission; it also uses a 'No Harm' testing policy.",
        "testing_excerpt": "Submitting an SAT or ACT is optional and not required for admission. In addition to being test-optional, UChicago practices a 'No Harm' policy for application review when considering SAT or ACT scores.",
        "testing_url": "https://collegeadmissions.uchicago.edu/apply/application/required-materials/",
        "gpa_policy": "UChicago does not publish a minimum GPA on the cited admissions page.",
        "course_rigor": "UChicago does not provide a single minimum course-rigor formula on the cited required-materials page.",
        "recommendations": "UChicago requires two teacher evaluations and a secondary school report with school counselor recommendation.",
        "recommendations_excerpt": "Two Teacher Evaluations ... We require two recommendations from teachers who have taught you in an academic subject ... Secondary School Report and School Counselor Recommendation.",
        "recommendations_url": "https://collegeadmissions.uchicago.edu/apply/application/required-materials/",
        "essays": "UChicago requires two supplemental essays overall, and its supplement specifically includes one extended essay and one short 'why UChicago' essay.",
        "essays_excerpt": "If you apply to the University of Chicago, you will also submit two supplemental essays ... The University of Chicago Supplement requires one extended essay ... and one short essay on why you would like to attend the University of Chicago.",
        "essays_url": "https://collegeadmissions.uchicago.edu/apply/application/required-materials/",
        "projects_research": [
            "UChicago says extracurricular activities help show what is meaningful, worthwhile, or interesting to you outside of class."
        ],
        "projects_url": "https://collegeadmissions.uchicago.edu/apply/application/required-materials/",
        "projects_excerpt": "Colleges ask for extracurricular information not because they have any specific expectation or preference for how you spend your time, but to see what's meaningful, worthwhile, or interesting to you.",
        "warnings": [],
    },
    "upenn": {
        "source_urls": {
            "admissions": [
                "https://admissions.upenn.edu/how-to-apply/preparing-your-application/testing",
                "https://admissions.upenn.edu/how-to-apply/preparing-your-application/academics",
                "https://admissions.upenn.edu/how-to-apply/preparing-your-application/letters-of-recommendation",
                "https://admissions.upenn.edu/how-to-apply/preparing-your-application/writing",
            ],
            "majors": [
                "https://admissions.upenn.edu/academics/exploring-academics/majors-minors",
            ],
        },
        "majors_count": 86,
        "majors_method": "counted visible major/concentration/program entries listed across Penn's undergraduate schools on the official Penn Admissions 'Majors and Minors' page; minors were excluded from the count",
        "majors_excerpt": "A phase-4 DOM count of major/concentration/program entries on Penn's official 'Majors and Minors' page yielded 86 non-minor undergraduate pathways across Penn's schools.",
        "majors_url": "https://admissions.upenn.edu/academics/exploring-academics/majors-minors",
        "testing_policy": "Penn requires applicants to submit the SAT or ACT for the 2025-26 application cycle, with a waiver available for hardship cases.",
        "testing_excerpt": "Penn applicants are required to submit the SAT or ACT for the 2025-26 application cycle. Applicants who face hardship in meeting this requirement can submit a waiver instead.",
        "testing_url": "https://admissions.upenn.edu/how-to-apply/preparing-your-application/testing",
        "gpa_policy": "Penn does not publish a minimum GPA on the cited admissions pages.",
        "course_rigor": "Penn evaluates the rigor available at a student's high school and asks whether the student took advantage of rigorous courses available in core subjects.",
        "course_rigor_excerpt": "Are you taking advantage of rigorous courses available in your high school? ... Do your grades in core subject areas show you are prepared for the specific academic program you have selected?",
        "course_rigor_url": "https://admissions.upenn.edu/how-to-apply/preparing-your-application/academics",
        "recommendations": "Penn requires recommendation letters from two people: a school counselor or other school administrator and a teacher in a core subject area; one additional recommendation is optional.",
        "recommendations_excerpt": "You will need to request recommendation letters from two people: your school counselor or other school administrator; a teacher in a core subject area ... You may also opt to submit one additional letter of recommendation.",
        "recommendations_url": "https://admissions.upenn.edu/how-to-apply/preparing-your-application/letters-of-recommendation",
        "essays": "Penn asks every applicant to complete two prompts and a school-specific prompt based on the undergraduate school or dual-degree program.",
        "essays_excerpt": "There are two prompts we ask every Penn applicant to complete. Additionally, there is a school-specific prompt based on the undergraduate school or dual-degree program to which you are applying.",
        "essays_url": "https://admissions.upenn.edu/how-to-apply/preparing-your-application/writing",
        "projects_research": [
            "Penn says there are endless opportunities for every student to engage in research that aligns with their interests."
        ],
        "projects_url": "https://admissions.upenn.edu/academics/research",
        "projects_excerpt": "Through Penn's wide-ranging network spanning our graduate schools, hospitals, and more, there are endless opportunities for every Penn student to engage in research that aligns with their interests.",
        "warnings": [
            "Penn majors count is a curated admissions-page count of visible undergraduate pathways across multiple schools, not a registrar-issued single-major total from one academic catalog page."
        ],
    },
    "duke": {
        "source_urls": {
            "admissions": [
                "https://admissions.duke.edu/apply/",
                "https://admissions.duke.edu/what-we-look-for/",
            ],
            "majors": [
                "https://admissions.duke.edu/academic-possibilities/",
            ],
        },
        "majors_count": 63,
        "majors_method": "official Duke 'Majors, Minors, and More' page states Duke offers 63 majors, 61 minors, and 23 certificates",
        "majors_excerpt": "Duke University offers 63 majors, 61 minors, and 23 certificates.",
        "majors_url": "https://admissions.duke.edu/academic-possibilities/",
        "testing_policy": "Duke is test-optional for first-year and transfer applicants in the 2026-2027 admissions cycle.",
        "testing_excerpt": "Duke University is test-optional for both first-year and transfer applicants in the 2026-2027 admissions cycle. Students who apply without SAT or ACT scores this year will not be at a disadvantage.",
        "testing_url": "https://admissions.duke.edu/apply/",
        "gpa_policy": "Duke does not publish a minimum GPA on the cited admissions pages.",
        "course_rigor": "Duke says it is guided by the rigor of a candidate's academic program and generally expects students to enroll in five academic courses per year, taking the best available and most challenging courses.",
        "course_rigor_excerpt": "The rigor of a candidate's academic program ... Enroll in the best available and most challenging courses. We generally expect students to enroll in five academic courses per year.",
        "course_rigor_url": "https://admissions.duke.edu/what-we-look-for/",
        "recommendations": "Duke requires a secondary school report with counselor recommendation and two teacher recommendations.",
        "recommendations_excerpt": "Secondary School Report with Counselor Recommendation Two Teacher Recommendations",
        "recommendations_url": "https://admissions.duke.edu/apply/",
        "essays": "Duke requires a one-page personal essay and short-answer questions specific to Duke.",
        "essays_excerpt": "Applications for admission require a one-page personal essay, along with short-answer questions specific to Duke.",
        "essays_url": "https://admissions.duke.edu/what-we-look-for/",
        "projects_research": [
            "Duke highlights undergraduate research as an academic opportunity and says extracurricular activities are one of its five primary review factors."
        ],
        "projects_url": "https://admissions.duke.edu/academic-possibilities/",
        "projects_excerpt": "Academic Opportunities ... Undergraduate Research ... Duke says extracurricular activities are one of its five primary review factors.",
        "warnings": [],
    },
    "columbia": {
        "source_urls": {
            "admissions": [
                "https://undergrad.admissions.columbia.edu/apply/firstyear",
            ],
            "majors": [
                "https://bulletin.columbia.edu/columbia-college/departments-instruction/",
            ],
        },
        "majors_count": None,
        "majors_method": "official Columbia admissions pages were blocked by CloudFront in this environment; Columbia bulletin pages were partially accessible but not enough to derive a reliable undergraduate majors total here",
        "testing_policy": "unknown",
        "gpa_policy": "unknown",
        "course_rigor": "unknown",
        "recommendations": "unknown",
        "essays": "unknown",
        "projects_research": [],
        "warnings": [
            "Columbia admissions pages returned 403 / CloudFront blocks in this environment during phase 4.",
            "Columbia bulletin pages were partially accessible, but a reliable structured admissions extraction was not completed in this pass."
        ],
    },
}


def update_record(slug: str) -> dict:
    record = load_record(slug)
    facts = FACTS[slug]

    record["source_urls"]["admissions"] = facts["source_urls"]["admissions"]
    record["source_urls"]["majors"] = facts["source_urls"]["majors"]

    record["majors"]["count"] = facts["majors_count"]
    record["majors"]["count_method"] = facts["majors_method"]
    record["majors"]["notes"] = facts["majors_method"]
    record["majors"]["confidence"] = "medium" if facts["majors_count"] is not None else "low"

    record["admissions"]["testing_policy"] = facts["testing_policy"]
    record["admissions"]["gpa_policy"] = facts["gpa_policy"]
    record["admissions"]["course_rigor"] = facts["course_rigor"]
    record["admissions"]["recommendations"] = facts["recommendations"]
    record["admissions"]["essays"] = facts["essays"]
    record["competitive_signals"]["projects_research"] = facts["projects_research"]

    if facts.get("majors_url") and facts.get("majors_count") is not None:
        upsert_evidence(record, "majors.count", f"Majors/program count recorded as {facts['majors_count']}", "official_recommendation", facts["majors_url"], facts["majors_excerpt"])
    if facts.get("testing_url") and facts.get("testing_policy") != "unknown":
        upsert_evidence(record, "admissions.testing_policy", facts["testing_policy"], "official_requirement", facts["testing_url"], facts["testing_excerpt"])
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

    record["verification"]["last_verified_at"] = now_iso()
    record["verification"]["confidence"] = "phase-4-top10-structured" if slug != "columbia" else "phase-4-partial"
    record["verification"]["unknown_fields"] = unknown
    warnings = [
        w for w in record["verification"].get("warnings", [])
        if "scaffold only" not in w.lower()
    ]
    warnings.append("Phase 4 structured upgrade applied to top-10 expansion schools.")
    warnings.extend(facts.get("warnings", []))
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
    (REQ_DIR / "testing_policy_phase4_top10.json").write_text(json.dumps(testing, indent=2))
    (MAJ_DIR / "majors_counts_phase4_top10.json").write_text(json.dumps(majors, indent=2))


def update_progress(records: list[dict]) -> None:
    progress = load_progress()
    progress.setdefault("schools", {})
    for record in records:
        slug = record["slug"]
        school = progress["schools"].setdefault(slug, {"name": record["name"], "rank": record["rank"]})
        school.update({
            "name": record["name"],
            "rank": record["rank"],
            "status": "done" if slug != "columbia" else "partial",
            "last_run_at": now_iso(),
            "output_markdown": str(UNI_DIR / f"{slug}.md"),
            "output_json": str(UNI_DIR / f"{slug}.json"),
            "notes": "phase-4 structured upgrade" if slug != "columbia" else "phase-4 partial upgrade; admissions blocked",
        })
    save_progress(progress)


def main() -> int:
    slugs = ["princeton", "yale", "caltech", "uchicago", "upenn", "columbia", "duke"]
    records = [update_record(slug) for slug in slugs]
    write_rollups(records)
    update_progress(records)
    print(json.dumps([
        {
            "slug": r["slug"],
            "majors_count": r["majors"]["count"],
            "testing_policy": r["admissions"]["testing_policy"],
            "unknown_fields": r["verification"]["unknown_fields"],
            "confidence": r["verification"]["confidence"],
        }
        for r in records
    ], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
