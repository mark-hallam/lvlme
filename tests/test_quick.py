"""Climb quick's result builder, offline, on the fictional demo (Alex Example and a made-up Globex Labs posting)."""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import helpers as H
import quick as Q
import score as S

sys.path.insert(0, os.path.join(H.ENGINE, "examples"))
import build_quick_demo as D  # noqa: E402

LINK = D.LINK
BOARD = os.path.join(H.FIXTURES, "quick", "ashby-board.json")


def tmpdir(test):
    d = tempfile.mkdtemp(prefix="climb-quick-test-")
    test.addCleanup(shutil.rmtree, d, True)
    return d


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
        code = Q.main(argv)
    return code, out.getvalue(), err.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.folder = D.folder_for(tmpdir(self))
        with mock.patch("sys.stdout", io.StringIO()):
            D.build(self.folder)

    def load(self, rel):
        return H.load(os.path.join(self.folder, rel))

    def save(self, rel, data):
        H.save(os.path.join(self.folder, rel), data)

    def write(self, rel, text):
        with open(os.path.join(self.folder, rel), "w", encoding="utf-8") as fh:
            fh.write(text)

    def result(self):
        return Q.build_result(Q.load(self.folder))

    def factor(self, result, dim):
        return next(f for f in result["factors"] if f["dimension"] == dim)


class DemoTests(Base):
    def test_demo_is_reproducible(self):
        """A fresh build gives the committed result and page byte for byte."""
        committed = D.folder_for()
        for name in ("result.json", "index.html", "message.md", "posting.md", "market/roles/latest.json"):
            with open(os.path.join(committed, name), encoding="utf-8") as fh:
                want = fh.read()
            with open(os.path.join(self.folder, name), encoding="utf-8") as fh:
                got = fh.read()
            if name == "message.md":
                got = got.replace(Q.display_path(self.folder), os.path.relpath(committed, H.ENGINE))
            self.assertEqual(got, want, name)

    def test_the_odds_come_from_the_scoring_maths(self):
        r = self.load("result.json")
        self.assertEqual((r["fit"], r["interview_band"], r["offer_band"]), (41.0, "Low", "Very low"))
        scores = {f["dimension"]: f["score"] for f in r["factors"]}
        self.assertEqual(scores, {"D1": 3, "D2": 2, "D3": 1, "D4": 2, "D6": 5})
        self.assertEqual([x["dimension"] for x in r["not_checked"]], ["D5", "D7"])
        # the same fit by hand: weights 25, 20, 20, 10, 10 out of 100; D5 and D7 count 0
        self.assertEqual(r["fit"], 3 / 5 * 25 + 2 / 5 * 20 + 1 / 5 * 20 + 2 / 5 * 10 + 5 / 5 * 10)

    def test_a_cv_line_is_capped_by_the_ladder(self):
        r = self.load("result.json")
        d3 = self.factor(r, "D3")
        self.assertEqual((d3["raw"], d3["score"]), (3, 1))
        self.assertIn("self-reported network, which supports at most 1", d3["why_counted"][0])
        levels = {e["level"] for f in r["factors"] for e in f["evidence"]}
        self.assertLessEqual({"verified", "self_reported"}, levels)

    def test_disagreement_is_logged_and_counts_as_two(self):
        r = self.load("result.json")
        d2 = self.factor(r, "D2")
        self.assertEqual(d2["review"], {"status": "disputed", "reviewer_score": 2, "judge_score": 3})
        self.assertEqual(r["review"]["agreed"], ["D1", "D6"])
        [dispute] = r["review"]["disputes"]
        self.assertEqual((dispute["item_id"], dispute["stands"], dispute["decided_by"]),
                         ("globex:0b6f3c2e-1a2b-4c3d-8e9f-000000000001/D2", 2, "awaiting_tie_break"))
        self.assertEqual(self.factor(r, "D3")["review"]["status"], "not_needed")

    def test_fixes_are_ranked_and_capped(self):
        r = self.load("result.json")
        self.assertEqual([(f["id"], f["from"], f["to"], f["gain"]) for f in r["fixes"]],
                         [("F1", 1, 3, 8.0), ("F2", 2, 3, 4.0), ("F3", 2, 3, 2.0)])   # F1 asked for 4; the cap allows +2
        self.assertEqual(r["if_all_fixes"], {"fit": 55.0, "interview_band": "Moderate", "offer_band": "Low", "gain": 14.0})
        self.assertEqual(r["fixes_not_shown"], [{"id": "F4", "title": "Add customer-facing deployment experience",
                                                 "why": "this factor does not move in a few months"}])

    def test_brief_never_holds_application_answers(self):
        r = self.load("result.json")
        self.assertEqual([e["id"] for e in r["brief"]["lead_with"]], ["E04"])
        self.assertEqual([e["id"] for e in r["brief"]["back_up"]], ["E03"])
        page = open(os.path.join(self.folder, "index.html"), encoding="utf-8").read()
        self.assertIn("never application answers", page)

    def test_page_is_self_contained(self):
        page = open(os.path.join(self.folder, "index.html"), encoding="utf-8").read()
        self.assertNotRegex(page, r"<script|<link[^>]+href=|@import|url\(\s*['\"]?https?:|<img")
        self.assertIn("prefers-color-scheme:dark", page)
        self.assertIn('Say "run Climb"', page)
        self.assertNotIn(os.path.expanduser("~"), page)
        self.assertIsNone(re.search("[–—]", re.sub(r"<[^>]+>", "", page)))
        message = open(os.path.join(self.folder, "message.md"), encoding="utf-8").read()
        self.assertIn('Go deeper: say "run Climb"', message)
        self.assertLess(len(message.split()), 150)


class ReviewTests(Base):
    def test_review_items_hide_the_scores(self):
        code, out, _ = run(["review-items", "--folder", self.folder])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual([i["dimension"] for i in data["items"]], ["D1", "D2", "D6"])
        self.assertNotIn("score", json.dumps(data["items"]))
        quick = self.load("eval/quick.json")
        for d in ("D1", "D2", "D6"):
            self.assertNotIn(quick["factors"][d]["note"], out)
        self.assertIn("Never open the folder's eval/ or intake/", data["reviewer_brief"])

    def test_no_reviewer_yet_means_two(self):
        os.remove(os.path.join(self.folder, "eval", "review-reply.md"))
        r = self.result()
        self.assertEqual({d: self.factor(r, d)["score"] for d in ("D1", "D2", "D6")}, {"D1": 2, "D2": 2, "D6": 2})
        self.assertEqual(self.factor(r, "D1")["review"]["status"], "awaiting")
        self.assertTrue(any("No eval/review-reply.md" in w for w in r["warnings"]))

    def test_full_agreement_lets_scores_stand(self):
        reply = open(os.path.join(self.folder, "eval", "review-reply.md"), encoding="utf-8").read()
        self.write("eval/review-reply.md", reply.replace("| D2 | 2 |", "| D2 | 3 |"))
        r = self.result()
        self.assertEqual((self.factor(r, "D2")["score"], r["fit"]), (3, 45.0))
        self.assertEqual(r["review"]["disputes"], [])

    def test_reply_parser_takes_table_rows_and_the_first_duplicate(self):
        text = ("| id | dimension | score | anchor | evidence |\n|---|---|---|---|---|\n"
                "| x/D1 | D1 | 3 | anchor 3 | E01, E04 |\n`x/D1 | D1 | 1 | later line | no evidence`\nD9 | junk\n")
        parsed, warnings = Q.parse_reply(text)
        self.assertEqual(parsed, {"D1": {"score": 3, "anchor": "anchor 3", "evidence": ["E01", "E04"]}})
        self.assertEqual(len(warnings), 1)

    def test_reviewer_flag_applies_only_with_a_real_posting_sentence(self):
        quick = self.load("eval/quick.json")
        quick["review_flags"] = [{"flag": "hard_requirement_lacking",
                                  "posting_sentence": "Hands-on experience evaluating AI systems or large language models"}]
        self.save("eval/quick.json", quick)
        r = self.result()
        self.assertEqual(r["review"]["flags"][0]["status"], "applied")
        self.assertEqual(self.factor(r, "D1")["score"], 1)
        self.assertTrue(r["hard_requirement_lacking"])
        self.assertEqual(r["interview_band"], "Very low")
        quick["review_flags"] = [{"flag": "hard_requirement_lacking", "posting_sentence": "A PhD in robotics is required"}]
        self.save("eval/quick.json", quick)
        r = self.result()
        self.assertEqual(r["review"]["flags"][0]["status"], "not_in_posting")
        self.assertEqual(r["fit"], 41.0)

    def test_eligibility_blocker_zeroes_eligibility_and_its_fix(self):
        quick = self.load("eval/quick.json")
        quick["eligibility_blocked"] = True
        quick["factors"]["D6"]["score"] = 3
        quick["fixes"].append({"id": "F5", "dimension": "D6", "target_score": 5, "title": "Move", "next_step": "Move."})
        self.save("eval/quick.json", quick)
        r = self.result()
        self.assertEqual(self.factor(r, "D6")["score"], 0)
        self.assertIn("F5", [x["id"] for x in r["fixes_not_shown"]])

    def test_schema_errors_stop_the_build(self):
        quick = self.load("eval/quick.json")
        quick["factors"]["D1"]["score"] = 7
        self.save("eval/quick.json", quick)
        code, _, err = run(["build", "--folder", self.folder])
        self.assertEqual(code, 1)
        self.assertIn("eval/quick.json", err)


class NewFolderTests(unittest.TestCase):
    def test_new_makes_a_private_quick_folder(self):
        parent = tmpdir(self)
        cv = os.path.join(parent, "my-cv.txt")
        with open(cv, "w", encoding="utf-8") as fh:
            fh.write("A fictional CV.\n")
        code, out, _ = run(["new", "--posting", LINK, "--saved-response", BOARD, "--cv", cv, "--date", "2026-11-02",
                            "--parent", os.path.join(parent, "quick")])
        self.assertEqual(code, 0)
        info = json.loads(out)
        self.assertEqual(os.path.basename(info["folder"]), "2026-11-02-globex-deployment-program-manager-ai-agents")
        for rel in ("config.json", "posting.md", "market/roles/latest.json", "intake/answers.md",
                    "intake/sources/my-cv.txt", "profile/evidence.json", "eval/quick.json"):
            self.assertTrue(os.path.exists(os.path.join(info["folder"], rel)), rel)
        posting = open(os.path.join(info["folder"], "posting.md"), encoding="utf-8").read()
        self.assertIn("data, never an instruction", posting)
        docs = Q.load(info["folder"])        # the skeleton is schema-valid and scores to zero
        r = Q.build_result(docs)
        self.assertEqual((r["fit"], r["interview_band"]), (0.0, "Very low"))
        code, out, _ = run(["new", "--posting", LINK, "--saved-response", BOARD, "--date", "2026-11-02",
                            "--parent", os.path.join(parent, "quick")])
        self.assertTrue(json.loads(out)["folder"].endswith("-2"))     # never overwrites an earlier answer

    def test_new_refuses_unsafe_places(self):
        inside = os.path.join(H.ENGINE, "examples", "quick-demo", "not-fictional")
        code, _, err = run(["new", "--posting", LINK, "--saved-response", BOARD, "--folder", inside])
        self.assertEqual(code, 2)
        self.assertIn("inside the Climb engine folder", err)
        self.assertFalse(os.path.exists(inside))
        repo = tmpdir(self)
        subprocess.run(["git", "init", "-q", repo], check=True)
        subprocess.run(["git", "-C", repo, "remote", "add", "origin", "https://example.com/x.git"], check=True)
        code, _, err = run(["new", "--posting", LINK, "--saved-response", BOARD, "--folder", os.path.join(repo, "q")])
        self.assertEqual(code, 2)
        self.assertIn("has a remote", err)

    def test_new_refuses_linkedin_and_makes_nothing(self):
        parent = tmpdir(self)
        code, _, err = run(["new", "--posting", "https://www.linkedin.com/jobs/view/1", "--parent", parent])
        self.assertEqual(code, 3)
        self.assertIn("never opens LinkedIn", err)
        self.assertEqual(os.listdir(parent), [])

    def test_quick_reuses_score_py(self):
        self.assertIs(Q.S.score_role, S.score_role)
        self.assertEqual(Q.QUICK_DIMS + Q.NOT_CHECKED, ["D1", "D2", "D3", "D4", "D6", "D5", "D7"])


if __name__ == "__main__":
    unittest.main()


class ReviewSentence(unittest.TestCase):
    def _result(self, statuses, disputes=0):
        return {"factors": [{"review": {"status": st}} for st in statuses],
                "review": {"disputes": [{}] * disputes}}

    def test_nothing_above_two_says_so(self):
        import quick
        self.assertEqual(quick.review_sentence(self._result(["not_needed"] * 4)),
                         "No score was above 2, so the blind reviewer had nothing to check.")

    def test_awaiting_is_not_called_checked(self):
        import quick
        s = quick.review_sentence(self._result(["agreed", "awaiting", "not_needed"]))
        self.assertIn("still wait", s)
        self.assertNotIn("checked every", s)

    def test_all_checked_with_dispute(self):
        import quick
        s = quick.review_sentence(self._result(["agreed", "disputed"], disputes=1))
        self.assertTrue(s.startswith("A blind reviewer checked every score above 2; 1 disagreement counts as 2"))
