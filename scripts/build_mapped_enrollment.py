#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNI_DIR = ROOT / "knowledgebase" / "universities"
ENROLL_DIR = ROOT / "data" / "enrollment"

LEGEND_ORDER = [
    "Architecture and Planning",
    "Engineering",
    "Science",
    "Social Sciences",
    "Humanities & Arts",
    "Sloan School of Management",
    "Interdisciplinary Programs",
]

DEGREE_SUFFIX_RE = re.compile(
    r",\s*(?:A\.?ENGT\.?|B\.?A\.?E\.?|B\.?ARCH\.?|B\.?DES\.?|B\.?F\.?A\.?|B\.?M\.?|B\.?MUS\.?|B\.?PHIL\.?|B\.?S\.?|B\.?A\.?|B\.?B\.?A\.?|B\.?S\.?B\.?A\.?|B\.?S\.?E\.?|B\.?ENG\.?|B\.?ENGR\.?|S\.?B\.?|SC\.?B\.?)(?:\s*\([^)]*\))?$",
    re.I,
)
UPPER_CODE_PAREN_RE = re.compile(r"\(([A-Z][A-Z0-9&/\- ]{1,14}|A-I)\)$")
TRAILING_NOISE_PAREN_RE = re.compile(
    r"\((?:[^)]*(?:campus|college|school|business|science|engineering|arts and architecture|information sciences and technology|health and human development|great valley|world campus|university college|capital|altoona|abington|behrend|berks|brandywine|dubois|erie|fayette|greater allegheny|harrisburg|hazleton|lehigh valley|mont alto|new kensington|schuylkill|scranton|shenango|wilkes-barre|york))[^)]*\)$",
    re.I,
)
GENERIC_RE = re.compile(
    r"catalog|bulletin|about |academic advising|academic information|academic integrity|academic progress|degree requirements|general education|archive|return to top|learn more|program finder|rotc|course(?:s)?$|courses$|requirements$|index$|overview$|explore degrees|majors and minors|undergraduate bulletin|advising and planning",
    re.I,
)
INVALID_EXACT = {
    "slide 1",
    "slide 2",
    "slide 3",
    "slide 4",
    "duke-in programs",
    "air force rotc",
    "army rotc",
    "navy rotc",
    "catalog a-z index",
    "undergraduate bulletin",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def latest_titles_source_url(record: dict) -> str:
    source_urls = record.get("source_urls") or {}
    majors = source_urls.get("majors") or []
    general = source_urls.get("general") or []
    admissions = source_urls.get("admissions") or []
    for group in (majors, general, admissions):
        for url in group:
            if url:
                return url
    return ""


def title_score(raw: str) -> int:
    score = 0
    if re.search(r",\s*(?:B\.|A\.ENGT|S\.B|Sc\.B)", raw, re.I):
        score += 4
    if UPPER_CODE_PAREN_RE.search(raw):
        score += 2
    lowered = raw.lower()
    if GENERIC_RE.search(lowered) or lowered in INVALID_EXACT:
        score -= 10
    if lowered in {"air force", "army", "navy"}:
        score -= 8
    return score


def canonicalize_title(raw: str) -> str:
    title = re.sub(r"\s+", " ", (raw or "").replace("\xa0", " ")).strip(" -–—|•")
    title = DEGREE_SUFFIX_RE.sub("", title).strip()
    title = TRAILING_NOISE_PAREN_RE.sub("", title).strip()
    title = UPPER_CODE_PAREN_RE.sub("", title).strip()
    title = re.sub(r"\s+", " ", title).strip(" ,;-:/")
    return title


def is_valid_title(title: str) -> bool:
    if not title:
        return False
    lowered = title.lower().strip()
    if lowered in INVALID_EXACT:
        return False
    if GENERIC_RE.search(lowered):
        return False
    if lowered.startswith("b.a. degree requirements") or lowered.startswith("b.s. degree requirements"):
        return False
    if lowered.startswith("baccalaureate degree"):
        return False
    if lowered in {"about penn state", "academic advising", "academic information", "academic integrity", "academic progress"}:
        return False
    return len(title) >= 3


def clean_titles(record: dict) -> list[str]:
    best_by_key: dict[str, tuple[int, str]] = {}
    for raw in (record.get("majors") or {}).get("titles") or []:
        title = canonicalize_title(raw)
        if not is_valid_title(title):
            continue
        key = title.casefold()
        score = title_score(raw)
        current = best_by_key.get(key)
        if current is None or score > current[0] or (score == current[0] and len(title) < len(current[1])):
            best_by_key[key] = (score, title)
    titles = [title for _score, title in best_by_key.values()]
    titles.sort()
    return titles


def abbrev(title: str) -> str:
    words = re.findall(r"[A-Za-z0-9&]+", title)
    if not words:
        return title[:8].upper()
    if len(words) == 1:
        word = words[0]
        return word[:8] if len(word) <= 8 else word[:4].title()
    initials = "".join(word[0].upper() for word in words[:4] if word[0].isalnum())
    return initials[:8] or title[:8].upper()


def map_school(title: str) -> str:
    t = title.lower()

    architecture_terms = ["architecture", "urban planning", "city planning", "planning", "landscape"]
    business_terms = [
        "accounting", "finance", "marketing", "business", "management", "entrepreneur", "real estate",
        "supply chain", "hospitality", "actuarial", "commerce", "merchandising", "operations management",
    ]
    engineering_terms = [
        "engineering", "computer science", "computer engineering", "electrical", "mechanical", "civil", "chemical",
        "aerospace", "industrial", "materials", "cyber", "informatics", "information systems", "data science",
        "artificial intelligence", "bioinformatics", "systems science", "operations research", "software",
    ]
    science_terms = [
        "biology", "chemistry", "physics", "mathematics", "math", "statistical", "statistics", "neuroscience",
        "earth", "geology", "astronomy", "astrophysics", "marine", "environmental science", "ecology",
        "animal science", "plant", "biochemistry", "molecular", "microbiology", "bio", "public health",
        "health science", "kinesiology", "nutrition", "genomics", "biomedical", "cognitive science",
    ]
    humanities_terms = [
        "history", "philosophy", "english", "literature", "language", "linguistics", "art", "music", "theater",
        "theatre", "dance", "film", "religion", "classics", "writing", "design", "studio", "visual",
        "journalism", "media studies", "creative writing", "museum", "performance",
    ]
    social_science_terms = [
        "economics", "psychology", "sociology", "political", "anthropology", "public policy", "international relations",
        "education", "communication", "criminology", "geography", "social work", "gender", "ethnic studies",
        "african", "american studies", "asian studies", "area studies", "justice", "human development",
    ]

    if any(term in t for term in architecture_terms):
        return "Architecture and Planning"
    if any(term in t for term in business_terms):
        return "Sloan School of Management"
    if any(term in t for term in engineering_terms):
        return "Engineering"
    if any(term in t for term in science_terms):
        return "Science"
    if any(term in t for term in humanities_terms):
        return "Humanities & Arts"
    if any(term in t for term in social_science_terms):
        return "Social Sciences"
    if any(term in t for term in ["interdisciplinary", "self-designed", "individualized", "general studies", "program ii", "symbolic systems"]):
        return "Interdisciplinary Programs"
    return "Interdisciplinary Programs"


def preserve_existing(payload: dict) -> bool:
    majors = payload.get("majors") or []
    if not majors:
        return False
    if payload.get("mode") in {"majors-list", "mapped-majors"}:
        return False
    totals = payload.get("totals") or {}
    return bool(totals) or payload.get("academic_term") or payload.get("academic_year")


def build_payload(record: dict) -> dict:
    titles = clean_titles(record)
    majors = []
    for title in titles:
        school = map_school(title)
        majors.append(
            {
                "name": title,
                "code": abbrev(title),
                "school": school,
                "primary": 1,
                "secondary": 0,
                "total": 1,
            }
        )
    source_url = latest_titles_source_url(record)
    major_count = (record.get("majors") or {}).get("count")
    count_method = (record.get("majors") or {}).get("count_method") or ""
    confidence = (record.get("majors") or {}).get("confidence") or ""
    notes = (record.get("majors") or {}).get("notes") or ""
    source_urls = []
    for group in ((record.get("source_urls") or {}).get("majors") or [], (record.get("source_urls") or {}).get("general") or []):
        for url in group:
            if url and url not in source_urls:
                source_urls.append(url)
    inferred_legend = [group for group in LEGEND_ORDER if any(m["school"] == group for m in majors)]
    return {
        "university": record["name"],
        "slug": record["slug"],
        "academic_year": "Structured majors inventory",
        "retrieved_at": str(date.today()),
        "mode": "mapped-majors",
        "source_url": source_url,
        "source_urls": source_urls,
        "chart_title": "Undergraduate majors map — structured inventory",
        "major_count_label": f"{len(majors)} mapped majors",
        "total_label": "equal-weight bubbles",
        "scope_note": "This school does not yet have a source-backed per-major enrollment breakdown in Goal Kicker. To keep the majors panel visually consistent with MIT, each official undergraduate major title is mapped into a broad discipline bucket and rendered as an equal-weight bubble. Bubble size here does not indicate enrollment.",
        "summary_note": f"{len(majors)} mapped majors · equal-weight bubbles" + (f" · official count page says {major_count} majors" if major_count else ""),
        "legend_order": inferred_legend,
        "totals": {
            "mapped_major_titles": len(majors),
            "official_major_count": major_count,
        },
        "notes": " ".join(bit for bit in [count_method, notes, f"Confidence: {confidence}." if confidence else ""] if bit).strip(),
        "majors": majors,
    }


def main() -> None:
    updated = 0
    preserved = 0
    for path in sorted(UNI_DIR.glob("*.json")):
        record = read_json(path)
        out_path = ENROLL_DIR / f"{record['slug']}.json"
        if out_path.exists():
            existing = read_json(out_path)
            if preserve_existing(existing):
                preserved += 1
                continue
        payload = build_payload(record)
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        updated += 1
    print(json.dumps({"updated": updated, "preserved": preserved}, indent=2))


if __name__ == "__main__":
    main()
