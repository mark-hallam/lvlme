"""The static demo folder (docs/demo/): fictional only, self-contained, true to the demos and kept up to date.

examples/build_demo_site.py copies the fictional demo page and writes an
index page. These tests build it into a temporary folder, offline, and check
that the copies are exact, every link on the index works, nothing is loaded
from anywhere, a workspace not marked fictional is refused, the index's numbers
match the demos, and the committed folder matches a fresh build.
"""
import glob
import os
import re
import shutil
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from unittest import mock

import helpers as H
import _page_html as PH
import test_page_a11y as A11Y

sys.path.insert(0, os.path.join(H.ENGINE, "examples"))
import build_demo_site as S  # noqa: E402

COMMITTED = os.path.join(H.ENGINE, "docs", "demo")
FILES = ["index.html", os.path.join("dashboard", "index.html")]
FILES += [os.path.join("dashboard", "research", "%s.html" % o) for o in ("acme", "globex", "initech")]


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.headings, self.hrefs, self.loads, self.text = [], [], [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append(int(tag[1]))
        if tag == "a" and "href" in a:
            self.hrefs.append(a["href"])
        if tag in ("script", "img", "iframe", "link", "source", "video", "audio") and (a.get("src") or a.get("href")):
            self.loads.append((tag, a.get("src") or a.get("href")))

    def handle_data(self, data):
        self.text.append(data)


def parse(page):
    p = Page()
    p.feed(page)
    return p


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.out = os.path.join(self.tmp, "demo")
        self.written = S.build(self.out)
        self.index = read(os.path.join(self.out, "index.html"))


class BuildTests(Base):
    def test_writes_the_index_and_two_exact_copies(self):
        self.assertEqual(sorted(os.path.relpath(p, self.out) for p in self.written), sorted(FILES))
        for name, workspace, page in S.sources():
            self.assertEqual(read(os.path.join(self.out, name, "index.html")), read(os.path.join(workspace, page)), name)

    def test_the_committed_folder_matches_a_fresh_build(self):
        """Rebuild with python3 examples/build_demo_site.py after the demos change."""
        committed = sorted(os.path.relpath(p, COMMITTED)
                           for p in glob.glob(os.path.join(COMMITTED, "**", "*"), recursive=True) if os.path.isfile(p))
        self.assertEqual(committed, sorted(FILES))
        for rel in FILES:
            self.assertEqual(read(os.path.join(COMMITTED, rel)), read(os.path.join(self.out, rel)), rel)

    def test_every_link_on_the_index_works(self):
        for href in parse(self.index).hrefs:
            if href.startswith("https://"):
                self.assertTrue(href == S.REPO or href.startswith(S.REPO + "/blob/HEAD/"), href)
                rel = href[len(S.REPO + "/blob/HEAD/"):] if "/blob/HEAD/" in href else ""
                if rel:
                    self.assertTrue(os.path.exists(os.path.join(H.ENGINE, rel)), href)
            else:
                self.assertTrue(os.path.isfile(os.path.join(self.out, href)), href)

    def test_no_page_loads_anything_from_anywhere(self):
        for rel in FILES:
            page = read(os.path.join(self.out, rel))
            self.assertEqual(parse(page).loads, [], rel)
            self.assertNotRegex(page, r"url\(\s*['\"]?https?:", rel)
            self.assertNotIn("@import", page, rel)


class FictionalOnlyTests(unittest.TestCase):
    def test_a_workspace_not_marked_fictional_is_refused_and_nothing_is_written(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        ws = os.path.join(tmp, "ws")
        shutil.copytree(os.path.join(H.DEMO, "report"), os.path.join(ws, "report"))
        config = H.load(os.path.join(H.DEMO, "config.json"))
        config.pop("fictional")
        H.save(os.path.join(ws, "config.json"), config)
        out = os.path.join(tmp, "demo")
        with mock.patch.object(S, "PAGES", [("dashboard", ws, os.path.join("report", "index.html"))]):
            with self.assertRaises(SystemExit) as caught:
                S.build(out)
        message = str(caught.exception)
        self.assertTrue(message.startswith("lvlme: ") and "\n" not in message, message)
        self.assertIn('"fictional": true', message)
        self.assertFalse(os.path.exists(out))

    def test_both_demos_say_they_are_fictional(self):
        for _name, workspace, _page in S.sources():
            self.assertIs(H.load(os.path.join(workspace, "config.json")).get("fictional"), True, workspace)


class IndexPageTests(Base):
    def test_numbers_match_the_demos(self):
        dash = H.load(os.path.join(H.DEMO, "report", "for-agents", "dashboard.json"))
        best = dash["levels"]["best_role"]
        text = " ".join(parse(self.index).text)
        self.assertIn("best match %s" % best["title"], text)
        self.assertIn("Level %d, %s" % (best["level"], best["band"]), text)
        self.assertIn(PH.long_date(dash["run_date"]), text)

    def test_says_it_is_fictional_and_names_every_made_up_name(self):
        text = " ".join(parse(self.index).text)
        for name in ("Alex Example", "Acme AI", "Globex Labs", "Initech Robotics", "fictional demo"):
            self.assertIn(name, text)

    def test_structure_one_h1_and_no_skipped_heading_level(self):
        p = parse(self.index)
        self.assertEqual(p.headings.count(1), 1)
        self.assertEqual(p.headings[0], 1)
        for a, b in zip(p.headings, p.headings[1:]):
            self.assertLessEqual(b, a + 1)
        self.assertIn('<html lang="en">', self.index)
        self.assertIn("<title>LVLme demo</title>", self.index)

    def test_plain_words_no_dashes_as_punctuation(self):
        text = " ".join(parse(self.index).text)
        self.assertNotRegex(text, "[–—]| - ")
        for word in ("revolutioni", "game-changer", "next-generation", "AI-powered", "Climb"):
            self.assertNotIn(word.lower(), text.lower())

    def test_colours_are_the_shared_pages_tested_tokens(self):
        """The index adds layout only, so the shared page's contrast checks cover it in every theme."""
        extra = S.CSS[len(PH.CSS):]
        self.assertTrue(S.CSS.startswith(PH.CSS))
        self.assertNotRegex(extra, r"#[0-9a-fA-F]{3,6}\b|rgba?\(")
        for theme, t in A11Y.themes().items():
            for fg, bg in (("ink", "card"), ("sub", "card"), ("sub", "bg"), ("accent", "card"), ("ink", "bg")):
                self.assertGreaterEqual(A11Y.contrast(t[fg], t[bg]), 4.5, "%s on %s, %s" % (fg, bg, theme))

    def test_rows_are_big_enough_to_tap(self):
        self.assertRegex(S.CSS, r"ul\.rows a\{[^}]*min-height:44px")


if __name__ == "__main__":
    unittest.main()
