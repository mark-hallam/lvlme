#!/usr/bin/env python3
"""Fetch open roles from the target organisations' public job boards.

Reads config.json (targets, role families and their keywords, location
classes) and writes:
  market/roles/latest.json              every open role that matches a family
  market/roles/snapshots/<date>.json    the role ids open on that date

Adapters: Greenhouse, Ashby, Lever, Workday, SmartRecruiters and Workable
public job-board APIs, plus "manual" (roles typed into market/roles/manual.json).
Greenhouse, Ashby and Lever give every posting in one answer. Workday,
SmartRecruiters and Workable list titles only, so the list is read page by
page and only the postings whose title fits a role family are read, with the
readers in scripts/_boards.py. Standard library only.
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
                security clearance, a named citizenship, a licence, AHPRA or
                other professional registration, a Working With Children Check,
                a police check, an Australian clearance level, or a White Card.
  blocker_counts  (in the summary, and printed) how many matched open roles
                state each blocker type. The interview asks the export
                control and clearance questions only when their count is
                above 0 (`method/INTERVIEW.md`, "Work rights"). Counts for
                `security_clearance` and `australian_security_clearance` both
                gate the clearance question.
  requires_heavy_coding  heuristic; coding_signals lists the phrases found.
                When candidate.writes_production_code is false, a software or
                coding title (software, coding or programming in the title or
                posting, or a known software role such as backend engineer)
                counts too, unless the posting says the role needs no production
                code. Civil, site, maintenance, biomedical and property roles
                are not treated as coding jobs from the title alone.
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _certs as CT  # noqa: E402
import _common as C  # noqa: E402
from _html_text import blocks_of, clean  # noqa: E402,F401  (FR.clean and FR.blocks_of stay in use)
import _boards as B  # noqa: E402
import _posting_checks as P  # noqa: E402

UA = "lvlme/0.6 (personal job-search research script; read only)"
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
    if ats in B.LISTED:
        try:
            return B.list_request(target, 0)[0]
        except ValueError:
            return None
    return None


def fetch_json(url, tries=3, timeout=90, body=None):
    """GET a JSON answer, or POST body as JSON (the Workday and Workable job lists ask for a POST)."""
    last = None
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with CT.open_checked(urllib.request.urlopen, req, timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            last = exc
            if attempt + 1 < tries:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError("%s: %s" % (type(last).__name__, last))


def load_raw(target, fixtures, save_raw, config=None):
    """Raw API response for one target: from fixtures if given, else the network."""
    if fixtures:
        path = os.path.join(fixtures, "%s.json" % target["id"])
        if not os.path.exists(path):
            raise RuntimeError("no fixture file %s" % path)
        return C.load_json(path)
    data = fetch_board(target, config) if target.get("ats") in B.LISTED else fetch_json(endpoint(target))
    if save_raw:
        C.write_json(os.path.join(save_raw, "%s.json" % target["id"]), data)
    return data


def fetch_board(target, config, pause=0.2):
    """Read a Workday, SmartRecruiters or Workable board: page through its job list, then read each posting
    whose title fits a role family. Other titles are kept as skipped, with the reason, never silently dropped.

    Returns a bundle, saved and read back exactly like any other board's raw answer:
    {"listed": n, "capped": bool, "postings": [{"link", "data"}], "skipped": [{"title", "url", "reason"}]}.
    """
    listed, token, offset, capped, reported = {}, None, 0, False, None
    while True:
        url, body = B.list_request(target, offset, token)
        data = fetch_json(url, body=body)
        jobs, token = B.list_page(target, data)
        reported = reported if reported is not None else B.list_total(target, data)
        fresh = [j for j in jobs if j["url"] not in listed]  # Workday repeats its last page past 2000 jobs
        listed.update((j["url"], j) for j in fresh)
        offset += B.PAGE[target["ats"]]
        if len(listed) >= B.MAX_LISTED:
            capped = True
            break
        if not fresh or (token is None and (target["ats"] == "workable" or len(jobs) < B.PAGE[target["ats"]])):
            break
        time.sleep(pause)
    capped = capped or bool(reported and reported > len(listed))
    postings, skipped = [], []
    for job in listed.values():
        fam, _, reason = classify(job["title"], job["depts"], config)
        if not fam:
            skipped.append({"title": job["title"], "url": job["url"], "reason": reason or "no role family matched"})
            continue
        time.sleep(pause)
        postings.append({"link": job["link"], "data": fetch_json(B.detail_url(job["link"]))})
    return {"listed": len(listed), "capped": capped, **({"reported": reported} if capped and reported else {}),
            "postings": postings, "skipped": skipped}

# ------------------------------------------------------------ HTML parsing


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
# Main title ends in Engineer or Developer, or starts with Engineering Manager.
ENGINEERING_JOB = re.compile(r"(?:\b(?:engineer|developer)(?:\s+(?:i{1,3}|iv|v|\d))?\s*$|^\s*(?:senior\s+|sr\.?\s+)?engineering\s+manager\b)", re.I)
NON_SOFTWARE_ENGINEER = re.compile(
    r"\bcivil\s+(?:\w+\s+)*engineer\b|"
    r"\binfrastructure\s+engineer\b|"
    r"\b(?:site|maintenance|biomedical|structural|mechanical|electrical|environmental|"
    r"property|construction|manufacturing|process|packaging|chemical|project)\s+"
    r"(?:engineer|developer)\b|"
    r"\b(?<!software\s)quality\s+(?:engineer|developer)\b|"
    r"\b(?<!site\s)reliability\s+(?:engineer|developer)\b|"
    r"\bproperty\s+developer\b",
    re.I,
)
# Clear software or coding words in a title. Fuzzy words (platform, deployment,
# performance, bare ml) are not enough on their own; the posting decides those.
TITLE_SOFTWARE_CODING_WORD = re.compile(
    r"\b(?:software|coding|programming|programmer|devops|sre\b|"
    r"backend|back[- ]end|frontend|front[- ]end|full[- ]stack|fullstack|"
    r"machine\s+learning|android|ios|"
    r"forward[- ]deployed|"
    r"site\s+reliability|software\s+quality|"
    r"plugin|monetization|chatgpt|data\s+engineer|analytics\s+engineer)\b",
    re.I,
)
POSTING_SOFTWARE_CODING_WORD = re.compile(
    r"\b(?:software|coding|programming|programmer|devops|sre\b|"
    r"backend|back[- ]end|frontend|front[- ]end|full[- ]stack|fullstack|"
    r"machine\s+learning|android|ios|"
    r"plugin|chatgpt|data\s+engineer|analytics\s+engineer)\b",
    re.I,
)


def posting_shows_coding(posting_text):
    """True when duties, requirements or description show software or coding work."""
    if not posting_text:
        return False
    if POSTING_SOFTWARE_CODING_WORD.search(posting_text):
        return True
    for rx in CODE_STRONG:
        for m in re.finditer(rx, posting_text, re.I):
            if not NEGATION.search(posting_text[max(0, m.start() - 40):m.start()]):
                return True
    return False


def engineering_title(title, posting_text=None):
    """True when the role is a software or coding job.

    Clear title words (software, backend, programming) still count. Fuzzy
    title words (platform, deployment, performance) do not, on their own.
    A non-software-looking title can still count when the posting shows
    coding work.
    """
    main = re.split(r"\s*(?:,|\(|\||\s[-\u2013\u2014]\s)", title or "", maxsplit=1)[0]
    body_coding = posting_shows_coding(posting_text)
    if NON_SOFTWARE_ENGINEER.search(main):
        return body_coding
    if not ENGINEERING_JOB.search(main):
        return False
    if TITLE_SOFTWARE_CODING_WORD.search(main):
        return True
    return body_coding


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
    heavy = bool(core or (engineering_title(title, text) and hits) or len(hits) >= 2)
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
    intro = [i for c, _, items in secs if c == "intro" for i in items]
    extra = [i for c, _, items in secs if c == "other" for i in items]
    role_text = " ".join(req + resp + nice + intro + extra)
    heavy, hits = coding_check(title, role_text)
    return {
        "hard": [shorten(i) for i in req if len(i) > 3][:6],
        "nice": [shorten(i) for i in nice if len(i) > 3][:4],
        "resp": [shorten(i) for i in resp if len(i) > 3][:6],
        "years": years, "years_basis": basis, "degree": degree,
        "text": "\n".join(lines), "full_text": full_text,
        "role_text": role_text,
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
HEALTH_REG_RX = re.compile(
    r"\bAHPRA\b|Australian\s+Health\s+Practitioner\s+Regulation\s+Agency|"
    r"(?:current\s+)?registration\s+with\s+(?:the\s+)?Australian\s+Health\s+Practitioner\s+Regulation\s+Agency|"
    r"registered\s+(?:[\w-]+\s+){0,4}(?:nurse|midwife|physiotherapist|psychologist|doctor|dentist)\s+with\s+AHPRA",
    re.I)
TEACHER_REG_RX = re.compile(
    r"teacher\s+registration\s+(?:is\s+)?required|"
    r"(?:must\s+hold|current|valid)\s+(?:[\w-]+\s+){0,3}teacher\s+registration|"
    r"teacher\s+registration\s+with\s+(?:the\s+)?(?:VIT|NESA)\b|"
    r"registration\s+with\s+(?:the\s+)?(?:QCT|Queensland\s+College\s+of\s+Teachers)\b|"
    r"(?:registration\s+with\s+(?:the\s+)?(?:VIT|Victorian\s+Institute\s+of\s+Teaching|NESA)|"
    r"Victorian\s+Institute\s+of\s+Teaching|NSW\s+Education\s+Standards\s+Authority|"
    r"registered\s+with\s+(?:the\s+)?(?:VIT|Victorian\s+Institute\s+of\s+Teaching|NESA))\b",
    re.I)
WWCC_RX = re.compile(
    r"working\s+with\s+children\s+check|\bWWCC\b|"
    r"(?:valid|current)\s+WWC\s+check",
    re.I)
POLICE_RX = re.compile(
    r"national\s+police\s+check|"
    r"AFP\s+(?:national\s+)?(?:police\s+)?check|"
    r"(?:must\s+hold|current|valid)\s+(?:a\s+)?national\s+police\s+check|"
    r"(?:must\s+hold|current|valid)\s+(?:a\s+)?police\s+check",
    re.I)
# The Australian levels: Baseline and Negative Vetting, written in full or as the short two letter code with its number.
_AU_LEVEL = r"(?:baseline|nv\s?[12]|negative\s+vetting(?:\s+level\s*[12])?)"
AU_CLEARANCE_RX = re.compile(
    r"\b" + _AU_LEVEL + r"\b(?:\s+level)?(?:\s+security)?\s+clearance|"
    r"Australian\s+Government\s+Security\s+Vetting|\bAGSVA\b|"
    r"(?:ability\s+to\s+obtain|must\s+hold|hold\s+or\s+obtain|current)\s+"
    r"(?:an?\s+)?" + _AU_LEVEL + r"(?:\s+(?:security\s+)?clearance)?",
    re.I)
WHITE_CARD_RX = re.compile(
    r"\bwhite\s+card\b|"
    r"(?:must\s+hold|required\s+to\s+hold|hold\s+(?:a\s+)?valid)\s+"
    r"(?:a\s+)?construction\s+induction(?:\s+card)?|"
    r"construction\s+induction(?:\s+card)?\s+(?:is\s+)?required|"
    r"\bCPCCWHS1001\b",
    re.I)
US_WORDS = re.compile(r"\bU\.?S\.?\b|united states|american", re.I)


def sentence_with(text, match):
    dot = text.rfind(". ", 0, match.start())
    start = dot + 2 if dot >= 0 else 0
    end = text.find(". ", match.end())
    return shorten(text[start: end + 1 if end >= 0 else len(text)])


def _append_blocker(out, kind, text):
    if not any(b["type"] == kind and b["text"] == text for b in out):
        out.append({"type": kind, "text": text})


def eligibility_blockers(full_text):
    out = []
    m = US_PERSON_RX.search(full_text)
    if m:
        out.append({"type": "us_person_export_control", "text": sentence_with(full_text, m)})
    for m in AU_CLEARANCE_RX.finditer(full_text):
        _append_blocker(out, "australian_security_clearance", sentence_with(full_text, m))
    for m in CLEARANCE_RX.finditer(full_text):
        sent = sentence_with(full_text, m)
        if not AU_CLEARANCE_RX.search(sent):
            _append_blocker(out, "security_clearance", sent)
    for m in CITIZEN_RX.finditer(full_text):
        if not US_WORDS.search(m.group(0)):
            out.append({"type": "citizenship", "text": sentence_with(full_text, m)})
            break
    m = LICENCE_RX.search(full_text)
    if m:
        out.append({"type": "licence", "text": sentence_with(full_text, m)})
    for rx, kind in (
        (HEALTH_REG_RX, "health_practitioner_registration"),
        (TEACHER_REG_RX, "teacher_registration"),
        (WWCC_RX, "working_with_children_check"),
        (POLICE_RX, "police_check"),
        (WHITE_CARD_RX, "white_card"),
    ):
        m = rx.search(full_text)
        if m:
            out.append({"type": kind, "text": sentence_with(full_text, m)})
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


def workplace(base):
    """The board's own workplace label as Remote, Hybrid or Onsite, or None when it gives none."""
    wt = (base.get("workplace_type") or "").lower().replace("-", "").replace(" ", "").replace("_", "")
    return {"remote": "Remote", "hybrid": "Hybrid", "onsite": "Onsite"}.get(wt)


def remote_status(base, text):
    # The board's workplace label wins over its is_remote flag: Ashby sends isRemote true with
    # workplaceType Hybrid for roles based in an office three days a week.
    wt = workplace(base)
    if wt == "Remote":
        return True
    if any(re.search(r"\bremote\b", s, re.I) for s in base["locations"]):
        return True
    if wt in ("Hybrid", "Onsite"):
        return False
    if base.get("is_remote") is True:
        return True
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
        wt = job.get("workplace_type")
        is_remote = job.get("remote")
        if wt:
            workplace_type = wt
        elif is_remote is True:
            workplace_type = "Remote"
        else:
            workplace_type = None
        yield {
            "source_id": str(job.get("id")), "title": clean(job.get("title") or ""),
            "depts": [dept] if dept else [], "team_or_department": dept,
            "locations": list(job.get("locations") or []), "extra_location_text": [],
            "workplace_type": workplace_type, "is_remote": is_remote,
            "url": job.get("url"), "updated_at": job.get("updated_at"), "published_at": job.get("published_at"),
            "raw_html": raw, "compensation": job.get("compensation"),
        }


ADAPTERS = {"greenhouse": greenhouse_postings, "ashby": ashby_postings, "lever": lever_postings,
            "workday": B.bundle_postings, "smartrecruiters": B.bundle_postings, "workable": B.bundle_postings}

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
    elif (not heavy and "candidate" in config and not (config["candidate"] or {}).get("writes_production_code", False)
          and engineering_title(base["title"], parsed.get("role_text") or parsed.get("full_text") or "")
          and not any(s.startswith("NOT required") for s in signals)):
        # Someone who doesn't write production code: a software or coding title counts as heavy coding
        # unless the posting itself says the role doesn't need it.
        heavy, signals = True, signals + ["title names a software or coding job: " + base["title"][:70]]
    fam_cfg = next(f for f in config["families"] if f["id"] == fam)
    if heavy and fam_cfg.get("drop_if_heavy_coding"):
        return None, "the %s family drops postings that expect production coding" % fam
    remote = remote_status(base, parsed["full_text"])
    role = {
        "id": "%s:%s" % (target["id"], base["source_id"]), "org": target["id"], "title": base["title"],
        "family": fam, "team_or_department": base["team_or_department"], "locations": base["locations"],
        "location_classes": location_classes(base["locations"] + [s for s in base["extra_location_text"] if s],
                                             remote, config),
        "remote": remote, "workplace": workplace(base), "url": base["url"], "updated_at": base["updated_at"],
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


def snapshot_history(snap_dir, date):
    """[(date, roles)] for the snapshots before date, within the repost window (scripts/_posting_checks.py)."""
    out = []
    for f in sorted(glob.glob(os.path.join(snap_dir, "*.json"))):
        d = os.path.basename(f)[:10]
        if re.match(r"\d{4}-\d{2}-\d{2}$", d) and d < date and (P.age_days(d, date) or 0) <= P.WINDOW_DAYS:
            out.append((d, (C.load_json(f, {}) or {}).get("roles") or {}))
    return out


def collect(config, workspace, fixtures=None, save_raw=None):
    """Fetch and classify every target. Returns (roles, excluded, fetched, errors, endpoints, notes)."""
    roles, excluded, fetched, errors, endpoints, notes = [], [], {}, {}, {}, {}
    manual = C.load_json(C.wpath(workspace, "market", "roles", "manual.json"), {"postings": []})
    for target in config["targets"]:
        tid, ats = target["id"], target["ats"]
        try:
            if ats == "manual":
                postings = list(manual_postings(manual, tid))
                endpoints[tid] = "market/roles/manual.json"
            else:
                endpoints[tid] = ("fixture %s.json" % tid) if fixtures else (endpoint(target) or ats)
                raw = load_raw(target, fixtures, save_raw, config)
                postings = list(ADAPTERS[ats](raw))
                if ats in B.LISTED:  # titles that fit no family were never read: list them as excluded
                    excluded.extend(dict(x, org=tid) for x in raw.get("skipped") or [])
                    if raw.get("capped"):
                        notes[tid] = "listed %d of the board's %s jobs only, so some roles may be missing" % (
                            raw["listed"], raw.get("reported") or "many")
                if not postings and not (ats in B.LISTED and raw.get("listed")):
                    raise RuntimeError("endpoint returned zero postings")
        except CT.CertificateProblem:  # the same for every board: stop with the one line that says the fix
            raise
        except Exception as exc:  # record and carry on with the other targets
            errors[tid] = "%s: %s" % (endpoints.get(tid), exc)
            fetched[tid] = 0
            continue
        fetched[tid] = raw.get("listed", len(postings)) if ats in B.LISTED else len(postings)
        for base in postings:
            role, why = build_role(target, base, config)
            if role:
                roles.append(role)
            elif why:
                excluded.append({"org": tid, "title": base["title"], "url": base["url"], "reason": why})
    return roles, excluded, fetched, errors, endpoints, notes


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

    roles, excluded, fetched, errors, endpoints, notes = collect(config, ws, args.fixtures, args.save_raw)
    data_date = prev_latest.get("fetched_on") or "unknown"
    remote_targets = [t["id"] for t in config["targets"] if t["ats"] != "manual"]
    if remote_targets and all(t in errors for t in remote_targets) and not roles:
        C.write_json(os.path.join(roles_dir, "fetch-status.json"),
                     {"date": date, "ok": False, "board_errors": errors, "data_date": data_date})
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
    snap_roles = {r["id"]: {"org": r["org"], "title": r["title"], "family": r["family"], "url": r.get("url"),
                            "published_at": r.get("published_at"),
                            "location": ", ".join(r.get("locations") or [])} for r in roles}
    checks = P.apply_checks(roles, snapshot_history(snap_dir, date) + [(date, snap_roles)], date,
                            {t["id"]: t.get("ats") for t in config["targets"]})
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
        "posting_checks": checks,
        "endpoint_errors": errors,
        **({"endpoint_notes": notes} if notes else {}),
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
    C.write_json(os.path.join(roles_dir, "fetch-status.json"),
                 {"date": date, "ok": not bool(errors), "board_errors": errors,
                  "data_date": date if not errors else data_date})
    snapshot = {"schema_version": 1, "date": date, "roles": snap_roles}
    C.write_json(os.path.join(snap_dir, "%s.json" % date), snapshot)
    print(json.dumps({"fetched_on": date, "total_postings_fetched": fetched, "matched_counts": counts,
                      "new_roles": len(new_ids), "closed_roles": len(closed_ids),
                      "blocker_counts": summary["blocker_counts"], "posting_checks": checks,
                      "endpoint_errors": errors,
                      **({"endpoint_notes": notes} if notes else {})}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(C.run_main(main))
