"""Offer help (scripts/offer.py). Fictional data, no network."""
import io
import os
import unittest
from contextlib import redirect_stdout
from unittest import mock

import helpers as H
import applications as APC
import offer as CLI

TODAY = "2026-11-05"


def quiet(fn, *args):
    with redirect_stdout(io.StringIO()) as out, mock.patch("sys.stderr", io.StringIO()):
        try:
            code = fn(list(args))
        except SystemExit as exc:
            code = 1 if isinstance(exc.code, str) else exc.code
            print(exc.code)
    return code, out.getvalue()


class OfferTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)

    def checklist(self, aid):
        with open(os.path.join(self.ws, "campaign", "drafts", "offer-%s-%s.md" % (aid, TODAY)), encoding="utf-8") as fh:
            return fh.read()

    def test_the_advertised_range_sits_beside_the_offer(self):
        quiet(APC.main, "--workspace", self.ws, "move", "ap8", "offer", "--date", TODAY)
        code, out = quiet(CLI.main, "--workspace", self.ws, "ap8", "--offered", "AUD 165,000 plus super", "--date", TODAY)
        self.assertEqual(code, 0, out)
        text = self.checklist("ap8")
        self.assertIn("Advertised in the posting: AUD 150,000 to 180,000 per year salary", text)
        self.assertIn("in your words: AUD 165,000 plus super", text)
        self.assertIn("Ask a lawyer before you sign", text)
        self.assertNotIn("safe to sign.", text.replace("never says an offer is fair or safe to sign", ""))

    def test_nothing_is_shown_for_a_posting_with_no_range(self):
        quiet(APC.main, "--workspace", self.ws, "add", "--org", "acme", "--title", "Applied AI Deployment Lead",
              "--role-id", "acme:4100002", "--stage", "offer", "--date", TODAY)
        self.assertEqual(quiet(CLI.main, "--workspace", self.ws, "ap9", "--date", TODAY)[0], 0)
        text = self.checklist("ap9")
        self.assertIn("The posting does not publish a pay range.", text)
        self.assertNotIn("Advertised in the posting", text)

    def test_only_for_an_interview_or_an_offer(self):
        code, out = quiet(CLI.main, "--workspace", self.ws, "ap7", "--date", TODAY)
        self.assertEqual(code, 1)
        self.assertIn("Offer help is for an application at Interview or Offer", out)


if __name__ == "__main__":
    unittest.main()
