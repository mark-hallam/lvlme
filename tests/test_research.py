"""Research packs (scripts/_research.py): one sourced page per target. Fictional data, no network."""
import os
import unittest

import helpers as H
import _research as RS

TODAY = "2026-11-01"


class PackTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)
        load = lambda *p: H.load(os.path.join(self.ws, *p))   # noqa: E731
        self.config, self.orgs = load("config.json"), load("market", "orgs.json")
        self.roles, self.doors = load("market", "roles", "latest.json"), load("market", "doors.json")

    def pack(self, org, **target):
        t = dict(next(t for t in self.config["targets"] if t["id"] == org), **target)
        return RS.pack(t, self.config, self.orgs, self.roles, self.doors, TODAY)

    def test_every_line_has_a_source_and_every_pack_says_what_was_not_checked(self):
        for t in self.config["targets"]:
            p = self.pack(t["id"])
            lines = [x for _, ls in p["sections"] for x in ls]
            self.assertTrue(lines, t["id"])
            self.assertTrue(all(x["source"] for x in lines), t["id"])
            self.assertTrue(all(x["seen_on"] or x["source"].startswith("config.json") for x in lines), t["id"])
            self.assertEqual(p["unchecked"], sum(1 for x in lines if not x["checked"]))

    def test_an_unverified_fact_is_marked_not_yet_checked(self):
        p = self.pack("acme")
        news = dict(p["sections"])["Recent news"]
        self.assertEqual((news[0]["seen_on"], news[0]["checked"]), ("2026-10-14", False))   # published date, unchecked
        page = RS.render(p, TODAY, fictional=True)
        self.assertIn("Not yet checked", page)
        self.assertIn('href="https://example.com/news/acme-sydney"', page)

    def test_the_pack_brings_in_roles_doors_and_the_ai_rules(self):
        titles = dict(self.pack("acme")["sections"])
        self.assertIn("open role", titles["Teams hiring"][0]["text"])
        self.assertTrue(any("Fellows" in x["text"] for x in titles["Events and programmes"]))
        self.assertIn("No published rules", titles["Its rules on AI for candidates"][0]["text"])
        ai = dict(self.pack("acme", ai_policy={"first_draft_by_person": True, "source": "https://example.com/ai",
                                               "checked_on": "2026-10-01"})["sections"])["Its rules on AI for candidates"]
        self.assertEqual(ai[0]["text"], "Acme AI asks for your own first draft. Write it, then I'll review it.")

    def test_the_demo_builds_a_pack_for_each_target_and_the_dashboard_links_them(self):
        for t in self.config["targets"]:
            self.assertTrue(os.path.isfile(os.path.join(H.DEMO, "report", "research", t["id"] + ".html")), t["id"])
        agents = H.load(os.path.join(H.DEMO, "report", "for-agents", "dashboard.json"))
        self.assertEqual(sorted(agents["research_packs"]), sorted(t["id"] for t in self.config["targets"]))
        with open(os.path.join(H.DEMO, "report", "index.html"), encoding="utf-8") as fh:
            self.assertIn('"packs":{"acme":{"path":"research/acme.html"', fh.read())


if __name__ == "__main__":
    unittest.main()
