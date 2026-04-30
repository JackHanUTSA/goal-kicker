# People Overrides

School-specific official-source overrides for Goal Kicker people enrichment.

Each file is named:
- `<school-slug>.json`

Example supported sections:
- `popular_professors`
- `successful_alumni`

These overrides are applied before the generic fallback pipeline.
If override items exist, the generic RateMyProfessors/Wikipedia item generation is skipped for that section.

Minimal shape:

```json
{
  "popular_professors": {
    "ranking_basis": "Official faculty directory ...",
    "source_summary": "Extracted from official school domain faculty pages.",
    "retrieved_at": "2026-04-25T00:00:00+00:00",
    "target_count": 20,
    "source_urls": ["https://example.edu/faculty"],
    "items": [
      {
        "rank": 1,
        "name": "Professor Name",
        "department": "Mathematics",
        "bio": "Short bio",
        "average_rating": null,
        "rating_count": null,
        "would_take_again_percent": null,
        "average_difficulty": null,
        "legacy_id": null,
        "profile_url": "https://example.edu/faculty/professor-name",
        "official_website": "https://example.edu/faculty/professor-name",
        "confirmation_url": "https://example.edu/faculty/professor-name",
        "confirmation_label": "Official faculty profile",
        "source_url": "https://example.edu/faculty",
        "source_confidence": "high"
      }
    ]
  },
    "successful_alumni": {
      "ranking_basis": "Official alumni / placement pages ...",
      "source_summary": "Extracted from official school domain alumni pages.",
      "retrieved_at": "2026-04-25T00:00:00+00:00",
      "target_count": 20,
      "recent_window_years": 10,
      "major_specific": true,
      "per_major_target_count": 10,
      "major_gap_counts": {
        "Mathematics": 9
      },
      "evidence_quality_counts": {
"official_profile": 12,
      "official_roster": 6,
      "near_term_student_profile": 2
    },
    "by_major": {
      "Mathematics": [
        {
          "rank": 1,
          "name": "Alum Name",
          "bio": "Short bio or first position",
          "description": "Researcher / professor / founder",
          "wikipedia_title": null,
          "wikipedia_url": null,
          "confirmation_url": "https://example.edu/alumni/alum-name",
          "confirmation_label": "Official alumni profile",
          "official_website": null,
          "recent_pageviews": null,
          "major": "Mathematics",
          "graduation_year": 2024,
          "within_last_10_years": true,
          "evidence_quality_label": "official_profile",
          "evidence_quality_note": "Official person-specific alumni or news profile with explicit degree/year evidence.",
          "source_url": "https://example.edu/alumni",
          "source_confidence": "high"
        }
      ]
    },
    "source_urls": ["https://example.edu/alumni"],
    "items": [
      {
        "rank": 1,
        "name": "Alum Name",
        "bio": "Short bio or first position",
        "description": "Researcher / professor / founder",
        "wikipedia_title": null,
        "wikipedia_url": null,
        "confirmation_url": "https://example.edu/alumni/alum-name",
        "confirmation_label": "Official alumni profile",
        "official_website": null,
        "recent_pageviews": null,
        "major": "Mathematics",
        "graduation_year": 2024,
        "within_last_10_years": true,
        "evidence_quality_label": "official_profile",
        "evidence_quality_note": "Official person-specific alumni or news profile with explicit degree/year evidence.",
        "source_url": "https://example.edu/alumni",
        "source_confidence": "high"
      }
    ]
  }
}
```
