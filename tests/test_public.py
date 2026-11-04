"""Build in public (scripts/public.py, scripts/_public.py). Fictional data, no network."""
import io
import os
import unittest
from contextlib import redirect_stdout
from unittest import mock

import helpers as H
import _autopilot as APL
import _public as PB
import public as CLI
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


class PublicTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)
        self.config = H.load(os.path.join(self.ws, "config.json"))
        os.remove(os.path.join(self.ws, PB.REL))                       # start with nothing posted
        self.plan = H.load(os.path.join(self.ws, "campaign", "plan.json"))
        self.evidence = H.load(os.path.join(self.ws, "profile", "evidence.json"))

    def run_cli(self, *args):
        return quiet(CLI.main, "--workspace", self.ws, *args, "--date", TODAY)

    def doc(self):
        return H.load(os.path.join(self.ws, PB.REL))

    def test_ideas_come_from_shareable_work_only(self):
        refs = [i["ref"] for i in PB.ideas(self.plan, self.evidence, None, None, TODAY)]
        self.assertEqual(refs, ["A03"])          # done D2 proof; A05 (a tailored CV) and A01 (a network map) are private
        self.assertEqual(PB.ideas(self.plan, self.evidence, None, None, "2026-12-30"), [])   # too long ago

    def test_a_door_you_went_to_is_an_idea_without_names(self):
        doors = {"doors": [{"id": "DR01", "title": "Builders Night", "status": "went", "starts_on": "2026-10-30"}]}
        i = next(i for i in PB.ideas(None, None, doors, None, TODAY) if i["ref"] == "DR01")
        self.assertIn("no one's name without their yes", i["why"])

    def test_a_draft_brief_holds_only_written_facts_and_the_voice(self):
        self.config["public"] = {"voice": "Like I talk. Aussie spelling.", "channels": ["linkedin"]}
        H.save(os.path.join(self.ws, "config.json"), self.config)
        code, out = self.run_cli("draft", "A03")
        self.assertEqual(code, 0, out)
        post = self.doc()["posts"][0]
        self.assertEqual((post["id"], post["about"], post["channel"], post["status"]), ("P01", "A03", "linkedin", "drafted"))
        with open(os.path.join(self.ws, post["draft_file"]), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("Like I talk. Aussie spelling.", text)
        self.assertIn("https://example.com/alex/case-study-scheduling", text)
        self.assertIn("LVLme never posts", text)
        self.assertEqual(self.run_cli("draft", "A03")[0], 1)                 # one post per idea
        self.assertEqual(PB.ideas(self.plan, self.evidence, None, self.doc(), TODAY), [])
        self.assertEqual(self.run_cli("draft", "A01")[0], 1)                 # not an idea: private work

    def test_a_post_counts_as_proof_only_once_its_link_is_checked(self):
        self.run_cli("draft", "A03")
        self.assertEqual(self.run_cli("checked", "P01")[0], 1)               # not posted yet
        self.run_cli("posted", "P01", "--url", "https://example.com/alex/posts/1")
        before = len(H.load(os.path.join(self.ws, "profile", "evidence.json"))["items"])
        code, out = self.run_cli("checked", "P01")
        self.assertEqual(code, 0, out)
        items = H.load(os.path.join(self.ws, "profile", "evidence.json"))["items"]
        self.assertEqual(len(items), before + 1)
        e = items[-1]
        self.assertEqual((e["kind"], e["level"], e["dimensions"], e["sources"][0]["ref"]),
                         ("public_signal", "verified", ["D5"], "https://example.com/alex/posts/1"))
        self.assertEqual(self.doc()["posts"][0]["evidence"], e["id"])
        self.assertEqual(self.run_cli("checked", "P01")[0], 1)               # not twice
        self.assertEqual(quiet(V.main, "--workspace", self.ws)[0], 0)

    def test_cadence_counts_weeks_and_the_run_on_target(self):
        doc = {"posts": [{"status": "posted", "posted_on": d} for d in ("2026-10-13", "2026-10-21", "2026-10-30")]}
        c = PB.cadence(doc, {"public": {"per_week": 1}}, "2026-11-01")
        self.assertEqual([w["posted"] for w in c["weeks"]], [0, 1, 1, 1])
        self.assertEqual((c["this_week"], c["streak"], c["due"]), (1, 3, 0))
        c = PB.cadence(doc, {"public": {"per_week": 1}}, "2026-11-03")     # a new week: still a 3-week run
        self.assertEqual((c["this_week"], c["streak"], c["due"]), (0, 3, 1))

    def test_drafts_and_posts_change_no_score(self):
        def run():
            quiet(S.main, "--workspace", self.ws, "--date", TODAY)
            return H.load(os.path.join(self.ws, "eval", "runs", TODAY + ".json"))
        before = run()
        self.run_cli("draft", "A03")
        self.run_cli("posted", "P01", "--url", "https://example.com/p")
        self.assertEqual(before["roles"], run()["roles"])

    def test_the_weekly_note_and_dashboard_carry_it(self):
        note = APL.week_note(self.ws, self.config, TODAY)
        self.assertEqual((note["public"]["posted"], note["public"]["ref"]), (0, "A03"))
        self.assertIn("Build in public: 0 of 1 post this week. Worth sharing:", APL.note_md(note))
        with open(os.path.join(H.DEMO, "report", "index.html"), encoding="utf-8") as fh:
            self.assertIn('id="publicCard"', fh.read())
        agents = H.load(os.path.join(H.DEMO, "report", "for-agents", "dashboard.json"))
        self.assertEqual(agents["build_in_public"]["cadence"]["this_week"], 1)

    def test_the_skill_never_posts(self):
        with open(os.path.join(H.ENGINE, "skills", "lvlme-public", "SKILL.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("It never posts, and never opens LinkedIn.", text)


if __name__ == "__main__":
    unittest.main()
