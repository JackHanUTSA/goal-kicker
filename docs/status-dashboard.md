# Goal Kicker Status Dashboard

Last audited: 2026-05-07 23:57 UTC

## Current completion

- Schools in scope: 100
- School records present: 100 / 100
- Majors coverage present: 94 / 100
- Professor coverage present: 100 / 100
- Alumni coverage present: 100 / 100
- Overall structured completion estimate: 98.8%

## What changed most recently

- Added official-source majors-title coverage for Michigan via the University of Michigan Atlas majorlist API, filtering to bachelor-level entries
- Added official-source majors-title coverage for UC Irvine via the UCI admissions majors/minors endpoint that powers the public majors explorer
- Added official-source majors-title coverage for Villanova via the embedded official programs dataset on the university programs page
- Added official-source majors-title coverage for WashU via the admissions degree-filters REST endpoint backing the public majors/programs finder
- Hardened `scripts/populate_major_titles.py` with school-specific extractors for Michigan, UC Irvine, Villanova, and WashU

## Remaining major gaps

6 schools still need majors-title coverage:

- baylor
- florida-state
- michigan-state
- uc-berkeley
- university-of-georgia
- university-of-san-diego

## Partial people-depth gaps

None at the current minimum-depth threshold.

Every school now has at least:
- 5 professor entries
- 10 alumni entries

## Recommended next focus

1. Push majors coverage from 94 toward full top-100 coverage
2. Target the remaining blocked/JS-heavy majors pages (especially UC Berkeley, Michigan State, Florida State, and Georgia)
3. Improve source quality for professor verification beyond RateMyProfessors-derived fallbacks
4. Improve recent-alumni and per-major alumni filtering
