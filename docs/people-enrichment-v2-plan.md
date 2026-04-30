# Goal Kicker People Enrichment v2

## Requested target
- up to 20 popular professors per school
- up to 20 successful alumni per school
- alumni filtered to the most recent 10 years
- alumni organized per major / major-related pathway
- each person should have:
  - name
  - short bio
  - confirmation link
  - ideally an official website/profile link

## What is implemented now
- `TOP_PROFESSORS = 20`
- `TOP_ALUMNI = 20`
- professor items now include:
  - `bio`
  - `confirmation_url`
  - `confirmation_label`
  - `official_website` (currently usually null)
  - `source_confidence`
- alumni items now include:
  - `bio`
  - `confirmation_url`
  - `confirmation_label`
  - `official_website` (currently usually null)
  - `major` (currently null in generic mode)
  - `graduation_year` (currently null in generic mode)
  - `within_last_10_years` (currently null in generic mode)
  - `source_confidence`
- markdown rendering now shows bios, confirmation links, and requested-target metadata

## Current hard limitation
The existing generic public-source pipeline uses:
- RateMyProfessors for professors
- Wikipedia / Wikimedia for alumni

Those sources do **not** reliably provide, for every school:
- official faculty website/profile URLs
- alumni graduation year
- alumni major
- recent-10-years filtering
- per-major alumni grouping

So the new schema is ready, but full population of the requested fields needs stronger school-specific sources.

## What is needed for the true v2 pipeline

### Professors
Preferred source order:
1. official school faculty directory / department people pages
2. official personal faculty pages on school domain
3. RateMyProfessors fallback

Needed extraction fields:
- full name
- department
- title / role
- short bio snippet
- official profile URL
- personal/official website URL if present
- optional external popularity metrics (RMP, citations, awards)

### Alumni
Preferred source order:
1. official alumni spotlights / school news / advancement pages
2. official commencement, alumni award, and career-outcomes pages
3. school-maintained notable alumni pages
4. Wikipedia fallback

Needed extraction fields:
- full name
- bio / role
- graduation year
- degree / major if available
- source date or activity date
- official confirmation URL
- optional personal/company website

## Recommended architecture for full v2

### Stage A — discovery
For each school:
- discover official faculty directories on the school domain
- discover official alumni pages on the school domain
- record discovered source patterns per school for reuse

### Stage B — structured extraction
For professors:
- scrape directory cards / profile pages
- rank by a configurable popularity heuristic
- fallback to RMP when official popularity signals are missing

For alumni:
- scrape official alumni pages
- extract year / degree / major when present
- reject entries missing evidence for recency when recent-window mode is strict

### Stage C — normalization
Normalize to:
- `school_people.popular_professors.items[]`
- `school_people.successful_alumni.items[]`
- optional future structure:
  - `school_people.successful_alumni.by_major[major_slug][]`

### Stage D — confidence and gaps
Each item should carry:
- source confidence
- whether year/major are explicit or inferred
- whether confirmation is official, semi-official, or fallback

## Suggested next implementation steps
1. build a school-domain source discovery cache
2. implement official faculty-directory extraction for 3 pilot schools
3. implement official alumni-page extraction for 3 pilot schools
4. add `by_major` output structure
5. add strict mode requiring explicit year evidence for recent-10-year alumni lists
6. expand school-by-school with cached selectors/patterns

## Practical note
A truly accurate “20 successful alumni in each major per school for the most recent 10 years” pipeline is possible, but it becomes a school-specific web data engineering problem rather than a generic Wikipedia pass.
