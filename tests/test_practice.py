"""Interview practice and debriefs (scripts/practice.py, scripts/_practice.py). Fictional data, no network."""
import io
import os
import unittest
from contextlib import redirect_stdout
from unittest import mock

import helpers as H
import _applications as AP
import _calibration as CAL
import _practice as PR
import _stories as ST
import practice as CLI
import score as S
import validate as V

TODAY = "2026-11-01"


def quiet(fn, *args):
    with redirect_stdout(io.StringIO()) as out, mock.patch("sys.stderr", io.StringIO()):
        try:
            code = fn(list(args))
        except SystemExit as exc:
            code = 1 if isinstance(exc.code, str) else exc.code
            print(exc.code)
    return code, out.getvalue()


class PracticeTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)

    def bank(self):
        return H.load(os.path.join(self.ws, PR.REL))

    def test_a_practice_set_covers_the_posting_and_cites_stories(self):
        code, out = quiet(CLI.main, "--workspace", self.ws, "questions", "--role", "initech:i-0001", "--json")
        self.assertEqual(code, 0, out)
        import json
        qs = json.loads(out)
        self.assertEqual(qs[0]["theme"], "why_here")
        reqs = [q for q in qs if q["why"].startswith("A hard requirement")]
        self.assertEqual(len(reqs), 3)                              # the posting's three hard requirements
        self.assertIn("S01", next(q for q in reqs if "warehouse" in q["text"])["stories"])
        values = next(q for q in qs if q["theme"] == "values")
        self.assertEqual(values["stories"], [])                     # no story yet: a gap
        self.assertTrue(any(q["stories"] for q in qs))

    def test_questions_asked_for_real_come_back_for_that_organisation(self):
        code, out = quiet(CLI.main, "--workspace", self.ws, "questions", "--role", "acme:4100001")
        self.assertIn("Asked in a real interview here on 2026-10-22", out)
        code, out = quiet(CLI.main, "--workspace", self.ws, "questions", "--role", "initech:i-0001")
        self.assertNotIn("Asked in a real interview", out)

    def test_a_debrief_moves_the_application_to_interview_and_logs_it(self):
        code, out = quiet(CLI.main, "--workspace", self.ws, "record", "--real", "--app", "ap8", "--question",
                          "Why robots?", "--rating", "solid", "--theme", "why_here", "--date", "2026-11-03")
        self.assertEqual(code, 0, out)
        self.assertIn("ap8 moved from applied to Interview", out)
        app = next(a for a in H.load(os.path.join(self.ws, AP.REL))["applications"] if a["id"] == "ap8")
        self.assertEqual((app["stage"], app["last_step_on"]), ("interview", "2026-11-03"))
        self.assertIn("interview", CAL.reached(self.ws)["ap8"])
        q = self.bank()["questions"][-1]
        self.assertEqual((q["kind"], q["org"], q["app"]), ("real", "initech", "ap8"))
        self.assertEqual(quiet(V.main, "--workspace", self.ws)[0], 0)

    def test_a_real_gap_marks_a_backed_theme_to_practise(self):
        config = H.load(os.path.join(self.ws, "config.json"))
        rows = {r["id"]: r for r in ST.coverage(H.load(os.path.join(self.ws, ST.REL)), config,
                                                H.load(os.path.join(self.ws, "profile", "evidence.json")),
                                                PR.struggled(self.bank()))}
        self.assertEqual((rows["lead"]["status"], rows["lead"]["struggled"]), ("practise", 1))
        self.assertEqual(rows["impact"]["status"], "backed")       # rated strong for real

    def test_record_checks_its_inputs(self):
        base = ["--workspace", self.ws, "record", "--question", "Q", "--rating", "gap"]
        self.assertEqual(quiet(CLI.main, *base, "--story", "S99")[0], 1)
        self.assertEqual(quiet(CLI.main, *base, "--theme", "nonsense")[0], 1)
        self.assertEqual(quiet(CLI.main, *base, "--real")[0], 1)    # a real question needs its application
        self.assertEqual(quiet(CLI.main, *base, "--app", "ap99")[0], 1)
        self.assertEqual(quiet(CLI.main, "--workspace", self.ws, "questions", "--role", "nope:1")[0], 1)

    def test_questions_change_no_score(self):
        def run():
            quiet(S.main, "--workspace", self.ws, "--date", TODAY)
            return H.load(os.path.join(self.ws, "eval", "runs", TODAY + ".json"))
        before = run()
        os.remove(os.path.join(self.ws, PR.REL))
        self.assertEqual(before["roles"], run()["roles"])

    def test_the_practice_and_debrief_skills_refuse_during_an_interview(self):
        for name in ("lvlme-practice", "lvlme-debrief"):
            with open(os.path.join(H.ENGINE, "skills", name, "SKILL.md"), encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("never during", text, name)


if __name__ == "__main__":
    unittest.main()
