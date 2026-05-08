#!/usr/bin/env /usr/bin/python3
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import tempfile
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
    "drexel": ["https://drexel.edu/academics/undergrad-programs"],
    "florida-state": [
        "https://admissions.fsu.edu/majors",
        "https://academic-guide.fsu.edu/all-programs",
    ],
    "indiana-bloomington": ["https://bloomington.iu.edu/academics/degrees-majors/index.html"],
    "mit": ["https://catalog.mit.edu/degree-charts/"],
    "carnegie-mellon": ["https://www.cmu.edu/admission/majors-programs"],
    "case-western": ["https://case.edu/programs/"],
    "fordham": ["https://www.fordham.edu/academics/programs-and-degrees/undergraduate-programs/"],
    "georgetown": ["https://www.georgetown.edu/academics/areas-of-study/"],
    "loyola-marymount": ["https://www.lmu.edu/academics/degrees/"],
    "stanford": [
        "https://majors.stanford.edu/majors/text-only-lists-majors-and-offerings",
        "https://majors.stanford.edu/majors",
    ],
    "duke": ["https://admissions.duke.edu/academic-possibilities/"],
    "rutgers-new-brunswick": ["https://www.rutgers.edu/academics/explore-undergraduate-programs?field_location=654"],
    "uconn": ["https://catalog.uconn.edu/undergraduate/programs/"],
    "uc-san-diego": ["https://students.ucsd.edu/academics/advising/majors-minors/undergraduate-majors.html"],
    "upenn": [
        "https://apps.sas.upenn.edu/annex/majors/view/frame",
        "https://academics.seas.upenn.edu/ugrad/student-handbook/programs-options/",
    ],
    "vanderbilt": ["https://www.vanderbilt.edu/academics/program-finder/?degrees=bachelors"],
    "university-of-washington": ["https://admit.washington.edu/academics/majors/"],
    "colorado-school-of-mines": ["https://catalog.mines.edu/undergraduate/programs/"],
    "wake-forest": ["https://admissions.wfu.edu/academics/majors-minors/"],
    "wisconsin-madison": ["https://guide.wisc.edu/undergraduate/"],
    "unc-chapel-hill": ["https://catalog.unc.edu/undergraduate/programs-study/"],
    "temple": ["https://www.temple.edu/academics/degree-programs"],
    "tulane": ["https://catalog.tulane.edu/programs/?optionlessH#filter=.filter_1"],
    "university-of-san-diego": [
        "https://www.sandiego.edu/academics/majors-and-minors.php",
    ],
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
    for term in BAD_TITLE_SUBSTRINGS:
        if " " in term:
            if term in lowered:
                return False
        elif re.search(rf"\b{re.escape(term)}\b", lowered):
            return False
    for term in BAD_LEVEL_TERMS:
        cleaned_term = term.strip()
        if cleaned_term.replace('.', '').isalnum() and len(cleaned_term.replace('.', '')) <= 5:
            if re.search(rf"\b{re.escape(cleaned_term)}\b", lowered):
                return False
        elif term in lowered:
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
    title_match = re.search(r"<title[^>]*>(.*?)</title>", text, flags=re.I | re.S)
    title_text = strip_text(title_match.group(1) if title_match else "")
    body_text = strip_text(BeautifulSoup(text, "lxml").get_text(" ", strip=True))
    block_blob = strip_text(f"{title_text} {body_text[:1200]}").lower()
    if any(term in block_blob for term in BLOCK_TERMS):
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


def has_undergrad_program_label(raw: str | None) -> bool:
    text = strip_text(raw)
    if not text:
        return False
    lowered = text.lower()
    if "bachelor" in lowered:
        return True
    for piece in re.split(r"[,/]", text):
        normalized = strip_text(piece).replace(".", "")
        if re.fullmatch(r"B[A-Za-z]{1,7}", normalized, re.I):
            return True
    return False


def fetch_drexel_titles() -> tuple[list[str], str | None]:
    endpoint = "https://drexel.edu/api/du/search"
    source_url = "https://drexel.edu/academics/undergrad-programs"
    page = 1
    session = requests.Session()
    titles: list[str] = []
    while True:
        try:
            response = session.get(
                endpoint,
                params={
                    "pageId": "{0D72043A-4302-411D-94F1-605178A129E0}",
                    "perPage": 50,
                    "sortBy": "relevance",
                    "sortOrder": "asc",
                    "page": page,
                },
                headers=HEADERS,
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return [], None
        for item in payload.get("results") or []:
            if not has_undergrad_program_label(item.get("program")):
                continue
            add_candidate(titles, item.get("title"))
        total_results = int(payload.get("totalResults") or 0)
        if page * 50 >= total_results:
            break
        page += 1
        time.sleep(0.2)
    titles = dedupe_keep_order(titles)
    return (titles, source_url) if titles else ([], None)


def fetch_indiana_bloomington_titles() -> tuple[list[str], str | None]:
    endpoint = "https://exdd-academics.webapps.iu.edu/api/public/v1/endpoint/degrees"
    source_url = "https://bloomington.iu.edu/academics/degrees-majors/index.html"
    session = requests.Session()
    page = 1
    titles: list[str] = []
    while True:
        try:
            response = session.get(
                endpoint,
                params={"inst_cd": "IUBLA", "program_type": "2", "page": page, "perPage": 100},
                headers=HEADERS,
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return [], None
        for item in payload.get("data") or []:
            add_candidate(titles, item.get("name"))
        if not (payload.get("pagination") or {}).get("next"):
            break
        page += 1
        time.sleep(0.2)
    titles = dedupe_keep_order(titles)
    return (titles, source_url) if titles else ([], None)


def fetch_michigan_titles() -> tuple[list[str], str | None]:
    source_url = "https://atlas.ai.umich.edu/api/majorlist/"
    try:
        response = requests.get(source_url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return [], None
    titles: list[str] = []
    for item in payload or []:
        if str(item.get("education_level") or "").lower() != "bachelor":
            continue
        add_candidate(titles, item.get("name"))
    titles = dedupe_keep_order(titles)
    return (titles, source_url) if titles else ([], None)


def fetch_uci_titles() -> tuple[list[str], str | None]:
    source_url = "https://admissions.uci.edu/study/majors-minors.php"
    endpoint = "https://admissions.uci.edu/_php/views/majors-minors.php"
    try:
        response = requests.get(
            endpoint,
            params={"type": "Major"},
            headers={**HEADERS, "X-Requested-With": "XMLHttpRequest"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return [], None
    if not payload or not isinstance(payload, list):
        return [], None
    results_html = (payload[0] or {}).get("results") or ""
    soup = BeautifulSoup(results_html, "html.parser")
    titles: list[str] = []
    for button in soup.select("button.accordion__trigger"):
        add_candidate(titles, button.get_text(" ", strip=True))
    titles = dedupe_keep_order(titles)
    return (titles, source_url) if titles else ([], None)


def fetch_villanova_titles() -> tuple[list[str], str | None]:
    source_url = "https://www.villanova.edu/university/programs.html"
    try:
        response = requests.get(source_url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
    except Exception:
        return [], None
    match = re.search(r'var data =\{\s*"Programs":\[(.*?)\]\s*\};', response.text, re.S)
    if not match:
        return [], None
    try:
        programs = json.loads(f'[{match.group(1)}]')
    except Exception:
        return [], None
    titles: list[str] = []
    for item in programs:
        tags = str(item.get("tags") or "").lower()
        if "bachelors" not in tags:
            continue
        add_candidate(titles, html.unescape(item.get("title") or ""))
    titles = dedupe_keep_order(titles)
    return (titles, source_url) if titles else ([], None)


def fetch_washu_titles() -> tuple[list[str], str | None]:
    source_url = "https://admissions.washu.edu/academics/majors-programs/"
    endpoint = "https://admissions.washu.edu/wp-json/wustl/v1/degree-filters-data/posts"
    try:
        response = requests.get(
            endpoint,
            params={"queryFilter": "schools", "selectedTab": "schools", "page": 1, "search": ""},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return [], None
    titles: list[str] = []
    for item in (payload or {}).get("posts") or []:
        if not ((item.get("degreeTypes") or {}).get("bachelor")):
            continue
        add_candidate(titles, html.unescape(item.get("title") or ""))
    titles = dedupe_keep_order(titles)
    return (titles, source_url) if titles else ([], None)


def fetch_florida_state_titles() -> tuple[list[str], str | None]:
    source_url = "https://academic-guide.fsu.edu/all-programs"
    try:
        response = requests.get(source_url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
    except Exception:
        return [], None
    soup = BeautifulSoup(response.text, "html.parser")
    titles: list[str] = []
    for row in soup.select("div.views-row"):
        text = strip_text(row.get_text(" ", strip=True))
        if not text:
            continue
        title = re.split(r"\bProgram Description\b", text, maxsplit=1)[0]
        title = normalize_title(title)
        add_candidate(titles, title)
    titles = dedupe_keep_order(titles)
    return (titles, source_url) if titles else ([], None)


def fetch_san_diego_titles() -> tuple[list[str], str | None]:
    source_url = "https://www.sandiego.edu/academics/majors-and-minors.php"
    endpoint = "https://www.sandiego.edu/academics/process-degree-finder.php"
    try:
        response = requests.get(endpoint, params={"filters[1]": "Undergraduate"}, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        payload = json.loads(response.text)
    except Exception:
        return [], None
    titles: list[str] = []
    for group in payload or []:
        if not isinstance(group, dict):
            continue
        for items in group.values():
            if not isinstance(items, list):
                continue
            for item in items:
                if str(item.get("program_type") or "").lower() != "undergraduate":
                    continue
                if str(item.get("major") or "").lower() != "yes":
                    continue
                add_candidate(titles, item.get("title_override") or item.get("name"))
    titles = dedupe_keep_order(titles)
    return (titles, source_url) if titles else ([], None)


def fetch_uga_titles() -> tuple[list[str], str | None]:
    source_url = "https://www.career.uga.edu/uploads/documents/UGAMajorsChecklist.pdf"
    try:
        response = requests.get(source_url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
    except Exception:
        return [], None
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "uga-majors.pdf"
        txt_path = Path(tmpdir) / "uga-majors.txt"
        pdf_path.write_bytes(response.content)
        try:
            subprocess.run(["pdftotext", str(pdf_path), str(txt_path)], check=True, capture_output=True)
        except Exception:
            return [], None
        try:
            text = txt_path.read_text(errors="ignore")
        except Exception:
            return [], None
    titles: list[str] = []
    for line in text.splitlines():
        cleaned = strip_text(line)
        if not cleaned.startswith(""):
            continue
        add_candidate(titles, cleaned.lstrip("").strip(" -–—"))
    titles = dedupe_keep_order(titles)
    return (titles, source_url) if titles else ([], None)


BAYLOR_QUICKSEARCH_TITLE_MAP = {
    "Accounting & Business Law, Department of": ["Accounting"],
    "American Studies": ["American Studies"],
    "Anthropology, Department of": ["Anthropology"],
    "Art, Department of": ["Art"],
    "Asian Studies": ["Asian Studies"],
    "Biology, Department of": ["Biology"],
    "Chemistry & Biochemistry, Department of": ["Chemistry", "Biochemistry"],
    "Classics, Department of": ["Classics"],
    "Communication Sciences & Disorders, Department of": ["Communication Sciences & Disorders"],
    "Communication, Department of": ["Communication"],
    "Computer Science": ["Computer Science"],
    "Department of Public Health": ["Public Health"],
    "Economics": ["Economics"],
    "Electrical and Computer Engineering": ["Electrical and Computer Engineering"],
    "Engineering, Department of": ["Engineering"],
    "English, Department of": ["English"],
    "Entrepreneurship": ["Entrepreneurship"],
    "Environmental Science": ["Environmental Science"],
    "Film and Digital Media Department": ["Film and Digital Media"],
    "Finance, Insurance and Real Estate": ["Finance", "Insurance", "Real Estate"],
    "French": ["French"],
    "German": ["German"],
    "Great Texts": ["Great Texts"],
    "History, Department of": ["History"],
    "Informatics": ["Bioinformatics"],
    "Institute for Aviation Sciences": ["Aviation Sciences"],
    "Interior Design": ["Interior Design"],
    "Italian": ["Italian"],
    "Journalism, Public Relations & New Media": ["Journalism", "Public Relations"],
    "Latin American Studies": ["Latin American Studies"],
    "Linguistics": ["Linguistics"],
    "Louise Herrington School of Nursing": ["Nursing"],
    "Management": ["Management"],
    "Marketing, Department of": ["Marketing"],
    "Mathematics, Department of": ["Mathematics"],
    "Middle East Studies": ["Middle East Studies"],
    "Nutrition Sciences": ["Nutrition Sciences"],
    "Physics, Department of": ["Physics"],
    "Psychology & Neuroscience": ["Psychology", "Neuroscience"],
    "Sociology, Department of": ["Sociology"],
    "Theatre, Department of": ["Theatre Arts"],
    "University Scholars": ["University Scholars"],
}


def extract_baylor_titles_from_quicksearch_html(page_html: str) -> list[str]:
    start = page_html.find("var quickSearchData = ")
    if start == -1:
        return []
    match = re.search(r"var quickSearchData = (\{.*?\});\s*\}", page_html[start:], re.S)
    if not match:
        return []
    try:
        payload = json.loads(match.group(1))
    except Exception:
        return []

    titles: list[str] = []
    for item in payload.values():
        if not isinstance(item, dict):
            continue
        title = html.unescape(strip_text(item.get("title") or ""))
        if title not in BAYLOR_QUICKSEARCH_TITLE_MAP:
            continue
        link = str(item.get("link") or "")
        if "baylor.edu" not in link or any(token in link for token in ["/news/", "calendar.", "/events", "/event/"]):
            continue
        for candidate in BAYLOR_QUICKSEARCH_TITLE_MAP[title]:
            add_candidate(titles, candidate)
    return dedupe_keep_order(titles)


def fetch_baylor_titles() -> tuple[list[str], str | None]:
    source_url = "https://www.baylor.edu/"
    try:
        response = requests.get(source_url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
    except Exception:
        return [], None
    titles = extract_baylor_titles_from_quicksearch_html(response.text)
    return (titles, source_url) if titles else ([], None)


def fetch_school_specific_titles(record: dict) -> tuple[list[str], str | None]:
    slug = record.get("slug")
    if slug == "baylor":
        return fetch_baylor_titles()
    if slug == "drexel":
        return fetch_drexel_titles()
    if slug == "florida-state":
        return fetch_florida_state_titles()
    if slug == "indiana-bloomington":
        return fetch_indiana_bloomington_titles()
    if slug == "michigan":
        return fetch_michigan_titles()
    if slug == "uc-irvine":
        return fetch_uci_titles()
    if slug == "villanova":
        return fetch_villanova_titles()
    if slug == "washu":
        return fetch_washu_titles()
    if slug == "university-of-georgia":
        return fetch_uga_titles()
    if slug == "university-of-san-diego":
        return fetch_san_diego_titles()
    return [], None


def is_rutgers_new_brunswick_text(text: str) -> bool:
    normalized = strip_text(text).lower()
    return re.search(r"rutgers[-\s]+new\s+brunswick", normalized) is not None


def extract_titles_from_page(page: dict, record: dict) -> list[str]:
    soup = page["soup"]
    main = soup.find("main") or soup
    candidates: list[str] = []
    page_blob = f"{page['title']} {page['url']}".lower()

    if record["slug"] == "upenn" and "apps.sas.upenn.edu/annex/majors/view/frame" in page["url"]:
        html = str(soup)
        matches = re.findall(r'"name":"([^"]+)"', html)
        if matches:
            return dedupe_keep_order([title for title in matches if is_good_title(normalize_title(title))])

    if record["slug"] == "upenn" and "programs-options" in page["url"]:
        return []

    if record["slug"] == "uconn" and "azindex" in page["url"]:
        return []

    if record["slug"] == "unc-chapel-hill" and "catalog.unc.edu/azindex/" in page["url"]:
        return []

    if record["slug"] == "unc-chapel-hill" and "catalog.unc.edu/undergraduate/programs-study/" not in page["url"]:
        return []

    if record["slug"] == "colorado-school-of-mines" and "azindex" in page["url"]:
        return []

    if record["slug"] == "baylor" and "catalog.baylor.edu/azindex/" in page["url"]:
        return []

    if record["slug"] == "baylor" and page["url"].rstrip("/") == "https://catalog.baylor.edu/undergraduate":
        return []

    if record["slug"] == "princeton" and "admission.princeton.edu/academics/degrees-departments" in page["url"]:
        princeton_titles: list[str] = []
        for heading in main.select("details.concentration h2"):
            title = normalize_title(heading.get_text(" ", strip=True))
            if not title or title.lower() in BAD_TITLE_EXACT:
                continue
            if title == "Computer Science":
                princeton_titles.extend(["Computer Science (A.B.)", "Computer Science (B.S.E.)"])
                continue
            princeton_titles.append(title)
        if princeton_titles:
            return dedupe_keep_order(princeton_titles)

    if record["slug"] == "cornell" and "admissions.cornell.edu/academics/majors" in page["url"]:
        cornell_titles: list[str] = []
        for heading in main.select("li h2"):
            title = normalize_title(heading.get_text(" ", strip=True))
            if not title or title.lower() in BAD_TITLE_EXACT:
                continue
            cornell_titles.append(title)
        if cornell_titles:
            return dedupe_keep_order(cornell_titles)

    if record["slug"] == "uconn" and "/undergraduate/programs/" in page["url"]:
        uconn_titles: list[str] = []
        for anchor in main.find_all("a", href=True):
            href = urljoin(page["url"], anchor["href"])
            if "/undergraduate/programs/" not in href:
                continue
            add_candidate(uconn_titles, anchor.get_text(" ", strip=True))
        if uconn_titles:
            return dedupe_keep_order(uconn_titles)

    if record["slug"] == "unc-chapel-hill" and "catalog.unc.edu/undergraduate/programs-study/" in page["url"]:
        unc_titles: list[str] = []
        for anchor in main.select(".az_sitemap li a[href]"):
            href = urljoin(page["url"], anchor["href"])
            if "/undergraduate/programs-study/" not in href:
                continue
            text = strip_text(anchor.get_text(" ", strip=True))
            if " major" not in text.lower():
                continue
            add_candidate(unc_titles, text)
        if unc_titles:
            return dedupe_keep_order(unc_titles)

    if record["slug"] == "temple" and "temple.edu/academics/degree-programs" in page["url"]:
        temple_titles: list[str] = []
        for option in main.select('select[name="major[]"] option'):
            text = strip_text(option.get_text(" ", strip=True))
            if not text:
                continue
            add_candidate(temple_titles, text)
        if temple_titles:
            return dedupe_keep_order(temple_titles)

    if record["slug"] == "tulane" and "catalog.tulane.edu/programs/" in page["url"]:
        tulane_titles: list[str] = []
        for item in main.select("li.item a"):
            card = item.find_parent("li", class_="item")
            if card is None:
                continue
            keywords = [strip_text(node.get_text(" ", strip=True)) for node in card.select("span.keyword")]
            lowered_keywords = [k.lower() for k in keywords]
            if not any("undergraduate" in k for k in lowered_keywords):
                continue
            if not any(re.fullmatch(r"major", k, re.I) for k in keywords):
                continue
            title_node = card.select_one("span.title")
            if not title_node:
                continue
            add_candidate(tulane_titles, title_node.get_text(" ", strip=True))
        if tulane_titles:
            return dedupe_keep_order(tulane_titles)

    if record["slug"] == "wisconsin-madison" and (
        "guide.wisc.edu/undergraduate/" in page["url"] or "guide.wisc.edu/explore-majors/" in page["url"]
    ):
        wisc_titles: list[str] = []
        for anchor in main.find_all("a", href=True):
            href = urljoin(page["url"], anchor["href"])
            if "/undergraduate/" not in href:
                continue
            text = strip_text(anchor.get_text(" ", strip=True))
            if "..." in text or "…" in text:
                text = re.split(r"(?:\.\.\.|…)", text, maxsplit=1)[-1].strip()
            if "certificate" in text.lower():
                continue
            degree_match = re.match(r"^(.*?),\s*(BA|BS|BBA|BFA|BM|BMus|BSE|BAS|BLS)\b", text)
            if degree_match:
                add_candidate(wisc_titles, degree_match.group(1))
        if wisc_titles:
            return dedupe_keep_order(wisc_titles)

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

    if record["slug"] == "wake-forest":
        wake_titles: list[str] = []
        for card in main.select("div.degree-list"):
            label = card.select_one("span.majorminor")
            if not label:
                continue
            label_text = strip_text(label.get_text(" ", strip=True)).lower()
            if "major" not in label_text:
                continue
            name_node = card.select_one("p.major-name")
            if not name_node:
                continue
            title_text = strip_text(name_node.get_text(" ", strip=True))
            title_text = re.sub(r"\b(Major|Minor|Certificate)(\s*,\s*(Major|Minor|Certificate))*$", "", title_text, flags=re.I).strip()
            add_candidate(wake_titles, title_text)
        if wake_titles:
            return dedupe_keep_order(wake_titles)

    if record["slug"] == "university-of-washington":
        uw_titles: list[str] = []
        for major_card in main.select("#majors-container div.major"):
            heading = major_card.select_one(".major-type h2 a")
            if heading:
                add_candidate(uw_titles, heading.get_text(" ", strip=True))
        if uw_titles:
            return dedupe_keep_order(uw_titles)

    if record["slug"] == "loyola-marymount":
        lmu_titles: list[str] = []
        for anchor in main.select("a.program-finder__results__item[data-item]"):
            degrees_node = anchor.select_one(".program-finder__results__degrees")
            degrees = strip_text(degrees_node.get_text(" ", strip=True) if degrees_node else "")
            if not degrees:
                continue
            lowered_degrees = degrees.lower()
            if not any(token in lowered_degrees for token in ("b.s.", "b.a.", "b.f.a.", "bachelor")):
                continue
            title_node = anchor.select_one(".program-finder__results__title")
            if title_node:
                add_candidate(lmu_titles, title_node.get_text(" ", strip=True))
        if lmu_titles:
            return dedupe_keep_order(lmu_titles)

    if record["slug"] == "rice" and "rice.edu/majors-minors-and-programs" in page["url"]:
        rice_titles: list[str] = []
        for anchor in main.find_all("a", href=True):
            href = urljoin(page["url"], anchor["href"])
            if "ga.rice.edu/programs-study/departments-programs/" not in href:
                continue
            add_candidate(rice_titles, anchor.get_text(" ", strip=True))
        if rice_titles:
            return dedupe_keep_order(rice_titles)

    if record["slug"] == "santa-clara" and "undergraduate-majors-and-minors" in page["url"]:
        scu_titles: list[str] = []
        for card in main.select("div.card"):
            card_text = strip_text(card.get_text(" ", strip=True))
            major_match = re.search(r"\bMajors?\s*:\s*(.+?)(?:\bMinors?\s*:|$)", card_text, re.I)
            if not major_match:
                continue
            major_blob = strip_text(major_match.group(1))
            if not major_blob:
                continue
            if "," in major_blob:
                for piece in major_blob.split(","):
                    add_candidate(scu_titles, piece)
            else:
                add_candidate(scu_titles, major_blob)
        if scu_titles:
            return dedupe_keep_order(scu_titles)

    if record["slug"] == "uc-san-diego" and "students.ucsd.edu/academics/advising/majors-minors/undergraduate-majors.html" in page["url"]:
        ucsd_titles: list[str] = []
        start = None
        for heading in main.find_all("h2"):
            if normalize_title(heading.get_text(" ", strip=True)).lower().startswith("majors"):
                start = heading
                break
        if start is not None:
            sibling = start.find_next_sibling()
            while sibling and isinstance(sibling, Tag):
                sibling_name = getattr(sibling, "name", "")
                sibling_text = normalize_title(sibling.get_text(" ", strip=True)) if sibling_name in HEADING_TAGS else ""
                if sibling_name == "h2" and not sibling_text.lower().startswith("majors"):
                    break
                if sibling_name == "p":
                    text = strip_text(sibling.get_text(" ", strip=True))
                    for match in re.findall(r"([A-Z][A-Za-z0-9&,:/'’()\- ]+?)\s*\((?:B\.A\.|B\.S\.|B\.F\.A\.|B\.I\.A\.|B\.S\./M\.S\.|B\.A\./M\.A\.)[^)]*\)[*†‡♦◊]*", text):
                        cleaned_match = normalize_title(match)
                        repeated_match = re.fullmatch(r"(.+?)\s+\1", cleaned_match)
                        if repeated_match:
                            cleaned_match = repeated_match.group(1)
                        repeated_with_suffix = re.fullmatch(r"(.+?)\s+\1(\s*\(.+\))", cleaned_match)
                        if repeated_with_suffix:
                            cleaned_match = f"{repeated_with_suffix.group(1)}{repeated_with_suffix.group(2)}"
                        add_candidate(ucsd_titles, cleaned_match)
                sibling = sibling.find_next_sibling()
        if ucsd_titles:
            return dedupe_keep_order(ucsd_titles)

    if record["slug"] == "colorado-school-of-mines" and "/undergraduate/programs/" in page["url"]:
        mines_titles: list[str] = []
        if page["url"].rstrip("/").endswith("/undergraduate/programs"):
            for anchor in main.find_all("a", href=True):
                href = urljoin(page["url"], anchor["href"])
                anchor_text = strip_text(anchor.get_text(" ", strip=True))
                if anchor_text.lower() == "print":
                    continue
                if "/undergraduate/programs/" not in href or href.rstrip("/") == page["url"].rstrip("/"):
                    continue
                if any(term in href.lower() for term in ("additionalprograms", "univhonorsandscholarsprogram", "hass/")):
                    continue
                add_candidate(mines_titles, anchor_text)
        for heading in main.find_all(["h2", "h3"]):
            text = normalize_title(heading.get_text(" ", strip=True))
            if not text.lower().startswith("bachelor of "):
                continue
            degree_title = re.sub(r"^Bachelor of [A-Za-z./ ]+ in ", "", text, flags=re.I)
            add_candidate(mines_titles, degree_title)
        if mines_titles:
            return dedupe_keep_order(mines_titles)

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
        bachelor_link = li.find("a", string=re.compile(r"^Bachelor'?s$", re.I))
        if bachelor_link:
            heading = li.find(HEADING_TAGS)
            if heading:
                add_candidate(candidates, heading.get_text(" ", strip=True))
            else:
                line = strip_text(li.get_text("\n", strip=True).split("\n", 1)[0])
                add_candidate(candidates, line)
            continue
        heading = li.find(HEADING_TAGS)
        if heading:
            li_text = strip_text(li.get_text(" ", strip=True))
            if re.search(r"(^|\s)M(\s|$)", li_text) or re.search(r"(^|\s)Major(s)?(\s|$)", li_text, re.I):
                add_candidate(candidates, heading.get_text(" ", strip=True))
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
        if anchor_text.lower() == "list of majors":
            continue
        if not anchor_text_generic:
            add_candidate(candidates, anchor_text)
        else:
            heading = nearest_heading(anchor)
            if heading:
                add_candidate(candidates, heading)

    finder_like_page = any(term in page_blob for term in ("program finder", "departments and programs"))
    if finder_like_page:
        for li in main.find_all("li"):
            first_link = li.find("a", href=True)
            if not first_link:
                continue
            text = normalize_title(first_link.get_text(" ", strip=True))
            lowered = text.lower()
            if lowered in {"bachelor's", "masters", "doctoral", "online", "non-degree"}:
                continue
            if any(term in lowered for term in ("admissions", "financial aid", "apply", "learn more", "cookie", "privacy")):
                continue
            add_candidate(candidates, text)

    if record["slug"] == "upenn":
        for button in main.find_all("button"):
            label = strip_text(button.get_text(" ", strip=True))
            if not label:
                continue
            if label.lower() in {"expand all majors", "collapse all majors"}:
                continue
            add_candidate(candidates, label)

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
    if "azindex" in url_blob:
        score -= 20.0
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


def latest_titles_source_url(record: dict) -> str | None:
    for item in reversed(record.get("evidence", [])):
        if item.get("field") == "majors.titles" and item.get("source_url"):
            return item["source_url"]
    return next(iter(record.get("source_urls", {}).get("majors", [])), None)


def save_record(record: dict) -> None:
    (UNI_DIR / f"{record['slug']}.json").write_text(json.dumps(record, indent=2))
    save_markdown(record)


def update_record(record: dict) -> tuple[dict, bool, str | None]:
    titles, source_url = fetch_school_specific_titles(record)
    if not titles:
        pages = crawl_school(record)
        titles, source_url = choose_best_titles(record, pages)
    changed = False
    old_titles = list((record.get("majors") or {}).get("titles") or [])
    old_source_urls = list(((record.get("source_urls") or {}).get("majors") or []))
    old_warnings = list((record.get("verification") or {}).get("warnings") or [])
    warnings = [warning for warning in old_warnings if "major titles" not in warning.lower()]
    if titles:
        changed = record.get("majors", {}).get("titles") != titles
        record["majors"]["titles"] = titles
        existing_count = record["majors"].get("count")
        existing_count_method = str(record["majors"].get("count_method") or "")
        if (not existing_count) or (
            "counted extracted undergraduate-major titles" in existing_count_method.lower() and existing_count != len(titles)
        ):
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
    if titles:
        confidence = str(record["verification"].get("confidence") or "")
        if not confidence.startswith("phase-"):
            confidence = "verified"
        record["verification"]["confidence"] = confidence
    record["verification"]["warnings"] = dedupe_keep_order(warnings)
    warnings = record["verification"]["warnings"]
    new_titles = list((record.get("majors") or {}).get("titles") or [])
    new_source_urls = list(((record.get("source_urls") or {}).get("majors") or []))
    if new_titles != old_titles or new_source_urls != old_source_urls or warnings != old_warnings:
        record["verification"]["last_verified_at"] = now_iso()
    save_record(record)
    return record, bool(titles), source_url


def main() -> int:
    parser = argparse.ArgumentParser(description="Populate majors.titles from official school sources.")
    parser.add_argument("--school", action="append", dest="schools", help="School slug to update (repeatable).")
    args = parser.parse_args()

    paths = sorted(UNI_DIR.glob("*.json"), key=lambda path: json.loads(path.read_text()).get("rank") or 999)
    all_paths = list(paths)
    if args.schools:
        allowed = set(args.schools)
        paths = [path for path in paths if path.stem in allowed]
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
    summary_results: list[dict] = []
    summary_populated = 0
    for path in all_paths:
        record = json.loads(path.read_text())
        titles = record.get("majors", {}).get("titles", [])
        if titles:
            summary_populated += 1
        summary_results.append(
            {
                "slug": record["slug"],
                "rank": record.get("rank"),
                "majors_count": record.get("majors", {}).get("count"),
                "titles_count": len(titles),
                "titles_source_url": latest_titles_source_url(record),
            }
        )
    summary = {
        "generated_at": now_iso(),
        "schools_total": len(summary_results),
        "schools_with_titles": summary_populated,
        "schools_without_titles": len(summary_results) - summary_populated,
        "results": summary_results,
    }
    ROLLUP_PATH.parent.mkdir(parents=True, exist_ok=True)
    ROLLUP_PATH.write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in ["schools_total", "schools_with_titles", "schools_without_titles"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
