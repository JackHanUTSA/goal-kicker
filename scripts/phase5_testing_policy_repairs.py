#!/usr/bin/env /usr/bin/python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNI_DIR = ROOT / "knowledgebase" / "universities"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load(slug: str) -> dict:
    return json.loads((UNI_DIR / f"{slug}.json").read_text())


def save(record: dict) -> None:
    (UNI_DIR / f"{record['slug']}.json").write_text(json.dumps(record, indent=2))
    md_lines = [
        "---",
        f"name: {record['name']}",
        f"short_name: {record['short_name']}",
        f"slug: {record['slug']}",
        f"rank: {record['rank']}",
        f"official_domain: {record['official_domain']}",
        f"status: {record['verification']['confidence']}",
        "---",
        "",
        f"# {record['name']}",
        "",
        "## Structured extraction",
        f"- Majors count: {record['majors']['count']}",
        f"- Count method: {record['majors']['count_method']}",
        f"- Testing policy: {record['admissions']['testing_policy']}",
        f"- GPA policy: {record['admissions']['gpa_policy']}",
        f"- Course rigor: {record['admissions']['course_rigor']}",
        f"- Recommendations: {record['admissions']['recommendations']}",
        f"- Essays: {record['admissions']['essays']}",
        "",
        "## Warnings",
    ]
    for warning in record.get('verification', {}).get('warnings', []):
        md_lines.append(f"- {warning}")
    (UNI_DIR / f"{record['slug']}.md").write_text("\n".join(md_lines))


def add_warning(record: dict, warning: str) -> None:
    warnings = [w for w in record.get('verification', {}).get('warnings', []) if w != warning]
    warnings.append(warning)
    record['verification']['warnings'] = warnings


def remove_warning_contains(record: dict, text: str) -> None:
    record['verification']['warnings'] = [w for w in record.get('verification', {}).get('warnings', []) if text.lower() not in w.lower()]


def upsert_evidence(record: dict, field: str, claim: str, classification: str, source_url: str, excerpt: str) -> None:
    evidence = [item for item in record.get('evidence', []) if item.get('field') and item.get('source_url')]
    key = (field, claim, source_url)
    evidence = [item for item in evidence if (item.get('field'), item.get('claim'), item.get('source_url')) != key]
    evidence.append(
        {
            'field': field,
            'claim': claim,
            'classification': classification,
            'source_url': source_url,
            'source_excerpt': excerpt,
            'retrieved_at': now_iso(),
        }
    )
    record['evidence'] = evidence


def recompute_unknowns(record: dict) -> None:
    unknown = []
    for field, value in [
        ('majors.count', record['majors'].get('count')),
        ('admissions.testing_policy', record['admissions'].get('testing_policy')),
        ('admissions.gpa_policy', record['admissions'].get('gpa_policy')),
        ('admissions.course_rigor', record['admissions'].get('course_rigor')),
        ('admissions.recommendations', record['admissions'].get('recommendations')),
        ('admissions.essays', record['admissions'].get('essays')),
    ]:
        if value in (None, '', 'unknown'):
            unknown.append(field)
    if not record.get('competitive_signals', {}).get('projects_research'):
        unknown.append('competitive_signals.projects_research')
    record['verification']['unknown_fields'] = unknown


UPDATES = {
    'ohio-state': {
        'testing_policy': 'Ohio State requires ACT or SAT scores for first-year applicants to the Columbus campus, and it says there are no minimum ACT or SAT score requirements.',
        'url': 'https://undergrad.osu.edu/apply/freshmen-columbus/apply-step-by-step',
        'excerpt': 'Yes, standardized test scores from ACT or SAT are required for first-year applicants to the Columbus campus.',
        'warning': 'Ohio State testing policy was manually repaired from the official undergraduate admissions page after the auto-crawl captured unrelated SB 1 compliance text.',
    },
    'george-washington': {
        'testing_policy': 'GW is test-optional for first-year applicants; students are not required to submit SAT or ACT scores, though some applicant groups still must provide them.',
        'url': 'https://undergraduate.admissions.gwu.edu/first-year-applicants',
        'excerpt': 'GW is test-optional, meaning students applying for first-year admission are not required to submit standardized test scores (SAT or ACT). GW requires SAT/ACT scores from the following groups:',
        'warning': 'George Washington testing policy was manually repaired from the official first-year admissions page after the auto-crawl captured nondiscrimination boilerplate.',
    },
    'smu': {
        'testing_policy': 'SMU is fully test-optional; applicants who do not submit ACT or SAT scores are evaluated on other factors including grades, résumé, essays, and recommendation letters.',
        'url': 'https://www.smu.edu/admission/apply/undergraduate-admission/testing',
        'excerpt': 'SMU is fully test-optional. Under SMU’s test-optional policy, applicants who choose not to submit ACT or SAT scores will be evaluated on the other factors, including grades, résumé, essays and recommendation letters.',
        'warning': 'SMU testing policy was manually repaired from the official undergraduate admission testing page after the auto-crawl captured unrelated program-marketing text.',
    },
    'loyola-marymount': {
        'testing_policy': 'LMU is test-optional for first-year applicants, and it says there is no minimum GPA or test score required for admission.',
        'url': 'https://admission.lmu.edu/learnmore/prospectivestudents/first-yearapplicants/',
        'excerpt': 'National SAT/ACT test scores (test optional). The ACT or SAT is optional for students. There is no minimum GPA or test score required for admission to LMU, but admission is selective.',
        'warning': 'Loyola Marymount testing policy was manually repaired from the official first-year applicants page after the auto-crawl captured Jesuit brand copy.',
    },
    'virginia-tech': {
        'testing_policy': 'Virginia Tech is test-optional for students entering through Fall 2028, and applicants can choose on the application whether scores should be reviewed.',
        'url': 'https://www.vt.edu/admissions/undergraduate/apply/freshman-requirements.html',
        'excerpt': 'Virginia Tech is test-optional for students entering through Fall 2028. On the application for admission, you will be able to select whether or not you would like your scores to be reviewed as part of your application.',
        'warning': 'Virginia Tech testing policy was manually repaired from the official freshman requirements page after the auto-crawl captured a CARES Act disclosure title.',
    },
    'umass-amherst': {
        'testing_policy': 'UMass Amherst is test-optional for first-year applicants and reviews applications with or without standardized test scores across all majors.',
        'url': 'https://www.umass.edu/admissions/undergraduate-admissions/connect/information-policies/test-optional-policy',
        'excerpt': 'At UMass Amherst, standardized tests are optional for first-year entering applicants. UMass Amherst will review applications with or without standardized test scores. The test-optional approach at UMass Amherst applies to all majors.',
        'warning': 'UMass Amherst testing policy was manually repaired from the official admissions test-optional policy page after the auto-crawl captured a slogan.',
    },
    'uc-santa-cruz': {
        'testing_policy': 'UC Santa Cruz does not use ACT or SAT scores in its comprehensive review and selection process.',
        'url': 'https://admissions.ucsc.edu/first-year-student',
        'excerpt': 'UC Santa Cruz does not use standardized exam scores (ACT/SAT) in our comprehensive review and selection process.',
        'warning': 'UC Santa Cruz testing policy was manually repaired from the official first-year student page after the auto-crawl captured Clery/safety disclosure text.',
    },
    'university-of-denver': {
        'testing_policy': 'The University of Denver is test-optional; submitting SAT or ACT scores is the applicant’s choice, and scores are considered with the rest of the application if submitted.',
        'url': 'https://www.du.edu/admission-aid/undergraduate/first-year-applicants/admission-standards',
        'excerpt': 'However, we are a test-optional university, and submitting test scores is your choice. If you choose to submit your SAT and/or ACT scores, they will be considered along with your other application materials for both admission and merit scholarships.',
        'warning': 'University of Denver testing policy was manually repaired from the official admission standards page after the auto-crawl captured drug/alcohol compliance text.',
    },
    'penn-state': {
        'testing_policy': 'Penn State is test-optional for first-year applicants; students can decide whether SAT or ACT scores should be considered, and scores are not required for the application.',
        'url': 'https://www.psu.edu/resources/faq/test-optional',
        'excerpt': 'For First-year applicants Penn State is test-optional, so submitting scores is not required for your application.',
        'warning': 'Penn State testing policy was manually repaired from the official test-optional FAQ after the auto-crawl captured a program-specific exception.',
    },
    'marquette': {
        'testing_policy': 'Marquette is test-optional; students may choose to submit ACT or SAT scores, and those who do not submit a score are not penalized.',
        'url': 'https://www.marquette.edu/apply/test-optional.php',
        'excerpt': 'Students may choose to submit their ACT and/or SAT scores to be included among the materials evaluated in the review process. Students not submitting a test score will not be penalized for making this choice.',
        'warning': 'Marquette testing policy was manually repaired from the official test-optional policy page after the auto-crawl captured a stats-navigation snippet.',
    },
    'temple': {
        'testing_policy': 'Temple is test-optional for first-year applicants; SAT or ACT scores are entirely optional and are not required for admission.',
        'url': 'https://admissions.temple.edu/apply/first-year-students/test-optional',
        'excerpt': 'Standardized test scores are otherwise entirely optional and in no way required for admission.',
        'warning': 'Temple testing policy was manually repaired from the official first-year test-optional page after the auto-crawl missed a clean policy sentence.',
    },
    'ut-austin': {
        'testing_policy': 'UT Austin requires official SAT or ACT scores for freshman applicants to be considered, and scores must be submitted by the application deadline.',
        'url': 'https://admissions.utexas.edu/apply/freshman/',
        'excerpt': 'SAT and ACT official test scores must be submitted by the appropriate deadline to be considered.',
        'warning': 'UT Austin testing policy was manually repaired from the official freshman application page after the auto-crawl left testing policy unresolved.',
    },
}


def apply_update(slug: str, spec: dict) -> dict:
    record = load(slug)
    record['admissions']['testing_policy'] = spec['testing_policy']
    record['source_urls']['admissions'] = sorted(set(record.get('source_urls', {}).get('admissions', []) + [spec['url']]))
    upsert_evidence(record, 'admissions.testing_policy', spec['testing_policy'], 'official_requirement', spec['url'], spec['excerpt'])
    remove_warning_contains(record, 'testing policy was manually repaired')
    remove_warning_contains(record, 'captured unrelated')
    remove_warning_contains(record, 'captured nondiscrimination')
    remove_warning_contains(record, 'captured jesuit')
    remove_warning_contains(record, 'captured a cares')
    remove_warning_contains(record, 'captured a slogan')
    remove_warning_contains(record, 'captured clery')
    remove_warning_contains(record, 'captured drug/alcohol')
    remove_warning_contains(record, 'captured a program-specific')
    remove_warning_contains(record, 'captured a stats-navigation')
    remove_warning_contains(record, 'testing_policy was reset to unknown')
    add_warning(record, spec['warning'])
    record['verification']['last_verified_at'] = now_iso()
    record['verification']['confidence'] = 'phase-5-manual-repair'
    recompute_unknowns(record)
    save(record)
    return record


def patch_blocked_school(slug: str, school_name: str, url: str, note: str) -> dict:
    record = load(slug)
    remove_warning_contains(record, 'testing_policy was reset to unknown')
    add_warning(record, note)
    record['source_urls']['admissions'] = sorted(set(record.get('source_urls', {}).get('admissions', []) + [url]))
    record['verification']['last_verified_at'] = now_iso()
    record['verification']['confidence'] = 'phase-5-manual-repair'
    recompute_unknowns(record)
    save(record)
    return record


def main() -> int:
    updated = []
    for slug, spec in UPDATES.items():
        updated.append(apply_update(slug, spec)['slug'])

    patch_blocked_school(
        'johns-hopkins',
        'Johns Hopkins University',
        'https://apply.jhu.edu/apply/first-year-applicants/',
        'Johns Hopkins official admissions and institutional research pages were still bot-protected in this environment during the second cleanup wave, so testing policy remains unresolved pending a direct official-source pass.',
    )
    patch_blocked_school(
        'columbia',
        'Columbia University',
        'https://undergrad.admissions.columbia.edu/apply/first-year',
        'Columbia official admissions and institutional research pages were still bot-protected in this environment during the second cleanup wave, so testing policy remains unresolved pending a direct official-source pass.',
    )

    print(json.dumps({'updated_testing_policy_slugs': updated, 'blocked_slugs': ['johns-hopkins', 'columbia']}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
