# Goal Kicker Schema

This file defines the normalized data model for one university record.

## Identity
- `name`
- `short_name`
- `slug`
- `rank`
- `official_domain`

## Source URLs
- `source_urls.admissions`
- `source_urls.majors`
- `source_urls.testing_policy`
- `source_urls.general`

## Majors
- `majors.count`
- `majors.count_method`
- `majors.titles`
- `majors.notes`
- `majors.confidence`

## Admissions
- `admissions.application_platform`
- `admissions.testing_policy`
- `admissions.gpa_policy`
- `admissions.course_rigor`
- `admissions.recommendations`
- `admissions.essays`
- `admissions.portfolio_or_audition`
- `admissions.international_notes`
- `admissions.deadlines`

## Competitive Signals
These are not always formal requirements. Store them separately.
- `competitive_signals.academics`
- `competitive_signals.projects_research`
- `competitive_signals.extracurriculars`
- `competitive_signals.leadership`
- `competitive_signals.service`
- `competitive_signals.special_notes`

## Evidence
Each important claim should be backed by an evidence record.

Evidence fields:
- `field`
- `claim`
- `classification`
- `source_url`
- `source_excerpt`
- `retrieved_at`

## Verification
- `verification.last_verified_at`
- `verification.confidence`
- `verification.unknown_fields`
- `verification.warnings`

## Null handling
Use null or empty arrays when a value is unknown.
Do not invent values.
