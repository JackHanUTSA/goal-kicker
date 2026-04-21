import unittest

from src.agent.admissions_strategy import admissions_landscape_2026, build_admissions_strategy


class AdmissionsStrategyTests(unittest.TestCase):
    def test_landscape_exposes_core_sections(self):
        landscape = admissions_landscape_2026()
        self.assertIn("timeline_options", landscape)
        self.assertIn("holistic_review", landscape)
        self.assertIn("financial_aid", landscape)
        self.assertIn("international_student_flow", landscape)
        self.assertEqual(landscape["timeline_options"]["early-decision"]["label"], "Early Decision")

    def test_early_decision_with_aid_warns_about_tradeoff(self):
        plan = build_admissions_strategy(
            application_round="early-decision",
            testing_category="required",
            needs_financial_aid=True,
            student_region="domestic",
        )
        self.assertIn("binding", plan["timeline"]) 
        self.assertTrue(plan["timeline"]["binding"])
        joined = " ".join(plan["strategy_notes"]).lower()
        self.assertIn("compare offers", joined)
        self.assertIn("requires testing", plan["testing_strategy"].lower())

    def test_international_strategy_includes_visa_steps(self):
        plan = build_admissions_strategy(
            application_round="regular-decision",
            testing_category="test-optional",
            needs_financial_aid=False,
            student_region="international",
        )
        self.assertTrue(plan["international_strategy"]["needed"])
        self.assertIn("Form I-20 issuance", plan["international_strategy"]["steps"])
        self.assertIn("strategic", plan["testing_strategy"].lower())


if __name__ == "__main__":
    unittest.main()
