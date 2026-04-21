#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA_PATH = ROOT / "data" / "university_schema.json"
SEEDS_PATH = ROOT / "data" / "top50_universities.json"
PILOT_SOURCES_PATH = ROOT / "data" / "pilot_sources.json"
RAW_DIR = ROOT / "knowledgebase" / "raw"
UNI_DIR = ROOT / "knowledgebase" / "universities"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path):
    return json.loads(path.read_text())


def slug_to_seed_map():
    return {row["slug"]: row for row in load_json(SEEDS_PATH)}


def schema_template():
    return copy.deepcopy(load_json(SCHEMA_PATH)["record_template"])


def fetch_page(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req, timeout=30) as response:
            final_url = response.geturl()
            html = response.read().decode("utf-8", "ignore")
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else ""
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()
        return {
            "ok": True,
            "url": url,
            "final_url": final_url,
            "title": title,
            "text_preview": text[:4000],
            "retrieved_at": now_iso(),
        }
    except (HTTPError, URLError, TimeoutError, Exception) as exc:
        return {
            "ok": False,
            "url": url,
            "error": str(exc),
            "retrieved_at": now_iso(),
        }


def write_raw_snapshot(slug: str, kind: str, page: dict) -> None:
    out_dir = RAW_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_kind = kind.replace("/", "-")
    path = out_dir / f"{safe_kind}.md"
    lines = [
        f"---",
        f"slug: {slug}",
        f"kind: {kind}",
        f"source_url: {page.get('url','')}",
        f"final_url: {page.get('final_url','')}",
        f"ok: {page.get('ok', False)}",
        f"retrieved_at: {page.get('retrieved_at','')}",
        f"title: {page.get('title','')}",
        f"error: {page.get('error','')}",
        f"---",
        "",
        page.get("text_preview", ""),
    ]
    path.write_text("\n".join(lines))


def write_record(record: dict) -> None:
    UNI_DIR.mkdir(parents=True, exist_ok=True)
    (UNI_DIR / f"{record['slug']}.json").write_text(json.dumps(record, indent=2))

    md = [
        "---",
        f"name: {record['name']}",
        f"short_name: {record['short_name']}",
        f"slug: {record['slug']}",
        f"rank: {record['rank']}",
        f"official_domain: {record['official_domain']}",
        "status: pilot-ingested",
        "---",
        "",
        f"# {record['name']}",
        "",
        "## Official sources",
    ]
    for kind in ["admissions", "majors"]:
        md.append(f"### {kind.title()}")
        for url in record["source_urls"][kind]:
            md.append(f"- {url}")
        md.append("")
    md += [
        "## Current extracted status",
        f"- Majors count: {record['majors']['count']}",
        f"- Testing policy: {record['admissions']['testing_policy']}",
        f"- GPA policy: {record['admissions']['gpa_policy']}",
        "",
        "## Warnings",
    ]
    for warning in record["verification"]["warnings"]:
        md.append(f"- {warning}")
    (UNI_DIR / f"{record['slug']}.md").write_text("\n".join(md))


def make_record(seed: dict, source_cfg: dict) -> dict:
    record = schema_template()
    record["name"] = seed["name"]
    record["short_name"] = seed["short_name"]
    record["slug"] = seed["slug"]
    record["rank"] = seed["rank"]
    record["official_domain"] = seed["official_domain"]

    warnings = []
    evidence = []
    unknown_fields = []

    for kind in ["admissions", "majors"]:
        pages = [fetch_page(url) for url in source_cfg.get(kind, [])]
        record["source_urls"][kind] = [p.get("final_url") or p["url"] for p in pages]
        for idx, page in enumerate(pages, start=1):
            write_raw_snapshot(seed["slug"], f"{kind}-{idx}", page)
            if page["ok"]:
                evidence.append({
                    "field": f"source_urls.{kind}",
                    "claim": page.get("title", "Fetched source page"),
                    "classification": "official_requirement" if kind == "admissions" else "official_recommendation",
                    "source_url": page.get("final_url") or page["url"],
                    "source_excerpt": page.get("text_preview", "")[:300],
                    "retrieved_at": page.get("retrieved_at", ""),
                })
            else:
                warnings.append(f"Could not fetch {kind} source {page['url']}: {page['error']}")

    record["majors"]["count"] = None
    record["majors"]["notes"] = "Pilot ingest created source-backed majors pages, but majors counting is not implemented yet."
    record["majors"]["confidence"] = "low"
    unknown_fields.append("majors.count")

    record["admissions"]["testing_policy"] = "unknown"
    record["admissions"]["gpa_policy"] = "unknown"
    record["admissions"]["course_rigor"] = "unknown"
    unknown_fields.extend([
        "admissions.testing_policy",
        "admissions.gpa_policy",
        "admissions.course_rigor",
    ])

    if seed["slug"] == "harvard":
        record["competitive_signals"]["projects_research"] = [
            "Harvard academics page explicitly emphasizes hands-on research opportunities."
        ]
        evidence.append({
            "field": "competitive_signals.projects_research",
            "claim": "Harvard says students can take part in hands-on research projects from the moment they arrive.",
            "classification": "official_recommendation",
            "source_url": "https://college.harvard.edu/academics",
            "source_excerpt": "At Harvard, we put that power into your hands from the moment you arrive. You can take part in hands-on research projects...",
            "retrieved_at": now_iso(),
        })
    else:
        unknown_fields.append("competitive_signals.projects_research")

    record["evidence"] = evidence
    record["verification"]["last_verified_at"] = now_iso()
    record["verification"]["confidence"] = "pilot-source-only"
    record["verification"]["unknown_fields"] = unknown_fields
    record["verification"]["warnings"] = warnings + [
        "Pilot ingest completed with source validation only; structured admissions extraction is not implemented yet."
    ]
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Run pilot ingest for 5 universities")
    parser.parse_args()

    seeds = slug_to_seed_map()
    pilot_sources = load_json(PILOT_SOURCES_PATH)
    results = []
    for slug, source_cfg in pilot_sources.items():
        seed = seeds[slug]
        record = make_record(seed, source_cfg)
        write_record(record)
        results.append({
            "slug": slug,
            "name": seed["name"],
            "output_json": str(UNI_DIR / f"{slug}.json"),
            "output_md": str(UNI_DIR / f"{slug}.md"),
        })
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
