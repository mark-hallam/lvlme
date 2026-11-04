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

    def test_the_message_names_the_role_not_its_internal_id(self):
        code, out = self.promote()
        self.assertEqual(code, 0, out)
        first = out.splitlines()[0]
        self.assertIn("Deployment Program Manager, AI Agents at Globex Labs is now a campaign", first)
        self.assertNotIn("globex_labs_example:", out)               # the internal role id
        self.assertNotIn("Deployment program roles", out)           # the goal is not repeated back

    def test_the_quick_fixes_become_the_plan_s_first_actions(self):
        """The three fixes the person was just shown carry over, so the dashboard never says "No open actions"."""
        code, out = self.promote()
        self.assertEqual(code, 0, out)
        fixes = H.load(os.path.join(self.quick, "result.json"))["fixes"]
        actions = self.load("campaign", "plan.json")["actions"]
        self.assertEqual([a["title"] for a in actions], [f["title"] for f in fixes])
        self.assertEqual([a["id"] for a in actions], ["A01", "A02", "A03"])
        role_id = H.load(os.path.join(self.quick, "result.json"))["role"]["id"]
        for a, f in zip(actions, fixes):
            with self.subTest(fix=f["id"]):
                self.assertEqual((a["status"], a["dimension"], a["expected_points"]), ("todo", f["dimension"], f["gain"]))
                self.assertEqual(a["effects"], [{"dimension": f["dimension"], "set_at_least": f["to"],
                                                 "scope": {"role_ids": [role_id]}, "note": a["effects"][0]["note"]}])
                self.assertIn(f["next_step"], a["done_when"])
                self.assertEqual(a["x_from_quick_fix"], f["id"])
        self.assertIn("Its plan starts with the 3 fixes from your quick result", out)
        agents = self.load("report", "for-agents", "dashboard.json")
        self.assertEqual(len(agents["actions_active"]), 3)
        self.assertEqual(V.validate_workspace(self.ws)[0], [])

    def test_which_ai_judged_carries_over_and_shows(self):
        q = H.load(os.path.join(self.quick, "eval", "quick.json"))
        q["judged_by"] = {"agent": "Claude Code", "model": "claude-opus-5-5"}
        H.save(os.path.join(self.quick, "eval", "quick.json"), q)
        code, out = self.promote()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.load("eval", "judgements.json")["judged_by"], q["judged_by"])
        with open(os.path.join(self.ws, "report", "for-agents", "SUMMARY.md"), encoding="utf-8") as f:
            summary = f.read()
        self.assertIn("Judged by Claude Code, using the model claude-opus-5-5.", summary)
        with open(os.path.join(self.ws, "report", "index.html"), encoding="utf-8") as f:
            self.assertIn("Judged by Claude Code, using the model claude-opus-5-5.", f.read())

    def test_the_agent_summary_says_the_goal_once(self):
        self.promote()
        with open(os.path.join(self.ws, "report", "for-agents", "SUMMARY.md"), encoding="utf-8") as f:
            summary = f.read()
        self.assertEqual(summary.count("Deployment program roles"), 1)

    def test_the_role_family_finds_its_own_title_on_the_next_refresh(self):
        # A comma in the title ("Customer Success Manager, Commercial") once made the family match nothing,
        # so the first job-board refresh after promote dropped the campaign's only role.
        import _common as C
        import _promote as P
        for title in ("Customer Success Manager, Commercial", "Program Manager - Robot Fleet",
                      "Engineer (Applied AI)", "Deployment Program Manager, AI Agents"):
            fam = P.family_for(title)
            self.assertTrue(C.matches_any(fam["title_keywords"], title), title)
        self.assertFalse(C.matches_any(P.family_for("Customer Success Manager, Commercial")["title_keywords"],
                                       "Solutions Engineer, Commercial"))
        code, _ = self.promote()
        self.assertEqual(code, 0)
        role = self.load("market", "roles", "latest.json")["roles"][0]
        fams = self.load("config.json")["families"]
        self.assertTrue(C.matches_any(fams[0]["title_keywords"], role["title"]))

    def test_the_market_counts_the_promoted_role_without_a_job_board_summary(self):
        import json
        import re
        code, _ = self.promote()
        self.assertEqual(code, 0)
        with open(os.path.join(self.ws, "report", "index.html"), encoding="utf-8") as fh:
            page = fh.read()
        data = json.loads(re.search(r'<script type="application/json"[^>]*>(.*?)</script>', page, re.S).group(1))
        counts = data["market"]["byOrgFamily"]
        self.assertEqual(sum(sum(v.values()) for v in counts.values()), 1)

    def test_a_blind_review_disagreement_carries_over_as_waiting_for_a_tie_break(self):
        import glob
        import json
        import re
        code, _ = self.promote()
        self.assertEqual(code, 0)
        files = glob.glob(os.path.join(self.ws, "eval", "reviews", "*.json"))
        self.assertEqual(len(files), 1)
        d = H.load(files[0])["disputes"][0]
        self.assertEqual((d["item_id"].endswith("/D2"), d["scorer"]["score"], d["reviewer"]["score"], d["decided_by"]),
                         (True, 3, 2, "awaiting_tie_break"))
        self.assertEqual(V.validate_workspace(self.ws)[0], [])
        with open(os.path.join(self.ws, "report", "index.html"), encoding="utf-8") as fh:
            page = fh.read()
        data = json.loads(re.search(r'<script type="application/json"[^>]*>(.*?)</script>', page, re.S).group(1))
        self.assertEqual(data["roles"][0]["disp"], {"D2": [3, 2]})
        self.assertIn("the blind reviewer disagreed (first score", page)

    def test_an_unfinished_quick_folder_is_refused(self):
        os.remove(os.path.join(self.quick, "eval", "quick.json"))
        with mock.patch("sys.stdout", io.StringIO()), self.assertRaises(SystemExit) as caught:
            self.promote()
        self.assertIn("is not a finished LVLme quick folder", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
