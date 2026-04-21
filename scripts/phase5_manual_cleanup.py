#!/usr/bin/env /usr/bin/python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNI_DIR = ROOT / "knowledgebase" / "universities"


MICHIGAN_CDS_URL = "https://obp.umich.edu/wp-content/uploads/pubdata/cds/cds_2022-2023_umaa.pdf"
MICHIGAN_ATLAS_URL = "https://atlas.ai.umich.edu/api/majorlist/"


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
    for warning in record['verification'].get('warnings', []):
        md_lines.append(f"- {warning}")
    (UNI_DIR / f"{record['slug']}.md").write_text("\n".join(md_lines))


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
    checks = [
        ('majors.count', record['majors'].get('count')),
        ('admissions.testing_policy', record['admissions'].get('testing_policy')),
        ('admissions.gpa_policy', record['admissions'].get('gpa_policy')),
        ('admissions.course_rigor', record['admissions'].get('course_rigor')),
        ('admissions.recommendations', record['admissions'].get('recommendations')),
        ('admissions.essays', record['admissions'].get('essays')),
    ]
    for field, value in checks:
        if value in (None, '', 'unknown'):
            unknown.append(field)
    if not record.get('competitive_signals', {}).get('projects_research'):
        unknown.append('competitive_signals.projects_research')
    record['verification']['unknown_fields'] = unknown


def add_warning(record: dict, warning: str) -> None:
    warnings = [w for w in record['verification'].get('warnings', []) if w != warning]
    warnings.append(warning)
    record['verification']['warnings'] = warnings


def remove_warning_contains(record: dict, text: str) -> None:
    record['verification']['warnings'] = [w for w in record['verification'].get('warnings', []) if text.lower() not in w.lower()]


def patch_field_to_unknown(record: dict, field_path: str, reason: str) -> None:
    top, field = field_path.split('.')
    record[top][field] = 'unknown'
    add_warning(record, reason)


def apply_michigan() -> dict:
    record = load('michigan')
    record['majors']['count'] = 146
    record['majors']['count_method'] = (
        'derived from the official University of Michigan Atlas API by counting unique bachelor-level study_field values; '
        'this is an API-derived undergraduate program-field count rather than a single admissions-page sentence'
    )
    record['majors']['notes'] = record['majors']['count_method']
    record['majors']['confidence'] = 'medium'

    record['admissions']['application_platform'] = 'Common App or Coalition Application'
    record['admissions']['testing_policy'] = (
        'Michigan treats SAT or ACT scores as considered if submitted; the official Common Data Set marks SAT or ACT under '
        '"Consider if Submitted," so applicants may apply without submitting scores.'
    )
    record['admissions']['gpa_policy'] = (
        'Michigan does not publish a minimum GPA in the source used here, but its official Common Data Set marks both '
        'academic record and academic GPA as very important in first-year admission decisions.'
    )
    record['admissions']['course_rigor'] = (
        'Michigan recommends a general college-preparatory program. Its official Common Data Set lists 16 required academic '
        'units, 23+ recommended units, and specifically recommends rigorous coursework such as IB, AP, A Levels, honors, '
        'advanced, accelerated, and enriched classes.'
    )
    record['admissions']['recommendations'] = (
        'Michigan’s official Common Data Set marks recommendations as important in first-year admissions review.'
    )
    record['admissions']['essays'] = (
        'Michigan’s official Common Data Set marks the application essay as important in first-year admissions review.'
    )
    record['competitive_signals']['academics'] = [
        'Michigan marks both academic record and academic GPA as very important in first-year admissions review.',
        'Michigan recommends a college-preparatory high school program with strong academic rigor.'
    ]

    record['source_urls']['admissions'] = sorted(set(record.get('source_urls', {}).get('admissions', []) + [MICHIGAN_CDS_URL]))
    record['source_urls']['majors'] = sorted(set(record.get('source_urls', {}).get('majors', []) + [MICHIGAN_ATLAS_URL]))

    upsert_evidence(
        record,
        'admissions.application_platform',
        'Michigan uses the Common App or Coalition Application.',
        'official_requirement',
        MICHIGAN_CDS_URL,
        'URL for school’s online application: apply.commonapp.org or coalitionforcollegeaccess.org',
    )
    upsert_evidence(
        record,
        'admissions.testing_policy',
        record['admissions']['testing_policy'],
        'official_requirement',
        MICHIGAN_CDS_URL,
        'In the official Common Data Set C8A table, the SAT or ACT row is marked under “Consider if Submitted.”',
    )
    upsert_evidence(
        record,
        'admissions.gpa_policy',
        record['admissions']['gpa_policy'],
        'reported_profile',
        MICHIGAN_CDS_URL,
        'In the official Common Data Set C7 table, both “Academic record” and “Academic GPA” are marked “Very Important.”',
    )
    upsert_evidence(
        record,
        'admissions.course_rigor',
        record['admissions']['course_rigor'],
        'reported_profile',
        MICHIGAN_CDS_URL,
        'The official Common Data Set marks a general college-preparatory program as recommended and lists 16 required / 23+ recommended academic units, including IB/AP/A Levels/honors/advanced coursework.',
    )
    upsert_evidence(
        record,
        'admissions.recommendations',
        record['admissions']['recommendations'],
        'reported_profile',
        MICHIGAN_CDS_URL,
        'The official Common Data Set C7 table marks “Recommendation(s)” as Important.',
    )
    upsert_evidence(
        record,
        'admissions.essays',
        record['admissions']['essays'],
        'reported_profile',
        MICHIGAN_CDS_URL,
        'The official Common Data Set C7 table marks “Application Essay” as Important.',
    )
    upsert_evidence(
        record,
        'majors.count',
        'Michigan Atlas API yields 146 unique bachelor-level study_field values.',
        'reported_profile',
        MICHIGAN_ATLAS_URL,
        'Official Atlas API responses were aggregated and deduplicated by bachelor-level study_field, producing 146 unique bachelor study fields.',
    )

    remove_warning_contains(record, 'blocked by bot protection')
    remove_warning_contains(record, 'cloudflare-style bot protection')
    add_warning(record, 'Michigan admissions pages remain bot-protected in this environment, so this record now relies on official U-M Common Data Set and official Atlas API sources.')
    add_warning(record, 'Michigan majors count is an official-API-derived bachelor study-field count, not a single registrar sentence from the admissions site.')

    record['verification']['last_verified_at'] = now_iso()
    record['verification']['confidence'] = 'phase-5-manual-repair'
    recompute_unknowns(record)
    save(record)
    return record


def apply_cleanup_overrides() -> list[dict]:
    cleanup_specs = {
        'johns-hopkins': {
            'admissions.testing_policy': 'unknown',
            'admissions.course_rigor': 'unknown',
            'majors_count_zero_warning': 'Johns Hopkins auto-extraction captured unrelated disclosure/catalog text; testing policy, course rigor, and majors count need a cleaner official-source pass.',
        },
        'ohio-state': {
            'admissions.testing_policy': 'unknown',
        },
        'george-washington': {
            'admissions.testing_policy': 'unknown',
        },
        'smu': {
            'admissions.testing_policy': 'unknown',
            'admissions.course_rigor': 'unknown',
        },
        'loyola-marymount': {
            'admissions.testing_policy': 'unknown',
            'admissions.recommendations': 'unknown',
            'admissions.essays': 'unknown',
        },
        'virginia-tech': {
            'admissions.testing_policy': 'unknown',
            'admissions.course_rigor': 'unknown',
        },
        'umass-amherst': {
            'admissions.testing_policy': 'unknown',
            'admissions.course_rigor': 'unknown',
        },
        'uc-santa-cruz': {
            'admissions.testing_policy': 'unknown',
            'admissions.course_rigor': 'unknown',
        },
        'university-of-denver': {
            'admissions.testing_policy': 'unknown',
        },
        'penn-state': {
            'admissions.testing_policy': 'unknown',
            'admissions.course_rigor': 'unknown',
            'admissions.recommendations': 'unknown',
        },
        'marquette': {
            'admissions.testing_policy': 'unknown',
        },
        'case-western': {
            'admissions.course_rigor': 'unknown',
        },
        'temple': {
            'admissions.course_rigor': 'unknown',
            'admissions.recommendations': 'unknown',
        },
        'ut-austin': {
            'admissions.course_rigor': 'unknown',
            'admissions.essays': 'unknown',
        },
    }
    updated = []
    for slug, spec in cleanup_specs.items():
        record = load(slug)
        for field_path, value in spec.items():
            if field_path == 'majors_count_zero_warning':
                add_warning(record, value)
                continue
            top, field = field_path.split('.')
            record[top][field] = value
            add_warning(record, f'{field_path} was reset to unknown during manual cleanup because the earlier auto-extracted text was unrelated to the requested admissions field.')
        record['verification']['last_verified_at'] = now_iso()
        record['verification']['confidence'] = 'phase-5-manual-repair'
        recompute_unknowns(record)
        save(record)
        updated.append(record)
    return updated


def main() -> int:
    michigan = apply_michigan()
    cleaned = apply_cleanup_overrides()
    print(json.dumps({
        'michigan_unknown_fields': michigan['verification']['unknown_fields'],
        'cleaned_count': len(cleaned),
        'cleaned_slugs': [record['slug'] for record in cleaned],
    }, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
