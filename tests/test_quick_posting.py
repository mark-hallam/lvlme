"""LVLme quick's posting fetcher, offline: saved Greenhouse, Ashby, Lever and Workday API responses and a saved page."""
import io
import os
import unittest
import urllib.error
from unittest import mock

import helpers as H
import quick_posting as Q
import validate as V

FX = os.path.join(H.FIXTURES, "quick")
GH = "https://job-boards.greenhouse.io/acmeai/jobs/4200001"
ASHBY = "https://jobs.ashbyhq.com/globex/0b6f3c2e-1a2b-4c3d-8e9f-000000000001"
LEVER = "https://jobs.lever.co/initech/7c1d2e3f-4a5b-4c6d-9e8f-000000000101"
WORKDAY = ("https://globex.wd3.myworkdayjobs.com/en-AU/Globex_Careers/job/Australia-NSW-Sydney/"
           "Senior-Program-Manager--Fleet-Rollouts_JR0004242")


def fx(name):
    return os.path.join(FX, name)


def schema_errors(role):
    doc = {"schema_version": 1, "fetched_on": "2026-11-02", "summary": {"matched_total": 1}, "roles": [role]}
    return V.check(doc, H.schema("roles.schema.json"))


class LinkTests(unittest.TestCase):
    def test_board_links(self):
        self.assertEqual(Q.parse_link(GH), {"ats": "greenhouse", "board": "acmeai", "job_id": "4200001", "region": None})
        self.assertEqual(Q.parse_link("https://boards.greenhouse.io/acmeai/jobs/4200001?gh_src=x")["job_id"], "4200001")
        embed = Q.parse_link("https://boards.greenhouse.io/embed/job_app?for=acmeai&token=4200001")
        self.assertEqual((embed["board"], embed["job_id"]), ("acmeai", "4200001"))
        ashby = Q.parse_link(ASHBY.replace("0b6f3c2e", "0B6F3C2E") + "/application")  # ids are matched in lower case
        self.assertEqual((ashby["ats"], ashby["job_id"]), ("ashby", "0b6f3c2e-1a2b-4c3d-8e9f-000000000001"))
        lever = Q.parse_link(LEVER.replace("jobs.lever.co", "jobs.eu.lever.co") + "/apply")
        self.assertEqual((lever["ats"], lever["region"]), ("lever", "eu"))
        self.assertEqual(Q.parse_link("https://careers.example.com/jobs/123")["ats"], "page")

    def test_api_addresses(self):
        self.assertEqual(Q.api_url(Q.parse_link(GH)), "https://boards-api.greenhouse.io/v1/boards/acmeai/jobs/4200001")
        self.assertEqual(Q.api_url(Q.parse_link(ASHBY)),
                         "https://api.ashbyhq.com/posting-api/job-board/globex?includeCompensation=true")
        self.assertEqual(Q.api_url(Q.parse_link(LEVER)),
                         "https://api.lever.co/v0/postings/initech/7c1d2e3f-4a5b-4c6d-9e8f-000000000101")
        eu = Q.parse_link(LEVER.replace("jobs.lever.co", "jobs.eu.lever.co"))
        self.assertTrue(Q.api_url(eu).startswith("https://api.eu.lever.co/"))

    def test_linkedin_and_bad_links_refused(self):
        for bad in ("https://www.linkedin.com/jobs/view/123", "https://au.linkedin.com/jobs/view/9", "https://lnkd.in/abc"):
            with self.assertRaises(Q.PostingError) as cm:
                Q.parse_link(bad)
            self.assertIn("never opens LinkedIn", str(cm.exception))
        for bad in ("ftp://example.com/x", "not a link", "https://example.com/a b", ""):
            with self.assertRaises(Q.PostingError):
                Q.parse_link(bad)


class FetchTests(unittest.TestCase):
    def test_greenhouse_single_job(self):
        role, source = Q.fetch(GH, saved=fx("greenhouse-job.json"))
        self.assertEqual(role["id"], "acmeai:4200001")
        self.assertEqual(source["org_name"], "Acme AI")             # the API's company_name
        self.assertEqual(role["title"], "Technical Program Manager, Model Launches")
        self.assertEqual(role["locations"], ["Sydney, Australia"])
        self.assertEqual([b["type"] for b in role["eligibility_blockers"]], ["citizenship"])
        self.assertEqual(role["years_experience"], 6)
        self.assertIn("$180,000 to $220,000", role["compensation"])
        self.assertNotIn("A fictional company", role["description_text"])  # the boilerplate intro is skipped
        self.assertEqual(schema_errors(role), [])

    def test_ashby_board_picks_the_linked_job(self):
        role, source = Q.fetch(ASHBY, saved=fx("ashby-board.json"))
        self.assertEqual(role["title"], "Deployment Program Manager, AI Agents")
        self.assertEqual(role["org"], "globex")
        self.assertEqual(source["org_name"], "Globex")              # no name in the API: from the board slug
        self.assertEqual(role["locations"], ["Sydney, Australia", "Remote (Australia)"])
        self.assertIs(role["remote"], True)
        self.assertEqual(role["compensation"], "AUD 170K to 200K")
        self.assertEqual(role["location_classes"], ["quick"])
        self.assertEqual(schema_errors(role), [])
        closed = ASHBY[:-1] + "9"
        with self.assertRaises(Q.PostingError) as cm:
            Q.fetch(closed, saved=fx("ashby-board.json"))
        self.assertIn("no open posting", str(cm.exception))

    def test_lever_single_posting(self):
        role, source = Q.fetch(LEVER, saved=fx("lever-posting.json"))
        self.assertEqual(role["id"], "initech:7c1d2e3f-4a5b-4c6d-9e8f-000000000101")
        self.assertEqual(role["title"], "Program Manager, Robot Fleet Deployments")
        self.assertEqual([b["type"] for b in role["eligibility_blockers"]], ["licence"])
        self.assertIn("4+ years of program or project management", role["hard_requirements"])
        self.assertEqual(role["compensation"], "AUD 140,000 to 165,000 per year salary")
        self.assertEqual(source["endpoint"], Q.api_url(Q.parse_link(LEVER)))
        self.assertEqual(schema_errors(role), [])

    def test_other_page_uses_its_job_posting_block(self):
        role, source = Q.fetch("https://careers.hooli.example/jobs/123", saved=fx("page-jsonld.html"))
        self.assertEqual(source["kind"], "page")
        self.assertEqual(source["org_name"], "Hooli Analytics")
        self.assertEqual(role["title"], "Senior Operations Lead")
        self.assertEqual(role["locations"], ["Brisbane, QLD, AU"])
        self.assertEqual(role["years_experience"], 5)
        self.assertTrue(role["id"].startswith("hooli_analytics:page_"))
        self.assertEqual(schema_errors(role), [])

    def test_thin_page_asks_for_pasted_text(self):
        path = os.path.join(self.tmp(), "thin.html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("<html><head><title>Jobs</title></head><body><div id='app'></div></body></html>")
        with self.assertRaises(Q.PostingError) as cm:
            Q.fetch("https://careers.example.com/jobs/1", saved=path)
        self.assertIn("Paste the posting text", str(cm.exception))

    def test_no_network_in_tests_gives_a_plain_message(self):
        with self.assertRaises(Q.PostingError) as cm:
            Q.fetch(LEVER)  # the API call is blocked, then the page fetch is blocked too
        self.assertIn("Could not open the link", str(cm.exception))

    def test_pasted_text(self):
        posting = ("Senior Program Manager\n\nAbout the role\nRun programs for our customers.\n\nRequirements\n"
                   "- 5+ years of program management\n- Experience with logistics operations\n\n" + "Extra detail. " * 40)
        role, source = Q.from_text(posting, org_name="Example Co")
        self.assertEqual(source["kind"], "text")
        self.assertEqual(role["title"], "Senior Program Manager")
        self.assertTrue(role["id"].startswith("example_co:text_"))
        self.assertIn("5+ years of program management", role["hard_requirements"])
        self.assertEqual(role["years_experience"], 5)
        with self.assertRaises(Q.PostingError):
            Q.from_text("Short posting\nOne line.")

    def test_cli_exit_codes(self):
        with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            self.assertEqual(Q.main(["https://www.linkedin.com/jobs/view/1"]), 3)
        self.assertIn("LinkedIn", err.getvalue())
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(Q.main([LEVER, "--saved", fx("lever-posting.json")]), 0)
        self.assertIn('"kind": "lever"', out.getvalue())

    def tmp(self):
        import shutil
        import tempfile
        d = tempfile.mkdtemp(prefix="lvlme-quick-posting-")
        self.addCleanup(shutil.rmtree, d, True)
        return d


class WorkdayTests(unittest.TestCase):
    """Workday careers pages carry only a flat summary, so LVLme quick reads the board's public job feed."""

    def test_links(self):
        link = Q.parse_link(WORKDAY + "?source=careers")
        self.assertEqual(link, {"ats": "workday", "board": "globex", "region": None, "host": "globex.wd3.myworkdayjobs.com",
                                "site": "Globex_Careers",
                                "job_id": "Australia-NSW-Sydney/Senior-Program-Manager--Fleet-Rollouts_JR0004242"})
        no_lang = Q.parse_link(WORKDAY.replace("/en-AU", ""))
        self.assertEqual((no_lang["site"], no_lang["job_id"]), (link["site"], link["job_id"]))
        details = Q.parse_link("https://globex.wd3.myworkdayjobs.com/en-US/Globex_Careers/details/Analyst_JR0004243")
        self.assertEqual(details["job_id"], "Analyst_JR0004243")
        for page in ("https://globex.wd3.myworkdayjobs.com/en-AU/Globex_Careers",          # the board, not a job
                     "https://globex.wd3.myworkdayjobs.com/en-AU/Globex_Careers/introduceYourself",
                     "https://wd3.myworkdayjobs.com/Globex_Careers/job/Sydney/Analyst_JR1"):   # no board name
            self.assertEqual(Q.parse_link(page)["ats"], "page", page)

    def test_api_address(self):
        self.assertEqual(Q.api_url(Q.parse_link(WORKDAY)),
                         "https://globex.wd3.myworkdayjobs.com/wday/cxs/globex/Globex_Careers/job/"
                         "Australia-NSW-Sydney/Senior-Program-Manager--Fleet-Rollouts_JR0004242")
        details = Q.parse_link("https://globex.wd3.myworkdayjobs.com/Globex_Careers/details/Analyst_JR0004243")
        self.assertTrue(Q.api_url(details).endswith("/wday/cxs/globex/Globex_Careers/job/Analyst_JR0004243"))

    def test_feed_gives_the_full_posting(self):
        role, source = Q.fetch(WORKDAY, saved=fx("workday-job.json"))
        self.assertEqual(source["kind"], "workday")
        self.assertEqual(source["endpoint"], Q.api_url(Q.parse_link(WORKDAY)))
        self.assertEqual(source["org_name"], "Globex")             # not the legal entity "4410 Globex Labs Australia Pty Ltd"
        self.assertEqual(role["id"], "globex:JR0004242")
        self.assertEqual(role["title"], "Senior Program Manager, Fleet Rollouts")
        self.assertEqual(role["locations"], ["Australia, NSW, Sydney", "Australia, VIC, Melbourne"])
        self.assertEqual(role["published_at"], "2026-10-30")
        self.assertEqual(role["years_experience"], 7)
        self.assertIn("7+ years of program management in logistics, robotics or industrial operations.",
                      role["hard_requirements"])
        # "Ways to stand out from the crowd" lists nice to haves, never hard requirements
        self.assertIn("Experience deploying autonomous mobile robots.", role["nice_to_haves"])
        self.assertNotIn("Experience deploying autonomous mobile robots.", role["hard_requirements"])
        self.assertEqual(len(role["responsibilities"]), 3)
        self.assertEqual(schema_errors(role), [])

    def test_empty_feed_asks_for_pasted_text(self):
        path = os.path.join(self.tmp(), "empty.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"jobPostingInfo": {}}')
        with self.assertRaises(Q.PostingError) as cm:
            Q.fetch(WORKDAY, saved=path)
        self.assertIn("Paste the posting text", str(cm.exception))

    def test_page_fallback_still_uses_the_everyday_name(self):
        """If the feed cannot be reached, the page's summary is read, under the everyday name."""
        page = ('<html><head><script type="application/ld+json">{"@type": "JobPosting", "title": "Analyst", '
                '"hiringOrganization": {"name": "4410 Globex Labs Australia Pty Ltd"}, "description": "%s"}'
                '</script></head></html>' % ("Globex runs warehouse robots. " * 30))
        calls = []

        def fake_get(url, accept):
            calls.append(url)
            if "/wday/cxs/" in url:
                raise urllib.error.URLError("feed unreachable")
            return page
        with mock.patch.object(Q, "http_get", fake_get):
            role, source = Q.fetch(WORKDAY)
        self.assertEqual([("/wday/cxs/" in c) for c in calls], [True, False])
        self.assertEqual((source["kind"], source["org_name"]), ("page", "Globex"))

    def test_everyday_name(self):
        self.assertEqual(Q.workday_org_name("acme", "2100 ACME USA", "ACME builds tools. Join ACME."), "ACME")
        self.assertEqual(Q.workday_org_name("acme", "Acme Pty Ltd", "acme.com is where Acme works"), "Acme")
        self.assertEqual(Q.workday_org_name("initech-robotics", "Initech Pty Ltd"), "Initech Robotics")  # no mention
        self.assertEqual(Q.workday_org_name("acme", "<p>Acme&nbsp;builds</p>"), "Acme")
        self.assertEqual(Q.workday_org_name("acme", "see acme.com, acme.com/jobs or acme.com/about"), "Acme")

    def test_common_section_headings(self):
        for heading, cat in (("What we need to see:", "req"), ("Ways to stand out from the crowd:", "nice"),
                             ("What will make you stand out", "nice"), ("Good To Have -", "nice"),
                             ("Must Have -", "req"), ("What You'll Actually Be Doing", "resp")):
            self.assertEqual(Q.FR.heading_category(heading), cat, heading)

    def tmp(self):
        return FetchTests.tmp(self)


if __name__ == "__main__":
    unittest.main()
