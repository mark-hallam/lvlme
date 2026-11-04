import unittest

import helpers as H  # noqa: F401, E402
import _public_link as P


class PublicLinkTests(unittest.TestCase):
    def test_only_public_https_hosts_count(self):
        for url in ("https://example.com/work", "https://8.8.8.8/page"):
            self.assertTrue(P.is_public_link(url), url)
        for url in ("http://example.com", "https://localhost/page", "https://127.0.0.1",
                    "https://10.0.0.1", "https://192.168.1.3", "https://172.16.0.1",
                    "https://172.31.255.255", "https://172.16", "https://127.1",
                    "https://[::1]/", "https://thing.local",
                    "https://thing.internal", "https://thing.lan", "file:///tmp/a",
                    "mailto:a@example.com", "on request"):
            self.assertFalse(P.is_public_link(url), url)

    def test_documents_emails_exports_and_references_are_not_links_and_keep_their_level(self):
        for source in ({"type": "document", "ref": "campaign/offer-letter.pdf"},
                       {"type": "email", "ref": "Email from the hiring manager, 3 Oct"},
                       {"type": "linkedin_export", "ref": "profile/linkedin/Positions.csv"},
                       {"type": "reference", "ref": "intake/answers.md"}):
            item = {"level": "verified", "sources": [source]}
            self.assertEqual(P.effective_level(item), "verified", source)

    def test_only_private_links_downgrade_a_checked_claim(self):
        private = {"type": "website", "ref": "http://localhost:8000/work"}
        self.assertEqual(P.effective_level({"level": "corroborated", "sources": [private]}), "self_reported")
        mixed = {"level": "verified", "sources": [private, {"type": "document", "ref": "campaign/letter.pdf"}]}
        self.assertEqual(P.effective_level(mixed), "verified")
        public = {"level": "verified", "sources": [private, {"type": "github", "ref": "https://github.com/x/y"}]}
        self.assertEqual(P.effective_level(public), "verified")


if __name__ == "__main__":
    unittest.main()
