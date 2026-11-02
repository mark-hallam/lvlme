"""The warm-path tracker: how far each contact at a target organisation has come.

campaign/warm-paths.json (schemas/warm-paths.schema.json) gives each contact the
person is warming up one stage on a fixed ladder:

  followed         you follow their work; they may not know you yet (a LinkedIn
                   connection you have never spoken with is here too)
  talked           a real exchange: a reply, a call, a chat at an event
  connected        a two-way line: they would recognise your name and reply
  knows_your_work  they have seen something you made or did
  would_refer      they have said they would refer you, or introduce you to the
                   hiring manager

Progress only. score.py never reads the file, so it changes no score: the warm
path factor (D3) is judged from evidence against the rubric's anchors, and a
tracker stage is the person's own account. This module summarises the file for
the dashboard (a small strip per organisation under Do next, and the contacts in
the organisation pane), the static summary, the agent briefing (SUMMARY.md and
dashboard.json) and validate.py's cross-file checks.

>>> per_org({"contacts": [{"org": "acme", "stage": "talked"}]}, ["acme"])["acme"]["furthest"]
'talked'
"""
import html

STAGES = ["followed", "talked", "connected", "knows_your_work", "would_refer"]
STAGE_NAMES = {"followed": "Followed", "talked": "Talked", "connected": "Connected",
               "knows_your_work": "Knows your work", "would_refer": "Would refer"}
NOTE = "Progress only: it changes no score. Your warm path score moves when the evidence does."
REL = "campaign/warm-paths.json"


def rank(stage):
    return STAGES.index(stage)


def contacts_of(doc):
    """The contacts with a known stage, as recorded."""
    return [c for c in ((doc or {}).get("contacts") or []) if isinstance(c, dict) and c.get("stage") in STAGES]


def per_org(doc, targets):
    """{target: {"people", "furthest" (a stage or None), "by_stage" {stage: count}}}, in target order.
    Contacts at an organisation that is not a target are left out (validate.py warns about them)."""
    out = {t: {"people": 0, "furthest": None, "by_stage": {s: 0 for s in STAGES}} for t in targets}
    for c in contacts_of(doc):
        o = out.get(c.get("org"))
        if o is None:
            continue
        o["people"] += 1
        o["by_stage"][c["stage"]] += 1
        if o["furthest"] is None or rank(c["stage"]) > rank(o["furthest"]):
            o["furthest"] = c["stage"]
    return out


def ordered_contacts(doc, targets):
    """Contacts at targets: in target order, furthest stage first, then by id."""
    order = {t: i for i, t in enumerate(targets)}
    return sorted((c for c in contacts_of(doc) if c.get("org") in order),
                  key=lambda c: (order[c["org"]], -rank(c["stage"]), c.get("id") or ""))


def person_names(doc):
    """Every recorded name, so the dashboard and the agent files can hide them like network names."""
    return {c["person"].strip() for c in (doc or {}).get("contacts") or []
            if isinstance(c, dict) and isinstance(c.get("person"), str) and len(c["person"].strip()) >= 2}


def people(n):
    return "%d %s" % (n, "person" if n == 1 else "people")


def stage_counts_text(by_stage):
    """'1 followed, 1 connected', furthest stage last."""
    return ", ".join("%d %s" % (by_stage[s], STAGE_NAMES[s].lower()) for s in STAGES if by_stage.get(s))


def org_line(name, stats):
    """One plain line per organisation, for the briefing and the static summary."""
    if not stats["people"]:
        return "%s: no one yet" % name
    return "%s: furthest %s; %s (%s)" % (name, STAGE_NAMES[stats["furthest"]], people(stats["people"]),
                                        stage_counts_text(stats["by_stage"]))

# ------------------------------------------------------------------ dashboard


def page_data(doc, targets, org_names, group_of, clean):
    """The page's D.warm: one strip per target organisation, and the contacts for the organisation pane."""
    stats = per_org(doc, targets)
    return {
        "stages": [STAGE_NAMES[s] for s in STAGES], "note": NOTE, "tracked": doc is not None,
        "orgs": [{"id": t, "g": group_of.get(t, t), "name": org_names.get(t, t), "people": s["people"],
                  "furthest": rank(s["furthest"]) if s["furthest"] else -1,
                  "counts": [s["by_stage"][x] for x in STAGES]} for t, s in stats.items()],
        "contacts": [{"org": c["org"], "who": clean(c.get("person")), "role": clean(c.get("role")),
                      "stage": rank(c["stage"]), "since": c.get("updated_on") or "", "next": clean(c.get("next_step"))}
                     for c in ordered_contacts(doc, targets)],
    }


def static_html(warm):
    """The static summary's Warm paths table (page data already has names hidden)."""
    if not warm or not warm["orgs"]:
        return ""
    rows = []
    for o in warm["orgs"]:
        furthest = warm["stages"][o["furthest"]] if o["furthest"] >= 0 else "No one yet"
        counts = ", ".join("%d %s" % (n, warm["stages"][i].lower()) for i, n in enumerate(o["counts"]) if n)
        rows.append('<tr><th scope="row">%s</th><td>%s</td><td>%s</td></tr>' % (
            html.escape(o["name"]), html.escape(furthest), html.escape(counts or "None tracked")))
    return ('<h3 id="staticWarmH">Warm paths</h3><p class="small sub">%s</p>'
            '<table aria-labelledby="staticWarmH"><thead><tr><th scope="col">Organisation</th>'
            '<th scope="col">Furthest stage</th><th scope="col">People at each stage</th></tr></thead>'
            '<tbody>%s</tbody></table>') % (html.escape(NOTE), "".join(rows))

# ------------------------------------------------------------- agent files


def agent_data(doc, targets, org_names, include_contacts):
    """dashboard.json's warm_paths block. Contacts are left out in sensitive mode; names are scrubbed later."""
    stats = per_org(doc, targets)
    out = {
        "about": "Progress only: score.py never reads campaign/warm-paths.json, so it changes no score. "
                 "The warm path factor (D3) is judged from evidence.",
        "stages": STAGES,
        "per_org": {t: {"org_name": org_names.get(t, t), "people": s["people"], "furthest_stage": s["furthest"],
                        "by_stage": s["by_stage"]} for t, s in stats.items()},
    }
    if include_contacts:
        out["contacts"] = [{k: c[k] for k in ("id", "org", "person", "role", "stage", "updated_on", "next_step", "action")
                            if c.get(k)} for c in ordered_contacts(doc, targets)]
    return out


def summary_lines(wp, org_name):
    """SUMMARY.md's Warm paths section, from the (already scrubbed) dashboard.json block."""
    lines = ["", "## Warm paths (progress only: changes no score; the warm path factor moves only with evidence)",
             "- Stages, in order: %s." % ", ".join(STAGE_NAMES[s].lower() for s in STAGES)]
    contacts = wp.get("contacts")
    for oid, s in wp["per_org"].items():
        lines.append("- " + org_line(org_name(oid), {"people": s["people"], "furthest": s["furthest_stage"],
                                                     "by_stage": s["by_stage"]}))
        for c in [c for c in contacts or [] if c["org"] == oid]:
            lines.append("  - %s%s: %s, updated %s.%s" % (
                c["person"], " (%s)" % c["role"] if c.get("role") else "", STAGE_NAMES[c["stage"]], c["updated_on"],
                " Next: %s" % c["next_step"] if c.get("next_step") else ""))
    if contacts is None:
        lines.append("- Contacts are left out in sensitive mode.")
    lines += ["- When the person says a contact has moved on, the agent running the campaign sets stage and updated_on and",
              "  adds a history entry in %s. Any other agent appends the message to campaign/inbox.md." % REL]
    return lines

# ------------------------------------------------------------------ checks


def checks(doc, targets, ev_ids, action_ids, errors, warnings):
    """validate.py's cross-file checks for campaign/warm-paths.json (the schema is checked separately)."""
    if doc is None:
        return
    where = REL + ": "
    seen, people_at = set(), set()
    for c in doc.get("contacts") or []:
        if not isinstance(c, dict):
            continue
        cid, org, stage = c.get("id"), c.get("org"), c.get("stage")
        if cid in seen:
            errors.append(where + "duplicate contact id %s" % cid)
        seen.add(cid)
        key = (org, (c.get("person") or "").strip().lower())
        if key in people_at:
            warnings.append(where + "%s is a second entry for the same person at %s (keep one per person)" % (cid, org))
        people_at.add(key)
        if targets and org not in targets:
            warnings.append(where + "%s is at %s, not a current target (it is left off the dashboard)" % (cid, org))
        for eid in c.get("evidence") or []:
            if eid not in ev_ids:
                errors.append(where + "%s cites evidence %s, which is not in profile/evidence.json" % (cid, eid))
        if c.get("action") and action_ids is not None and c["action"] not in action_ids:
            errors.append(where + "%s names action %s, which is not in campaign/plan.json" % (cid, c["action"]))
        history_checks(where + str(cid), c, warnings)
        if stage == "would_refer" and not c.get("evidence"):
            warnings.append(where + "%s would refer, with no evidence cited. The tracker changes no score: the warm path "
                            "factor counts an agreed referral once their own words are in profile/evidence.json" % cid)


def history_checks(where, c, warnings):
    hist = [h for h in c.get("history") or [] if isinstance(h, dict)]
    if not hist:
        return
    dates = [h.get("on") or "" for h in hist]
    if dates != sorted(dates):
        warnings.append("%s: history is not oldest first" % where)
    if hist[-1].get("stage") != c.get("stage"):
        warnings.append("%s: stage is %s, but the latest history entry says %s" % (where, c.get("stage"), hist[-1].get("stage")))
    if c.get("updated_on") and max(dates) > c["updated_on"]:
        warnings.append("%s: updated_on %s is earlier than the latest history entry (%s)" % (where, c["updated_on"], max(dates)))
