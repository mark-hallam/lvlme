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
import shutil

import _common as C
import _doors as DR
import _applications as AP
import _public as PB
import _weekly as WK
import _goal as GL

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_NAMES = dict(zip(DAYS, ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]))
DEFAULTS = {"rhythm": "weekly", "day": "mon", "time": "07:00", "run": "light", "sources": [], "helpers": True}
WEEKLY_DIR = ("campaign", "weekly")
ALLOWED_TOOLS = 'Bash(python3 *) Bash(ls *) Bash(cat *) Bash(test *) Bash(echo *) Bash(date *) Read Write Edit Glob Grep'


def settings(config):
    return dict(DEFAULTS, **((config or {}).get("autopilot") or {}))


def next_run(ap, today, now=None):
    """The date of the next scheduled run on or after today (ISO), or None when Autopilot is off."""
    if not ap.get("enabled"):
        return None
    d = dt.date.fromisoformat(today)
    current = dt.datetime.fromisoformat(now) if now else None
    if current and current.date() == d and current.strftime("%H:%M") >= ap["time"]:
        d += dt.timedelta(days=1)
    if ap["rhythm"] == "daily":
        return d.isoformat()
    return (d + dt.timedelta(days=(DAYS.index(ap["day"]) - d.weekday()) % 7)).isoformat()


def when_text(ap):
    return ("Every day at %s" % ap["time"]) if ap["rhythm"] == "daily" else ("%ss at %s" % (DAY_NAMES[ap["day"]], ap["time"]))


def claude_path():
    found = shutil.which("claude")
    if found:
        return found
    fallback = os.path.expanduser("~/.local/bin/claude")
    return fallback if os.path.isfile(fallback) else next((p for p in ("/opt/homebrew/bin/claude", "/usr/local/bin/claude") if os.path.isfile(p)), None)


# ------------------------------------------------------------ the schedule


def task_prompt(engine, ws, ap):
    """The prompt a scheduled task runs. Generic: every fact about the person comes from their workspace."""
    sources = ", ".join(ap["sources"]) if ap["sources"] else "none beyond the workspace files"
    return "\n".join([
        "You are running LVLme on autopilot for the person who owns this workspace. Nobody is present.",
        "",
        "Engine (read only, never edit it): %s" % engine,
        "Workspace (all of the person's data): %s" % ws,
        "Run each script as a plain python3 scripts/<name>.py --workspace %s command. Do not put variable assignments first and do not use cd." % ws,
        "",
        "Read %s/SKILL.md, %s/method/RUNBOOK.md and \"Runs with nobody present\" in %s/docs/ORCHESTRATION.md, "
        "and follow them exactly: ask nothing, approve nothing new, take no step that needs the person's yes."
        % (engine, engine, engine),
        "",
        "This run, in order:",
        "1. Process campaign/inbox.md and actions marked done in campaign/plan.json.",
        "2. python3 scripts/fetch_roles.py --workspace %s (it also checks each posting's age and reposts)." % ws,
        "3. python3 scripts/fetch_doors.py --workspace %s. If it fails, skip it like any other source." % ws,
        "4. Evidence since the last run, from these approved read-only sources only: %s." % sources,
        "5. python3 scripts/run_plan.py --workspace %s, then judge the roles of a %s run (--json lists them). "
        "Set judged_by at the top of eval/judgements.json to the agent you are and your model." % (ws, ap["run"]),
        ("6. The blind review gate, with fresh helper agents, as method/REVIEW.md says."
         if ap["helpers"] else
         "6. Start no helper agents: leave new scores above 2 waiting for review (they count as 2) and say so."),
        "7. python3 scripts/score.py --workspace %s, then python3 scripts/build_dashboard.py --workspace %s, then python3 scripts/validate.py --workspace %s (it must exit 0)." % (ws, ws, ws),
        "8. python3 scripts/autopilot.py week --workspace %s (writes this week's note and rebuilds the dashboard's This week card)." % ws,
        "9. On a Monday also run python3 scripts/autopilot.py plan --workspace %s (the Monday plan note). "
        "On a Friday also run python3 scripts/autopilot.py review --workspace %s (the Friday review: what was done with "
        "evidence, what moved, next week's one move)." % (ws, ws),
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
    claude = claude_path()
    python = shutil.which("python3") or "/usr/bin/python3"
    path = ":".join(dict.fromkeys([os.path.dirname(claude) if claude else "CLAUDE_PATH_HERE", os.path.dirname(python), "/usr/bin", "/bin"]))
    return ('%d %d * * %s PATH="%s"; cd "%s" && %s -p "$(cat \'%s\')" --permission-mode acceptEdits '
            '--allowedTools "%s" >> "%s" 2>&1'
            % (int(mm), int(hh), days, path, engine, claude or "CLAUDE_PATH_HERE", prompt_path, ALLOWED_TOOLS, log_path))


# ------------------------------------------------------------ the weekly note


def _load(ws, *parts):
    return C.load_json(C.wpath(ws, *parts), None)


def previous_note(ws, today):
    notes = sorted(f for f in glob.glob(os.path.join(C.wpath(ws, *WEEKLY_DIR), "*.json"))
                   if os.path.basename(f)[:10] < today)
    return C.load_json(notes[-1], {}) if notes else None


def previous_run(ws, today):
    """{"date", "fit"} for the newest scored run before today (its best judged fit), or None."""
    runs = sorted(f for f in glob.glob(os.path.join(C.wpath(ws, "eval", "runs"), "*.json"))
                  if os.path.basename(f)[:10] < today)
    if not runs:
        return None
    run = C.load_json(runs[-1], {}) or {}
    fits = [r.get("fit") for r in run.get("roles") or [] if r.get("judged", True) and r.get("fit") is not None]
    return {"date": run.get("run_date") or os.path.basename(runs[-1])[:10], "fit": max(fits) if fits else None,
            "rubric_version": run.get("rubric_version")}


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
    prev_note = previous_note(ws, today)
    prior_run = previous_run(ws, today)
    prev = prev_note or prior_run
    since = (prev or {}).get("date")
    previous = previous_note(ws, today)
    reported = set((previous or {}).get("reported_progress_ids") or [])
    progress, reported_now = [], []
    for d in (dash.get("levels") or {}).get("progress_days") or []:
        if not since or d.get("date", "") >= since:
            for kind in ("actions", "evidence"):
                for item in d.get(kind) or []:
                    ident = "%s:%s:%s" % (kind, d.get("date", ""), item)
                    if ident not in reported:
                        progress.append((kind, item, d.get("date", "")))
                        reported_now.append(ident)
    changed = []
    if prior_run and best and prior_run.get("fit") is not None and prior_run.get("rubric_version") == dash.get("rubric_version"):
        delta = round(best["fit"] - prior_run["fit"], 1)
        changed.append("Best fit %s, from %s to %s." % ("up %s" % num(delta) if delta > 0 else "down %s" % num(-delta)
                                                      if delta < 0 else "unchanged", num(prior_run["fit"]), num(best["fit"])))
    elif prior_run and best and prior_run.get("rubric_version") != dash.get("rubric_version"):
        changed.append("The scoring rules changed from version %s to %s, so this change is not comparable." %
                       (prior_run.get("rubric_version"), dash.get("rubric_version")))
    done = sorted({item for kind, item, _ in progress if kind == "actions"})
    evidence = sorted({item for kind, item, _ in progress if kind == "evidence"})
    if done:
        titles = {a.get("id"): a.get("title", a.get("id")) for a in dash.get("actions_done") or []}
        changed.append("%d plan action%s done: %s." % (len(done), "" if len(done) == 1 else "s",
                                                      "; ".join(titles.get(a, a).rstrip(".") for a in done)))
    if evidence:
        changed.append("%d new piece%s of evidence counted." % (len(evidence), "" if len(evidence) == 1 else "s"))
    apps_doc = _load(ws, *AP.REL.split("/")) or {}
    app_titles = {a.get("id"): a.get("title", a.get("id")) for a in apps_doc.get("applications") or []}
    log_path = C.wpath(ws, *AP.LOG.split("/"))
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8") as f:
            rows = [line.rstrip("\n").split("\t") for line in f.readlines()[1:]]
        for row in rows:
            if len(row) < 5:
                continue
            changed_on, aid, event, before, after = row[:5]
            ident = "application:%s:%s:%s" % (changed_on, aid, event)
            if (not since or changed_on >= since) and ident not in reported:
                label = {"added": AP.STAGE_NAMES.get(after, after), "stage": AP.STAGE_NAMES.get(after, after),
                         "followup": "Follow-up sent", "thanks": "Thank-you note sent"}.get(event, event)
                changed.append("Application %s: %s (%s)." % (app_titles.get(aid, aid), label, changed_on))
                reported_now.append(ident)
    warm = _load(ws, "campaign", "warm-paths.json") or {}
    for contact in warm.get("contacts") or []:
        changed_on = contact.get("updated_on", "")
        ident = "warm:%s:%s:%s" % (contact.get("id"), contact.get("stage"), changed_on)
        if (not since or changed_on >= since) and ident not in reported:
            changed.append("Warm contact %s: %s (%s)." % (contact.get("person", contact.get("id")), contact.get("stage"), changed_on))
            reported_now.append(ident)
    if not changed:
        changed.append("Nothing moved since %s." % since if since else "This is the first scored run: the next note says what moved.")
    apps = AP.due_now(apps_doc, today)
    top = (dash.get("actions_active") or [None])[0]
    next_level = next_level_line(best)
    streak = WK.weeks_in_a_row((dash.get("levels") or {}).get("progress_days") or [], today)
    runs = sorted(glob.glob(os.path.join(C.wpath(ws, "eval", "runs"), "*.json")))
    run = C.load_json(runs[-1], {}) if runs else {}
    awaiting = sum(1 for r in (run or {}).get("roles") or [] if r.get("awaiting_review"))
    fetch = _load(ws, "market", "roles", "fetch-status.json") or {}
    data_date = fetch.get("data_date") or roles_doc.get("fetched_on") or "unknown"
    checked = bool(fetch.get("ok", True)) and fetch.get("date", today) >= today and data_date == today
    board_errors = fetch.get("board_errors") or sorted((summary.get("endpoint_errors") or {}).keys())
    if not checked:
        changed.append("Job boards could not be reached, so the role numbers are from %s." % data_date)
    return {
        "schema_version": 1, "date": today, "since": since,
        "rubric_version": dash.get("rubric_version"),
        "fit": best.get("fit"), "level": best.get("level"), "band": best.get("band"),
        "role": best.get("title"), "org": names.get(best.get("org"), best.get("org")),
        "points_to_next": best.get("points_to_next"), "next_band": best.get("next_band"),
        "next_level_line": next_level, "weeks_in_a_row": streak,
        "changed": changed, "reported_progress_ids": reported_now,
        "roles": {"new": len(summary.get("new_role_ids") or []), "closed": len(summary.get("closed_role_ids") or []),
                  "suspicious": (summary.get("posting_checks") or {}).get("suspicious", 0),
                  "board_errors": board_errors, "checked": checked, "data_date": data_date},
        "follow_ups": [{"id": a["id"], "title": a.get("title"), "org": names.get(a.get("org"), a.get("org")),
                        "what": AP.follow_up(a, today)["what"], "due_on": AP.follow_up(a, today)["due_on"]} for a in apps],
        "event": (DR.next_door(_load(ws, "market", "doors.json"), today, names)
                  or best_event(_load(ws, "market", "orgs.json"), C.target_ids(config), names)),
        "review_waiting": awaiting,
        "public": public_line(ws, config, today),
        "action": {"id": top["id"], "title": top.get("title"), "why": top.get("why", "")} if top else None,
        "autopilot": {"enabled": bool(settings(config).get("enabled")), "when": when_text(settings(config)),
                      "next": next_run(settings(config), (dt.date.fromisoformat(today) + dt.timedelta(days=1)).isoformat())},
    }


def next_level_line(best):
    """One sentence on the next level from the dashboard's agent file (levels.best_role), or None at the top."""
    if not best or best.get("top_level") or not best.get("next_level"):
        return None
    if best.get("reachable_on_expected_odds"):
        s = best.get("smallest_set") or {}
        return GL.next_sentence(best["next_level"], True, s.get("level_reached_on"), len(s.get("actions") or []))
    m = best.get("missing") or {}
    return GL.next_sentence(best["next_level"], False, None, 0, m.get("points_short", 0),
                            [x["name"].lower() for x in (m.get("room_by_factor") or [])[:3]])


def public_line(ws, config, today):
    """Build in public this week: posts against the person's target, and the newest idea worth sharing."""
    doc = _load(ws, *PB.REL.split("/"))
    found = PB.ideas(_load(ws, "campaign", "plan.json"), _load(ws, "profile", "evidence.json"),
                     _load(ws, "market", "doors.json"), doc, today)
    if doc is None and not found:
        return None
    c = PB.cadence(doc, config, today)
    return {"posted": c["this_week"], "per_week": c["per_week"], "idea": found[0]["title"] if found else None,
            "ref": found[0]["ref"] if found else None}


def num(x):
    return ("%d" % x) if isinstance(x, float) and x.is_integer() else str(x)


def note_md(n):
    lines = ["# This week: %s" % n["date"], ""]
    if n.get("level"):
        lines.append("Level %s, %s: fit %s for %s%s." % (n["level"], n["band"], num(n["fit"]), n["role"],
                                                       ", %s" % n["org"] if n.get("org") else ""))
        if n.get("points_to_next"):
            lines.append("%s points to Level %s, %s." % (num(n["points_to_next"]), n["level"] + 1, n["next_band"]))
        if n.get("next_level_line"):
            lines.append(n["next_level_line"])
        if n.get("weeks_in_a_row") is not None:
            lines.append(WK.streak_text(n["weeks_in_a_row"]))
        lines.append("")
    lines += ["What changed:", ""] + ["- " + c for c in n["changed"]] + [""]
    r = n["roles"]
    if r.get("checked", True):
        lines.append("Roles: %d new, %d closed%s." % (r["new"], r["closed"],
                     ", %d look suspicious (check before applying)" % r["suspicious"] if r["suspicious"] else ""))
    else:
        lines.append("Job boards could not be reached, so the role numbers are from %s." % r.get("data_date", "unknown"))
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
    if n.get("public"):
        p = n["public"]
        lines += ["", "Build in public: %d of %d post%s this week.%s" % (
            p["posted"], p["per_week"], "" if p["per_week"] == 1 else "s",
            " Worth sharing: %s (%s); I can draft it, you post it." % (p["idea"].rstrip("."), p["ref"]) if p["idea"] else "")]
    if n["action"]:
        lines += ["", "The one thing to do this week: %s." % n["action"]["title"].rstrip(".")]
    return "\n".join(lines) + "\n"


def write_note(ws, config, today, stamp=None):
    """Write campaign/weekly/<stamp or today>.json, and .md unless the agent already wrote one. Returns the note.

    stamp is the Monday for the Monday plan note, so the file is named for the week's Monday."""
    n = week_note(ws, config, today)
    stamp = stamp or today
    n["date"] = stamp
    C.write_json(C.wpath(ws, *WEEKLY_DIR, stamp + ".json"), n)
    md = C.wpath(ws, *WEEKLY_DIR, stamp + ".md")
    mine = os.path.exists(md) and open(md, encoding="utf-8").read().startswith("# This week: ")
    if mine or not os.path.exists(md):   # rewrite our own note; never one the agent wrote
        C.write_text(md, note_md(n))
    return n


def page_data(note, clean):
    """The page's D.week: the newest note, for the This week card, or None."""
    if not note:
        return None
    return json.loads(json.dumps(note), object_hook=lambda d: {k: clean(v) if isinstance(v, str) and k not in (
        "date", "since", "due_on", "next", "source", "seen_on", "id") else v for k, v in d.items()})
