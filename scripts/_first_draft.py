"""The first-draft rule, checked in code: drafts for an employer that asks for the person's own first draft.

Where a target's `ai_policy.first_draft_by_person` is true (config.json),
LVLme never writes its application answers, cover letters or résumé text
(method/CAMPAIGN.md, "When an organisation asks for your own first draft").
This module makes that a check rather than something the agent must remember.

Every draft in campaign/drafts/ whose path names such a target (its id or
name) must say what it is in its first lines:

    LVLme brief. Policy: https://www.anthropic.com/candidate-ai-guidance, checked 2026-11-02.

The kinds allowed are the help the policy permits: `brief` (what the role
asks for, the evidence and the gaps, for the person to write from), `review`
(comments on the person's own draft), `prep` (research, interview practice,
questions to ask) and `outreach` (a message to a person, not part of an
application). A draft with no such line, or with another kind, is an error.
A policy checked more than 30 days ago is a warning: re-read the employer's
page before the next application.
"""
import datetime as dt
import os
import re

import _common as C

KINDS = ("brief", "review", "prep", "outreach")
READABLE = (".md", ".txt", ".html")
STALE_DAYS = 30
HEAD_LINES = 10
HEADER = re.compile(r"\bLVLme (\w+)\b[^\n]*?\bPolicy: (\S+?),? checked (\d{4}-\d{2}-\d{2})", re.I)
PLAIN = "%s asks for your own first draft. Write it, then I'll review it."


def first_draft_targets(cfg):
    """{target id: (name, policy)} for each target whose policy says the person writes the first draft."""
    return {t["id"]: (t.get("name", t["id"]), t["ai_policy"]) for t in (cfg or {}).get("targets", [])
            if (t.get("ai_policy") or {}).get("first_draft_by_person") is True}


def _tokens(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def target_of(rel, targets):
    """The first-draft target a draft's path names, or None."""
    words = _tokens(rel)
    for tid, (name, _) in targets.items():
        if _tokens(tid) <= words or (_tokens(name) and _tokens(name) <= words):
            return tid
    return None


def header_of(path):
    """(kind, source, checked date) from the first lines of a draft, or None."""
    with open(path, encoding="utf-8", errors="replace") as f:
        head = "".join(f.readline() for _ in range(HEAD_LINES))
    m = HEADER.search(head)
    return (m.group(1).lower(), m.group(2), m.group(3)) if m else None


def drafts(ws):
    root = C.wpath(ws, "campaign", "drafts")
    for folder, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not d.startswith((".", "_")))
        for name in sorted(files):
            if not name.startswith("."):
                yield os.path.relpath(os.path.join(folder, name), ws)


def checks(ws, cfg, errors, warnings, today=None):
    """Add an error for each draft for a first-draft employer that is not a brief, review, prep or outreach."""
    targets = first_draft_targets(cfg)
    if not targets:
        return
    today = today or C.today_in(cfg)
    unread = []
    for rel in drafts(ws):
        tid = target_of(rel, targets)
        if not tid:
            continue
        name, policy = targets[tid]
        if not rel.lower().endswith(READABLE):
            unread.append(rel)
            continue
        found = header_of(C.wpath(ws, rel))
        if not found or found[0] not in KINDS:
            what = "says it is a %r" % found[0] if found else "does not say what it is"
            errors.append("%s: %s. %s So LVLme writes only a brief, a review of your own draft, preparation "
                          "or outreach, and each starts with a line such as 'LVLme brief. Policy: %s, checked "
                          "%s.' (method/CAMPAIGN.md)" % (rel, what, PLAIN % name, policy.get("source"),
                                                         policy.get("checked_on") or today))
            continue
        _, source, checked = found
        if source.rstrip("/") != (policy.get("source") or "").rstrip("/"):
            warnings.append("%s: names the policy %s, but config.json records %s for %s"
                            % (rel, source, policy.get("source"), name))
        if _days(checked, today) > STALE_DAYS:
            warnings.append("%s: %s's AI policy was last checked on %s, more than %d days ago. Re-read %s "
                            "before the next application." % (rel, name, checked, STALE_DAYS, policy.get("source")))
    if unread:
        warnings.append("campaign/drafts: %d file(s) for an employer that asks for your own first draft could "
                        "not be read (%s). Make sure you wrote them yourself." % (len(unread), ", ".join(unread)))


def _days(earlier, later):
    try:
        return (dt.date.fromisoformat(later) - dt.date.fromisoformat(earlier)).days
    except ValueError:
        return STALE_DAYS + 1
