#!/usr/bin/env /usr/bin/python3
from __future__ import annotations

import json
import re
import time
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, unquote, urljoin, urlparse, urlsplit

import requests
from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parents[1]
UNI_DIR = ROOT / "knowledgebase" / "universities"
ROLLUP_PATH = ROOT / "knowledgebase" / "majors" / "majors_titles_phase6.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 25
MAX_PAGES = 6
MAX_LINKS_PER_PAGE = 16
MIN_TITLES_TO_ACCEPT = 6
DISCOVERY_TERMS = (
    "major",
    "majors",
    "program",
    "programs",
    "degree-program",
    "academic-program",
    "areas-of-study",
    "fields-of-study",
    "concentration",
    "concentrations",
    "undergraduate-programs",
    "study",
    "catalog",
    "bulletin",
)
BLOCK_TERMS = (
    "attention required",
    "enable cookies",
    "access denied",
    "captcha",
)
BAD_DISCOVERY_LINK_TERMS = (
    "study abroad",
    "family program",
    "family resource",
    "orientation",
    "graduate program",
    "visitor and exchange",
    "global education",
    "international program",
)

SPECIAL_MAJOR_URL_HINTS = {
    "brown": ["https://www.brown.edu/undergraduate-programs"],
    "binghamton": ["https://www.binghamton.edu/academics/programs/"],
    "boston-university": ["https://www.bu.edu/academics/degree-programs/"],
    "mit": ["https://catalog.mit.edu/degree-charts/"],
    "carnegie-mellon": ["https://www.cmu.edu/admission/majors-programs"],
    "case-western": ["https://case.edu/programs/"],
    "fordham": ["https://www.fordham.edu/academics/programs-and-degrees/undergraduate-programs/"],
    "georgetown": ["https://www.georgetown.edu/undergraduate-admissions/academics/"],
    "stanford": [
        "https://majors.stanford.edu/majors/text-only-lists-majors-and-offerings",
        "https://majors.stanford.edu/majors",
    ],
    "duke": ["https://admissions.duke.edu/academic-possibilities/"],
    "rutgers-new-brunswick": ["https://www.rutgers.edu/academics/explore-undergraduate-programs?field_location=654"],
}

BAD_TITLE_EXACT = {
    "overview",
    "undergraduate",
    "graduate",
    "degrees",
    "programs",
    "program",
    "majors",
    "academics",
    "site navigation",
    "main navigation",
    "user account menu",
    "clear",
    "visit program page",
    "undergraduate major",
    "undergraduate majors",
    "undergraduate programs",
    "academic programs",
    "degree programs",
    "academic pillars",
    "academic opportunities",
    "alphabetic listing",
    "in this section",
    "return to top",
    "back to top",
}
BAD_TITLE_SUBSTRINGS = (
    "skip to",
    "admission",
    "apply",
    "contact",
    "tuition",
    "financial aid",
    "request information",
    "learn more",
    "student life",
    "campus life",
    "news",
    "events",
    "athletics",
    "alumni",
    "giving",
    "faq",
    "search",
    "menu",
    "check your status",
    "career center",
    "libraries",
    "research",
)
BAD_LEVEL_TERMS = (
    "minor",
    "certificate",
    "master",
    "doctor",
    "doctoral",
    "phd",
    " m.s",
    " ms",
    " m.a",
    " ma",
    "llm",
    "jd",
    "md",
    "dmd",
    "dma",
    "edd",
    "associate",
    "postbaccalaureate",
    "post-bac",
)
DEGREE_CODE_RE = re.compile(
    r"\b(BA|BS|BFA|BSE|BArch|BM|BMus|BBA|BSA|BAS|BSBA|BSN|BSc|BFS|BPhil|SB|AB|ScB|BE|BEng|BASc)\b",
    re.I,
)
UNDERGRAD_HREF_RE = re.compile(
    r"(/program/ug/|/undergraduate-programs/|/majors?/|/areas-of-study/|/fields-of-study/|/degree-charts/|/programs?/|/degrees?/bachelors/|/ugrd/programs/|/undergraduate/)",
    re.I,
)
UNDERGRAD_TEXT_RE = re.compile(r"\b(undergraduate|bachelor|baccalaureate|major|concentration)\b", re.I)
GENERIC_LINK_TEXT_RE = re.compile(r"^(undergraduate|graduate|details|learn more|read more|visit program page|apply|bs|ba|sb|bfa|bse)$", re.I)
HEADING_TAGS = ("h1", "h2", "h3", "h4")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def strip_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def same_school_domain(netloc: str, official_domain: str) -> bool:
    host = netloc.lower()
    domain = official_domain.lower()
    return host == domain or host.endswith(f".{domain}")


def normalize_title(value: str) -> str:
    title = strip_text(value.replace("\xa0", " "))
    title = title.strip("|•· ")
    title = re.sub(r"\s+", " ", title)
    title = re.sub(r"\s+[–—-]\s+(BA|BS|BFA|BSE|BArch|BM|BMus|BBA|BSA|BAS|BSBA|BSN|BSc|BFS|BPhil|SB|AB|ScB|BE|BEng|BASc)\b.*$", "", title, flags=re.I)
    title = re.sub(r"\((BA|BS|BFA|BSE|BArch|BM|BMus|BBA|BSA|BAS|BSBA|BSN|BSc|BFS|BPhil|SB|AB|ScB|BE|BEng|BASc)[^)]*\)$", "", title, flags=re.I)
    title = re.sub(r"\s*\[[^\]]+\]$", "", title)
    title = re.sub(r"\*+$", "", title).strip()
    title = title.strip(" -–—,;:/")
    title = title.replace("/Second Major", "")
    title = title.replace(" as Recommended by the Department of ", " - ")
    title = title.replace("  ", " ")
    return title


def is_good_title(title: str) -> bool:
    lowered = title.lower().strip()
    if not lowered or lowered in BAD_TITLE_EXACT:
        return False
    if len(title) < 4 or len(title) > 110:
        return False
    if sum(char.isalpha() for char in title) < 4:
        return False
    if len(title.split()) > 12:
        return False
    if title.startswith("College of ") or title.startswith("School of ") or title.startswith("Department of "):
        return False
    if any(term in lowered for term in BAD_TITLE_SUBSTRINGS):
        return False
    if any(term in lowered for term in BAD_LEVEL_TERMS):
        return False
    if re.fullmatch(r"[A-Z]{1,5}|[A-Za-z]{1,3}", title):
        return False
    return True


def dedupe_keep_order(values: Iterable[str]) -> list[str]:
    out = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def unwrap_duckduckgo_url(url: str) -> str:
    if "duckduckgo.com/l/?" not in url:
        return url
    parsed = urlsplit(url)
    q = parse_qs(parsed.query)
    uddg = q.get("uddg")
    if not uddg:
        return url
    return unquote(uddg[0])


def discover_major_search_urls(record: dict) -> list[str]:
    queries = [
        f'site:{record["official_domain"]} undergraduate majors',
        f'site:{record["official_domain"]} majors programs',
        f'site:{record["official_domain"]} areas of study undergraduate',
    ]
    found: list[str] = []
    session = requests.Session()
    for query in queries:
        try:
            response = session.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers=HEADERS,
                timeout=TIMEOUT,
            )
        except Exception:
            continue
        soup = BeautifulSoup(response.text or "", "lxml")
        for anchor in soup.select("a.result__a"):
            href = unwrap_duckduckgo_url(anchor.get("href") or "")
            if not href:
                continue
            parsed = urlparse(href)
            if not parsed.scheme.startswith("http"):
                continue
            if not same_school_domain(parsed.netloc, record["official_domain"]):
                continue
            blob = f"{strip_text(anchor.get_text(' ', strip=True))} {href}".lower()
            if any(term in blob for term in DISCOVERY_TERMS):
                found.append(href)
        if found:
            break
        time.sleep(0.3)
    return dedupe_keep_order(found)[:5]


def candidate_urls(record: dict) -> list[str]:
    urls: list[str] = []
    urls.extend(SPECIAL_MAJOR_URL_HINTS.get(record["slug"], []))
    for group in ("majors", "general", "admissions"):
        urls.extend(record.get("source_urls", {}).get(group, []))
    urls.extend(
        [
            f"https://www.{record['official_domain']}/academics",
            f"https://www.{record['official_domain']}/academics/programs",
            f"https://www.{record['official_domain']}/programs",
            f"https://www.{record['official_domain']}/academic-programs",
            f"https://www.{record['official_domain']}/majors",
        ]
    )
    urls.extend(discover_major_search_urls(record))
    return dedupe_keep_order(url for url in urls if url)


def fetch_page(session: requests.Session, url: str) -> dict | None:
    try:
        response = session.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except Exception:
        return None
    if response.status_code >= 400:
        return None
    content_type = response.headers.get("content-type", "")
    if "html" not in content_type:
        return None
    text = response.text or ""
    lowered = text.lower()
    if any(term in lowered for term in BLOCK_TERMS):
        return None
    soup = BeautifulSoup(text, "lxml")
    return {
        "requested_url": url,
        "url": response.url,
        "status_code": response.status_code,
        "title": strip_text(soup.title.get_text(" ", strip=True) if soup.title else ""),
        "soup": soup,
    }


def relevant_links(page: dict, official_domain: str) -> list[str]:
    found: list[str] = []
    for anchor in page["soup"].find_all("a", href=True):
        href = urljoin(page["url"], anchor["href"])
        parsed = urlparse(href)
        if not parsed.scheme.startswith("http"):
            continue
        if parsed.fragment:
            href = parsed._replace(fragment="").geturl()
            parsed = urlparse(href)
        if not same_school_domain(parsed.netloc, official_domain):
            continue
        blob = f"{strip_text(anchor.get_text(' ', strip=True))} {href}".lower()
        if any(term in blob for term in BAD_DISCOVERY_LINK_TERMS):
            continue
        if any(term in blob for term in DISCOVERY_TERMS):
            found.append(href)
    return dedupe_keep_order(found)[:MAX_LINKS_PER_PAGE]


def crawl_school(record: dict) -> list[dict]:
    session = requests.Session()
    queue = deque(candidate_urls(record))
    pages: list[dict] = []
    seen = set()
    while queue and len(pages) < MAX_PAGES:
        url = queue.popleft()
        parsed = urlparse(url)
        if parsed.fragment:
            url = parsed._replace(fragment="").geturl()
        if url in seen:
            continue
        seen.add(url)
        page = fetch_page(session, url)
        if not page:
            continue
        final_url = urlparse(page["url"])._replace(fragment="").geturl()
        if final_url != page["url"]:
            page = dict(page)
            page["url"] = final_url
        if not same_school_domain(urlparse(page["url"]).netloc, record["official_domain"]):
            continue
        pages.append(page)
        discovered_links = relevant_links(page, record["official_domain"])
        for href in reversed(discovered_links):
            if href not in seen:
                queue.appendleft(href)
        time.sleep(0.2)
    return pages


def nearest_heading(tag: Tag) -> str | None:
    current: Tag | None = tag
    while current and getattr(current, "name", None) not in (None, "body"):
        sibling = current.previous_sibling
        while sibling:
            if isinstance(sibling, Tag):
                if sibling.name in HEADING_TAGS:
                    text = normalize_title(sibling.get_text(" ", strip=True))
                    if is_good_title(text):
                        return text
                for heading in reversed(sibling.find_all(HEADING_TAGS)):
                    text = normalize_title(heading.get_text(" ", strip=True))
                    if is_good_title(text):
                        return text
            sibling = sibling.previous_sibling
        for heading in current.find_all(HEADING_TAGS, recursive=False):
            text = normalize_title(heading.get_text(" ", strip=True))
            if is_good_title(text):
                return text
        current = current.parent if isinstance(current.parent, Tag) else None
    return None


def add_candidate(candidates: list[str], raw: str | None) -> None:
    if not raw:
        return
    title = normalize_title(raw)
    if is_good_title(title):
        candidates.append(title)


def add_delimited_text_candidates(candidates: list[str], raw: str | None) -> None:
    if not raw:
        return
    for part in re.split(r"[\n\r]+", raw):
        text = strip_text(part)
        if not text:
            continue
        text = re.sub(r"^[\-•·]+\s*", "", text)
        if not text or text.startswith("*"):
            continue
        add_candidate(candidates, text)


def is_rutgers_new_brunswick_text(text: str) -> bool:
    normalized = strip_text(text).lower()
    return re.search(r"rutgers[-\s]+new\s+brunswick", normalized) is not None


def extract_titles_from_page(page: dict, record: dict) -> list[str]:
    soup = page["soup"]
    main = soup.find("main") or soup
    candidates: list[str] = []
    page_blob = f"{page['title']} {page['url']}".lower()

    if record["slug"] == "rutgers-new-brunswick":
        rutgers_titles: list[str] = []
        for row in main.select("li.views-row, li.accordion-list-item"):
            campus_cell = row.select_one("tr.program_implementation td")
            if campus_cell and not is_rutgers_new_brunswick_text(campus_cell.get_text(" ", strip=True)):
                continue
            accordion_title = row.select_one("button.accordion-trigger h3")
            if accordion_title:
                title = normalize_title(accordion_title.get_text(" ", strip=True))
                if is_good_title(title):
                    rutgers_titles.append(title)
        if rutgers_titles:
            return dedupe_keep_order(rutgers_titles)

    for item in main.select(".item, .card, .program, .program-card, .program-item, .major-item, .tile, .result, .link-container"):
        title_node = item.select_one(".title, .text--title .title")
        type_node = item.select_one(".type, .text--title .type")
        type_text = strip_text(type_node.get_text(" ", strip=True) if type_node else "")
        if title_node and type_text:
            lowered_type = type_text.lower()
            if "major" in lowered_type or "bachelor" in lowered_type or "undergraduate" in lowered_type:
                if not any(term in lowered_type for term in BAD_LEVEL_TERMS if term.strip()):
                    add_candidate(candidates, title_node.get_text(" ", strip=True))

        if record["slug"] == "rutgers-new-brunswick":
            campus_cell = item.select_one("tr.program_implementation td")
            if campus_cell and not is_rutgers_new_brunswick_text(campus_cell.get_text(" ", strip=True)):
                continue
            accordion_title = item.select_one("button.accordion-trigger h3")
            if accordion_title:
                add_candidate(candidates, accordion_title.get_text(" ", strip=True))

        has_undergrad_signal = bool(item.select_one('a[href*="/program/ug/"]'))
        if not has_undergrad_signal:
            has_undergrad_signal = UNDERGRAD_TEXT_RE.search(item.get_text(" ", strip=True)) is not None and (
                UNDERGRAD_HREF_RE.search(str(item)) is not None or item.find("a", string=re.compile(r"^Major$", re.I)) is not None
            )
        if has_undergrad_signal:
            heading = item.find(HEADING_TAGS)
            if heading:
                add_candidate(candidates, heading.get_text(" ", strip=True))

    for container in main.find_all(["div", "article", "section"]):
        heading = container.find(HEADING_TAGS)
        if not heading:
            continue
        if container.find("a", string=re.compile(r"^(Major|Undergraduate|Bachelor)\b", re.I)):
            add_candidate(candidates, heading.get_text(" ", strip=True))

    if record["slug"] == "duke":
        for heading in main.find_all(HEADING_TAGS):
            if normalize_title(heading.get_text(" ", strip=True)).lower() != "majors":
                continue
            sibling = heading.find_next_sibling()
            while sibling and isinstance(sibling, Tag):
                sibling_name = getattr(sibling, "name", "")
                sibling_text = normalize_title(sibling.get_text(" ", strip=True)) if sibling_name in HEADING_TAGS else ""
                if sibling_name in HEADING_TAGS and sibling_text and sibling_text.lower() != "majors":
                    break
                if sibling_name == "div":
                    add_delimited_text_candidates(candidates, sibling.get_text("\n", strip=True))
                sibling = sibling.find_next_sibling()

    if record["slug"] == "stanford":
        for anchor in main.find_all("a", href=True):
            href = urljoin(page["url"], anchor["href"])
            parsed = urlparse(href)
            if not same_school_domain(parsed.netloc, record["official_domain"]):
                continue
            if "/opportunities/" not in parsed.path:
                continue
            add_candidate(candidates, anchor.get_text(" ", strip=True))

    for li in main.find_all("li"):
        classes = " ".join(li.get("class", [])).lower()
        text = strip_text(li.get_text(" ", strip=True))
        if not text:
            continue
        if record["slug"] == "rutgers-new-brunswick":
            campus_cell = li.select_one("tr.program_implementation td")
            if campus_cell:
                if not is_rutgers_new_brunswick_text(campus_cell.get_text(" ", strip=True)):
                    continue
                accordion_title = li.select_one("button.accordion-trigger h3")
                if accordion_title:
                    add_candidate(candidates, accordion_title.get_text(" ", strip=True))
                    continue
        if any(token in classes for token in ("mj", "major", "bachelors", "undergraduate")):
            add_candidate(candidates, re.split(r"\(", text, 1)[0])
            continue
        if DEGREE_CODE_RE.search(text) and len(text) < 120:
            add_candidate(candidates, re.split(r"\(", text, 1)[0])

    for anchor in main.find_all("a", href=True):
        href = urljoin(page["url"], anchor["href"])
        if not same_school_domain(urlparse(href).netloc, record["official_domain"]):
            continue
        if record["slug"] == "rutgers-new-brunswick":
            row = anchor.find_parent("li")
            if row is not None:
                campus_cell = row.select_one("tr.program_implementation td")
                if campus_cell and not is_rutgers_new_brunswick_text(campus_cell.get_text(" ", strip=True)):
                    continue
        anchor_text = strip_text(anchor.get_text(" ", strip=True))
        anchor_blob = f"{anchor_text} {href} {' '.join(anchor.get('class', []))}".lower()
        anchor_text_generic = not anchor_text or GENERIC_LINK_TEXT_RE.fullmatch(anchor_text) is not None
        bachelor_href = "/bachelors/" in href.lower() or "/undergraduate/" in href.lower()
        filtered_out_degree = any(term in anchor_blob for term in ("minor", "master", "ph.d", "phd", "doctor", "certificate"))
        undergradish = (
            (UNDERGRAD_HREF_RE.search(href) is not None or UNDERGRAD_TEXT_RE.search(anchor_blob) is not None)
            and not filtered_out_degree
        ) or bachelor_href
        if not undergradish and not ("major" in page_blob and href.startswith(page["url"].rstrip("/") + "/")):
            continue
        if not anchor_text_generic:
            add_candidate(candidates, anchor_text)
        else:
            heading = nearest_heading(anchor)
            if heading:
                add_candidate(candidates, heading)

    if record["slug"] == "mit":
        for anchor in main.find_all("a", href=True):
            href = urljoin(page["url"], anchor["href"])
            text = strip_text(anchor.get_text(" ", strip=True))
            if "/degree-charts/" not in href:
                continue
            if "(phd" in text.lower() or "(sm" in text.lower() or "(meng" in text.lower() or "(masc" in text.lower() or "(march" in text.lower():
                continue
            if "(sb" not in text.lower() and "course" not in text.lower():
                continue
            add_candidate(candidates, re.split(r"\(", text, 1)[0])

    if "undergraduate-programs" in page["url"] and record["slug"] == "brown":
        for heading in main.find_all("h3"):
            add_candidate(candidates, heading.get_text(" ", strip=True))

    cleaned = []
    blocked_exact_titles = {
        "Brown University",
        "The College",
        "Schools and Colleges",
        "Find your way around Brown",
        record.get("name", ""),
        record.get("short_name", ""),
    }
    blocked_exact_titles = {title for title in blocked_exact_titles if title}
    for title in dedupe_keep_order(candidates):
        if title.lower().startswith("department of "):
            continue
        if title in blocked_exact_titles:
            continue
        cleaned.append(title)
    return cleaned


def score_title_set(titles: list[str], page: dict, record: dict) -> tuple[float, list[str]]:
    titles = dedupe_keep_order(titles)
    if not titles:
        return -1.0, []
    score = float(len(titles))
    url_blob = f"{page['url']} {page['title']}".lower()
    if any(term in url_blob for term in ["major", "program", "degree", "concentration", "undergraduate", "study", "catalog", "bulletin"]):
        score += 8.0
    if any(term in url_blob for term in ["admission", "apply"]):
        score -= 12.0
    existing_count = record.get("majors", {}).get("count")
    if isinstance(existing_count, int) and existing_count >= 8 and len(titles) > 0:
        ratio = len(titles) / max(existing_count, 1)
        if 0.5 <= ratio <= 1.6:
            score += 10.0
        elif 0.25 <= ratio <= 2.2:
            score += 4.0
        else:
            score -= 4.0
    obvious_noise = sum(1 for title in titles if title.lower().startswith(("college of ", "school of ", "department of ")))
    score -= obvious_noise * 3.0
    return score, titles


def choose_best_titles(record: dict, pages: list[dict]) -> tuple[list[str], str | None]:
    best_titles: list[str] = []
    best_url: str | None = None
    best_score = -1.0
    for page in pages:
        titles = extract_titles_from_page(page, record)
        score, cleaned = score_title_set(titles, page, record)
        if score > best_score:
            best_score = score
            best_titles = cleaned
            best_url = page["url"]
    if len(best_titles) < MIN_TITLES_TO_ACCEPT:
        return [], best_url
    return best_titles, best_url


def upsert_evidence(record: dict, field: str, claim: str, classification: str, source_url: str | None, source_excerpt: str) -> None:
    if not source_url:
        return
    existing = [item for item in record.get("evidence", []) if item.get("field") and item.get("source_url")]
    key = (field, claim, source_url)
    existing = [item for item in existing if (item.get("field"), item.get("claim"), item.get("source_url")) != key]
    existing.append(
        {
            "field": field,
            "claim": claim,
            "classification": classification,
            "source_url": source_url,
            "source_excerpt": source_excerpt,
            "retrieved_at": now_iso(),
        }
    )
    record["evidence"] = existing


def save_markdown(record: dict) -> None:
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
    lines.extend(
        [
            "## Majors",
            f"- Count: {record['majors']['count']}",
            f"- Count method: {record['majors']['count_method']}",
            f"- Titles extracted: {len(record['majors'].get('titles', []))}",
            "",
        ]
    )
    if record["majors"].get("titles"):
        lines.append("### Titles")
        for title in record["majors"]["titles"]:
            lines.append(f"- {title}")
        lines.append("")
    lines.extend(
        [
            "## Warnings",
        ]
    )
    for warning in record.get("verification", {}).get("warnings", []):
        lines.append(f"- {warning}")
    (UNI_DIR / f"{record['slug']}.md").write_text("\n".join(lines))


def save_record(record: dict) -> None:
    (UNI_DIR / f"{record['slug']}.json").write_text(json.dumps(record, indent=2))
    save_markdown(record)


def update_record(record: dict) -> tuple[dict, bool, str | None]:
    pages = crawl_school(record)
    titles, source_url = choose_best_titles(record, pages)
    changed = False
    warnings = [warning for warning in record.get("verification", {}).get("warnings", []) if "major titles" not in warning.lower()]
    if titles:
        changed = record.get("majors", {}).get("titles") != titles
        record["majors"]["titles"] = titles
        if not record["majors"].get("count"):
            record["majors"]["count"] = len(titles)
            record["majors"]["count_method"] = "counted extracted undergraduate-major titles from an official page"
        if source_url and source_url not in record.setdefault("source_urls", {}).setdefault("majors", []):
            record["source_urls"]["majors"].append(source_url)
        notes = record["majors"].get("notes") or record["majors"].get("count_method") or ""
        extraction_note = f"titles extracted from official page: {source_url}" if source_url else "titles extracted from official major/program page"
        if extraction_note not in notes:
            record["majors"]["notes"] = f"{notes}; {extraction_note}".strip("; ")
        claim = f"Extracted {len(titles)} official undergraduate major/program titles"
        upsert_evidence(record, "majors.titles", claim, "official_recommendation", source_url, "; ".join(titles[:12]))
        warnings.insert(0, f"Major titles extracted from official school source ({len(titles)} titles).")
    else:
        warnings.insert(0, "Major titles still need manual follow-up; no reliable official title list was extracted in this pass.")
    record.setdefault("verification", {})
    record["verification"]["last_verified_at"] = now_iso()
    if titles:
        confidence = str(record["verification"].get("confidence") or "")
        if not confidence.startswith("phase-"):
            confidence = "verified"
        record["verification"]["confidence"] = confidence
    record["verification"]["warnings"] = dedupe_keep_order(warnings)
    save_record(record)
    return record, bool(titles), source_url


def main() -> int:
    paths = sorted(UNI_DIR.glob("*.json"), key=lambda path: json.loads(path.read_text()).get("rank") or 999)
    updated: list[dict] = []
    populated = 0
    for path in paths:
        record = json.loads(path.read_text())
        record, has_titles, source_url = update_record(record)
        if has_titles:
            populated += 1
        updated.append(
            {
                "slug": record["slug"],
                "rank": record.get("rank"),
                "majors_count": record.get("majors", {}).get("count"),
                "titles_count": len(record.get("majors", {}).get("titles", [])),
                "titles_source_url": source_url,
            }
        )
    summary = {
        "generated_at": now_iso(),
        "schools_total": len(updated),
        "schools_with_titles": populated,
        "schools_without_titles": len(updated) - populated,
        "results": updated,
    }
    ROLLUP_PATH.parent.mkdir(parents=True, exist_ok=True)
    ROLLUP_PATH.write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in ["schools_total", "schools_with_titles", "schools_without_titles"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
