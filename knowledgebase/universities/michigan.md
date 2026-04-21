---
name: University of Michigan
short_name: Michigan
slug: michigan
rank: 25
official_domain: umich.edu
status: phase-5-manual-repair
---

# University of Michigan

## Structured extraction
- Majors count: 146
- Count method: derived from the official University of Michigan Atlas API by counting unique bachelor-level study_field values; this is an API-derived undergraduate program-field count rather than a single admissions-page sentence
- Testing policy: Michigan treats SAT or ACT scores as considered if submitted; the official Common Data Set marks SAT or ACT under "Consider if Submitted," so applicants may apply without submitting scores.
- GPA policy: Michigan does not publish a minimum GPA in the source used here, but its official Common Data Set marks both academic record and academic GPA as very important in first-year admission decisions.
- Course rigor: Michigan recommends a general college-preparatory program. Its official Common Data Set lists 16 required academic units, 23+ recommended units, and specifically recommends rigorous coursework such as IB, AP, A Levels, honors, advanced, accelerated, and enriched classes.
- Recommendations: Michigan’s official Common Data Set marks recommendations as important in first-year admissions review.
- Essays: Michigan’s official Common Data Set marks the application essay as important in first-year admissions review.

## Warnings
- Could not fetch admissions source https://admissions.umich.edu/: HTTP Error 403: Forbidden
- Could not fetch majors source https://admissions.umich.edu/academics-majors: HTTP Error 403: Forbidden
- Phase 3 structured upgrade completed with improved majors counting, admissions extraction, and query-ready records.
- Michigan admissions pages remain bot-protected in this environment, so this record now relies on official U-M Common Data Set and official Atlas API sources.
- Michigan majors count is an official-API-derived bachelor study-field count, not a single registrar sentence from the admissions site.