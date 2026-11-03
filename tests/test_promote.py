"""Climb from here: quick.py promote turns a LVLme quick result into a campaign (scripts/_promote.py).

The fictional quick demo, copied to a temporary folder; no network.
"""
import io
import os
import shutil
import tempfile
import unittest
from unittest import mock

import helpers as H
import quick as Q
import validate as V

QUICK = os.path.join(H.ENGINE, "examples", "quick-demo",
                     "2026-11-02-globex-labs-deployment-program-manager-ai-agents")


class PromoteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="lvlme-promote-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.quick = os.path.join(self.tmp, "quick")
        shutil.copytree(QUICK, self.quick)
        cfg = H.load(os.path.join(self.quick, "config.json"))
        cfg.pop("fictional")                      # a real quick folder, outside the engine
        H.save(os.path.join(self.quick, "config.json"), cfg)
        self.ws = os.path.join(self.tmp, "campaign")

    def promote(self):
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            code = Q.main(["promote", "--folder", self.quick, "--goal", "Deployment program roles",
                           "--workspace", self.ws, "--date", "2026-11-03"])
        return code, out.getvalue()

    def load(self, *p):
        return H.load(os.path.join(self.ws, *p))

    def test_promoting_keeps_every_evidence_item_and_its_level(self):
        code, out = self.promote()
        self.assertEqual(code, 0, out)
        before = H.load(os.path.join(self.quick, "profile", "evidence.json"))["items"]
        after = self.load("profile", "evidence.json")["items"]
        self.assertEqual([(e["id"], e["level"], e["claim"]) for e in after], [(e["id"], e["level"], e["claim"]) for e in before])
        self.assertTrue(os.path.exists(os.path.join(self.ws, "intake", "sources", "cv-alex-example.md")))
        with open(os.path.join(self.ws, "intake", "answers.md"), encoding="utf-8") as f:
            self.assertIn("## From LVLme quick (2026-11-02)", f.read())
        self.assertEqual(V.validate_workspace(self.ws)[0], [])

    def test_the_first_campaign_score_matches_quick_with_nothing_redone(self):
        self.promote()
        quick = H.load(os.path.join(self.quick, "result.json"))
        run = self.load("eval", "runs", "2026-11-03.json")
        role = run["roles"][0]
        self.assertEqual(role["role_id"], quick["role"]["id"])
        self.assertEqual(role["fit"], quick["fit"])                         # 41, quick's "today"
        self.assertEqual(role["awaiting_review"], ["D2"])                    # the open dispute still waits
        judged = self.load("eval", "judgements.json")["roles"][role["role_id"]]
        self.assertEqual(judged["D1"]["reviewed_on"], "2026-11-02")          # agreed in quick's blind review
        self.assertNotIn("reviewed_on", judged["D2"])
        prof = self.load("eval", "profile-dimensions.json")
        self.assertEqual(prof["D6_rules"]["classes"]["australia_nz"]["score"], 5)
        self.assertEqual(prof["D3"]["globex_labs_example"]["evidence"], ["E06"])
        self.assertTrue(os.path.exists(os.path.join(self.ws, "report", "index.html")))

    def test_the_employer_becomes_a_target_on_its_own_job_board(self):
        self.promote()
        cfg = self.load("config.json")
        self.assertEqual({k: cfg["targets"][0][k] for k in ("id", "name", "ats", "slug")},
                         {"id": "globex_labs_example", "name": "Globex Labs", "ats": "ashby", "slug": "globex-labs-example"})
        self.assertEqual(len(cfg["families"]), 1)
        self.assertEqual(cfg["goal"]["title"], "Deployment program roles")

    def test_an_unfinished_quick_folder_is_refused(self):
        os.remove(os.path.join(self.quick, "eval", "quick.json"))
        with mock.patch("sys.stdout", io.StringIO()), self.assertRaises(SystemExit) as caught:
            self.promote()
        self.assertIn("is not a finished LVLme quick folder", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
