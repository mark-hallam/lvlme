"""Autopilot: a check-in that runs itself, and the "This week" note it leaves for the person.

Autopilot for the thinking, never for the doing. A scheduled run fetches roles,
checks postings, judges what changed, scores, rebuilds the dashboard and
writes campaign/weekly/<date>.json (and .md when the agent has not written
one): what changed, the level, new and closed roles, follow-ups due, one
event worth going to, and exactly one thing to do this week, the top of Do
next. It never sends, applies, posts or contacts anyone, and a run with
nobody present asks nothing: questions wait in the note.

The settings are the person's answers in config.json "autopilot"
(schemas/config.schema.json), recorded by scripts/autopilot.py on their yes.
No network calls here.
"""
import datetime as dt
import glob
import json
import os

import _common as C
import _applications as AP

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_NAMES = dict(zip(DAYS, ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]))
DEFAULTS = {"rhythm": "weekly", "day": "mon", "time": "07:00", "run": "light", "sources": [], "helpers": True}
WEEKLY_DIR = ("campaign", "weekly")


def settings(config):
    return dict(DEFAULTS, **((config or {}).get("autopilot") or {}))


def next_run(ap, today):
    """The date of the next scheduled run on or after today (ISO), or None when Autopilot is off."""
    if not ap.get("enabled"):
        return None
    d = dt.date.fromisoformat(today)
    if ap["rhythm"] == "daily":
        return d.isoformat()
    return (d + dt.timedelta(days=(DAYS.index(ap["day"]) - d.weekday()) % 7)).isoformat()


def when_text(ap):
    return ("Every day at %s" % ap["time"]) if ap["rhythm"] == "daily" else ("%ss at %s" % (DAY_NAMES[ap["day"]], ap["time"]))


# ------------------------------------------------------------ the schedule


def task_prompt(engine, ws, ap):
    """The prompt a scheduled task runs. Generic: every fact about the person comes from their workspace."""
    sources = ", ".join(ap["sources"]) if ap["sources"] else "none beyond the workspace files"
    return "\n".join([
        "You are running LVLme on autopilot for the person who owns this workspace. Nobody is present.",
        "",
        "Engine (read only, never edit it): %s" % engine,
        "Workspace (all of the person's data): %s" % ws,
        "Run every engine script from the engine folder with --workspace %s." % ws,
        "",
        "Read %s/SKILL.md, %s/method/RUNBOOK.md and \"Runs with nobody present\" in %s/docs/ORCHESTRATION.md, "
        "and follow them exactly: ask nothing, approve nothing new, take no step that needs the person's yes."
        % (engine, engine, engine),
        "",
        "This run, in order:",
        "1. Process campaign/inbox.md and actions marked done in campaign/plan.json.",
        "2. python3 scripts/fetch_roles.py (it also checks each posting's age and reposts).",
        "3. Evidence since the last run, from these approved read-only sources only: %s." % sources,
        "4. python3 scripts/run_plan.py, then judge the roles of a %s run (--json lists them)." % ap["run"],
        ("5. The blind review gate, with fresh helper agents, as method/REVIEW.md says."
         if ap["helpers"] else
         "5. Start no helper agents: leave new scores above 2 waiting for review (they count as 2) and say so."),
        "6. python3 scripts/score.py, then python3 scripts/build_dashboard.py, then python3 scripts/validate.py (it must exit 0).",
        "7. python3 scripts/autopilot.py week (writes this week's note and rebuilds the dashboard's This week card).",
        "",
        "Never apply for a job, send any email or message, post anything, accept anything, or change an account. "
        "Drafts go in campaign/drafts/ for the person to send. Evidence or it scores zero; never invent anything.",
        "If a step fails (a job board is down, a source is unavailable), skip it, say so, and carry on.",
        "",
        "Finish with a short plain-English message: what changed, the one thing to do this week, any question only "
        "the person can answer, and the command to open the dashboard: open %s" % os.path.join(ws, "report", "index.html"),
    ]) + "\n"


def cron_line(engine, ws, ap, prompt_path, log_path):
    """A crontab line that runs Claude Code on the schedule (for a computer without the desktop app)."""
    hh, mm = ap["time"].split(":")
    days = "*" if ap["rhythm"] == "daily" else str((DAYS.index(ap["day"]) + 1) % 7)
    return ('%d %d * * %s cd "%s" && claude -p "$(cat \'%s\')" --permission-mode acceptEdits '
            '--allowedTools "Bash(python3 scripts/*)" Read Write Edit Glob Grep >> "%s" 2>&1'
            % (int(mm), int(hh), days, engine, prompt_path, log_path))


# ------------------------------------------------------------ the weekly note


def _load(ws, *parts):
    return C.load_json(C.wpath(ws, *parts), None)


def previous_note(ws, today):
    notes = sorted(f for f in glob.glob(os.path.join(C.wpath(ws, *WEEKLY_DIR), "*.json"))
                   if os.path.basename(f)[:10] < today)
    return C.load_json(notes[-1], {}) if notes else None


def newest_note(ws):
    notes = sorted(glob.glob(os.path.join(C.wpath(ws, *WEEKLY_DIR), "*.json")))
    return C.load_json(notes[-1], None) if notes else None


def best_event(orgs_doc, targets, names):
    """The most recently seen sourced event at a target organisation, or None."""
    found = []
    for oid, org in ((orgs_doc or {}).get("orgs") or {}).items():
        for f in (org or {}).get("facts") or []:
            if f.get("kind") == "event" and f.get("source") and (not targets or oid in targets):
                found.append((f.get("seen_on") or "", names.get(oid, oid), f))
    if not found:
        return None
    seen, org, f = max(found, key=lambda x: x[0])
    return {"org": org, "text": f.get("text", ""), "source": f["source"], "seen_on": seen}


def week_note(ws, config, today):
    """This week's note, from the dashboard's agent file and the workspace (report/for-agents/dashboard.json first)."""
    dash = _load(ws, "report", "for-agents", "dashboard.json") or {}
    roles_doc = _load(ws, "market", "roles", "latest.json") or {}
    summary = roles_doc.get("summary") or {}
    names = C.target_names(config)
    best = (dash.get("levels") or {}).get("best_role") or {}
    prev = previous_note(ws, today)
    since = (prev or {}).get("date")
    days = [d for d in (dash.get("levels") or {}).get("progress_days") or [] if not since or d.get("date", "") > since]
    changed = []
    if prev and best and prev.get("fit") is not None:
        delta = round(best["fit"] - prev["fit"], 1)
        changed.append("Best fit %s, from %s to %s." % ("up %s" % num(delta) if delta > 0 else "down %s" % num(-delta)
                                                      if delta < 0 else "unchanged", num(prev["fit"]), num(best["fit"])))
    done = sorted({a for d in days for a in d.get("actions") or []})
    evidence = sorted({e for d in days for e in d.get("evidence") or []})
    if done:
        titles = {a.get("id"): a.get("title", a.get("id")) for a in dash.get("actions_done") or []}
        changed.append("%d plan action%s done: %s." % (len(done), "" if len(done) == 1 else "s",
                                                      "; ".join(titles.get(a, a).rstrip(".") for a in done)))
    if evidence:
        changed.append("%d new piece%s of evidence counted." % (len(evidence), "" if len(evidence) == 1 else "s"))
    if not changed:
        changed.append("Nothing moved since %s." % since if since else "This is the first note: next week's says what moved.")
    apps = AP.due_now(_load(ws, *AP.REL.split("/")), today)
    top = (dash.get("actions_active") or [None])[0]
    runs = sorted(glob.glob(os.path.join(C.wpath(ws, "eval", "runs"), "*.json")))
    run = C.load_json(runs[-1], {}) if runs else {}
    awaiting = sum(1 for r in (run or {}).get("roles") or [] if r.get("awaiting_review"))
    return {
        "schema_version": 1, "date": today, "since": since,
        "fit": best.get("fit"), "level": best.get("level"), "band": best.get("band"),
        "role": best.get("title"), "org": names.get(best.get("org"), best.get("org")),
        "points_to_next": best.get("points_to_next"), "next_band": best.get("next_band"),
        "changed": changed,
        "roles": {"new": len(summary.get("new_role_ids") or []), "closed": len(summary.get("closed_role_ids") or []),
                  "suspicious": (summary.get("posting_checks") or {}).get("suspicious", 0),
                  "board_errors": sorted((summary.get("endpoint_errors") or {}).keys())},
        "follow_ups": [{"id": a["id"], "title": a.get("title"), "org": names.get(a.get("org"), a.get("org")),
                        "what": AP.follow_up(a, today)["what"], "due_on": AP.follow_up(a, today)["due_on"]} for a in apps],
        "event": best_event(_load(ws, "market", "orgs.json"), C.target_ids(config), names),
        "review_waiting": awaiting,
        "action": {"id": top["id"], "title": top.get("title"), "why": top.get("why", "")} if top else None,
        "autopilot": {"enabled": bool(settings(config).get("enabled")), "when": when_text(settings(config)),
                      "next": next_run(settings(config), (dt.date.fromisoformat(today) + dt.timedelta(days=1)).isoformat())},
    }


def num(x):
    return ("%d" % x) if isinstance(x, float) and x.is_integer() else str(x)


def note_md(n):
    lines = ["# This week: %s" % n["date"], ""]
    if n.get("level"):
        lines.append("Level %s, %s: fit %s for %s%s." % (n["level"], n["band"], num(n["fit"]), n["role"],
                                                       ", %s" % n["org"] if n.get("org") else ""))
        if n.get("points_to_next"):
            lines.append("%s points to Level %s, %s." % (num(n["points_to_next"]), n["level"] + 1, n["next_band"]))
        lines.append("")
    lines += ["What changed:", ""] + ["- " + c for c in n["changed"]] + [""]
    r = n["roles"]
    lines.append("Roles: %d new, %d closed%s." % (r["new"], r["closed"],
                 ", %d look suspicious (check before applying)" % r["suspicious"] if r["suspicious"] else ""))
    if r["board_errors"]:
        lines.append("Job boards that failed this run: %s (their roles were kept as they were)." % ", ".join(r["board_errors"]))
    if n["follow_ups"]:
        lines += ["", "Follow-ups due:", ""] + ["- %s, %s: %s, due %s." % (f["title"], f["org"], f["what"], f["due_on"])
                                               for f in n["follow_ups"]]
    if n["review_waiting"]:
        lines += ["", "%s for the blind reviewer; those scores count as 2 until then."
                  % ("1 role waits" if n["review_waiting"] == 1 else "%d roles wait" % n["review_waiting"])]
    if n["event"]:
        e = n["event"]
        lines += ["", "One event worth a look: %s (%s, %s)." % (e["text"].rstrip("."), e["org"], e["source"])]
    if n["action"]:
        lines += ["", "The one thing to do this week: %s." % n["action"]["title"].rstrip(".")]
    return "\n".join(lines) + "\n"


def write_note(ws, config, today):
    """Write campaign/weekly/<today>.json, and .md unless the agent already wrote one. Returns the note."""
    n = week_note(ws, config, today)
    C.write_json(C.wpath(ws, *WEEKLY_DIR, today + ".json"), n)
    md = C.wpath(ws, *WEEKLY_DIR, today + ".md")
    if not os.path.exists(md):
        C.write_text(md, note_md(n))
    return n


def page_data(note, clean):
    """The page's D.week: the newest note, for the This week card, or None."""
    if not note:
        return None
    return json.loads(json.dumps(note), object_hook=lambda d: {k: clean(v) if isinstance(v, str) and k not in (
        "date", "since", "due_on", "next", "source", "seen_on", "id") else v for k, v in d.items()})
