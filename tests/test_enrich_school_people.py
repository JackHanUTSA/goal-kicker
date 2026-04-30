import unittest

from scripts.enrich_school_people import alumni_items_need_refresh, looks_like_person


class LooksLikePersonTests(unittest.TestCase):
    def test_rejects_non_people_with_role_substrings_inside_words(self):
        self.assertFalse(
            looks_like_person(
                {
                    "type": "standard",
                    "description": "Study of general and fundamental questions",
                    "titles": {"display": "Philosophy"},
                },
                "Philosophy",
            )
        )
        self.assertFalse(
            looks_like_person(
                {
                    "type": "standard",
                    "description": "Application of engineering principles and design concepts to medicine and biology",
                    "titles": {"display": "Biomedical engineering"},
                },
                "Biomedical engineering",
            )
        )

    def test_accepts_actual_people(self):
        self.assertTrue(
            looks_like_person(
                {
                    "type": "standard",
                    "description": "American economist (born 1980)",
                    "titles": {"display": "Emi Nakamura"},
                },
                "Emi Nakamura",
            )
        )

    def test_existing_alumni_items_with_non_people_trigger_refresh(self):
        self.assertTrue(
            alumni_items_need_refresh(
                [
                    {
                        "rank": 1,
                        "name": "Philosophy",
                        "bio": "Study of general and fundamental questions.",
                        "description": "Study of general and fundamental questions",
                        "confirmation_url": "https://en.wikipedia.org/wiki/Philosophy",
                    },
                    {
                        "rank": 2,
                        "name": "Emi Nakamura",
                        "bio": "Emi Nakamura is an American economist.",
                        "description": "American economist (born 1980)",
                        "confirmation_url": "https://en.wikipedia.org/wiki/Emi_Nakamura",
                    },
                ]
            )
        )


if __name__ == "__main__":
    unittest.main()
