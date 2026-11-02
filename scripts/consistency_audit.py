#!/usr/bin/env python3
"""Check that the person's work history says the same thing in every source.

Recruiters and background checks compare the CV, LinkedIn, the website and
official forms. A raised title (a missing "Deputy") reads as dishonesty, and
dates that differ by a few months read as careless. This script compares role
records copied from each source and reports:

  title_mismatch       titles differ; "likely inflation" when one title leaves
                       out a qualifier (Deputy, Assistant, Acting, Associate and
                       so on) or is a seniority step above the other
  date_mismatch        start or end dates differ by more than the tolerance, or
                       one source says the role is current and another does not
  missing_role         a role is missing from a source that should list it
  gap                  time between roles longer than the gap limit, unexplained
  overlap              two roles at the same time, not marked concurrent
  single_source_claim  a claim on only one of the person's own pages
  claim_mismatch       the same claim with different numbers in different places
  denied_claim         a claim the person says is not true

It suggests one source of truth per role and the exact fixes per source. It
changes nothing except its own two output files.

Input:  profile/role-records.json (schemas/role-records.schema.json)
Output: profile/consistency.json (schemas/consistency.schema.json) and
        profile/consistency.md

Usage
  python3 scripts/consistency_audit.py --workspace PATH
  python3 scripts/consistency_audit.py --input FILE [--json]    (prints only, writes nothing)
Options: --tolerance-months N (default 1), --gap-months N (default 3), --today YYYY-MM-DD
Exit codes: 0 done (findings are not errors), 1 bad input, 2 refused location.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402
import validate as V  # noqa: E402
from network_map import normalise as normalise_org  # noqa: E402

CONFIRMED = "confirmed"
DEFAULT_ORDER = [CONFIRMED, "official_form", "references", "cv", "linkedin", "website"]
SOURCE_NAMES = {CONFIRMED: "Confirmed by the person", "official_form": "Official form", "references": "References",
                "cv": "CV", "linkedin": "LinkedIn", "website": "Website"}
COMPLETE_BY_DEFAULT = {CONFIRMED, "official_form", "cv", "linkedin"}
FIXED_BY_DEFAULT = {"official_form", "references"}
TITLE_KINDS = {"role", "business", "volunteer"}
LISTED_KINDS = {"role", "business"}
SEVERITIES = ["high", "medium", "low"]
TYPES = ["title_mismatch", "date_mismatch", "missing_role", "denied_claim", "claim_mismatch",
         "single_source_claim", "overlap", "gap"]
ONGOING = "present"
ONGOING_WORDS = {"present", "current", "currently", "now", "today", "ongoing", "to date", "date"}
FULL_MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september",
               "october", "november", "december"]
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Title words. A qualifier lowers a title; leaving one out is the classic inflation.
QUALIFIERS = {"deputy", "assistant", "acting", "associate", "junior", "trainee", "graduate", "intern",
              "interim", "vice", "apprentice", "co", "sub"}
RANKS = {"intern": 0, "trainee": 0, "apprentice": 0, "graduate": 0, "assistant": 1, "associate": 1,
         "officer": 1, "coordinator": 1, "administrator": 1, "analyst": 1, "specialist": 1, "engineer": 1,
         "consultant": 1, "advisor": 1, "developer": 1, "designer": 1, "technician": 1, "scientist": 1,
         "researcher": 1, "supervisor": 2, "lead": 2, "leader": 2, "manager": 3, "head": 4, "director": 5,
         "president": 6, "chief": 7}
MODIFIERS = {"senior": 1, "principal": 1, "general": 1, "executive": 1, "junior": -1}
EXPAND = {"mgr": "manager", "sr": "senior", "snr": "senior", "jr": "junior", "asst": "assistant",
          "assoc": "associate", "dep": "deputy", "vp": "vice president", "svp": "senior vice president",
          "gm": "general manager", "ceo": "chief executive officer", "cto": "chief technology officer",
          "cfo": "chief financial officer", "coo": "chief operating officer", "programme": "program",
          "adviser": "advisor", "organisation": "organization", "defence": "defense", "centre": "center"}
STOP = {"of", "the", "and", "for", "to", "in", "a", "an", "at", "on", "with", "by", "from", "my", "our",
        "i", "we", "as", "into", "over", "across", "per", "was", "were", "is", "are", "that", "this"}


class InputError(Exception):
    """Raised when role-records.json cannot be read; carries a list of messages."""


# ----------------------------------------------------------------- dates


def parse_month(value):
    """'Oct 2007', 'October 2007', '2007-10', '10/2007', '2007' -> (2007, 10) or (2007, None).

    'present', 'current' or 'now' -> ONGOING. None or '' -> None (not given).
    """
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value).strip().lower()).rstrip(".")
    if not text:
        return None
    if text in ONGOING_WORDS:
        return ONGOING
    year, month = None, None
    m = re.fullmatch(r"(\d{4})", text)
    if m:
        year = int(m.group(1))
    elif re.fullmatch(r"\d{4}[-/.]\d{1,2}([-/.]\d{1,2})?", text):
        parts = re.split(r"[-/.]", text)
        year, month = int(parts[0]), int(parts[1])
    elif re.fullmatch(r"\d{1,2}[-/.]\d{4}", text):
        month, year = (int(p) for p in re.split(r"[-/.]", text))
    else:
        m = re.fullmatch(r"(?:\d{1,2} )?([a-z]+)\.?,? (?:\d{1,2},? )?(\d{4})", text)
        month = month_from_word(m.group(1)) if m else None
        if month is None:
            raise ValueError("cannot read the date %r (use 'Oct 2007', '2007-10' or '2007')" % value)
        year = int(m.group(2))
    if not 1900 <= year <= 2100 or (month is not None and not 1 <= month <= 12):
        raise ValueError("the date %r is out of range" % value)
    return (year, month)


def month_from_word(word):
    """'oct', 'october' or 'sept' -> 10 or 9; anything else -> None."""
    for i, full in enumerate(FULL_MONTHS, 1):
        if word == full or (len(word) >= 3 and full.startswith(word)) or (word == "sept" and i == 9):
            return i
    return None


def month_index(d, edge):
    """Month number of a parsed date; a year alone counts as January ('lo') or December ('hi')."""
    year, month = d
    return year * 12 + ((month or (1 if edge == "lo" else 12)) - 1)


def date_diff(a, b):
    """Months between two parsed dates at the coarser precision; None if only one is ongoing."""
    if a == ONGOING or b == ONGOING:
        return 0 if a == b else None
    if a[1] is None or b[1] is None:
        return abs(a[0] - b[0]) * 12
    return abs(month_index(a, "lo") - month_index(b, "lo"))


def iso(d):
    if d is None or d == ONGOING:
        return d
    return "%04d" % d[0] if d[1] is None else "%04d-%02d" % d


def human(d):
    if d is None:
        return "not given"
    if d == ONGOING:
        return ONGOING
    return str(d[0]) if d[1] is None else "%s %d" % (MONTH_NAMES[d[1] - 1], d[0])


def human_index(i):
    return "%s %d" % (MONTH_NAMES[i % 12], i // 12)


def period(start, end, today_idx, generous=True):
    """(first, last) month numbers. Generous widens year-only dates (for gaps); narrow shrinks them (overlaps)."""
    lo = month_index(start, "lo" if generous else "hi")
    if end is None:
        hi = lo
    elif end == ONGOING:
        hi = today_idx
    else:
        hi = month_index(end, "hi" if generous else "lo")
    return lo, max(lo, hi)


# ----------------------------------------------------------------- words


def stem(word):
    if len(word) > 5 and word.endswith("ing"):
        return word[:-3]
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def title_tokens(title):
    """Normalised title words: 'Sr. Quality Mgr' and 'Senior Quality Manager' give the same tuple."""
    words = re.findall(r"[a-z0-9]+", (title or "").lower().replace("&", " and "))
    out = []
    for w in words:
        out.extend(EXPAND.get(w, w).split())
    known = QUALIFIERS | set(RANKS) | set(MODIFIERS)
    return tuple(sorted(w if w in known else stem(w) for w in out if w not in STOP))


def seniority(tokens):
    ranks = [RANKS[t] for t in tokens if t in RANKS]
    mods = sum(MODIFIERS.get(t, 0) for t in tokens if t != "executive" or ranks)
    return (max(ranks) if ranks else 1) * 10 + mods * 3 - 5 * sum(1 for t in tokens if t in QUALIFIERS)


def core(tokens):
    return set(tokens) - QUALIFIERS - set(RANKS) - set(MODIFIERS)


def inflation(a, b):
    """(higher, lower, words) if one title reads as a raised version of the other, else None.

    words lists the qualifiers the higher title leaves out; empty means a seniority step.
    """
    for hi, lo in ((a, b), (b, a)):
        dropped = (set(lo) - set(hi)) & QUALIFIERS
        if dropped and set(lo) - QUALIFIERS == set(hi) - QUALIFIERS and not (set(hi) - set(lo)) & QUALIFIERS:
            return hi, lo, sorted(dropped)
    ranked = all(any(t in RANKS for t in x) for x in (a, b))
    only_levels = (set(a) ^ set(b)) <= set(MODIFIERS) | QUALIFIERS
    if core(a) == core(b) and seniority(a) != seniority(b) and (ranked or only_levels):
        return (a, b, []) if seniority(a) > seniority(b) else (b, a, [])
    return None


def claim_tokens(text):
    words = re.findall(r"[a-z]+|\d+(?:[.,]\d+)?", (text or "").lower())
    return {stem(w) for w in words if w not in STOP and (len(w) > 2 or w[0].isdigit())}


def numbers(text):
    return sorted(set(re.findall(r"\d+(?:[.,]\d+)?", text or "")))


def similar(a, b):
    both = len(a & b)
    return both >= 2 and both / max(1, min(len(a), len(b))) >= 0.6


# ----------------------------------------------------------------- input


def read_input(doc, today_idx):
    """Return (sources, order, records, explained). Raises InputError."""
    schema = C.load_json(os.path.join(C.SCHEMA_DIR, "role-records.schema.json"))
    errors = V.check(doc, schema)
    if errors:
        raise InputError(errors)
    raw = doc["sources"]
    given = doc.get("truth_order") or DEFAULT_ORDER
    order = [s for s in given if s in raw] + [s for s in raw if s not in given]
    sources, records, errors = {}, [], []
    aliases = {}
    for canon, names in (doc.get("organisation_aliases") or {}).items():
        for name in [canon] + list(names):
            aliases[normalise_org(name)] = normalise_org(canon)
    for sid in order:
        src = raw[sid]
        if not re.fullmatch(r"[a-z][a-z0-9_]*", sid):
            errors.append("sources.%s: source ids use lower case letters, digits and _" % sid)
        info = {"id": sid, "label": src.get("label") or SOURCE_NAMES.get(sid, sid),
                "complete": src.get("complete", sid in COMPLETE_BY_DEFAULT),
                "editable": src.get("editable", sid not in FIXED_BY_DEFAULT and sid != CONFIRMED),
                "records": len(src["records"])}
        if src.get("ref"):
            info["ref"] = src["ref"]
        try:
            cov = src.get("covers") or {}
            info["covers"] = (parse_month(cov.get("from")), parse_month(cov.get("to")))
        except ValueError as exc:
            errors.append("sources.%s.covers: %s" % (sid, exc))
        sources[sid] = info
        for i, r in enumerate(src["records"]):
            where = "sources.%s.records[%d]" % (sid, i)
            try:
                start, end = parse_month(r.get("start")), parse_month(r.get("end"))
            except ValueError as exc:
                errors.append("%s: %s" % (where, exc))
                continue
            if start == ONGOING:
                errors.append("%s: start cannot be %r" % (where, r.get("start")))
                continue
            if start and end and end != ONGOING and month_index(end, "hi") < month_index(start, "lo"):
                errors.append("%s: ends before it starts" % where)
                continue
            org_key = normalise_org(r["organisation"])
            records.append({"source": sid, "where": where, "org": r["organisation"],
                            "org_key": aliases.get(org_key, org_key), "title": (r.get("title") or "").strip(),
                            "tokens": title_tokens(r.get("title")), "start": start, "end": end,
                            "kind": r.get("kind", "role"), "key": r.get("key"), "concurrent": bool(r.get("concurrent")),
                            "claims": list(r.get("claims") or []), "denies": list(r.get("denies") or []),
                            "evidence": list(r.get("evidence") or [])})
    explained = []
    for i, g in enumerate(doc.get("explained_gaps") or []):
        try:
            start, end = parse_month(g["start"]), parse_month(g["end"])
            if start in (None, ONGOING) or end is None:
                raise ValueError("needs a start and an end")
            explained.append(period(start, end, today_idx))
        except ValueError as exc:
            errors.append("explained_gaps[%d]: %s" % (i, exc))
    if errors:
        raise InputError(errors)
    return sources, order, records, explained


# ---------------------------------------------------------------- groups


def kind_family(kind):
    return "education" if kind == "education" else "work"


def match_score(rec, group, today_idx):
    best = 0.0
    for other in group["members"].values():
        a, b = set(rec["tokens"]), set(other["tokens"])
        sim = len(a & b) / len(a | b) if a | b else 0.0
        if rec["start"] and other["start"]:
            p, q = period(rec["start"], rec["end"], today_idx), period(other["start"], other["end"], today_idx)
            shared = min(p[1], q[1]) - max(p[0], q[0]) + 1
            ratio = max(0, shared) / min(p[1] - p[0] + 1, q[1] - q[0] + 1)
            if ratio >= 0.3 or (sim >= 0.5 and abs(p[0] - q[0]) <= 12):
                best = max(best, ratio + sim)
        elif sim >= 0.5:
            best = max(best, sim)
    return best


def build_groups(records, today_idx):
    """Put the records that describe the same role into one group, one record per source."""
    groups, by_key, errors = [], {}, []
    for rec in sorted(records, key=lambda r: r["key"] is None):
        if rec["key"]:
            g = by_key.get(rec["key"])
            if g is None:
                g = by_key[rec["key"]] = {"members": {}, "org": rec["org"], "kind": rec["kind"]}
                groups.append(g)
            if rec["source"] in g["members"]:
                errors.append("%s: key %r is used twice in source %s" % (rec["where"], rec["key"], rec["source"]))
            g["members"][rec["source"]] = rec
            continue
        candidates = [(match_score(rec, g, today_idx), i) for i, g in enumerate(groups)
                      if rec["source"] not in g["members"] and kind_family(g["kind"]) == kind_family(rec["kind"])
                      and any(m["org_key"] == rec["org_key"] for m in g["members"].values())]
        score, i = max(candidates or [(0, -1)])
        if score > 0:
            groups[i]["members"][rec["source"]] = rec
        else:
            groups.append({"members": {rec["source"]: rec}, "org": rec["org"], "kind": rec["kind"]})
    if errors:
        raise InputError(errors)
    return groups


def ordered(group, order):
    return [(sid, group["members"][sid]) for sid in order if sid in group["members"]]


def settle_dates(group, order, field):
    vals = [(sid, r[field]) for sid, r in ordered(group, order) if r[field] is not None]
    if not vals:
        return None, None
    sid, best = vals[0]
    if best != ONGOING and best[1] is None:
        for sid2, v in vals[1:]:
            if v != ONGOING and v[1] is not None and v[0] == best[0]:
                return v, sid2
    return best, sid


def settle(group, order):
    """Pick the suggested single source of truth for one role, field by field."""
    titles = {}
    for sid, r in ordered(group, order):
        if r["tokens"]:
            titles.setdefault(r["tokens"], {"title": r["title"], "sources": []})["sources"].append(sid)
    keys = list(titles)
    pairs = [p for i, a in enumerate(keys) for b in keys[i + 1:] for p in [inflation(a, b)] if p]
    chosen, title_from = None, None
    if keys:
        chosen = keys[0]
        conf = group["members"].get(CONFIRMED)
        if conf and conf["tokens"]:
            chosen = conf["tokens"]
        else:
            lower = {}
            for hi, lo, _ in pairs:
                if hi not in lower or seniority(lo) < seniority(lower[hi]):
                    lower[hi] = lo
            seen = set()
            while chosen in lower and chosen not in seen:
                seen.add(chosen)
                chosen = lower[chosen]
        title_from = titles[chosen]["sources"][0]
    start, start_from = settle_dates(group, order, "start")
    end, end_from = settle_dates(group, order, "end")
    first = ordered(group, order)[0][1]
    group.update(titles=titles, pairs=pairs, org=first["org"], kind=first["kind"], confirm=False,
                 concurrent=any(r["concurrent"] for r in group["members"].values()),
                 truth={"title_key": chosen, "title": titles[chosen]["title"] if chosen else None,
                        "title_from": title_from, "start": start, "start_from": start_from,
                        "end": end, "end_from": end_from})


# ---------------------------------------------------------------- checks


def quoted(text):
    return '"%s"' % text


def role_label(g):
    t = g["truth"]
    return "%s at %s" % (quoted(t["title"]), g["org"]) if t["title"] else g["org"]


def dates_label(g):
    t = g["truth"]
    return "%s to %s" % (human(t["start"]), human(t["end"]))


class Audit:
    """Collects findings and fixes for one run."""

    def __init__(self, sources, order, tolerance, gap_limit, today_idx):
        self.sources, self.order = sources, order
        self.tolerance, self.gap_limit, self.today_idx = tolerance, gap_limit, today_idx
        self.findings, self.fixes = [], []

    def label(self, sid):
        return self.sources[sid]["label"] if sid in self.sources else "All sources"

    def labels(self, sids):
        names = [self.label(s) for s in sids]
        return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]

    def published(self, sid):
        return sid != CONFIRMED and self.sources[sid]["editable"]

    def finding(self, kind, severity, roles, sources, summary, **extra):
        f = {"type": kind, "severity": severity, "roles": roles, "sources": sources, "summary": summary}
        f.update({k: v for k, v in extra.items() if v is not None})
        self.findings.append(f)
        return f

    def fix(self, f, sid, action, text, role=None, **extra):
        x = {"finding": f, "source": sid, "action": action, "text": text}
        if role:
            x["role"] = role
        x.update({k: v for k, v in extra.items() if v is not None})
        self.fixes.append(x)

    def change(self, f, sid, g, field, current, suggested, show=quoted):
        if sid == CONFIRMED:
            return
        name = "title" if field == "title" else "claim" if field == "claim" else field + " date"
        if self.sources[sid]["editable"]:
            text = "Change the %s from %s to %s." % (name, show(current), show(suggested))
            action = "change"
        else:
            text = ("%s says %s for the %s and cannot be edited. Use %s everywhere else, and be ready to "
                    "explain the difference." % (self.label(sid), show(current), name, show(suggested)))
            action = "explain"
        self.fix(f, sid, action, text, g["id"], field=field, current=current, suggested=suggested)


def check_titles(a, g):
    if g["kind"] not in TITLE_KINDS or len(g["titles"]) < 2:
        return
    said = "; ".join("%s %s %s" % (a.labels(v["sources"]), "says" if len(v["sources"]) == 1 else "say",
                                   quoted(v["title"])) for v in g["titles"].values())
    reasons = []
    for hi, lo, words in g["pairs"]:
        h, low = g["titles"][hi]["title"], g["titles"][lo]["title"]
        if words:
            reasons.append("%s leaves out %s (from %s)." % (quoted(h), " and ".join(quoted(w.capitalize()) for w in words),
                                                           quoted(low)))
        else:
            reasons.append("%s is a seniority step above %s." % (quoted(h), quoted(low)))
    reason = ("Likely inflation: " + " ".join(reasons)) if reasons else \
        "The titles describe different jobs: check which is right."
    f = a.finding("title_mismatch", "high" if reasons else "medium", [g["id"]], sum((v["sources"] for v in
                  g["titles"].values()), []), "%s: %s." % (g["org"], said), likely_inflation=bool(reasons),
                  reason=reason, field="title", values={s: r["title"] for s, r in ordered(g, a.order) if r["tokens"]},
                  inflated=sorted({g["titles"][hi]["title"] for hi, _, _ in g["pairs"]}) or None)
    g["confirm"] = g["truth"]["title_from"] != CONFIRMED
    for sid, r in ordered(g, a.order):
        if r["tokens"] and r["tokens"] != g["truth"]["title_key"]:
            a.change(f, sid, g, "title", r["title"], g["truth"]["title"])


def check_dates(a, g):
    for field in ("start", "end"):
        vals = [(sid, r[field]) for sid, r in ordered(g, a.order) if r[field] is not None]
        if len(vals) < 2:
            continue
        ongoing = sum(1 for _, v in vals if v == ONGOING)
        months = None
        if ongoing and ongoing < len(vals):
            severity = "high"
        else:
            months = max(date_diff(x, y) for i, (_, x) in enumerate(vals) for _, y in vals[i + 1:])
            if months <= a.tolerance:
                continue
            severity = "high" if months >= 6 else "medium"
        said = "; ".join("%s %s" % (a.label(s), human(v)) for s, v in vals)
        what = "one source says it is current and another says it ended" if months is None else \
            "they differ by up to %d months" % months
        f = a.finding("date_mismatch", severity, [g["id"]], [s for s, _ in vals],
                      "%s, %s: the %s date differs (%s); %s." % (g["org"], g["truth"]["title"] or g["kind"], field,
                                                               said, what),
                      field=field, months=months, values={s: human(v) for s, v in vals})
        g["confirm"] = g["confirm"] or g["truth"][field + "_from"] != CONFIRMED
        truth = g["truth"][field]
        for sid, v in vals:
            if date_diff(v, truth) != 0:
                a.change(f, sid, g, field, human(v), human(truth), show=str)


def covers(a, sid, g):
    lo_c, hi_c = a.sources[sid]["covers"]
    t = g["truth"]
    if not t["start"] or (lo_c is None and hi_c is None):
        return True
    lo, hi = period(t["start"], t["end"], a.today_idx)
    first = month_index(lo_c, "lo") if lo_c and lo_c != ONGOING else -10 ** 6
    last = a.today_idx if hi_c == ONGOING else month_index(hi_c, "hi") if hi_c else 10 ** 6
    return hi >= first and lo <= last


def check_missing(a, g):
    if g["kind"] not in LISTED_KINDS:
        return
    present = [s for s in a.order if s in g["members"]]
    missing = [s for s in a.order if s not in g["members"] and a.sources[s]["complete"] and covers(a, s, g)]
    if not missing:
        return
    trusted = lambda s: not a.published(s)  # noqa: E731
    high = not any(trusted(s) for s in present) and any(trusted(s) for s in missing)
    summary = "%s (%s) is in %s but not in %s." % (role_label(g), dates_label(g), a.labels(present), a.labels(missing))
    if high:
        summary += " Only the person's own pages list it."
    f = a.finding("missing_role", "high" if high else "medium", [g["id"]], present + missing, summary,
                  present_in=present, missing_from=missing)
    t = g["truth"]
    g["confirm"] = g["confirm"] or any(t[k] not in (None, CONFIRMED) for k in ("title_from", "start_from", "end_from"))
    if high:
        for sid in present:
            a.fix(f, sid, "remove_or_prove", "Remove %s unless the person confirms it and a document backs it."
                  % role_label(g), g["id"])
    for sid in missing:
        if sid == CONFIRMED:
            a.fix(f, sid, "confirm", "Ask the person whether they held %s (%s), and record the answer."
                  % (role_label(g), dates_label(g)), g["id"])
        elif high:
            continue  # do not spread a role nobody trusted lists
        elif not a.sources[sid]["editable"]:
            a.fix(f, sid, "explain", "%s does not list %s and cannot be edited. Be ready to explain why."
                  % (a.label(sid), role_label(g)), g["id"])
        else:
            a.fix(f, sid, "add", "Add %s, %s, or be ready to say why it is left out." % (role_label(g), dates_label(g)),
                  g["id"])


def check_claims(a, g):
    entries = [{"sid": sid, "text": t, "tokens": claim_tokens(t), "nums": numbers(t)}
               for sid, r in ordered(g, a.order) for t in r["claims"]]
    denials = [claim_tokens(t) for _, r in ordered(g, a.order) for t in r["denies"]]
    clusters = []
    for e in entries:
        if a.published(e["sid"]) and any(similar(e["tokens"], d) for d in denials):
            f = a.finding("denied_claim", "high", [g["id"]], [e["sid"]], "%s, %s: %s says %s, but the person says "
                          "this is not true." % (g["org"], g["truth"]["title"], a.label(e["sid"]), quoted(e["text"])),
                          claim=e["text"])
            a.fix(f, e["sid"], "remove", "Remove %s: the person says it is not true." % quoted(e["text"]), g["id"],
                  field="claim", current=e["text"])
            continue
        home = next((c for c in clusters if any(similar(e["tokens"], o["tokens"]) for o in c)), None)
        (home.append(e) if home is not None else clusters.append([e]))
    for c in clusters:
        sids = list(dict.fromkeys(e["sid"] for e in c))
        if len(sids) == 1:
            if a.published(sids[0]):
                f = a.finding("single_source_claim", "medium", [g["id"]], sids, "%s, %s: only %s says %s."
                              % (g["org"], g["truth"]["title"], a.label(sids[0]), quoted(c[0]["text"])),
                              claim=c[0]["text"], has_number=bool(c[0]["nums"]))
                a.fix(f, sids[0], "prove_or_remove", "Keep %s only if a second source backs it (a referee, a document, "
                      "a press article); otherwise remove or soften it." % quoted(c[0]["text"]), g["id"],
                      field="claim", current=c[0]["text"])
            continue
        if len({tuple(e["nums"]) for e in c}) > 1:
            best = c[0]
            f = a.finding("claim_mismatch", "medium", [g["id"]], sids, "%s, %s: the same claim has different numbers "
                          "(%s)." % (g["org"], g["truth"]["title"], "; ".join("%s %s" % (a.label(e["sid"]),
                                                                                         quoted(e["text"])) for e in c)),
                          claim=best["text"], values={e["sid"]: e["text"] for e in c})
            for e in c[1:]:
                if e["nums"] != best["nums"] and a.published(e["sid"]):
                    a.change(f, e["sid"], g, "claim", e["text"], best["text"])


def check_overlaps(a, groups):
    work = [g for g in groups if g["kind"] in LISTED_KINDS and g["truth"]["start"] and g["truth"]["end"]]
    for i, x in enumerate(work):
        for y in work[i + 1:]:
            if x["concurrent"] or y["concurrent"]:
                continue
            px = period(x["truth"]["start"], x["truth"]["end"], a.today_idx, generous=False)
            py = period(y["truth"]["start"], y["truth"]["end"], a.today_idx, generous=False)
            lo, hi = max(px[0], py[0]), min(px[1], py[1])
            months = hi - lo + 1
            if months <= a.tolerance:
                continue
            f = a.finding("overlap", "low" if months <= 3 else "medium", [x["id"], y["id"]], [],
                          "%s and %s overlap for %d months (%s to %s), and neither is marked concurrent."
                          % (role_label(x), role_label(y), months, human_index(lo), human_index(hi)), months=months)
            a.fix(f, "all", "mark_concurrent", "If %s and %s really ran at the same time, mark them concurrent in "
                  "profile/role-records.json and make that clear on the CV; otherwise fix the dates."
                  % (x["id"], y["id"]), x["id"])


def check_gaps(a, groups, explained):
    dated = [g for g in groups if g["truth"]["start"]]
    listed = [g for g in dated if g["kind"] in LISTED_KINDS]
    if not listed:
        return
    spans = {g["id"]: period(g["truth"]["start"], g["truth"]["end"], a.today_idx) for g in dated}
    begin = min(spans[g["id"]][0] for g in listed)
    ivs = sorted((max(lo, begin), hi) for lo, hi in list(spans.values()) + list(explained) if hi >= begin)
    gaps, cur = [], None
    for lo, hi in ivs:
        if cur is not None and lo - cur - 1 > a.gap_limit:
            gaps.append((cur + 1, lo - 1, False))
        cur = hi if cur is None else max(cur, hi)
    if a.today_idx - cur > a.gap_limit:
        gaps.append((cur + 1, a.today_idx, True))
    for lo, hi, now in gaps:
        months = hi - lo + 1
        near = [rid for rid, (s, e) in sorted(spans.items()) if e == lo - 1 or s == hi + 1]
        if now:
            summary = "Nothing recorded since %s (%d months to %s)." % (human_index(lo), months, human_index(hi))
            text = ("Say what the person is doing now (for example study, a business, a career break or looking for "
                    "work) in one line on the CV and LinkedIn, then add it to explained_gaps.")
        else:
            summary = "No role, study or explained break from %s to %s (%d months)." % (human_index(lo),
                                                                                       human_index(hi), months)
            text = ("Explain %s to %s in one line on the CV and LinkedIn (for example study, a business, travel or a "
                    "career break), then add it to explained_gaps." % (human_index(lo), human_index(hi)))
        f = a.finding("gap", "low" if months <= 6 else "medium", near, [], summary, months=months,
                      gap={"start": "%04d-%02d" % (lo // 12, lo % 12 + 1), "end": "%04d-%02d" % (hi // 12, hi % 12 + 1),
                           "current": now})
        a.fix(f, "all", "explain", text, near[0] if near else None)


# ---------------------------------------------------------------- report


def role_out(g, order):
    t = g["truth"]
    truth = {"title": t["title"], "title_from": t["title_from"], "start": iso(t["start"]),
             "start_from": t["start_from"], "end": iso(t["end"]), "end_from": t["end_from"],
             "needs_confirmation": g["confirm"]}
    seen = {}
    for sid, r in ordered(g, order):
        seen[sid] = {k: v for k, v in (("title", r["title"] or None), ("start", iso(r["start"])),
                                       ("end", iso(r["end"]))) if v}
    return {"id": g["id"], "organisation": g["org"], "kind": g["kind"], "concurrent": g["concurrent"],
            "truth": {k: v for k, v in truth.items() if v is not None}, "seen_in": seen}


def run_audit(doc, tolerance=1, gap_limit=3, today=None, input_label="profile/role-records.json",
              evidence_ids=None):
    """Compare the sources in a role-records document and return the report (a dict)."""
    today = today or dt.date.today()
    today_idx = today.year * 12 + today.month - 1
    sources, order, records, explained = read_input(doc, today_idx)
    groups = build_groups(records, today_idx)
    for g in groups:
        settle(g, order)
    groups.sort(key=lambda g: (g["truth"]["start"] is None,
                               period(g["truth"]["start"], g["truth"]["end"], today_idx) if g["truth"]["start"] else 0,
                               g["org"].lower(), g["truth"]["title"] or ""))
    for i, g in enumerate(groups, 1):
        g["id"] = "R%02d" % i
    a = Audit(sources, order, tolerance, gap_limit, today_idx)
    for g in groups:
        check_titles(a, g)
        check_dates(a, g)
        check_missing(a, g)
        check_claims(a, g)
    check_overlaps(a, groups)
    check_gaps(a, groups, explained)
    a.findings.sort(key=lambda f: (SEVERITIES.index(f["severity"]), (f["roles"] or ["R999"])[0], TYPES.index(f["type"])))
    for i, f in enumerate(a.findings, 1):
        rest = dict(f)
        f.clear()
        f.update(id="F%02d" % i, **rest)
    place = {s: i for i, s in enumerate(order + ["all"])}
    fixes = sorted(a.fixes, key=lambda x: (place[x["source"]], x["finding"]["id"]))
    for x in fixes:
        x["finding"] = x["finding"]["id"]
    notes = ["%s has no end date in any source, so the gap check counts it as one month." % g["id"]
             for g in groups if g["truth"]["start"] and g["truth"]["end"] is None]
    notes += ["%s has no start date in any source, so it is left out of the gap and overlap checks." % g["id"]
              for g in groups if not g["truth"]["start"]]
    if evidence_ids is not None:
        for r in records:
            notes += ["%s cites %s, which is not in profile/evidence.json." % (r["where"], e)
                      for e in r["evidence"] if e not in evidence_ids]
    by_type = {t: sum(1 for f in a.findings if f["type"] == t) for t in TYPES}
    src_out = []
    for sid in order:
        s = dict(sources[sid])
        lo_c, hi_c = s.pop("covers")
        if lo_c or hi_c:
            s["covers"] = {k: v for k, v in (("from", iso(lo_c)), ("to", iso(hi_c))) if v}
        src_out.append(s)
    return {"schema_version": 1, "generated_on": today.isoformat(), "input": input_label,
            "settings": {"date_tolerance_months": tolerance, "gap_months": gap_limit, "truth_order": order},
            "sources": src_out,
            "counts": dict({s: sum(1 for f in a.findings if f["severity"] == s) for s in SEVERITIES},
                           by_type={t: n for t, n in by_type.items() if n}),
            "roles": [role_out(g, order) for g in groups], "findings": a.findings, "fixes": fixes, "notes": notes}


TYPE_NAMES = {"title_mismatch": "Title differs", "date_mismatch": "Dates differ", "missing_role": "Role missing",
              "gap": "Unexplained gap", "overlap": "Roles overlap", "single_source_claim": "Claim in one place only",
              "claim_mismatch": "Claim differs", "denied_claim": "Claim the person denies"}


def _human_iso(value):
    return human(parse_month(value)) if value else "not given"


def to_markdown(report):
    """The short summary for the person: truth table, findings and the exact fixes per source."""
    labels = {s["id"]: s["label"] for s in report["sources"]}
    c = report["counts"]
    day = dt.date.fromisoformat(report["generated_on"])
    out = ["# Consistency audit", "",
           "Generated on %d %s %d from `%s`. Compared: %s." % (
               day.day, MONTH_NAMES[day.month - 1], day.year, report["input"],
               ", ".join("%s (%d records)" % (s["label"], s["records"]) for s in report["sources"])), ""]
    total = c["high"] + c["medium"] + c["low"]
    if c["high"]:
        advice = ("Fix the high ones first: a raised title, a role nobody else lists or a claim the person denies "
                  "reads as dishonesty to a recruiter or a background check.")
    elif total:
        advice = "Nothing high. Fix the rest before the next application."
    else:
        advice = "Every source agrees. Run the audit again whenever a source changes."
    out += ["**%d high, %d medium, %d low.** %s" % (c["high"], c["medium"], c["low"], advice), "",
            "## Suggested single source of truth", "",
            "Use these values everywhere. Each one comes from the most trusted source that has it (%s). Where titles "
            "disagree and the person has not confirmed one, the more modest title is suggested. Check every line "
            "marked **confirm** with the person, against a document if possible." %
            ", then ".join(labels[s] for s in report["settings"]["truth_order"]), "",
            "| Role | Organisation | Title | Start | End | Taken from | |", "|---|---|---|---|---|---|---|"]
    for r in report["roles"]:
        t = r["truth"]
        froms = [t.get("title_from"), t.get("start_from"), t.get("end_from")]
        if len(set(f for f in froms if f)) <= 1:
            taken = labels.get(next((f for f in froms if f), ""), "")
        else:
            taken = "; ".join("%s: %s" % (k, labels[f]) for k, f in zip(("title", "start", "end"), froms) if f)
        out.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            r["id"], r["organisation"], t.get("title", ""), _human_iso(t.get("start")), _human_iso(t.get("end")),
            taken, "**confirm**" if t.get("needs_confirmation") else ""))
    out += ["", "## Findings", ""]
    if not report["findings"]:
        out += ["None.", ""]
    for sev in SEVERITIES:
        items = [f for f in report["findings"] if f["severity"] == sev]
        if not items:
            continue
        out += ["### %s" % sev.capitalize(), ""]
        for f in items:
            name = "Likely title inflation" if f.get("likely_inflation") else TYPE_NAMES[f["type"]]
            extra = " " + f["reason"] if f.get("reason") else ""
            out.append("- **%s %s%s.** %s%s" % (f["id"], name, (", " + " and ".join(f["roles"])) if f["roles"] else "",
                                                 f["summary"], extra))
        out.append("")
    out += ["## Fixes by source", ""]
    if not report["fixes"]:
        out += ["Nothing to change.", ""]
    orgs = {r["id"]: r["organisation"] for r in report["roles"]}
    editable = {s["id"]: s["editable"] for s in report["sources"]}
    for sid in report["settings"]["truth_order"] + ["all"]:
        items = [x for x in report["fixes"] if x["source"] == sid]
        if not items:
            continue
        head = "All sources" if sid == "all" else labels[sid]
        if sid == CONFIRMED:
            head += " (questions to ask)"
        elif sid != "all" and not editable[sid]:
            head += " (cannot be edited)"
        out += ["### %s" % head, ""]
        for i, x in enumerate(items, 1):
            where = "%s %s: " % (x["role"], orgs[x["role"]]) if x.get("role") else ""
            out.append("%d. %s%s (%s)" % (i, where, x["text"], x["finding"]))
        out.append("")
    out += ["## Next steps", "",
            "- Draft the edits with `method/PROFILE_FIXES.md`. Nothing here changes any account; the person makes "
            "every change, or asks their agent to.",
            "- Every high finding becomes a top priority plan action.",
            "- After a source changes, copy it again into `profile/role-records.json` and re-run the audit. Before "
            "publishing, run it with `--tolerance-months 0` so every date matches exactly.", ""]
    if report["notes"]:
        out += ["## Notes", ""] + ["- " + n for n in report["notes"]] + [""]
    return "\n".join(out)


# ------------------------------------------------------------------ main


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check that a work history agrees across the CV, LinkedIn, the "
                                             "website and official forms.")
    ap.add_argument("--workspace", help="workspace folder (default: $LVLME_HOME)")
    ap.add_argument("--input", help="role records file (default: profile/role-records.json in the workspace). "
                                    "Without --workspace the report is printed and nothing is written.")
    ap.add_argument("--json", action="store_true", help="with --input only: print the JSON report, not Markdown")
    ap.add_argument("--tolerance-months", type=int, default=1, help="date differences up to this are ignored (1)")
    ap.add_argument("--gap-months", type=int, default=3, help="report gaps longer than this (3)")
    ap.add_argument("--today", help="date to measure current roles and gaps against (default: today)")
    args = ap.parse_args(argv)
    if args.tolerance_months < 0 or args.gap_months < 0:
        ap.error("--tolerance-months and --gap-months cannot be negative")
    standalone = bool(args.input) and not args.workspace
    ws, config, evidence_ids = None, {}, None
    if not standalone:
        ws, config = C.open_workspace(args.workspace)
    today = dt.date.fromisoformat(C.check_date(args.today)) if args.today else \
        dt.date.fromisoformat(C.today_in(config)) if ws else dt.date.today()
    path = args.input or C.wpath(ws, "profile", "role-records.json")
    if ws and not os.path.exists(path) and os.path.exists(C.wpath(ws, path)):
        path = C.wpath(ws, path)
    if not os.path.exists(path):
        print("lvlme: no role records at %s. Copy each source into it first (see method/CONSISTENCY.md)." % path,
              file=sys.stderr)
        return 1
    label = os.path.relpath(path, ws) if ws and C._is_within(path, ws) else os.path.basename(path)
    if ws:
        ev = C.load_json(C.wpath(ws, "profile", "evidence.json"), {}) or {}
        evidence_ids = {e.get("id") for e in ev.get("items", [])}
    try:
        doc = C.load_json(path)
        report = run_audit(doc, args.tolerance_months, args.gap_months, today, label, evidence_ids)
    except C.FileProblem as exc:
        print("lvlme: %s" % exc, file=sys.stderr)
        return 1
    except ValueError as exc:
        print("lvlme: %s: %s" % (label, exc), file=sys.stderr)
        return 1
    except InputError as exc:
        for msg in exc.args[0]:
            print("lvlme: %s: %s" % (label, msg), file=sys.stderr)
        return 1
    if standalone:
        print(C.dump_json(report) if args.json else to_markdown(report), end="")
        return 0
    C.write_json(C.wpath(ws, "profile", "consistency.json"), report)
    C.write_text(C.wpath(ws, "profile", "consistency.md"), to_markdown(report))
    print(json.dumps({"wrote": ["profile/consistency.json", "profile/consistency.md"], "roles": len(report["roles"]),
                      "findings": {s: report["counts"][s] for s in SEVERITIES}, "fixes": len(report["fixes"])},
                     indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(C.run_main(main))
