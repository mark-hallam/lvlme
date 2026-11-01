"""End to end on a copy of the demo workspace: fetch (offline), network map, score, dashboard, validate."""
import os
import re
import subprocess
import sys
import unittest
from unittest import mock

import helpers as H
import build_dashboard as B
import fetch_roles as F
import network_map as N
import score as S
import validate as V

DATE = "2026-11-01"
VIEWS = ["orgs", "top", "moves", "roles", "swot", "plan", "evidence", "market"]


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)
        fx = os.path.join(self.ws, "market", "fixtures")
        with mock.patch("sys.stdout"), mock.patch("sys.stderr"):
            self.assertEqual(F.main(["--workspace", self.ws, "--fixtures", fx, "--date", DATE]), 0)
            self.assertEqual(N.main(["--workspace", self.ws, "--today", DATE,
                                     "--csv", os.path.join(self.ws, "intake", "sources", "Connections.csv")]), 0)
            self.assertEqual(S.main(["--workspace", self.ws, "--date", DATE]), 0)

    def read(self, *parts):
        with open(os.path.join(self.ws, *parts), encoding="utf-8") as fh:
            return fh.read()

    def build(self):
        with mock.patch("sys.stdout"):
            self.assertEqual(B.main(["--workspace", self.ws]), 0)

    def test_demo_is_reproducible(self):
        """Re-running the pipeline gives the committed run file byte for byte."""
        with open(os.path.join(H.DEMO, "eval", "runs", DATE + ".json"), encoding="utf-8") as fh:
            committed = fh.read()
        self.assertEqual(self.read("eval", "runs", DATE + ".json"), committed)

    def test_dashboard_views_and_no_external_requests(self):
        result = subprocess.run([sys.executable, os.path.join(H.ENGINE, "scripts", "build_dashboard.py"),
                                 "--workspace", self.ws], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read("report", "index.html")
        for v in VIEWS:
            self.assertIn('id="v-%s"' % v, page)
        self.assertNotRegex(page, r"<script[^>]+src=|<link[^>]+href=|@import|url\(\s*['\"]?https?:|fetch\(|XMLHttpRequest")
        self.assertIn(":root[data-theme=dark]", page)              # light by default, with a dark switch
        self.assertIn("prefers-reduced-motion", page)
        self.assertNotIn("IntersectionObserver", page)              # content never waits for scroll events
        self.assertIn("Show the journey as a table", page)
        self.assertIn("Path to the top band", page)
        self.assertNotIn("Jordan Sample", page)  # names hidden unless show_contact_names_in_dashboard
        self.assertNotIn(os.path.expanduser("~"), page)
        errors, _, _ = V.validate_workspace(self.ws)
        self.assertEqual(errors, [])

    def test_sensitive_mode_agent_files(self):
        self.build()
        summary = self.read("report", "for-agents", "SUMMARY.md")
        data = self.read("report", "for-agents", "dashboard.json")
        for text in (summary, data):
            self.assertNotIn("Contoso", text)          # employer name from redact_terms
            self.assertNotIn("Jordan Sample", text)    # contact name from network.json
            self.assertNotRegex(text, r"\$\s?\d")      # no salary figures
            self.assertNotIn("compensation", text)
        self.assertIn("[contact]", data)
        self.assertIn("sensitive mode is ON", summary)
        self.assertIn("campaign/inbox.md", summary)
        payload = H.load(os.path.join(self.ws, "report", "for-agents", "dashboard.json"))
        self.assertNotIn("evidence", payload)
        self.assertEqual(payload["per_org"]["initech"]["role_id"], "initech:i-0001")

    def test_open_mode_still_hides_contact_names_without_opt_in(self):
        cfg = H.load(os.path.join(self.ws, "config.json"))
        cfg["privacy"]["sensitive_mode"] = False
        H.save(os.path.join(self.ws, "config.json"), cfg)
        self.build()
        payload = H.load(os.path.join(self.ws, "report", "for-agents", "dashboard.json"))
        self.assertIn("evidence", payload)
        self.assertTrue(any(r.get("compensation") for r in payload["roles"]))
        data = self.read("report", "for-agents", "dashboard.json")
        self.assertNotIn("Jordan Sample", data)
        self.assertIn("Contoso", data)
        cfg["privacy"]["share_contact_names_with_agents"] = True
        H.save(os.path.join(self.ws, "config.json"), cfg)
        self.build()
        self.assertIn("Jordan Sample", self.read("report", "for-agents", "dashboard.json"))

    def test_metrics_history_appended_once_per_date(self):
        self.build()
        self.build()
        hist = H.load(os.path.join(self.ws, "campaign", "metrics-history.json"))
        dates = [h["date"] for h in hist]
        self.assertEqual(dates, sorted(set(dates)))
        self.assertEqual(dates[-1], DATE)
        self.assertGreaterEqual(len(dates), 5)


class RepoHygieneTests(unittest.TestCase):
    """The engine repo holds no personal data and its prose avoids dashes as punctuation."""

    def files(self, exts):
        for root, dirs, names in os.walk(H.ENGINE):
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
            for n in names:
                if n.endswith(exts):
                    yield os.path.join(root, n)

    def test_no_en_or_em_dashes_in_docs(self):
        for path in self.files((".md",)):
            if os.sep + "docs" + os.sep in path:
                continue  # docs/DESIGN.md is the original spec, kept as written
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            self.assertIsNone(re.search("[\u2013\u2014]", text), path)


if __name__ == "__main__":
    unittest.main()
