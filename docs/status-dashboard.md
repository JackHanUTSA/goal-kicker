# Goal Kicker Status Dashboard

Last audited: 2026-05-09 07:16 UTC

## Current completion

- Schools in scope: 100
- School records present: 100 / 100
- Majors coverage present: 100 / 100
- Professor coverage present: 100 / 100
- Alumni coverage present: 100 / 100
- Overall structured completion estimate: 100.0%

## What changed most recently

- Repaired Ohio State majors-title coverage from a 15-item undecided/program-cluster scrape to 172 named entries from Ohio State's official majors-and-degrees directory, and corrected the stored majors count from the prior graduate-program misread to the official '200-plus undergraduate majors' claim
- Repaired RIT majors-title coverage from a noisy 80-item mixed page scrape to a clean 79-title list from RIT's official Undergraduate Degrees directory, and aligned the stored majors count to that audited directory
- Repaired Clemson majors-title coverage from a stale 27-title admissions-nav scrape to 76 bachelor-level titles from Clemson's official Program Finder, and replaced incorrect admissions text with grounded first-year requirements/testing details
- Repaired University of Georgia admissions fields from official first-year admissions pages while preserving the 143-title official majors checklist

## Remaining major gaps

No schools remain at zero-title coverage, but several records still look materially under-covered relative to their official offerings and should be prioritized next:

- usc — 6 titles currently stored
- william-and-mary — 7 titles currently stored
- stevens — 7 titles currently stored
- american — 7 titles currently stored and the direct academics site is still Cloudflare-blocked in this environment
- carnegie-mellon — 8 titles currently stored
- ut-austin — 8 titles currently stored
- njit — 8 titles currently stored
- fordham — 9 titles currently stored
- uc-santa-barbara — 9 titles currently stored

Residual source caveat:

- baylor — majors titles are populated from official Baylor homepage directory metadata because the direct majors pages were inaccessible here; treat that count as a recovered official fallback rather than a direct-program-page census

## Partial people-depth gaps

None at the current minimum-depth threshold.

Every school now has at least:
- 5 professor entries
- 10 alumni entries

## Recommended next focus

1. Improve Baylor from recovered homepage-directory titles to a direct majors-page or catalog-derived official census once an accessible official source path exists in this environment
2. Improve source quality for professor verification beyond RateMyProfessors-derived fallbacks
3. Improve recent-alumni and per-major alumni filtering
4. Continue replacing low-quality or clearly off-target admissions text in residual partial records
