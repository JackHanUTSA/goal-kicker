# Goal Kicker — Build & Research Process

How the demo site at https://jackhanutsa.github.io/goal-kicker/ got built, the search strategy used to fill in admissions data, and how each data point was verified.

---

## Part 1 — Step-by-step build of the website

The site is a single static `index.html` hosted on GitHub Pages, with structured JSON data files in the same repo that the page fetches at runtime from `raw.githubusercontent.com`. No backend, no build step, no framework.

### 1. Verify the existing project

- Cloned `JackHanUTSA/goal-kicker` into the sandbox.
- Ran `pytest` against `tests/`. Got **20/20 passing**. This established a baseline that the Python research-agent code was healthy before adding anything.

### 2. Inventory the knowledgebase

- Walked `knowledgebase/universities/` and counted files: 100 schools, each with both a `.json` and `.md` record.
- Read a couple of records (`mit.json`, `uc-berkeley.json`) to learn the schema: `name`, `slug`, `rank`, `majors{count,titles,…}`, `admissions{testing_policy,gpa_policy,course_rigor,…}`, `evidence[]`.

### 3. Choose hosting (and accept the constraints)

- Tried public file hosts (0x0.st, surge.sh, transfer.sh, etc.) — all blocked by the sandbox egress allowlist.
- Confirmed that `github.com` *was* reachable, and the user was already logged into GitHub in their browser.
- Settled on **GitHub Pages** off the user's existing repo, driven via the Claude-in-Chrome extension. No tokens, no keys, no shared credentials.

### 4. Design the page architecture

Two design decisions made everything else cheaper:

1. **Fetch data at runtime, not at build time.** The page only ships `index.html` (~28 KB now). All university records, enrollment, testing, GPA, and rigor data are pulled live from `raw.githubusercontent.com/.../main/data/...`. Adding a new school later means dropping a JSON file in the repo — no rebuild.
2. **One toggle pattern, reused four times.** Every detail box (Majors, Testing, GPA, Course Rigor) follows the same shape: a clickable summary row that, on click, reveals a `<div class="toggle-wrap">` rendered from a typed JSON payload. The wiring is one helper function (`wireOne`) called four times.

### 5. Ship in increments

Each feature was a separate commit so the live site got better immediately, and a regression in one feature wouldn't block the others.

| Step | What shipped | Files committed |
|---|---|---|
| 1 | List of universities with search + filter, test-suite output | `index.html` |
| 2 | MIT enrollment data + packed-bubble chart on Majors click | `data/enrollment/mit.json`, `index.html` |
| 3 | MIT class-wide SAT/ACT ranges with bar visualization on Testing click | `data/testing/mit.json`, `index.html` |
| 4 | GPA panel (honest "no data published" treatment), Course Rigor cards | `data/gpa/mit.json`, `data/rigor/mit.json`, `index.html` |
| 5 | Recommended-GPA cards from third-party aggregators | `data/gpa/mit.json`, `index.html` |

### 6. Working around the editor's quirks

GitHub's web file editor uses CodeMirror 6, which isn't directly scriptable from outside the page. To paste a 28 KB HTML file:

- Encoded the file as base64 in chunks of ~12 KB.
- Pushed each chunk into a `window.__b64` variable via `javascript_tool`.
- After all chunks accumulated, decoded via `atob()` + `TextDecoder('utf-8')` and inserted with `document.execCommand('insertText', …)` in a single shot.
- One nuance: when the file extension is `.json`, CM enables auto-bracket-completion, and inserting a large JSON in chunks corrupts the editor and freezes the page. Workaround: insert in **one** `execCommand` call, not many — because the chunk already has balanced braces, auto-pair stays out of the way.

### 7. Verify after each commit

- After each commit, navigated to https://jackhanutsa.github.io/goal-kicker/ in the user's browser, hit the row, opened the relevant panel, and checked that:
  - The data rendered (no fetch errors visible in DevTools).
  - The numbers matched what the source page actually said.
  - Source links opened to the right place.

---

## Part 2 — Search plan: where to look, in what order, and what to do when it fails

The recurring research question was: *"What does $school officially say about $thing (majors enrollment, SAT/ACT, GPA, course rigor)?"* My priority order was always **official → semi-official → third-party with attribution**, and never **made up**.

### Tier 1 — The school's own admissions site

**First stop, every time.** This is the only source where claims are unambiguously the school's own.

- For MIT: `mitadmissions.org` and `registrar.mit.edu`.
- Specific landing pages I always tried:
  - `/apply/process/stats/` — admit rate, test ranges, geography.
  - `/apply/prepare/foundations/` (or equivalent) — recommended HS coursework.
  - `/apply/process/selection/` — what they say about the holistic process.
  - `registrar.mit.edu/stats-reports/` — enrollment-by-major counts.

**If the official site doesn't have it →** check whether the school publishes the *Common Data Set* (almost every US school does). The CDS has standard fields like C9 (test scores), C11 (GPA / class rank), C2 (admit rate) that are filled in or explicitly marked "not reported". This was the source for confirming MIT does not publish HS GPA data.

**If a specific page 404s →** click into the school's "Statistics & Reports" or "Admission requirements" landing page and follow links from there. URLs change; landing pages tend not to.

### Tier 2 — Third-party aggregators

Used **only** when Tier 1 explicitly says the data isn't published, or when the user wants a directional estimate. I always show the source name on the rendered card so the reader can decide how much to trust it.

The order I tried for MIT's GPA estimate:

1. **PrepScholar** (`prepscholar.com/sat/s/colleges/MIT-admission-requirements`) — usually has a numeric "Average GPA" with their methodology disclosed. Got **4.19 weighted**.
2. **Niche** (`niche.com/colleges/.../admissions/`) — sometimes lists an HS GPA. For MIT they don't publish a number ("Considered but not required") — moved on.
3. **US News** (`usnews.com/best-colleges/.../applying`) — describes selectivity factors. Confirmed GPA is "an important academic factor" but no numeric value on the free page; the actual number sits behind College Compass.
4. **CollegeSimply** (`collegesimply.com/colleges/.../admission/`) — Got **3.96 unweighted** with their algorithm caveat.
5. **College Scorecard** (federal data) — confirmed it has admit rate, costs, and earnings but not HS GPA. Useful negative result.

**The cascade rule:** if a Tier 2 source publishes a number, also capture *how* they got it (algorithm, self-reports, scraped CDS) and put that on the card under the value. Two sources with different methodologies (4.19 weighted vs. 3.96 unweighted) is more honest than one number alone — readers see they're talking about different scales.

### Tier 3 — When nothing reliable exists

For per-major SAT/ACT scores at MIT, no Tier 1 or Tier 2 source publishes the data — almost no school does. I refused to generate synthetic estimates. Instead the panel now:

- Shows the *class-wide* range (real, official, single-source).
- Has a clear amber "Scope" note: *"MIT does not publish admitted SAT/ACT scores broken down by major. The numbers below are MIT's published class-wide middle 50% ranges."*

That's the rule: **when good data doesn't exist, say so on the page.**

### Egress-blocked detour

The sandbox can't reach most websites — only `github.com`, npm/pypi mirrors, and a few Anthropic domains. So all Tier 1/2 lookups had to go through the user's browser via the Claude-in-Chrome extension:

- `navigate` → wait for load → `get_page_text` for short articles, or `javascript_tool` with a regex against `document.body.innerText` for specific values.
- For numeric values: `text.match(/Average GPA:\s*([\d.]+)/)` — much faster and more reliable than asking for the whole page text and scrolling.

---

## Part 3 — How each data point was verified

Every claim displayed on the site has at least one of these guarantees:

### A. Source URL on the rendered card

Every panel renders a `source` link next to its title. The user (or any reviewer) can click through and check the page directly. No one has to trust me; everything is one click away from primary evidence.

For multi-claim panels (GPA's "What MIT does say" list), each individual claim has its own `source_url`.

### B. Direct quoting + small extracts

When pulling text from a source, I stored MIT's actual phrasing in the JSON (e.g., *"the most important thing to remember is that at MIT we admit people, not numbers"*). That way a reviewer can grep the source page for the exact phrase and confirm it.

### C. Cross-checking numbers across two sources

For MIT's enrollment, the registrar page reported a Grand Total of **4,961** declared majors. The 56 records I parsed sum to **3,636.5** — the gap (1,155 first-years + 10 undesignated sophomores + ~150 from joint-major halving) reconciles with what the page also publishes as "Undesignated Sophomores" and "First Year". I checked the arithmetic before shipping. If it hadn't reconciled, that would have been a flag that I'd misread the table.

### D. Scope notes for every dataset

Each JSON file has a top-level `scope_note` describing what the dataset is and isn't. Examples shipped:

- Testing: *"MIT does not publish admitted SAT/ACT scores broken down by major. The numbers below are MIT's published class-wide middle 50% ranges for the most recent admitted class."*
- GPA: *"MIT does not publish a minimum GPA cutoff, an admitted-student GPA distribution, or any GPA breakdown by major. Their stated process is holistic, not numeric."*
- Course Rigor: *"MIT publishes recommended high-school preparation but does not require a specific course list. Recommendations apply to all admitted students; MIT does not break course-rigor expectations down by major."*
- Recommended GPA: *"MIT does not publish HS GPA data for its incoming class. The numbers below are third-party predictions, not official MIT figures. Use them as a directional reference, not a cutoff."*

The scope note is the first thing the reader sees inside the panel, in amber. It's deliberately hard to ignore.

### E. Live-render verification

After each commit, I:

1. Hard-refreshed the live page (`?bust=…`).
2. Opened the panel.
3. Confirmed the numbers matched what I'd put into the JSON.
4. Confirmed the source link landed on the page that the value came from.

If a panel didn't render or numbers were off, that meant a real bug — usually a CDN cache lag or a JSON parse failure — and got fixed before moving on.

### F. Honest-failure default

When a source doesn't publish a number, the JSON either:
- Omits the field entirely (panel shows policy text without numbers), or
- Sets `scope: "no_per_major_data"` and the panel displays the scope note prominently instead of fake numbers.

The site never invents data.

---

## File map

```
goal-kicker/
├── index.html                      # the demo page (28 KB, single file)
├── data/
│   ├── enrollment/mit.json         # Tier-1: registrar.mit.edu
│   ├── testing/mit.json            # Tier-1: mitadmissions.org/apply/process/stats
│   ├── gpa/mit.json                # Tier-1 holistic policy + Tier-2 estimates
│   ├── rigor/mit.json              # Tier-1: mitadmissions.org/apply/prepare/foundations
│   └── top50_universities.json     # the master list the page loads first
├── knowledgebase/universities/     # 100 schools × {.json, .md}
└── tests/                          # pytest suite, 20/20 passing
```

## Adding a new school

The pattern is school-agnostic. To add `caltech` for example:

1. Find Caltech's enrollment-by-major page (Tier 1).
2. Drop `data/enrollment/caltech.json` with the same shape as MIT's.
3. Repeat for testing/gpa/rigor as data is available.
4. Push. The page picks them up automatically — no code change needed.

The boxes that have data become clickable; ones without data render plain text and stay non-clickable. Same UX, no template editing.
