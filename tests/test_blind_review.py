"""The review is blind: no method file may tell anyone to hand the reviewer the scores.

agents/reviewer.md, SKILL.md and docs/ORCHESTRATION.md say the reviewer
never sees the score it checks. Until November 2026, method/REVIEW.md, RUNBOOK.md step
7 and docs/DESIGN.md said the opposite. This test reads every instruction file
and fails on any sentence that gives the reviewer scores.
"""
import os
import re
import unittest

import helpers as H

# Release notes and the changelog describe old wording; examples are output.
SKIP_DIRS = {"examples", "tests", ".git", "__pycache__"}
SKIP_FILES = {"CHANGELOG.md"}
NEGATION = re.compile(r"\b(not|never|without|nothing|no)\b", re.I)
GIVES = re.compile(r"\b(give it|gets|you have|is given|hand(ed)?|pass(ed)?)\b", re.I)
SCORES = re.compile(r"\b(the scores|(evidence|rubric),? and scores|scores \(|run files?|eval/runs)\b", re.I)
REVIEWER = re.compile(r"\breview(er)?\b", re.I)


def method_files():
    for root, dirs, files in os.walk(H.ENGINE):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if name.endswith(".md") and name not in SKIP_FILES and not name.startswith("RELEASE-"):
                yield os.path.join(root, name)


def sentences(text):
    flat = re.sub(r"\s+", " ", text)
    return re.split(r"(?<=[.:;])\s+(?=[A-Z0-9`(-])|\s(?=\d+\.\s)|\s-\s", flat)


def offending(text):
    """Sentences that hand the reviewer scores, where it or the paragraph before is about the review."""
    paras = re.split(r"\n\s*\n", text)
    return [s for i, para in enumerate(paras) if REVIEWER.search(" ".join(paras[max(i - 1, 0):i + 1]))
            for s in sentences(para) if GIVES.search(s) and gives_scores(s)]


def gives_scores(text):
    """'the scores' with no 'not' or 'never' before it ('the scores, not the notes' still gives them)."""
    m = SCORES.search(text)
    return bool(m) and not NEGATION.search(text[:m.start()])


def block_offending(text):
    """'Give it:' lists, where the scores are a numbered item of their own."""
    found = []
    for m in re.finditer(r"Give it( only)?:\s*\n(.*?)(?:\n\n[^\d\n ]|\Z)", text, re.S):
        found += [item for item in re.split(r"\n(?=\d+\.)", m.group(2))
                  if gives_scores(item)]
    return found


OLD_WORDING = [
    "Start a fresh reviewer. Give it the rubric, the evidence and the scores, not the scorer's notes.",
    "the reviewer gets the rubric, evidence and scores, but not the scorer's reasoning",
    "You are an independent, sceptical reviewer.\n\n"
    "You have: the rubric (method/RUBRIC.md), the evidence file (profile/evidence.json), "
    "the scores (with the scorer's notes removed), and the job postings.",
]
OLD_LIST = "Give it:\n\n1. `method/RUBRIC.md`.\n2. The evidence.\n3. The scores: the newest `eval/runs/<date>.json`.\n\nDo not give it:\n"


class BlindReviewTests(unittest.TestCase):
    def test_the_check_catches_the_old_wording(self):
        for line in OLD_WORDING:
            self.assertTrue(offending(line), line)
        self.assertTrue(block_offending(OLD_LIST))

    def test_the_check_allows_the_blind_wording(self):
        self.assertFalse(offending("Give it the rubric, the evidence, the postings and the list of "
                                   "items to review, never the scores or the scorer's notes."))

    def test_no_method_file_hands_the_reviewer_scores(self):
        for path in method_files():
            with open(path, encoding="utf-8") as f:
                text = f.read()
            bad = offending(text) + block_offending(text)
            self.assertEqual(bad, [], os.path.relpath(path, H.ENGINE))

    def test_every_review_description_says_blind(self):
        for rel in ("method/REVIEW.md", "method/RUNBOOK.md", "docs/DESIGN.md",
                    "docs/ORCHESTRATION.md", "SKILL.md"):
            with open(os.path.join(H.ENGINE, rel), encoding="utf-8") as f:
                self.assertTrue("blind" in f.read(), rel)


if __name__ == "__main__":
    unittest.main()
