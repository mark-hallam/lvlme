"""The proof profile: only checked claims with a public source, the level history, and the leak check."""
import contextlib
import io
import os
import re
import shutil
import tempfile
import unittest

import helpers as H  # noqa: F401, E402
import _proof_profile as PP
import proof_profile as CLI


def copy_demo():
    tmp = tempfile.mkdtemp()
    ws = os.path.join(tmp, "ws")
    shutil.copytree(H.DEMO, ws)
    return tmp, ws


def run(ws, *extra):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = CLI.main(["--workspace", ws, "--date", "2026-11-05", *extra])
    return code, out.getvalue(), err.getvalue()


def edit_evidence(ws, fn):
    path = os.path.join(ws, "profile", "evidence.json")
    doc = H.load(path)
    fn(doc)
    H.save(path, doc)


def page(ws):
    with open(os.path.join(ws, "report", "profile", "index.html"), encoding="utf-8") as fh:
        return fh.read()


class ProofProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp, self.ws = copy_demo()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_builds_the_demo_profile_with_only_checked_public_claims(self):
        code, out, err = run(self.ws)
        self.assertEqual(code, 0, err)
        html = page(self.ws)
        for shown in ("E04", "E07", "E08", "E14", "E15"):
            claim = next(i["claim"] for i in H.load(os.path.join(self.ws, "profile", "evidence.json"))["items"] if i["id"] == shown)
            self.assertIn(claim.replace("'", "&#x27;"), html)
        self.assertEqual(len(re.findall('data-claim-level="', html)), 5)
        self.assertEqual(set(re.findall('data-claim-level="([^"]*)"', html)), {"verified", "corroborated"})
        # checked but with no public link (a document or a pointer): not shown, and counted honestly
        self.assertNotIn("Contoso", html)
        self.assertNotIn("Jordan Sample", html)
        self.assertIn("3 checked claims with no public link", html)

    def test_the_page_explains_verified_and_corroborated(self):
        page = open(os.path.join(H.DEMO, "report", "profile", "index.html"), encoding="utf-8").read()
        self.assertIn("checked directly against the source shown", page)
        self.assertIn("two independent sources agree", page)

    def test_unchecked_and_contradicted_claims_never_appear(self):
        run(self.ws)
        html = page(self.ws)
        for words in ("late deliveries", "led a team of 40", "6 sites", "Bachelor"):
            self.assertNotIn(words, html)

    def test_every_claim_has_a_public_https_link(self):
        run(self.ws)
        html = page(self.ws)
        cards = re.findall(r'<li class="claim".*?</li>', html, re.S)
        self.assertEqual(len(cards), 5)
        for card in cards:
            hrefs = re.findall(r'href="([^"]*)"', card)
            self.assertTrue(hrefs and all(h.startswith("https://") for h in hrefs), card)

    def test_a_private_link_is_not_shown_and_a_claim_left_with_none_is_dropped(self):
        def fn(doc):
            for i in doc["items"]:
                if i["id"] == "E07":
                    i["sources"] = [{"type": "website", "ref": "http://localhost:3000/me"}]
        edit_evidence(self.ws, fn)
        code, _, err = run(self.ws)
        self.assertEqual(code, 0, err)
        html = page(self.ws)
        self.assertNotIn("Personal site with 6 essays", html)
        self.assertNotIn("localhost", html)

    def test_level_history_is_dated_and_current_level_shown(self):
        run(self.ws)
        html = page(self.ws)
        self.assertIn("Level 3 of 5", html)
        for date in ("4 Oct 2026", "25 Oct 2026", "1 Nov 2026"):
            self.assertIn(date, html)
        self.assertEqual(html.count("Level up</span>"), 1)
        self.assertIn("A program, applied AI or policy role", html)

    def test_level_events_from_the_journey_workstream_are_used_when_present_and_not_needed(self):
        run(self.ws)
        self.assertNotIn("Goal reached", page(self.ws))
        H.save(os.path.join(self.ws, "eval", "levels.json"),
               {"events": [{"date": "2026-11-01", "kind": "goal_reached", "from_level": 3, "to_level": 5,
                            "role_id": "acme:a-1", "evidence": ["E04"]}]})
        run(self.ws)
        html = page(self.ws)
        self.assertIn("Goal reached", html)
        self.assertNotIn("acme:a-1", html)

    def test_page_is_self_contained_light_first_with_dark_and_phone_rules(self):
        run(self.ws)
        html = page(self.ws)
        self.assertNotRegex(html, r"(?i)<script|<link|<img|<iframe|@import|url\(")
        self.assertLess(html.index("--bg:#fff"), html.index("prefers-color-scheme:dark"))
        self.assertIn("max-width:480px", html)
        self.assertIn('name="viewport"', html)
        self.assertIn("-apple-system", html)
        self.assertEqual(re.findall("[–—]", html), [])

    def test_agent_file_matches_the_page(self):
        run(self.ws)
        facts = H.load(os.path.join(self.ws, "report", "profile", "profile.json"))
        self.assertEqual([c["id"] for c in facts["claims"]], ["E04", "E07", "E08", "E14", "E15"])
        self.assertEqual(facts["checked_claims_without_public_link"], 3)

    def test_demo_is_labelled_fictional(self):
        run(self.ws)
        self.assertIn("fictional demo profile", page(self.ws))

    def test_committed_demo_profile_is_current(self):
        run(self.ws)
        with open(os.path.join(H.DEMO, "report", "profile", "index.html"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), page(self.ws), "rebuild: python3 scripts/proof_profile.py --workspace examples/demo-workspace --date 2026-11-05")


class LeakCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp, self.ws = copy_demo()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def refuse(self, claim, reason, level="verified"):
        def fn(doc):
            doc["items"].append({"id": "E99", "claim": claim, "kind": "artefact", "level": level,
                                 "sources": [{"type": "website", "ref": "https://example.com/proof"}]})
        edit_evidence(self.ws, fn)
        path = os.path.join(self.ws, "report", "profile", "index.html")
        if os.path.exists(path):
            os.remove(path)
        code, _, err = run(self.ws)
        self.assertEqual(code, 1, claim)
        self.assertIn("was not written", err)
        self.assertIn(reason, err)
        self.assertFalse(os.path.exists(path), "a refused build must write nothing")

    def test_refuses_an_email_address(self):
        self.refuse("Built a tool, questions to alex@example.org", "email address")

    def test_refuses_a_phone_number(self):
        self.refuse("Talk organiser, call +61 412 345 678", "phone number")
        self.refuse("Talk organiser, call (07) 3555 0123", "phone number")

    def test_refuses_a_home_folder_path(self):
        self.refuse("Code lives in /" + "Users/alex/code/route-eval", "folder path")
        self.refuse("Code lives in ~/code/route-eval", "folder path")

    def test_refuses_a_private_network_or_local_link_in_a_claim(self):
        self.refuse("Demo at http://192.168.1.20:8000/demo", "private-network")
        self.refuse("Demo at https://tool.internal/demo", "private-network")

    def test_refuses_a_name_the_person_asked_to_keep_out(self):
        self.refuse("Ran the Contoso Freight rollout", "Contoso Freight")

    def test_dates_and_ordinary_numbers_are_not_phone_numbers(self):
        self.assertEqual(PP.leak_problems("<p>Released 2026-10-04, 14 releases, 2,500 users, 12 345 downloads</p>"), [])

    def test_the_guard_refuses_any_claim_below_corroborated_even_if_one_slips_through(self):
        for level in ("partially_verified", "self_reported", "unverified", "contradicted"):
            bad = '<li class="claim" data-claim-level="%s"><p>x</p></li>' % level
            self.assertIn("below corroborated", " ".join(PP.leak_problems(bad)), level)

    def test_the_guard_refuses_loading_from_outside(self):
        self.assertTrue(PP.leak_problems('<img src="https://cdn.example.com/a.png">'))
        self.assertTrue(PP.leak_problems('<script src="https://cdn.example.com/a.js"></script>'))

    def test_clean_build_passes(self):
        code, _, err = run(self.ws)
        self.assertEqual(code, 0, err)


if __name__ == "__main__":
    unittest.main()
