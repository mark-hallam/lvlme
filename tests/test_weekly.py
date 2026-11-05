"""The weekly rhythm: Monday plan note, Friday review, weeks in a row."""
import io
import os
import unittest
from unittest import mock

import helpers as H
import _autopilot as A
import _common as C
import _weekly as WK
import autopilot as CLI


def days(*pairs):
    return [{"date": d, "progress": p} for d, p in pairs]


class StreakTests(unittest.TestCase):
    def test_weeks_in_a_row_counts_consecutive_weeks_with_progress(self):
        d = days(("2026-10-06", True), ("2026-10-13", True), ("2026-10-20", True))
        self.assertEqual(WK.weeks_in_a_row(d, "2026-10-22"), 3)

    def test_a_week_without_progress_ends_the_count(self):
        d = days(("2026-10-06", True), ("2026-10-13", False), ("2026-10-20", True))
        self.assertEqual(WK.weeks_in_a_row(d, "2026-10-22"), 1)

    def test_this_week_is_not_over_so_a_quiet_start_does_not_break_the_count(self):
        d = days(("2026-10-06", True), ("2026-10-13", True))
        self.assertEqual(WK.weeks_in_a_row(d, "2026-10-19"), 2)       # Monday of a week with nothing yet
        self.assertEqual(WK.weeks_in_a_row(d, "2026-11-02"), 0)       # but a whole missed week breaks it

    def test_no_progress_at_all_is_zero_and_said_plainly(self):
        self.assertEqual(WK.weeks_in_a_row([], "2026-10-22"), 0)
        self.assertIn("No weeks in a row yet", WK.streak_text(0))
        self.assertEqual(WK.streak_text(1), "1 week in a row with real evidence.")

    def test_monday_and_friday(self):
        self.assertEqual(WK.monday_of("2026-11-05"), "2026-11-02")
        self.assertEqual(WK.friday_of("2026-11-05"), "2026-11-06")
        self.assertEqual(WK.monday_of("2026-11-08"), "2026-11-02")      # Sunday belongs to the week before


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)
        self.cfg = H.load(os.path.join(self.ws, "config.json"))
        self.dash = H.load(os.path.join(self.ws, "report", "for-agents", "dashboard.json"))

    def test_review_lists_what_was_done_with_evidence_and_what_moved(self):
        r = WK.review(self.ws, self.cfg, "2026-10-23", "2026-10-26", self.dash)
        self.assertEqual([d["id"] for d in r["done"]], ["A03"])
        self.assertTrue(r["done"][0]["evidence"])
        self.assertTrue(r["moved"]["changed"])
        self.assertEqual((r["moved"]["level_from"], r["moved"]["level_to"]), (2, 3))
        self.assertIsNotNone(r["next_move"])
        self.assertGreaterEqual(r["weeks_in_a_row"], 1)
        md = WK.review_md(r)
        self.assertIn("Done with evidence this week:", md)
        self.assertIn("Level 2 to Level 3", md)
        self.assertIn("Next week's one move:", md)

    def test_a_week_with_nothing_done_says_so(self):
        r = WK.review(self.ws, self.cfg, "2026-11-13", "2026-11-13", self.dash)
        self.assertEqual(r["done"], [])
        self.assertIn("No move was finished with evidence this week.", WK.review_md(r))
        self.assertIn("unchanged", r["moved"]["text"])

    def test_a_rubric_change_is_not_called_progress(self):
        path = os.path.join(self.ws, "eval", "runs", "2026-10-25.json")
        run = H.load(path)
        run["rubric_version"] = "1.0"
        H.save(path, run)
        r = WK.review(self.ws, self.cfg, "2026-10-30", "2026-11-01", self.dash)
        self.assertFalse(r["moved"]["changed"])
        self.assertIn("not comparable", r["moved"]["text"])


class CliTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)

    def run_cli(self, *args):
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            self.assertEqual(CLI.main(["--workspace", self.ws] + list(args)), 0)
        return out.getvalue()

    def test_plan_is_named_for_the_monday_and_review_for_the_friday(self):
        self.run_cli("plan", "--date", "2026-11-04", "--no-dashboard")
        self.assertTrue(os.path.exists(os.path.join(self.ws, "campaign", "weekly", "2026-11-02.md")))
        note = H.load(os.path.join(self.ws, "campaign", "weekly", "2026-11-02.json"))
        self.assertEqual(note["date"], "2026-11-02")
        self.assertIn("weeks_in_a_row", note)
        md = open(os.path.join(self.ws, "campaign", "weekly", "2026-11-02.md"), encoding="utf-8").read()
        self.assertIn("in a row", md)
        out = self.run_cli("review", "--date", "2026-11-04")
        self.assertIn("campaign/weekly/2026-11-06-review.md", out)
        self.assertTrue(os.path.exists(os.path.join(self.ws, "campaign", "weekly", "2026-11-06-review.md")))

    def test_the_scheduled_task_runs_plan_on_monday_and_review_on_friday(self):
        prompt = A.task_prompt(H.ENGINE, self.ws, A.settings({}))
        self.assertIn("autopilot.py plan", prompt)
        self.assertIn("autopilot.py review", prompt)


if __name__ == "__main__":
    unittest.main()
