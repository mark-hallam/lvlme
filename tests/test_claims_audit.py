"""claims_audit.py: claim extraction from files and URLs, de-duplication, judged claims left alone."""
import io
import os
import unittest
from unittest import mock

import helpers as H
import claims_audit as CA
import validate as V

ABOUT = """# About me

I led a team of 8 across six warehouses. I like hiking.

- Built route-eval, an open-source tool with 14 releases.
- Cut late deliveries by 18% in 2023.

Thanks for visiting my site, it is nice.
"""


class ClaimsAuditTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.new_workspace(self)
        self.src = os.path.join(os.path.dirname(self.ws), "about.md")
        with open(self.src, "w") as fh:
            fh.write(ABOUT)

    def run_main(self, *sources):
        with mock.patch("sys.stdout"):
            return CA.main(["--workspace", self.ws, "--today", "2026-11-01"] + list(sources))

    def audit(self):
        return H.load(os.path.join(self.ws, "profile", "claims-audit.json"))

    def test_extracts_pending_claims_and_dedupes(self):
        self.assertEqual(self.run_main(self.src), 0)
        claims = self.audit()["claims"]
        texts = [c["text"] for c in claims]
        self.assertIn("I led a team of 8 across six warehouses.", texts)
        self.assertIn("Built route-eval, an open-source tool with 14 releases.", texts)
        self.assertIn("Cut late deliveries by 18% in 2023.", texts)
        self.assertFalse(any("hiking" in t or "Thanks" in t for t in texts))
        self.assertTrue(all(c["status"] == "pending" for c in claims))
        self.assertEqual([c["id"] for c in claims], ["C001", "C002", "C003"])
        self.assertEqual(V.check(self.audit(), H.schema("claims-audit.schema.json")), [])

        audit = self.audit()
        audit["claims"][0].update(status="overstated", suggested_wording="Led a small team.")
        H.save(os.path.join(self.ws, "profile", "claims-audit.json"), audit)
        self.run_main(self.src)
        again = self.audit()["claims"]
        self.assertEqual(len(again), 3)
        self.assertEqual(again[0]["status"], "overstated")

    def test_html_and_url_sources(self):
        page = b"<html><body><nav>Home I built nothing here 100%</nav><p>I founded a startup that grew to 40 customers.</p></body></html>"

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        with mock.patch.object(CA.urllib.request, "urlopen", return_value=Resp(page)) as op:
            self.run_main("https://example.com/about")
        self.assertEqual(op.call_count, 1)
        texts = [c["text"] for c in self.audit()["claims"]]
        self.assertEqual(texts, ["I founded a startup that grew to 40 customers."])

    def test_only_http_urls(self):
        with self.assertRaises(SystemExit):
            CA.read_source("ftp://example.com/file.txt")


if __name__ == "__main__":
    unittest.main()
