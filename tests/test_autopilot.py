"""Autopilot (scripts/autopilot.py, scripts/_autopilot.py): the person's yes, the schedule, the weekly note.

The fictional demo, no network, no scheduler touched: the tests read what the
script records and prints.
"""
import io
import json
import os
import re
import unittest
from unittest import mock

import helpers as H
import _autopilot as A
import autopilot as CLI
import validate as V


class AutopilotTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)

    def run_cli(self, *args):
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            self.assertEqual(CLI.main(["--workspace", self.ws] + list(args)), 0)
        return out.getvalue()

    def config(self):
        return H.load(os.path.join(self.ws, "config.json"))

    def test_on_is_one_command_after_a_yes_and_off_is_one_more(self):
        self.assertIn("Autopilot is off.", self.run_cli("status"))
        out = self.run_cli("on", "--rhythm", "weekly", "--day", "mon", "--time", "07:00", "--run", "light",
                           "--sources", "github, website", "--helpers", "no", "--date", "2026-11-03")
        self.assertIn("Autopilot is on: Mondays at 07:00, a light run. Approved sources: github, website.", out)
        self.assertIn("Next run: 2026-11-09.", out)
        ap = self.config()["autopilot"]
        self.assertEqual((ap["enabled"], ap["sources"], ap["helpers"], ap["approved_on"]),
                         (True, ["github", "website"], False, "2026-11-03"))
        self.assertEqual(V.check(self.config(), H.schema("config.schema.json")), [])
        self.assertEqual(V.validate_workspace(self.ws)[0], [])
        self.assertTrue(os.path.exists(os.path.join(self.ws, "campaign", "autopilot-prompt.md")))
        self.assertIn("Autopilot is off.", self.run_cli("off"))
        self.assertFalse(self.config()["autopilot"]["enabled"])

    def test_the_prompt_asks_nothing_and_keeps_to_the_approved_sources(self):
        self.run_cli("on", "--sources", "github", "--helpers", "no")
        text = self.run_cli("prompt")
        self.assertIn("Nobody is present", text)
        self.assertIn("ask nothing, approve nothing new", text)
        self.assertIn("approved read-only sources only: github.", text)
        self.assertIn("Start no helper agents", text)
        self.assertIn("Never apply for a job, send any email or message", text)
        self.assertIn("python3 scripts/autopilot.py week", text)
        self.assertNotIn("Mark", text.replace(CLI.ENGINE, ""))   # generic: nothing about one person is built in

    def test_the_schedule_line_and_next_run(self):
        ap = dict(A.DEFAULTS, enabled=True)
        self.assertTrue(A.cron_line("/e", "/w", ap, "/w/p.md", "/w/l.log").startswith("0 7 * * 1 cd \"/e\""))
        self.assertTrue(A.cron_line("/e", "/w", dict(ap, day="sun", time="18:30"), "p", "l").startswith("30 18 * * 0 "))
        self.assertTrue(A.cron_line("/e", "/w", dict(ap, rhythm="daily"), "p", "l").startswith("0 7 * * * "))
        self.assertEqual(A.next_run(ap, "2026-11-03"), "2026-11-09")     # a Tuesday: next Monday
        self.assertEqual(A.next_run(ap, "2026-11-09"), "2026-11-09")
        self.assertIsNone(A.next_run(dict(ap, enabled=False), "2026-11-03"))

    def test_two_runs_a_week_apart_leave_two_dated_notes_with_one_action_each(self):
        self.run_cli("on")
        self.run_cli("week", "--date", "2026-11-03", "--no-dashboard")
        first = H.load(os.path.join(self.ws, "campaign", "weekly", "2026-11-03.json"))
        self.assertEqual(first["since"], "2026-11-01")        # a first note compares with the last scored run
        self.assertIn("Best fit unchanged, from 57 to 57.", first["changed"])
        self.assertTrue(first["action"]["title"])
        self.run_cli("week", "--date", "2026-11-10", "--no-dashboard")
        second = H.load(os.path.join(self.ws, "campaign", "weekly", "2026-11-10.json"))
        self.assertEqual(second["since"], "2026-11-03")
        self.assertIn("Best fit unchanged, from 57 to 57.", second["changed"])
        with open(os.path.join(self.ws, "campaign", "weekly", "2026-11-10.md"), encoding="utf-8") as f:
            md = f.read()
        self.assertEqual(md.count("The one thing to do this week:"), 1)
        self.assertIn("Level 3, Moderate: fit 57", md)

    def test_its_own_note_is_rewritten_on_a_second_run_that_day(self):
        self.run_cli("week", "--date", "2026-11-03", "--no-dashboard")
        path = os.path.join(self.ws, "campaign", "weekly", "2026-11-03.md")
        with open(path, "a", encoding="utf-8") as f:
            f.write("stale line\n")
        self.run_cli("week", "--date", "2026-11-03", "--no-dashboard")
        with open(path, encoding="utf-8") as f:
            self.assertNotIn("stale line", f.read())

    def test_a_note_the_agent_wrote_is_kept(self):
        path = os.path.join(self.ws, "campaign", "weekly", "2026-11-03.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("# The agent's own weekly comparison\n")
        self.run_cli("week", "--date", "2026-11-03", "--no-dashboard")
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), "# The agent's own weekly comparison\n")

    def test_the_dashboard_opens_on_this_week(self):
        self.run_cli("on", "--date", "2026-11-03")
        self.run_cli("week", "--date", "2026-11-03")
        with open(os.path.join(self.ws, "report", "index.html"), encoding="utf-8") as f:
            page = f.read()
        data = json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', page, re.S).group(1))
        self.assertEqual(data["week"]["date"], "2026-11-03")
        self.assertTrue(data["week"]["autopilot"]["enabled"])
        self.assertLess(page.index('id="weekCard"'), page.index('id="hero"'))   # the first card on the page


if __name__ == "__main__":
    unittest.main()
