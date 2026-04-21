# Goal Kicker

Goal Kicker is a Hermes-like research agent project for building a structured LLM knowledgebase about the top 100 universities in the United States.

Primary objective:
- learn the top 100 USA universities
- determine how many majors each university offers
- collect the standard expectations a high school student should meet to be a competitive applicant
- build the knowledgebase step by step as each university is scanned

Examples of applicant signals to capture:
- GPA expectations or typical admitted GPA ranges
- SAT/ACT policy and typical score ranges if published
- AP/IB / rigorous coursework expectations
- extracurricular expectations
- research, projects, leadership, volunteering, competitions, internships
- portfolio or audition requirements where relevant
- recommendation / essay expectations if clearly documented

Important constraint:
- the system should avoid hallucinating admissions standards
- every claim should be attached to a source and date
- the knowledgebase should distinguish between:
  - official university requirements
  - common admitted-student profile ranges
  - inferred competitiveness notes

## Project vision

The end product should behave like a Hermes-style agent that can:
1. discover a university source page
2. extract majors and admissions requirements
3. normalize them into a common schema
4. update a growing markdown/JSON knowledgebase
5. answer questions like:
   - "How many majors does Stanford have?"
   - "What should a 4.0 GPA student still need beyond grades to be competitive at MIT?"
   - "Which top universities explicitly value research or maker projects?"
   - "Which schools are test-optional versus test-required?"

## Initial scope

Target set:
- top 100 U.S. universities

For each university, collect at minimum:
- university name
- official admissions page(s)
- undergraduate admissions requirements page(s)
- majors/programs listing page(s)
- estimated count of majors
- admissions policy summary
- academic expectations summary
- extracurricular/project expectations summary
- notes on ambiguity or missing data
- source URLs
- last-updated crawl date

## Suggested output structure

Knowledgebase lives under `knowledgebase/`:
- `knowledgebase/raw/`
  - raw extracted source text / html / markdown snapshots
- `knowledgebase/universities/`
  - one normalized markdown or JSON file per university
- `knowledgebase/requirements/`
  - cross-university normalized requirement tables
- `knowledgebase/majors/`
  - university major counts and program-list references

## Proposed core components

- `src/discovery/`
  - find official university pages
- `src/extract/`
  - parse admissions and majors pages
- `src/normalize/`
  - convert source data into a common schema
- `src/kb/`
  - write markdown/JSON knowledgebase entries
- `src/agent/`
  - orchestration logic for step-by-step scanning
- `scripts/`
  - runnable entry points for crawl / refresh / verify

## Data model sketch

Per-university record should include fields like:
- `name`
- `rank_bucket` or source ranking list
- `official_domain`
- `majors_count`
- `majors_source_url`
- `admissions_source_urls`
- `minimum_requirements`
- `competitive_profile`
- `course_rigor_notes`
- `testing_policy`
- `essay_requirements`
- `recommendation_requirements`
- `project_extracurricular_notes`
- `special_program_notes`
- `last_verified_at`
- `confidence`

## Recommended development order

1. define the top-100 university seed list
2. define the normalized schema
3. build one-university ingestion workflow
4. write university markdown + JSON outputs
5. validate on 3-5 schools first
6. expand to full top 100
7. add question-answering over the accumulated knowledgebase

## Key design rules

- prefer official university sources over blogs or ranking sites
- if a value is not stated by the school, mark it as unknown instead of guessing
- separate hard requirements from "competitive profile" guidance
- record source URLs for every important field
- keep step-by-step ingest logs so the agent can resume cleanly

## Current status

Project scaffold created.
Next recommended file:
- `docs/goal-kicker-implementation-plan.md`
