# Goal Kicker Status Dashboard

Last audited: 2026-05-07 05:43 UTC

## Current completion

- Schools in scope: 100
- School records present: 100 / 100
- Majors coverage present: 77 / 100
- Professor coverage present: 100 / 100
- Alumni coverage present: 100 / 100
- Overall structured completion estimate: 94.3%

## What changed most recently

- Added official-source majors-title coverage for loyola-marymount
- Added official-source majors-title coverage for uconn
- Added official-source majors-title coverage for university-of-washington
- Added official-source majors-title coverage for wake-forest
- Replaced low-quality majors-title captures for upenn and wisconsin-madison with cleaner official-source lists
- Hardened `scripts/populate_major_titles.py` against false CAPTCHA blocking and added new site-specific extraction coverage/tests

## Remaining major gaps

23 schools still need majors-title coverage:

- baylor
- colorado-school-of-mines
- drexel
- florida-state
- georgetown
- indiana-bloomington
- michigan-state
- michigan
- northeastern
- rice
- santa-clara
- temple
- tulane
- uc-berkeley
- uc-irvine
- uc-san-diego
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
