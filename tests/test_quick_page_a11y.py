"""The LVLme quick result page stays readable for everyone: contrast, text size, structure and contrast themes.

Checks the page's own CSS tokens and the rendered demo page, offline. The contrast maths is WCAG 2.2's
(relative luminance, ratio 4.5 for text, 3 for graphics such as the logo).
"""
import json
import os
import re
import unittest
from html.parser import HTMLParser

import helpers as H
import _quick_html as QH

DEMO_RESULT = os.path.join(H.ENGINE, "examples", "quick-demo",
                           "2026-11-02-globex-labs-deployment-program-manager-ai-agents", "result.json")

# (text colour, background, where it appears). Every pair the page draws text with.
TEXT_PAIRS = [
    ("ink", "bg", "page"), ("ink", "card", "cards"), ("ink", "card2", "tiles and notes"),
    ("ink", "accent-soft", "the all-fixes line and the run LVLme line"),
    ("sub", "bg", "header date and footer"), ("sub", "card", "grey text on cards"),
    ("sub", "card2", "tile labels and the Very low to Strong scale"), ("sub", "accent-soft", "Say to your agent"),
    ("accent", "card", "the posting link and fit points"), ("accent", "accent-soft", "fix numbers"),
    ("warn", "card", "why a score was capped"), ("warn", "warn-bg", "band change banners"),
    ("v-t", "v-bg", "Verified chips"), ("c-t", "c-bg", "Contradicted chips"),
    ("p-t", "p-bg", "Partly checked chips"), ("s-t", "s-bg", "Self-reported chips"),
]


def luminance(hex_colour):
    h = hex_colour.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    out = []
    for i in (0, 2, 4):
        v = int(h[i:i + 2], 16) / 255
        out.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2]


def contrast(a, b):
    x, y = luminance(a), luminance(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def tokens(block):
    return dict(re.findall(r"--([a-z0-9-]+):([^;}]+)", block))


def themes():
    """The colour tokens for light, dark, and each with the device's increase contrast setting."""
    css = QH.CSS
    light = tokens(re.search(r":root\{color-scheme:light;(.*?)\}", css, re.S).group(1))
    dark = dict(light, **tokens(re.search(r"@media \(prefers-color-scheme:dark\)\{:root\{(.*?)\}\}", css, re.S).group(1)))
    more = tokens(re.search(r"@media \(prefers-contrast:more\)\{:root\{(.*?)\}\}", css, re.S).group(1))
    more_dark = tokens(re.search(r"@media \(prefers-contrast:more\) and \(prefers-color-scheme:dark\)\{:root\{(.*?)\}\}",
                                 css, re.S).group(1))
    out = {"light": light, "dark": dark, "light, more contrast": dict(light, **more),
           "dark, more contrast": {**dark, **more, **more_dark}}
    for name, t in out.items():                      # resolve var(--x) references
        for k, v in list(t.items()):
            m = re.fullmatch(r"var\(--([a-z0-9-]+)\)", v.strip())
            t[k] = t[m.group(1)] if m else v.strip()
    return out


class Outline(HTMLParser):
    """Headings, sections and their labels, ids, links and the say line, in page order."""

    def __init__(self):
        super().__init__()
        self.headings, self.sections, self.ids, self.links, self.say_tags = [], [], {}, [], []
        self.text = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append(int(tag[1]))
        if "id" in a:
            self.ids[a["id"]] = tag
        if tag == "section":
            self.sections.append(a.get("aria-labelledby"))
        if tag == "a":
            self.links.append(a)
        if "say" in (a.get("class") or "").split():
            self.say_tags.append(tag)

    def handle_data(self, data):
        self.text.append(data)


def outline(page):
    p = Outline()
    p.feed(page)
    return p


def demo_result():
    with open(DEMO_RESULT, encoding="utf-8") as fh:
        return json.load(fh)


class ContrastTests(unittest.TestCase):
    def test_every_text_colour_pair_passes_aa_in_every_theme(self):
        for theme, t in themes().items():
            for fg, bg, where in TEXT_PAIRS:
                with self.subTest(theme=theme, pair="%s on %s" % (fg, bg)):
                    self.assertGreaterEqual(contrast(t[fg], t[bg]), 4.5, "%s in %s" % (where, theme))

    def test_the_logo_line_stands_out_from_its_tile(self):
        """The logo's line is drawn in --on-accent on --accent: 3 to 1 at least, for a graphic. In dark mode it
        used to be white on light blue (2.3 to 1)."""
        self.assertIn('stroke="currentColor"', QH.LOGO)
        self.assertNotIn("#fff", QH.LOGO)
        self.assertIn("background:var(--accent);color:var(--on-accent)", QH.CSS)
        for theme, t in themes().items():
            with self.subTest(theme=theme):
                self.assertGreaterEqual(contrast(t["on-accent"], t["accent"]), 3.0)

    def test_increase_contrast_turns_grey_text_to_full_ink(self):
        for theme in ("light, more contrast", "dark, more contrast"):
            t = themes()[theme]
            self.assertEqual(t["sub"], t["ink"])
            # the empty steps of a meter stand out from their tile, so "2 of 5" reads as a scale
            self.assertGreaterEqual(contrast(t["pip"], t["card2"]), 2.4, theme)


class TextSizeTests(unittest.TestCase):
    def test_no_text_is_smaller_than_12px(self):
        sizes = [int(x) for x in re.findall(r"font-size:(\d+)px", QH.CSS)]
        self.assertTrue(sizes)
        self.assertGreaterEqual(min(sizes), 12)


class ForcedColoursTests(unittest.TestCase):
    """In a Windows contrast theme the browser drops background colours, which used to erase the meters, the
    score dots and the fit bar. They now keep system colours: an outline for every step, Highlight for the
    filled ones."""

    def block(self):
        m = re.search(r"@media \(forced-colors:active\)\{(.*)\}\s*$", QH.CSS.strip(), re.S)
        self.assertIsNotNone(m, "the page has a forced colours block")
        return m.group(1)

    def test_meters_dots_and_fit_bar_keep_their_shape(self):
        b = self.block()
        self.assertIn(".meter i,.pips i,.track{forced-color-adjust:none;background:Canvas;border:1px solid CanvasText}", b)
        self.assertIn(".meter i.on,.pips i.on,.track .now{background:Highlight}", b)
        self.assertIn(".track .maybe{background:repeating-linear-gradient(135deg,Highlight", b)

    def test_cards_chips_and_the_logo_get_an_outline(self):
        first_rule = self.block().split("{", 1)[0].split(",")
        for selector in (".card", ".tile", ".chip", ".mark", ".say", "ol.fixes li::before"):
            self.assertIn(selector, first_rule)


class StructureTests(unittest.TestCase):
    def setUp(self):
        self.result = demo_result()
        self.page = QH.render(self.result)
        self.o = outline(self.page)

    def test_one_h1_and_headings_never_skip_a_level(self):
        self.assertEqual(self.o.headings.count(1), 1)
        self.assertEqual(self.o.headings[0], 1)
        for before, after in zip(self.o.headings, self.o.headings[1:]):
            self.assertLessEqual(after, before + 1)

    def test_every_section_is_named_by_its_heading(self):
        self.assertTrue(self.o.sections)
        for label in self.o.sections:
            self.assertIsNotNone(label, "a section without a name")
            self.assertRegex(self.o.ids.get(label, ""), r"h[1-6]", label)
        self.assertEqual(self.o.ids[self.o.sections[0]], "h1")   # the odds are named by the role, not a sentence

    def test_a_result_with_no_fix_still_names_every_section(self):
        o = outline(QH.render(dict(self.result, fixes=[])))
        self.assertIn("No fix found", "".join(o.text))
        for label in o.sections:
            self.assertRegex(o.ids.get(label, ""), r"h[1-6]")

    def test_the_posting_link_has_a_bigger_tap_area(self):
        self.assertEqual([a.get("class") for a in self.o.links], [])   # the demo's posting is fictional: no link
        real = outline(QH.render(dict(self.result, fictional=False)))
        self.assertEqual([a.get("class") for a in real.links], ["posting"])
        self.assertIn("a.posting,a.guide{padding:10px 4px;margin:0 -4px}", QH.CSS)

    def test_the_ai_guidance_link_has_a_bigger_tap_area_too(self):
        role = dict(self.result["role"], org_name="Anthropic", ai_policy={
            "first_draft_by_person": True, "source": "https://www.anthropic.com/candidate-ai-guidance",
            "checked_on": "2026-11-03"})
        o = outline(QH.render(dict(self.result, role=role)))
        self.assertEqual([a.get("class") for a in o.links], ["guide"])

    def test_meters_say_where_on_the_scale_without_repeating_the_band(self):
        self.assertIn('role="img" aria-label="Step 3 of 6, from Almost none to Strong"', self.page)
        self.assertIn('role="img" aria-label="Step 2 of 6, from Almost none to Strong"', self.page)

    def test_the_go_deeper_line_is_words_to_say_not_a_button(self):
        """A static page cannot run anything, so the line is a quote to say to the agent, not a filled button."""
        self.assertEqual(self.o.say_tags, ["p"])
        self.assertIn('<span class="k">Say to your agent</span> <b>"run LVLme"</b>', self.page)
        say_rule = re.search(r"\.say\{([^}]*)\}", QH.CSS).group(1)
        self.assertNotIn("background:var(--accent)", say_rule.replace("var(--accent-soft)", ""))

    def test_no_old_product_name_in_the_page_text(self):
        self.assertNotRegex("".join(self.o.text), r"(?i)\bclimb\b")

    def test_the_demo_label_never_splits_on_a_phone(self):
        self.assertIn('<span class="nw">2 November 2026</span><span class="sep"> · </span>'
                      '<span class="nw">fictional demo</span>', self.page)
        self.assertIn(".top .nw{display:block}.top .sep{display:none}", QH.CSS)


if __name__ == "__main__":
    unittest.main()
