# Goal Kicker Status Dashboard

Last audited: 2026-05-12 06:53 UTC

## Current completion

- Schools in scope: 100
- School records present: 100 / 100
- Majors coverage present: 100 / 100
- Professor coverage present: 100 / 100
- Alumni coverage present: 100 / 100
- Overall structured completion estimate: 100.0%
- Site panel coverage present: 100 / 100 schools × 4 panel types

## What changed most recently

- Repaired Stevens majors-title coverage from a 7-item navigation scrape to 35 bachelor-level titles from Stevens' official Program Finder
- Repaired William & Mary majors-title coverage from a 7-item navigation scrape to 53 bachelor-level programs from William & Mary's official Program Finder
- Repaired Carnegie Mellon majors-title coverage from an 8-item engineering-only scrape to 28 undergraduate program titles from Carnegie Mellon's official Majors & Programs page, and corrected the stored majors count from 1 to a counted 28-title official-page census
- Repaired UC Santa Barbara majors-title coverage from a 9-item partial scrape to 73 official majors across Letters & Science, Engineering, and Creative Studies from UCSB Undergraduate Admissions
- Repaired NJIT majors-title coverage from an 8-item top-level scrape to 42 bachelor-level programs from NJIT's official catalog programs index

## Remaining major gaps

The lowest-title records after this repair pass are now:

- usc — 6 titles currently stored
- american — 7 titles currently stored and the direct academics site is still Cloudflare-blocked in this environment
- ut-austin — 8 titles currently stored
- fordham — 9 titles currently stored
- yeshiva — 9 titles currently stored
- emory — 10 titles currently stored
- marquette — 10 titles currently stored
- rutgers-new-brunswick — 10 titles currently stored

Residual source caveat:

- baylor — majors titles are populated from official Baylor homepage directory metadata because the direct majors pages were inaccessible here; treat that count as a recovered official fallback rather than a direct-program-page census

## Partial people-depth gaps

None at the current minimum-depth threshold.

Every school now has at least:
- 5 professor entries
- 10 alumni entries

## Recommended next focus

1. Site panels are now complete for ranks 3–100 as well as the two pilot schools; prioritize quality upgrades instead of raw panel-count expansion
2. Improve Baylor from recovered homepage-directory titles to a direct majors-page or catalog-derived official census once an accessible official source path exists in this environment
3. Improve source quality for professor verification beyond RateMyProfessors-derived fallbacks
4. Continue replacing low-quality or clearly off-target admissions text in residual partial records
