"""Is this job still open, and is it a real opening? Age and repost checks for each open role.

Some job ads never lead to a hire. LVLme does not guess which: it says what it
saw and when. Each open role in market/roles/latest.json gets a
`posting_check`:

    {"label": "likely_real" | "check_first" | "suspicious",
     "note": "Open, but posted 14 months ago", "age_days": 425, "reposts": 0}

- Age comes from the board's own date. Greenhouse gives first_published and
  Lever createdAt (the first posting); Ashby's publishedAt resets when a job
  is republished, so it is read as "last published".
- A repost is career-ops' rule: two or more different links for the same
  exact title words at the same organisation, seen on two or more scan dates
  within 90 days.
- With no date the label is check_first, never suspicious.

A role that has gone from a board that answered is closed (fetch_roles.py
lists it in closed_role_ids); a role on a board that failed is never called
closed. The checks never change a score: they only lower the priority of a
plan action whose roles all look suspicious, and they label the role.
No network calls here.
"""
import datetime as dt
import re

WINDOW_DAYS = 90
OLD_DAYS = 90         # older than this: check first
STALE_DAYS = 365      # older than this: suspicious
REPOSTS_SUSPICIOUS = 2
LAST_PUBLISHED = {"ashby"}  # boards whose date resets on republishing
LABELS = ("likely_real", "check_first", "suspicious")


def title_key(org, title):
    """Same organisation, same exact title words (case and punctuation aside)."""
    return org, " ".join(re.findall(r"[a-z0-9]+", (title or "").lower()))


def age_days(published, today):
    """Whole days since an ISO date or timestamp, or None when there is no usable date."""
    try:
        return (dt.date.fromisoformat(today) - dt.date.fromisoformat(str(published)[:10])).days
    except (TypeError, ValueError):
        return None


def months(days):
    n = max(1, round(days / 30.44))
    return "%d month%s" % (n, "" if n == 1 else "s")


def repost_counts(history, today):
    """{(org, title words): (distinct role ids, distinct scan dates)} over the last 90 days of snapshots.

    history: [(date, {role id: {"org", "title", ...}})], today's included.
    """
    seen = {}
    for date, roles in history:
        d = age_days(date, today)
        if d is None or d < 0 or d > WINDOW_DAYS:
            continue
        for rid, r in roles.items():
            ids, dates = seen.setdefault(title_key(r.get("org"), r.get("title")), (set(), set()))
            ids.add(rid)
            dates.add(date)
    return seen


def check(role, seen, today, ats=None):
    """The posting_check for one role."""
    age = age_days(role.get("published_at"), today)
    ids, dates = seen.get(title_key(role.get("org"), role.get("title")), (set(), set()))
    reposts = len(ids) - 1 if len(ids) >= 2 and len(dates) >= 2 else 0
    when = "last published" if ats in LAST_PUBLISHED else "posted"
    if reposts >= REPOSTS_SUSPICIOUS or (age is not None and age >= STALE_DAYS):
        label = "suspicious"
    elif age is None or reposts == 1 or age >= OLD_DAYS:
        label = "check_first"
    else:
        label = "likely_real"
    parts = []
    if reposts:
        parts.append("reposted %d time%s in %d days" % (reposts, "" if reposts == 1 else "s", WINDOW_DAYS))
    if age is None:
        parts.append("the board gives no date")
    elif age >= OLD_DAYS:
        parts.append("%s %s ago" % (when, months(age)))
    note = "Open" + (", but " + " and ".join(parts) if parts else "")
    return {"label": label, "note": note, "age_days": age, "reposts": reposts}


def apply_checks(roles, history, today, ats_of):
    """Add posting_check to every role. ats_of: {org id: board name}. Returns counts per label."""
    seen = repost_counts(history, today)
    counts = dict.fromkeys(LABELS, 0)
    for r in roles:
        r["posting_check"] = check(r, seen, today, ats_of.get(r.get("org")))
        counts[r["posting_check"]["label"]] += 1
    return counts


def suspicious_ids(roles_doc):
    return {r["id"] for r in (roles_doc or {}).get("roles", [])
            if (r.get("posting_check") or {}).get("label") == "suspicious"}


def action_role_ids(action):
    """Every role id a plan action names, in its own scope or its effects' scopes."""
    ids = list((action.get("scope") or {}).get("role_ids") or [])
    for e in action.get("effects") or []:
        ids += (e.get("scope") or {}).get("role_ids") or []
    return ids


def only_suspicious(action, suspicious):
    """True when an action names roles and every one of them looks suspicious."""
    ids = action_role_ids(action)
    return bool(ids) and all(i in suspicious for i in ids)
