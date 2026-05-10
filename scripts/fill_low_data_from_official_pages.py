#!/usr/bin/env /usr/bin/python3
from __future__ import annotations

import json
import re
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
UNI_DIR = ROOT / "knowledgebase" / "universities"
HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 30
MAX_PAGES = 10
KEY_TERMS = (
    "apply",
    "application",
    "check",
    "checklist",
    "requirements",
    "testing",
    "test",
    "essay",
    "writing",
    "supplement",
    "recommend",
    "teacher",
    "counselor",
    "curriculum",
    "course",
    "academic",
    "first-year",
    "freshman",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def strip_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def same_school_domain(netloc: str, official_domain: str) -> bool:
    host = netloc.lower()
    domain = official_domain.lower()
    return host == domain or host.endswith("." + domain)


def load_record(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def save_record(record: dict[str, Any]) -> None:
    (UNI_DIR / f"{record['slug']}.json").write_text(json.dumps(record, indent=2))


def upsert_evidence(record: dict[str, Any], field: str, claim: str, classification: str, source_url: str, excerpt: str) -> None:
    evidence = [item for item in record.get("evidence", []) if item.get("field") and item.get("source_url")]
    key = (field, claim, source_url)
    evidence = [item for item in evidence if (item.get("field"), item.get("claim"), item.get("source_url")) != key]
    evidence.append(
        {
            "field": field,
            "claim": claim,
            "classification": classification,
            "source_url": source_url,
            "source_excerpt": excerpt,
            "retrieved_at": now_iso(),
        }
    )
    record["evidence"] = evidence


def recompute_unknowns(record: dict[str, Any]) -> None:
    unknown = []
    for field, value in [
        ("majors.count", record.get("majors", {}).get("count")),
        ("admissions.testing_policy", record.get("admissions", {}).get("testing_policy")),
        ("admissions.gpa_policy", record.get("admissions", {}).get("gpa_policy")),
        ("admissions.course_rigor", record.get("admissions", {}).get("course_rigor")),
        ("admissions.recommendations", record.get("admissions", {}).get("recommendations")),
        ("admissions.essays", record.get("admissions", {}).get("essays")),
    ]:
        if value in (None, "", "unknown"):
            unknown.append(field)
    if not record.get("competitive_signals", {}).get("projects_research"):
        unknown.append("competitive_signals.projects_research")
    record.setdefault("verification", {})["unknown_fields"] = unknown


def add_warning(record: dict[str, Any], warning: str) -> None:
    warnings = [w for w in record.get("verification", {}).get("warnings", []) if w != warning]
    warnings.append(warning)
    record.setdefault("verification", {})["warnings"] = warnings


def remove_warning_contains(record: dict[str, Any], text: str) -> None:
    record.setdefault("verification", {})["warnings"] = [
        w for w in record.get("verification", {}).get("warnings", []) if text.lower() not in w.lower()
    ]


def fetch_markdown(url: str) -> str:
    wrapped = f"https://r.jina.ai/http://{url}" if not url.startswith("https://r.jina.ai/") else url
    r = requests.get(wrapped, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text or ""


def candidate_urls(record: dict[str, Any]) -> list[str]:
    domain = record["official_domain"]
    urls: list[str] = []
    urls.extend(record.get("source_urls", {}).get("admissions", []))
    urls.extend(
        [
            f"https://www.{domain}/admission",
            f"https://www.{domain}/admissions",
            f"https://www.{domain}/apply",
            f"https://admissions.{domain}/",
            f"https://admission.{domain}/",
            f"https://apply.{domain}/",
        ]
    )
    out = []
    seen = set()
    for url in urls:
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(url)
    return out


def extract_links(markdown: str, official_domain: str) -> list[str]:
    scored = []
    seen = set()
    for text, href in re.findall(r"\[([^\]]+)\]\((https?://[^)]+)\)", markdown):
        parsed = urlparse(href)
        if not same_school_domain(parsed.netloc, official_domain):
            continue
        blob = f"{text} {href}".lower()
        if not any(term in blob for term in KEY_TERMS):
            continue
        if href in seen:
            continue
        seen.add(href)
        score = 0
        for term in ("testing", "test", "checklist", "requirement", "recommend", "essay", "counselor", "teacher", "apply", "application", "first-year", "freshman"):
            if term in blob:
                score += 2
        if "academics" in blob or "areas-study" in blob:
            score -= 1
        scored.append((score, href))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [href for _, href in scored[:20]]


def markdown_lines(markdown: str) -> list[str]:
    lines = []
    for raw in markdown.splitlines():
        line = strip_text(raw)
        if not line:
            continue
        if line.startswith("Title:") or line.startswith("URL Source:") or line.startswith("Markdown Content:"):
            continue
        lines.append(line)
    return lines


def choose_line(lines: list[str], include_terms: list[str], exclude_terms: list[str] | None = None) -> str | None:
    exclude_terms = exclude_terms or []
    candidates = []
    for line in lines:
        lower = line.lower()
        if len(line) < 25 or len(line) > 420:
            continue
        if any(term in lower for term in exclude_terms):
            continue
        if all(term in lower for term in include_terms):
            candidates.append(line)
    if not candidates:
        return None
    candidates.sort(key=lambda s: (len(s), s))
    return candidates[0]


def choose_any(lines: list[str], include_terms: list[str], exclude_terms: list[str] | None = None) -> str | None:
    exclude_terms = exclude_terms or []
    candidates = []
    for line in lines:
        lower = line.lower()
        if len(line) < 25 or len(line) > 420:
            continue
        if any(term in lower for term in exclude_terms):
            continue
        if any(term in lower for term in include_terms):
            candidates.append(line)
    if not candidates:
        return None
    candidates.sort(key=lambda s: (len(s), s))
    return candidates[0]


def page_blob(page: dict[str, Any]) -> str:
    return f"{page['url']} {' '.join(page['lines'][:80])}".lower()


def is_valid_testing(line: str) -> bool:
    lower = line.lower()
    if any(term in lower for term in [
        "college of fine arts",
        "portfolio",
        "audition",
        "english proficiency",
        "international students may",
        "some schools require test scores while others are test-optional or test-blind",
        "if you're planning to submit scores",
        "if you’re planning to submit scores",
    ]):
        return False
    return any(term in lower for term in ["sat", "act", "test-optional", "test optional", "standardized testing", "testing requirement"]) and any(
        term in lower for term in ["required", "optional", "submit", "considered", "superscored"]
    )


def is_valid_recommendations(line: str) -> bool:
    lower = line.lower()
    return any(term in lower for term in ["teacher recommendation", "teacher recommendations", "teacher evaluations", "counselor evaluation", "secondary school report", "letters of recommendation"]) and not any(
        term in lower for term in ["additional letter", "deferred applicants", "may wish to submit"]
    )


def is_valid_essays(line: str) -> bool:
    lower = line.lower()
    return any(term in lower for term in ["essay", "essays", "personal statement", "writing supplement", "supplemental question"]) and not any(
        term in lower for term in ["extended essay", "contact the office", "special academic program", "video essay"]
    )


def is_valid_rigor(line: str) -> bool:
    lower = line.lower()
    return any(term in lower for term in ["rigor", "rigorous", "college preparatory", "most challenging", "academic preparation", "challenging courses", "coursework available to you"]) and not any(
        term in lower for term in ["film and media", "professor", "research asks", "contact the office"]
    )


def crawl(record: dict[str, Any]) -> list[dict[str, Any]]:
    queue = deque(candidate_urls(record))
    seen = set()
    pages = []
    while queue and len(pages) < MAX_PAGES:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        try:
            md = fetch_markdown(url)
        except Exception:
            continue
        pages.append({"url": url, "markdown": md, "lines": markdown_lines(md)})
        for href in extract_links(md, record["official_domain"]):
            if href not in seen:
                queue.append(href)
        time.sleep(0.1)
    return pages


def find_testing(pages: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    for page in pages:
        if not any(term in page_blob(page) for term in ["test", "sat", "act", "standardized"]):
            continue
        lines = page["lines"]
        line = choose_any(lines, ["test-optional", "test optional", "standardized testing is a required", "must submit results of either the sat or act", "sat or act scores", "not considered for admission"], ["english proficiency", "international students"])
        if line and is_valid_testing(line):
            return line, page["url"]
    return None, None


def find_recommendations(pages: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    for page in pages:
        if not any(term in page_blob(page) for term in ["recommend", "teacher", "counselor", "secondary school report"]):
            continue
        lines = page["lines"]
        line = choose_any(lines, ["teacher recommendation", "teacher recommendations", "teacher evaluations", "counselor evaluation", "secondary school report", "letters of recommendation"], ["deferred", "additional letter"])
        if line and is_valid_recommendations(line):
            return line, page["url"]
    return None, None


def find_essays(pages: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    for page in pages:
        if not any(term in page_blob(page) for term in ["essay", "writing supplement", "personal statement", "questions"]):
            continue
        lines = page["lines"]
        line = choose_any(lines, ["essay", "essays", "personal statement", "writing supplement", "questions"], ["extended essay", "theory of knowledge", "essay prompts may change", "video essay"])
        if line and is_valid_essays(line):
            return line, page["url"]
    return None, None


def find_rigor(pages: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    for page in pages:
        if not any(term in page_blob(page) for term in ["rigor", "rigorous", "challenging", "coursework", "academic preparation", "college preparatory"]):
            continue
        lines = page["lines"]
        line = choose_any(lines, ["rigor", "rigorous", "college preparatory", "most challenging", "academic preparation", "secondary school report and recommendations helps us better understand your academic preparation", "coursework"], ["financial aid", "english proficiency"])
        if line and is_valid_rigor(line):
            return line, page["url"]
    return None, None


def normalize_claim(text: str) -> str:
    return strip_text(text).strip("-• ")


def maybe_apply(record: dict[str, Any], pages: list[dict[str, Any]]) -> dict[str, Any]:
    changed = []
    admissions = record.setdefault("admissions", {})
    source_urls = record.setdefault("source_urls", {})
    source_urls.setdefault("admissions", [])

    testing, testing_url = find_testing(pages)
    if testing and (admissions.get("testing_policy") == "unknown" or "could not be confidently extracted" in str(admissions.get("testing_policy", "")).lower()):
        admissions["testing_policy"] = normalize_claim(testing)
        upsert_evidence(record, "admissions.testing_policy", admissions["testing_policy"], "official_requirement", testing_url, testing)
        if testing_url and testing_url not in source_urls["admissions"]:
            source_urls["admissions"].append(testing_url)
        changed.append("testing_policy")

    recs, recs_url = find_recommendations(pages)
    if recs and admissions.get("recommendations") == "unknown":
        admissions["recommendations"] = normalize_claim(recs)
        upsert_evidence(record, "admissions.recommendations", admissions["recommendations"], "official_requirement", recs_url, recs)
        if recs_url and recs_url not in source_urls["admissions"]:
            source_urls["admissions"].append(recs_url)
        changed.append("recommendations")

    essays, essays_url = find_essays(pages)
    if essays and admissions.get("essays") == "unknown":
        admissions["essays"] = normalize_claim(essays)
        upsert_evidence(record, "admissions.essays", admissions["essays"], "official_requirement", essays_url, essays)
        if essays_url and essays_url not in source_urls["admissions"]:
            source_urls["admissions"].append(essays_url)
        changed.append("essays")

    rigor, rigor_url = find_rigor(pages)
    if rigor and admissions.get("course_rigor") == "unknown":
        admissions["course_rigor"] = normalize_claim(rigor)
        upsert_evidence(record, "admissions.course_rigor", admissions["course_rigor"], "official_requirement", rigor_url, rigor)
        if rigor_url and rigor_url not in source_urls["admissions"]:
            source_urls["admissions"].append(rigor_url)
        changed.append("course_rigor")

    if changed:
        source_urls["admissions"] = sorted(set(source_urls["admissions"]))
        remove_warning_contains(record, "testing policy needs manual confirmation")
        add_warning(record, f"Official-page repair filled {', '.join(changed)} from cited school admissions pages.")
        record.setdefault("verification", {})["confidence"] = "phase-6-official-page-repair"
        record["verification"]["last_verified_at"] = now_iso()
        recompute_unknowns(record)
        save_record(record)
    return {"slug": record["slug"], "changed": changed, "pages": [p['url'] for p in pages]}


def main() -> int:
    results = []
    for path in sorted(UNI_DIR.glob("*.json"), key=lambda p: load_record(p).get("rank") or 999):
        record = load_record(path)
        unknowns = set(record.get("verification", {}).get("unknown_fields", []))
        if not unknowns.intersection({"admissions.testing_policy", "admissions.course_rigor", "admissions.recommendations", "admissions.essays"}):
            continue
        pages = crawl(record)
        results.append(maybe_apply(record, pages))
    changed = [r for r in results if r["changed"]]
    print(json.dumps({"processed": len(results), "changed": len(changed), "results": results[:80]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
