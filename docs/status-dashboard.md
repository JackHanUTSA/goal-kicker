# Goal Kicker Status Dashboard

Last audited: 2026-05-08 18:12 UTC

## Current completion

- Schools in scope: 100
- School records present: 100 / 100
- Majors coverage present: 100 / 100
- Professor coverage present: 100 / 100
- Alumni coverage present: 100 / 100
- Overall structured completion estimate: 100.0%

## What changed most recently

- Added Baylor majors-title coverage by mining Baylor's official homepage quick-search directory after the direct majors and academics pages remained Cloudflare-blocked and the undergraduate catalog returned empty 202 responses
- Recovered 45 Baylor undergraduate major/program titles from official Baylor homepage directory metadata spanning arts & sciences, business, ECS, nursing, and honors entries
- Hardened `scripts/populate_major_titles.py` with a Baylor-specific official-domain fallback extractor that reads the homepage quick-search dataset when the direct Baylor majors pages are inaccessible in this environment
- Added a regression test covering the Baylor quick-search fallback extractor

## Remaining major gaps

None at the majors-title coverage threshold.

Residual Baylor caveat:

- baylor — majors titles are now populated from official Baylor homepage directory metadata, but the direct admissions/go majors pages are still Cloudflare-blocked here, so Baylor's majors count should still be treated as a conservative recovered list rather than a fully confirmed direct-program-page census

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
