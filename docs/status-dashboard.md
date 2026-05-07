# Goal Kicker Status Dashboard

Last audited: 2026-05-07 08:03 UTC

## Current completion

- Schools in scope: 100
- School records present: 100 / 100
- Majors coverage present: 81 / 100
- Professor coverage present: 100 / 100
- Alumni coverage present: 100 / 100
- Overall structured completion estimate: 95.3%

## What changed most recently

- Added official-source majors-title coverage for colorado-school-of-mines
- Added official-source majors-title coverage for rice
- Added official-source majors-title coverage for santa-clara
- Added official-source majors-title coverage for uc-san-diego
- Added targeted `--school` support to `scripts/populate_major_titles.py` to avoid broad timestamp churn during focused repair passes
- Hardened majors-title parsing/tests for Rice, Santa Clara, UC San Diego, and Colorado School of Mines, plus fixed false negative filtering on titles like `Applied Mathematics and Statistics`

## Remaining major gaps

19 schools still need majors-title coverage:

- baylor
- drexel
- florida-state
- georgetown
- indiana-bloomington
- michigan-state
- michigan
- northeastern
- temple
- tulane
- uc-berkeley
- uc-irvine
- uchicago
- unc-chapel-hill
- university-of-georgia
- university-of-san-diego
- vanderbilt
- villanova
- washu

## Partial people-depth gaps

None at the current minimum-depth threshold.

Every school now has at least:
- 5 professor entries
- 10 alumni entries

## Recommended next focus

1. Push majors coverage from 77 to 85+
2. Target the remaining blocked/JS-heavy majors pages (especially Georgetown, Michigan, UNC, Vanderbilt, Temple, and Tulane)
3. Improve source quality for professor verification beyond RateMyProfessors-derived fallbacks
4. Improve recent-alumni and per-major alumni filtering
