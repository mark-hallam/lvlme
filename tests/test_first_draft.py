"""The first-draft rule in code: validate.py flags drafted answers for an employer that asks for the person's own.

Uses a copy of the fictional demo workspace, with Initech Robotics given an
AI policy that asks for the person's own first draft.
"""
import json
import os
import unittest

import helpers as H
import _first_draft as F
import validate as V

SOURCE = "https://example.com/initech/candidate-ai-guidance"
HEADER = "LVLme %s. Policy: " + SOURCE + ", checked %s.\n"


class FirstDraftTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)
        path = os.path.join(self.ws, "config.json")
        with open(path, encoding="utf-8") as f:
            self.cfg = json.load(f)
        initech = next(t for t in self.cfg["targets"] if t["id"] == "initech")
        initech["ai_policy"] = {"first_draft_by_person": True, "source": SOURCE, "checked_on": "2026-11-01"}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.cfg, f, indent=2)
        self.drafts = os.path.join(self.ws, "campaign", "drafts")
        # The demo's drafted application is exactly what the rule forbids: start without it.
        os.remove(os.path.join(self.drafts, "initech-fleet-application.md"))

    def write(self, rel, text):
        path = os.path.join(self.drafts, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def run_checks(self, today="2026-11-03"):
        errors, warnings = [], []
        F.checks(self.ws, self.cfg, errors, warnings, today=today)
        return errors, warnings

    def test_a_brief_passes(self):
        self.write("initech-fleet-brief.md", "# Brief\n\n" + HEADER % ("brief", "2026-11-01") + "Lead with E04.\n")
        self.assertEqual(self.run_checks(), ([], []))

    def test_a_drafted_answer_fails(self):
        self.write("initech-fleet-application.md", "Hello Initech Robotics hiring team,\n\nI have spent ten years...\n")
        errors, _ = self.run_checks()
        self.assertEqual(len(errors), 1)
        self.assertIn("campaign/drafts/initech-fleet-application.md: does not say what it is", errors[0])
        self.assertIn("Initech Robotics asks for your own first draft. Write it, then I'll review it.", errors[0])

    def test_an_answer_that_calls_itself_one_fails(self):
        self.write("A05/answer-initech.md", HEADER % ("answer", "2026-11-01") + "Why Initech? Because...\n")
        errors, _ = self.run_checks()
        self.assertIn("says it is a 'answer'", errors[0])

    def test_the_employer_is_found_by_name_and_in_folders(self):
        self.write("A05-resume-briefs/brief-initech-robotics-pm.html", "<p>CV text</p>\n")
        self.write("cover letter for Initech Robotics.txt", "Dear team\n")
        self.assertEqual(len(self.run_checks()[0]), 2)

    def test_other_employers_and_kinds_are_left_alone(self):
        self.write("globex-cover-letter.md", "Dear Globex team,\n")
        self.write("intro-initech-contact.md", HEADER % ("outreach", "2026-11-01") + "Hi Sam,\n")
        self.write("initech-interview-prep.md", HEADER % ("prep", "2026-11-01") + "Questions to ask\n")
        self.write("initech-my-draft-review.md", HEADER % ("review", "2026-11-01") + "Your second line has no evidence.\n")
        self.assertEqual(self.run_checks(), ([], []))

    def test_an_old_policy_check_asks_to_re_read_the_page(self):
        self.write("initech-fleet-brief.md", HEADER % ("brief", "2026-09-01"))
        errors, warnings = self.run_checks()
        self.assertEqual(errors, [])
        self.assertIn("last checked on 2026-09-01, more than 30 days ago. Re-read " + SOURCE, warnings[0])

    def test_a_different_policy_address_is_a_warning(self):
        self.write("initech-fleet-brief.md", "LVLme brief. Policy: https://example.com/old, checked 2026-11-01.\n")
        self.assertIn("but config.json records " + SOURCE, self.run_checks()[1][0])

    def test_files_it_cannot_read_are_named(self):
        self.write("initech-cv.docx", "binary")
        errors, warnings = self.run_checks()
        self.assertEqual(errors, [])
        self.assertIn("could not be read (campaign/drafts/initech-cv.docx)", warnings[0])

    def test_validate_reports_it_and_fails(self):
        self.write("initech-fleet-application.md", "Hello Initech Robotics hiring team,\n")
        errors, _, _ = V.validate_workspace(self.ws)
        self.assertTrue(any("initech-fleet-application.md: does not say what it is" in e for e in errors))

    def test_no_policy_means_no_check(self):
        self.assertEqual(V.validate_workspace(H.DEMO)[0], [])


if __name__ == "__main__":
    unittest.main()
