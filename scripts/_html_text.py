"""Posting HTML as plain text blocks, shared by fetch_roles.py and _boards.py.

blocks_of turns a posting's HTML into (kind, text, all_bold) blocks, where kind
is h (a heading), li (a list item) or p; clean folds white space. No network.
"""
import re
from html.parser import HTMLParser


class _Blocks(HTMLParser):
    """Turn posting HTML into (kind, text, all_bold) blocks; kind is h, li or p."""
    BLOCK = {"p", "div", "li", "ul", "ol", "br", "tr", "table", "section",
             "h1", "h2", "h3", "h4", "h5", "h6"}
    HEAD = {"h1", "h2", "h3", "h4", "h5", "h6"}
    SKIP_DIV = ("content-intro", "content-conclusion", "content-pay-transparency")

    def __init__(self, skip_boilerplate):
        super().__init__(convert_charrefs=True)
        self.skip_boilerplate = skip_boilerplate
        self.blocks, self.buf = [], []
        self.bold = self.chars = 0
        self.li = self.h = self.b = self.skip = self.ignore = 0
        self.divs = []

    def handle_starttag(self, tag, attrs):
        if tag == "div":
            cls = dict(attrs).get("class") or ""
            hit = self.skip_boilerplate and any(c in cls for c in self.SKIP_DIV)
            self.divs.append(hit)
            self.skip += hit
        if tag in self.BLOCK:
            self._flush()
        if tag == "li":
            self.li += 1
        elif tag in self.HEAD:
            self.h += 1
        elif tag in ("strong", "b"):
            self.b += 1
        elif tag in ("script", "style"):
            self.ignore += 1

    def handle_endtag(self, tag):
        if tag in self.BLOCK:
            self._flush()
        if tag == "li":
            self.li = max(0, self.li - 1)
        elif tag in self.HEAD:
            self.h = max(0, self.h - 1)
        elif tag in ("strong", "b"):
            self.b = max(0, self.b - 1)
        elif tag in ("script", "style"):
            self.ignore = max(0, self.ignore - 1)
        elif tag == "div" and self.divs:
            self.skip -= self.divs.pop()

    def handle_data(self, data):
        if self.skip or self.ignore:
            return
        self.buf.append(data)
        n = len(re.sub(r"\s", "", data))
        self.chars += n
        if self.b:
            self.bold += n

    def _flush(self):
        text = clean(" ".join(self.buf))
        if text:
            kind = "li" if self.li else "h" if self.h else "p"
            self.blocks.append((kind, text, self.chars > 0 and self.bold >= 0.9 * self.chars))
        self.buf, self.bold, self.chars = [], 0, 0


def clean(s):
    s = (s or "").replace("\xa0", " ").replace("\u200b", "").replace("\u200d", "")
    return re.sub(r"\s+", " ", s).strip()


def blocks_of(raw_html, skip_boilerplate=True):
    p = _Blocks(skip_boilerplate)
    p.feed(raw_html or "")
    p.close()
    p._flush()
    return p.blocks
