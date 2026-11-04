"""LVLme quick's result builder, offline, on the fictional demo (Alex Example and a made-up Globex Labs posting)."""
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
import _quick_html as QH
import quick as Q
import score as S

sys.path.insert(0, os.path.join(H.ENGINE, "examples"))
import build_quick_demo as D  # noqa: E402

LINK = D.LINK
BOARD = os.path.join(H.FIXTURES, "quick", "ashby-board.json")


def tmpdir(test):
    d = tempfile.mkdtemp(prefix="lvlme-quick-test-")
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
                         ("globex_labs_example:0b6f3c2e-1a2b-4c3d-8e9f-000000000001/D2", 2, "awaiting_tie_break"))
        self.assertEqual(self.factor(r, "D3")["review"]["status"], "not_needed")

    def test_fixes_are_ranked_and_capped(self):
        r = self.load("result.json")
        self.assertEqual([(f["id"], f["from"], f["to"], f["gain"]) for f in r["fixes"]],
                         [("F1", 1, 3, 8.0), ("F2", 2, 3, 4.0), ("F3", 2, 3, 2.0)])   # F1 asked for 4; the cap allows +2
        self.assertEqual(r["if_all_fixes"], {"fit": 55.0, "interview_band": "Moderate", "offer_band": "Low", "gain": 14.0})
        self.assertEqual(r["fixes_not_shown"], [{"id": "F4", "dimension": "D1", "title": "Add customer-facing deployment experience",
                                                 "why": "requirements match does not move in a few months"}])

    def test_a_left_out_fix_is_named_with_its_reason(self):
        """A fix the agent suggested never disappears without a word: the page always says why, and the
        message does too when fewer than three fixes are shown."""
        line = 'Not listed: "Add customer-facing deployment experience", because requirements match does not move in a few months.'
        page = open(os.path.join(self.folder, "index.html"), encoding="utf-8").read()
        self.assertIn(line, page.replace("&quot;", '"'))
        self.assertNotIn("Not listed", open(os.path.join(self.folder, "message.md"), encoding="utf-8").read())
        quick = self.load("eval/quick.json")
        quick["fixes"] = [f for f in quick["fixes"] if f["id"] != "F3"]
        self.save("eval/quick.json", quick)
        result, message = Q.build(self.folder)
        self.assertEqual(len(result["fixes"]), 2)
        self.assertIn(line, message)
        self.assertLess(len(message.split()), 150)

    def test_every_left_out_fix_is_named_so_the_agent_cannot_add_one(self):
        # An agent once told the person the page listed a left-out fix it did not; now every one is named.
        r = self.load("result.json")
        r["fixes_not_shown"] = [{"id": "F9", "dimension": "D2", "title": "Smaller",
                                 "why": "it is not in the top 3 (+1 fit points)"},
                                {"id": "F8", "dimension": "D2", "title": "Same", "why": "another fix to the same factor adds more"}]
        self.assertEqual(QH.not_shown_lines(r), [
            'Not listed: "Smaller", because it is not in the top 3 (+1 fit points).',
            'Not listed: "Same", because another fix to the same factor adds more.'])

    def test_brief_never_holds_application_answers(self):
        r = self.load("result.json")
        self.assertEqual([e["id"] for e in r["brief"]["lead_with"]], ["E04"])
        self.assertEqual([e["id"] for e in r["brief"]["back_up"]], ["E03"])
        page = open(os.path.join(self.folder, "index.html"), encoding="utf-8").read()
        self.assertIn("never application answers", page)

    def test_a_fictional_posting_sends_no_one_to_a_real_job_board(self):
        """The demo's made-up posting is shown as plain text, never as a link to a real board."""
        page = open(os.path.join(self.folder, "index.html"), encoding="utf-8").read()
        self.assertNotIn("Open the posting", page)
        self.assertNotRegex(page, r'href="https?://[^"]*(ashbyhq|greenhouse|lever|workday|smartrecruiters|workable)')
        self.assertIn("fictional posting", page)
        posting = open(os.path.join(self.folder, "posting.md"), encoding="utf-8").read()
        self.assertIn("(a fictional posting: this address has no real page)", posting)
        self.assertIn("/globex-labs-example/", D.LINK)  # a board name no real employer uses
        # a real folder still links to its posting
        result = Q.build_result(Q.load(self.folder))
        result["fictional"] = False
        import _quick_html
        self.assertIn('<a class="posting" href="%s">Open the posting</a>' % D.LINK, _quick_html.render(result))

    def test_page_is_self_contained(self):
        page = open(os.path.join(self.folder, "index.html"), encoding="utf-8").read()
        self.assertNotRegex(page, r"<script|<link[^>]+href=|@import|url\(\s*['\"]?https?:|<img")
        self.assertIn("prefers-color-scheme:dark", page)
        self.assertIn('Say to your agent</span> <b>"run LVLme"</b>', page)
        self.assertNotIn(os.path.expanduser("~"), page)
        self.assertIsNone(re.search("[–—]", re.sub(r"<[^>]+>", "", page)))
        message = open(os.path.join(self.folder, "message.md"), encoding="utf-8").read()
        self.assertIn('Go deeper: say "run LVLme"', message)
        self.assertLess(len(message.split()), 150)


class NotCheckedTests(Base):
    """Public signal and application readiness cannot be checked from one posting and a CV: shown as not
    checked, with the fit as a range (today's fit, up to the fit if both turned out strong), never a silent 0."""

    def page(self):
        with open(os.path.join(self.folder, "index.html"), encoding="utf-8") as fh:
            return fh.read()

    def test_the_fit_is_a_range_and_the_odds_stay_today_s(self):
        r = self.load("result.json")
        self.assertEqual((r["fit"], r["interview_band"], r["offer_band"]), (41.0, "Low", "Very low"))
        self.assertEqual(r["if_unchecked_strong"],
                         {"fit": 56.0, "interview_band": "Moderate", "offer_band": "Low", "gain": 15.0})
        # the top of the range adds exactly the unchecked factors' full weight: 10 + 5 out of 100
        self.assertEqual(r["if_unchecked_strong"]["gain"], sum(x["max_points"] for x in r["not_checked"]))
        self.assertEqual([(x["dimension"], x["status"], x["max_points"]) for x in r["not_checked"]],
                         [("D5", "not_checked", 10.0), ("D7", "not_checked", 5.0)])
        self.assertTrue(all(x["what"] for x in r["not_checked"]))

    def test_strong_unchecked_factors_pass_the_caps_and_keep_the_band_rules(self):
        """The top of the range is the scoring maths: D5 and D7 count 5, and the cold-application cap still holds."""
        ev = self.load("profile/evidence.json")
        quick = self.load("eval/quick.json")
        for d in ("D1", "D2", "D4"):
            quick["factors"][d].update(score=5, evidence=["E04"])          # E04 is verified
        self.save("eval/quick.json", quick)
        self.write("eval/review-reply.md", "".join("x/%s | %s | 5 | anchor 5 | E04\n" % (d, d) for d in ("D1", "D2", "D4"))
                   + "D6/quick | D6 | 5 | anchor | E05\n")
        self.assertIn("E04", [e["id"] for e in ev["items"]])
        r = self.result()
        self.assertEqual((r["fit"], r["interview_band"], r["offer_band"]), (69.0, "Moderate", "Low"))
        top = r["if_unchecked_strong"]
        self.assertEqual((top["fit"], top["interview_band"]), (84.0, "Good"))
        self.assertEqual(top["offer_band"], "Low")          # the offer table says Moderate; D3 at 1 caps it at Low
        docs = Q.load(self.folder)
        flags = Q.check_flags(docs["quick"], docs["role"])
        scored, _ = Q.score(docs, flags, set(r["review"]["agreed"]), {"D5": 5, "D7": 5})
        self.assertEqual((scored["scores"]["D5"]["score"], scored["scores"]["D7"]["score"]), (5, 5))

    def test_the_page_shows_them_as_not_checked_with_the_range(self):
        page = self.page()
        self.assertIn('<b class="num">41</b> today, up to <b class="num">56</b>', page)
        self.assertIn('<i class="maybe" style="width:15%">', page)
        self.assertEqual(page.count('<span class="score nc">Not checked</span>'), 2)
        self.assertIn("Up to 10 fit points", page)
        self.assertIn("Up to 5 fit points", page)
        self.assertIn("the fit is <b class=\"num\">56</b> instead of 41: moderate chance of an interview, low chance "
                      "of an offer", page)
        self.assertNotIn("five factors", page)     # the old line said 41 was out of 100 on five factors: it is not

    def test_the_message_gives_the_range(self):
        with open(os.path.join(self.folder, "message.md"), encoding="utf-8") as fh:
            message = fh.read()
        self.assertIn("Odds today: Low chance of an interview, very low chance of an offer.\n", message)
        self.assertIn("Fit 41 of 100 today, up to 56 if public signal and application readiness (not checked here) "
                      "turn out strong.", message)

    def test_no_range_when_the_unchecked_factors_could_add_nothing(self):
        import _quick_html as QH
        r = self.load("result.json")
        r["if_unchecked_strong"] = dict(r["if_unchecked_strong"], fit=r["fit"], gain=0.0)
        page = QH.render(r)
        self.assertNotIn("up to <b", page)
        self.assertNotIn('class="maybe"', page)
        self.assertNotIn('class="note"', page)
        self.assertEqual(QH.fit_sentence(r), "Fit 41 of 100.")
        del r["if_unchecked_strong"]                    # a result.json from before the range still renders
        self.assertIn("Not checked", QH.render(r))

    def test_header_says_hybrid_not_remote(self):
        import _quick_html as QH
        r = self.load("result.json")
        r["role"] = dict(r["role"], locations=["London, UK"], remote=False, workplace="Hybrid")
        self.assertIn("London, UK · Hybrid", QH.hero(r))
        self.assertNotIn("Remote", QH.hero(r))
        r["role"] = dict(r["role"], remote=True, workplace="Remote")
        self.assertIn("London, UK · Remote", QH.hero(r))


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

    def test_reply_parser_takes_the_factor_by_code_name_or_item_id(self):
        # Real reviewers wrote "D1 Requirements match" or the name alone; each must still count.
        for line in ("x | D1 Requirements match | 2 | 2, Partial | E01, E02 (E04 at most 1)",
                     "x | Requirements match | 2 | Partial | E01, E02",
                     "x/D1 | the first factor | **2** | Partial | E01, E02"):
            parsed, warnings = Q.parse_reply(line)
            self.assertEqual(parsed["D1"]["score"], 2, line)
            self.assertEqual(warnings, [], line)

    def test_an_unreadable_reply_is_said_plainly_never_as_waiting(self):
        self.write("eval/review-reply.md", "The reviewer thought D1 deserved a 2.\n")
        r = self.result()
        self.assertEqual(self.factor(r, "D1")["review"]["status"], "unreadable")
        self.assertEqual(self.factor(r, "D1")["score"], 2)
        self.assertTrue(any("no score line LVLme can read" in w for w in r["warnings"]))
        self.assertIn("no readable score", Q.review_sentence(r))
        self.assertNotIn("still wait", Q.review_sentence(r))

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

    def test_a_missing_hard_requirement_is_said_in_the_chat_and_the_fixes_card(self):
        quick = self.load("eval/quick.json")
        quick["hard_requirement_lacking"] = True
        quick["hard_requirement_note"] = "5+ years deploying language models"
        self.save("eval/quick.json", quick)
        result, message = Q.build(self.folder)
        self.assertEqual(result["fixes_not_shown"][0]["dimension"], "D1")
        line = ("A hard requirement is missing (5+ years deploying language models), so both chances drop a step, "
                "and none of the fixes below changes that. The requirements match fix (\"Add customer-facing "
                "deployment experience\") is not listed because requirements match does not move in a few months.")
        self.assertIn(line, message)
        self.assertLess(message.index(line), message.index("The fixes that would raise them most"))
        page = open(os.path.join(self.folder, "index.html"), encoding="utf-8").read()
        fixes_card = page[page.index('id="fixH"'):]
        self.assertIn("none of the fixes below changes that", fixes_card[:fixes_card.index("</section>")])

    def test_no_hard_requirement_line_when_none_is_missing(self):
        result, message = Q.build(self.folder)
        self.assertFalse(result["hard_requirement_lacking"])
        self.assertNotIn("hard requirement", message.lower())

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


class JudgedByTests(Base):
    """Different AI agents can judge the same evidence differently, so the result names which one judged."""

    def test_the_agent_and_model_reach_the_result_and_its_page(self):
        q = self.load("eval/quick.json")
        q["judged_by"] = {"agent": "Codex", "model": "gpt-5-codex"}
        self.save("eval/quick.json", q)
        with mock.patch("sys.stdout", io.StringIO()):
            result, text = Q.build(self.folder)
        self.assertEqual(result["judged_by"], {"agent": "Codex", "model": "gpt-5-codex"})
        with open(os.path.join(self.folder, "index.html"), encoding="utf-8") as fh:
            page = fh.read()
        self.assertIn("Judged by Codex, using the model gpt-5-codex. Another AI agent, or another run, can judge the same evidence differently", page)
        self.assertLess(len(text.split()), 150)        # the chat message stays short; the page says who judged

    def test_the_blind_reviewer_is_named_when_recorded(self):
        q = self.load("eval/quick.json")
        q["reviewed_by"] = {"agent": "Claude Code helper agent (lvlme:reviewer)", "model": "claude-opus-5-5"}
        self.save("eval/quick.json", q)
        with mock.patch("sys.stdout", io.StringIO()):
            result, _ = Q.build(self.folder)
        page = QH.render(result)
        self.assertIn("The blind reviewer was Claude Code helper agent (lvlme:reviewer), using the model claude-opus-5-5, "
                      "a separate agent that saw none of the first scores.", page)
        self.assertNotIn("The blind reviewer was", QH.render(dict(result, reviewed_by=None)))

    def test_the_top_card_names_the_judge_and_evidence_is_in_order(self):
        q = self.load("eval/quick.json")
        q["judged_by"] = {"agent": "Codex"}
        self.save("eval/quick.json", q)
        with mock.patch("sys.stdout", io.StringIO()):
            result, _ = Q.build(self.folder)
        page = QH.render(result)
        top = page[page.index('aria-labelledby="oddsH"'):page.index('aria-labelledby="whyH"')]
        self.assertIn("Judged by Codex.", top)
        for f in result["factors"]:
            ids = re.findall(r'<span class="id">(E\d+)</span>', QH.evidence_list(f["evidence"]))
            self.assertEqual(ids, sorted(ids))

    def test_not_recorded_is_said_plainly(self):
        result = self.result()
        self.assertIsNone(result["judged_by"])
        self.assertIn("Which AI agent judged was not recorded.", QH.render(result))

    def test_the_schema_accepts_it(self):
        import validate as V
        q = self.load("eval/quick.json")
        q["judged_by"] = {"agent": "Claude Code"}
        self.assertEqual(V.check(q, H.schema("quick.schema.json")), [])
        q["judged_by"] = {"model": "x"}
        self.assertNotEqual(V.check(q, H.schema("quick.schema.json")), [])


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
        self.assertEqual(os.path.basename(info["folder"]), "2026-11-02-globex-labs-example-deployment-program-manager-ai-agents")
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

    def test_a_guessed_employer_name_is_flagged_and_org_corrects_it(self):
        # The demo board slug "globex-labs-example" is never written that way in the posting, so its name is a guess.
        parent = tmpdir(self)
        code, out, err = run(["new", "--posting", LINK, "--saved-response", BOARD, "--date", "2026-11-02",
                              "--parent", os.path.join(parent, "quick")])
        self.assertEqual(code, 0, err)
        info = json.loads(out)
        self.assertEqual((info["org_name"], info["org_name_guessed"]), ("Globex Labs Example", True))
        self.assertIn("is a guess from the link", err)
        code, out, err = run(["new", "--posting", LINK, "--saved-response", BOARD, "--date", "2026-11-02",
                              "--org", "Globex Labs", "--parent", os.path.join(parent, "quick")])
        info = json.loads(out)
        self.assertNotIn("org_name_guessed", info)
        self.assertEqual(info["org_name"], "Globex Labs")
        self.assertNotIn("is a guess", err)

    def test_an_employer_that_asks_for_your_own_first_draft_is_named(self):
        """Anthropic's rule (read on its own page) goes on the target, the message and the brief; others get none."""
        parent = tmpdir(self)
        code, out, err = run(["new", "--posting", LINK, "--saved-response", BOARD, "--date", "2026-11-02",
                              "--org", "Anthropic", "--parent", os.path.join(parent, "quick")])
        self.assertEqual(code, 0, err)
        folder = json.loads(out)["folder"]
        target = H.load(os.path.join(folder, "config.json"))["targets"][0]
        self.assertEqual(target["ai_policy"], {"first_draft_by_person": True, "checked_on": "2026-11-03",
                                               "source": "https://www.anthropic.com/candidate-ai-guidance"})
        result = Q.build_result(Q.load(folder))
        message = Q.message(result, folder)
        self.assertIn("Anthropic asks for your own first draft. Write it, then I'll review it. Their guidance: "
                      "https://www.anthropic.com/candidate-ai-guidance", message)
        self.assertLess(len(message.split()), 150)
        page = QH.render(result)
        self.assertIn('Anthropic asks for your own first draft. Write it, then ask your agent to review it. <a class="guide" '
                      'href="https://www.anthropic.com/candidate-ai-guidance">Their guidance on AI use</a>, checked '
                      '3 November 2026.', page)
        code, out, _ = run(["new", "--posting", LINK, "--saved-response", BOARD, "--date", "2026-11-02",
                            "--org", "Globex Labs", "--parent", os.path.join(parent, "quick")])
        other = json.loads(out)["folder"]
        self.assertNotIn("ai_policy", H.load(os.path.join(other, "config.json"))["targets"][0])
        self.assertNotIn("first draft", Q.message(Q.build_result(Q.load(other)), other))

    def test_new_refuses_unsafe_places(self):
        inside = os.path.join(H.ENGINE, "examples", "quick-demo", "not-fictional")
        code, _, err = run(["new", "--posting", LINK, "--saved-response", BOARD, "--folder", inside])
        self.assertEqual(code, 2)
        self.assertIn("inside the LVLme engine folder", err)
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
