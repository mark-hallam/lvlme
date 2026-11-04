"""Import from career-ops (scripts/import_career_ops.py, scripts/_career_ops.py), against career-ops' own test
files where it publishes them (tests/fixtures/career-ops/NOTICE.md). No network."""
import glob
import hashlib
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

import helpers as H
import _applications as AP
import _calibration as CAL
import _career_ops as CO
import _stories as ST
import _warm_paths as W
import import_career_ops as CLI
import validate as V

SRC = os.path.join(H.FIXTURES, "career-ops")
TODAY = "2026-11-04"


def quiet(fn, *args):
    with redirect_stdout(io.StringIO()) as out, mock.patch("sys.stderr", io.StringIO()):
        try:
            code = fn(list(args))
        except SystemExit as exc:
            code = 1 if isinstance(exc.code, str) else exc.code
            print(exc.code)
    return code, out.getvalue()


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def fingerprint(folder):
    return {p: digest(p) for p in glob.glob(os.path.join(folder, "**", "*"), recursive=True) if os.path.isfile(p)}


class ReaderTests(unittest.TestCase):
    def test_every_row_split_case_from_career_ops_matches(self):
        with open(os.path.join(SRC, "tracker-row-split-parity.json"), encoding="utf-8") as fh:
            cases = json.load(fh)["cases"]
        self.assertGreaterEqual(len(cases), 9)
        for c in cases:
            self.assertEqual(CO.split_row(c["line"]), c["cells"], c["name"])

    def test_career_ops_own_tracker_reads_cleanly(self):
        with open(os.path.join(SRC, "data", "applications.md"), encoding="utf-8") as fh:
            rows = CO.read_tracker(fh.read())
        self.assertEqual([(r["num"], r["stage"]) for r in rows], [
            (1, "applied"), (2, "interview"), (3, "skip"), (4, "evaluated"), (5, "rejected"), (6, "applied")])
        self.assertEqual(rows[1]["company"], "Globex")

    def test_columns_are_found_by_name_including_via_and_aliases(self):
        text = ("| # | Date | Company | Via | Role | Score | Status | PDF | Report | Notes |\n|---|---|---|---|---|---|"
                "---|---|---|---|\n| 3 | 2026-09-01 | Acme | referral | PM | 4/5 | **Entrevista** | ❌ | — | — |\n")
        r = CO.read_tracker(text)[0]
        self.assertEqual((r["role"], r["via"], r["stage"], r["notes"]), ("PM", "referral", "interview", ""))

    def test_stories_skip_comments_and_blocks_without_an_action(self):
        with open(os.path.join(SRC, "interview-prep", "story-bank.md"), encoding="utf-8") as fh:
            stories = CO.read_stories(fh.read())
        self.assertEqual([s["title"] for s in stories], ["Moving six teams to one release train",
                                                         "Building a garden shed"])
        self.assertEqual(CO.themes_for(stories[0], {t["id"] for t in ST.THEMES})[0], "lead")

    def test_contacts_never_carry_phone_email_or_linkedin(self):
        with open(os.path.join(SRC, "data", "contacts.tsv"), encoding="utf-8") as fh:
            contacts = CO.read_contacts(fh.read())
        self.assertEqual(set(contacts[0]), {"name", "company", "type", "title", "tracker"})


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)
        for rel in (AP.REL, AP.LOG):
            os.remove(os.path.join(self.ws, rel))
        cfg = H.load(os.path.join(self.ws, "config.json"))
        for t in cfg["targets"]:
            t["aliases"] = [t["name"].split()[0]]           # "Globex" is "Globex Labs" here
        H.save(os.path.join(self.ws, "config.json"), cfg)
        self.src = os.path.join(tempfile.mkdtemp(prefix="lvlme-career-ops-"), "career-ops")
        self.addCleanup(shutil.rmtree, os.path.dirname(self.src), True)
        shutil.copytree(SRC, self.src)

    def run_import(self, *extra):
        return quiet(CLI.main, "--workspace", self.ws, "--from", self.src, "--date", TODAY, *extra)

    def apps(self):
        return H.load(os.path.join(self.ws, AP.REL))["applications"]

    def test_a_dry_run_writes_nothing(self):
        before = fingerprint(self.ws)
        code, out = self.run_import("--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("Would import 6 applications", out)
        self.assertEqual(fingerprint(self.ws), before)

    def test_import_keeps_history_and_never_touches_the_career_ops_folder(self):
        before = fingerprint(self.src)
        code, out = self.run_import()
        self.assertEqual(code, 0, out)
        self.assertEqual(fingerprint(self.src), before)
        by = {a["x_career_ops"]["tracker"]: a for a in self.apps()}
        self.assertEqual(len(by), 6)
        g = by[2]
        self.assertEqual((g["org"], g["stage"], g["applied_on"], g["last_step_on"]),
                         ("globex", "interview", "2026-06-26", "2026-07-02"))
        self.assertNotIn("applied_on", by[4])                     # evaluated, never sent
        self.assertEqual(by[1]["org"], "acme")
        self.assertEqual(by[5]["org"], "Hooli")                   # not a target: kept by name
        self.assertEqual(CAL.reached(self.ws)[g["id"]], {"evaluated", "applied", "interview"})
        self.assertEqual(quiet(V.main, "--workspace", self.ws)[0], 0)

    def test_importing_again_adds_nothing_and_follows_a_stage_change(self):
        self.run_import()
        path = os.path.join(self.src, "data", "applications.md")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text.replace("| Applied | ✅ | [1]", "| Rejected | ✅ | [1]"))
        code, out = self.run_import()
        self.assertIn("Imported 0 applications from career-ops; 1 already here changed stage.", out)
        apps = self.apps()
        self.assertEqual(len(apps), 6)
        self.assertEqual(next(a for a in apps if a["x_career_ops"]["tracker"] == 1)["stage"], "rejected")

    def test_contacts_at_targets_arrive_at_talked_without_their_details(self):
        code, out = self.run_import("--only", "contacts")
        self.assertIn("1 at other companies left out", out)
        warm = H.load(os.path.join(self.ws, W.REL))
        sam = next(c for c in warm["contacts"] if c["person"] == "Sam Sample")
        self.assertEqual((sam["org"], sam["stage"], sam["role"]), ("globex", "talked", "Talent Partner"))
        text = json.dumps(warm)
        for detail in ("sam@example.com", "+61 400", "example.com/in/sam"):
            self.assertNotIn(detail, text)
        self.run_import("--only", "contacts")
        self.assertEqual(len(H.load(os.path.join(self.ws, W.REL))["contacts"]), len(warm["contacts"]))

    def test_stories_arrive_as_your_word_and_unmatched_ones_are_listed(self):
        code, out = self.run_import("--only", "stories")
        self.assertIn("Not placed (no theme matched, or a STAR part missing): Building a garden shed", out)
        s = H.load(os.path.join(self.ws, ST.REL))["stories"][-1]
        self.assertEqual((s["title"], s["source"], s["evidence"], s["themes"][0]),
                         ("Moving six teams to one release train", "career-ops", [], "lead"))
        self.assertEqual(quiet(V.main, "--workspace", self.ws)[0], 0)


if __name__ == "__main__":
    unittest.main()
