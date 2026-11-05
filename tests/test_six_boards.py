"""Job boards: a campaign reads Workday, SmartRecruiters and Workable boards.

Those boards list titles only, so fetch_roles.py pages through the list,
reads each posting whose title fits a role family, and lists the rest as
excluded. Every answer here is fictional and saved: no network.
"""
import io
import os
import unittest
from unittest import mock

import helpers as H
import _boards as B
import fetch_roles as F
import validate as V


def fx(name):
    return H.load(os.path.join(H.FIXTURES, "boards", name))


WORKDAY_URL = "https://globex.wd3.myworkdayjobs.com/en-AU/Globex_Careers"
WORKDAY_PATH = "/job/Australia-NSW-Sydney/Senior-Program-Manager--Fleet-Rollouts_JR0004242"
TARGETS = [
    {"id": "wd", "name": "Globex", "ats": "workday", "careers_url": WORKDAY_URL},
    {"id": "sr", "name": "Initech Robotics", "ats": "smartrecruiters", "slug": "InitechRobotics"},
    {"id": "wk", "name": "Globex Labs", "ats": "workable", "slug": "globexlabs"},
]
# The address each board gives one posting's details at.
DETAIL_URL = {
    "wd": "https://globex.wd3.myworkdayjobs.com/wday/cxs/globex/Globex_Careers/job" + "/Australia-NSW-Sydney/Senior-Program-Manager--Fleet-Rollouts_JR0004242",
    "sr": "https://api.smartrecruiters.com/v1/companies/InitechRobotics/postings/744000000004242",
    "wk": "https://apply.workable.com/api/v2/accounts/globexlabs/jobs/A1B2C3D4E5",
}
LISTS = {  # one page of each board's job list: the posting the campaign reads, and one title that fits no family
    "wd": {"total": 2, "jobPostings": [
        {"title": "Senior Program Manager, Fleet Rollouts", "externalPath": WORKDAY_PATH},
        {"title": "Payroll Specialist", "externalPath": "/job/Australia-NSW-Sydney/Payroll-Specialist_JR0009999"}]},
    "sr": {"totalFound": 2, "offset": 0, "limit": 100, "content": [
        {"id": "744000000004242", "name": "Operations Program Lead, Robot Fleets",
         "department": {"label": "Field Operations"}},
        {"id": "744000000009999", "name": "Payroll Specialist"}]},
    "wk": {"total": 2, "results": [
        {"shortcode": "A1B2C3D4E5", "title": "Research Program Manager, Model Evaluations",
         "department": ["Research Operations"]},
        {"shortcode": "Z9Y8X7W6V5", "title": "Payroll Specialist", "department": ["Finance"]}]},
}
DETAILS = {"wd": "workday-job.json", "sr": "smartrecruiters-posting.json", "wk": "workable-job.json"}


def config():
    cfg = H.example_config()
    cfg["targets"] = [dict(t) for t in TARGETS]
    cfg["families"] = [{"id": "program", "name": "Program roles", "title_keywords": ["program"]}]
    return cfg


def answers(target):
    """A stand-in for the network: each URL fetch_board asks for, and what the board would answer."""
    tid = target["id"]
    url, _ = B.list_request(target, 0)
    pages = {url: LISTS[tid]}

    def fetch(where, body=None):
        if where in pages:
            return pages[where]
        if where == DETAIL_URL[tid]:
            return fx(DETAILS[tid])
        raise AssertionError("asked for %s" % where)
    return fetch


class ListTests(unittest.TestCase):
    def test_list_addresses(self):
        self.assertEqual(B.workday_site(WORKDAY_URL), ("globex.wd3.myworkdayjobs.com", "globex", "Globex_Careers"))
        self.assertEqual(B.list_request(TARGETS[0], 40), (
            "https://globex.wd3.myworkdayjobs.com/wday/cxs/globex/Globex_Careers/jobs",
            {"appliedFacets": {}, "limit": 20, "offset": 40, "searchText": ""}))
        self.assertEqual(B.list_request(TARGETS[1], 100)[0],
                         "https://api.smartrecruiters.com/v1/companies/InitechRobotics/postings?limit=100&offset=100")
        self.assertEqual(B.list_request(TARGETS[2], 0, "tok")[1]["token"], "tok")
        with self.assertRaises(ValueError):
            B.list_request({"id": "wd", "ats": "workday"}, 0)

    def test_a_board_reads_only_the_postings_that_fit_a_family(self):
        cfg = config()
        for target in cfg["targets"]:
            with mock.patch.object(F, "fetch_json", answers(target)):
                bundle = F.fetch_board(target, cfg, pause=0)
            self.assertEqual((bundle["listed"], len(bundle["postings"]), bundle["capped"]), (2, 1, False), target["id"])
            self.assertEqual([s["title"] for s in bundle["skipped"]], ["Payroll Specialist"])
            self.assertTrue(bundle["skipped"][0]["url"].startswith("https://"))

    def test_paging_stops_at_a_short_page_or_a_repeat_and_a_huge_board_says_it_was_read_in_part(self):
        target, cfg = TARGETS[0], config()

        def page(offset, n=20):
            return [{"title": "Payroll Specialist", "externalPath": "/job/x/P_%d" % (offset + i)} for i in range(n)]
        asked = []

        def short(where, body=None):
            asked.append(body["offset"])
            return {"total": 43, "jobPostings": page(body["offset"], 20 if body["offset"] < 40 else 3)}
        with mock.patch.object(F, "fetch_json", short):
            bundle = F.fetch_board(target, cfg, pause=0)
        self.assertEqual((asked, bundle["listed"], bundle["capped"]), ([0, 20, 40], 43, False))
        asked.clear()

        def repeats(where, body=None):  # past its limit, a Workday board answers with the same page again
            asked.append(body["offset"])
            return {"total": 2000 if body["offset"] == 0 else 0, "jobPostings": page(min(body["offset"], 40))}
        with mock.patch.object(F, "fetch_json", repeats):
            bundle = F.fetch_board(target, cfg, pause=0)
        self.assertEqual((asked, bundle["listed"]), ([0, 20, 40, 60], 60))
        self.assertEqual((bundle["capped"], bundle["reported"]), (True, 2000))
        with mock.patch.object(F, "fetch_json", lambda where, body=None: {"jobPostings": page(body["offset"])}), \
                mock.patch.object(B, "MAX_LISTED", 60):
            self.assertTrue(F.fetch_board(target, cfg, pause=0)["capped"])

    def test_a_board_read_in_part_is_noted_in_the_summary(self):
        ws = H.new_workspace(self, config())
        fx_dir = os.path.join(os.path.dirname(ws), "fixtures")
        os.makedirs(fx_dir)
        for target in config()["targets"]:
            with mock.patch.object(F, "fetch_json", answers(target)):
                bundle = F.fetch_board(target, config(), pause=0)
            if target["id"] == "wd":
                bundle.update(capped=True, reported=2000)
            H.save(os.path.join(fx_dir, target["id"] + ".json"), bundle)
        with mock.patch("sys.stdout", io.StringIO()):
            F.main(["--workspace", ws, "--fixtures", fx_dir, "--date", "2026-11-03"])
        latest = H.load(os.path.join(ws, "market", "roles", "latest.json"))
        self.assertEqual(latest["summary"]["endpoint_notes"],
                         {"wd": "listed 2 of the board's 2000 jobs only, so some roles may be missing"})
        self.assertEqual(V.check(latest, H.schema("roles.schema.json")), [])


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.cfg = config()
        self.ws = H.new_workspace(self, self.cfg)
        self.fx = os.path.join(os.path.dirname(self.ws), "fixtures")
        os.makedirs(self.fx)
        for target in self.cfg["targets"]:  # the saved file is what --save-raw writes for that board
            with mock.patch.object(F, "fetch_json", answers(target)):
                H.save(os.path.join(self.fx, target["id"] + ".json"), F.fetch_board(target, self.cfg, pause=0))

    def run_main(self):
        with mock.patch("sys.stdout", io.StringIO()):
            self.assertEqual(F.main(["--workspace", self.ws, "--fixtures", self.fx, "--date", "2026-11-03"]), 0)
        return H.load(os.path.join(self.ws, "market", "roles", "latest.json"))

    def test_each_new_board_fetches_from_a_saved_file(self):
        latest = self.run_main()
        self.assertEqual(V.check(latest, H.schema("roles.schema.json")), [])
        self.assertEqual(sorted(r["id"] for r in latest["roles"]),
                         ["sr:744000000004242", "wd:JR0004242", "wk:A1B2C3D4E5"])
        self.assertEqual(latest["summary"]["total_postings_fetched"], {"wd": 2, "sr": 2, "wk": 2})
        self.assertEqual(latest["summary"]["endpoint_errors"], {})
        self.assertEqual(sorted((x["org"], x["title"]) for x in latest["excluded"]),
                         [("sr", "Payroll Specialist"), ("wd", "Payroll Specialist"), ("wk", "Payroll Specialist")])
        self.assertNotIn("endpoint_notes", latest["summary"])

    def test_a_board_that_fails_is_recorded_and_the_others_carry_on(self):
        os.remove(os.path.join(self.fx, "sr.json"))
        latest = self.run_main()
        self.assertIn("sr", latest["summary"]["endpoint_errors"])
        self.assertEqual(sorted(r["org"] for r in latest["roles"]), ["wd", "wk"])

    def test_a_workday_target_without_its_careers_page_says_what_to_add(self):
        target = {"id": "wd", "name": "Globex", "ats": "workday"}
        self.assertIsNone(F.endpoint(target))
        with self.assertRaises(ValueError) as caught:
            F.fetch_board(target, self.cfg, pause=0)
        self.assertIn("needs careers_url", str(caught.exception))

    def test_the_config_accepts_all_six_boards(self):
        cfg = H.example_config()
        cfg["targets"] = [dict(t) for t in TARGETS] + [
            {"id": b, "name": b, "ats": b, "slug": b} for b in ("greenhouse", "ashby", "lever")]
        self.assertEqual(V.check(cfg, H.schema("config.schema.json")), [])


if __name__ == "__main__":
    unittest.main()
