"""One plain vocabulary in what the person reads first: fit, chance, level and next level.

The dashboard page has its own words (checked in test_dashboard); this covers the messages, notes and
instructions the engine writes: the run message, the weekly note, the score summary.
"""
import io
import os
import re
import unittest
from unittest import mock

import helpers as H
import score as S

OLD_WORDS = re.compile(r"(?i)\baltitude\b|flight[ -]?level|\bheight\b")


def read(rel):
    with open(os.path.join(H.ENGINE, rel), encoding="utf-8") as fh:
        return fh.read()


class VocabularyTests(unittest.TestCase):
    def test_messages_and_notes_do_not_use_altitude_or_flight_level(self):
        for rel in ("scripts/score.py", "scripts/_autopilot.py", "scripts/autopilot.py", "scripts/run_plan.py",
                    "scripts/init.py", "README.md", "SKILL.md", "AGENTS.md"):
            self.assertIsNone(OLD_WORDS.search(read(rel)), rel)

    def test_the_run_message_uses_fit_chance_level_and_next_level(self):
        stage = read("SKILL.md").split("### 10. Tell the person")[1].split("## Cadence")[0]
        for word in ("level", "fit", "chance", "next level"):
            self.assertIn(word, stage.lower())

    def test_the_score_summary_names_the_fit_range_and_chance(self):
        ws = H.copy_demo(self)
        out = io.StringIO()
        with mock.patch("sys.stdout", out), mock.patch("sys.stderr", io.StringIO()):
            self.assertEqual(S.main(["--workspace", ws, "--date", "2026-11-02", "--force"]), 0)
        text = out.getvalue()
        self.assertIn("Interview chance / offer chance", text)
        self.assertRegex(text, r"\(\d+(\.\d)? to \d+(\.\d)?\)")      # the demo's first role was judged twice


if __name__ == "__main__":
    unittest.main()
