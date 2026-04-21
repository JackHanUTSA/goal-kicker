#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNI_DIR = ROOT / "knowledgebase" / "universities"


def load_records() -> list[dict]:
    records = []
    for path in sorted(UNI_DIR.glob('*.json')):
        records.append(json.loads(path.read_text()))
    return records


def find_record(records: list[dict], needle: str) -> dict:
    key = needle.strip().lower()
    for record in records:
        hay = [record['slug'], record['short_name'], record['name']]
        if any(key == item.lower() for item in hay):
            return record
    for record in records:
        hay = ' '.join([record['slug'], record['short_name'], record['name']]).lower()
        if key in hay:
            return record
    raise SystemExit(f"School not found: {needle}")


def summarize(record: dict) -> dict:
    return {
        'name': record['name'],
        'slug': record['slug'],
        'majors_count': record['majors']['count'],
        'testing_policy': record['admissions']['testing_policy'],
        'gpa_policy': record['admissions']['gpa_policy'],
        'course_rigor': record['admissions']['course_rigor'],
        'recommendations': record['admissions']['recommendations'],
        'essays': record['admissions']['essays'],
        'projects_research': record['competitive_signals']['projects_research'],
        'warnings': record['verification']['warnings'],
        'unknown_fields': record['verification']['unknown_fields'],
    }


def cmd_show(records: list[dict], school: str) -> None:
    print(json.dumps(summarize(find_record(records, school)), indent=2))


def cmd_compare(records: list[dict], school_a: str, school_b: str) -> None:
    a = find_record(records, school_a)
    b = find_record(records, school_b)
    out = {
        'schools': [a['name'], b['name']],
        'comparison': {
            'majors_count': {a['slug']: a['majors']['count'], b['slug']: b['majors']['count']},
            'testing_policy': {a['slug']: a['admissions']['testing_policy'], b['slug']: b['admissions']['testing_policy']},
            'gpa_policy': {a['slug']: a['admissions']['gpa_policy'], b['slug']: b['admissions']['gpa_policy']},
            'course_rigor': {a['slug']: a['admissions']['course_rigor'], b['slug']: b['admissions']['course_rigor']},
            'recommendations': {a['slug']: a['admissions']['recommendations'], b['slug']: b['admissions']['recommendations']},
            'essays': {a['slug']: a['admissions']['essays'], b['slug']: b['admissions']['essays']},
            'projects_research': {a['slug']: a['competitive_signals']['projects_research'], b['slug']: b['competitive_signals']['projects_research']},
        }
    }
    print(json.dumps(out, indent=2))


def cmd_filter_testing(records: list[dict], mode: str) -> None:
    selected = []
    for record in records:
        policy = (record['admissions']['testing_policy'] or '').lower()
        if mode == 'required':
            if 'require' in policy and 'does not require' not in policy and 'not require' not in policy:
                selected.append(record)
        elif mode == 'unknown' and (policy.startswith('unknown') or policy == ''):
            selected.append(record)
    print(json.dumps([{
        'slug': r['slug'],
        'name': r['name'],
        'testing_policy': r['admissions']['testing_policy'],
    } for r in selected], indent=2))


def cmd_filter_projects(records: list[dict]) -> None:
    selected = [r for r in records if r['competitive_signals']['projects_research']]
    print(json.dumps([{
        'slug': r['slug'],
        'name': r['name'],
        'projects_research': r['competitive_signals']['projects_research'],
    } for r in selected], indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description='Query Goal Kicker structured university records')
    sub = parser.add_subparsers(dest='command', required=True)

    show = sub.add_parser('show', help='Show one school record summary')
    show.add_argument('school')

    compare = sub.add_parser('compare', help='Compare two schools')
    compare.add_argument('school_a')
    compare.add_argument('school_b')

    testing = sub.add_parser('testing', help='Filter by testing policy')
    testing.add_argument('mode', choices=['required', 'unknown'])

    sub.add_parser('projects', help='List schools with project/research signals')

    args = parser.parse_args()
    records = load_records()

    if args.command == 'show':
        cmd_show(records, args.school)
    elif args.command == 'compare':
        cmd_compare(records, args.school_a, args.school_b)
    elif args.command == 'testing':
        cmd_filter_testing(records, args.mode)
    elif args.command == 'projects':
        cmd_filter_projects(records)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
