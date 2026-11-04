"""Climb from here: turn a LVLme quick result into a full campaign, with nothing redone and nothing lost.

quick.py promote makes a new campaign workspace (init.py) and carries across:
- every evidence item and open question, with its id and level unchanged;
- the CV and other sources, and the quick answers (appended to intake/answers.md);
- the posting, as the campaign's first role and its first target (with the
  job board, so fetch_roles.py reads the rest of that employer's roles);
- the judgements: requirements match, proof of work and organisation edge
  into eval/judgements.json; the warm path for that employer, and
  eligibility for the role's location classes, into
  eval/profile-dimensions.json. A score the blind reviewer agreed keeps its
  review date; one still waiting for a tie-break stays unreviewed (it
  counts as 2 until reviewed), as in the quick result.
- the fixes the quick result showed (up to three), as the plan's first open
  actions, each raising its factor for that role to the fix's target, with
  first estimates of effort and chance the person can change;
- which AI agent judged (judged_by), when quick recorded it.
The factors quick cannot check (public signal, application readiness) stay
"not yet judged", so the campaign's first fit can be lower than quick's
range: the interview fills them in. Nothing counts as verified on the CV's
say-so. No network calls here.
"""
import os
import re
import shutil

import _common as C
import fetch_roles as FR
import quick_posting as QP

ROLE_DIMS = ("D1", "D2", "D4")
# First estimates for a quick fix turned into a plan action: (effort hours, chance it works), by factor.
# The person can change them; the campaign's method says how (method/CAMPAIGN.md).
FIX_DEFAULTS = {"D1": (20, 0.3), "D2": (8, 0.5), "D3": (3, 0.3), "D4": (4, 0.5), "D6": (2, 0.5)}
FIX_NOTE = "From LVLme quick fix %s. Effort and chance are first estimates: change them if you know better."


def fix_actions(result, role, today):
    """The quick result's ranked fixes as open plan actions (A01, A02, ...), for this one role."""
    actions = []
    for n, f in enumerate(result.get("fixes") or [], 1):
        effort, chance = FIX_DEFAULTS.get(f["dimension"], (4, 0.4))
        actions.append({
            "id": "A%02d" % n, "title": f["title"],
            "why": "%s from %d to %d for %s: about %s more fit points (LVLme quick, %s)." % (
                f["name"], f["from"], f["to"], role["title"], "%g" % f["gain"], result.get("date") or today),
            "status": "todo", "owner": "you", "dimension": f["dimension"], "orgs": [role["org"]],
            "effort_hours": effort, "expected_points": f["gain"], "roles_affected": 1, "chance": chance,
            "done_when": "You have done the next step and can show it (a link, a file or a name): %s" % f["next_step"],
            "added_on": today,
            "effects": [{"dimension": f["dimension"], "set_at_least": f["to"], "scope": {"role_ids": [role["id"]]},
                         "note": FIX_NOTE % f["id"]}],
            "x_from_quick_fix": f["id"]})
    return actions


def target_for(role, org_name, quick_config):
    """The campaign target for the quick role's employer: its job board when quick read one, else manual."""
    t = {"id": role["org"], "name": org_name}
    try:
        link = QP.parse_link(role.get("url") or "")
    except QP.PostingError:
        link = {"ats": "page"}
    kind = ((quick_config.get("targets") or [{}])[0]).get("ats")
    if link["ats"] in ("greenhouse", "ashby", "lever", "smartrecruiters", "workable") and link.get("board"):
        t.update(ats=link["ats"], slug=link["board"])
        if link.get("region"):
            t["region"] = link["region"]
    elif link["ats"] == "workday":
        t.update(ats="workday", careers_url="https://%s/%s" % (link["host"], link["site"]))
    else:
        t["ats"] = "manual"
    t["x_from_quick"] = kind or link["ats"]
    return t


def family_for(title):
    """One role family from the posting's title words, for the interview to widen.

    The keyword is the title's first four words in order, with any punctuation between them, so the next
    job-board refresh finds the same role again: "Customer Success Manager, Commercial" matches itself
    (a plain phrase would not, because of the comma)."""
    words = re.sub(r"[^a-z0-9 ]+", " ", (title or "").lower()).split()[:4]
    if not words:
        return {"id": "role", "name": title or "The target role", "title_keywords": ["role"]}
    keyword = "re:(?<![a-z0-9])" + r"[^a-z0-9]+".join(re.escape(w) for w in words)
    return {"id": re.sub(r"[^a-z0-9]+", "_", " ".join(words)).strip("_")[:40] or "role",
            "name": title or "The target role", "title_keywords": [keyword]}


def write_open_disputes(ws, result, role, judged_on):
    """The quick answer's blind-review disagreements (D1, D2, D4) carried into eval/reviews/<date>.json, waiting
    for the tie-break the full campaign runs, so the dashboard says the reviewer disagreed, not that it never ran."""
    disputes = []
    for d in (result.get("review") or {}).get("disputes") or []:
        if d.get("dimension") not in ROLE_DIMS:
            continue
        side = lambda x, by: dict({k: x[k] for k in ("score", "anchor", "evidence") if x.get(k) not in (None, "")}, by=by)  # noqa: E731
        disputes.append({"item_id": "%s/%s" % (role["id"], d["dimension"]), "scorer": side(d["scorer"], "scorer"),
                         "reviewer": side(d["reviewer"], "reviewer"),
                         "tie_break": {"absent": True, "why": "LVLme quick has no tie-break; the full campaign runs it."},
                         "stands": 2, "decided_by": "awaiting_tie_break"})
    if disputes:
        C.write_json(C.wpath(ws, "eval", "reviews", "%s.json" % judged_on),
                     {"schema_version": 1, "date": judged_on, "rubric_version": "1.0", "disputes": disputes,
                      "note": "Carried over from LVLme quick."})


def promote(folder, ws, today):
    """Fill the new campaign workspace ws from the quick folder. Returns a short summary dict."""
    load = lambda *p: C.load_json(os.path.join(folder, *p), None)  # noqa: E731
    qcfg, quick, evidence = load("config.json") or {}, load("eval", "quick.json") or {}, load("profile", "evidence.json")
    roles_doc, result = load("market", "roles", "latest.json") or {}, load("result.json") or {}
    if not quick or not evidence or not roles_doc.get("roles"):
        raise SystemExit("lvlme: %s is not a finished LVLme quick folder (it needs eval/quick.json, "
                         "profile/evidence.json and the posting). Finish LVLme quick first." % C.show_path(folder))
    role = dict(roles_doc["roles"][0])
    org_name = ((qcfg.get("targets") or [{}])[0]).get("name") or role["org"]
    config = C.load_json(C.wpath(ws, "config.json"))
    target, family = target_for(role, org_name, qcfg), family_for(role.get("title"))
    config["targets"], config["families"] = [target], [family]
    cleared = sorted(set(quick.get("eligibility_cleared") or []))
    if cleared:
        config.setdefault("candidate", {})["eligibility_cleared"] = cleared
    C.write_json(C.wpath(ws, "config.json"), config)

    C.write_json(C.wpath(ws, "profile", "evidence.json"), dict(evidence, updated_on=today))
    src = os.path.join(folder, "intake", "sources")
    for name in sorted(os.listdir(src)) if os.path.isdir(src) else []:
        shutil.copyfile(os.path.join(src, name), C.wpath(ws, "intake", "sources", name))
    answers = os.path.join(folder, "intake", "answers.md")
    if os.path.exists(answers):
        with open(C.wpath(ws, "intake", "answers.md"), "a", encoding="utf-8") as out, open(answers, encoding="utf-8") as f:
            out.write("\n\n## From LVLme quick (%s)\n\n%s" % (quick.get("judged_on", today), f.read()))

    remote = role.get("remote")
    role.update(family=family["id"], location_classes=FR.location_classes(
        list(role.get("locations") or []), remote if remote in (True, False) else False, config))
    role.setdefault("first_seen", quick.get("judged_on", today))
    C.write_json(C.wpath(ws, "market", "roles", "latest.json"), {
        "schema_version": 1, "fetched_on": quick.get("judged_on", today),
        "summary": {"matched_total": 1, "endpoints": {role["org"]: "LVLme quick"}}, "roles": [role]})
    if target["ats"] == "manual":
        C.write_json(C.wpath(ws, "market", "roles", "manual.json"), {"postings": [{
            "org": role["org"], "id": role["id"].split(":", 1)[1], "title": role["title"],
            "locations": role.get("locations") or [], "url": role.get("url"),
            "description": role.get("description_text") or ""}]})

    agreed, judged_on = set((result.get("review") or {}).get("agreed") or []), quick.get("judged_on", today)
    entry = {"judged_on": judged_on, "hard_requirement_lacking": bool(quick.get("hard_requirement_lacking"))}
    for d in ROLE_DIMS:
        f = quick["factors"].get(d) or {}
        entry[d] = {"score": f.get("score", 0), "evidence": f.get("evidence") or [], "note": f.get("note", "")}
        if d in agreed:
            entry[d].update(reviewed_on=judged_on)
    if quick.get("eligibility_blocked") is not None:
        entry["eligibility_blocked"] = bool(quick["eligibility_blocked"])
    write_open_disputes(ws, result, role, judged_on)
    judgements = {"schema_version": 1, "rubric_version": "1.0", "roles": {role["id"]: entry}}
    if quick.get("judged_by"):
        judgements["judged_by"] = quick["judged_by"]
    C.write_json(C.wpath(ws, "eval", "judgements.json"), judgements)

    plan = C.load_json(C.wpath(ws, "campaign", "plan.json"))
    actions = fix_actions(result, role, today)
    plan.update(actions=actions, updated_on=today)
    C.write_json(C.wpath(ws, "campaign", "plan.json"), plan)

    prof = C.load_json(C.wpath(ws, "eval", "profile-dimensions.json"))
    for d, place, keys in (("D3", prof["D3"], [role["org"]]),
                           ("D6", prof["D6_rules"]["classes"], role["location_classes"])):
        f = quick["factors"].get(d)
        for k in keys if f else []:
            place[k] = {"score": f.get("score", 0), "evidence": f.get("evidence") or [], "note": f.get("note", ""),
                        "judged_on": judged_on, **({"reviewed_on": judged_on} if d in agreed else {})}
    C.write_json(C.wpath(ws, "eval", "profile-dimensions.json"), prof)
    return {"role": role["id"], "title": role["title"], "actions": actions, "target": target, "family": family["id"], "evidence": len(evidence.get("items") or []),
            "classes": role["location_classes"], "agreed": sorted(agreed)}
