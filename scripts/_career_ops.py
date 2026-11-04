"""Read a career-ops folder (github.com/career-ops-hq/career-ops, MIT): its tracker, status log, contacts and stories.

Read only: nothing here writes into a career-ops folder. The formats follow its
DATA_CONTRACT.md (version 1.38.0, read 4 November 2026):

  data/applications.md       a pipe table: #, Date, Company, [Via,] Role, Score, Status, PDF, Report, Notes
                             (columns found by header name; older tab-separated rows still read)
  data/status-log.tsv        tracker#, date, from, to, source, note (append-only)
  data/contacts.tsv          name, company, type, title, phone, email, linkedin, tracker#, notes
  interview-prep/story-bank.md   "### [Theme] Title" blocks with **S (Situation):** and the rest

career-ops' statuses map one to one onto LVLme's stages (the same ten names),
including its aliases. Its tracker number and report number differ: the
tracker number (#) is the one kept. Only a contact's name, company, type and
title are read; phone, email and LinkedIn address are never copied. No network
calls here.
"""
import csv
import os
import re

STATES = {  # career-ops templates/states.yml: id -> aliases (case-insensitive)
    "evaluated": ["evaluated", "evaluada", "condicional", "hold", "evaluar", "verificar"],
    "applied": ["applied", "aplicado", "enviada", "aplicada", "sent"],
    "responded": ["responded", "respondido"],
    "assessment": ["assessment", "screening", "online assessment", "online_assessment", "online screening"],
    "interview": ["interview", "entrevista"],
    "offer": ["offer", "oferta"],
    "rejected": ["rejected", "rechazado", "rechazada"],
    "discarded": ["discarded", "descartado", "descartada", "cerrada", "cancelada"],
    "skip": ["skip", "no_aplicar", "no aplicar", "monitor", "geo blocker", "geo_blocker"],
    "hired": ["hired", "contratado", "contratada", "accepted", "accept"],
}
ALIAS = {a: s for s, names in STATES.items() for a in names}
HEADERS = {"#": "num", "date": "date", "company": "company", "via": "via", "role": "role", "score": "score",
           "status": "status", "pdf": "pdf", "report": "report", "notes": "notes", "url": "url"}
FIELDS = {"S (Situation)": "situation", "T (Task)": "task", "A (Action)": "action", "R (Result)": "result",
          "Reflection": "reflection", "Best for questions about": "best_for", "Source": "source"}
# career-ops' free-text story themes, matched to LVLme's story themes by keyword.
THEME_WORDS = [("lead", r"lead|influenc|stakeholder|team|mentor|ownership"),
               ("disagree", r"conflict|disagree|push ?back|negotiat"),
               ("mistake", r"fail|mistake|learn|setback|error"),
               ("impact", r"impact|result|metric|revenue|cost|growth|scale|deliver"),
               ("hard_problem", r"problem|technical|ambigu|complex|debug|architect"),
               ("values", r"ethic|value|integrity|safety|right thing"),
               ("why_here", r"motivat|why |mission|passion")]


def split_row(line):
    """The trimmed cells of one tracker line, first real column first (career-ops' own rule: a line is
    tab-separated only when it holds a tab and at most two pipes; a tab inside a pipe table is text)."""
    closing = line.rstrip().endswith("|")
    if "\t" in line and line.count("|") <= 2:
        start = line.find("|")
        body = line[start + 1:] if start >= 0 else line
        if closing and start >= 0 and line.rstrip().rfind("|") > start:
            body = body[:body.rstrip().rfind("|")]
        return [c.strip() for c in body.split("\t")]
    parts = line.split("|")[1:]
    if closing:
        parts = parts[:-1]
    return [c.strip() for c in parts]


def stage_of(status):
    s = re.sub(r"[*_`]", "", status or "").strip().lower()
    return ALIAS.get(s)


def read_tracker(text):
    """[{num, date, company, role, status, stage, score, notes, via, url}] from applications.md."""
    cols, rows = None, []
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = split_row(line)
        names = [c.lower() for c in cells]
        if cols is None:
            if {"#", "company", "role", "status"} <= set(names):
                cols = {HEADERS[n]: i for i, n in enumerate(names) if n in HEADERS}
            continue
        if all(re.fullmatch(r":?-+:?", c or "-") for c in cells):
            continue
        get = lambda k: cells[cols[k]] if k in cols and cols[k] < len(cells) else ""   # noqa: E731
        if not get("num").isdigit():
            continue
        rows.append({"num": int(get("num")), "date": get("date"), "company": get("company"), "role": get("role"),
                     "status": get("status"), "stage": stage_of(get("status")), "score": get("score"),
                     "notes": "" if get("notes") in ("—", "-") else get("notes"), "via": get("via"),
                     "url": (re.search(r"https://[^)\s]+", get("url")) or [""])[0]})
    return rows


def read_status_log(text):
    """{tracker#: [(date, from stage or None, to stage or None, source)]}, oldest first."""
    out = {}
    for line in text.splitlines():
        cells = line.split("\t")
        if len(cells) < 4 or not cells[0].strip().isdigit():
            continue
        num, date = int(cells[0]), cells[1].strip()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            continue
        out.setdefault(num, []).append((date, stage_of(cells[2]), stage_of(cells[3]),
                                        cells[4].strip() if len(cells) > 4 else ""))
    for events in out.values():
        events.sort(key=lambda e: e[0])
    return out


def read_contacts(text):
    """[{name, company, type, title, tracker}]: never phone, email or LinkedIn."""
    out = []
    for cells in csv.reader(text.splitlines(), delimiter="\t"):
        if len(cells) < 2 or not cells[0].strip() or cells[0].strip().lower() == "name":
            continue
        cells += [""] * 9
        out.append({"name": cells[0].strip(), "company": cells[1].strip(), "type": cells[2].strip(),
                    "title": cells[3].strip(), "tracker": cells[7].strip() if cells[7].strip() != "-" else ""})
    return out


def read_stories(text):
    """[{theme, title, situation, task, action, result, reflection, best_for, source}] from story-bank.md.
    A block without an action is skipped, as career-ops' own readers skip it."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"(?ms)^ {0,3}(`{3,}|~{3,}).*?^ {0,3}\1[ \t]*$", "", text)
    out, cur = [], None
    for line in text.splitlines():
        m = re.match(r"^### (.*)$", line)
        if m or re.match(r"^#{1,2}\s", line):
            if cur and cur.get("action"):
                out.append(cur)
            cur = None
            if m:
                head = m.group(1).strip()
                t = re.match(r"^\[([^\]]*)\]\s*(.*)$", head)
                cur = {"theme": t.group(1).strip() if t else "", "title": (t.group(2) if t else head).strip()}
            continue
        f = re.match(r"^\*\*([^*]+):\*\*\s*(.*)$", line.strip())
        if cur is not None and f and f.group(1).strip() in FIELDS:
            cur[FIELDS[f.group(1).strip()]] = f.group(2).strip()
    if cur and cur.get("action"):
        out.append(cur)
    return out


def themes_for(story, known):
    text = " ".join([story.get("theme", ""), story.get("best_for", ""), story.get("title", "")]).lower()
    found = [t for t, rx in THEME_WORDS if t in known and re.search(rx, text)]
    return found[:3]


def read_folder(path):
    """Everything LVLme reads from a career-ops folder, and which files were found."""
    def text(*parts):
        p = os.path.join(path, *parts)
        if not os.path.isfile(p):
            return None
        with open(p, encoding="utf-8") as fh:
            return fh.read()
    tracker = text("data", "applications.md") or text("applications.md")
    if tracker is None:
        raise SystemExit("lvlme: no career-ops tracker at %s (looked for data/applications.md)." % path)
    log, contacts, stories = text("data", "status-log.tsv"), text("data", "contacts.tsv"), \
        text("interview-prep", "story-bank.md")
    return {"applications": read_tracker(tracker), "log": read_status_log(log or ""),
            "contacts": read_contacts(contacts or ""), "stories": read_stories(stories or ""),
            "found": {"status-log": log is not None, "contacts": contacts is not None, "stories": stories is not None}}
