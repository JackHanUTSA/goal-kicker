# Guideline — Adding the next 99 schools

A repeatable playbook for adding any school to the demo at https://jackhanutsa.github.io/goal-kicker/. MIT is the worked example; this is what to do for school #2 through #100.

The site reads four JSON files per school from the repo at runtime. Drop in any subset; whatever exists becomes a clickable panel. **No code change needed.**

```
data/enrollment/{slug}.json   → Majors panel (bubble chart)
data/testing/{slug}.json      → Testing panel (SAT/ACT ranges)
data/gpa/{slug}.json          → GPA panel (policy + recommended estimates)
data/rigor/{slug}.json        → Course Rigor panel (HS prep cards)
```

`{slug}` must match the `slug` field already in `knowledgebase/universities/{slug}.json`.

---

## Step 1 — Confirm the slug

Look up the school in `knowledgebase/universities/`. Use the existing slug exactly (lowercase, hyphenated). Examples: `mit`, `stanford`, `uc-berkeley`, `johns-hopkins`. Don't invent new slugs.

## Step 2 — Search in tier order

For each of the four data types, walk the source tiers in this order. Stop as soon as you have a defensible answer.

### Tier 1 — Official school sources (always try first)

| Data type | Where to look |
|---|---|
| Enrollment per major | `registrar.{school}.edu` → "Statistics", "Reports", "Enrollment", "Majors count" |
| Testing (SAT/ACT) | `{school}admissions.{tld}` → "Admissions Statistics", "Class Profile", "Stats" |
| GPA policy | Same as Testing; also "Selection", "How we review", "Process" |
| Course Rigor | Admissions site → "Prepare", "Academic preparation", "High school requirements" |

If a specific URL 404s, click into the school's "Statistics & Reports" or "Admissions" landing page and follow links from there. Landing pages outlive specific URLs.

**Common Data Set fallback.** Almost every US school publishes a CDS PDF. Standard sections: C2 (admit rate), C9 (test scores), C11 (GPA / class rank). Marked fields are gold; explicitly-blank fields ("not reported") are also a useful, citable answer.

### Tier 2 — Third-party aggregators (only when Tier 1 is silent)

Try in this order; record source + methodology on the card.

1. **PrepScholar** — `prepscholar.com/sat/s/colleges/{Name}-admission-requirements`. Always discloses methodology. Good for an estimated weighted GPA when the school doesn't publish one.
2. **CollegeSimply** — `collegesimply.com/colleges/{state}/{name}/admission/`. Predicts unweighted GPA from test scores via algorithm. Always says so.
3. **Niche** — `niche.com/colleges/{name}/admissions/`. Often vague ("Considered but not required"); useful negative result.
4. **US News** — `usnews.com/best-colleges/{name}-{id}/applying`. Free page describes selectivity factors but rarely lists a GPA number (paywalled).
5. **College Scorecard** — `collegescorecard.ed.gov/school/?{id}`. Has admit rate, costs, earnings — no HS GPA.

### Tier 3 — When nothing exists

Don't invent numbers. Either omit the field or use a `scope_note` that explains why and what the panel is showing instead (e.g., class-wide instead of per-major).

## Step 3 — Save the data in the right shape

Each JSON file has a documented schema. Copy MIT's file for that data type as a template and replace the values. Required fields are marked **bold** below.

### `data/enrollment/{slug}.json`

```json
{
  "university": "...",
  "slug": "...",
  "academic_year": "2025-2026",
  "source_url": "https://registrar.{school}.edu/...",
  "retrieved_at": "YYYY-MM-DD",
  "majors": [
    {
      "name": "Computer Science",
      "code": "VI-3",
      "school": "Engineering",
      "primary": 626,
      "secondary": 46,
      "total": 672
    }
  ]
}
```

Required: `slug`, `source_url`, `majors[].name`, `majors[].school`, `majors[].total`. Color of each bubble comes from the `school` value (add new schools to `SCHOOL_COLORS` in `index.html` if needed).

### `data/testing/{slug}.json`

```json
{
  "slug": "...",
  "class_label": "Class of 2029",
  "source_url": "...",
  "retrieved_at": "YYYY-MM-DD",
  "scope": "class_wide",
  "scope_note": "Most schools publish only class-wide ranges, not per-major.",
  "policy": "...",
  "ranges": [
    {"test": "SAT Math", "p25": 740, "p75": 800, "max": 800}
  ],
  "general": {
    "applications": 0,
    "admits": 0,
    "admit_rate": 0.0
  }
}
```

`general.*` is optional; include only fields the school publishes. Test `max` defaults to 800 if omitted; `min` is auto-detected from the test name.

### `data/gpa/{slug}.json`

Two sections. Always include `what_*_does_say` for Tier-1 quotes. Include `recommended_gpa` only when Tier-2 sources have a number.

```json
{
  "slug": "...",
  "source_urls": ["https://..."],
  "retrieved_at": "YYYY-MM-DD",
  "scope": "no_per_major_data",
  "scope_note": "...",
  "policy_summary": "...",
  "what_school_does_say": [
    { "claim": "Exact quote or paraphrase", "source_url": "..." }
  ],
  "recommended_gpa": {
    "summary": "These are third-party predictions, not official.",
    "estimates": [
      {
        "source": "PrepScholar",
        "value": "4.19",
        "scale": "weighted, 4.0 scale",
        "label": "Weighted (estimate)",
        "method": "Estimated from over 1,000 schools...",
        "url": "https://..."
      }
    ],
    "interpretation": "Optional one-paragraph reading of the numbers."
  }
}
```

### `data/rigor/{slug}.json`

```json
{
  "slug": "...",
  "source_url": "...",
  "retrieved_at": "YYYY-MM-DD",
  "scope": "institution_wide",
  "scope_note": "...",
  "audience": "Students in an American curriculum",
  "areas": [
    {
      "key": "math",
      "name": "Math",
      "level": "required-equivalent",
      "summary": "...",
      "detail": "...",
      "color": "#60a5fa"
    }
  ],
  "international_note": "..."
}
```

Use 2–4 areas. `level` is free text but stick to a small vocabulary: `required` / `required-equivalent` / `strongly-recommended` / `recommended` / `optional`. `color` is the left-border accent.

## Step 4 — Verify before committing

Run this checklist for every school. **All four boxes must be true.**

- [ ] Every numeric value matches the cited source page exactly. Open the source URL and re-check.
- [ ] Every field whose value came from a third party has the source name on it.
- [ ] Totals reconcile when applicable (e.g., enrollment: sum of `majors[].total` ≈ the school's published total, with first-years and undeclared/joint majors accounting for the gap).
- [ ] `scope_note` describes what the panel is and isn't — especially when data is missing or aggregate.

## Step 5 — Commit and verify on the live site

1. Commit each JSON file with a message naming the school and source, e.g. `Add Stanford enrollment data (2024-25, registrar.stanford.edu)`.
2. Wait ~30–60s for GitHub Pages CDN refresh.
3. Open `https://jackhanutsa.github.io/goal-kicker/?bust=$(date +%s)` to dodge cache.
4. Click the school's row → click each panel → confirm:
   - Numbers render and match the source.
   - The source link opens to the page the number came from.
   - The amber `Scope:` note is visible and accurate.

If anything is wrong, fix the JSON and recommit. Do not "patch" by tweaking the HTML for a single school — keep all per-school content in JSON.

## Anti-patterns — don't do these

- ❌ **Inventing numbers when a source doesn't publish one.** Use a scope-noted panel instead.
- ❌ **Mixing weighted and unweighted GPA without labeling.** Always say `scale` and `label` on each estimate card.
- ❌ **Quoting a non-original aggregator as if it were the school.** Source must be the school's own page (Tier 1) for any "what {school} says" claim.
- ❌ **Editing `index.html` to special-case a school.** Schema-driven only.
- ❌ **Dumping a screenshot from an aggregator into the repo.** Always store structured JSON with a source URL.

## Throughput plan (suggested batch sizes)

- **Day 1**: Verify your slug list against existing `knowledgebase/universities/`. Pick a starter set of 5 schools to fully process.
- **Per school target**: ~15 minutes if Tier 1 has good data; up to 45 minutes if you have to walk all three tiers and reconcile numbers.
- **Order of operations within a school**: Testing → Course Rigor → GPA → Enrollment. (Testing and Rigor are usually the easiest, GPA is the trickiest because of the Tier-2 cascade, Enrollment is the most data entry.)

## Optional improvements (if you want to scale)

- **Schema validation.** Add a `scripts/validate_data.py` script that walks `data/{enrollment,testing,gpa,rigor}/*.json`, validates against the shapes in this guide, and fails CI if any file is malformed. Hook it into the existing `tests/` suite.
- **Master index.** Generate a `data/coverage.json` listing which of the four data types each school has, so the page can sort/filter by "schools with full coverage". Regenerate it from a CI job whenever a JSON file changes.
- **`scope` enum.** Standardize on values like `official_per_major`, `class_wide`, `no_per_major_data`, `third_party_estimate`. The renderer can pick badge colors per enum value.
