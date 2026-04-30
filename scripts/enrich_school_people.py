#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse, urljoin

try:
    import requests
except ImportError as exc:  # pragma: no cover
    raise SystemExit("This script requires the 'requests' package to be installed.") from exc

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.kb.write_json import write_university_json  # noqa: E402
from src.kb.write_markdown import write_university_markdown  # noqa: E402

UNI_DIR = ROOT / "knowledgebase" / "universities"
PEOPLE_OVERRIDE_DIR = ROOT / "data" / "people_overrides"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIMEDIA_PAGEVIEWS = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia.org/all-access/user/{title}/daily/{start}/{end}"
RMP_GRAPHQL = "https://www.ratemyprofessors.com/graphql"
USER_AGENT = "goal-kicker-school-people/1.0"
WIKI_HOSTS = {"en.wikipedia.org", "wikimedia.org", "www.wikimedia.org"}
WIKI_REQUEST_LOCK = threading.Lock()
WIKI_NEXT_ALLOWED_AT = 0.0
TOP_PROFESSORS = 20
TOP_ALUMNI = 20
RECENT_ALUMNI_WINDOW_YEARS = 10

RMP_SCHOOL_QUERY = """
query SearchSchools($query: SchoolSearchQuery!, $first: Int!, $after: String) {
  newSearch {
    schools(query: $query, first: $first, after: $after) {
      edges {
        node {
          id
          legacyId
          name
          city
          state
          numRatings
        }
      }
    }
  }
}
""".strip()

RMP_TEACHER_QUERY = """
query SearchTeachers($query: TeacherSearchQuery!, $first: Int!, $after: String) {
  newSearch {
    teachers(query: $query, first: $first, after: $after) {
      resultCount
      edges {
        cursor
        node {
          id
          legacyId
          firstName
          lastName
          department
          avgRating
          numRatings
          wouldTakeAgainPercent
          avgDifficulty
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
""".strip()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_name(value: str) -> str:
    value = value.lower()
    value = value.replace("&", " and ")
    value = re.sub(r"\bthe\b", " ", value)
    value = re.sub(r"\buniversity\b", "university", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def request_with_retries(session: requests.Session, method: str, url: str, **kwargs: Any) -> requests.Response:
    backoff = 2.0
    last_response: requests.Response | None = None
    last_error: Exception | None = None
    for attempt in range(6):
        try:
            maybe_throttle_request(url)
            response = session.request(method, url, **kwargs)
        except requests.RequestException as exc:
            last_error = exc
            time.sleep(min(backoff, 30.0))
            backoff *= 2
            continue
        last_response = response
        if response.status_code not in {429, 500, 502, 503, 504}:
            return response
        retry_after = response.headers.get("Retry-After")
        sleep_for = parse_retry_after(retry_after) if retry_after else backoff
        if response.status_code == 429:
            sleep_for = max(sleep_for, 20.0 + (attempt * 10.0))
        time.sleep(min(sleep_for, 120.0))
        backoff *= 2
    if last_response is not None:
        return last_response
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"No response returned for {method} {url}")


def parse_retry_after(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def maybe_throttle_request(url: str) -> None:
    global WIKI_NEXT_ALLOWED_AT
    hostname = (urlparse(url).hostname or "").lower()
    if hostname not in WIKI_HOSTS:
        return
    with WIKI_REQUEST_LOCK:
        now = time.monotonic()
        if now < WIKI_NEXT_ALLOWED_AT:
            time.sleep(WIKI_NEXT_ALLOWED_AT - now)
        WIKI_NEXT_ALLOWED_AT = time.monotonic() + 3.0 + random.uniform(0.4, 1.2)


def graphql_post(session: requests.Session, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    response = request_with_retries(
        session,
        "POST",
        RMP_GRAPHQL,
        json={"query": query, "variables": variables},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(f"GraphQL error: {payload['errors']}")
    return payload


def search_rmp_school(session: requests.Session, record: dict[str, Any]) -> dict[str, Any] | None:
    queries = [record["name"], record.get("short_name", "")]
    candidates: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for query_text in queries:
        query_text = query_text.strip()
        if not query_text:
            continue
        payload = graphql_post(session, RMP_SCHOOL_QUERY, {"query": {"text": query_text}, "first": 10, "after": None})
        edges = payload["data"]["newSearch"]["schools"]["edges"]
        for edge in edges:
            node = edge["node"]
            school_id = node["id"]
            if school_id in seen_ids:
                continue
            seen_ids.add(school_id)
            normalized_target = normalize_name(record["name"])
            normalized_candidate = normalize_name(node["name"])
            score = SequenceMatcher(None, normalized_target, normalized_candidate).ratio()
            exact_bonus = 0.2 if normalized_target == normalized_candidate else 0.0
            short_bonus = 0.1 if normalize_name(record.get("short_name", "")) == normalized_candidate else 0.0
            candidate = dict(node)
            candidate["match_score"] = round(score + exact_bonus + short_bonus, 4)
            candidates.append(candidate)
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item["match_score"], item.get("numRatings", 0)), reverse=True)
    best = candidates[0]
    if best["match_score"] < 0.72:
        return None
    return best


def fetch_all_rmp_teachers(session: requests.Session, school_id: str) -> list[dict[str, Any]]:
    teachers: list[dict[str, Any]] = []
    after: str | None = None
    while True:
        payload = graphql_post(
            session,
            RMP_TEACHER_QUERY,
            {"query": {"text": "", "schoolID": school_id, "fallback": True}, "first": 100, "after": after},
        )
        connection = payload["data"]["newSearch"]["teachers"]
        teachers.extend(edge["node"] for edge in connection["edges"])
        page_info = connection["pageInfo"]
        if not page_info.get("hasNextPage"):
            break
        after = page_info.get("endCursor")
        if not after:
            break
    deduped: dict[int, dict[str, Any]] = {}
    for teacher in teachers:
        legacy_id = teacher.get("legacyId")
        if legacy_id is None:
            continue
        deduped[legacy_id] = teacher
    return list(deduped.values())


def items_need_refresh(items: list[dict[str, Any]], required_keys: set[str]) -> bool:
    if not items:
        return False
    for item in items:
        for key in required_keys:
            if item.get(key) in (None, ""):
                return True
    return False


def alumni_items_need_refresh(items: list[dict[str, Any]]) -> bool:
    if items_need_refresh(items, {"rank", "name", "bio", "confirmation_url"}):
        return True
    for item in items:
        summary = {
            "type": "standard",
            "description": item.get("description") or item.get("bio") or "",
            "titles": {"display": item.get("name") or ""},
        }
        if not looks_like_person(summary, item.get("name") or ""):
            return True
    return False


def build_professor_items(record: dict[str, Any], school_match: dict[str, Any], teachers: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    warnings: list[str] = []
    source_urls = [f"https://www.ratemyprofessors.com/school/{school_match['legacyId']}"]
    ranked = [teacher for teacher in teachers if (teacher.get("numRatings") or 0) > 0]
    ranked.sort(
        key=lambda item: (
            item.get("numRatings") or 0,
            item.get("avgRating") or 0,
            item.get("wouldTakeAgainPercent") or 0,
            -1 * (item.get("avgDifficulty") or 0),
        ),
        reverse=True,
    )
    top_items: list[dict[str, Any]] = []
    for index, teacher in enumerate(ranked[:TOP_PROFESSORS], start=1):
        name = f"{teacher.get('firstName', '').strip()} {teacher.get('lastName', '').strip()}".strip()
        department = teacher.get("department")
        rating_count = teacher.get("numRatings")
        avg_rating = teacher.get("avgRating")
        bio = coalesce_text(
            f"{department} professor listed on RateMyProfessors for {record['name']} with {rating_count} ratings and average rating {avg_rating}." if department and rating_count is not None and avg_rating is not None else None,
            f"Professor in {department} listed on RateMyProfessors for {record['name']}." if department else None,
            f"RateMyProfessors-listed instructor for {record['name']}.",
        )
        profile_url = f"https://www.ratemyprofessors.com/professor/{teacher['legacyId']}"
        top_items.append(
            {
                "rank": index,
                "name": name,
                "department": department,
                "bio": bio,
                "average_rating": avg_rating,
                "rating_count": rating_count,
                "would_take_again_percent": round(teacher.get("wouldTakeAgainPercent"), 1) if teacher.get("wouldTakeAgainPercent") is not None else None,
                "average_difficulty": teacher.get("avgDifficulty"),
                "legacy_id": teacher.get("legacyId"),
                "profile_url": profile_url,
                "official_website": None,
                "confirmation_url": profile_url,
                "confirmation_label": "RateMyProfessors profile",
                "source_url": source_urls[0],
                "source_confidence": "medium",
            }
        )
    if len(top_items) < TOP_PROFESSORS:
        warnings.append(f"Only found {len(top_items)} RateMyProfessors professors with ratings; no generic official faculty-page pipeline is implemented yet.")
    else:
        warnings.append("Professor bios and confirmation links currently come from RateMyProfessors-derived profiles; a school-official faculty-page resolver still needs to be implemented for stronger verification.")
    return top_items, source_urls, warnings


def wiki_get(session: requests.Session, **params: Any) -> dict[str, Any]:
    response = request_with_retries(session, "GET", WIKIPEDIA_API, params={"format": "json", **params}, timeout=60)
    response.raise_for_status()
    return response.json()


def wiki_search_titles(session: requests.Session, query: str, namespaces: str) -> list[str]:
    payload = wiki_get(session, action="query", list="search", srsearch=query, srnamespace=namespaces, srlimit=10)
    return [item["title"] for item in payload.get("query", {}).get("search", [])]


def wiki_fetch_wikitext(session: requests.Session, title: str) -> str:
    payload = wiki_get(session, action="query", prop="revisions", rvprop="content", rvslots="main", titles=title, formatversion=2)
    pages = payload.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        return ""
    revisions = pages[0].get("revisions") or []
    if not revisions:
        return ""
    return revisions[0].get("slots", {}).get("main", {}).get("content", "")


def _slice_named_section(text: str, heading_pattern: str) -> str:
    lines = text.splitlines()
    capture = False
    section_level = None
    collected: list[str] = []
    heading_regex = re.compile(r"^(=+)\s*(.*?)\s*\1\s*$")
    for line in lines:
        match = heading_regex.match(line.strip())
        if match:
            level = len(match.group(1))
            heading = match.group(2).strip().lower()
            if capture and section_level is not None and level <= section_level:
                break
            if re.search(heading_pattern, heading):
                capture = True
                section_level = level
                continue
        if capture:
            collected.append(line)
    return "\n".join(collected)


def extract_titles_from_wikitext(text: str) -> list[str]:
    titles: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("{{", "<!--", "==")):
            continue
        if not stripped.startswith(("*", "|")):
            continue
        matches = re.findall(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]", stripped)
        if not matches:
            continue
        first = matches[0].strip()
        if not first or first.lower().startswith(("list of ", "category:", "help:", "file:")):
            continue
        if first not in seen:
            seen.add(first)
            titles.append(first)
    return titles


def extract_titles_from_source_page(text: str, page_title: str) -> list[str]:
    lowered = page_title.lower()
    if "people" in lowered and "alumni" not in lowered and "graduates" not in lowered:
        alumni_section = _slice_named_section(text, r"notable alumni|alumni|former students|graduates")
        if alumni_section.strip():
            return extract_titles_from_wikitext(alumni_section)
    return extract_titles_from_wikitext(text)


def wiki_category_members(session: requests.Session, category_title: str, limit: int = 200) -> list[str]:
    titles: list[str] = []
    cursor: str | None = None
    while len(titles) < limit:
        params: dict[str, Any] = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category_title,
            "cmlimit": min(500, limit - len(titles)),
            "cmtype": "page",
        }
        if cursor:
            params["cmcontinue"] = cursor
        payload = wiki_get(session, **params)
        titles.extend(item["title"] for item in payload.get("query", {}).get("categorymembers", []))
        cursor = payload.get("continue", {}).get("cmcontinue")
        if not cursor:
            break
    return titles[:limit]


def wiki_summary(session: requests.Session, title: str) -> dict[str, Any] | None:
    response = request_with_retries(
        session,
        "GET",
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title, safe='')}",
        timeout=60,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def coalesce_text(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def absolute_url(base_url: str, href: str | None) -> str | None:
    if not href:
        return None
    return urljoin(base_url, href)


def load_people_override(slug: str) -> dict[str, Any] | None:
    path = PEOPLE_OVERRIDE_DIR / f"{slug}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def apply_people_override(record: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    school_people = record.setdefault("school_people", {})
    source_urls = record.setdefault("source_urls", {})
    source_urls.setdefault("professors", [])
    source_urls.setdefault("alumni", [])
    warnings = school_people.get("warnings", []) or []

    professors = override.get("popular_professors")
    if professors:
        school_people["popular_professors"] = professors
        source_urls["professors"] = sorted(set(source_urls.get("professors", []) + (professors.get("source_urls") or [])))
        warnings.append("Applied school-specific professor override data.")

    alumni = override.get("successful_alumni")
    if alumni:
        school_people["successful_alumni"] = alumni
        source_urls["alumni"] = sorted(set(source_urls.get("alumni", []) + (alumni.get("source_urls") or [])))
        warnings.append("Applied school-specific alumni override data.")

    warnings.extend(override.get("override_warnings", []))
    school_people["warnings"] = list(dict.fromkeys(warnings))
    record["school_people"] = school_people
    return record


NON_PERSON_KEYWORDS = {
    "university",
    "college",
    "school",
    "company",
    "organization",
    "association",
    "city",
    "town",
    "state",
    "county",
    "district",
    "territory",
    "house of representatives",
    "senate",
    "air service",
    "appointee",
    "film",
    "album",
    "song",
    "book",
    "award",
    "conference",
    "campus",
    "building",
    "department",
    "program",
    "list of",
    "museum",
    "magazine",
    "newspaper",
}

PERSON_HINT_KEYWORDS = {
    "actor",
    "actress",
    "artist",
    "athlete",
    "author",
    "businessman",
    "businesswoman",
    "composer",
    "director",
    "economist",
    "engineer",
    "entrepreneur",
    "executive",
    "filmmaker",
    "inventor",
    "journalist",
    "lawyer",
    "mathematician",
    "musician",
    "philanthropist",
    "physicist",
    "politician",
    "producer",
    "professor",
    "scientist",
    "singer",
    "writer",
    "born",
}


def description_has_keyword(description: str, keywords: set[str]) -> bool:
    for keyword in keywords:
        pattern = rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])"
        if re.search(pattern, description):
            return True
    return False


def looks_like_person(summary: dict[str, Any] | None, title: str) -> bool:
    if not summary:
        return False
    if summary.get("type") != "standard":
        return False
    description = (summary.get("description") or summary.get("titles", {}).get("display") or "").lower()
    if not description:
        return False
    if description_has_keyword(description, NON_PERSON_KEYWORDS):
        return False
    if "disambiguation" in description:
        return False
    if re.search(r"\b\d{4}\b", title):
        return False
    if not description_has_keyword(description, PERSON_HINT_KEYWORDS):
        return False
    return True


def fetch_pageviews(session: requests.Session, title: str) -> int:
    end = datetime.now(timezone.utc).date() - timedelta(days=1)
    start = end - timedelta(days=364)
    url = WIKIMEDIA_PAGEVIEWS.format(title=quote(title, safe=""), start=start.strftime("%Y%m%d"), end=end.strftime("%Y%m%d"))
    response = request_with_retries(session, "GET", url, timeout=60)
    if response.status_code == 404:
        return 0
    response.raise_for_status()
    payload = response.json()
    return sum(item.get("views", 0) for item in payload.get("items", []))


def gather_alumni_candidates(session: requests.Session, record: dict[str, Any]) -> tuple[list[str], list[str]]:
    school_name = record["name"]
    short_name = record.get("short_name", "")
    candidate_pages: list[str] = []
    candidate_categories: list[str] = []
    for base_name in [school_name, short_name]:
        if not base_name:
            continue
        page_queries = [
            f'"List of {base_name} alumni"',
            f'"List of {base_name} people"',
            f'"{base_name} alumni"',
            f'"{base_name} people"',
        ]
        for query_text in page_queries:
            for title in wiki_search_titles(session, query_text, "0"):
                lowered = title.lower()
                if base_name.lower() in lowered and any(token in lowered for token in ("alumni", "people", "graduates", "former students")) and "faculty" not in lowered:
                    if title not in candidate_pages:
                        candidate_pages.append(title)
        category_queries = [f'"{base_name} alumni"', f'"{base_name} people"']
        for query_text in category_queries:
            for title in wiki_search_titles(session, query_text, "14"):
                lowered = title.lower()
                if any(token in lowered for token in ("alumni", "graduates", "people")) and "faculty" not in lowered:
                    if title not in candidate_categories:
                        candidate_categories.append(title)
    return candidate_pages[:5], candidate_categories[:5]


def build_alumni_items(session: requests.Session, record: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    warnings: list[str] = []
    source_urls: list[str] = []
    candidate_pages, candidate_categories = gather_alumni_candidates(session, record)
    candidate_titles: list[str] = []
    title_sources: dict[str, str] = {}

    for page_title in candidate_pages:
        text = wiki_fetch_wikitext(session, page_title)
        if not text:
            continue
        source_url = f"https://en.wikipedia.org/wiki/{quote(page_title.replace(' ', '_'))}"
        source_urls.append(source_url)
        for candidate_title in extract_titles_from_source_page(text, page_title):
            if candidate_title == record["name"]:
                continue
            if candidate_title not in title_sources:
                title_sources[candidate_title] = source_url
                candidate_titles.append(candidate_title)
        if len(candidate_titles) >= 120:
            break

    if len(candidate_titles) < 50:
        for category_title in candidate_categories:
            source_url = f"https://en.wikipedia.org/wiki/{quote(category_title.replace(' ', '_'))}"
            source_urls.append(source_url)
            for candidate_title in wiki_category_members(session, category_title, limit=200):
                if candidate_title == record["name"]:
                    continue
                if candidate_title not in title_sources:
                    title_sources[candidate_title] = source_url
                    candidate_titles.append(candidate_title)
            if len(candidate_titles) >= 180:
                break

    unique_candidates = candidate_titles[:180]
    if not unique_candidates:
        warnings.append("No Wikipedia alumni source page or category produced candidates.")
        return [], sorted(set(source_urls)), warnings

    summaries: dict[str, dict[str, Any] | None] = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_title = {executor.submit(wiki_summary, session, title): title for title in unique_candidates}
        for future in as_completed(future_to_title):
            title = future_to_title[future]
            try:
                summaries[title] = future.result()
            except Exception:
                summaries[title] = None

    person_titles = [title for title in unique_candidates if looks_like_person(summaries.get(title), title)]
    if len(person_titles) < TOP_ALUMNI:
        warnings.append(f"Only identified {len(person_titles)} alumni candidates that looked like people.")

    pageviews: dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=1) as executor:
        future_to_title = {executor.submit(fetch_pageviews, session, title): title for title in person_titles[:120]}
        for future in as_completed(future_to_title):
            title = future_to_title[future]
            try:
                pageviews[title] = future.result()
            except Exception:
                pageviews[title] = 0

    ranked_titles = sorted(person_titles[:120], key=lambda title: (pageviews.get(title, 0), title), reverse=True)[:TOP_ALUMNI]
    items: list[dict[str, Any]] = []
    for index, title in enumerate(ranked_titles, start=1):
        summary = summaries.get(title) or {}
        canonical_title = summary.get("title") or title
        wikipedia_url = summary.get("content_urls", {}).get("desktop", {}).get("page") or f"https://en.wikipedia.org/wiki/{quote(canonical_title.replace(' ', '_'))}"
        bio = coalesce_text(summary.get("extract"), summary.get("description"))
        items.append(
            {
                "rank": index,
                "name": canonical_title,
                "bio": bio,
                "description": summary.get("description"),
                "wikipedia_title": canonical_title,
                "wikipedia_url": wikipedia_url,
                "confirmation_url": wikipedia_url,
                "confirmation_label": "Wikipedia biography",
                "official_website": None,
                "recent_pageviews": pageviews.get(title, 0),
                "major": None,
                "graduation_year": None,
                "within_last_10_years": None,
                "source_url": title_sources.get(title),
                "source_confidence": "medium",
            }
        )
    if len(items) < TOP_ALUMNI:
        warnings.append(f"Only ranked {len(items)} successful alumni items.")
    warnings.append(
        f"Recent-{RECENT_ALUMNI_WINDOW_YEARS}-years and per-major alumni filtering is not yet available from the generic Wikipedia pipeline; those fields remain null unless stronger school-specific alumni sources are added."
    )
    return items, sorted(set(source_urls)), warnings


def upsert_evidence(record: dict[str, Any], field: str, claim: str, source_url: str, source_excerpt: str, classification: str = "reported_profile") -> None:
    evidence = [item for item in record.get("evidence", []) if item.get("field") != field]
    evidence.append(
        {
            "field": field,
            "claim": claim,
            "classification": classification,
            "source_url": source_url,
            "source_excerpt": source_excerpt,
            "retrieved_at": now_iso(),
        }
    )
    record["evidence"] = evidence


def enrich_record(record: dict[str, Any]) -> dict[str, Any]:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    override = load_people_override(record["slug"])
    if override:
        record = apply_people_override(record, override)

    school_people: dict[str, Any] = record.get("school_people") or {}
    source_urls = record.setdefault("source_urls", {})
    source_urls.setdefault("professors", [])
    source_urls.setdefault("alumni", [])

    people_warnings: list[str] = school_people.get("warnings", []) or []

    existing_prof_items = school_people.get("popular_professors", {}).get("items") or []
    existing_alumni_items = school_people.get("successful_alumni", {}).get("items") or []
    if items_need_refresh(existing_prof_items, {"rank", "name", "profile_url", "bio", "confirmation_url"}):
        existing_prof_items = []
        people_warnings.append("Refreshed stale professor entries to backfill required bio/confirmation fields.")
    if alumni_items_need_refresh(existing_alumni_items):
        existing_alumni_items = []
        people_warnings.append("Refreshed stale alumni entries to backfill required fields or invalid non-person matches.")

    school_match = search_rmp_school(session, record)
    professor_items: list[dict[str, Any]] = list(existing_prof_items)
    if school_match and not existing_prof_items:
        teachers = fetch_all_rmp_teachers(session, school_match["id"])
        professor_items, professor_urls, professor_warnings = build_professor_items(record, school_match, teachers)
        source_urls["professors"] = professor_urls
        people_warnings.extend(professor_warnings)
        school_people["popular_professors"] = {
            "ranking_basis": "RateMyProfessors entries sorted by rating_count desc, then average_rating desc, then would_take_again_percent desc.",
            "source_summary": f"Matched RateMyProfessors school '{school_match['name']}' (legacyId={school_match['legacyId']}) and ranked up to {TOP_PROFESSORS} professors with at least one rating.",
            "retrieved_at": now_iso(),
            "target_count": TOP_PROFESSORS,
            "items": professor_items,
        }
        upsert_evidence(
            record,
            field="school_people.popular_professors",
            claim=f"Ranked top {len(professor_items)} professors from RateMyProfessors by rating count and sentiment metrics.",
            source_url=professor_urls[0],
            source_excerpt=school_people["popular_professors"]["source_summary"],
        )
    else:
        if not existing_prof_items:
            people_warnings.append("Could not confidently match this school to a RateMyProfessors school record.")
            school_people["popular_professors"] = {
                "ranking_basis": "RateMyProfessors school match required.",
                "source_summary": "No confident school match found on RateMyProfessors.",
                "retrieved_at": now_iso(),
                "items": [],
            }

    alumni_items = list(existing_alumni_items)
    alumni_urls: list[str] = source_urls.get("alumni", [])
    alumni_warnings: list[str] = []
    if not existing_alumni_items:
        alumni_items, alumni_urls, alumni_warnings = build_alumni_items(session, record)
        school_people["successful_alumni"] = {
            "ranking_basis": "Wikipedia list/category candidates ranked by trailing-365-day Wikipedia pageviews.",
            "source_summary": "Candidates were harvested from school-specific Wikipedia alumni/people pages or categories, filtered to likely people, and ranked by pageviews. Major-specific and last-10-years filtering requires stronger school-specific alumni sources than this generic pipeline currently has.",
            "retrieved_at": now_iso(),
            "target_count": TOP_ALUMNI,
            "recent_window_years": RECENT_ALUMNI_WINDOW_YEARS,
            "major_specific": False,
            "items": alumni_items,
        }
    source_urls["alumni"] = alumni_urls
    people_warnings.extend(alumni_warnings)
    if alumni_urls and not existing_alumni_items:
        upsert_evidence(
            record,
            field="school_people.successful_alumni",
            claim=f"Ranked top {len(alumni_items)} notable alumni from Wikipedia-derived candidate lists using trailing pageviews.",
            source_url=alumni_urls[0],
            source_excerpt=school_people["successful_alumni"]["source_summary"],
        )

    school_people["warnings"] = people_warnings
    record["school_people"] = school_people
    verification = record.setdefault("verification", {})
    verification["last_verified_at"] = now_iso()
    existing_verification_warnings = verification.get("warnings", [])
    applied_override = any(
        "Applied school-specific" in warning
        for warning in school_people.get("warnings", [])
    )
    people_source_warning = (
        "School-people enrichment includes school-specific override data sourced from official university domains for populated sections."
        if applied_override
        else "School-people enrichment uses public third-party sources (RateMyProfessors and Wikipedia/Wikimedia), so rankings are heuristic rather than official university data."
    )
    warnings = list(dict.fromkeys(existing_verification_warnings + [people_source_warning]))
    verification["warnings"] = warnings
    return record


def validate_school_people(record: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    school_people = record.get("school_people") or {}
    professors = school_people.get("popular_professors", {}).get("items", [])
    alumni = school_people.get("successful_alumni", {}).get("items", [])
    if len(professors) > TOP_PROFESSORS:
        problems.append(f"popular_professors contains more than {TOP_PROFESSORS} items")
    if len(alumni) > TOP_ALUMNI:
        problems.append(f"successful_alumni contains more than {TOP_ALUMNI} items")
    for label, items, required_keys in [
        ("popular_professors", professors, {"rank", "name", "profile_url", "bio", "confirmation_url"}),
        ("successful_alumni", alumni, {"rank", "name", "bio", "confirmation_url"}),
    ]:
        for index, item in enumerate(items, start=1):
            missing = sorted(key for key in required_keys if item.get(key) in (None, ""))
            if missing:
                problems.append(f"{label}[{index}] missing keys: {', '.join(missing)}")
    return problems


def summarize_bucket_fill_status(record: dict[str, Any]) -> dict[str, Any]:
    alumni_section = record.get("school_people", {}).get("successful_alumni", {})
    major_gap_counts = alumni_section.get("major_gap_counts") or {}
    open_gaps = {major: gap for major, gap in major_gap_counts.items() if gap > 0}
    return {
        "per_major_target_count": alumni_section.get("per_major_target_count"),
        "major_buckets_total": len(alumni_section.get("by_major") or {}),
        "major_buckets_below_target": len(open_gaps),
        "total_bucket_gap": sum(open_gaps.values()),
    }


def process_record_path(path: Path) -> dict[str, Any]:
    original = json.loads(path.read_text())
    try:
        enriched = enrich_record(original)
        json_path = write_university_json(enriched)
        md_path = write_university_markdown(enriched)
        validation_problems = validate_school_people(enriched)
        result = {
            "slug": enriched.get("slug"),
            "name": enriched.get("name"),
            "json": str(json_path),
            "markdown": str(md_path),
            "popular_professors": len(enriched.get("school_people", {}).get("popular_professors", {}).get("items", [])),
            "successful_alumni": len(enriched.get("school_people", {}).get("successful_alumni", {}).get("items", [])),
            "validation_problems": validation_problems,
            "school_people_warnings": enriched.get("school_people", {}).get("warnings", []),
        }
        result.update(summarize_bucket_fill_status(enriched))
        return result
    except Exception as exc:
        result = {
            "slug": original.get("slug"),
            "name": original.get("name"),
            "popular_professors": len(original.get("school_people", {}).get("popular_professors", {}).get("items", [])),
            "successful_alumni": len(original.get("school_people", {}).get("successful_alumni", {}).get("items", [])),
            "validation_problems": [f"enrichment_error: {exc}"],
            "school_people_warnings": [],
        }
        result.update(summarize_bucket_fill_status(original))
        return result


def load_records(selected_schools: list[str] | None) -> list[Path]:
    paths = sorted(UNI_DIR.glob("*.json"))
    if not selected_schools:
        return paths
    wanted = {value.strip().lower() for value in selected_schools}
    result: list[Path] = []
    for path in paths:
        record = json.loads(path.read_text())
        if record.get("slug", "").lower() in wanted or record.get("name", "").lower() in wanted or record.get("short_name", "").lower() in wanted:
            result.append(path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich university records with top professors and successful alumni from public sources.")
    parser.add_argument("--school", action="append", dest="schools", help="School slug, short name, or full name. Repeatable.")
    parser.add_argument("--limit", type=int, default=None, help="Optional max number of matching records to process.")
    parser.add_argument(
        "--max-workers",
        type=int,
        default=10,
        help="Maximum number of universities to process concurrently. Values above 10 are capped at 10.",
    )
    args = parser.parse_args()

    paths = load_records(args.schools)
    if args.limit is not None:
        paths = paths[: args.limit]
    if not paths:
        raise SystemExit("No matching university records found.")

    worker_count = max(1, min(args.max_workers, 10, len(paths)))
    results_by_index: dict[int, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_to_index = {executor.submit(process_record_path, path): index for index, path in enumerate(paths)}
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            results_by_index[index] = future.result()
            time.sleep(0.1)

    results = [results_by_index[index] for index in sorted(results_by_index)]
    print(json.dumps({"processed": len(results), "max_workers": worker_count, "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
