from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "knowledgebase" / "universities"


def _bullet_list(items: list[str]) -> str:
    if not items:
        return "- none"
    return "\n".join(f"- {item}" for item in items)


def _render_key_value_map(mapping: dict[str, Any]) -> str:
    if not mapping:
        return "- none"
    return "\n".join(f"- {key}: {value}" for key, value in mapping.items())


def _render_ranked_people(items: list[dict[str, Any]], kind: str) -> str:
    if not items:
        return "- none"

    lines: list[str] = []
    for item in items:
        if kind == "professor":
            stats = []
            if item.get("rating_count") is not None:
                stats.append(f"ratings={item['rating_count']}")
            if item.get("average_rating") is not None:
                stats.append(f"avg={item['average_rating']}")
            if item.get("would_take_again_percent") is not None:
                stats.append(f"would_take_again={item['would_take_again_percent']}%")
            if item.get("average_difficulty") is not None:
                stats.append(f"difficulty={item['average_difficulty']}")
            stats_text = f" ({', '.join(stats)})" if stats else ""
            department = f" — {item['department']}" if item.get("department") else ""
            lines.append(f"- #{item.get('rank', '?')} {item['name']}{department}{stats_text}")
            if item.get("bio"):
                lines.append(f"  - bio: {item['bio']}")
            if item.get("confirmation_url"):
                label = item.get("confirmation_label") or "confirmation"
                lines.append(f"  - {label}: {item['confirmation_url']}")
            if item.get("official_website"):
                lines.append(f"  - official website: {item['official_website']}")
            elif item.get("profile_url") and item.get("profile_url") != item.get("confirmation_url"):
                lines.append(f"  - profile: {item['profile_url']}")
        else:
            pageviews = item.get("recent_pageviews")
            pageviews_text = f" — recent_pageviews={pageviews}" if pageviews is not None else ""
            description = f" — {item['description']}" if item.get("description") else ""
            lines.append(f"- #{item.get('rank', '?')} {item['name']}{description}{pageviews_text}")
            if item.get("bio"):
                lines.append(f"  - bio: {item['bio']}")
            major_bits = []
            if item.get("major"):
                major_bits.append(f"major={item['major']}")
            if item.get("graduation_year"):
                major_bits.append(f"graduation_year={item['graduation_year']}")
            if item.get("within_last_10_years") is not None:
                major_bits.append(f"within_last_10_years={item['within_last_10_years']}")
            if major_bits:
                lines.append(f"  - {'; '.join(major_bits)}")
            if item.get("evidence_quality_label"):
                lines.append(f"  - evidence_quality={item['evidence_quality_label']}")
            if item.get("evidence_quality_note"):
                lines.append(f"  - evidence_note: {item['evidence_quality_note']}")
            if item.get("confirmation_url"):
                label = item.get("confirmation_label") or "confirmation"
                lines.append(f"  - {label}: {item['confirmation_url']}")
            if item.get("official_website"):
                lines.append(f"  - official website: {item['official_website']}")
            elif item.get("wikipedia_url") and item.get("wikipedia_url") != item.get("confirmation_url"):
                lines.append(f"  - wikipedia: {item['wikipedia_url']}")
    return "\n".join(lines)


def _render_by_major(by_major: dict[str, list[dict[str, Any]]]) -> str:
    if not by_major:
        return "- none"
    lines: list[str] = []
    for major, items in by_major.items():
        lines.append(f"- {major} ({len(items)})")
        for item in items:
            description = f" — {item['description']}" if item.get('description') else ""
            lines.append(f"  - #{item.get('rank', '?')} {item['name']}{description}")
    return "\n".join(lines)


def render_university_markdown(record: dict[str, Any]) -> str:
    source_urls = record.get("source_urls", {})
    verification = record.get("verification", {})
    admissions = record.get("admissions", {})
    majors = record.get("majors", {})
    school_people = record.get("school_people", {})
    popular_professors = school_people.get("popular_professors", {})
    successful_alumni = school_people.get("successful_alumni", {})

    sections = [
        "---",
        f"name: {record['name']}",
        f"short_name: {record['short_name']}",
        f"slug: {record['slug']}",
        f"rank: {record['rank']}",
        f"official_domain: {record['official_domain']}",
        f"status: {verification.get('confidence', 'unknown')}",
        "---",
        "",
        f"# {record['name']}",
        "",
        "## Official sources",
        "### Admissions",
        _bullet_list(source_urls.get("admissions", [])),
        "",
        "### Majors",
        _bullet_list(source_urls.get("majors", [])),
    ]

    if source_urls.get("professors"):
        sections.extend(["", "### Professors", _bullet_list(source_urls.get("professors", []))])
    if source_urls.get("alumni"):
        sections.extend(["", "### Alumni", _bullet_list(source_urls.get("alumni", []))])

    sections.extend(
        [
            "",
            "## Structured extraction",
            f"- Majors count: {majors.get('count')}",
            f"- Count method: {majors.get('count_method')}",
            f"- Testing policy: {admissions.get('testing_policy')}",
            f"- GPA policy: {admissions.get('gpa_policy')}",
            f"- Course rigor: {admissions.get('course_rigor')}",
            f"- Recommendations: {admissions.get('recommendations')}",
            f"- Essays: {admissions.get('essays')}",
        ]
    )

    if popular_professors.get("items") or successful_alumni.get("items"):
        sections.extend(["", "## School people"])
        if popular_professors.get("ranking_basis"):
            sections.append(f"- Popular professors basis: {popular_professors['ranking_basis']}")
        if popular_professors.get("target_count") is not None:
            sections.append(f"- Popular professors target count: {popular_professors['target_count']}")
        if successful_alumni.get("ranking_basis"):
            sections.append(f"- Successful alumni basis: {successful_alumni['ranking_basis']}")
        if successful_alumni.get("target_count") is not None:
            sections.append(f"- Successful alumni target count: {successful_alumni['target_count']}")
        if successful_alumni.get("recent_window_years") is not None:
            sections.append(f"- Recent alumni window requested: {successful_alumni['recent_window_years']} years")
        if successful_alumni.get("major_specific") is not None:
            sections.append(f"- Major specific alumni filtering enabled: {successful_alumni['major_specific']}")
        if successful_alumni.get("per_major_target_count") is not None:
            sections.append(f"- Per-major alumni target count: {successful_alumni['per_major_target_count']}")
        if successful_alumni.get("major_gap_counts"):
            sections.extend([
                "",
                "### Alumni per-major gaps",
                _render_key_value_map(successful_alumni.get("major_gap_counts", {})),
            ])
        if successful_alumni.get("evidence_quality_counts"):
            sections.extend([
                "",
                "### Alumni evidence quality counts",
                _render_key_value_map(successful_alumni.get("evidence_quality_counts", {})),
            ])
        if successful_alumni.get("by_major"):
            sections.extend([
                "",
                "### Alumni by major",
                _render_by_major(successful_alumni.get("by_major", {})),
            ])

        sections.extend(
            [
                "",
                "### Top professors",
                _render_ranked_people(popular_professors.get("items", []), kind="professor"),
                "",
                "### Top students / alumni",
                _render_ranked_people(successful_alumni.get("items", []), kind="alumni"),
            ]
        )

        combined_warnings = school_people.get("warnings", [])
        if combined_warnings:
            sections.extend(["", "### School people warnings", _bullet_list(combined_warnings)])

    unknowns = verification.get("unknown_fields", [])
    warnings = verification.get("warnings", [])
    if unknowns:
        sections.extend(["", "## Unknown fields", _bullet_list(unknowns)])
    if warnings:
        sections.extend(["", "## Warnings", _bullet_list(warnings)])

    return "\n".join(sections).rstrip() + "\n"


def write_university_markdown(record: dict[str, Any]) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{record['slug']}.md"
    path.write_text(render_university_markdown(record))
    return path
