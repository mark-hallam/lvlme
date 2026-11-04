#!/usr/bin/env python3
"""Pull candidate claims from the person's public pages into the claims audit.

Give it the URLs of the person's own pages (site, LinkedIn "about" text saved
to a file, GitHub README) or local .txt / .md / .html files. It extracts
sentences that read like claims (achievements, numbers, titles, awards) and
adds each new one to profile/claims-audit.json with status "pending". The
agent then judges each claim against profile/evidence.json: supported,
overstated, unsupported or contradicted, with honest suggested wording.

Network: only the URLs passed on the command line are fetched. Claims already
judged are never changed; re-running only adds claims not seen before.

Usage
  python3 scripts/claims_audit.py --workspace PATH https://example.com/about notes/linkedin-about.txt
"""
import argparse
import hashlib
import html
import json
import os
import re
import sys
import urllib.request
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _certs as CT  # noqa: E402
import _common as C  # noqa: E402

UA = "lvlme/0.6 (claims audit of the user's own pages; read only)"
MAX_BYTES = 2_000_000
CLAIM_RX = re.compile(
    r"\b(led|lead|leading|managed|managing|built|building|founded|co-?founded|launched|shipped|delivered|"
    r"created|designed|grew|grown|scaled|increased|reduced|cut|saved|won|awarded|award|certified|"
    r"certification|published|spoke|keynote|mentored|hired|raised|generated|drove|owned|ran|"
    r"architected|deployed|negotiated|expert|specialist|pioneer|first|top|leading)\b|"
    r"\d+\s*(%|percent|x\b|\+|k\b|m\b|million|billion|users|customers|people|years|countries|team)|"
    r"[$\u00a3\u20ac]\s?\d", re.I)
FIRST_PERSON = re.compile(r"\b(i|i'm|i've|my|me|we|our)\b", re.I)


class _Text(HTMLParser):
    BLOCK = {"p", "div", "li", "br", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer", "noscript"):
            self.skip += 1
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "noscript"):
            self.skip = max(0, self.skip - 1)
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(raw):
    p = _Text()
    p.feed(raw or "")
    p.close()
    return html.unescape("".join(p.parts))


def read_source(src, workspace=None):
    """Return plain text for a URL or a local file (relative paths also tried inside the workspace)."""
    if re.match(r"^https?://", src, re.I):
        req = urllib.request.Request(src, headers={"User-Agent": UA})
        with CT.open_checked(urllib.request.urlopen, req, 60) as resp:
            body = resp.read(MAX_BYTES).decode("utf-8", errors="replace")
        return html_to_text(body) if "<" in body else body
    if re.match(r"^[a-z]+://", src, re.I):
        raise SystemExit("lvlme: only http and https URLs are supported: %s" % src)
    if workspace and not os.path.exists(src) and os.path.exists(os.path.join(workspace, src)):
        src = os.path.join(workspace, src)
    with open(src, encoding="utf-8", errors="replace") as fh:
        body = fh.read()
    return html_to_text(body) if src.lower().endswith((".html", ".htm")) else body


def sentences(text):
    out = []
    for block in re.split(r"\n\s*\n|\n(?=\s*[-*\u2022])", text):
        block = re.sub(r"^\s*[-*\u2022#>]+\s*", "", block.strip())
        block = re.sub(r"\s+", " ", block)
        for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", block):
            s = s.strip()
            if 20 <= len(s) <= 400:
                out.append(s)
    return out


def looks_like_claim(sentence):
    return bool(CLAIM_RX.search(sentence)) and (len(sentence.split()) >= 5 or FIRST_PERSON.search(sentence))


def fingerprint(text):
    norm = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:16]


def add_claims(audit, source, text, today):
    """Append new pending claims from text; return how many were added."""
    seen = {c.get("fingerprint") for c in audit["claims"]}
    nums = [int(c["id"][1:]) for c in audit["claims"] if re.match(r"^C\d+$", c.get("id", ""))]
    next_id = max(nums or [0]) + 1
    added = 0
    for s in sentences(text):
        if not looks_like_claim(s):
            continue
        fp = fingerprint(s)
        if fp in seen:
            continue
        seen.add(fp)
        audit["claims"].append({"id": "C%03d" % next_id, "source": source, "text": s, "fingerprint": fp,
                                "status": "pending", "evidence": [], "suggested_wording": "", "found_on": today})
        next_id += 1
        added += 1
    return added


def main(argv=None):
    ap = argparse.ArgumentParser(description="Extract candidate claims from the person's own public pages.")
    ap.add_argument("--workspace", help="workspace folder (default: $LVLME_HOME)")
    ap.add_argument("--today", help="date stamp for new claims (default: today)")
    ap.add_argument("sources", nargs="+", help="URLs (http or https) or .txt / .md / .html files")
    args = ap.parse_args(argv)
    ws, config = C.open_workspace(args.workspace)
    today = C.check_date(args.today) if args.today else C.today_in(config)
    path = C.wpath(ws, "profile", "claims-audit.json")
    audit = C.load_json(path, None) or {"schema_version": 1, "claims": []}
    report = {}
    for src in args.sources:
        try:
            report[src] = add_claims(audit, src, read_source(src, ws), today)
        except (OSError, ValueError) as exc:
            report[src] = "error: %s" % exc
    audit["updated_on"] = today
    C.write_json(path, audit)
    pending = sum(1 for c in audit["claims"] if c["status"] == "pending")
    print(json.dumps({"wrote": "profile/claims-audit.json", "added_per_source": report,
                      "pending_for_agent": pending}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(C.run_main(main))
