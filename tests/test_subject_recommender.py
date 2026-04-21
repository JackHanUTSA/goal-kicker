import unittest

from src.agent.subject_recommender import recommend_subject_schools
from src.agent.student_profiles import build_profile


class SubjectRecommenderTests(unittest.TestCase):
    def setUp(self):
        self.profile = build_profile(
            slug="elite",
            name="Elite",
            gpa_strength=0.99,
            test_strength=0.98,
            course_rigor=0.96,
            research_interest=0.95,
            leadership=0.7,
            prefers_test_optional=False,
        )

    def test_cs_recommender_boosts_computing_heavy_school(self):
        records = [
            {
                "name": "Carnegie Mellon University",
                "short_name": "Carnegie Mellon",
                "slug": "carnegie-mellon",
                "rank": 22,
                "official_domain": "cmu.edu",
                "majors": {"count": 95},
                "admissions": {"testing_policy": "This school requires the SAT or ACT."},
                "competitive_signals": {"projects_research": ["Research encouraged.", "Projects matter."]},
                "verification": {"confidence": "high", "unknown_fields": [], "warnings": []},
            },
            {
                "name": "Classic Liberal University",
                "short_name": "Classic U",
                "slug": "classic-u",
                "rank": 6,
                "official_domain": "classic.edu",
                "majors": {"count": 40},
                "admissions": {"testing_policy": "This school requires the SAT or ACT."},
                "competitive_signals": {"projects_research": []},
                "verification": {"confidence": "high", "unknown_fields": [], "warnings": []},
            },
        ]
        recommendations = recommend_subject_schools(records, self.profile, subject="cs", top_n=2)
        self.assertEqual(recommendations[0]["slug"], "carnegie-mellon")
        self.assertGreater(recommendations[0]["subject_bonus"], 0)

    def test_physics_recommender_boosts_caltech_like_school(self):
        records = [
            {
                "name": "California Institute of Technology",
                "short_name": "Caltech",
                "slug": "caltech",
                "rank": 6,
                "official_domain": "caltech.edu",
                "majors": {"count": 31},
                "admissions": {"testing_policy": "This school requires the SAT or ACT."},
                "competitive_signals": {"projects_research": ["Research is central.", "Independent inquiry matters."]},
                "verification": {"confidence": "high", "unknown_fields": [], "warnings": []},
            },
            {
                "name": "Large Optional State University",
                "short_name": "Large State",
                "slug": "large-state",
                "rank": 20,
                "official_domain": "large.edu",
                "majors": {"count": 120},
                "admissions": {"testing_policy": "This school is test-optional."},
                "competitive_signals": {"projects_research": []},
                "verification": {"confidence": "high", "unknown_fields": [], "warnings": []},
            },
        ]
        recommendations = recommend_subject_schools(records, self.profile, subject="physics", top_n=2)
        self.assertEqual(recommendations[0]["slug"], "caltech")
        self.assertGreater(recommendations[0]["subject_bonus"], 0)

    def test_math_subject_uses_base_math_behavior(self):
        records = [
            {
                "name": "Top Tech",
                "short_name": "Top Tech",
                "slug": "top-tech",
                "rank": 1,
                "official_domain": "toptech.edu",
                "majors": {"count": 60},
                "admissions": {"testing_policy": "Top Tech requires the SAT or the ACT."},
                "competitive_signals": {"projects_research": ["Research is central."]},
                "verification": {"confidence": "high", "unknown_fields": [], "warnings": []},
            },
        ]
        recommendations = recommend_subject_schools(records, self.profile, subject="math", top_n=1)
        self.assertEqual(recommendations[0]["subject"], "math")
        self.assertEqual(recommendations[0]["subject_bonus"], 0.0)


if __name__ == "__main__":
    unittest.main()
