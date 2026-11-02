"""LVLme quick's posting fetcher, offline: saved Greenhouse, Ashby, Lever, Workday, SmartRecruiters and Workable API
responses and a saved page."""
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
SMART = "https://jobs.smartrecruiters.com/InitechRobotics/744000000004242-operations-program-lead-robot-fleets"
WORKABLE = "https://apply.workable.com/globexlabs/j/A1B2C3D4E5/"


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


class SmartRecruitersTests(unittest.TestCase):
    """SmartRecruiters pages open with the employer's welcome, so LVLme quick reads the posting API instead."""

    def test_links(self):
        link = Q.parse_link(SMART + "?trid=abc")
        self.assertEqual(link, {"ats": "smartrecruiters", "board": "InitechRobotics", "job_id": "744000000004242",
                                "region": None})
        self.assertEqual(Q.parse_link("https://jobs.smartrecruiters.com/InitechRobotics/744000000004242")["job_id"],
                         "744000000004242")
        apply_page = Q.parse_link("https://jobs.smartrecruiters.com/oneclick-ui/company/InitechRobotics/publication/"
                                  "0B6F3C2E-1A2B-4C3D-8E9F-000000004242?dcr_ci=InitechRobotics")
        self.assertEqual((apply_page["board"], apply_page["job_id"]),
                         ("InitechRobotics", "0b6f3c2e-1a2b-4c3d-8e9f-000000004242"))
        for page in ("https://jobs.smartrecruiters.com/InitechRobotics",                 # the board, not a job
                     "https://jobs.smartrecruiters.com/InitechRobotics/careers-at-initech",
                     "https://careers.smartrecruiters.com/InitechRobotics/744000000004242"):  # another host
            self.assertEqual(Q.parse_link(page)["ats"], "page", page)

    def test_api_address(self):
        self.assertEqual(Q.api_url(Q.parse_link(SMART)),
                         "https://api.smartrecruiters.com/v1/companies/InitechRobotics/postings/744000000004242")

    def test_api_gives_the_sections_in_order(self):
        role, source = Q.fetch(SMART, saved=fx("smartrecruiters-posting.json"))
        self.assertEqual(source["kind"], "smartrecruiters")
        self.assertEqual(source["endpoint"], Q.api_url(Q.parse_link(SMART)))
        self.assertEqual(source["org_name"], "Initech Robotics")   # the API's company name, not the board id
        self.assertEqual(role["id"], "initechrobotics:744000000004242")
        self.assertEqual(role["title"], "Operations Program Lead, Robot Fleets")
        self.assertEqual(role["locations"], ["Melbourne, VIC, Australia"])
        self.assertIs(role["remote"], False)                        # hybrid is not remote
        self.assertEqual(role["published_at"], "2026-10-28")
        self.assertEqual(role["team_or_department"], "Field Operations")
        self.assertEqual(role["years_experience"], 6)
        self.assertEqual(role["hard_requirements"], [
            "You have 6+ years of program or operations management in logistics or industrial settings.",
            "You have led cross-functional teams through complex hardware deployments.",
            "Experience with safety management systems in a regulated industry."])
        self.assertEqual(role["nice_to_haves"], ["Experience deploying autonomous mobile robots."])
        self.assertEqual(len(role["responsibilities"]), 3)
        # the welcome is kept for the reader, last, and never read as a requirement
        text = role["description_text"]
        self.assertIn("Hello, g'day, kia ora!", text)
        self.assertGreater(text.index("Hello, g'day"), text.index("Experience deploying autonomous"))
        self.assertFalse(any("g'day" in r or "Join the team" in r for r in role["hard_requirements"]))
        self.assertEqual(schema_errors(role), [])

    def test_posting_file_names_the_board(self):
        import quick
        role, source = Q.fetch(SMART, saved=fx("smartrecruiters-posting.json"))
        text = quick.posting_md(role, source["org_name"], source, "2026-11-03")
        self.assertIn("Initech Robotics · Melbourne, VIC, Australia", text)
        self.assertIn("from the public SmartRecruiters job board, read only", text)

    def test_remote_flag(self):
        data = Q.C.load_json(fx("smartrecruiters-posting.json"))
        data["location"].update({"remote": True, "hybrid": False})
        base = Q.smartrecruiters_base(Q.parse_link(SMART), data)
        self.assertEqual((base["workplace_type"], base["is_remote"]), ("Remote", True))

    def test_closed_or_empty_posting_asks_for_pasted_text(self):
        data = Q.C.load_json(fx("smartrecruiters-posting.json"))
        for change in ({"active": False}, {"jobAd": {"sections": {}}}, {"jobAd": None}):
            path = os.path.join(self.tmp(), "posting.json")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(Q.json.dumps(dict(data, **change)))
            with self.assertRaises(Q.PostingError) as cm:
                Q.fetch(SMART, saved=path)
            self.assertIn("SmartRecruiters board 'InitechRobotics' gave no posting", str(cm.exception))

    def test_a_closed_link_names_the_board_plainly(self):
        def gone(url, accept):
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        with mock.patch.object(Q, "http_get", gone):
            with self.assertRaises(Q.PostingError) as cm:
                Q.fetch(SMART)
        self.assertIn("no longer open on the SmartRecruiters board 'InitechRobotics'", str(cm.exception))

    def test_welcome_inside_the_job_description(self):
        # Canva puts its welcome at the top of the job description, after a bold line about "experiences"
        data = Q.C.load_json(fx("smartrecruiters-posting.json"))
        jd = data["jobAd"]["sections"]["jobDescription"]
        jd["text"] = ("<p><strong>Join the team changing how the world experiences warehouses.</strong></p>"
                      "<p>Hello, g'day, kia ora!</p><p>Thanks for stopping by.</p>" + jd["text"])
        data["jobAd"]["sections"]["companyDescription"]["text"] = ""
        self.assertIsNone(Q.FR.heading_category("Join the team changing how the world experiences warehouses."))
        path = os.path.join(self.tmp(), "posting.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(Q.json.dumps(data))
        role, _ = Q.fetch(SMART, saved=path)
        self.assertEqual(len(role["hard_requirements"]), 3)
        self.assertFalse(any("g'day" in r or "stopping by" in r or "Join the team" in r
                             for r in role["hard_requirements"]))

    def test_whole_posting_under_the_company_description(self):
        # an open posting whose every section but the company description is empty is still read
        data = Q.C.load_json(fx("smartrecruiters-posting.json"))
        secs = data["jobAd"]["sections"]
        secs["companyDescription"]["text"] = (secs["jobDescription"]["text"] + "<h3>Qualifications</h3>"
                                             + secs["qualifications"]["text"])
        for key in Q.SR_SECTIONS:
            secs[key]["text"] = ""
        data["location"]["fullLocation"] = "Melbourne, , Australia"
        path = os.path.join(self.tmp(), "posting.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(Q.json.dumps(data))
        role, _ = Q.fetch(SMART, saved=path)
        self.assertEqual(len(role["hard_requirements"]), 3)
        self.assertEqual(role["nice_to_haves"], ["Experience deploying autonomous mobile robots."])
        self.assertEqual(role["locations"], ["Melbourne, Australia"])   # an empty region is dropped

    def test_more_headings(self):
        for heading, cat in (("You're probably a match if", "req"), ("At the moment, this role is focused on:", "resp"),
                             ("What you'll learn and how you'll develop at Initech", "about"),
                             ("Your missions:", "resp"), ("Our mission", None)):
            self.assertEqual(Q.FR.heading_category(heading), cat, heading)

    def tmp(self):
        return FetchTests.tmp(self)


class WorkableTests(unittest.TestCase):
    """A Workable page is drawn in the browser and holds no posting text, so LVLme quick reads its job feed."""

    def test_links(self):
        self.assertEqual(Q.parse_link(WORKABLE), {"ats": "workable", "board": "globexlabs", "job_id": "A1B2C3D4E5",
                                                  "region": None})
        for same in ("https://apply.workable.com/globexlabs/j/a1b2c3d4e5/apply/",   # the apply page, any case
                     "https://apply.workable.com/globexlabs/j/A1B2C3D4E5?utm_source=x",
                     "https://globexlabs.workable.com/j/A1B2C3D4E5"):                 # the older address
            link = Q.parse_link(same)
            self.assertEqual((link["ats"], link["board"], link["job_id"]), ("workable", "globexlabs", "A1B2C3D4E5"), same)
        short = Q.parse_link("https://apply.workable.com/j/A1B2C3D4E5")
        self.assertEqual((short["ats"], short["board"]), ("workable", None))     # the account comes from following it
        for page in ("https://apply.workable.com/globexlabs/",                      # the board, not a job
                     "https://apply.workable.com/api/v2/accounts/globexlabs",
                     "https://www.workable.com/j/A1B2C3D4E5",                       # Workable's own site
                     "https://apply.workable.com/globexlabs/j/x/"):                  # too short to be a code
            self.assertEqual(Q.parse_link(page)["ats"], "page", page)

    def test_api_address(self):
        self.assertEqual(Q.api_url(Q.parse_link(WORKABLE)),
                         "https://apply.workable.com/api/v2/accounts/globexlabs/jobs/A1B2C3D4E5")

    def test_feed_gives_requirements_and_keeps_benefits_out(self):
        role, source = Q.fetch(WORKABLE, saved=fx("workable-job.json"))
        self.assertEqual(source["kind"], "workable")
        self.assertEqual(source["endpoint"], Q.api_url(Q.parse_link(WORKABLE)))
        self.assertEqual(source["org_name"], "Globex Labs")   # how the posting writes the account's name
        self.assertEqual(role["id"], "globexlabs:A1B2C3D4E5")
        self.assertEqual(role["title"], "Research Program Manager, Model Evaluations")
        self.assertEqual(role["locations"], ["Sydney, New South Wales, Australia", "Melbourne, Victoria, Australia"])
        self.assertIs(role["remote"], False)                    # hybrid is not remote
        self.assertEqual(role["published_at"], "2026-10-30")
        self.assertEqual(role["team_or_department"], "Research Operations")
        self.assertEqual(role["url"], WORKABLE)
        self.assertEqual(role["years_experience"], 5)
        # the requirements field has no heading of its own: it is still read as the requirements
        self.assertEqual(role["hard_requirements"], [
            "5+ years of program management in a research or technical setting.",
            "Clear written communication for both technical and non-technical readers.",
            "Experience coordinating work across research, engineering and customer teams."])
        self.assertEqual(role["nice_to_haves"], ["Familiarity with machine learning evaluation methods."])
        self.assertEqual(len(role["responsibilities"]), 3)
        # the benefits come last, kept for the reader and never read as a requirement
        text = role["description_text"]
        self.assertIn("four day week", text)
        self.assertGreater(text.index("four day week"), text.index("evaluation methods"))
        self.assertFalse(any("four day week" in r for r in role["hard_requirements"] + role["nice_to_haves"]))
        self.assertEqual(schema_errors(role), [])

    def test_the_account_feed_gives_the_name(self):
        calls = []

        def get(url, accept):
            calls.append(url)
            if url.endswith("/api/v1/accounts/globexlabs"):
                return Q.json.dumps({"subdomain": "globexlabs", "name": "Globex Labs Pty Ltd"})
            with open(fx("workable-job.json"), encoding="utf-8") as fh:
                return fh.read()
        with mock.patch.object(Q, "http_get", get):
            role, source = Q.fetch(WORKABLE)
        self.assertEqual(source["org_name"], "Globex Labs Pty Ltd")
        self.assertEqual(calls, ["https://apply.workable.com/api/v2/accounts/globexlabs/jobs/A1B2C3D4E5",
                                 "https://apply.workable.com/api/v1/accounts/globexlabs"])

        def no_account(url, accept):   # the account feed cannot be read: the posting's own spelling stands
            if "/api/v1/accounts/" in url:
                raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
            return get(url, accept)
        with mock.patch.object(Q, "http_get", no_account):
            _, source = Q.fetch(WORKABLE)
        self.assertEqual(source["org_name"], "Globex Labs")

    def test_org_name_from_the_account(self):
        self.assertEqual(Q.workable_org_name("acmeai", "Join Acme AI. Visit acmeai.example to learn more."), "Acme AI")
        self.assertEqual(Q.workable_org_name("acme-ai", "<p>At ACME-AI we build</p>"), "ACME-AI")
        self.assertEqual(Q.workable_org_name("initech", "No mention here."), "Initech")
        self.assertEqual(Q.workable_org_name("globexlabs", "Globex Labsmith is not the name"), "Globexlabs")

    def test_short_link_is_followed_once(self):
        with mock.patch.object(Q, "follow_short_link", return_value=WORKABLE) as follow, \
                mock.patch.object(Q, "workable_account_name", return_value=None), \
                mock.patch.object(Q, "http_get", lambda url, accept: open(fx("workable-job.json"), encoding="utf-8").read()):
            role, source = Q.fetch("https://apply.workable.com/j/A1B2C3D4E5")
        follow.assert_called_once_with("https://apply.workable.com/j/A1B2C3D4E5")
        self.assertEqual(source["endpoint"], "https://apply.workable.com/api/v2/accounts/globexlabs/jobs/A1B2C3D4E5")
        self.assertEqual(role["id"], "globexlabs:A1B2C3D4E5")
        with mock.patch.object(Q, "follow_short_link", return_value=None):
            with self.assertRaises(Q.PostingError) as cm:
                Q.fetch("https://apply.workable.com/j/A1B2C3D4E5")
        self.assertIn("Give the full link", str(cm.exception))

    def test_closed_or_empty_posting_asks_for_pasted_text(self):
        data = Q.C.load_json(fx("workable-job.json"))
        for change in ({"state": "closed"}, {"description": "", "requirements": "<p></p>", "benefits": None}):
            path = os.path.join(self.tmp(), "job.json")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(Q.json.dumps(dict(data, **change)))
            with self.assertRaises(Q.PostingError) as cm:
                Q.fetch(WORKABLE, saved=path)
            self.assertIn("Workable board 'globexlabs' gave no posting", str(cm.exception))

    def test_a_closed_link_names_the_board_plainly(self):
        def gone(url, accept):
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        with mock.patch.object(Q, "http_get", gone):
            with self.assertRaises(Q.PostingError) as cm:
                Q.fetch(WORKABLE)
        self.assertIn("no longer open on the Workable board 'globexlabs'", str(cm.exception))

    def test_remote_and_on_site(self):
        data = Q.C.load_json(fx("workable-job.json"))
        link = Q.parse_link(WORKABLE)
        for change, want in (({"workplace": "remote"}, ("Remote", True)), ({"workplace": "on_site"}, ("Onsite", False)),
                             ({"workplace": None, "remote": True}, ("Remote", True)),
                             ({"workplace": None, "remote": False}, (None, None))):
            base = Q.workable_base(link, dict(data, **change))
            self.assertEqual((base["workplace_type"], base["is_remote"]), want, change)

    def test_posting_file_names_the_board(self):
        import quick
        role, source = Q.fetch(WORKABLE, saved=fx("workable-job.json"))
        text = quick.posting_md(role, source["org_name"], source, "2026-11-03")
        self.assertIn("from the public Workable job board, read only", text)

    def tmp(self):
        return FetchTests.tmp(self)


if __name__ == "__main__":
    unittest.main()
