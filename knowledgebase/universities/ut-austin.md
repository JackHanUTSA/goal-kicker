---
name: University of Texas at Austin
short_name: UT Austin
slug: ut-austin
rank: 36
official_domain: utexas.edu
status: phase-5-manual-repair
---

# University of Texas at Austin

## Structured extraction
- Majors count: 8
- Count method: counted extracted undergraduate-major titles from an official page
- Testing policy: UT Austin requires official SAT or ACT scores for freshman applicants to be considered, and scores must be submitted by the application deadline.
- GPA policy: No explicit minimum GPA was found on the cited official pages used in this auto-enrichment pass.
- Course rigor: unknown
- Recommendations: unknown
- Essays: unknown

## Warnings
- Major titles extracted from official school source (8 titles).
- Phase 5 auto-enrichment completed using official-school web crawl heuristics; manual spot-checking is still recommended for edge cases.
- GPA policy was normalized from absence of an explicit minimum-GPA statement on the cited official pages.
- Testing policy needs manual confirmation; the crawler did not find a clean official testing-policy sentence.
- Majors count needs manual confirmation; the crawler did not find a clean count or stable program-list page.
- School-people enrichment uses public third-party sources (RateMyProfessors and Wikipedia/Wikimedia), so rankings are heuristic rather than official university data.
- admissions.course_rigor was reset to unknown during manual cleanup because the earlier auto-extracted text was unrelated to the requested admissions field.
- admissions.essays was reset to unknown during manual cleanup because the earlier auto-extracted text was unrelated to the requested admissions field.
- UT Austin testing policy was manually repaired from the official freshman application page after the auto-crawl left testing policy unresolved.