"""CHANGELOG.md: every version is there, newest first, and agrees with the manifest and the git tags.

The newest released heading must be the version in .claude-plugin/plugin.json,
so a release cannot bump one without the other. Where the repository has git
and a tag for a version, the tag's date and the manifest at that tag must match
the heading. Links, paths and punctuation are checked with the other docs in
test_packaging.
"""
import datetime
import json
import os
import re
import subprocess
import unittest

import helpers as H

PATH = os.path.join(H.ENGINE, "CHANGELOG.md")
HEADING = re.compile(r"^## (?:(Unreleased)|(\d+)\.(\d+)\.(\d+) \((\d{1,2} [A-Z][a-z]+ \d{4})\))$")
SUBHEADINGS = {"Added", "Changed", "Fixed", "Removed", "Still works"}
REQUIRED = ["0.4.0", "0.3.0", "0.2.0", "0.1.1", "0.1.0"]
BANNED = re.compile(r"(?i)revolutioni[sz]e|\btransform(s|ed|ing)?\b|game-changer|next-generation|AI-powered")


def read():
    with open(PATH, encoding="utf-8") as fh:
        return fh.read()


def sections():
    """[(version or 'Unreleased', date or None, body lines)] in file order; fails on a malformed ## heading."""
    found = []
    for line in read().splitlines():
        if line.startswith("## "):
            m = HEADING.match(line)
            if not m:
                raise AssertionError("malformed version heading: %r" % line)
            if m.group(1):
                found.append(("Unreleased", None, []))
            else:
                version = "%s.%s.%s" % m.group(2, 3, 4)
                date = datetime.datetime.strptime(m.group(5), "%d %B %Y").date()
                found.append((version, date, []))
        elif found:
            found[-1][2].append(line)
    return found


def git(*args):
    """Output of a git command in the engine folder, or None without git or a repository."""
    try:
        out = subprocess.run(["git", "-C", H.ENGINE] + list(args), capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def key(version):
    return tuple(int(p) for p in version.split("."))


class ChangelogTests(unittest.TestCase):
    def setUp(self):
        self.sections = sections()
        self.released = [s for s in self.sections if s[0] != "Unreleased"]

    def test_every_version_is_there_once(self):
        versions = [s[0] for s in self.released]
        for v in REQUIRED:
            self.assertEqual(versions.count(v), 1, v)
        self.assertEqual(len(versions), len(set(versions)))

    def test_newest_first(self):
        names = [s[0] for s in self.sections]
        self.assertNotIn("Unreleased", names[1:], "Unreleased goes at the top, once")
        versions = [key(s[0]) for s in self.released]
        self.assertEqual(versions, sorted(versions, reverse=True))
        dates = [s[1] for s in self.released]
        self.assertEqual(dates, sorted(dates, reverse=True), "a newer version cannot be dated earlier")

    def test_newest_release_is_the_manifest_version(self):
        with open(os.path.join(H.ENGINE, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
            manifest = json.load(fh)["version"]
        self.assertEqual(self.released[0][0], manifest,
                         "bump plugin.json and add its CHANGELOG.md heading in the same change")

    def test_sections_use_the_known_subheadings(self):
        for name, _, body in self.sections:
            heads = [l[4:] for l in body if l.startswith("### ")]
            with self.subTest(version=name):
                self.assertTrue(heads, "every version says what it added, changed or fixed")
                self.assertLessEqual(set(heads), SUBHEADINGS)
                self.assertTrue(any(l.startswith("- ") for l in body))

    def test_released_versions_record_their_test_count(self):
        for name, _, body in self.sections:
            counts = [l for l in body if re.match(r"^Tests: \d+ pass\.$", l)]
            with self.subTest(version=name):
                self.assertEqual(len(counts), 0 if name == "Unreleased" else 1)

    def test_tags_match_where_git_has_them(self):
        if git("rev-parse", "--git-dir") is None:
            self.skipTest("not a git repository")
        checked = 0
        for version, date, _ in self.released:
            tag = "v" + version
            if git("rev-parse", "-q", "--verify", "refs/tags/" + tag) is None:
                continue  # not tagged yet, or a copy without tags
            with self.subTest(tag=tag):
                self.assertEqual(git("log", "-1", "--format=%ad", "--date=short", tag), date.isoformat())
                manifest = json.loads(git("show", tag + ":.claude-plugin/plugin.json"))
                self.assertEqual(manifest["version"], version)
            checked += 1
        if not checked:
            self.skipTest("no release tags in this copy")

    def test_plain_words(self):
        text = read()
        self.assertIsNone(BANNED.search(text))
        for word in ("organization", "behavior", "color", "skeptic"):
            self.assertNotIn(word, text.lower())

    def test_linked_from_the_readme_and_the_release_steps(self):
        with open(os.path.join(H.ENGINE, "README.md"), encoding="utf-8") as fh:
            self.assertIn("](CHANGELOG.md)", fh.read())
        with open(os.path.join(H.ENGINE, "docs", "INSTALL.md"), encoding="utf-8") as fh:
            self.assertIn("CHANGELOG.md", fh.read())


if __name__ == "__main__":
    unittest.main()
