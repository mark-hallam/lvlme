"""The shared page style stays readable for everyone: contrast, text size and contrast themes.

Checks the stylesheet's own CSS tokens, offline. The contrast maths is WCAG 2.2's
(relative luminance, ratio 4.5 for text, 3 for graphics such as the logo).
"""
import os
import re
import unittest

import helpers as H
import _page_html as PH

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
    css = PH.CSS
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


class ContrastTests(unittest.TestCase):
    def test_every_text_colour_pair_passes_aa_in_every_theme(self):
        for theme, t in themes().items():
            for fg, bg, where in TEXT_PAIRS:
                with self.subTest(theme=theme, pair="%s on %s" % (fg, bg)):
                    self.assertGreaterEqual(contrast(t[fg], t[bg]), 4.5, "%s in %s" % (where, theme))

    def test_the_logo_line_stands_out_from_its_tile(self):
        """The logo's line is drawn in --on-accent on --accent: 3 to 1 at least, for a graphic. In dark mode it
        used to be white on light blue (2.3 to 1)."""
        self.assertIn('stroke="currentColor"', PH.LOGO)
        self.assertNotIn("#fff", PH.LOGO)
        self.assertIn("background:var(--accent);color:var(--on-accent)", PH.CSS)
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
        sizes = [int(x) for x in re.findall(r"font-size:(\d+)px", PH.CSS)]
        self.assertTrue(sizes)
        self.assertGreaterEqual(min(sizes), 12)


class ForcedColoursTests(unittest.TestCase):
    """In a Windows contrast theme the browser drops background colours, which used to erase the meters, the
    score dots and the fit bar. They now keep system colours: an outline for every step, Highlight for the
    filled ones."""

    def block(self):
        m = re.search(r"@media \(forced-colors:active\)\{(.*)\}\s*$", PH.CSS.strip(), re.S)
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


if __name__ == "__main__":
    unittest.main()
