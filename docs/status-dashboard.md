# Goal Kicker Status Dashboard

Last audited: 2026-05-07 17:08 UTC

## Current completion

- Schools in scope: 100
- School records present: 100 / 100
- Majors coverage present: 88 / 100
- Professor coverage present: 100 / 100
- Alumni coverage present: 100 / 100
- Overall structured completion estimate: 97.0%

## What changed most recently

- Added official-source majors-title coverage for unc-chapel-hill via the official UNC undergraduate Programs of Study catalog page
- Added official-source majors-title coverage for temple via the official Temple degree-program finder page
- Added official-source majors-title coverage for tulane via the official Tulane university catalog programs page filtered to undergraduate major cards
- Hardened `scripts/populate_major_titles.py` for UNC, Temple, and Tulane with targeted source hints and school-specific parsers
- Added regression tests covering UNC catalog major links, Temple degree-program option extraction, and Tulane undergraduate-major catalog cards

## Remaining major gaps

12 schools still need majors-title coverage:

- baylor
- drexel
- florida-state
- indiana-bloomington
- michigan-state
- michigan
- uc-berkeley
- uc-irvine
- university-of-georgia
- university-of-san-diego
- villanova
- washu

## Partial people-depth gaps

None at the current minimum-depth threshold.

Every school now has at least:
- 5 professor entries
- 10 alumni entries

## Recommended next focus

1. Push majors coverage from 88 toward 90+
2. Target the remaining blocked/JS-heavy majors pages (especially Michigan, UC Berkeley, Michigan State, and WashU)
3. Improve source quality for professor verification beyond RateMyProfessors-derived fallbacks
4. Improve recent-alumni and per-major alumni filtering
