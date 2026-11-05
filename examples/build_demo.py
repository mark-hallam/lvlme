#!/usr/bin/env python3
"""Rebuild every generated file in the demo workspace from its inputs.

The demo is a fictional person (Alex Example) applying to fictional
organisations (Acme AI, Globex Labs, Initech Robotics). To give the Trends view
some history, this replays five weekly runs, 2026-10-04 to 2026-11-01. Each
week uses the job postings that were open then and the evidence, judgements
and metrics as they stood then, and runs the real scripts on them.

Hand-written inputs: config.json, intake/, profile/evidence.json,
profile/claims-audit.json, profile/network.json (second_degree only),
eval/judgements.json, eval/profile-dimensions.json, eval/gap-templates.json,
eval/outlook.json, eval/swot.json, eval/reviews/ (a dispute settled by the middle of
three), campaign/ (including a parked action, status later; applications.json and its log are
generated from APPS), market/orgs.json,
market/fixtures/. profile/evidence.json has a partially verified item and an
extension field (x_...).
Generated: market/roles/, profile/network.json (orgs), eval/runs/,
campaign/metrics-history.json, report/.

Usage: python3 examples/build_demo.py
"""
import copy
import glob
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.join(HERE, "demo-workspace")
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import _autopilot as autopilot_notes  # noqa: E402
import _weekly as weekly  # noqa: E402
import applications  # noqa: E402
import build_dashboard  # noqa: E402
import doors  # noqa: E402
import fetch_doors  # noqa: E402
import fetch_roles  # noqa: E402
import network_map  # noqa: E402
import practice  # noqa: E402
import proof_profile  # noqa: E402
import public  # noqa: E402
import score  # noqa: E402

WEEKS = ["2026-10-04", "2026-10-11", "2026-10-18", "2026-10-25", "2026-11-01"]
# Postings that were not open for the whole period: role id -> (first week, last week), as indexes into WEEKS.
OPEN = {"acme:4100007": (0, 2), "initech:i-0001": (2, 4), "globex:g-0004": (3, 4), "initech:i-0004": (4, 4)}
FIXTURE_ORGS = {"acme": "greenhouse", "globex": "ashby", "initech": "lever"}
METRICS = {"warm_intros": [0, 0, 0, 1, 1], "proof_pieces": [1, 1, 2, 3, 3]}
# Doors added by hand on the demo (scripts/doors.py add), beside the ones read from the fictional calendar.
DOORS = [["--kind", "programme", "--title", "Acme AI Fellows programme", "--org", "acme", "--closes", "2026-12-15",
          "--place", "Sydney or remote", "--link", "https://example.com/acme/fellows", "--source-kind", "employer_page",
          "--verified"],
         ["--kind", "community", "--title", "Initech Robotics partner community", "--org", "initech",
          "--place", "Melbourne", "--link", "https://example.com/initech/partners", "--source-kind", "employer_page",
          "--verified"]]
# Made-up applications and what happened to them (scripts/applications.py), so the tracker and the "How right has
# LVLme been" panel have something to show: [date, command, arguments]. Each records the odds the role had that day.
APPS = [["2026-10-04", "add", "--org", "acme", "--title", "Applied AI Deployment Lead, Asia Pacific", "--role-id", "acme:4100002"],
        ["2026-10-04", "add", "--org", "globex", "--title", "AI Success Manager, Asia", "--role-id", "globex:g-0003"],
        ["2026-10-05", "add", "--org", "initech", "--title", "Product Manager, Warehouse Autonomy", "--role-id", "initech:i-0002"],
        ["2026-10-11", "add", "--org", "acme", "--title", "Technical Program Manager, Model Launches", "--role-id", "acme:4100001"],
        ["2026-10-12", "add", "--org", "globex", "--title", "Product Manager, Developer Platform", "--role-id", "globex:g-0001"],
        ["2026-10-15", "move", "ap2", "rejected"],
        ["2026-10-16", "move", "ap4", "responded"],
        ["2026-10-18", "add", "--org", "acme", "--title", "Product Manager, Safety Tooling", "--role-id", "acme:4100007"],
        ["2026-10-19", "add", "--org", "globex", "--title", "Technical Program Manager, Infrastructure", "--role-id", "globex:g-0002"],
        ["2026-10-20", "move", "ap1", "rejected"],
        ["2026-10-22", "move", "ap4", "interview"],
        ["2026-10-23", "thanks", "ap4"],
        ["2026-10-25", "move", "ap6", "rejected", "--note", "The posting closed."],
        ["2026-10-26", "add", "--org", "initech", "--title", "Program Manager, Robot Fleet Deployments", "--role-id", "initech:i-0001"],
        ["2026-10-26", "move", "ap5", "rejected"],
        ["2026-10-26", "followup", "ap7"],
        ["2026-10-28", "move", "ap3", "rejected"],
        ["2026-10-30", "move", "ap4", "rejected", "--note", "After the first interview."]]
# A made-up practice session and the debrief of ap4's interview (scripts/practice.py): [date, arguments].
QUESTIONS = [["2026-10-20", "--question", "Why Acme AI, and why this role now?", "--rating", "solid", "--theme",
              "why_here", "--story", "S02", "--org", "acme"],
             ["2026-10-20", "--question", "Tell me about a time you disagreed with a decision.", "--rating", "gap",
              "--theme", "disagree", "--org", "acme"],
             ["2026-10-22", "--real", "--app", "ap4", "--question", "Tell me about a launch you ran end to end.",
              "--rating", "strong", "--theme", "impact", "--story", "S01"],
             ["2026-10-22", "--real", "--app", "ap4", "--question", "How have you led people who did not report to "
              "you?", "--rating", "gap", "--theme", "lead", "--story", "S01"]]
# A made-up build in public post (scripts/public.py): drafted, posted, and what it led to. Its link is left
# unchecked, so the demo shows a post that does not count as proof yet.
PUBLIC = [["2026-10-26", "draft", "A03", "--channel", "x"],
          ["2026-10-27", "posted", "P01", "--url", "https://example.com/alex/posts/scheduling-case-study"],
          ["2026-10-30", "result", "P01", "--note", "4 replies, and a warehouse operator asked for the checklist"]]
OUTPUTS = ["eval/runs", "market/roles", "market/doors.json", "report", "campaign/metrics-history.json",
           "campaign/applications.json", "campaign/applications-log.tsv", "campaign/questions.json",
           "campaign/public.json", "campaign/drafts/public-P01-2026-10-26.md"]


def load(rel, root=DEMO):
    with open(os.path.join(root, rel), encoding="utf-8") as fh:
        return json.load(fh)


def save(rel, data, root):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def entry(score_, evidence, note, judged="2026-10-04"):
    return {"score": score_, "evidence": evidence, "note": note, "judged_on": judged}


def earlier_judgements():
    """Judgements as they stood before the 2026-10-25 re-judging."""
    base = {"hard_requirement_lacking": False, "judged_on": "2026-10-04", "reviewed_on": "2026-10-05"}
    return {
        "globex:g-0002": dict(base, D1=entry(2, ["E01", "E02"], "Programs were operations, not infrastructure."),
                              D2=entry(2, ["E05"], "Rollout claim is self-reported only."),
                              D4=entry(1, ["E01"], "Hardware delivery tracking is adjacent.")),
        "globex:g-0003": dict(base, D1=entry(3, ["E01", "E02"], "Operations roles close to implementation work."),
                              D2=entry(3, ["E04"], "Verified tool."), D4=entry(2, ["E01"], "Logistics customers are a plus.")),
        "initech:i-0002": dict(base, D1=entry(2, ["E01"], "Operations close to product, but no product title."),
                               D2=entry(2, ["E04", "E05"], "No case study yet."),
                               D4=entry(3, ["E01"], "Deep warehouse workflow knowledge.")),
        "acme:4100007": dict(base, hard_requirement_lacking=True, hard_requirement_note="4+ years of product management",
                             D1=entry(1, ["E02"], "No product management title."),
                             D2=entry(2, ["E04"], "route-eval is close to safety tooling."),
                             D4=entry(1, ["E04"], "Some overlap with evaluation tools.")),
    }


def week_state(i, cur):
    """Return the input documents as they stood in week i."""
    week = WEEKS[i]
    ev, jd, prof, plan, outlook = (copy.deepcopy(cur[k]) for k in ("evidence", "judgements", "profile", "plan", "outlook"))
    ev["items"] = [e for e in ev["items"] if e.get("added_on", "") <= week]
    known = {e["id"] for e in ev["items"]}
    for q in ev["open_questions"]:
        if any(a not in known for a in q.get("answer_evidence", [])):
            q["status"], q["answer_evidence"] = "open", []
    older = earlier_judgements()
    roles = {}
    for rid, j in jd["roles"].items():
        if j.get("judged_on", "") <= week:
            roles[rid] = j
        elif rid in older:
            roles[rid] = older[rid]
    if i <= 2:
        roles["acme:4100007"] = older["acme:4100007"]
    jd["roles"] = roles
    d3 = prof["D3"]
    if i == 0:
        for org in ("acme", "globex", "initech"):
            d3[org] = entry(0, [], "Network not mapped yet.")
    elif i < 3:
        d3["globex"] = entry(1, ["E09"], "Two first-degree contacts; neither has seen Alex's work yet.", "2026-10-11")
    if i < 2:
        prof["D5"]["default"] = entry(1, ["E07"], "Personal site and essays only.")
    if i < 4:
        prof["D7"].pop("initech", None)
    prof["reviewed_on"] = week
    for m in plan["north_star"]:
        if m["id"] in METRICS:
            m["current"] = METRICS[m["id"]][i]
    if i < 2:
        outlook.update(band="Very low", text="Early days: no warm paths and little public proof yet.", reasons=[])
    elif i < 4:
        outlook.update(band="Low", text="The Initech fleet role is a strong domain fit, but there is no warm path yet.",
                       reasons=[])
    outlook["judged_on"] = week
    for doc in (jd, prof):  # a review recorded later than this run had not happened yet: it happened in this run
        for e in _entries(doc):
            if e.get("reviewed_on", "") > week:
                e["reviewed_on"] = week
    return {"profile/evidence.json": ev, "eval/judgements.json": jd, "eval/profile-dimensions.json": prof,
            "campaign/plan.json": plan, "eval/outlook.json": outlook}


def _entries(doc):
    if "roles" in doc:
        for j in doc["roles"].values():
            yield j
            for d in ("D1", "D2", "D4"):
                yield j[d]
    else:
        for sec in ("D3", "D5", "D7"):
            yield from doc.get(sec, {}).values()
        yield from doc.get("D6_rules", {}).get("classes", {}).values()


def role_id(org, job):
    return "%s:%s" % (org, job["id"])


def week_fixtures(i, dest):
    os.makedirs(dest, exist_ok=True)
    extra = {}
    for path in glob.glob(os.path.join(DEMO, "market", "fixtures", "history-only", "*.json")):
        org = os.path.basename(path).split("-", 1)[0]
        extra.setdefault(org, []).append(load(os.path.relpath(path, DEMO)))

    def open_now(org, job):
        first, last = OPEN.get(role_id(org, job), (0, len(WEEKS) - 1))
        return first <= i <= last

    for org in FIXTURE_ORGS:
        data = load("market/fixtures/%s.json" % org)
        jobs = data if isinstance(data, list) else data["jobs"]
        jobs = [j for j in jobs + extra.get(org, []) if open_now(org, j)]
        if isinstance(data, list):
            data = jobs
        else:
            data["jobs"] = jobs
        save("%s.json" % org, data, dest)


def clean_outputs(root):
    for rel in OUTPUTS:
        path = os.path.join(root, rel)
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.exists(path):
            os.remove(path)


def run(fn, argv):
    code = fn(argv)
    if code:
        raise SystemExit("LVLme demo: %s %s failed with code %s" % (fn.__module__, argv, code))


def main():
    cur = {"evidence": load("profile/evidence.json"), "judgements": load("eval/judgements.json"),
           "profile": load("eval/profile-dimensions.json"), "plan": load("campaign/plan.json"),
           "outlook": load("eval/outlook.json")}
    tmp = tempfile.mkdtemp(prefix="lvlme-demo-")
    try:
        work = os.path.join(tmp, "demo")
        shutil.copytree(DEMO, work)
        clean_outputs(work)
        for i, week in enumerate(WEEKS[:-1]):
            for rel, doc in week_state(i, cur).items():
                save(rel, doc, work)
            fx = os.path.join(tmp, "fixtures-%s" % week)
            week_fixtures(i, fx)
            run(fetch_roles.main, ["--workspace", work, "--fixtures", fx, "--date", week])
            run(score.main, ["--workspace", work, "--date", week])
            run(build_dashboard.main, ["--workspace", work])
            if week == "2026-10-25":     # the Monday plan note for the next day, written from the data of this run
                autopilot_notes.write_note(work, json.load(open(os.path.join(work, "config.json"), encoding="utf-8")),
                                           "2026-10-26", "2026-10-26")
        clean_outputs(DEMO)
        for name in glob.glob(os.path.join(work, "campaign", "weekly", "2026-10-26.*")):
            shutil.copy2(name, os.path.join(DEMO, "campaign", "weekly", os.path.basename(name)))
        for rel in ("eval/runs", "market/roles"):
            shutil.copytree(os.path.join(work, rel), os.path.join(DEMO, rel))
        shutil.copy2(os.path.join(work, "campaign", "metrics-history.json"),
                     os.path.join(DEMO, "campaign", "metrics-history.json"))
        fx = os.path.join(tmp, "fixtures-final")
        week_fixtures(len(WEEKS) - 1, fx)
        today = WEEKS[-1]
        run(fetch_roles.main, ["--workspace", DEMO, "--fixtures", fx, "--date", today])
        run(network_map.main, ["--workspace", DEMO, "--csv", os.path.join(DEMO, "intake", "sources", "Connections.csv"),
                               "--today", today])
        run(fetch_doors.main, ["--workspace", DEMO, "--ics", os.path.join(DEMO, "market", "fixtures", "doors.ics"),
                               "--date", today])
        for door in DOORS:
            run(doors.main, ["--workspace", DEMO, "add", "--date", today] + door)
        for date, cmd, *rest in APPS:
            run(applications.main, ["--workspace", DEMO, cmd] + rest + ["--date", date])
        for date, *rest in QUESTIONS:
            run(practice.main, ["--workspace", DEMO, "record"] + rest + ["--date", date])
        for date, *rest in PUBLIC:
            run(public.main, ["--workspace", DEMO] + rest + ["--date", date])
        run(score.main, ["--workspace", DEMO, "--date", today])
        run(build_dashboard.main, ["--workspace", DEMO, "--today", today])
        cfg = json.load(open(os.path.join(DEMO, "config.json"), encoding="utf-8"))
        dash = json.load(open(os.path.join(DEMO, "report", "for-agents", "dashboard.json"), encoding="utf-8"))
        weekly.write_review(DEMO, cfg, "2026-10-30", "2026-10-30", dash)         # Friday review of the week of 26 Oct
        run(build_dashboard.main, ["--workspace", DEMO, "--today", today])
        run(proof_profile.main, ["--workspace", DEMO, "--date", "2026-11-05"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("Demo rebuilt: examples/demo-workspace/report/index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
