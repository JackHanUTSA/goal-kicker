# Goal Kicker Implementation Plan

> For Hermes: implement this project in small validated steps. Prefer official university sources, save every source URL, and never guess missing admissions criteria.

Goal:
Build a Hermes-like agent that learns the top 100 U.S. universities, captures how many majors each offers, records what a strong high school applicant typically needs, and grows a step-by-step LLM-readable knowledgebase as each university is scanned.

Architecture:
Use a pipeline with five layers:
1. seed list + source discovery
2. extraction from official admissions and majors pages
3. normalization into a common schema
4. markdown/JSON knowledgebase writing
5. QA/query layer over the accumulated knowledgebase

Tech stack:
- Python 3
- markdown + JSON knowledgebase files
- web retrieval/extraction
- optional SQLite for indexing later

---

## Directory plan

Project root:
- `/home/jack/swarmlab/projects/goal-kicker`

Existing scaffold:
- `README.md`
- `docs/`
- `src/`
- `scripts/`
- `data/`
- `knowledgebase/raw/`
- `knowledgebase/universities/`
- `knowledgebase/requirements/`
- `knowledgebase/majors/`

## Phase 1: establish seeds and schema

### Task 1: Create the seed university list
Objective:
Create a canonical list of the top 100 U.S. universities to scan.

Files:
- Create: `data/top50_universities.json`
- Create: `data/top50_universities.md`

Fields per seed:
- `name`
- `short_name`
- `official_domain`
- `notes`
- `status` (`pending`, `in_progress`, `done`)

Definition note:
Pick one ranking source for the initial seed list and store that source in metadata. The agent can be expanded later to support alternate ranking lists.

### Task 2: Define the normalized university schema
Objective:
Define exactly what each university record must contain.

Files:
- Create: `docs/schema.md`
- Create: `data/university_schema.json`

Required fields:
- university identity
- source URLs
- majors count
- majors source page
- freshman admissions requirements
- testing policy
- GPA/course-rigor notes
- extracurricular/project notes
- essays/recommendations requirements
- confidence and last verified time

### Task 3: Define evidence rules
Objective:
Prevent the system from mixing hard requirements with inferred competitiveness.

Files:
- Create: `docs/evidence-policy.md`

Rules:
- tag each extracted statement as one of:
  - `official_requirement`
  - `official_recommendation`
  - `reported_profile`
  - `inference`
- if only inferred, say so explicitly
- if unknown, store null/unknown

## Phase 2: build single-university ingestion

### Task 4: Create source discovery module
Objective:
Given one university seed, find official admissions and majors pages.

Files:
- Create: `src/discovery/find_sources.py`
- Create: `scripts/find_sources.py`

Output fields:
- `admissions_url`
- `requirements_url`
- `majors_url`
- `additional_urls`

### Task 5: Create raw source snapshot writer
Objective:
Save every fetched source into the knowledgebase raw layer.

Files:
- Create: `src/kb/raw_store.py`
- Create: `knowledgebase/raw/.gitkeep`

Naming convention:
- `knowledgebase/raw/<university-slug>/<timestamp>-<source-type>.md`
- preserve original URL and fetched-at timestamp in frontmatter

### Task 6: Create majors extractor
Objective:
Extract majors/program count from official pages.

Files:
- Create: `src/extract/majors.py`
- Create: `scripts/extract_majors.py`

Output:
- raw major titles if possible
- computed count
- extraction confidence
- majors source URL

### Task 7: Create admissions extractor
Objective:
Extract official admissions expectations and competitiveness notes.

Files:
- Create: `src/extract/admissions.py`
- Create: `scripts/extract_admissions.py`

Capture:
- GPA/course rigor language
- testing policy
- recommendations
- essays
- extracurricular/project language
- portfolio/audition requirements if applicable

### Task 8: Create normalization logic
Objective:
Map extracted text into a common structured record.

Files:
- Create: `src/normalize/university_record.py`

Output schema:
- one canonical Python dict matching `data/university_schema.json`

## Phase 3: write the knowledgebase

### Task 9: Create per-university markdown writer
Objective:
Write a readable markdown page for each school.

Files:
- Create: `src/kb/write_markdown.py`
- Output: `knowledgebase/universities/<slug>.md`

Markdown sections:
- Overview
- Official sources
- Majors
- Admissions requirements
- Competitive profile
- Project/extracurricular expectations
- Unknowns / caveats

### Task 10: Create per-university JSON writer
Objective:
Write machine-readable structured outputs.

Files:
- Create: `src/kb/write_json.py`
- Output: `knowledgebase/universities/<slug>.json`

### Task 11: Create cross-university rollups
Objective:
Aggregate key comparisons across schools.

Files:
- Create: `src/kb/build_rollups.py`
- Output: `knowledgebase/requirements/testing_policy.json`
- Output: `knowledgebase/requirements/admissions_signals.json`
- Output: `knowledgebase/majors/majors_counts.json`

## Phase 4: orchestrate agent behavior

### Task 12: Create one-school pipeline runner
Objective:
Run discovery -> fetch -> extract -> normalize -> write for one school.

Files:
- Create: `src/agent/run_one_university.py`
- Create: `scripts/run_one_university.py`

CLI example:
- `python scripts/run_one_university.py --school "Stanford University"`

### Task 13: Create top-100 batch runner
Objective:
Process schools one by one and resume safely.

Files:
- Create: `src/agent/run_batch.py`
- Create: `scripts/run_batch.py`
- Create: `data/progress.json`

Behavior:
- skip already complete schools unless `--refresh`
- save progress after each school
- log failures cleanly

### Task 14: Create verification pass
Objective:
Check each university record for missing critical fields.

Files:
- Create: `src/agent/verify_record.py`
- Create: `scripts/verify_knowledgebase.py`

Checks:
- missing majors count
- missing official source URLs
- missing testing policy
- unsupported inference without citation

## Phase 5: query and explain

### Task 15: Create simple query layer
Objective:
Answer user questions from the generated knowledgebase.

Files:
- Create: `src/agent/query.py`
- Create: `scripts/query.py`

Queries to support first:
- count of majors by school
- schools with strongest project/research emphasis
- GPA/testing policy summaries
- side-by-side comparison for 2-3 universities

### Task 16: Create applicant-fit summary format
Objective:
Turn university records into practical guidance for high school students.

Files:
- Create: `docs/applicant-summary-format.md`
- Create: `src/agent/fit_summary.py`

Example output:
- academics needed
- projects/research leadership signals
- essays/recommendations signals
- gaps/unknowns

## First milestone recommendation

Before attempting all 50 universities, validate on these 5:
- MIT
- Stanford
- Harvard
- UC Berkeley
- University of Michigan

Success criteria for milestone 1:
- seed records exist
- one-command ingestion works per school
- markdown + JSON output generated
- majors count captured with source URL
- admissions expectations separated into official vs inferred

## Suggested immediate next implementation files

Create next:
- `data/top50_universities.json`
- `data/university_schema.json`
- `docs/schema.md`
- `docs/evidence-policy.md`
- `scripts/run_one_university.py`

## Deliverable definition

A successful Goal Kicker system should produce:
- a maintained knowledgebase for top 100 U.S. universities
- structured source-backed university records
- human-readable summaries for students
- machine-readable JSON for later LLM / search / ranking use
- resumable step-by-step ingestion logs
