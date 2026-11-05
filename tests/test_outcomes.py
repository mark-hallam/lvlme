"""The outcome opt-in: numbers only, your choice, nothing sent."""
import io
import json
import os
import re
import unittest
from contextlib import redirect_stdout, redirect_stderr

import helpers as H
import _outcomes as O
import outcomes as CLI
import build_dashboard as B


def run(ws, *args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = CLI.main(["--workspace", ws] + list(args))
    return code, out.getvalue(), err.getvalue()


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)

    def test_the_export_is_numbers_only(self):
        export = O.build(self.ws, "2026-11-05")
        self.assertGreater(export["applications"], 0)
        row = export["rows"][0]
        self.assertEqual(set(row), {"rubric_version", "family", "month", "fit", "factor_scores", "interview_band", "offer_band",
                                    "warm_path", "interview", "offer"})
        self.assertEqual(len(row["factor_scores"]), 7)
        text = json.dumps(export)
        for private in ("Acme", "Globex", "Initech", "acme", "globex", "initech", "Alex", "example.com", "Sample", "Manager", "ap1"):
            self.assertNotIn(private, text)
        self.assertFalse(re.search(r"\d{4}-\d{2}-\d{2}", text))     # months, never exact days

    def test_export_is_refused_without_consent_and_saved_with_it(self):
        code, _, err = run(self.ws, "export")
        self.assertEqual(code, 1)
        self.assertIn("Nothing is ever sent", err)
        self.assertFalse(os.path.exists(os.path.join(self.ws, "report", "outcomes-export.json")))
        code, out, _ = run(self.ws, "export", "--consent")
        self.assertEqual(code, 0)
        self.assertEqual(H.load(os.path.join(self.ws, "report", "outcomes-export.json"))["schema"], O.SCHEMA)
        self.assertIn("LVLme sent nothing", out)

    def test_preview_writes_nothing(self):
        before = sorted(os.listdir(os.path.join(self.ws, "report")))
        code, out, _ = run(self.ws, "preview")
        self.assertIn("Never in it", out)
        self.assertEqual(sorted(os.listdir(os.path.join(self.ws, "report"))), before)


class ConsentPageTests(unittest.TestCase):
    def test_page_states_what_is_in_and_not_in_and_has_no_network(self):
        ws = H.copy_demo(self)
        run(ws, "page")
        page = open(os.path.join(ws, "report", "share-numbers.html"), encoding="utf-8").read()
        self.assertIn("What is never in it", page)
        self.assertIn("Nothing is sent.", page)
        self.assertIn('<button id="go" disabled>', page)          # off until the person ticks the box
        for call in ("fetch(", "XMLHttpRequest", "sendBeacon", "http://", "https://"):
            self.assertNotIn(call, page)

    def test_today_links_the_page_only_when_it_exists(self):
        ws = H.copy_demo(self)
        B.main(["--workspace", ws, "--today", "2026-11-05"])
        self.assertNotIn("share-numbers.html", open(os.path.join(ws, "report", "index.html"), encoding="utf-8").read())
        run(ws, "page")
        B.main(["--workspace", ws, "--today", "2026-11-05"])
        self.assertIn('href="share-numbers.html"', open(os.path.join(ws, "report", "index.html"), encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
