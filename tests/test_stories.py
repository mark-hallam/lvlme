"""Interview story bank (scripts/stories.py, scripts/_stories.py). Fictional data, no network."""
import io
import os
import unittest
from contextlib import redirect_stdout
from unittest import mock

import helpers as H
import _stories as ST
import score as S
import stories as CLI
import validate as V

TODAY = "2026-11-01"
STORY = ["--title", "A values story", "--theme", "values", "--situation", "s", "--task", "t", "--action", "a",
         "--result", "r"]


def quiet(fn, *args):
    with redirect_stdout(io.StringIO()) as out, mock.patch("sys.stderr", io.StringIO()):
        try:
            code = fn(list(args))
        except SystemExit as exc:
            code = 1 if isinstance(exc.code, str) else exc.code
            print(exc.code)
    return code, out.getvalue()


class StoryTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)
        self.config = H.load(os.path.join(self.ws, "config.json"))
        self.evidence = H.load(os.path.join(self.ws, "profile", "evidence.json"))

    def doc(self):
        return H.load(os.path.join(self.ws, ST.REL))

    def test_strength_is_the_best_evidence_behind_a_story(self):
        levels = ST.levels_of(self.evidence)
        by = {s["id"]: ST.strength(s, levels) for s in self.doc()["stories"]}
        self.assertEqual(by, {"S01": "corroborated", "S02": "verified", "S03": "partially_verified",
                              "S04": "self_reported"})
        self.assertEqual(ST.strength({"evidence": ["E16"]}, levels), "self_reported")   # contradicted never backs

    def test_a_theme_with_no_story_or_no_backed_story_is_a_gap(self):
        gaps = {r["id"]: r["status"] for r in ST.gaps(self.doc(), self.config, self.evidence)}
        self.assertEqual(gaps, {"mistake": "word", "disagree": "word", "values": "missing"})

    def test_adding_a_story_checks_themes_and_evidence(self):
        self.assertEqual(quiet(CLI.main, "--workspace", self.ws, "add", *STORY, "--evidence", "E04", "--date", TODAY)[0], 0)
        s = self.doc()["stories"][-1]
        self.assertEqual((s["id"], s["themes"], s["evidence"], s["source"]), ("S05", ["values"], ["E04"], "person"))
        self.assertNotIn("values", {r["id"] for r in ST.gaps(self.doc(), self.config, self.evidence)})
        self.assertEqual(quiet(CLI.main, "--workspace", self.ws, "add", *STORY[:2], "--theme", "nonsense",
                               *STORY[4:])[0], 1)
        self.assertEqual(quiet(CLI.main, "--workspace", self.ws, "add", *STORY, "--evidence", "E99")[0], 1)
        self.assertEqual(quiet(V.main, "--workspace", self.ws)[0], 0)

    def test_a_gap_becomes_one_plan_action(self):
        code, out = quiet(CLI.main, "--workspace", self.ws, "plan", "values", "--date", TODAY)
        self.assertEqual(code, 0, out)
        plan = H.load(os.path.join(self.ws, "campaign", "plan.json"))
        a = plan["actions"][-1]
        self.assertEqual((a["dimension"], a["title"]), ("D7", 'Write a story for "Values under pressure"'))
        self.assertEqual(self.doc()["actions"]["values"], a["id"])
        self.assertEqual(quiet(CLI.main, "--workspace", self.ws, "plan", "values")[0], 1)    # not twice
        self.assertEqual(quiet(CLI.main, "--workspace", self.ws, "plan", "impact")[0], 1)    # already backed
        self.assertEqual(quiet(V.main, "--workspace", self.ws)[0], 0)

    def test_validate_catches_a_story_citing_missing_evidence(self):
        doc = self.doc()
        doc["stories"][0]["evidence"].append("E99")
        H.save(os.path.join(self.ws, ST.REL), doc)
        code, out = quiet(V.main, "--workspace", self.ws)
        self.assertEqual(code, 1)
        self.assertIn("cites evidence E99", out)

    def test_stories_change_no_score(self):
        def run():
            quiet(S.main, "--workspace", self.ws, "--date", TODAY)
            return H.load(os.path.join(self.ws, "eval", "runs", TODAY + ".json"))
        before = run()
        os.remove(os.path.join(self.ws, ST.REL))
        self.assertEqual(before["roles"], run()["roles"])

    def test_the_dashboard_shows_the_gaps(self):
        with open(os.path.join(H.DEMO, "report", "index.html"), encoding="utf-8") as fh:
            self.assertIn('id="storiesCard"', fh.read())
        agents = H.load(os.path.join(H.DEMO, "report", "for-agents", "dashboard.json"))
        self.assertEqual(agents["stories"]["gaps"], 3)
        with open(os.path.join(H.DEMO, "report", "for-agents", "SUMMARY.md"), encoding="utf-8") as fh:
            self.assertIn("Values under pressure: no story yet.", fh.read())


if __name__ == "__main__":
    unittest.main()
