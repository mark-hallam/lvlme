"""Know the size of a run before it starts (scripts/run_plan.py). The fictional demo, no network."""
import io
import os
import unittest
from unittest import mock

import helpers as H
import run_plan as R


class RunPlanTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)
        self.config = H.load(os.path.join(self.ws, "config.json"))

    def judge_everything_on(self, date):
        path = os.path.join(self.ws, "eval", "judgements.json")
        doc = H.load(path)
        for entry in doc["roles"].values():
            entry["judged_on"] = date
        H.save(path, doc)

    def test_a_second_run_with_no_changes_starts_no_judging_helpers(self):
        self.judge_everything_on("2026-11-02")
        p = R.plan(self.ws, self.config)
        roles = H.load(os.path.join(self.ws, "market", "roles", "latest.json"))["roles"]
        judged = H.load(os.path.join(self.ws, "eval", "judgements.json"))["roles"]
        new = [r["id"] for r in roles if r["id"] not in judged]
        self.assertEqual(p["full"]["role_ids"], new)            # only the never-judged role is left
        for r in roles:
            if r["id"] not in judged:
                judged[r["id"]] = {"judged_on": "2026-11-02"}
        H.save(os.path.join(self.ws, "eval", "judgements.json"), {"schema_version": 1, "roles": judged})
        p = R.plan(self.ws, self.config)
        self.assertEqual((p["full"]["roles"], p["full"]["judges"], p["unchanged"]), (0, 0, len(roles)))
        self.assertIn("Nothing needs judging: this run starts no judging helpers.", R.say(p))

    def test_why_a_role_needs_judging(self):
        ev = [("2026-10-10", None), ("2026-10-20", {"globex"})]
        role = {"id": "acme:1", "org": "acme", "updated_at": "2026-10-01T09:00:00Z"}
        self.assertEqual(R.why_judge(role, None, ev), "new")
        self.assertEqual(R.why_judge(role, {"judged_on": "2026-09-30"}, []), "posting changed")
        self.assertEqual(R.why_judge(role, {"judged_on": "2026-10-05"}, ev), "new evidence")
        self.assertIsNone(R.why_judge(role, {"judged_on": "2026-10-15"}, ev))     # the newer item is about Globex only
        self.assertEqual(R.why_judge(dict(role, org="globex"), {"judged_on": "2026-10-15"}, ev), "new evidence")

    def test_only_evidence_on_the_judged_factors_counts(self):
        doc = {"items": [{"dimensions": ["D3"], "added_on": "2026-11-01"},
                         {"dimensions": ["D2"], "added_on": "2026-10-01", "sources": [{"checked_on": "2026-10-20"}]}]}
        self.assertEqual(R.evidence_dates(doc), [("2026-10-20", None)])

    def test_the_light_run_keeps_the_full_runs_top_five(self):
        p = R.plan(self.ws, self.config, top=5)
        fits = R.last_fits(self.ws)
        top5 = sorted((rid for rid in p["full"]["role_ids"] if rid in fits), key=lambda rid: (-fits[rid], rid))[:5]
        self.assertEqual(p["light"]["role_ids"][:5], top5)
        self.assertLess(p["light"]["helpers"], p["full"]["helpers"])

    def test_it_counts_helpers_and_never_states_a_cost(self):
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            self.assertEqual(R.main(["--workspace", self.ws, "--top", "3"]), 0)
        text = out.getvalue()
        self.assertIn("Full run: judges 12 roles", text)
        self.assertIn("Light run: judges your top 3 by fit", text)
        self.assertNotRegex(text, r"\$|\btokens? (used|cost)|\d+ ?tokens|dollars?")
        self.assertEqual(R.helpers(17, 3), {"roles": 17, "judges": 3, "reviewers": 2, "scouts": 3, "helpers": 8})


if __name__ == "__main__":
    unittest.main()
