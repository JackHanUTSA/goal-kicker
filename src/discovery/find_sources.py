from __future__ import annotations

from typing import Any


def guess_official_urls(seed: dict[str, Any]) -> dict[str, Any]:
    domain = seed["official_domain"].strip()
    root = f"https://www.{domain}"
    return {
        "official_domain": domain,
        "root_url": root,
        "candidate_urls": {
            "admissions": [
                f"{root}/admissions",
                f"{root}/admission",
                f"{root}/apply",
            ],
            "majors": [
                f"{root}/academics",
                f"{root}/academic-programs",
                f"{root}/majors",
                f"{root}/undergraduate/programs",
            ],
            "general": [root],
        },
    }
