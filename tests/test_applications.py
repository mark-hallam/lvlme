"""Applications and follow-ups (scripts/applications.py, scripts/_applications.py). Fictional data, no network."""
import io
import json
import os
import re
import unittest
from unittest import mock

import helpers as H
import _applications as AP
import _first_draft as FD
import applications as CLI
import autopilot as AUTO
import build_dashboard as B
import doors as DOORS
import practice as PRACTICE
import public as PUBLIC
import stories as STORIES
import validate as V


def app(stage="applied", last="2026-11-01", **kw):
    return dict({"id": "ap1", "org": "acme", "title": "Program Manager", "stage": stage, "last_step_on": last,
                 "applied_on": "2026-11-01", "nudges": 0}, **kw)


class TimingTests(unittest.TestCase):
    def status(self, a, today):
        f = AP.follow_up(a, today)
        return f["status"], f["what"], f["due_on"]

    def test_first_nudge_seven_days_after_the_last_step(self):
        self.assertEqual(self.status(app(), "2026-11-04"), ("waiting", "Follow-up 1 of 2", "2026-11-08"))
        self.assertEqual(self.status(app(), "2026-11-08")[0], "due")
        self.assertEqual(self.status(app(), "2026-11-11")[0], "due")       # up to 3 days late
        self.assertEqual(self.status(app(), "2026-11-12")[0], "overdue")

    def test_at_most_two_then_it_has_gone_quiet(self):
        self.assertEqual(self.status(app(nudges=1, last="2026-11-08"), "2026-11-15"), ("due", "Follow-up 2 of 2", "2026-11-15"))
        self.assertEqual(self.status(app(nudges=2, last="2026-11-15"), "2026-11-20")[0], "waiting")
        self.assertEqual(self.status(app(nudges=2, last="2026-11-15"), "2026-11-22"), ("gone_quiet", "", None))

    def test_a_thank_you_one_day_after_an_interview(self):
        self.assertEqual(self.status(app("interview", "2026-11-10"), "2026-11-11"), ("due", "Thank-you note", "2026-11-11"))
        self.assertEqual(self.status(app("interview", "2026-11-10", thanked=True), "2026-11-12")[1], "Follow-up 1 of 2")

    def test_closed_and_unsent_stages_need_nothing(self):
        for stage in ("evaluated", "offer", "rejected", "discarded", "skip", "hired"):
            self.assertEqual(AP.follow_up(app(stage), "2026-12-01")["status"], "none", stage)


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)
        for rel in (AP.REL, AP.LOG, "campaign/questions.json"):   # an empty tracker, not the demo's made-up ones
            os.remove(os.path.join(self.ws, rel))

    def run_cli(self, *args):
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            self.assertEqual(CLI.main(["--workspace", self.ws] + list(args)), 0)
        return out.getvalue()

    def doc(self):
        return H.load(os.path.join(self.ws, AP.REL))

    def log(self):
        with open(os.path.join(self.ws, AP.LOG), encoding="utf-8") as f:
            return [line.rstrip("\n").split("\t") for line in f][1:]

    def test_adding_is_one_command_and_every_step_is_logged_for_good(self):
        self.assertIn("Added ap1", self.run_cli("add", "--org", "initech", "--title", "Program Manager, Robot Fleet",
                                                 "--role-id", "initech:7c1d2e3f", "--date", "2026-11-01"))
        self.run_cli("followup", "ap1", "--date", "2026-11-08")
        self.run_cli("move", "ap1", "interview", "--date", "2026-11-12", "--note", "first round")
        self.run_cli("thanks", "ap1", "--date", "2026-11-13")
        a = self.doc()["applications"][0]
        self.assertEqual((a["stage"], a["applied_on"], a["last_step_on"], a["nudges"], a["thanked"]),
                         ("interview", "2026-11-01", "2026-11-12", 0, True))
        self.assertEqual([r[:5] for r in self.log()], [
            ["2026-11-01", "ap1", "added", "", "applied"], ["2026-11-08", "ap1", "followup", "due", "sent"],
            ["2026-11-12", "ap1", "stage", "applied", "interview"], ["2026-11-13", "ap1", "thanks", "due", "sent"]])
        self.assertEqual(V.check(self.doc(), H.schema("applications.schema.json")), [])
        errors, warnings, _ = V.validate_workspace(self.ws)
        self.assertEqual(errors, [])

    def test_workspace_is_accepted_before_or_after_subcommand(self):
        cases = ((CLI, "list"), (DOORS, "list"), (PRACTICE, "list"), (STORIES, "list"),
                 (PUBLIC, "list"), (AUTO, "status"))
        for module, command in cases:
            for args in (("--workspace", self.ws, command), (command, "--workspace", self.ws)):
                with self.subTest(script=module.__name__, args=args), mock.patch("sys.stdout", io.StringIO()):
                    self.assertEqual(module.main(list(args)), 0)

    def test_no_third_follow_up_and_no_thank_you_without_an_interview(self):
        self.run_cli("add", "--org", "acme", "--title", "Analyst", "--date", "2026-11-01")
        self.run_cli("followup", "ap1", "--date", "2026-11-08")
        self.run_cli("followup", "ap1", "--date", "2026-11-15")
        with mock.patch("sys.stdout", io.StringIO()), self.assertRaises(SystemExit) as caught:
            CLI.main(["--workspace", self.ws, "followup", "ap1", "--date", "2026-11-22"])
        self.assertIn("let it go quiet", str(caught.exception))
        with mock.patch("sys.stdout", io.StringIO()), self.assertRaises(SystemExit):
            CLI.main(["--workspace", self.ws, "thanks", "ap1"])

    def test_a_draft_leaves_the_words_to_the_person_and_keeps_the_first_draft_rule(self):
        cfg_path = os.path.join(self.ws, "config.json")
        cfg = H.load(cfg_path)
        acme = next(t for t in cfg["targets"] if t["id"] == "acme")
        acme["ai_policy"] = {"first_draft_by_person": True, "source": "https://example.com/acme/ai", "checked_on": "2026-11-01"}
        H.save(cfg_path, cfg)
        self.run_cli("add", "--org", "acme", "--title", "Analyst", "--date", "2026-11-01")
        out = self.run_cli("draft", "ap1", "--date", "2026-11-08")
        rel = re.search(r"campaign/drafts/\S+\.md", out).group(0)
        with open(os.path.join(self.ws, rel), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("[Your words:", text)
        self.assertIn("send it yourself", text)
        errors, warnings = [], []
        FD.checks(self.ws, H.load(cfg_path), errors, warnings, today="2026-11-08")
        self.assertEqual(errors, [])                 # it says it is outreach, so the first-draft check passes
        self.run_cli("move", "ap1", "rejected", "--date", "2026-11-09")
        with mock.patch("sys.stdout", io.StringIO()), self.assertRaises(SystemExit) as caught:
            CLI.main(["--workspace", self.ws, "draft", "ap1", "--date", "2026-11-10"])
        self.assertIn("nothing is due", str(caught.exception))

    def test_a_due_follow_up_shows_on_the_dashboard_and_in_the_summary(self):
        self.run_cli("add", "--org", "initech", "--title", "Program Manager, Robot Fleet", "--date", "2026-10-01")
        with mock.patch("sys.stdout", io.StringIO()), mock.patch.object(B.C, "today_in", lambda cfg: "2026-10-09"):
            self.assertEqual(B.main(["--workspace", self.ws]), 0)
        with open(os.path.join(self.ws, "report", "index.html"), encoding="utf-8") as f:
            page = f.read()
        data = json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', page, re.S).group(1))
        self.assertEqual(data["apps"]["due"], 1)
        self.assertEqual((data["apps"]["rows"][0]["status"], data["apps"]["rows"][0]["what"]), ("due", "Follow-up 1 of 2"))
        self.assertIn('id="appsCard"', page)
        with open(os.path.join(self.ws, "report", "for-agents", "SUMMARY.md"), encoding="utf-8") as f:
            summary = f.read()
        self.assertIn("## Applications (progress only: changes no score)", summary)
        self.assertIn("due follow-up 1 of 2 2026-10-08", summary)


if __name__ == "__main__":
    unittest.main()
