"""Doors: the events, programmes and communities where people from the target organisations can be met.

market/doors.json (schemas/doors.schema.json) lists each door with a date, a
place, a link and its source. A referral comes from a person, and people are
met at events and programmes, so each door says which factor it can move (warm
path D3 for meeting people, organisation-specific edge D4 for a programme) and
can become a plan action with `scripts/doors.py plan`.

Where doors come from (scripts/fetch_doors.py, the only part that fetches):
  luma_ical     a public Luma calendar's iCal feed the person named in config
  job_board     a fellowship, residency or ambassador posting already in
                market/roles/latest.json (no new fetching)
  employer_page, scout, person
                added with `scripts/doors.py add`, from the employer's own
                events page, the market scout, or the person

Never fetched: Meetup and Eventbrite pages (their terms or robots files forbid
it) and LinkedIn (LVLme never opens it). blocked() is checked before every
request. This module parses and never fetches.

Doors are progress only: score.py never reads this file. People met at a door
go into campaign/warm-paths.json when the person names them (`doors.py met`),
never by a guess.

>>> blocked("https://www.meetup.com/x/events/1"), blocked("https://lu.ma/ics/get?entity=calendar&id=cal-1")
(True, False)
"""
import datetime as dt
import html
import re

REL = "market/doors.json"
KINDS = ["event", "conference", "community", "programme"]
KIND_NAMES = {"event": "Event", "conference": "Conference", "community": "Community", "programme": "Programme"}
STATUSES = ["new", "interested", "going", "went", "applied", "skipped"]
STATUS_NAMES = {"new": "New", "interested": "Interested", "going": "Going", "went": "Went", "applied": "Applied",
                "skipped": "Skipped"}
SOURCE_KINDS = ["luma_ical", "employer_page", "job_board", "scout", "person"]
BLOCKED = re.compile(r"(^|\.)(meetup\.com|meetu\.ps|eventbrite\.[a-z.]+|evbuc\.com|linkedin\.com|lnkd\.in)$", re.I)
PROGRAMME = re.compile(r"\b(fellow(ship)?s?|residen(cy|cies|t)|ambassadors?|scholars?(hip)?|apprentice(ship)?)\b", re.I)
CONFERENCE = re.compile(r"\b(conference|summit|expo|festival|symposium|conf)\b", re.I)
COMMUNITY = re.compile(r"\b(user group|community|club)\b", re.I)
ONLINE = re.compile(r"\b(online|virtual|zoom|google meet|livestream|webinar)\b|https?://", re.I)
HORIZON_DAYS = 120
# Plan defaults for a door turned into an action: (effort hours, chance it works). Estimates; the person can change them.
DEFAULTS = {"event": (3, 0.4), "conference": (8, 0.4), "community": (2, 0.3), "programme": (6, 0.15)}
DONE_WHEN = {"event": "Name one person you spoke with there.",
             "conference": "Name one person you spoke with there.",
             "community": "You joined, and spoke or posted once.",
             "programme": "Your application is in: the confirmation email."}


def host_of(url):
    m = re.match(r"^[a-z][a-z0-9+.-]*://([^/?#:@]+)", (url or "").strip(), re.I)
    return (m.group(1) if m else "").lower()


def blocked(url):
    """True for an address LVLme must never fetch (Meetup, Eventbrite, LinkedIn)."""
    return bool(BLOCKED.search(host_of(url)))


# ------------------------------------------------------------------ iCal


def _unfold(text):
    out = []
    for line in (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line[:1] in (" ", "\t") and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return out


def _unescape(value):
    return re.sub(r"\\([\\;,nN])", lambda m: "\n" if m.group(1) in "nN" else m.group(1), value).strip()


def _when(value, params, tz_name):
    """(date, 'HH:MM' or None) in the person's time zone for an iCal DTSTART or DTEND."""
    m = re.match(r"^(\d{4})(\d{2})(\d{2})(?:T(\d{2})(\d{2})(\d{2})?(Z)?)?$", value.strip())
    if not m:
        return None, None
    y, mo, d, hh, mi, _, z = m.groups()
    day = dt.date(int(y), int(mo), int(d))
    if hh is None:
        return day.isoformat(), None
    stamp = dt.datetime(int(y), int(mo), int(d), int(hh), int(mi))
    src = "UTC" if z else (re.search(r"TZID=([^;:]+)", params or "") or [None, None])[1]
    try:
        from zoneinfo import ZoneInfo
        if src and tz_name:
            stamp = stamp.replace(tzinfo=ZoneInfo(src)).astimezone(ZoneInfo(tz_name)).replace(tzinfo=None)
    except Exception:
        pass
    return stamp.date().isoformat(), stamp.strftime("%H:%M")


def parse_ics(text, tz_name="UTC"):
    """The VEVENTs in an iCal file: uid, title, starts_on, time, ends_on, place, link, text."""
    events, cur = [], None
    for line in _unfold(text):
        if line == "BEGIN:VEVENT":
            cur = {}
        elif line == "END:VEVENT" and cur is not None:
            if cur.get("title") and cur.get("starts_on"):
                events.append(cur)
            cur = None
        elif cur is not None and ":" in line:
            head, value = line.split(":", 1)
            name, _, params = head.partition(";")
            name = name.upper()
            if name == "SUMMARY":
                cur["title"] = _unescape(value)
            elif name == "UID":
                cur["uid"] = value.strip()
            elif name == "LOCATION":
                cur["place"] = _unescape(value)
            elif name == "URL":
                cur["link"] = value.strip()
            elif name == "DESCRIPTION":
                cur["text"] = _unescape(value)
            elif name in ("DTSTART", "DTEND"):
                day, time = _when(value, params, tz_name)
                if name == "DTSTART":
                    cur["starts_on"], cur["time"] = day, time
                else:
                    cur["ends_on"] = day
    for e in events:
        if not e.get("link"):
            m = re.search(r"https://[^\s<>\"]+", e.get("text", "") + " " + e.get("place", ""))
            if m:
                e["link"] = m.group(0).rstrip(".,)")
    return events


# ------------------------------------------------------------------ matching


def _names(target):
    return [target.get("name") or target["id"]] + list(target.get("aliases") or [])


def match_orgs(text, targets):
    """Target ids whose name or an alias appears in text as whole words."""
    found = []
    for t in targets or []:
        for n in _names(t):
            if n and re.search(r"(?<![a-z0-9])" + re.escape(n) + r"(?![a-z0-9])", text or "", re.I):
                found.append(t["id"])
                break
    return found


def home_city(config):
    region = ((config or {}).get("candidate") or {}).get("home_region") or ""
    return region.split(",")[0].strip()


def kind_of(title):
    if PROGRAMME.search(title):
        return "programme"
    if CONFERENCE.search(title):
        return "conference"
    if COMMUNITY.search(title):
        return "community"
    return "event"


def why_of(kind, orgs, names, online=False):
    """The factor a door can move, and why, in plain words."""
    who = ", ".join(names.get(o, o) for o in orgs)
    if kind == "programme":
        return {"dimension": "D4", "note": ("A programme run by %s: an edge there, and people who know your work." % who)
                if who else "A programme in your field: people who know your work."}
    if kind == "community":
        return {"dimension": "D3", "note": ("A community where people from %s take part: a slow, steady warm path." % who)
                if who else "A community in your field: one member may know someone at a target."}
    if not who:
        return {"dimension": "D3", "note": "People in your field near you: one may know someone at a target."}
    return {"dimension": "D3", "note": ("Talk with people from %s online: the start of a warm path." if online
                                        else "Meet people from %s in person: the start of a warm path.") % who}


def from_ical(events, calendar, config, today, horizon=HORIZON_DAYS):
    """Doors from one calendar's events: dated today or later within the horizon, at a target or near home."""
    targets, names, city = (config or {}).get("targets") or [], _target_names(config), home_city(config)
    last = (dt.date.fromisoformat(today) + dt.timedelta(days=horizon)).isoformat()
    out = []
    for e in events:
        if not (today <= e["starts_on"] <= last):
            continue
        blob = " ".join([e.get("title", ""), e.get("text", ""), e.get("place", "")])
        orgs = match_orgs(blob, targets)
        place = e.get("place", "")
        near = bool(city) and city.lower() in place.lower()
        online = bool(ONLINE.search(place)) or not place
        if not orgs and not near:
            continue
        kind = kind_of(e["title"])
        door = {"kind": kind, "title": e["title"], "orgs": orgs, "starts_on": e["starts_on"],
                "place": "Online" if online and not near else place,
                "online": online and not near, "link": e.get("link") or calendar["url"],
                "source": calendar["url"], "source_kind": "luma_ical", "verified": True,
                "uid": "ical:" + (e.get("uid") or e["title"] + "@" + e["starts_on"]),
                "why": why_of(kind, orgs, names, online and not near)}
        for key in ("time", "ends_on"):
            if e.get(key) and not (key == "ends_on" and e[key] == e["starts_on"]):
                door[key] = e[key]
        if calendar.get("name"):
            door["note"] = "From the %s calendar." % calendar["name"]
        out.append(door)
    return out


def from_roles(roles_doc, config):
    """Programme doors from fellowship, residency and ambassador postings already fetched. No new fetching."""
    names, out = _target_names(config), []
    rows = list((roles_doc or {}).get("roles") or []) + list((roles_doc or {}).get("excluded") or [])
    for r in rows:
        if not (r.get("title") and r.get("url") and PROGRAMME.search(r["title"])):
            continue
        orgs = [r["org"]] if r.get("org") else []
        door = {"kind": "programme", "title": r["title"], "orgs": orgs, "place": ", ".join(r.get("locations") or [])
                or "See the posting", "online": bool(r.get("remote")), "link": r["url"], "source": r["url"],
                "source_kind": "job_board", "verified": True, "uid": "role:" + (r.get("id") or r["url"]),
                "why": why_of("programme", orgs, names)}
        out.append(door)
    return out


def _target_names(config):
    return {t["id"]: t.get("name", t["id"]) for t in (config or {}).get("targets") or []}


# ------------------------------------------------------------------ the file


def empty():
    return {"schema_version": 1, "doors": []}


def next_id(doc):
    n = max([int(d["id"][2:]) for d in doc.get("doors") or [] if re.match(r"^DR\d+$", d.get("id", ""))] or [0])
    return "DR%02d" % (n + 1)


def merge(doc, found, today):
    """Add new doors and refresh the facts of known ones (same uid or link); the person's status, action and notes stay."""
    doc = doc or empty()
    doors = doc.setdefault("doors", [])
    by_key = {}
    for d in doors:
        for k in (d.get("uid"), d.get("link")):
            if k:
                by_key.setdefault(k, d)
    added = refreshed = 0
    for f in found:
        old = by_key.get(f.get("uid")) or by_key.get(f.get("link"))
        if old:
            for key in ("title", "starts_on", "time", "ends_on", "place", "online", "link", "orgs", "source"):
                if key in f:
                    old[key] = f[key]
            old["seen_on"] = today
            refreshed += 1
            continue
        door = {"id": next_id(doc)}
        door.update(f)
        door.update(seen_on=today, status="new", done_when=DONE_WHEN[f["kind"]])
        doors.append(door)
        for k in (door.get("uid"), door.get("link")):
            if k:
                by_key.setdefault(k, door)
        added += 1
    doc["updated_on"] = max(doc.get("updated_on") or today, today)
    return doc, added, refreshed


def date_of(door):
    return door.get("starts_on") or door.get("closes_on") or ""


def upcoming(doc, today):
    """Doors still open to the person: not skipped, and dated today or later (or undated), soonest first."""
    rows = [d for d in (doc or {}).get("doors") or []
            if d.get("status") != "skipped" and (not date_of(d) or date_of(d) >= today or d.get("ends_on", "") >= today)]
    return sorted(rows, key=lambda d: (date_of(d) or "9999-99-99", d.get("id", "")))


def next_door(doc, today, names):
    """For the weekly note: the soonest dated door at a target, else the soonest dated door, or None."""
    dated = [d for d in upcoming(doc, today) if d.get("starts_on") and d.get("status") not in ("went", "skipped")]
    pick = next((d for d in dated if d.get("orgs")), dated[0] if dated else None)
    if not pick:
        return None
    return {"org": ", ".join(names.get(o, o) for o in pick.get("orgs") or []) or "near you",
            "text": "%s, %s" % (pick["title"], when_text(pick)), "source": pick.get("link") or pick["source"],
            "seen_on": pick.get("seen_on", ""), "id": pick["id"]}


def when_text(door):
    day = date_of(door)
    if not day:
        return "Open now"
    d = dt.date.fromisoformat(day)
    text = "%s %d %s" % (d.strftime("%a"), d.day, d.strftime("%b"))
    if door.get("closes_on") and not door.get("starts_on"):
        return "Closes " + text
    if door.get("time"):
        h, m = (int(x) for x in door["time"].split(":"))
        text += ", %d%s%s" % (h % 12 or 12, ":%02d" % m if m else "", "am" if h < 12 else "pm")
    return text


# ------------------------------------------------------------------ to a plan action


def action_for(door, plan, config, roles_doc, today):
    """A plan action for one door: the factor it can move, its date and a done-when the person can show."""
    kind = door["kind"]
    dim = (door.get("why") or {}).get("dimension") or ("D4" if kind == "programme" else "D3")
    weight = ((config.get("scoring") or {}).get("weights") or {}).get(dim) or {"D3": 20, "D4": 10}.get(dim, 10)
    orgs = list(door.get("orgs") or [])
    roles = [r for r in (roles_doc or {}).get("roles") or [] if not orgs or r.get("org") in orgs]
    effort, chance = DEFAULTS[kind]
    n = max([int(a["id"][1:]) for a in (plan or {}).get("actions") or [] if re.match(r"^A\d+$", a.get("id", ""))]
            or [0]) + 1
    verb = "Apply to" if kind == "programme" else "Join" if kind == "community" else "Go to"
    action = {"id": "A%02d" % n, "title": "%s %s" % (verb, door["title"]), "why": (door.get("why") or {}).get("note", ""),
              "status": "todo", "owner": "you", "dimension": dim, "orgs": orgs or "all", "effort_hours": effort,
              "expected_points": round(weight / 5.0, 1), "roles_affected": len(roles), "chance": chance,
              "done_when": door.get("done_when") or DONE_WHEN[kind], "added_on": today,
              "effects": [{"dimension": dim, "delta": 1, "scope": {"orgs": orgs} if orgs else {},
                           "note": "From door %s. Effort and chance are first estimates: change them if you know better."
                           % door["id"]}],
              "notes": "Door %s (%s)." % (door["id"], door.get("link") or door.get("source"))}
    if date_of(door) and date_of(door) >= today:
        action["target_date"] = date_of(door)
    return action


# ------------------------------------------------------------------ for the dashboard and agents


def page_data(doc, today, names, limit=6):
    rows = upcoming(doc, today)
    out = []
    for d in rows[:limit]:
        out.append({"id": d["id"], "kind": KIND_NAMES.get(d["kind"], d["kind"]), "title": d["title"],
                    "when": when_text(d), "date": date_of(d), "place": d.get("place") or "",
                    "orgs": [names.get(o, o) for o in d.get("orgs") or []],
                    "why": (d.get("why") or {}).get("note", ""), "dimension": (d.get("why") or {}).get("dimension", ""),
                    "status": d.get("status", "new"), "status_name": STATUS_NAMES.get(d.get("status", "new"), ""),
                    "link": d.get("link") or d.get("source"), "source": d.get("source"), "action": d.get("action"),
                    "verified": bool(d.get("verified"))})
    if not out:
        return None
    return {"rows": out, "total": len(rows), "more": max(0, len(rows) - limit)}


NOTE = "Progress only: doors change no score. You register, RSVP or apply yourself."


def static_html(doors):
    """The static summary's Doors table."""
    if not doors:
        return ""
    rows = "".join('<tr><th scope="row">%s</th><td>%s</td><td>%s</td><td>%s</td></tr>' % (
        html.escape(r["title"] + (", " + ", ".join(r["orgs"]) if r["orgs"] else "")), html.escape(r["when"]),
        html.escape(r["place"] or "Not given"), html.escape(r["why"])) for r in doors["rows"])
    return ('<h3 id="staticDoorsH">Doors</h3><p class="small sub">%s</p>'
            '<table aria-labelledby="staticDoorsH"><thead><tr><th scope="col">Door</th><th scope="col">When</th>'
            '<th scope="col">Where</th><th scope="col">Why</th></tr></thead><tbody>%s</tbody></table>'
            ) % (html.escape(NOTE), rows)


def summary_lines(doors):
    if not doors:
        return []
    lines = ["", "## Doors (market/doors.json)", "",
             "%d upcoming. Progress only: score.py never reads doors. Turn one into a plan action with "
             "`python3 scripts/doors.py plan <id>` on the person's yes." % doors["total"], ""]
    for r in doors["rows"]:
        lines.append("- %s %s: %s, %s, %s%s. %s Source: %s%s" % (
            r["id"], r["kind"], r["title"], r["when"], r["place"] or "place not given",
            " (" + ", ".join(r["orgs"]) + ")" if r["orgs"] else "", r["why"], r["source"],
            "" if r["verified"] else " (UNVERIFIED)"))
    return lines


def checks(doc, target_ids, action_ids, errors, warnings):
    """Cross-file checks for validate.py: unique ids, known targets and plan actions, dates in order."""
    seen = set()
    for d in (doc or {}).get("doors") or []:
        where = "%s %s" % (REL, d.get("id"))
        if d.get("id") in seen:
            errors.append("%s: the id is used twice" % where)
        seen.add(d.get("id"))
        for o in d.get("orgs") or []:
            if target_ids and o not in target_ids:
                warnings.append("%s: org %r is not a target in config.json" % (where, o))
        if d.get("action") and action_ids is not None and d["action"] not in action_ids:
            errors.append("%s: action %s is not in campaign/plan.json" % (where, d["action"]))
        if d.get("ends_on") and d.get("starts_on") and d["ends_on"] < d["starts_on"]:
            errors.append("%s: ends_on is before starts_on" % where)
        if d.get("kind") != "programme" and d.get("kind") != "community" and not d.get("starts_on"):
            warnings.append("%s: this %s has no date, so it cannot be planned for" % (where, d.get("kind")))
        if not d.get("verified") and d.get("source_kind") in ("scout",):
            warnings.append("%s: from a helper and not yet opened by the lead (check, do not relay)" % where)
