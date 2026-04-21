#!/usr/bin/env /usr/bin/python3
from __future__ import annotations

import json
import re
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
UNI_DIR = ROOT / "knowledgebase" / "universities"
REQ_DIR = ROOT / "knowledgebase" / "requirements"
MAJ_DIR = ROOT / "knowledgebase" / "majors"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 25
MAX_PAGES = 8
MAX_LINKS_PER_PAGE = 12
KEY_LINK_TERMS = (
    "apply",
    "admission",
    "admissions",
    "requirements",
    "deadlines",
    "testing",
    "test",
    "essay",
    "writing",
    "recommend",
    "academics",
    "academic",
    "majors",
    "major",
    "programs",
    "areas-of-study",
    "fields-of-study",
    "research",
)
BLOCK_TERMS = (
    "cloudflare",
    "attention required",
    "enable cookies",
    "access denied",
    "captcha",
)

SPECIAL_URL_HINTS = {
    "johns-hopkins": [
        "https://admissions.jhu.edu/apply/",
        "https://admissions.jhu.edu/academics",
        "https://e-catalogue.jhu.edu/arts-sciences/full-time-residential-programs-of-study/",
        "https://e-catalogue.jhu.edu/engineering/full-time-residential-programs-of-study/",
    ],
    "brown": [
        "https://admission.brown.edu/first-year/application-checklist",
        "https://admission.brown.edu/first-year/standardized-tests",
        "https://admission.brown.edu/explore/academics",
    ],
    "cornell": [
        "https://admissions.cornell.edu/how-to-apply/first-year-applicants",
        "https://admissions.cornell.edu/how-to-apply/first-year-applicants/college-and-school-admissions-requirements",
        "https://admissions.cornell.edu/academics/majors",
    ],
    "ucla": [
        "https://admission.ucla.edu/apply/freshman",
        "https://admission.ucla.edu/academics/majors",
        "https://admission.ucla.edu/learn-more/first-year-applicant",
    ],
    "georgetown": [
        "https://uadmissions.georgetown.edu/apply/first-year/",
        "https://uadmissions.georgetown.edu/explore/academics/",
    ],
    "uva": [
        "https://admission.virginia.edu/admission/first-year-admission",
        "https://admission.virginia.edu/admission/deadlines-instructions",
        "https://admission.virginia.edu/academics",
    ],
    "wake-forest": [
        "https://admissions.wfu.edu/apply/",
        "https://admissions.wfu.edu/academics/",
    ],
    "boston-college": [
        "https://www.bc.edu/content/bc-web/admission/apply.html",
        "https://www.bc.edu/content/bc-web/admission/academics.html",
    ],
    "unc-chapel-hill": [
        "https://admissions.unc.edu/apply/first-year-students/",
        "https://admissions.unc.edu/explore/academics/",
    ],
    "usc": [
        "https://admission.usc.edu/apply/first-year-students/",
        "https://admission.usc.edu/learn/academic-life/",
    ],
    "northwestern": [
        "https://admissions.northwestern.edu/apply/requirements.html",
        "https://admissions.northwestern.edu/academics/",
    ],
    "rice": [
        "https://admission.rice.edu/apply/freshman-applicants",
        "https://admission.rice.edu/academics",
    ],
    "washu": [
        "https://admissions.wustl.edu/how-to-apply/",
        "https://admissions.wustl.edu/academics/",
    ],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def strip_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def same_school_domain(netloc: str, official_domain: str) -> bool:
    host = netloc.lower()
    domain = official_domain.lower()
    return host == domain or host.endswith(f".{domain}")


def candidate_urls(record: dict) -> list[str]:
    domain = record["official_domain"]
    urls = []
    urls.extend(SPECIAL_URL_HINTS.get(record["slug"], []))
    urls.extend(
        [
            f"https://admissions.{domain}/",
            f"https://admission.{domain}/",
            f"https://apply.{domain}/",
            f"https://www.{domain}/",
            f"https://www.{domain}/admissions",
            f"https://www.{domain}/admission",
            f"https://www.{domain}/apply",
            f"https://www.{domain}/academics",
            f"https://www.{domain}/majors",
        ]
    )
    for group in ("admissions", "majors", "general"):
        urls.extend(record.get("source_urls", {}).get(group, []))
    deduped = []
    seen = set()
    for url in urls:
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(url)
    return deduped


def fetch_page(session: requests.Session, url: str) -> dict | None:
    try:
        response = session.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except Exception:
        return None
    text = response.text or ""
    lower = text.lower()
    blocked = any(term in lower for term in BLOCK_TERMS)
    soup = BeautifulSoup(text, "lxml")
    page_texts = []
    for tag in soup.find_all(["title", "h1", "h2", "h3", "p", "li", "a"]):
        t = strip_text(tag.get_text(" ", strip=True))
        if t:
            page_texts.append(t)
    all_text = "\n".join(page_texts)
    return {
        "requested_url": url,
        "url": response.url,
        "status_code": response.status_code,
        "blocked": blocked,
        "soup": soup,
        "texts": page_texts,
        "all_text": all_text,
    }


def relevant_links(page: dict, official_domain: str) -> list[str]:
    discovered = []
    for anchor in page["soup"].find_all("a", href=True):
        href = urljoin(page["url"], anchor["href"])
        parsed = urlparse(href)
        if not parsed.scheme.startswith("http"):
            continue
        if not same_school_domain(parsed.netloc, official_domain):
            continue
        blob = f"{strip_text(anchor.get_text(' ', strip=True))} {href}".lower()
        if any(term in blob for term in KEY_LINK_TERMS):
            discovered.append(href)
    out = []
    seen = set()
    for href in discovered:
        if href in seen:
            continue
        seen.add(href)
        out.append(href)
        if len(out) >= MAX_LINKS_PER_PAGE:
            break
    return out


def crawl_school(record: dict) -> list[dict]:
    session = requests.Session()
    queue = deque(candidate_urls(record))
    seen = set()
    pages = []
    while queue and len(pages) < MAX_PAGES:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        page = fetch_page(session, url)
        if not page:
            continue
        pages.append(page)
        for href in relevant_links(page, record["official_domain"]):
            if href not in seen:
                queue.append(href)
        time.sleep(0.25)
    return pages


def contains_term(line: str, term: str) -> bool:
    escaped = re.escape(term.lower())
    hay = line.lower()
    if re.fullmatch(r"[a-z0-9.+-]+", term.lower()):
        return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", hay) is not None
    return escaped in hay


def choose_line(texts: Iterable[str], predicates: list[str], exclude: Iterable[str] = ()) -> str | None:
    exclude_set = tuple(item.lower() for item in exclude)
    candidates = []
    for line in texts:
        lower = line.lower()
        if len(line) < 25:
            continue
        if exclude_set and any(item in lower for item in exclude_set):
            continue
        if all(contains_term(lower, term) for term in predicates):
            candidates.append(line)
    if not candidates:
        return None
    candidates.sort(key=lambda item: (len(item), item))
    return candidates[0]


def choose_any_line(texts: Iterable[str], include_terms: Iterable[str], exclude: Iterable[str] = ()) -> str | None:
    include = tuple(term.lower() for term in include_terms)
    exclude = tuple(term.lower() for term in exclude)
    candidates = []
    for line in texts:
        lower = line.lower()
        if len(line) < 25:
            continue
        if exclude and any(term in lower for term in exclude):
            continue
        if any(contains_term(lower, term) for term in include):
            candidates.append(line)
    if not candidates:
        return None
    candidates.sort(key=lambda item: (len(item), item))
    return candidates[0]


def find_page_url(pages: list[dict], terms: Iterable[str]) -> str | None:
    lowered = tuple(term.lower() for term in terms)
    for page in pages:
        url = page["url"].lower()
        if any(term in url for term in lowered):
            return page["url"]
    return pages[0]["url"] if pages else None


def classify_application_platform(texts: list[str]) -> str | None:
    text = "\n".join(texts).lower()
    if "common application" in text or "common app" in text:
        return "Common Application"
    if "coalition application" in text or "coalition" in text:
        return "Coalition Application"
    if "applytexas" in text:
        return "ApplyTexas"
    if "university of california application" in text or "uc application" in text:
        return "UC Application"
    return None


def extract_testing_policy(texts: list[str]) -> str | None:
    preferred = [
        ("sat", "act", "require"),
        ("sat", "act", "required"),
        ("test-optional",),
        ("test optional",),
        ("test-flexible",),
        ("standardized", "test", "score"),
    ]
    for group in preferred:
        line = choose_line(texts, list(group), exclude=["contact us", "faq", "transfer", "student success"])
        if line:
            return line
    return choose_any_line(
        texts,
        ["sat", "act", "test-optional", "test optional", "standardized test", "testing policy"],
        exclude=["contact us", "faq", "transfer", "student success"],
    )


def extract_gpa_policy(texts: list[str]) -> str | None:
    line = choose_any_line(texts, [" gpa", "gpa ", "grade point average"], exclude=["transfer", "faq"])
    if line:
        return line
    return None


def extract_course_rigor(texts: list[str]) -> str | None:
    return choose_any_line(
        texts,
        ["rigor", "rigorous", "coursework", "curriculum", "transcript", "most challenging", "academic preparation"],
        exclude=["transfer", "faq", "contact us"],
    )


def extract_recommendations(texts: list[str]) -> str | None:
    return choose_any_line(
        texts,
        ["recommendation", "recommendations", "teacher evaluation", "teacher recommendation", "counselor recommendation", "letters of recommendation"],
        exclude=["transfer", "faq", "contact us"],
    )


def extract_essays(texts: list[str]) -> str | None:
    return choose_any_line(
        texts,
        ["essay", "essays", "personal statement", "writing supplement", "short-answer", "short answer"],
        exclude=["transfer", "faq", "contact us"],
    )


def extract_research_signal(texts: list[str]) -> str | None:
    return choose_any_line(texts, ["undergraduate research", "research opportunities", "research", "projects"], exclude=["faculty research", "contact us"])


def majors_count_from_line(line: str) -> int | None:
    normalized = line.lower().replace(",", "")
    patterns = [
        r"one of (\d{1,3})(?:\+)? (?:[a-z-]+\s+){0,3}(?:majors|concentrations|programs|fields of study|areas of study)",
        r"choose from among (\d{1,3})(?:\+)? (?:[a-z-]+\s+){0,3}(?:majors|concentrations|programs|fields of study|areas of study)",
        r"over (\d{1,3})(?:\+)? (?:[a-z-]+\s+){0,3}(?:majors|concentrations|programs|fields of study|areas of study)",
        r"more than (\d{1,3})(?:\+)? (?:[a-z-]+\s+){0,3}(?:majors|concentrations|programs|fields of study|areas of study)",
        r"nearly (\d{1,3})(?:\+)? (?:[a-z-]+\s+){0,3}(?:majors|concentrations|programs|fields of study|areas of study)",
        r"offers (\d{1,3})(?:\+)? (?:[a-z-]+\s+){0,3}(?:majors|concentrations|programs|fields of study|areas of study)",
        r"(\d{1,3})(?:\+)? undergraduate (?:[a-z-]+\s+){0,3}(?:majors|concentrations|programs|fields of study|areas of study)",
        r"(\d{1,3})(?:\+)? (?:[a-z-]+\s+){0,3}(?:majors|concentrations|programs|fields of study|areas of study)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            return int(match.group(1))
    return None


def count_major_like_items(page: dict, official_domain: str) -> tuple[int | None, str | None]:
    terms = set()
    for tag in page["soup"].find_all(["a", "li"]):
        text = strip_text(tag.get_text(" ", strip=True))
        lower = text.lower()
        if not text:
            continue
        if len(text) < 4 or len(text) > 100:
            continue
        if any(bad in lower for bad in ["minor", "certificate", "faq", "contact", "apply", "admission", "student life", "learn more", "request information"]):
            continue
        if lower.count(" ") < 1:
            continue
        href = None
        if tag.name == "a" and tag.get("href"):
            href = urljoin(page["url"], tag.get("href"))
            if not same_school_domain(urlparse(href).netloc, official_domain):
                continue
        keywordish = any(word in lower for word in ["major", "program", "study", "science", "engineering", "arts", "mathematics", "history", "biology", "economics", "computer", "physics", "chemistry"]) or (href and any(token in href.lower() for token in ["major", "program", "academics", "study", "department"]))
        if keywordish:
            terms.add(text)
    if 15 <= len(terms) <= 250:
        return len(terms), f"counted {len(terms)} unique major/program-like entries from the cited official page DOM"
    return None, None


def extract_majors_info(pages: list[dict], record: dict) -> tuple[int | None, str | None, str | None, str | None]:
    major_pages = [
        page for page in pages
        if any(term in page["url"].lower() for term in ["major", "majors", "academic", "academics", "program", "study", "catalog"])
    ]
    if not major_pages:
        major_pages = pages[:]
    for page in major_pages:
        for line in page["texts"]:
            if any(word in line.lower() for word in ["major", "majors", "concentration", "concentrations", "fields of study", "areas of study", "programs"]):
                count = majors_count_from_line(line)
                if count is not None:
                    return count, line, page["url"], "explicit official page sentence"
    for page in major_pages:
        count, method = count_major_like_items(page, record["official_domain"])
        if count is not None:
            sample = choose_any_line(page["texts"], ["major", "program", "study", "academics"], exclude=["contact us", "faq"]) or page["texts"][0]
            return count, sample, page["url"], method
    return None, None, None, None


def upsert_evidence(record: dict, field: str, claim: str, classification: str, source_url: str | None, source_excerpt: str | None) -> None:
    if not source_url:
        return
    clean = [item for item in record.get("evidence", []) if item.get("field") and item.get("source_url")]
    key = (field, claim, source_url)
    clean = [item for item in clean if (item.get("field"), item.get("claim"), item.get("source_url")) != key]
    clean.append(
        {
            "field": field,
            "claim": claim,
            "classification": classification,
            "source_url": source_url,
            "source_excerpt": source_excerpt or "",
            "retrieved_at": now_iso(),
        }
    )
    record["evidence"] = clean


def save_record(record: dict) -> None:
    (UNI_DIR / f"{record['slug']}.json").write_text(json.dumps(record, indent=2))
    lines = [
        "---",
        f"name: {record['name']}",
        f"short_name: {record['short_name']}",
        f"slug: {record['slug']}",
        f"rank: {record['rank']}",
        f"official_domain: {record['official_domain']}",
        f"status: {record['verification']['confidence']}",
        "---",
        "",
        f"# {record['name']}",
        "",
        "## Official sources",
    ]
    for group in ("admissions", "majors"):
        lines.append(f"### {group.title()}")
        for url in record.get("source_urls", {}).get(group, []):
            lines.append(f"- {url}")
        lines.append("")
    lines += [
        "## Structured extraction",
        f"- Majors count: {record['majors']['count']}",
        f"- Count method: {record['majors']['count_method']}",
        f"- Testing policy: {record['admissions']['testing_policy']}",
        f"- GPA policy: {record['admissions']['gpa_policy']}",
        f"- Course rigor: {record['admissions']['course_rigor']}",
        f"- Recommendations: {record['admissions']['recommendations']}",
        f"- Essays: {record['admissions']['essays']}",
        "",
        "## Warnings",
    ]
    for warning in record.get("verification", {}).get("warnings", []):
        lines.append(f"- {warning}")
    (UNI_DIR / f"{record['slug']}.md").write_text("\n".join(lines))


def update_record(record: dict, pages: list[dict]) -> dict:
    texts = []
    for page in pages:
        texts.extend(page["texts"])

    admissions_urls = []
    majors_urls = []
    for page in pages:
        url_lower = page["url"].lower()
        if any(token in url_lower for token in ["apply", "admission", "requirements", "deadline", "testing", "essay", "recommend"]):
            admissions_urls.append(page["url"])
        if any(token in url_lower for token in ["major", "academ", "program", "study", "catalog"]):
            majors_urls.append(page["url"])

    testing = extract_testing_policy(texts)
    gpa = extract_gpa_policy(texts)
    course_rigor = extract_course_rigor(texts)
    recommendations = extract_recommendations(texts)
    essays = extract_essays(texts)
    research_signal = extract_research_signal(texts)
    platform = classify_application_platform(texts)
    majors_count, majors_excerpt, majors_url, majors_method = extract_majors_info(pages, record)

    warnings = [
        warning
        for warning in record.get("verification", {}).get("warnings", [])
        if "scaffold only" not in warning.lower()
    ]

    if not gpa:
        gpa = "No explicit minimum GPA was found on the cited official pages used in this auto-enrichment pass."
        warnings.append("GPA policy was normalized from absence of an explicit minimum-GPA statement on the cited official pages.")
    if not testing:
        testing = "Testing policy could not be confidently extracted from the cited official pages in this auto-enrichment pass."
        warnings.append("Testing policy needs manual confirmation; the crawler did not find a clean official testing-policy sentence.")
    if majors_count is None:
        majors_count = 0
        majors_method = "auto-enrichment could not derive a reliable major/program count from the pages reached in this pass"
        warnings.append("Majors count needs manual confirmation; the crawler did not find a clean count or stable program-list page.")
    if not course_rigor:
        course_rigor = "unknown"
    if not recommendations:
        recommendations = "unknown"
    if not essays:
        essays = "unknown"

    record.setdefault("source_urls", {})
    record["source_urls"]["admissions"] = sorted(set(admissions_urls))[:8] or record["source_urls"].get("admissions", [])
    record["source_urls"]["majors"] = sorted(set(majors_urls))[:8] or record["source_urls"].get("majors", [])

    record["majors"]["count"] = majors_count
    record["majors"]["count_method"] = majors_method or record["majors"].get("count_method") or "heuristic DOM count"
    record["majors"]["notes"] = record["majors"]["count_method"]
    record["majors"]["confidence"] = "medium" if majors_count and majors_count > 0 else "low"

    record["admissions"]["application_platform"] = platform or record["admissions"].get("application_platform")
    record["admissions"]["testing_policy"] = testing
    record["admissions"]["gpa_policy"] = gpa
    record["admissions"]["course_rigor"] = course_rigor
    record["admissions"]["recommendations"] = recommendations
    record["admissions"]["essays"] = essays
    if research_signal and not record["competitive_signals"].get("projects_research"):
        record["competitive_signals"]["projects_research"] = [research_signal]

    upsert_evidence(record, "majors.count", f"Majors/program count recorded as {majors_count}", "official_requirement", majors_url, majors_excerpt or record["majors"]["count_method"])
    upsert_evidence(record, "admissions.testing_policy", testing, "official_requirement", find_page_url(pages, ["testing", "apply", "admission", "requirements"]), testing)
    upsert_evidence(record, "admissions.gpa_policy", gpa, "reported_profile", find_page_url(pages, ["apply", "admission", "requirements", "first-year"]), gpa)
    if course_rigor != "unknown":
        upsert_evidence(record, "admissions.course_rigor", course_rigor, "reported_profile", find_page_url(pages, ["academics", "apply", "admission"]), course_rigor)
    if recommendations != "unknown":
        upsert_evidence(record, "admissions.recommendations", recommendations, "official_requirement", find_page_url(pages, ["recommend", "apply", "requirements"]), recommendations)
    if essays != "unknown":
        upsert_evidence(record, "admissions.essays", essays, "official_requirement", find_page_url(pages, ["essay", "writing", "apply"]), essays)

    unknown = []
    for field_path, value in [
        ("majors.count", record["majors"]["count"]),
        ("admissions.testing_policy", record["admissions"]["testing_policy"]),
        ("admissions.gpa_policy", record["admissions"]["gpa_policy"]),
        ("admissions.course_rigor", record["admissions"]["course_rigor"]),
        ("admissions.recommendations", record["admissions"]["recommendations"]),
        ("admissions.essays", record["admissions"]["essays"]),
    ]:
        if value in (None, "", "unknown"):
            unknown.append(field_path)
    if not record["competitive_signals"].get("projects_research"):
        unknown.append("competitive_signals.projects_research")

    warnings = list(dict.fromkeys(warnings))
    warnings.insert(0, "Phase 5 auto-enrichment completed using official-school web crawl heuristics; manual spot-checking is still recommended for edge cases.")

    record["verification"]["last_verified_at"] = now_iso()
    record["verification"]["confidence"] = "phase-5-auto-enriched"
    record["verification"]["unknown_fields"] = unknown
    record["verification"]["warnings"] = warnings
    save_record(record)
    return record


def write_rollups(records: list[dict]) -> None:
    REQ_DIR.mkdir(parents=True, exist_ok=True)
    MAJ_DIR.mkdir(parents=True, exist_ok=True)
    testing = []
    majors = []
    for record in records:
        testing.append(
            {
                "slug": record["slug"],
                "name": record["name"],
                "testing_policy": record["admissions"]["testing_policy"],
                "gpa_policy": record["admissions"]["gpa_policy"],
                "confidence": record["verification"]["confidence"],
                "unknown_fields": record["verification"]["unknown_fields"],
            }
        )
        majors.append(
            {
                "slug": record["slug"],
                "name": record["name"],
                "majors_count": record["majors"]["count"],
                "count_method": record["majors"]["count_method"],
                "confidence": record["majors"]["confidence"],
            }
        )
    (REQ_DIR / "testing_policy_phase5_auto.json").write_text(json.dumps(testing, indent=2))
    (MAJ_DIR / "majors_counts_phase5_auto.json").write_text(json.dumps(majors, indent=2))


def main() -> int:
    paths = sorted(UNI_DIR.glob("*.json"), key=lambda path: json.loads(path.read_text()).get("rank") or 999)
    updated = []
    skipped = []
    for path in paths:
        record = json.loads(path.read_text())
        rank = record.get("rank") or 999
        confidence = str(record.get("verification", {}).get("confidence") or "")
        if rank < 11:
            skipped.append({"slug": record["slug"], "reason": "top-10 already handled"})
            continue
        if confidence != "placeholder":
            skipped.append({"slug": record["slug"], "reason": f"already {confidence}"})
            continue
        pages = crawl_school(record)
        updated_record = update_record(record, pages)
        updated.append(
            {
                "slug": updated_record["slug"],
                "rank": updated_record["rank"],
                "majors_count": updated_record["majors"]["count"],
                "testing_policy": updated_record["admissions"]["testing_policy"],
                "gpa_policy": updated_record["admissions"]["gpa_policy"],
                "unknown_fields": updated_record["verification"]["unknown_fields"],
                "warnings": updated_record["verification"]["warnings"][:3],
            }
        )
    write_rollups([json.loads(path.read_text()) for path in paths if json.loads(path.read_text()).get("rank") and json.loads(path.read_text()).get("rank") >= 11])
    print(json.dumps({"updated_count": len(updated), "updated": updated[:20], "skipped_count": len(skipped)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
