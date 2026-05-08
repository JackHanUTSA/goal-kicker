# Goal Kicker Status Dashboard

Last audited: 2026-05-08 15:58 UTC

## Current completion

- Schools in scope: 100
- School records present: 100 / 100
- Majors coverage present: 99 / 100
- Professor coverage present: 100 / 100
- Alumni coverage present: 100 / 100
- Overall structured completion estimate: 99.7%

## What changed most recently

- Added official-source majors-title coverage for Florida State via the academic guide all-programs directory
- Added official-source majors-title coverage for Michigan State via the admissions majors/degrees/programs directory
- Added official-source majors-title coverage for UC Berkeley via the undergraduate catalog Programs page with the Major filter applied
- Added official-source majors-title coverage for the University of Georgia via the official UGA majors checklist PDF
- Added official-source majors-title coverage for the University of San Diego via the undergraduate majors/minors endpoint behind the public degree finder
- Hardened `scripts/populate_major_titles.py` with school-specific extractors for Florida State, University of Georgia, and University of San Diego, plus an extra Baylor false-positive guard for the generic Baylor undergraduate catalog landing page

## Remaining major gaps

1 school still needs majors-title coverage:

- baylor — official majors pages on admissions.web.baylor.edu and go.web.baylor.edu were Cloudflare-blocked in this environment, and the undergraduate catalog root returned an empty 202 response during this audit

## Partial people-depth gaps

None at the current minimum-depth threshold.

Every school now has at least:
- 5 professor entries
- 10 alumni entries

## Recommended next focus

1. Push majors coverage from 99 toward full top-100 coverage by solving Baylor's remaining official-source access problem
2. Revisit Baylor with an official source that is accessible in this environment, or with a browser-capable/manual workflow that can bypass the current Cloudflare and empty-catalog blockers
3. Improve source quality for professor verification beyond RateMyProfessors-derived fallbacks
4. Improve recent-alumni and per-major alumni filtering
