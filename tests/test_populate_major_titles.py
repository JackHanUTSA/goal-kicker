import importlib.util
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "populate_major_titles.py"
SPEC = importlib.util.spec_from_file_location("populate_major_titles", MODULE_PATH)
populate_major_titles = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(populate_major_titles)


class FakeResponse:
    def __init__(self, *, status_code=200, text="<html></html>", url="https://example.edu/page", content_type="text/html"):
        self.status_code = status_code
        self.text = text
        self.url = url
        self.headers = {"content-type": content_type}


class FakeSession:
    def __init__(self, response):
        self.response = response

    def get(self, *args, **kwargs):
        return self.response


class PopulateMajorTitlesTests(unittest.TestCase):
    def test_extract_titles_from_page_keeps_bachelors_and_drops_other_gatech_degrees(self):
        html = """
        <html><body><main>
          <h2>Main navigation</h2>
          <a href="/academics/degrees/bachelors/ignore-me">Explore Degrees and Majors</a>
          <a href="/academics/degrees/bachelors/aerospace-engineering-bs">Aerospace Engineering (BS)</a>
          <a href="/academics/degrees/masters/aerospace-engineering-ms">Aerospace Engineering (MS)</a>
          <a href="/academics/degrees/phd/biology-phd">Biology (Ph.D.)</a>
          <a href="/academics/degrees/bachelors/biology-minor">Biology (Minor)</a>
          <a href="/academics/degrees/bachelors/biochemistry-bs">Biochemistry (BS)</a>
        </main></body></html>
        """
        page = {
            "title": "Majors and Degrees | Georgia Tech",
            "url": "https://www.gatech.edu/academics/all-degree-programs",
            "soup": BeautifulSoup(html, "lxml"),
        }
        record = {"slug": "georgia-tech", "official_domain": "gatech.edu", "majors": {"count": 21}}

        titles = populate_major_titles.extract_titles_from_page(page, record)

        self.assertIn("Aerospace Engineering", titles)
        self.assertIn("Biochemistry", titles)
        self.assertNotIn("Biology", titles)
        self.assertNotIn("Main navigation", titles)
        self.assertEqual(titles.count("Aerospace Engineering"), 1)

    def test_extract_titles_from_page_reads_catalog_cards_with_major_type_labels(self):
        html = """
        <html><body><main>
          <li class="item filter_22 filter_29">
            <div class="item-container">
              <div class="text-container">
                <div class="text--title">
                  <span class="title">Computer Science</span>
                  <span class="type">major | UF Online</span>
                </div>
                <div class="description">
                  <p><a class="learn-more" href="/UGRD/colleges-schools/UGLAS/CSC_BS_UFO/">Learn more</a></p>
                </div>
              </div>
            </div>
          </li>
          <li class="item filter_23 filter_29">
            <div class="item-container">
              <div class="text-container">
                <div class="text--title">
                  <span class="title">Business Administration</span>
                  <span class="type">minor</span>
                </div>
              </div>
            </div>
          </li>
        </main></body></html>
        """
        page = {
            "title": "Programs | UF",
            "url": "https://catalog.ufl.edu/UGRD/programs/",
            "soup": BeautifulSoup(html, "lxml"),
        }
        record = {"slug": "uf", "official_domain": "ufl.edu", "majors": {"count": 300}}

        titles = populate_major_titles.extract_titles_from_page(page, record)

        self.assertIn("Computer Science", titles)
        self.assertNotIn("Business Administration", titles)

    def test_fetch_page_ignores_http_error_pages(self):
        page = populate_major_titles.fetch_page(
            FakeSession(FakeResponse(status_code=404, text="<html><title>Missing</title></html>")),
            "https://example.edu/missing",
        )

        self.assertIsNone(page)

    def test_crawl_school_prioritizes_discovered_links_before_generic_seed_urls(self):
        original_candidate_urls = populate_major_titles.candidate_urls
        original_fetch_page = populate_major_titles.fetch_page
        original_relevant_links = populate_major_titles.relevant_links
        original_max_pages = populate_major_titles.MAX_PAGES
        original_sleep = populate_major_titles.time.sleep
        original_session = populate_major_titles.requests.Session

        try:
            populate_major_titles.MAX_PAGES = 3
            populate_major_titles.time.sleep = lambda *_args, **_kwargs: None
            populate_major_titles.requests.Session = lambda: object()
            populate_major_titles.candidate_urls = lambda _record: [
                "https://example.edu/academics",
                "https://example.edu/generic-1",
                "https://example.edu/generic-2",
            ]

            page_map = {
                "https://example.edu/academics": {"url": "https://example.edu/academics", "soup": BeautifulSoup("<html></html>", "lxml"), "title": "Academics", "status_code": 200},
                "https://example.edu/focused-programs": {"url": "https://example.edu/focused-programs", "soup": BeautifulSoup("<html></html>", "lxml"), "title": "Programs", "status_code": 200},
                "https://example.edu/generic-1": {"url": "https://example.edu/generic-1", "soup": BeautifulSoup("<html></html>", "lxml"), "title": "Generic 1", "status_code": 200},
                "https://example.edu/generic-2": {"url": "https://example.edu/generic-2", "soup": BeautifulSoup("<html></html>", "lxml"), "title": "Generic 2", "status_code": 200},
            }
            populate_major_titles.fetch_page = lambda _session, url: page_map.get(url)
            populate_major_titles.relevant_links = lambda page, _domain: ["https://example.edu/focused-programs"] if page["url"].endswith("/academics") else []

            pages = populate_major_titles.crawl_school({"official_domain": "example.edu"})

            crawled_urls = [page["url"] for page in pages]
            self.assertEqual(crawled_urls[:2], [
                "https://example.edu/academics",
                "https://example.edu/focused-programs",
            ])
        finally:
            populate_major_titles.candidate_urls = original_candidate_urls
            populate_major_titles.fetch_page = original_fetch_page
            populate_major_titles.relevant_links = original_relevant_links
            populate_major_titles.MAX_PAGES = original_max_pages
            populate_major_titles.time.sleep = original_sleep
            populate_major_titles.requests.Session = original_session

    def test_extract_titles_from_page_reads_duke_plaintext_major_section(self):
        html = """
        <html><body><main>
          <h3>Majors</h3>
          <div class="desc body-text-lg">
            <p>
              -African &amp; African American Studies<br/>
              -Biology<br/>
              -Visual &amp; Media Studies: Cinematic Arts**<br/>
              **Only available as a second major.
            </p>
          </div>
        </main></body></html>
        """
        page = {
            "title": "Academic Possibilities | Duke",
            "url": "https://admissions.duke.edu/academic-possibilities/",
            "soup": BeautifulSoup(html, "lxml"),
        }
        record = {"slug": "duke", "official_domain": "duke.edu", "majors": {"count": 63}}

        titles = populate_major_titles.extract_titles_from_page(page, record)

        self.assertIn("African & African American Studies", titles)
        self.assertIn("Biology", titles)
        self.assertIn("Visual & Media Studies: Cinematic Arts", titles)
        self.assertNotIn("Only available as a second major.", titles)

    def test_extract_titles_from_page_reads_rutgers_accordion_program_titles(self):
        html = """
        <html><body><main>
          <li class="views-row accordion-list-item">
            <div class="program">
              <button class="accordion-trigger"><h3>Accounting</h3></button>
              <table class="program-data">
                <tr class="program_implementation">
                  <td>Rutgers-New Brunswick</td>
                  <td>Business School</td>
                  <td><a href="/undergraduate-new-brunswick/accounting">Learn More</a></td>
                </tr>
              </table>
            </div>
          </li>
          <li class="views-row accordion-list-item">
            <div class="program">
              <button class="accordion-trigger"><h3>Nursing</h3></button>
              <table class="program-data">
                <tr class="program_implementation">
                  <td>Rutgers-Camden</td>
                  <td>Nursing School</td>
                  <td><a href="/undergraduate-camden/nursing">Learn More</a></td>
                </tr>
              </table>
            </div>
          </li>
        </main></body></html>
        """
        page = {
            "title": "Explore Undergraduate Programs | Rutgers",
            "url": "https://www.rutgers.edu/academics/explore-undergraduate-programs?field_location=654",
            "soup": BeautifulSoup(html, "lxml"),
        }
        record = {"slug": "rutgers-new-brunswick", "official_domain": "rutgers.edu", "majors": {"count": 120}}

        titles = populate_major_titles.extract_titles_from_page(page, record)

        self.assertIn("Accounting", titles)
        self.assertNotIn("Nursing", titles)

    def test_relevant_links_skips_noisy_program_pages(self):
        html = """
        <html><body>
          <a href="/academics/program-finder">Program Finder</a>
          <a href="/study-abroad/programs">Study Abroad Programs</a>
          <a href="/family-programs/resources">Family Programs</a>
          <a href="/graduate/programs">Graduate Programs</a>
        </body></html>
        """
        page = {
            "url": "https://example.edu/academics",
            "soup": BeautifulSoup(html, "lxml"),
        }

        links = populate_major_titles.relevant_links(page, "example.edu")

        self.assertIn("https://example.edu/academics/program-finder", links)
        self.assertNotIn("https://example.edu/study-abroad/programs", links)
        self.assertNotIn("https://example.edu/family-programs/resources", links)
        self.assertNotIn("https://example.edu/graduate/programs", links)


if __name__ == "__main__":
    unittest.main()
