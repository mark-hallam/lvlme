"""Research packs: one page per target organisation, for before a coffee chat or an application.

Built only from what the workspace already holds, so it fetches nothing:
market/orgs.json (the market scout's sourced facts), market/roles/latest.json
(what the job boards list), market/doors.json (events and programmes) and the
target's ai_policy in config.json. Every line carries its source and the date
it was seen. A fact the lead has not opened itself (verified is not true) says
"Not yet checked" (hard rule 7: check, do not relay).

Facts about organisations only: nothing about named employees beyond what the
person asked for. Written by build_dashboard.py to report/research/<org>.html.
No network calls here.
"""
import html

import _ai_policies as AIP
import _common as C
import _doors as DR
import _page_html as PH

FOLDER = ("report", "research")
SECTIONS = [("building", "What it is building"), ("news", "Recent news"), ("offices", "Offices"),
            ("hiring", "Teams hiring"), ("doors", "Events and programmes"), ("ai", "Its rules on AI for candidates"),
            ("eligibility", "Eligibility"), ("other", "Other facts")]
KIND_SECTION = {"building": "building", "news": "news", "office": "offices", "team_growth": "hiring",
                "hiring_signal": "hiring", "event": "doors", "partner_programme": "doors", "eligibility": "eligibility",
                "other": "other"}
NOTE = ("Built from the facts LVLme already holds, each with its source and the date it was seen. Lines marked "
        "\"Not yet checked\" came from a search and nobody has opened the source yet: open it before you repeat it.")


def line(text, source, seen_on, checked, said="seen"):
    return {"text": text, "source": source, "seen_on": seen_on, "checked": bool(checked), "said": said}


def hiring_lines(org, roles_doc, fam_names):
    roles = [r for r in (roles_doc or {}).get("roles") or [] if r.get("org") == org]
    if not roles:
        return []
    fetched, teams = roles_doc.get("fetched_on"), {}
    for r in roles:
        teams.setdefault(r.get("team_or_department") or fam_names.get(r.get("family"), "Other"), []).append(r)
    out = [line("%d open role%s matching your role types." % (len(roles), "" if len(roles) == 1 else "s"),
                "market/roles/latest.json (the employer's own job board)", fetched, True)]
    for team, rs in sorted(teams.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        places = sorted({p for r in rs for p in r.get("locations") or []})
        out.append(line("%s: %s%s." % (team, "; ".join(r["title"] for r in rs),
                                       " (%s)" % ", ".join(places[:4]) if places else ""),
                        rs[0].get("url") or "market/roles/latest.json", fetched, True))
    return out


def door_lines(org, doors_doc, today):
    out = []
    for d in DR.upcoming(doors_doc, today):
        if org in (d.get("orgs") or []):
            out.append(line("%s: %s, %s%s." % (DR.KIND_NAMES.get(d["kind"], d["kind"]), d["title"], DR.when_text(d),
                                               ", " + d["place"] if d.get("place") else ""),
                            d.get("source") or d.get("link"), d.get("seen_on"), d.get("verified")))
    return out


def ai_lines(target):
    policy = target.get("ai_policy") or AIP.policy_for(target.get("id"), target.get("name"))
    if not policy:
        return [line("No published rules on candidates' use of AI on record. Check its careers page before you "
                     "use AI on an application.", "config.json (ai_policy)", None, True)]
    said = AIP.first_draft_line(target.get("name"), policy) or "Its published rules are at the source."
    return [line(said, policy.get("source"), policy.get("checked_on"), True)]


def pack(target, config, orgs_doc, roles_doc, doors_doc, today):
    """{"org", "name", "sections": [(title, [line])], "unchecked"} for one target."""
    org = target["id"]
    info = ((orgs_doc or {}).get("orgs") or {}).get(org) or {}
    found = {key: [] for key, _ in SECTIONS}
    for f in info.get("facts") or []:
        found[KIND_SECTION.get(f.get("kind"), "other")].append(
            line(f["text"], f["source"], f.get("published_on") or f.get("seen_on"), f.get("verified"),
                 "published" if f.get("published_on") else "seen"))
    found["news"].sort(key=lambda x: x["seen_on"] or "", reverse=True)
    if info.get("offices"):
        found["offices"].insert(0, line(", ".join(info["offices"]) + ".", "market/orgs.json",
                                        (orgs_doc or {}).get("updated_on"), False))
    found["hiring"] = hiring_lines(org, roles_doc, C.family_names(config)) + found["hiring"]
    found["doors"] = door_lines(org, doors_doc, today) + found["doors"]
    found["ai"] = ai_lines(target)
    sections = [(title, found[key]) for key, title in SECTIONS if found[key]]
    return {"org": org, "name": target.get("name") or org, "sections": sections,
            "unchecked": sum(1 for _, ls in sections for x in ls if not x["checked"])}


def render(p, today, fictional=False):
    def src(x):
        s = x["source"] or ""
        link = ('<a href="%s" target="_blank" rel="noopener noreferrer">source</a>' % PH.esc(s)
                if s.startswith("https://") else PH.esc(s))
        return "%s%s" % (link, ", %s %s" % (x["said"], PH.esc(PH.long_date(x["seen_on"]))) if x["seen_on"] else "")
    cards = "".join(
        '<section class="card"><h2>%s</h2><ul class="rows">%s</ul></section>' % (PH.esc(title), "".join(
            '<li><div class="row-h"><h3 style="font-weight:500">%s</h3>%s</div><p class="tiny sub">%s</p></li>' % (
                PH.esc(x["text"]), "" if x["checked"] else PH.chip("Not yet checked", "s"), src(x))
            for x in lines)) for title, lines in p["sections"])
    demo = '<span class="sep"> · </span><span class="nw">fictional demo</span>' if fictional else ""
    head = ('<section class="card"><div class="eyebrow">Research pack</div><h1>%s</h1><p class="small sub">%s</p>%s</section>'
            % (PH.esc(p["name"]), PH.esc(NOTE), '<p class="small">%d line%s not yet checked.</p>' % (
                p["unchecked"], "" if p["unchecked"] == 1 else "s") if p["unchecked"] else ""))
    return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<meta name=\"color-scheme\" content=\"light dark\">"
            "<title>LVLme research pack: %s</title><style>%s</style></head><body><div class=\"wrap\">"
            "<header class=\"top\"><span class=\"mark\">%s</span><b>LVLme</b>"
            "<span class=\"sub\"><span class=\"nw\">%s</span>%s</span></header><main>%s%s</main>"
            "<footer><a href=\"../index.html\">Back to the dashboard</a>. Public sources only; nothing about named "
            "people.</footer></div></body></html>\n" % (
                PH.esc(p["name"]), PH.CSS, PH.LOGO, PH.esc(PH.long_date(today)), demo, head, cards))


def write_all(ws, config, orgs_doc, roles_doc, doors_doc, today):
    """Write one page per target; returns {org id: path relative to report/}."""
    out = {}
    for t in config.get("targets") or []:
        p = pack(t, config, orgs_doc, roles_doc, doors_doc, today)
        C.write_text(C.wpath(ws, *FOLDER, "%s.html" % t["id"]), render(p, today, config.get("fictional") is True))
        out[t["id"]] = {"path": "research/%s.html" % t["id"], "unchecked": p["unchecked"],
                        "lines": sum(len(ls) for _, ls in p["sections"])}
    return out


def summary_lines(packs, names):
    if not packs:
        return []
    return ["", "## Research packs (one page per target, every line sourced)"] + [
        "- %s: report/%s (%d lines, %d not yet checked)." % (names.get(o, o), p["path"], p["lines"], p["unchecked"])
        for o, p in packs.items()]
