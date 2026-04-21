import unittest

from src.agent.math_recommender import recommend_math_schools
from src.agent.student_profiles import build_profile


class MathRecommenderTests(unittest.TestCase):
    def test_recommender_prefers_complete_strong_math_school_for_elite_profile(self):
        records = [
            {
                "name": "Top Tech",
                "short_name": "Top Tech",
                "slug": "top-tech",
                "rank": 1,
                "official_domain": "toptech.edu",
                "majors": {"count": 60},
                "admissions": {"testing_policy": "Top Tech requires the SAT or the ACT."},
                "competitive_signals": {"projects_research": ["Research is central.", "Independent projects matter."]},
                "verification": {"confidence": "high", "unknown_fields": [], "warnings": []},
            },
            {
                "name": "Unknown College",
                "short_name": "Unknown",
                "slug": "unknown-college",
                "rank": 4,
                "official_domain": "unknown.edu",
                "majors": {"count": None},
                "admissions": {"testing_policy": "unknown"},
                "competitive_signals": {"projects_research": []},
                "verification": {"confidence": "low", "unknown_fields": ["majors.count"], "warnings": ["limited data"]},
            },
        ]
        profile = build_profile(
            slug="elite",
            name="Elite",
            gpa_strength=0.99,
            test_strength=0.98,
            course_rigor=0.95,
            research_interest=0.95,
            leadership=0.7,
            prefers_test_optional=False,
        )
        recommendations = recommend_math_schools(records, profile, top_n=2)
        self.assertEqual(recommendations[0]["slug"], "top-tech")
        self.assertGreater(recommendations[0]["fit_score"], recommendations[1]["fit_score"])

    def test_recommender_penalizes_required_testing_when_student_has_no_test(self):
        records = [
            {
                "name": "Required Test Institute",
                "short_name": "Required Test",
                "slug": "required-test",
                "rank": 3,
                "official_domain": "required.edu",
                "majors": {"count": 50},
                "admissions": {"testing_policy": "This school requires the SAT or ACT."},
                "competitive_signals": {"projects_research": ["Research encouraged."]},
                "verification": {"confidence": "high", "unknown_fields": [], "warnings": []},
            },
            {
                "name": "Optional Test University",
                "short_name": "Optional Test",
                "slug": "optional-test",
                "rank": 6,
                "official_domain": "optional.edu",
                "majors": {"count": 40},
                "admissions": {"testing_policy": "This school is test-optional."},
                "competitive_signals": {"projects_research": ["Projects valued."]},
                "verification": {"confidence": "high", "unknown_fields": [], "warnings": []},
            },
        ]
        profile = build_profile(
            slug="no-test",
            name="No Test Student",
            gpa_strength=0.95,
            test_strength=None,
            course_rigor=0.9,
            research_interest=0.8,
            leadership=0.7,
            prefers_test_optional=True,
        )
        recommendations = recommend_math_schools(records, profile, top_n=2)
        self.assertEqual(recommendations[0]["slug"], "optional-test")


if __name__ == "__main__":
    unittest.main()
