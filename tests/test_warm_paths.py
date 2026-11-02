"""The warm-path tracker (campaign/warm-paths.json): schema, checks, no effect on any score, the dashboard strip,
the static summary and the agent files, with contact names hidden unless the person opts in."""
import html
import json
import os
import re
import unittest
from unittest import mock

import helpers as H
import _warm_paths as W
import build_dashboard as B
import score as S
import validate as V

DEMO_DATE = "2026-11-01"


def page_data(ws):
    with open(os.path.join(ws, "report", "index.html"), encoding="utf-8") as fh:
        page = fh.read()
    blob = re.search(r'<script type="application/json" id="data">(.*?)</script>', page, re.S).group(1)
    return page, json.loads(blob)


class SchemaAndChecksTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)
        self.path = os.path.join(self.ws, "campaign", "warm-paths.json")
        self.doc = H.load(self.path)

    def check(self, change=None):
        if change:
            change(self.doc)
        H.save(self.path, self.doc)
        errors, warnings, checked = V.validate_workspace(self.ws)
        return [e for e in errors if "warm-paths" in e], [w for w in warnings if "warm-paths" in w], checked

    def test_demo_and_template_are_valid(self):
        errors, warnings, checked = self.check()
        self.assertIn(W.REL, checked)
        self.assertEqual((errors, warnings), ([], []))
        template = H.load(os.path.join(H.ENGINE, "templates", "campaign", "warm-paths.json"))
        self.assertEqual(V.check(template, H.schema("warm-paths.schema.json")), [])
        self.assertEqual(template["contacts"], [])

    def test_schema_keeps_the_ladder(self):
        schema = H.schema("warm-paths.schema.json")
        self.assertEqual(schema["definitions"]["stage"]["enum"], W.STAGES)
        self.assertEqual(W.STAGES, ["followed", "talked", "connected", "knows_your_work", "would_refer"])
        bad = H.deep(self.doc)
        bad["contacts"][0]["stage"] = "best_friends"
        bad["contacts"][1].pop("updated_on")
        bad["contacts"][2]["x_from_old_tool"] = "kept"            # extension fields are allowed
        errors = V.check(bad, schema)
        self.assertEqual(len(errors), 2, errors)
        self.assertIn("best_friends", errors[0])
        self.assertIn("updated_on", errors[1])

    def test_cross_file_checks(self):
        def change(doc):
            c = doc["contacts"]
            c.append(dict(H.deep(c[0]), id="W01", person="Someone Else"))          # duplicate id
            c.append(dict(H.deep(c[1]), id="W06"))                                 # same person twice
            c.append({"id": "W07", "org": "hooli", "person": "Pat Nobody", "stage": "talked", "updated_on": "2026-10-01"})
            c[2]["evidence"] = ["E99"]
            c[2]["action"] = "A99"
            c[3]["stage"] = "would_refer"                                          # no evidence, and history disagrees
            c[0]["updated_on"] = "2026-10-01"                                      # earlier than its history
            c[1]["history"] = [{"stage": "talked", "on": "2026-10-11"}, {"stage": "followed", "on": "2026-09-01"}]
        errors, warnings, _ = self.check(change)
        text = "\n".join(errors + warnings)
        self.assertIn("duplicate contact id W01", "\n".join(errors))
        self.assertIn("W03 cites evidence E99", "\n".join(errors))
        self.assertIn("W03 names action A99", "\n".join(errors))
        self.assertIn("W06 is a second entry for the same person at globex", "\n".join(warnings))
        self.assertIn("W07 is at hooli, not a current target", "\n".join(warnings))
        self.assertIn("W04 would refer, with no evidence cited", "\n".join(warnings))
        self.assertIn("W04: stage is would_refer, but the latest history entry says followed", text)
        self.assertIn("W01: updated_on 2026-10-01 is earlier than the latest history entry (2026-10-24)", text)
        self.assertIn("W02: history is not oldest first", text)
        self.assertEqual(len(errors), 3, errors)

    def test_missing_file_is_fine(self):
        os.remove(self.path)
        errors, warnings, checked = V.validate_workspace(self.ws)
        self.assertEqual(errors, [])
        self.assertNotIn(W.REL, checked)


class NoScoreChangeTests(unittest.TestCase):
    """Progress only: the tracker never moves a score."""

    def test_score_is_identical_with_any_tracker(self):
        ws = H.copy_demo(self)
        config = H.load(os.path.join(ws, "config.json"))
        path = os.path.join(ws, "campaign", "warm-paths.json")
        with_tracker = S.build_run(ws, config, DEMO_DATE)
        doc = H.load(path)
        for c in doc["contacts"]:
            c["stage"] = "would_refer"
        H.save(path, doc)
        everyone_refers = S.build_run(ws, config, DEMO_DATE)
        os.remove(path)
        without = S.build_run(ws, config, DEMO_DATE)
        self.assertEqual(with_tracker, without)
        self.assertEqual(everyone_refers, without)
        saved = H.load(os.path.join(ws, "eval", "runs", DEMO_DATE + ".json"))
        self.assertEqual([r["fit"] for r in saved["roles"]], [r["fit"] for r in without["roles"]])


class SummaryTests(unittest.TestCase):
    def test_per_org_and_ordering(self):
        doc = {"contacts": [
            {"id": "W02", "org": "b", "person": "P Two", "stage": "followed", "updated_on": "2026-01-02"},
            {"id": "W01", "org": "b", "person": "P One", "stage": "knows_your_work", "updated_on": "2026-01-01"},
            {"id": "W03", "org": "zzz", "person": "P Three", "stage": "would_refer", "updated_on": "2026-01-01"},
            {"id": "W04", "org": "a", "person": "P Four", "stage": "nonsense", "updated_on": "2026-01-01"}]}
        stats = W.per_org(doc, ["a", "b"])
        self.assertEqual(list(stats), ["a", "b"])
        self.assertEqual((stats["a"]["people"], stats["a"]["furthest"]), (0, None))
        self.assertEqual((stats["b"]["people"], stats["b"]["furthest"]), (2, "knows_your_work"))
        self.assertEqual(W.stage_counts_text(stats["b"]["by_stage"]), "1 followed, 1 knows your work")
        self.assertEqual([c["id"] for c in W.ordered_contacts(doc, ["a", "b"])], ["W01", "W02"])
        self.assertEqual(W.org_line("Acme", stats["a"]), "Acme: no one yet")
        self.assertEqual(W.org_line("B Co", stats["b"]), "B Co: furthest Knows your work; 2 people (1 followed, 1 knows your work)")
        self.assertEqual(W.per_org(None, ["a"])["a"]["people"], 0)


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)

    def build(self, privacy=None):
        if privacy is not None:
            cfg = H.load(os.path.join(self.ws, "config.json"))
            cfg["privacy"] = dict(cfg.get("privacy") or {}, **privacy)
            H.save(os.path.join(self.ws, "config.json"), cfg)
        with mock.patch("sys.stdout"):
            self.assertEqual(B.main(["--workspace", self.ws]), 0)
        page, d = page_data(self.ws)
        payload = H.load(os.path.join(self.ws, "report", "for-agents", "dashboard.json"))
        with open(os.path.join(self.ws, "report", "for-agents", "SUMMARY.md"), encoding="utf-8") as fh:
            summary = fh.read()
        return page, d, payload, summary

    def test_strip_data_and_names_hidden_by_default(self):
        page, d, payload, summary = self.build()
        warm = d["warm"]
        self.assertEqual(warm["stages"], ["Followed", "Talked", "Connected", "Knows your work", "Would refer"])
        orgs = {o["id"]: o for o in warm["orgs"]}
        self.assertEqual([o["id"] for o in warm["orgs"]], ["acme", "globex", "initech"])
        self.assertEqual((orgs["globex"]["people"], orgs["globex"]["furthest"], orgs["globex"]["counts"]), (2, 2, [1, 0, 1, 0, 0]))
        self.assertEqual((orgs["acme"]["furthest"], orgs["initech"]["furthest"]), (1, 0))
        self.assertEqual(orgs["globex"]["g"], "globex")
        self.assertEqual({c["who"] for c in warm["contacts"]}, {"A contact"})
        for name in ("Jordan", "Casey", "Riley", "Harper", "Placeholder", "Mock"):
            self.assertNotIn(name, page)
        # The strip sits in Start here (right pane on wide screens, its own card on narrower ones), before Biggest unlocks.
        body = page.split('<script type="application/json"')[0]
        self.assertLess(body.index('id="warmCard"'), body.index('id="unlocksCard"'))
        self.assertIn('<div class="card pair" id="warmCard" hidden>', body)
        self.assertIn("<h2 class=\"pane-h\" style=\"margin:18px 0 0\">Warm paths</h2>", page)
        self.assertLess(page.index("${doNextHTML()}</div>\n    ${warm ?"), page.index(">Biggest unlocks</h2>"))
        self.assertIn('<span class="sr-only">furthest stage: </span>', page)        # the words carry it, not colour alone
        self.assertIn('<span class="wp-bar" aria-hidden="true">', page)
        self.assertIn("Progress only: it changes no score.", page)
        # Agent files: sensitive mode (the demo's) keeps the counts and leaves the contacts out.
        wp = payload["warm_paths"]
        self.assertTrue(payload["sensitive_mode"])
        self.assertNotIn("contacts", wp)
        self.assertEqual(wp["per_org"]["globex"]["furthest_stage"], "connected")
        self.assertIn("## Warm paths (progress only: changes no score", summary)
        self.assertIn("- Globex Labs: furthest Connected; 2 people (1 followed, 1 connected)", summary)
        self.assertIn("- Contacts are left out in sensitive mode.", summary)

    def test_agent_files_hide_names_unless_shared(self):
        _, _, payload, summary = self.build({"sensitive_mode": False})
        contacts = payload["warm_paths"]["contacts"]
        self.assertEqual([c["id"] for c in contacts], ["W03", "W01", "W02", "W04"])    # target order, furthest first
        self.assertEqual({c["person"] for c in contacts}, {"[contact]"})
        self.assertNotIn("Jordan", summary)
        self.assertIn("  - [contact] (Program Manager): Connected, updated 2026-10-24. Next: Send the route-eval", summary)
        _, d, payload, summary = self.build({"sensitive_mode": False, "share_contact_names_with_agents": True,
                                             "show_contact_names_in_dashboard": True})
        self.assertIn("Jordan Sample", [c["person"] for c in payload["warm_paths"]["contacts"]])
        self.assertIn("  - Jordan Sample (Program Manager): Connected", summary)
        self.assertIn("Harper Mock", {c["who"] for c in d["warm"]["contacts"]})

    def test_static_summary_lists_the_warm_paths(self):
        page, _, _, _ = self.build()
        body = page.split('<script type="application/json"')[0]
        section = re.search(r'<section class="card static-sum" id="staticSummary"[^>]*>(.*?)</section>', body, re.S).group(1)
        text = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", section)))
        self.assertIn('<table aria-labelledby="staticWarmH">', section)
        self.assertIn("Globex Labs Connected 1 followed, 1 connected", text)
        self.assertIn("Initech Robotics Followed 1 followed", text)
        self.assertNotRegex(text, "[–—]| - ")

    def test_no_tracker_file_shows_empty_strips(self):
        os.remove(os.path.join(self.ws, "campaign", "warm-paths.json"))
        page, d, payload, summary = self.build()
        self.assertFalse(d["warm"]["tracked"])
        self.assertEqual([o["people"] for o in d["warm"]["orgs"]], [0, 0, 0])
        self.assertEqual([o["furthest"] for o in d["warm"]["orgs"]], [-1, -1, -1])
        self.assertIn("Tell your agent who you know at each organisation and how far you have got.", page)
        self.assertIn("- Acme AI: no one yet", summary)
        self.assertEqual(payload["warm_paths"]["per_org"]["acme"]["people"], 0)


if __name__ == "__main__":
    unittest.main()
