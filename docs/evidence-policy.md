# Goal Kicker Evidence Policy

Goal Kicker must not blur official requirements with inferred competitiveness.

## Evidence classifications

Use one of these labels for every important claim:

- `official_requirement`
  - explicitly required by the university
- `official_recommendation`
  - recommended or encouraged by the university
- `reported_profile`
  - descriptive profile language about typical admitted students or class profile
- `inference`
  - synthesis or interpretation produced by the agent

## Rules

1. Prefer official university pages.
2. Save the source URL for every important field.
3. Include a short source excerpt when possible.
4. If the school does not publish a value, store unknown/null.
5. Never turn a competitive pattern into a formal requirement.
6. Keep majors count confidence separate from admissions confidence.
7. If the source language is vague, mark it as `official_recommendation` or `reported_profile`, not `official_requirement`.

## Examples

Example 1:
- claim: "School requires two teacher recommendations"
- label: `official_requirement`

Example 2:
- claim: "School says successful applicants usually pursue rigorous coursework"
- label: `reported_profile` or `official_recommendation`

Example 3:
- claim: "A 4.0 GPA alone is probably not enough without strong projects"
- label: `inference`

## Output behavior

User-facing summaries should clearly distinguish:
- what the school requires
- what the school emphasizes
- what the agent infers about competitiveness
