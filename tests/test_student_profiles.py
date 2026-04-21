import unittest

from src.agent.student_profiles import build_profile, preset_student_profiles


class StudentProfileTests(unittest.TestCase):
    def test_preset_profiles_include_multiple_qualified_archetypes(self):
        profiles = preset_student_profiles()
        self.assertGreaterEqual(len(profiles), 4)
        self.assertIn("elite-math-researcher", {profile["slug"] for profile in profiles})
        self.assertTrue(all(0.0 <= profile["gpa_strength"] <= 1.0 for profile in profiles))
        self.assertTrue(all(0.0 <= profile["course_rigor"] <= 1.0 for profile in profiles))

    def test_build_profile_supports_missing_test_score(self):
        profile = build_profile(
            slug="custom-test-optional",
            name="Custom Test Optional",
            gpa_strength=0.95,
            course_rigor=0.9,
            research_interest=0.7,
            leadership=0.6,
            prefers_test_optional=True,
            test_strength=None,
        )
        self.assertIsNone(profile["test_strength"])
        self.assertTrue(profile["prefers_test_optional"])


if __name__ == "__main__":
    unittest.main()
