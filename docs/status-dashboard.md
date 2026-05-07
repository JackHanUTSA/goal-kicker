# Goal Kicker Status Dashboard

Last audited: 2026-05-07 21:41 UTC

## Current completion

- Schools in scope: 100
- School records present: 100 / 100
- Majors coverage present: 90 / 100
- Professor coverage present: 100 / 100
- Alumni coverage present: 100 / 100
- Overall structured completion estimate: 98.0%

## What changed most recently

- Added official-source majors-title coverage for Drexel via the official Drexel undergraduate-program search endpoint backing the public programs page
- Added official-source majors-title coverage for Indiana Bloomington via the official IU Bloomington degrees-and-majors API backing the public academics page
- Hardened `scripts/populate_major_titles.py` with school-specific API-backed extraction for Drexel and Indiana Bloomington
- Added regression coverage to ensure school-specific title extraction runs before the generic crawler and that bachelor-level degree labels are filtered correctly

## Remaining major gaps

10 schools still need majors-title coverage:

- baylor
- florida-state
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

1. Push majors coverage from 90 toward full top-100 coverage
2. Target the remaining blocked/JS-heavy majors pages (especially Michigan, UC Berkeley, Michigan State, WashU, and Florida State)
3. Improve source quality for professor verification beyond RateMyProfessors-derived fallbacks
4. Improve recent-alumni and per-major alumni filtering
