#!/usr/bin/env /usr/bin/python3
from __future__ import annotations

import json
import re
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
UNI_DIR = ROOT / "knowledgebase" / "universities"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
SEARCH_URL = "https://html.duckduckgo.com/html/"
TIMEOUT = 25

C7_FIELDS = {
    "Rigor of secondary school record": "admissions.course_rigor",
    "Recommendation(s)": "admissions.recommendations",
    "Application Essay": "admissions.essays",
    "Academic GPA": "admissions.gpa_policy_importance",
    "Standardized test scores": "admissions.testing_policy_importance",
}
C7_LABELS = ["Very Important", "Important", "Considered", "Not Considered"]
C8_LABELS = [
    "Required to be considered for admission",
    "Required for some",
    "Recommended",
    "Not required for admission, but considered if submitted",
    "Not considered for admission, even if submitted",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def strip_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def unwrap_ddg_url(url: str) -> str:
    if "duckduckgo.com/l/?" not in url:
        return url
    q = parse_qs(urlparse(url).query)
    uddg = q.get("uddg")
    if not uddg:
        return url
    return unquote(uddg[0])


def load_record(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def save_record(record: dict[str, Any]) -> None:
    path = UNI_DIR / f"{record['slug']}.json"
    path.write_text(json.dumps(record, indent=2))


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


def discover_cds_url(record: dict[str, Any]) -> str | None:
    domain = record["official_domain"]
    queries = [
        f'site:{domain} "Common Data Set" pdf',
        f'site:{domain} "Common Data Set"',
        f'site:{domain} cds pdf admissions',
    ]
    session = requests.Session()
    for query in queries:
        try:
            response = session.get(SEARCH_URL, params={"q": query}, headers=HEADERS, timeout=TIMEOUT)
        except Exception:
            continue
        soup = BeautifulSoup(response.text or "", "lxml")
        for anchor in soup.select("a.result__a"):
            href = unwrap_ddg_url(anchor.get("href") or "")
            parsed = urlparse(href)
            if not parsed.scheme.startswith("http"):
                continue
            host = parsed.netloc.lower()
            if host == domain or host.endswith("." + domain):
                blob = (href + " " + anchor.get_text(" ", strip=True)).lower()
                if "common data set" in blob or "/cds" in blob or "cds_" in blob:
                    return href
        time.sleep(0.2)
    return None


def fetch_text(url: str) -> str:
    if url.lower().endswith(".pdf") or ".pdf" in url.lower():
        with tempfile.TemporaryDirectory() as td:
            pdf_path = Path(td) / "cds.pdf"
            txt_path = Path(td) / "cds.txt"
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            pdf_path.write_bytes(r.content)
            subprocess.run(["pdftotext", "-layout", str(pdf_path), str(txt_path)], check=True)
            return txt_path.read_text(errors="ignore")
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    html = r.text or ""
    if "<html" in html.lower():
        soup = BeautifulSoup(html, "lxml")
        return soup.get_text("\n", strip=False)
    return html


def find_heading_positions(line: str, labels: list[str]) -> list[tuple[int, str]]:
    positions = []
    for label in labels:
        idx = line.find(label)
        if idx >= 0:
            positions.append((idx, label))
    return sorted(positions)


def pick_label_from_x(line: str, positions: list[tuple[int, str]]) -> str | None:
    xs = [m.start() for m in re.finditer(r"\bX\b", line)]
    if not xs or not positions:
        return None
    x = xs[-1]
    return min(positions, key=lambda item: abs(item[0] - x))[1]


def parse_c7(text: str) -> dict[str, dict[str, str]]:
    lines = text.splitlines()
    out: dict[str, dict[str, str]] = {}
    for i, line in enumerate(lines):
        if line.strip().startswith("Academic") and "Very Important" in line and "Not Considered" in line:
            positions = find_heading_positions(line, C7_LABELS)
            for row in lines[i + 1 : i + 20]:
                clean = row.rstrip()
                for label, field in C7_FIELDS.items():
                    if clean.strip().startswith(label):
                        importance = pick_label_from_x(clean, positions)
                        if importance:
                            out[field] = {"importance": importance, "excerpt": clean.strip()}
            if out:
                return out
    return out


def parse_c8(text: str) -> dict[str, str]:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("C8A"):
            header_block = "\n".join(lines[i : i + 18])
            positions = []
            for label in C8_LABELS:
                idx = header_block.find(label)
                if idx >= 0:
                    positions.append((idx, label))
            if not positions:
                continue
            for row in lines[i : i + 22]:
                if row.strip().startswith("SAT or ACT"):
                    label = pick_label_from_x(row, positions)
                    if label:
                        return {"policy": label, "excerpt": row.strip()}
    return {}


def summarize_testing(short_name: str, parsed: dict[str, str]) -> str:
    policy = parsed.get("policy")
    if policy == "Required to be considered for admission":
        return f"{short_name} requires SAT or ACT scores to be considered for first-year admission according to its Common Data Set."
    if policy == "Required for some":
        return f"{short_name} reports in its Common Data Set that SAT or ACT scores are required for some first-year applicants."
    if policy == "Recommended":
        return f"{short_name} reports in its Common Data Set that SAT or ACT scores are recommended for first-year admission."
    if policy == "Not required for admission, but considered if submitted":
        return f"{short_name} reports in its Common Data Set that SAT or ACT scores are not required for admission but are considered if submitted."
    if policy == "Not considered for admission, even if submitted":
        return f"{short_name} reports in its Common Data Set that SAT or ACT scores are not considered for admission even if submitted."
    return ""


def summarize_course_rigor(short_name: str, importance: str) -> str:
    if importance == "Very Important":
        return f"{short_name}'s Common Data Set marks rigor of secondary school record as very important in first-year admissions decisions."
    if importance == "Important":
        return f"{short_name}'s Common Data Set marks rigor of secondary school record as important in first-year admissions decisions."
    if importance == "Considered":
        return f"{short_name}'s Common Data Set marks rigor of secondary school record as considered in first-year admissions decisions."
    return f"{short_name}'s Common Data Set marks rigor of secondary school record as not considered in general first-year admissions decisions."


def summarize_recommendations(short_name: str, importance: str) -> str:
    if importance == "Very Important":
        return f"{short_name}'s Common Data Set marks recommendations as very important in first-year admissions decisions."
    if importance == "Important":
        return f"{short_name}'s Common Data Set marks recommendations as important in first-year admissions decisions."
    if importance == "Considered":
        return f"{short_name}'s Common Data Set marks recommendations as considered in first-year admissions decisions."
    return f"{short_name}'s Common Data Set marks recommendations as not considered in general first-year admissions decisions."


def summarize_essays(short_name: str, importance: str) -> str:
    if importance == "Very Important":
        return f"{short_name}'s Common Data Set marks the application essay as very important in first-year admissions decisions."
    if importance == "Important":
        return f"{short_name}'s Common Data Set marks the application essay as important in first-year admissions decisions."
    if importance == "Considered":
        return f"{short_name}'s Common Data Set marks the application essay as considered in first-year admissions decisions."
    return f"{short_name}'s Common Data Set marks the application essay as not considered in general first-year admissions decisions."


def maybe_apply(record: dict[str, Any], cds_url: str, c7: dict[str, dict[str, str]], c8: dict[str, str]) -> dict[str, Any]:
    changed_fields: list[str] = []
    short_name = record.get("short_name") or record["name"]
    admissions = record.setdefault("admissions", {})
    source_urls = record.setdefault("source_urls", {})
    source_urls.setdefault("admissions", [])
    if cds_url not in source_urls["admissions"]:
        source_urls["admissions"].append(cds_url)
        source_urls["admissions"] = sorted(set(source_urls["admissions"]))

    if admissions.get("course_rigor") == "unknown" and "admissions.course_rigor" in c7:
        imp = c7["admissions.course_rigor"]["importance"]
        text = summarize_course_rigor(short_name, imp)
        admissions["course_rigor"] = text
        upsert_evidence(record, "admissions.course_rigor", text, "official_requirement", cds_url, c7["admissions.course_rigor"]["excerpt"])
        changed_fields.append("course_rigor")
    if admissions.get("recommendations") == "unknown" and "admissions.recommendations" in c7:
        imp = c7["admissions.recommendations"]["importance"]
        text = summarize_recommendations(short_name, imp)
        admissions["recommendations"] = text
        upsert_evidence(record, "admissions.recommendations", text, "official_requirement", cds_url, c7["admissions.recommendations"]["excerpt"])
        changed_fields.append("recommendations")
    if admissions.get("essays") == "unknown" and "admissions.essays" in c7:
        imp = c7["admissions.essays"]["importance"]
        text = summarize_essays(short_name, imp)
        admissions["essays"] = text
        upsert_evidence(record, "admissions.essays", text, "official_requirement", cds_url, c7["admissions.essays"]["excerpt"])
        changed_fields.append("essays")
    testing = admissions.get("testing_policy") or ""
    if (testing == "unknown" or "could not be confidently extracted" in testing.lower()) and c8.get("policy"):
        text = summarize_testing(short_name, c8)
        if text:
            admissions["testing_policy"] = text
            upsert_evidence(record, "admissions.testing_policy", text, "official_requirement", cds_url, c8["excerpt"])
            changed_fields.append("testing_policy")
    if changed_fields:
        remove_warning_contains(record, "testing policy needs manual confirmation")
        add_warning(record, f"Common Data Set repair filled {', '.join(changed_fields)} from an official institutional CDS source.")
        record.setdefault("verification", {})["confidence"] = "phase-6-cds-repair"
        record["verification"]["last_verified_at"] = now_iso()
        recompute_unknowns(record)
        save_record(record)
    return {"slug": record["slug"], "changed_fields": changed_fields, "cds_url": cds_url}


def main() -> int:
    results = []
    for path in sorted(UNI_DIR.glob("*.json"), key=lambda p: load_record(p).get("rank") or 999):
        record = load_record(path)
        unknowns = set(record.get("verification", {}).get("unknown_fields", []))
        if not unknowns.intersection({"admissions.course_rigor", "admissions.recommendations", "admissions.essays", "admissions.testing_policy"}):
            continue
        cds_url = discover_cds_url(record)
        if not cds_url:
            results.append({"slug": record["slug"], "changed_fields": [], "error": "no_cds_url"})
            continue
        try:
            text = fetch_text(cds_url)
            c7 = parse_c7(text)
            c8 = parse_c8(text)
            results.append(maybe_apply(record, cds_url, c7, c8))
        except Exception as exc:
            results.append({"slug": record["slug"], "changed_fields": [], "cds_url": cds_url, "error": str(exc)[:200]})
        time.sleep(0.2)
    changed = [r for r in results if r.get("changed_fields")]
    print(json.dumps({"processed": len(results), "changed": len(changed), "results": results[:80]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
