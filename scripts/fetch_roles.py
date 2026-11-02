#!/usr/bin/env python3
"""Fetch open roles from the target organisations' public job boards.

Reads config.json (targets, role families and their keywords, location
classes) and writes:
  market/roles/latest.json              every open role that matches a family
  market/roles/snapshots/<date>.json    the role ids open on that date

Adapters: Greenhouse, Ashby and Lever public job-board APIs, plus "manual"
(roles typed into market/roles/manual.json). Standard library only.
Read only: nothing is applied to or submitted, and no account is used.

Usage
  python3 scripts/fetch_roles.py --workspace PATH
  python3 scripts/fetch_roles.py --fixtures DIR      # offline: read DIR/<target id>.json
  python3 scripts/fetch_roles.py --save-raw DIR      # also keep the raw responses
  python3 scripts/fetch_roles.py --date 2026-11-01   # snapshot date (default: today)

Field notes
  remote        true = advertised as remote; false = on-site, hybrid or no
                remote signal; "unknown" = only the text mentions remote work.
  location_classes  from the config keywords. "remote" counts as its own class
                only when the same location line names no region.
  eligibility_blockers  postings that say US person / ITAR / export control,
                security clearance, a named citizenship, or a licence.
  blocker_counts  (in the summary, and printed) how many matched open roles
                state each blocker type. The interview asks the export
                control and clearance questions only when their count is
                above 0 (method/INTERVIEW.md, "Work rights").
  requires_heavy_coding  heuristic; coding_signals lists the phrases found.
"""
import argparse
import datetime as dt
import glob
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

UA = "lvlme/0.3 (personal job-search research script; read only)"
MAX_REQ_LEN = 160
DASHES = "\u2013\u2014"

# ---------------------------------------------------------------- fetching


def endpoint(target):
    ats, slug = target.get("ats"), target.get("slug") or target["id"]
    if ats == "greenhouse":
        return "https://boards-api.greenhouse.io/v1/boards/%s/jobs?content=true" % slug
    if ats == "ashby":
        return "https://api.ashbyhq.com/posting-api/job-board/%s?includeCompensation=true" % slug
    if ats == "lever":
        host = "api.eu.lever.co" if target.get("region") == "eu" else "api.lever.co"
        return "https://%s/v0/postings/%s?mode=json" % (host, slug)
    return None


def fetch_json(url, tries=3, timeout=90):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            last = exc
            if attempt + 1 < tries:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError("%s: %s" % (type(last).__name__, last))


def load_raw(target, fixtures, save_raw):
    """Raw API response for one target: from fixtures if given, else the network."""
    if fixtures:
        path = os.path.join(fixtures, "%s.json" % target["id"])
        if not os.path.exists(path):
            raise RuntimeError("no fixture file %s" % path)
        return C.load_json(path)
    data = fetch_json(endpoint(target))
    if save_raw:
        C.write_json(os.path.join(save_raw, "%s.json" % target["id"]), data)
    return data

# ------------------------------------------------------------ HTML parsing


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


def shorten(s, limit=MAX_REQ_LEN):
    s = re.sub(r"^[\s\u2022\u00b7\-%s*]+" % DASHES, "", clean(s))
    if len(s) < limit:
        return s
    cut = s[: limit - 2]
    cut = cut[: cut.rfind(" ")] if " " in cut else cut
    return cut.rstrip(" ,;:.") + "\u2026"


STOP_H = re.compile(r"compensation|benefits|logistics|^location|workplace|itar|equal opportunity|"
                    r"how we.?re different|^pay\b|salary|deadline|accommodation|"
                    r"^about (us|the company|our company)\b", re.I)
ABOUT_H = re.compile(r"^about\b|^the (role|team)\b|^overview|^who we are|"
                     r"what you.?ll learn|how you.?ll (?:grow|develop)", re.I)
NICE_H = re.compile(r"prefer|nice[- ]to[- ]have|bonus|strong candidates may|\bideally\b|\bplus\b|"
                    r"additional (skills|qualifications|experience)|desired|great if|extra credit|good to have|stand out", re.I)
REQ_H = re.compile(r"qualifications|requirements?\b|good fit|thrive|looking for|seeking|what you.?ll (need|bring)|need to see|"
                   r"\byou (have|bring|are|should|might be)\b|about you|who you are|your background|"
                   r"background might|must[- ]have|minimum|basic|skills|experience(?!s)|ideal candidate|"
                   r"(?:probably|might be) a (?:good )?match|you.?re a match", re.I)
RESP_H = re.compile(r"responsib|what you.?ll (actually )?(do|be doing|work on)|in this role|you will|"
                    r"key duties|day[- ]to[- ]day|representative projects|your impact|the work|"
                    r"role is focused on|^your missions?\b", re.I)


def heading_category(text, org_stop=None):
    if org_stop is not None and org_stop.search(text):
        return "stop"
    for cat, rx in (("stop", STOP_H), ("about", ABOUT_H), ("nice", NICE_H), ("req", REQ_H), ("resp", RESP_H)):
        if rx.search(text):
            return cat
    return None


def looks_like_heading(kind, text, bold):
    if len(text) > 100 or kind == "li":
        return False
    return (kind == "h" or (bold and len(text) <= 100) or (len(text) <= 80 and text.endswith(":"))
            or (text.isupper() and len(text) <= 60))


def sections_of(blocks, org_stop=None):
    """Group blocks under headings. Returns [(category, heading, [items])]."""
    out, cur = [], ("intro", "", [])
    for kind, text, bold in blocks:
        if looks_like_heading(kind, text, bold):
            cat = heading_category(text, org_stop)
            structural = kind == "h" or text.endswith(":") or text.isupper()
            if cat is None and cur[0] in ("req", "nice", "resp") and not structural:
                cur[2].append(text)  # bold lead-in sentence inside a list section
                continue
            out.append(cur)
            cur = (cat or "other", text, [])
        else:
            cur[2].append(text)
    out.append(cur)
    return out


YEARS = re.compile(r"(\d{1,2})\s*\+?\s*(?:(?:-|[%s]|to)\s*\d{1,2}\s*\+?\s*)?(?:or more\s+|plus\s+)?\+?\s*years?"
                   % DASHES, re.I)
DEGREE = re.compile(r"\b(bachelor|master|ph\.?\s?d|doctorate|mba|b\.s\.|b\.a\.|bs/ba|ba/bs|bs/ms|ms/phd)\b|"
                    r"\bdegree\s+(in|or)\b|\b(university|college|undergraduate|advanced)\s+degree", re.I)
CODE_CORE = [
    r"production[- ](?:quality|grade|ready|level)?\s*code",
    r"production[- ](?:quality|grade|ready|level|relevant)\s+(?:software|systems|services)",
    r"\b(?:write|writing|ship|shipping)\s+(?:and\s+review\s+)?(?:high[- ]quality\s+|clean\s+|maintainable\s+|"
    r"well[- ]tested\s+)?(?:production\s+)?code\b",
]
CODE_STRONG = CODE_CORE + [
    r"\d+\+?\s*(?:or more\s+)?years?\s+(?:of\s+)?(?:professional\s+|industry\s+|hands[- ]on\s+)?"
    r"(?:software|full[- ]stack|backend|back[- ]end|frontend|front[- ]end)\s+(?:engineering|development)",
    r"(?:software|full[- ]stack|backend|back[- ]end)\s+(?:engineering|development)\s+experience",
    r"experience\s+as\s+an?\s+(?:software|backend|full[- ]stack|machine learning|ml|forward[- ]deployed)\s+engineer",
    r"strong\s+(?:software\s+)?(?:engineering|coding|programming)\s+(?:skills|background|fundamentals|ability|abilities)",
    r"(?:proficien(?:t|cy)|fluen(?:t|cy)|expertise|expert)\s+(?:in|with)\s+(?:one or more\s+|at least one\s+)?"
    r"(?:(?:programming\s+)?languages?\s+(?:such as|like)\s+)?(?:python|typescript|javascript|java\b|golang|go\b|c\+\+|rust|scala|kotlin)",
    r"(?:build|building|develop|developing)\s+(?:and\s+(?:deploy|deploying|ship|shipping|maintain|maintaining)\s+)?"
    r"(?:production|scalable|robust)\s+(?:systems|services|software|applications|pipelines|infrastructure)",
    r"hands[- ]on\s+(?:coding|programming|software development)",
    r"computer science\s+(?:degree|or\s+(?:a\s+)?related)",
    r"strong\s+in\s+(?:python|typescript|javascript|java\b|go\b|c\+\+|rust)",
    r"(?:industry|professional)\s+experience\s+(?:in|with)\s+(?:programming|coding|software)",
    r"strong\s+engineering\s+depth",
]
NEGATION = re.compile(r"(?:n't|\bnot|\bnever|\bwithout|\bno need to|\bno)\s+(?:\w+\s+){0,3}$", re.I)
ENGINEER_TITLE = re.compile(r"\b(engineer|developer)\b", re.I)


def coding_check(title, text):
    """Return (requires_heavy_coding, signals). Negated phrases ("you won't write
    production code") are reported as 'NOT required: ...' and never count."""
    hits, negated, core = [], [], False
    for rx in CODE_STRONG:
        for m in re.finditer(rx, text, re.I):
            if NEGATION.search(text[max(0, m.start() - 40):m.start()]):
                negated.append("NOT required: " + m.group(0)[:70])
                continue
            hits.append(m.group(0)[:80])
            core = core or rx in CODE_CORE
            break
    heavy = bool(core or (ENGINEER_TITLE.search(title) and hits) or len(hits) >= 2)
    return heavy, hits + list(dict.fromkeys(negated))


def parse_posting(raw_html, title, org_stop=None):
    blocks = blocks_of(raw_html, skip_boilerplate=True)
    secs = sections_of(blocks, org_stop)
    req = [i for c, _, items in secs if c == "req" for i in items]
    nice = [i for c, _, items in secs if c == "nice" for i in items]
    resp = [i for c, _, items in secs if c == "resp" for i in items]
    note = None
    if not req:
        loose = [i for c, _, items in secs if c in ("intro", "about", "other") for i in items]
        req = [t for t in loose if re.search(
            r"experience|years|degree|ability to|proficien|familiar|background in", t, re.I) and len(t) < 400]
        note = ("no requirements heading found; requirements picked by keyword" if req
                else "no required-qualifications section found" + (" (posting lists preferred only)" if nice else ""))
    years, basis = None, None
    for label, items in (("required", req), ("preferred", nice)):
        for item in items:
            m = YEARS.search(item)
            if m and not re.search(r"years?\s+(ago|old)\b", item[m.start():m.end() + 8], re.I):
                years, basis = int(m.group(1)), label
                break
        if years is not None:
            break
    degree = next((shorten(i) for i in req if DEGREE.search(i)), None)
    if not degree:
        pref = next((i for i in nice if DEGREE.search(i)), None)
        degree = shorten("Preferred: " + pref) if pref else None
    lines = [("- " if kind == "li" else "") + text for kind, text, _ in blocks]
    full_text = clean(" ".join(t for _, t, _ in blocks_of(raw_html, skip_boilerplate=False)))
    heavy, hits = coding_check(title, " ".join(req + resp + nice))
    return {
        "hard": [shorten(i) for i in req if len(i) > 3][:6],
        "nice": [shorten(i) for i in nice if len(i) > 3][:4],
        "resp": [shorten(i) for i in resp if len(i) > 3][:6],
        "years": years, "years_basis": basis, "degree": degree,
        "text": "\n".join(lines), "full_text": full_text,
        "coding": (heavy, hits), "parse_note": note,
    }

# ------------------------------------------------------ pay, flags, remote


def greenhouse_pay(raw):
    out = []
    for m in re.finditer(r'<div class="pay-input">(.*?)<div class="pay-range">(.*?)</div>', raw, re.S):
        label = re.search(r'<div class="title">(.*?)</div>', m.group(1), re.S)
        rng = clean(re.sub(r"<[^>]+>", " ", html.unescape(m.group(2))))
        rng = re.sub(r"\s*[%s]\s*" % DASHES, " to ", rng)
        lab = clean(re.sub(r"<[^>]+>", "", label.group(1))) if label else ""
        lab = "" if lab.lower().rstrip(":") in ("annual salary", "") else lab.rstrip(":")
        out.append("%s: %s" % (lab, rng) if lab else rng)
    if not out:
        text = clean(re.sub(r"<[^>]+>", " ", raw))
        m = re.search(r"(?:pay range|salary range|base salary|compensation)[^$]{0,120}?"
                      r"(\$\s?[\d,]+(?:\.\d+)?\s*[kK]?\s*(?:-|[%s]|to)\s*\$\s?[\d,]+(?:\.\d+)?\s*[kK]?"
                      r"(?:\s*(?:USD|/\s*(?:per\s+)?(?:year|yr|hour|hr)))?)" % DASHES, text, re.I)
        if m:
            out.append(re.sub(r"\s*(?:-|[%s])\s*" % DASHES, " to ", clean(m.group(1))))
    return "; ".join(dict.fromkeys(out)) or None


def ashby_pay(job):
    comp = job.get("compensation") or {}
    if not comp or job.get("shouldDisplayCompensationOnJobPostings") is False:
        return None
    tiers = [t.get("tierSummary") for t in comp.get("compensationTiers") or [] if t.get("tierSummary")]
    if len(tiers) > 1:
        out = "; ".join(tiers)
    else:
        out = comp.get("compensationTierSummary") or comp.get("scrapeableCompensationSalarySummary") or (
            tiers[0] if tiers else None)
    return re.sub(r"\s*[%s]\s*" % DASHES, " to ", out) if out else None


def lever_pay(job):
    rng = job.get("salaryRange") or {}
    if rng.get("min") is not None and rng.get("max") is not None:
        interval = (rng.get("interval") or "").replace("-", " ")
        out = "%s %s to %s" % (rng.get("currency") or "", "{:,}".format(rng["min"]), "{:,}".format(rng["max"]))
        return clean(out + (" " + interval if interval else ""))
    desc = clean(re.sub(r"<[^>]+>", " ", job.get("salaryDescription") or ""))
    return desc or None


US_PERSON_RX = re.compile(
    r"(?:must be|requires?|required to be|only)\s+(?:a\s+)?U\.?S\.?\s+(?:citizen|person)|"
    r"U\.?S\.?\s+citizenship|lawful,?\s+permanent resident|green card holder|ITAR\b|"
    r"export[- ]control(?:led)?\s+(?:laws|regulations|requirements)|"
    r"to (?:conform|comply) (?:to|with) (?:U\.S\.\s+)?(?:Government\s+)?export", re.I)
CLEARANCE_RX = re.compile(r"security clearance|TS/SCI|top secret|secret clearance|"
                          r"(?:active|obtain|maintain)\s+(?:a|an|the)?\s*\w*\s*clearance", re.I)
CITIZEN_RX = re.compile(r"(?:must|required to|need to|have to)\s+(?:be|hold)\s+(?:an?\s+)?(?:[\w.]+\s+){0,2}"
                        r"citizen(?:s|ship)?\b|\bcitizens?\s+only\b|\bcitizenship\s+(?:is\s+)?required", re.I)
LICENCE_RX = re.compile(r"(?:must|required to|need to)\s+(?:hold|have|possess)\s+(?:an?\s+)?"
                        r"(?:valid\s+|current\s+|active\s+)?(?:[\w']+\s+){0,3}licen[cs]e\b|"
                        r"valid\s+(?:[\w']+\s+){0,3}licen[cs]e\s+(?:is\s+)?required", re.I)
US_WORDS = re.compile(r"\bU\.?S\.?\b|united states|american", re.I)


def sentence_with(text, match):
    start = max(text.rfind(". ", 0, match.start()) + 2, 0)
    end = text.find(". ", match.end())
    return shorten(text[start: end + 1 if end >= 0 else len(text)])


def eligibility_blockers(full_text):
    out = []
    m = US_PERSON_RX.search(full_text)
    if m:
        out.append({"type": "us_person_export_control", "text": sentence_with(full_text, m)})
    m = CLEARANCE_RX.search(full_text)
    if m:
        out.append({"type": "security_clearance", "text": sentence_with(full_text, m)})
    for m in CITIZEN_RX.finditer(full_text):
        if not US_WORDS.search(m.group(0)):
            out.append({"type": "citizenship", "text": sentence_with(full_text, m)})
            break
    m = LICENCE_RX.search(full_text)
    if m:
        out.append({"type": "licence", "text": sentence_with(full_text, m)})
    return out


def blocker_counts(roles):
    """{blocker type: how many of these roles state it}, every type listed, 0 when none do."""
    counts = {t: 0 for t in C.BLOCKER_TYPES}
    for r in roles:
        for t in {b.get("type") for b in r.get("eligibility_blockers") or []}:
            if t in counts:
                counts[t] += 1
    return counts


def visa_note(full_text):
    for sent in re.split(r"(?<=[.!?])\s+", full_text):
        if re.search(r"\bvisa|relocation (assistance|support|package)|sponsor", sent, re.I):
            return shorten(sent)
    return None


def remote_status(base, text):
    if any(re.search(r"\bremote\b", s, re.I) for s in base["locations"]):
        return True
    wt = (base.get("workplace_type") or "").lower().replace("-", "").replace(" ", "")
    if wt == "remote" or base.get("is_remote") is True:
        return True
    if wt in ("hybrid", "onsite"):
        return False
    work_rx = (r"\bremote(?:ly)?[- ](?:work|role|position|option|friendly|eligible|first|opportunit|employ|candidate)|"
               r"\b(?:fully|100%)\s+remote|\bwork(?:ing)?\s+(?:from\s+home|remotely)|\bremote\s+(?:is|considered)")
    sents = [x for x in re.split(r"(?<=[.!?])\s+|\n", text) if re.search(work_rx, x, re.I)]
    if not sents:
        return False
    if all(re.search(r"\bnot\b|\bno\b|\bnon-|onsite|on-site|in[- ]office|in person", x, re.I) for x in sents):
        return False
    return "unknown"


def location_classes(locations, remote, config):
    """Location class ids for a role, in config order."""
    loc_cfg = config.get("locations") or {}
    classes = loc_cfg.get("classes") or []
    order = [c["id"] for c in classes]
    found = set()
    for loc in locations:
        hits = [c["id"] for c in classes if C.matches_any(c.get("keywords"), loc)]
        geo = [h for h in hits if h != "remote"]
        found.update(geo if geo else hits)
    if remote is True and not (found - {"remote"}) and "remote" in order:
        found.add("remote")
    if not found:
        return [loc_cfg.get("default_class") or "other"]
    return [c for c in order if c in found]

# ----------------------------------------------------------- classification


def classify(title, depts, config):
    """Return (family_id or None, classification_note, exclusion_reason)."""
    families = config.get("families") or []
    glob_ex = config.get("exclude_title_keywords") or []
    title_hit = [f for f in families if C.matches_any(f.get("title_keywords"), title)]
    if C.matches_any(glob_ex, title):
        reason = "title matches an exclude keyword" if title_hit else None
        return None, None, reason
    reason = None
    for fam in title_hit:
        if C.matches_any(fam.get("exclude_title_keywords"), title):
            reason = "title matches the %s family but also one of its exclude keywords" % fam["id"]
            continue
        return fam["id"], None, None
    for fam in families:
        if C.matches_any(fam.get("exclude_title_keywords"), title):
            continue
        for d in depts:
            if C.matches_any(fam.get("department_keywords"), d):
                return fam["id"], "Classified by department ('%s'); title has no family keyword." % d, None
    return None, None, reason

# ------------------------------------------------------------- adapters


def _split_locations(name):
    return list(dict.fromkeys(s.strip() for s in re.split(r"\s*[|;]\s*", name or "") if s.strip()))


def greenhouse_postings(data):
    for job in (data or {}).get("jobs") or []:
        raw = html.unescape(job.get("content") or "")
        depts = [d.get("name") for d in job.get("departments") or [] if d.get("name")]
        yield {
            "source_id": str(job.get("id")), "title": clean(job.get("title") or ""), "depts": depts,
            "team_or_department": " / ".join(depts) or None,
            "locations": _split_locations((job.get("location") or {}).get("name")),
            "extra_location_text": [o.get("location") or o.get("name") or "" for o in job.get("offices") or []],
            "workplace_type": None, "is_remote": None,
            "url": job.get("absolute_url"), "updated_at": job.get("updated_at"),
            "published_at": job.get("first_published"), "raw_html": raw, "compensation": greenhouse_pay(raw),
        }


def ashby_postings(data):
    for job in (data or {}).get("jobs") or []:
        if job.get("isListed") is False:
            continue
        sec = job.get("secondaryLocations") or []
        locs = [job.get("location") or ""] + [s.get("location") or "" for s in sec]
        dept, team = job.get("department") or "", job.get("team") or ""
        yield {
            "source_id": str(job.get("id")), "title": clean(job.get("title") or ""),
            "depts": [d for d in (dept, team) if d],
            "team_or_department": (dept if not team or team == dept else "%s / %s" % (dept, team)) or None,
            "locations": list(dict.fromkeys(s.strip() for s in locs if s and s.strip())),
            "extra_location_text": [], "workplace_type": job.get("workplaceType"),
            "is_remote": job.get("isRemote"), "url": job.get("jobUrl"),
            "updated_at": job.get("publishedAt"), "published_at": job.get("publishedAt"),
            "raw_html": job.get("descriptionHtml") or "", "compensation": ashby_pay(job),
        }


def _ms_to_iso(ms):
    if not isinstance(ms, (int, float)):
        return None
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def lever_postings(data):
    jobs = data if isinstance(data, list) else (data or {}).get("postings") or []
    for job in jobs:
        cats = job.get("categories") or {}
        locs = cats.get("allLocations") or ([cats["location"]] if cats.get("location") else [])
        parts = [job.get("description") or ""]
        for lst in job.get("lists") or []:
            parts.append("<h3>%s</h3><ul>%s</ul>" % (html.escape(lst.get("text") or ""), lst.get("content") or ""))
        parts.append(job.get("additional") or "")
        depts = [d for d in (cats.get("department"), cats.get("team")) if d]
        yield {
            "source_id": str(job.get("id")), "title": clean(job.get("text") or ""), "depts": depts,
            "team_or_department": " / ".join(dict.fromkeys(depts)) or None,
            "locations": list(dict.fromkeys(locs)), "extra_location_text": [],
            "workplace_type": job.get("workplaceType"), "is_remote": None,
            "url": job.get("hostedUrl"), "updated_at": _ms_to_iso(job.get("updatedAt") or job.get("createdAt")),
            "published_at": _ms_to_iso(job.get("createdAt")), "raw_html": "".join(parts),
            "compensation": lever_pay(job),
        }


def manual_postings(data, org):
    for job in (data or {}).get("postings") or []:
        if job.get("org") != org:
            continue
        desc = job.get("description") or ""
        raw = desc if "<" in desc else "".join("<p>%s</p>" % html.escape(p) for p in desc.split("\n") if p.strip())
        dept = job.get("department")
        yield {
            "source_id": str(job.get("id")), "title": clean(job.get("title") or ""),
            "depts": [dept] if dept else [], "team_or_department": dept,
            "locations": list(job.get("locations") or []), "extra_location_text": [],
            "workplace_type": "Remote" if job.get("remote") is True else None, "is_remote": job.get("remote"),
            "url": job.get("url"), "updated_at": job.get("updated_at"), "published_at": job.get("published_at"),
            "raw_html": raw, "compensation": job.get("compensation"),
        }


ADAPTERS = {"greenhouse": greenhouse_postings, "ashby": ashby_postings, "lever": lever_postings}

# ----------------------------------------------------------- record build


def org_stop_regex(target):
    names = [target.get("name") or ""] + list(target.get("aliases") or [])
    names = [re.escape(n) for n in names if n]
    return re.compile(r"^about (?:%s)\b" % "|".join(names), re.I) if names else None


def build_role(target, base, config):
    """Return (role or None, exclusion_reason or None)."""
    fam, note, reason = classify(base["title"], base["depts"], config)
    if not fam:
        return None, reason
    parsed = parse_posting(base["raw_html"], base["title"], org_stop_regex(target))
    heavy, signals = parsed["coding"]
    if not (config.get("heavy_coding") or {}).get("detect", True):
        heavy, signals = False, []
    fam_cfg = next(f for f in config["families"] if f["id"] == fam)
    if heavy and fam_cfg.get("drop_if_heavy_coding"):
        return None, "the %s family drops postings that expect production coding" % fam
    remote = remote_status(base, parsed["full_text"])
    role = {
        "id": "%s:%s" % (target["id"], base["source_id"]), "org": target["id"], "title": base["title"],
        "family": fam, "team_or_department": base["team_or_department"], "locations": base["locations"],
        "location_classes": location_classes(base["locations"] + [s for s in base["extra_location_text"] if s],
                                             remote, config),
        "remote": remote, "url": base["url"], "updated_at": base["updated_at"],
        "published_at": base["published_at"], "compensation": base["compensation"],
        "years_experience": parsed["years"], "years_experience_basis": parsed["years_basis"],
        "degree_requirement": parsed["degree"], "hard_requirements": parsed["hard"],
        "nice_to_haves": parsed["nice"], "responsibilities": parsed["resp"],
        "requires_heavy_coding": heavy, "coding_signals": signals,
        "eligibility_blockers": eligibility_blockers(parsed["full_text"]),
        "visa_or_relocation_note": visa_note(parsed["full_text"]),
        "description_text": parsed["text"],
    }
    if note:
        role["classification_note"] = note
    if parsed["parse_note"]:
        role["parse_note"] = parsed["parse_note"]
    return role, None

# ------------------------------------------------------------ snapshots


def previous_snapshot(snap_dir, date):
    files = sorted(f for f in glob.glob(os.path.join(snap_dir, "*.json"))
                   if re.match(r"\d{4}-\d{2}-\d{2}\.json$", os.path.basename(f)))
    older = [f for f in files if os.path.basename(f)[:10] < date]
    return (os.path.basename(older[-1])[:10], C.load_json(older[-1])) if older else (None, None)


def collect(config, workspace, fixtures=None, save_raw=None):
    """Fetch and classify every target. Returns (roles, excluded, fetched, errors, endpoints)."""
    roles, excluded, fetched, errors, endpoints = [], [], {}, {}, {}
    manual = C.load_json(C.wpath(workspace, "market", "roles", "manual.json"), {"postings": []})
    for target in config["targets"]:
        tid, ats = target["id"], target["ats"]
        try:
            if ats == "manual":
                postings = list(manual_postings(manual, tid))
                endpoints[tid] = "market/roles/manual.json"
            else:
                endpoints[tid] = ("fixture %s.json" % tid) if fixtures else endpoint(target)
                postings = list(ADAPTERS[ats](load_raw(target, fixtures, save_raw)))
                if not postings:
                    raise RuntimeError("endpoint returned zero postings")
        except Exception as exc:  # record and carry on with the other targets
            errors[tid] = "%s: %s" % (endpoints.get(tid), exc)
            fetched[tid] = 0
            continue
        fetched[tid] = len(postings)
        for base in postings:
            role, why = build_role(target, base, config)
            if role:
                roles.append(role)
            elif why:
                excluded.append({"org": tid, "title": base["title"], "url": base["url"], "reason": why})
    return roles, excluded, fetched, errors, endpoints


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fetch and classify open roles at the target organisations.")
    ap.add_argument("--workspace", help="workspace folder (default: $LVLME_HOME)")
    ap.add_argument("--fixtures", help="offline mode: read <DIR>/<target id>.json instead of the network")
    ap.add_argument("--save-raw", help="also save each raw API response to <DIR>/<target id>.json")
    ap.add_argument("--date", help="snapshot date YYYY-MM-DD (default: today in the candidate's time zone)")
    args = ap.parse_args(argv)
    ws, config = C.open_workspace(args.workspace)
    if C.setup_problem(config):
        print(C.setup_problem(config), file=sys.stderr)
        return 1
    date = C.check_date(args.date) if args.date else C.today_in(config)
    roles_dir = C.wpath(ws, "market", "roles")
    prev_latest = C.load_json(os.path.join(roles_dir, "latest.json"), {}) or {}
    prev_roles = {r["id"]: r for r in prev_latest.get("roles", [])}

    roles, excluded, fetched, errors, endpoints = collect(config, ws, args.fixtures, args.save_raw)
    remote_targets = [t["id"] for t in config["targets"] if t["ats"] != "manual"]
    if remote_targets and all(t in errors for t in remote_targets) and not roles:
        print(json.dumps({"endpoint_errors": errors}, indent=2), file=sys.stderr)
        print("lvlme: every job board failed; latest.json left unchanged.", file=sys.stderr)
        return 1
    for tid in errors:  # keep the last known roles for a board that failed today
        roles.extend(r for r in prev_roles.values() if r.get("org") == tid)

    for r in roles:
        r["first_seen"] = (prev_roles.get(r["id"]) or {}).get("first_seen") or date
    order = {t: i for i, t in enumerate(C.target_ids(config))}
    roles.sort(key=lambda r: (order.get(r["org"], 99), r["family"], r["title"].lower(), r["id"]))

    snap_dir = os.path.join(roles_dir, "snapshots")
    prev_date, prev_snap = previous_snapshot(snap_dir, date)
    prev_ids = set((prev_snap or {}).get("roles", {}))
    cur_ids = {r["id"] for r in roles}
    errored = set(errors)
    new_ids = sorted(i for i in cur_ids - prev_ids) if prev_snap else []
    closed_ids = sorted(i for i in prev_ids - cur_ids if i.split(":", 1)[0] not in errored) if prev_snap else []

    fam_ids = [f["id"] for f in config["families"]]
    counts = {t: dict({f: 0 for f in fam_ids}, total=0) for t in C.target_ids(config)}
    for r in roles:
        counts[r["org"]][r["family"]] += 1
        counts[r["org"]]["total"] += 1
    cleared = set((config.get("candidate") or {}).get("eligibility_cleared") or [])
    summary = {
        "endpoints": endpoints,
        "total_postings_fetched": fetched,
        "matched_counts": counts,
        "matched_total": len(roles),
        "remote_true": sum(1 for r in roles if r["remote"] is True),
        "blocked_by_eligibility": sum(1 for r in roles if any(
            b["type"] not in cleared for b in r.get("eligibility_blockers", []))),
        "blocker_counts": blocker_counts(roles),
        "excluded_count": len(excluded),
        "endpoint_errors": errors,
        "previous_snapshot": prev_date,
        "new_role_ids": new_ids,
        "closed_role_ids": closed_ids,
    }
    out = {"schema_version": 1, "fetched_on": date,
           "fetched_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "summary": summary, "roles": roles, "excluded": excluded}
    if args.fixtures:  # offline runs are reproducible: no wall-clock time in the output
        out["fetched_at_utc"] = date + "T00:00:00Z"
    C.write_json(os.path.join(roles_dir, "latest.json"), out)
    snapshot = {"schema_version": 1, "date": date,
                "roles": {r["id"]: {"org": r["org"], "title": r["title"], "family": r["family"]} for r in roles}}
    C.write_json(os.path.join(snap_dir, "%s.json" % date), snapshot)
    print(json.dumps({"fetched_on": date, "total_postings_fetched": fetched, "matched_counts": counts,
                      "new_roles": len(new_ids), "closed_roles": len(closed_ids),
                      "blocker_counts": summary["blocker_counts"], "endpoint_errors": errors}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(C.run_main(main))
