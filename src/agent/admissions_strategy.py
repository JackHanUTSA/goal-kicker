from __future__ import annotations

from typing import Any, Literal

ApplicationRound = Literal["early-decision", "early-action", "regular-decision"]
TestingCategory = Literal["required", "test-optional", "test-flexible", "unclear"]
StudentRegion = Literal["domestic", "international"]

TIMELINE_OPTIONS: dict[str, dict[str, Any]] = {
    "early-action": {
        "label": "Early Action",
        "binding": False,
        "typical_deadline": "around November 1",
        "typical_notification": "mid-December to mid-February",
        "best_for": "students who want early clarity without committing to one school",
        "tradeoff": "still requires early preparation, but keeps application choice flexibility",
    },
    "early-decision": {
        "label": "Early Decision",
        "binding": True,
        "typical_deadline": "around November 1",
        "typical_notification": "mid-December to mid-February",
        "best_for": "students with a crystal-clear first-choice school who are comfortable with a binding commitment",
        "tradeoff": "accepted students usually cannot compare multiple aid packages before committing",
    },
    "regular-decision": {
        "label": "Regular Decision",
        "binding": False,
        "typical_deadline": "mid-December to mid-January, sometimes into February",
        "typical_notification": "mid-March to mid-April",
        "best_for": "students who need more time for essays, senior-year grades, testing, or aid comparison",
        "tradeoff": "less of an early-round timing advantage at many selective schools",
    },
}

HOLISTIC_REVIEW = {
    "hard_factors": [
        "GPA",
        "course rigor, especially AP/IB/honors in the context available at the student's school",
        "standardized testing when required or strategically useful",
    ],
    "soft_factors": [
        "personal statement and supplements",
        "extracurricular depth and leadership",
        "letters of recommendation",
        "demonstrated interest and school-specific fit signals",
    ],
    "context_and_fit": [
        "admissions readers evaluate students relative to opportunity, not just raw metrics",
        "work, family responsibilities, or unusual constraints can matter when they reveal maturity, initiative, or character",
        "similarly qualified students are often separated by fit, context, and the credibility of their overall story",
    ],
}

TESTING_GUIDANCE = {
    "fall_2026_snapshot": "NotebookLM synthesis reported that 2,088 of 2,248 confirmed ranked four-year colleges (92.8%) remain test-optional or test-free for Fall 2026, even as some elite schools reinstate testing.",
    "student_rule": "Submit scores when they are required, or when strong scores sit within or above a target school's middle-50% range and materially strengthen the application.",
    "categories": {
        "required": "This school path currently requires testing, so exam prep must happen early.",
        "test-optional": "Testing is not mandatory here, so score submission should be strategic rather than automatic.",
        "test-flexible": "This policy still expects some form of testing evidence, so students should confirm accepted pathways early.",
        "unclear": "The policy is unresolved or not yet verified here, so students should confirm the current rule directly from the school.",
    },
}

FINANCIAL_AID = {
    "fafsa": [
        "covers federal and many state aid pathways",
        "free to submit",
        "uses federal methodology",
    ],
    "css_profile": [
        "used by many schools for institutional aid",
        "paid submission",
        "often asks for more detailed family financial information, sometimes including home equity and non-custodial parent details",
    ],
    "strategy_note": "Aid methodology changes application strategy. Students who need to compare offers should be warned that binding Early Decision can reduce aid-comparison flexibility.",
}

INTERNATIONAL_STUDENT_FLOW = {
    "visa_routes": [
        "F-1 is the standard path for academic study",
        "M-1 is generally for vocational study",
    ],
    "steps": [
        "admission to a SEVP-approved school",
        "SEVIS registration and I-901 fee",
        "Form I-20 issuance",
        "DS-160 application and visa interview",
    ],
    "timing_note": "Students generally cannot enter the U.S. more than 30 days before the program start date.",
}

EARLY_ROUND_EDGE = [
    {"school": "Brown", "early_acceptance_rate": "12.98%", "regular_acceptance_rate": "3.88%"},
    {"school": "Columbia", "early_acceptance_rate": "11.33%", "regular_acceptance_rate": "2.82%"},
    {"school": "Harvard", "early_acceptance_rate": "7.56%", "regular_acceptance_rate": "2.75%"},
    {"school": "Yale", "early_acceptance_rate": "10.3%", "regular_acceptance_rate": "3.37%"},
]


def admissions_landscape_2026() -> dict[str, Any]:
    return {
        "summary": {
            "student_flow": [
                "choose timeline strategy",
                "understand holistic review",
                "set a student profile",
                "compare schools",
                "inspect evidence and unresolved gaps",
            ],
            "key_takeaways": [
                "most schools remain test-optional or test-free overall, but some elite schools require tests again",
                "early rounds can provide a real edge at selective schools",
                "binding early decision should be recommended carefully when aid comparison matters",
                "financial aid and international logistics should be surfaced early because they change strategy, not just paperwork",
            ],
        },
        "timeline_options": TIMELINE_OPTIONS,
        "holistic_review": HOLISTIC_REVIEW,
        "testing_guidance": TESTING_GUIDANCE,
        "financial_aid": FINANCIAL_AID,
        "international_student_flow": INTERNATIONAL_STUDENT_FLOW,
        "early_round_examples": EARLY_ROUND_EDGE,
    }


def _testing_strategy(testing_category: str) -> str:
    category = str(testing_category or "unclear").strip().lower()
    normalized = {
        "optional": "test-optional",
        "test optional": "test-optional",
        "test-optional": "test-optional",
        "required": "required",
        "test required": "required",
        "test-flexible": "test-flexible",
        "flexible": "test-flexible",
        "unclear": "unclear",
        "unknown": "unclear",
        "unresolved": "unclear",
    }.get(category, "unclear")
    return TESTING_GUIDANCE["categories"][normalized]


def build_admissions_strategy(
    *,
    application_round: str,
    testing_category: str,
    needs_financial_aid: bool,
    student_region: str,
) -> dict[str, Any]:
    timeline_key = str(application_round or "regular-decision").strip().lower()
    timeline = TIMELINE_OPTIONS.get(timeline_key, TIMELINE_OPTIONS["regular-decision"])
    region = "international" if str(student_region or "domestic").strip().lower() == "international" else "domestic"

    strategy_notes: list[str] = [
        f"{timeline['label']} is best for {timeline['best_for']}.",
        f"Typical deadline: {timeline['typical_deadline']}; typical notification: {timeline['typical_notification']}.",
        _testing_strategy(testing_category),
        "Students should treat essays, recommendations, activities, and context as core parts of the application, not side details.",
    ]

    if timeline_key == "early-decision":
        strategy_notes.append("Use Early Decision only when the student truly has a first-choice school and understands the binding commitment.")
        if needs_financial_aid:
            strategy_notes.append("Because this student needs aid, explicitly warn that Early Decision can reduce the ability to compare offers.")
    elif timeline_key == "early-action":
        strategy_notes.append("Early Action gives earlier feedback without forcing a final commitment, which makes it a safer default early-round strategy for many students.")
    else:
        strategy_notes.append("Regular Decision is the safer path when a student needs more time, wants broader comparison, or is still shaping the final school list.")

    if needs_financial_aid:
        strategy_notes.append("Discuss FAFSA and CSS Profile early so the student understands which aid systems each school may require.")

    if region == "international":
        strategy_notes.append("International applicants should plan for visa logistics early: SEVIS, I-20, DS-160, and interview timing can affect the application timeline.")

    return {
        "application_round": timeline_key,
        "student_region": region,
        "needs_financial_aid": bool(needs_financial_aid),
        "timeline": timeline,
        "testing_strategy": _testing_strategy(testing_category),
        "financial_aid_strategy": (
            FINANCIAL_AID["strategy_note"] if needs_financial_aid else "Aid comparison flexibility is less central here, but schools may still use different aid methodologies."
        ),
        "international_strategy": (
            {
                "needed": True,
                "visa_routes": INTERNATIONAL_STUDENT_FLOW["visa_routes"],
                "steps": INTERNATIONAL_STUDENT_FLOW["steps"],
                "timing_note": INTERNATIONAL_STUDENT_FLOW["timing_note"],
            }
            if region == "international"
            else {
                "needed": False,
                "note": "Domestic student path selected; international visa workflow does not apply.",
            }
        ),
        "holistic_review_prompt": "Frame the student as a whole person: academics, initiative, recommendations, essays, and context all matter.",
        "strategy_notes": strategy_notes,
    }
