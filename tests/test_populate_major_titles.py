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

    def test_fetch_page_does_not_false_positive_on_embedded_captcha_script_text(self):
        html = """
        <html>
          <head><title>Majors – Example University</title></head>
          <body>
            <main>
              <h1>Majors</h1>
              <p>Choose from dozens of undergraduate majors.</p>
              <script>var analytics = 'captcha';</script>
            </main>
          </body>
        </html>
        """
        page = populate_major_titles.fetch_page(
            FakeSession(FakeResponse(text=html, url="https://example.edu/majors")),
            "https://example.edu/majors",
        )

        self.assertIsNotNone(page)

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

    def test_extract_titles_from_page_reads_wake_forest_degree_cards(self):
        html = """
        <html><body><main>
          <div class="degree-list">
            <a href="/academics/majors-minors/accountancy/">
              <p class="major-name">Accountancy <span class="majorminor">Major, Minor</span></p>
            </a>
          </div>
          <div class="degree-list">
            <a href="/academics/majors-minors/african-studies/">
              <p class="major-name">African Studies <span class="majorminor">Minor</span></p>
            </a>
          </div>
        </main></body></html>
        """
        page = {
            "title": "Majors & Minors | Wake Forest",
            "url": "https://admissions.wfu.edu/academics/majors-minors/",
            "soup": BeautifulSoup(html, "lxml"),
        }
        record = {"slug": "wake-forest", "official_domain": "wfu.edu", "majors": {"count": 50}}

        titles = populate_major_titles.extract_titles_from_page(page, record)

        self.assertIn("Accountancy", titles)
        self.assertNotIn("African Studies", titles)

    def test_extract_titles_from_page_reads_university_of_washington_major_cards(self):
        html = """
        <html><body><main>
          <span id="majors-container">
            <div class="major"><div class="major-type"><h2><a href="/majors/aeronautics-astronautics/">Aeronautics &amp; Astronautics</a></h2></div></div>
            <div class="major"><div class="major-type"><h2><a href="/majors/anthropology/">Anthropology</a></h2></div></div>
          </span>
        </main></body></html>
        """
        page = {
            "title": "Majors – Office of Admissions",
            "url": "https://admit.washington.edu/academics/majors/",
            "soup": BeautifulSoup(html, "lxml"),
        }
        record = {"slug": "university-of-washington", "official_domain": "washington.edu", "majors": {"count": 180}}

        titles = populate_major_titles.extract_titles_from_page(page, record)

        self.assertEqual(titles[:2], ["Aeronautics & Astronautics", "Anthropology"])

    def test_extract_titles_from_page_reads_lmu_program_cards_with_bachelors(self):
        html = """
        <html><body><main>
          <a class="program-finder__results__item" data-item href="/program/accounting">
            <span class="program-finder__results__title">Accounting</span>
            <span class="program-finder__results__degrees">B.S. / M.S. / Minor</span>
          </a>
          <a class="program-finder__results__item" data-item href="/program/additive-manufacturing">
            <span class="program-finder__results__title">Additive Manufacturing Certificate</span>
            <span class="program-finder__results__degrees">Certificate</span>
          </a>
        </main></body></html>
        """
        page = {
            "title": "Degrees & Programs - Loyola Marymount University",
            "url": "https://www.lmu.edu/academics/degrees/",
            "soup": BeautifulSoup(html, "lxml"),
        }
        record = {"slug": "loyola-marymount", "official_domain": "lmu.edu", "majors": {"count": 60}}

        titles = populate_major_titles.extract_titles_from_page(page, record)

        self.assertIn("Accounting", titles)
        self.assertNotIn("Additive Manufacturing Certificate", titles)

    def test_extract_titles_from_page_reads_rice_catalog_links(self):
        html = """
        <html><body><main>
          <ul>
            <li><a href="https://ga.rice.edu/programs-study/departments-programs/engineering/computer-science/">Computer Science</a></li>
            <li><a href="https://ga.rice.edu/programs-study/departments-programs/humanities/history/">History</a></li>
            <li><a href="https://business.rice.edu/rice-mba/full-time-mba/deferred-enrollment">Rice MBA Deferred Enrollment Program</a></li>
          </ul>
        </main></body></html>
        """
        page = {
            "title": "Majors, Minors and Programs | Rice University",
            "url": "https://www.rice.edu/majors-minors-and-programs",
            "soup": BeautifulSoup(html, "lxml"),
        }
        record = {"slug": "rice", "official_domain": "rice.edu", "majors": {"count": 50}}

        titles = populate_major_titles.extract_titles_from_page(page, record)

        self.assertIn("Computer Science", titles)
        self.assertIn("History", titles)
        self.assertNotIn("Rice MBA Deferred Enrollment Program", titles)

    def test_extract_titles_from_page_reads_santa_clara_major_cards(self):
        html = """
        <html><body><main>
          <div class="card h-100">
            <div class="card-body">
              <h2 class="card-title">Anthropology</h2>
              <p>Major: Anthropology<br/>Minor: Anthropology</p>
            </div>
          </div>
          <div class="card h-100">
            <div class="card-body">
              <h2 class="card-title">Art &amp; Art History</h2>
              <p>Majors: Art History, Studio Art<br/>Minors: Art History, Studio Art</p>
            </div>
          </div>
          <div class="card h-100">
            <div class="card-body">
              <h2 class="card-title">Asian Studies</h2>
              <p>Minor: Asian Studies</p>
            </div>
          </div>
        </main></body></html>
        """
        page = {
            "title": "Undergraduate Majors and Minors - Santa Clara University",
            "url": "https://www.scu.edu/cas/academics/undergraduate-majors-and-minors/",
            "soup": BeautifulSoup(html, "lxml"),
        }
        record = {"slug": "santa-clara", "official_domain": "scu.edu", "majors": {"count": 50}}

        titles = populate_major_titles.extract_titles_from_page(page, record)

        self.assertIn("Anthropology", titles)
        self.assertIn("Art History", titles)
        self.assertIn("Studio Art", titles)
        self.assertNotIn("Asian Studies", titles)

    def test_extract_titles_from_page_reads_ucsd_majors_section(self):
        html = """
        <html><body><main>
          <h2>Majors:</h2>
          <p>Astronomy &amp; Astrophysics Astronomy &amp; Astrophysics (B.S.)♦ Astrophysical Sciences (B.S.)♦</p>
          <p>Anthropology Anthropology (Archaeology) (B.A.) Anthropology (Biological Anthropology) (B.A.)</p>
          <h2>Majors/Minors</h2>
        </main></body></html>
        """
        page = {
            "title": "Undergraduate Majors at UC San Diego",
            "url": "https://students.ucsd.edu/academics/advising/majors-minors/undergraduate-majors.html",
            "soup": BeautifulSoup(html, "lxml"),
        }
        record = {"slug": "uc-san-diego", "official_domain": "ucsd.edu", "majors": {"count": 100}}

        titles = populate_major_titles.extract_titles_from_page(page, record)

        self.assertIn("Astronomy & Astrophysics", titles)
        self.assertIn("Astrophysical Sciences", titles)
        self.assertIn("Anthropology (Archaeology)", titles)
        self.assertIn("Anthropology (Biological Anthropology)", titles)

    def test_extract_titles_from_page_reads_mines_bachelor_headings(self):
        html = """
        <html><body><main>
          <h3>Bachelor of Science in Applied Mathematics and Statistics</h3>
          <h2>Bachelor of Science in BUSINESS ENGINEERING AND MANAGEMENT SCIENCE</h2>
          <h3>Minor Program in Economics</h3>
        </main></body></html>
        """
        page = {
            "title": "Applied Mathematics and Statistics | Colorado School of Mines Catalog",
            "url": "https://catalog.mines.edu/undergraduate/programs/ams/",
            "soup": BeautifulSoup(html, "lxml"),
        }
        record = {"slug": "colorado-school-of-mines", "official_domain": "mines.edu", "majors": {"count": 18}}

        titles = populate_major_titles.extract_titles_from_page(page, record)

        self.assertIn("Applied Mathematics and Statistics", titles)
        self.assertIn("BUSINESS ENGINEERING AND MANAGEMENT SCIENCE", titles)
        self.assertNotIn("Economics", titles)

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
