"""Reading your dashboard: the plain-English guide stays linked, true to the page and plain.

The guide (docs/for-you/READING-YOUR-DASHBOARD.md) is for people who are not
technical. These tests keep it honest as the dashboard changes. The demo
dashboard is rebuilt from the demo workspace with the current engine, then:
every on-screen label the guide puts in bold must be on that page, every demo
number it quotes must match that build's dashboard.json, its numbered parts
must match the numbered picture, and it must stay plain, short and free of
jargon. Offline and standard library only.
"""
import html
import os
import re
import shutil
import tempfile
import unittest
from unittest import mock

import helpers as H
import _levels as LV
import build_dashboard as B

GUIDE = "docs/for-you/READING-YOUR-DASHBOARD.md"
IMAGE = "docs/images/reading-your-dashboard.png"
NUMBER_WORDS = {5: "five", 7: "seven", 9: "nine"}


def read(rel):
    with open(os.path.join(H.ENGINE, rel), encoding="utf-8") as fh:
        return fh.read()


def flat(text):
    return " ".join(text.split())


def prose(text):
    """The guide without code spans, fenced code or the image line: what a person reads as sentences."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\]\([^)]*\)", "]", text)  # a link's words stay, its address goes
    return re.sub(r"`[^`]*`", " ", text)


def page_text(page):
    """The page's words, from its HTML and its page script: styles, data, comments and tags removed, lower case."""
    with open(page, encoding="utf-8") as fh:
        raw = fh.read()
    raw = re.sub(r"<style>.*?</style>", " ", raw, flags=re.S)
    raw = re.sub(r'<script type="application/json"[^>]*>.*?</script>', " ", raw, flags=re.S)  # the data
    raw = re.sub(r"(?m)^\s*//.*$", " ", raw)  # code comments
    return flat(html.unescape(re.sub(r"<[^>]+>", " ", raw))).lower()


def shown_on_page(label, text):
    """True if the label is in the page as words, not only as code (a property such as .height or height:)."""
    for m in re.finditer(r"(?<![\w.#-])%s(?![\w-])" % re.escape(label.lower()), text):
        if not re.match(r"\s*[:=(]", text[m.end():]):
            return True
    return False


class ReadingGuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guide = read(GUIDE)
        cls.flat = flat(cls.guide)
        parent = tempfile.mkdtemp(prefix="lvlme-guide-test-")
        cls.addClassCleanup(shutil.rmtree, parent, True)
        ws = os.path.join(parent, "demo")
        shutil.copytree(H.DEMO, ws)
        with mock.patch("sys.stdout"):
            if B.main(["--workspace", ws]) != 0:
                raise AssertionError("the demo dashboard did not build")
        cls.page = os.path.join(ws, "report", "index.html")
        cls.data = H.load(os.path.join(ws, "report", "for-agents", "dashboard.json"))

    def test_linked_where_people_and_agents_look(self):
        """People find it from the README and the docs; every agent's run points to it the first time."""
        links = {"README.md": "](docs/for-you/READING-YOUR-DASHBOARD.md)",
                 "docs/HOW-IT-WORKS.md": "](for-you/READING-YOUR-DASHBOARD.md)",
                 "docs/LEVELS.md": "](for-you/READING-YOUR-DASHBOARD.md)"}
        for rel, link in links.items():
            with self.subTest(doc=rel):
                self.assertIn(link, read(rel))
        for rel in ("SKILL.md", "AGENTS.md", ".cursor/rules/lvlme-run.mdc", "skills/lvlme-dashboard/SKILL.md"):
            with self.subTest(doc=rel):
                self.assertIn("docs/for-you/READING-YOUR-DASHBOARD.md", read(rel))

    def test_every_label_in_bold_is_on_the_page(self):
        """Bold marks words the person will see on the page, so a renamed label fails here, not in a reader's hands."""
        text = page_text(self.page)
        labels = [flat(m) for m in re.findall(r"\*\*(.+?)\*\*", self.guide, flags=re.S)]
        self.assertGreater(len(labels), 20)
        for label in labels:
            if re.search(r"\d", label):
                continue  # numbers are checked against the demo's data below
            with self.subTest(label=label):
                self.assertTrue(shown_on_page(label, text), "%r is not on the demo page" % label)

    def test_demo_numbers_match_the_demo(self):
        best = self.data["levels"]["best_role"]
        top = self.data["roles"][0]
        self.assertEqual(top["role_id"], best["role_id"])
        self.assertIn("**%g of 100**" % best["fit"], self.flat)
        self.assertIn("%g points to Level %d, %s" % (best["points_to_next"], best["next_level"], best["next_band"]),
                      self.flat)
        self.assertIn("%g points short" % best["missing"]["points_short"], self.flat)
        self.assertIn("**Interview** %s and **Offer** %s" % (top["interview_band"], top["offer_band"]), self.flat)
        unlock = self.data["gaps"][0]
        self.assertIn("+%g across %d roles" % (unlock["points_gain"], unlock["roles_affected"]), self.flat)
        each = unlock["points_gain"] / unlock["roles_affected"]
        self.assertIn("about %g points on each role" % round(each), self.flat)
        self.assertIn("+%g" % self.data["levels"]["quests"][0]["points_expected"], self.flat)

    def test_levels_and_factors_match_the_engine(self):
        rows = re.findall(r"^\| (\d) \| ([A-Za-z ]+) \| (\d+) to (\d+) \|$", self.guide, flags=re.M)
        self.assertEqual([(int(n), name) for n, name, _, _ in rows], [(i + 1, b) for i, b in enumerate(LV.BANDS)])
        self.assertEqual([int(lo) for _, _, lo, _ in rows], LV.THRESH)
        self.assertEqual([int(hi) for _, _, _, hi in rows], [t - 1 for t in LV.THRESH[1:]] + [100])
        self.assertIn("%s factors" % NUMBER_WORDS[len(H.C.DIMENSIONS)], self.flat)
        self.assertIn("Your fit, put into %s levels" % NUMBER_WORDS[len(LV.BANDS)], self.flat)
        self.assertIn("They run %s." % ", ".join(H.C.CHANCE_BANDS), self.flat)

    def test_numbered_parts_match_the_picture(self):
        parts = re.findall(r"^### (\d+)\. (.+)$", self.guide, flags=re.M)
        self.assertEqual([int(n) for n, _ in parts], list(range(1, len(parts) + 1)))
        alt = re.search(r"!\[([^\]]+)\]\(\.\./images/reading-your-dashboard\.png\)", self.guide)
        self.assertIsNotNone(alt, "the guide shows the numbered picture")
        self.assertIn("%s numbered markers" % NUMBER_WORDS[len(parts)], alt.group(1))
        named = re.findall(r"(\d+) ((?:the )?[A-Za-z ]+?)(?=, \d| \()", alt.group(1))
        norm = lambda s: re.sub(r"^the ", "", s.strip().lower())
        self.assertEqual([(int(n), norm(s)) for n, s in named], [(int(n), norm(s)) for n, s in parts])
        path = os.path.join(H.ENGINE, IMAGE)
        with open(path, "rb") as fh:
            self.assertEqual(fh.read(8), b"\x89PNG\r\n\x1a\n")
        self.assertLess(os.path.getsize(path), 400 * 1024, "keep the picture light")

    def test_first_steps_come_first(self):
        """A non-technical reader gets three steps before any detail."""
        heads = re.findall(r"^## (.+)$", self.guide, flags=re.M)
        self.assertEqual(heads[0], "Your first two minutes")
        first = self.guide.split("## Your first two minutes", 1)[1].split("\n## ", 1)[0]
        self.assertEqual(len(re.findall(r"^\d\. ", first, flags=re.M)), 3)

    def test_plain_short_and_fictional(self):
        words = prose(self.guide)
        self.assertLess(len(words.split()), 1200, "one page: keep it short")
        self.assertIsNone(re.search(r"(?i)revolutioni[sz]e|transform|game-changer|next-generation|ai-powered", words))
        self.assertIsNone(re.search(r"(?i)\b(organiz\w*|colors?|behaviors?|centers?|analyz\w*|recogniz\w*)\b", words),
                          "Australian spelling")
        self.assertIsNone(re.search("[–—]", self.guide), "no dashes as punctuation")
        self.assertNotIn(" - ", re.sub(r"(?m)^\s*(?:[-*]|\d+\.)\s+", "", words))
        # Jargon: any capitalised abbreviation must be explained right after it is used.
        for abbr in sorted(set(re.findall(r"\b[A-Z]{2,}\b", words))):
            with self.subTest(abbreviation=abbr):
                self.assertIn(abbr, {"SWOT", "TOWS"})
        self.assertRegex(self.flat, r"\*\*SWOT and TOWS\*\* \(your strengths, weaknesses, opportunities and threats")
        self.assertNotRegex(words, r"https?://", "no links out of the repository")
        self.assertIn("Alex Example", words)
        self.assertIn("fictional demo", words)


if __name__ == "__main__":
    unittest.main()
