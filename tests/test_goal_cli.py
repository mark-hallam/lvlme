"""scripts/goal.py: check, choose a stepping stone, start the next goal."""
import io
import json
import os
import unittest
from contextlib import redirect_stdout

import helpers as H
import goal as GL


def run(ws, *args):
    out = io.StringIO()
    with redirect_stdout(out):
        code = GL.main(["--workspace", ws] + list(args))
    return code, out.getvalue()


class GoalCliTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)
        cfg = H.load(os.path.join(self.ws, "config.json"))
        cfg["goal"].update(role="Applied AI", organisations=["Acme AI"], where="Melbourne", by="2026-12-15")
        H.save(os.path.join(self.ws, "config.json"), cfg)

    def test_check_saves_the_result_and_says_it_plainly(self):
        code, out = run(self.ws, "check", "--date", "2026-11-05")
        self.assertEqual(code, 0)
        saved = H.load(os.path.join(self.ws, "campaign", "goal-check.json"))
        self.assertIn(saved["verdict"], ("on_track", "stretch", "out_of_reach", "reached"))
        self.assertIn("Level 4 (Good)", out)

    def test_accepting_a_stone_changes_the_config_and_declining_does_not(self):
        cfg = H.load(os.path.join(self.ws, "config.json"))
        cfg["goal"]["target_level"] = 5          # two levels away, so there is a smaller step to propose
        H.save(os.path.join(self.ws, "config.json"), cfg)
        run(self.ws, "check", "--date", "2026-11-05")
        saved = H.load(os.path.join(self.ws, "campaign", "goal-check.json"))
        self.assertIsNotNone(saved["stepping_stone"])
        before = H.load(os.path.join(self.ws, "config.json"))
        self.assertNotIn("stepping_stone", before["goal"])
        run(self.ws, "stone", "decline", "--date", "2026-11-05")
        self.assertEqual(H.load(os.path.join(self.ws, "config.json")), before)       # declining changes nothing
        self.assertEqual(H.load(os.path.join(self.ws, "campaign", "goal-check.json"))["decision"], "declined")
        run(self.ws, "check", "--date", "2026-11-06")
        self.assertEqual(H.load(os.path.join(self.ws, "campaign", "goal-check.json"))["decision"], "declined")   # remembered
        run(self.ws, "stone", "accept", "--date", "2026-11-06")
        goal = H.load(os.path.join(self.ws, "config.json"))["goal"]
        self.assertEqual(goal["stepping_stone"]["accepted_on"], "2026-11-06")
        self.assertTrue(goal["stepping_stone"]["why"])
        self.assertEqual(goal["role"], "Applied AI")                 # the goal itself is unchanged

    def test_stone_without_a_proposal_is_refused(self):
        with self.assertRaises(SystemExit):
            run(self.ws, "stone", "accept")

    def test_startline_in_plain_words(self):
        code, out = run(self.ws, "startline", "--date", "2026-11-05")
        self.assertIn("Level 3, Moderate", out)
        self.assertIn("fit about 57 to 61", out)       # the demo's best role is judged twice
        self.assertNotIn("One judging so far", out)
        self.assertNotIn("altitude", out.lower())

    def test_startline_with_one_judging_says_so(self):
        path = os.path.join(self.ws, "eval", "runs", "2026-11-01.json")
        run_doc = H.load(path)
        for r in run_doc["roles"]:
            r.pop("fit_low", None)
            r.pop("fit_high", None)
        H.save(path, run_doc)
        code, out = run(self.ws, "startline", "--date", "2026-11-05")
        self.assertIn("One judging so far", out)
        self.assertNotIn("altitude", out.lower())

    def test_next_goal_keeps_the_old_one(self):
        run(self.ws, "next-goal", "--role", "Head of Applied AI", "--organisations", "Globex Labs", "--by", "2027-12-01",
            "--date", "2026-11-05")
        cfg = H.load(os.path.join(self.ws, "config.json"))
        self.assertEqual(cfg["goal"]["role"], "Head of Applied AI")
        self.assertEqual(cfg["goal_history"][0]["role"], "Applied AI")
        self.assertEqual(cfg["goal_history"][0]["outcome"], "reached")
        import validate as V
        self.assertEqual(V.validate_workspace(self.ws)[0], [])


if __name__ == "__main__":
    unittest.main()
