"""Applications and follow-ups (campaign/applications.json): the last step of a climb, kept track of.

Stages use career-ops' ten names (schemas/applications.schema.json), so the two
tools can talk. Silence is the most common outcome, so follow-ups are timed:
the first nudge 7 days after the last step, then every 7 days, at most 2; a
thank-you note 1 day after an interview. Each open application is labelled:

    waiting     nothing due yet
    due         a follow-up or thank-you is due (up to 3 days late)
    overdue     more than 3 days late
    gone quiet  two follow-ups sent and 7 more days of silence

Progress only: score.py never reads this file. Drafts only: the person sends
every note. Stage changes are recorded only when the person confirms them
(scripts/applications.py). No network calls here.
"""
import datetime as dt
import html

REL = "campaign/applications.json"
LOG = "campaign/applications-log.tsv"
STAGES = ["evaluated", "applied", "responded", "assessment", "interview", "offer", "rejected", "discarded", "skip", "hired"]
STAGE_NAMES = {"evaluated": "Evaluated", "applied": "Applied", "responded": "Responded", "assessment": "Assessment",
               "interview": "Interview", "offer": "Offer", "rejected": "Rejected", "discarded": "Discarded",
               "skip": "Skipped", "hired": "Hired"}
CHASED = {"applied", "responded", "assessment", "interview"}   # stages where silence earns a follow-up
NUDGE_DAYS, MAX_NUDGES, THANKS_DAYS, LATE_DAYS = 7, 2, 1, 3
LABELS = {"waiting": "Waiting", "due": "Due", "overdue": "Overdue", "gone_quiet": "Gone quiet", "none": ""}
NOTE = "Progress only: it changes no score. You send every note yourself."


def days(a, b):
    try:
        return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days
    except (TypeError, ValueError):
        return 0


def plus(date, n):
    return (dt.date.fromisoformat(date) + dt.timedelta(days=n)).isoformat()


def follow_up(app, today):
    """{"status", "what", "due_on", "since"} for one application. since: days since the last step."""
    stage, last = app.get("stage"), app.get("last_step_on") or today
    out = {"status": "none", "what": "", "due_on": None, "since": max(0, days(last, today))}
    if stage not in CHASED:
        return out
    if stage == "interview" and not app.get("thanked"):
        what, due_on = "Thank-you note", plus(last, THANKS_DAYS)
    elif (app.get("nudges") or 0) >= MAX_NUDGES:
        out["status"] = "gone_quiet" if out["since"] >= NUDGE_DAYS else "waiting"
        return out
    else:
        what, due_on = ("Follow-up %d of %d" % ((app.get("nudges") or 0) + 1, MAX_NUDGES)), plus(last, NUDGE_DAYS)
    late = days(due_on, today)
    out.update(what=what, due_on=due_on,
               status="waiting" if late < 0 else "due" if late <= LATE_DAYS else "overdue")
    return out


def ordered(doc, today):
    """Open applications, most urgent first, then the closed ones, newest step first."""
    apps = [a for a in (doc or {}).get("applications") or [] if isinstance(a, dict)]
    urgency = {"overdue": 0, "due": 1, "gone_quiet": 2, "waiting": 3, "none": 4}
    return sorted(apps, key=lambda a: (urgency[follow_up(a, today)["status"]],
                                       -days("2000-01-01", a.get("last_step_on") or "2000-01-01"), a.get("id", "")))


def due_now(doc, today):
    return [a for a in ordered(doc, today) if follow_up(a, today)["status"] in ("due", "overdue")]


# ------------------------------------------------------------------ the page


def page_data(doc, today, org_names, clean):
    """The page's D.apps: one row per application, most urgent first, or None when nothing is tracked."""
    if doc is None:
        return None
    rows = []
    for a in ordered(doc, today):
        f = follow_up(a, today)
        rows.append({"id": a["id"], "title": clean(a.get("title")), "org": org_names.get(a.get("org"), a.get("org")),
                     "stage": STAGE_NAMES.get(a.get("stage"), a.get("stage")), "since": f["since"],
                     "status": f["status"], "label": LABELS[f["status"]], "what": f["what"], "due": f["due_on"] or "",
                     "role": a.get("role_id") or ""})
    return {"note": NOTE, "rows": rows, "due": sum(1 for r in rows if r["status"] in ("due", "overdue"))}


def static_html(apps):
    """The static summary's Applications table."""
    if not apps or not apps["rows"]:
        return ""
    rows = "".join('<tr><th scope="row">%s</th><td>%s</td><td>%s</td><td>%s</td></tr>' % (
        html.escape("%s, %s" % (r["title"], r["org"])), html.escape(r["stage"]),
        html.escape("%d day%s ago" % (r["since"], "" if r["since"] == 1 else "s")),
        html.escape(("%s: %s" % (r["label"], r["what"])) if r["what"] and r["status"] != "waiting" else r["label"] or "Closed"))
        for r in apps["rows"])
    return ('<h3 id="staticAppsH">Applications</h3><p class="small sub">%s</p>'
            '<table aria-labelledby="staticAppsH"><thead><tr><th scope="col">Application</th><th scope="col">Stage</th>'
            '<th scope="col">Last step</th><th scope="col">Follow-up</th></tr></thead><tbody>%s</tbody></table>'
            ) % (html.escape(NOTE), rows)


# ------------------------------------------------------------- agent files


def agent_data(doc, today, org_names):
    """dashboard.json's applications block."""
    out = []
    for a in ordered(doc, today):
        f = follow_up(a, today)
        out.append({"id": a["id"], "org": a.get("org"), "org_name": org_names.get(a.get("org"), a.get("org")),
                    "title": a.get("title"), "stage": a.get("stage"), "last_step_on": a.get("last_step_on"),
                    "follow_up": f["status"], "next": f["what"], "due_on": f["due_on"]})
    return {"about": NOTE + " Stages are career-ops' names. Record a change with scripts/applications.py, "
                     "only after the person confirms it.", "applications": out}


def summary_lines(block):
    lines = ["", "## Applications (progress only: changes no score)"]
    for a in block["applications"]:
        due = "; %s %s %s" % (LABELS[a["follow_up"]].lower(), a["next"].lower(), a["due_on"]) if a["next"] else ""
        lines.append("- %s, %s: %s since %s%s." % (a["title"], a["org_name"], STAGE_NAMES.get(a["stage"], a["stage"]),
                                                     a["last_step_on"], due))
    lines.append("- Draft a due note with `python3 scripts/applications.py draft <id>`; the person sends it.")
    return lines


# ------------------------------------------------------------------ checks


def checks(doc, targets, role_ids, errors, warnings):
    """validate.py's cross-file checks for campaign/applications.json (the schema is checked separately)."""
    if doc is None:
        return
    seen = set()
    for a in doc.get("applications") or []:
        if not isinstance(a, dict):
            continue
        aid, where = a.get("id"), REL + ": " + str(a.get("id"))
        if aid in seen:
            errors.append(where + " is a duplicate id")
        seen.add(aid)
        if a.get("role_id") and role_ids and a["role_id"] not in role_ids and a.get("stage") in CHASED | {"evaluated"}:
            warnings.append(where + " names role %s, which is not open in market/roles/latest.json (it may have closed)"
                            % a["role_id"])
        if a.get("applied_on") and a.get("last_step_on") and a["applied_on"] > a["last_step_on"]:
            errors.append(where + ": applied_on %s is after last_step_on %s" % (a["applied_on"], a["last_step_on"]))
        if a.get("stage") == "applied" and not a.get("applied_on"):
            warnings.append(where + " is at applied with no applied_on date")
