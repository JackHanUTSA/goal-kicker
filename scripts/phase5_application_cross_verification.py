#!/usr/bin/env /usr/bin/python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNI_DIR = ROOT / "knowledgebase" / "universities"

COMMONAPP_COLUMBIA = "https://www.commonapp.org/explore/columbia-university/"
COMMONAPP_JHU = "https://www.commonapp.org/explore/johns-hopkins-university/"


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
        f"- Application platform: {record['admissions']['application_platform']}",
        f"- Testing policy: {record['admissions']['testing_policy']}",
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


def add_warning(record: dict, warning: str) -> None:
    warnings = [w for w in record['verification'].get('warnings', []) if w != warning]
    warnings.append(warning)
    record['verification']['warnings'] = warnings


def remove_warning_contains(record: dict, text: str) -> None:
    record['verification']['warnings'] = [w for w in record['verification'].get('warnings', []) if text.lower() not in w.lower()]


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


def patch_columbia() -> dict:
    record = load('columbia')
    record['admissions']['application_platform'] = 'Common Application, Coalition Application, or QuestBridge Application'
    record['admissions']['testing_policy'] = 'Cross-verified from the Common App school page: Columbia lists optional SAT or ACT scores (self-reported) for first-year applicants.'
    record['admissions']['recommendations'] = 'Cross-verified from the Common App school page: Columbia lists a secondary school report and two teacher recommendations for first-year applicants.'
    record['admissions']['essays'] = 'Cross-verified from the Common App school page: Columbia lists Columbia-specific questions as part of the first-year application.'
    record['source_urls']['admissions'] = sorted(set(record.get('source_urls', {}).get('admissions', []) + [COMMONAPP_COLUMBIA]))

    excerpt = ('We ask first-year applicants to submit the Common Application, Coalition Application or QuestBridge Application '
               'with Columbia-specific questions, a secondary school report, two teacher recommendations and optional SAT or ACT scores (self-reported).')
    upsert_evidence(record, 'admissions.application_platform', record['admissions']['application_platform'], 'cross_verification', COMMONAPP_COLUMBIA, excerpt)
    upsert_evidence(record, 'admissions.testing_policy', record['admissions']['testing_policy'], 'cross_verification', COMMONAPP_COLUMBIA, excerpt)
    upsert_evidence(record, 'admissions.recommendations', record['admissions']['recommendations'], 'cross_verification', COMMONAPP_COLUMBIA, excerpt)
    upsert_evidence(record, 'admissions.essays', record['admissions']['essays'], 'cross_verification', COMMONAPP_COLUMBIA, excerpt)

    remove_warning_contains(record, 'testing policy remains unresolved')
    add_warning(record, 'Columbia admissions fields were cross-verified from the Common App school profile because official Columbia admissions pages were bot-protected in this environment.')
    record['verification']['last_verified_at'] = now_iso()
    record['verification']['confidence'] = 'phase-5-cross-verified'
    recompute_unknowns(record)
    save(record)
    return record


def patch_jhu() -> dict:
    record = load('johns-hopkins')
    record['admissions']['application_platform'] = 'Common Application'
    record['source_urls']['admissions'] = sorted(set(record.get('source_urls', {}).get('admissions', []) + [COMMONAPP_JHU]))
    upsert_evidence(
        record,
        'admissions.application_platform',
        'Cross-verified from the Common App school page: Johns Hopkins uses the Common Application.',
        'cross_verification',
        COMMONAPP_JHU,
        'The Common App school profile for Johns Hopkins is itself an application-site source and lists Johns Hopkins within the Common Application explore directory.',
    )
    remove_warning_contains(record, 'testing policy remains unresolved')
    add_warning(record, 'Johns Hopkins application platform was cross-verified from the Common App school profile, but first-year testing-policy details were not exposed there and official JHU admissions pages remained bot-protected in this environment.')
    record['verification']['last_verified_at'] = now_iso()
    record['verification']['confidence'] = 'phase-5-cross-verified'
    recompute_unknowns(record)
    save(record)
    return record


def main() -> int:
    columbia = patch_columbia()
    jhu = patch_jhu()
    print(json.dumps({
        'columbia_unknown_fields': columbia['verification']['unknown_fields'],
        'jhu_unknown_fields': jhu['verification']['unknown_fields'],
        'columbia_confidence': columbia['verification']['confidence'],
        'jhu_confidence': jhu['verification']['confidence'],
    }, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
