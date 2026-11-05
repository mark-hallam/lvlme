"""Workday, SmartRecruiters and Workable postings, read by the campaign.

Each reader turns one posting from a board's public API answer into the
posting shape fetch_roles.py builds a role from (`_base`). fetch_roles.py uses
them for every matching posting on a target's board. No network calls here:
fetch_roles.py fetches the answers and passes them in.
"""
import html
import re

import urllib.parse

import _html_text as T

WORKDAY_HOST = re.compile(r"^([a-z0-9][a-z0-9-]*)\.(wd\d+)\.myworkdayjobs\.com$")
LANG = re.compile(r"^[a-z]{2}(-[a-z]{2})?$", re.I)
LISTED = ("workday", "smartrecruiters", "workable")  # boards whose job list holds titles only, not the postings
PAGE = {"workday": 20, "smartrecruiters": 100, "workable": 100}  # the most each list gives per request
MAX_LISTED = 3000  # a board this big is read in part, and the summary says so
BOARD_NAMES = {"greenhouse": "Greenhouse", "ashby": "Ashby", "lever": "Lever", "workday": "Workday",
               "smartrecruiters": "SmartRecruiters", "workable": "Workable"}
WORKABLE_PLACES = {"remote": "Remote", "hybrid": "Hybrid", "on_site": "Onsite", "onsite": "Onsite"}
SR_SECTIONS = ("jobDescription", "qualifications", "additionalInformation")  # the employer's welcome goes last


def nice_name(board):
    return " ".join(w.capitalize() for w in re.split(r"[-_\s]+", board or "") if w) or "The employer"


def workday_org_name(tenant, *texts):
    """The organisation's everyday name for a Workday board.

    Workday lists the legal entity that hires ("2100 Example Corp USA", "Example
    Australia Pty Ltd"), not the name people know. The board's own name (the first
    part of the link) is the everyday one: it is written the way the posting
    writes it most often ("ACME" or "Acme"), else in capitals at the start.
    """
    if not tenant:
        return nice_name(tenant)
    word = re.compile(r"\b%s\b" % re.escape(tenant), re.I)
    seen = {}
    for text in texts:
        for m in word.finditer(T.clean(text) if text else ""):
            if m.group(0) != m.group(0).lower():  # "acme" in a web address is not how the name is written
                seen[m.group(0)] = seen.get(m.group(0), 0) + 1
    return max(seen, key=seen.get) if seen else nice_name(tenant)


def workday_base(link, data):
    """One posting from a Workday job feed response ({"jobPostingInfo": ...}), or None."""
    job = data.get("jobPostingInfo") if isinstance(data, dict) else None
    if not isinstance(job, dict) or not job.get("jobDescription"):
        return None
    legal = (data.get("hiringOrganization") or {}).get("name") if isinstance(data.get("hiringOrganization"), dict) else None
    locs = [job.get("location")] + list(job.get("additionalLocations") or [])
    published = job.get("startDate") if re.match(r"^\d{4}-\d{2}-\d{2}$", str(job.get("startDate") or "")) else None
    title = T.clean(job.get("title") or "")
    base = _base(str(job.get("jobReqId") or job.get("jobPostingId") or link["job_id"]), title,
                 [str(l) for l in locs if l], job.get("externalUrl") or None, job["jobDescription"],
                 workday_org_name(link["board"], legal, title, job["jobDescription"]), published=published)
    base["workplace_type"] = job.get("remoteType") or None
    return base


def smartrecruiters_base(link, data):
    """One posting from a SmartRecruiters posting API response ({"name", "jobAd": {"sections"}, ...}), or None.

    The sections come in the order a reader needs them: the job description,
    the qualifications and any additional information, then the employer's
    welcome under "About <organisation>", so a greeting is never read as a
    requirement.
    """
    if not isinstance(data, dict) or data.get("active") is False:
        return None
    sections = ((data.get("jobAd") or {}).get("sections") or {}) if isinstance(data.get("jobAd"), dict) else {}
    sections = sections if isinstance(sections, dict) else {}
    company = data.get("company") if isinstance(data.get("company"), dict) else {}
    org_name = T.clean(company.get("name") or "") or nice_name(link["board"])
    parts = []
    for key in SR_SECTIONS:
        sec = sections.get(key) if isinstance(sections.get(key), dict) else {}
        if T.clean(re.sub(r"<[^>]+>", " ", sec.get("text") or "")):
            parts.append("<h2>%s</h2>%s" % (html.escape(sec.get("title") or key), sec["text"]))
    welcome = sections.get("companyDescription") if isinstance(sections.get("companyDescription"), dict) else {}
    if not parts:  # some employers put the whole posting under the company description
        if not T.clean(re.sub(r"<[^>]+>", " ", welcome.get("text") or "")):
            return None
        parts, welcome = [welcome["text"]], {}
    lines = [text for _, text, _ in T.blocks_of(welcome.get("text") or "", skip_boilerplate=False)]
    if lines:  # plain paragraphs, so a bold welcome line is never taken for a requirements heading
        parts.append("<h2>About %s</h2>%s" % (html.escape(org_name),
                                               "".join("<p>%s</p>" % html.escape(t.rstrip(":")) for t in lines)))
    loc = data.get("location") if isinstance(data.get("location"), dict) else {}
    where = ", ".join(p for p in (T.clean(x) for x in str(loc.get("fullLocation") or ", ".join(
        str(loc[k]) for k in ("city", "region", "country") if loc.get(k))).split(",")) if p)  # "Sydney, , Australia"
    workplace = "Remote" if loc.get("remote") is True else "Hybrid" if loc.get("hybrid") is True else (
        "Onsite" if loc.get("remote") is False else None)
    released = str(data.get("releasedDate") or "")[:10]
    base = _base(str(data.get("id") or link["job_id"]), T.clean(data.get("name") or ""),
                 [where] if where else [], data.get("postingUrl") or None, "".join(parts), org_name,
                 published=released if re.match(r"^\d{4}-\d{2}-\d{2}$", released) else None)
    dept = data.get("department") if isinstance(data.get("department"), dict) else {}
    if dept.get("label"):
        base["depts"], base["team_or_department"] = [dept["label"]], dept["label"]
    base["workplace_type"], base["is_remote"] = workplace, loc.get("remote") if workplace else None
    return base


def workable_base(link, data):
    """One posting from a Workable job feed response ({"title", "description", "requirements", "benefits", ...}), or None.

    Workable keeps the requirements and the benefits in their own fields, often
    with no heading of their own, so each gets its heading here: the
    requirements are read as requirements, and the benefits come last, where
    they are never read as one. The feed does not name the organisation, so
    the name is the account's (see workable_org_name), until fetch() asks
    the account feed for the name it gives itself.
    """
    if not isinstance(data, dict) or str(data.get("state") or "published") != "published":
        return None
    parts = []
    for key, heading in (("description", None), ("requirements", "Requirements"), ("benefits", "Benefits")):
        text = data.get(key) if isinstance(data.get(key), str) else ""
        if T.clean(re.sub(r"<[^>]+>", " ", text)):
            parts.append(("<h2>%s</h2>" % heading if heading else "") + text)
    if not parts:
        return None
    places = [data.get("location")] + list(data.get("locations") or [])
    where = [", ".join(T.clean(str(p[k])) for k in ("city", "region", "country") if p.get(k))
             for p in places if isinstance(p, dict)]
    workplace = WORKABLE_PLACES.get(str(data.get("workplace") or "").lower()) or (
        "Remote" if data.get("remote") is True else None)
    published = str(data.get("published") or "")[:10]
    title = T.clean(data.get("title") or "")
    raw = "".join(parts)
    base = _base(str(data.get("shortcode") or link["job_id"]).upper(), title, [w for w in dict.fromkeys(where) if w],
                 "https://apply.workable.com/%s/j/%s/" % (link["board"], str(data.get("shortcode") or link["job_id"])),
                 raw, workable_org_name(link["board"], title, raw),
                 published=published if re.match(r"^\d{4}-\d{2}-\d{2}$", published) else None)
    depts = [T.clean(str(d)) for d in (data.get("department") or []) if T.clean(str(d))] \
        if isinstance(data.get("department"), list) else [T.clean(str(data["department"]))] if data.get("department") else []
    if depts:
        base["depts"], base["team_or_department"] = depts, depts[0]
    base["workplace_type"] = workplace
    base["is_remote"] = True if workplace == "Remote" else (False if workplace else None)
    return base


def workable_org_name(account, *texts):
    """The organisation's name for a Workable account, from how the posting writes it.

    An account is the name run together in lower case ("acmeai" for "Acme
    AI"), so the posting's own spelling is found by allowing a space, a hyphen
    or a full stop between its letters. Written in lower case does not count
    (that is a web address); with no match, the account in capitals.
    """
    return spelled_name(account, *texts) or nice_name(account)


def spelled_name(account, *texts):
    """How the posting itself writes a board's run-together name ("openai" as "OpenAI"), or None.

    Used for every board whose API gives no employer name (Ashby, Lever, and
    Greenhouse when company_name is missing): the link's slug in capitals is
    only a guess ("Openai"), so the posting's own spelling wins.
    """
    letters = re.sub(r"[^a-z0-9]", "", (account or "").lower())
    if len(letters) < 3:
        return None
    word = re.compile(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % r"[ .-]?".join(re.escape(ch) for ch in letters), re.I)
    seen = {}
    for text in texts:
        for m in word.finditer(T.clean(re.sub(r"<[^>]+>", " ", text)) if text else ""):
            if m.group(0) != m.group(0).lower() and not m.group(0).endswith((" ", "-", ".")):
                seen[m.group(0)] = seen.get(m.group(0), 0) + 1
    return max(seen, key=seen.get) if seen else None


def _base(source_id, title, locations, url, raw_html, org_name, published=None):
    return {"source_id": source_id, "title": T.clean(title) or "Untitled posting", "depts": [],
            "team_or_department": None, "locations": list(locations), "extra_location_text": [],
            "workplace_type": None, "is_remote": None, "url": url, "updated_at": None,
            "published_at": published, "raw_html": raw_html or "", "compensation": None, "org_name": org_name}


# ------------------------------------------------------ a whole board, for fetch_roles.py


def workday_site(careers_url):
    """(host, tenant, site) from a Workday careers address such as https://acme.wd5.myworkdayjobs.com/en-US/Careers."""
    parts = urllib.parse.urlsplit(careers_url or "")
    host = parts.netloc.lower().split(":")[0]
    m = WORKDAY_HOST.match(host)
    segs = [x for x in parts.path.split("/") if x]
    segs = segs[1:] if segs and LANG.match(segs[0]) else segs
    return (host, m.group(1), segs[0]) if m and segs else None


def list_request(target, offset, token=None):
    """(url, JSON body or None) for one page of a target's job list on Workday, SmartRecruiters or Workable.

    Raises ValueError when the target lacks what the board needs (a Workday target needs careers_url).
    """
    ats, slug = target["ats"], urllib.parse.quote(target.get("slug") or target["id"], safe="")
    if ats == "workday":
        site = workday_site(target.get("careers_url"))
        if not site:
            raise ValueError("a Workday target needs careers_url, such as https://acme.wd5.myworkdayjobs.com/Careers")
        host, tenant, name = site
        return ("https://%s/wday/cxs/%s/%s/jobs" % (host, tenant, name),
                {"appliedFacets": {}, "limit": PAGE[ats], "offset": offset, "searchText": ""})
    if ats == "smartrecruiters":
        return "https://api.smartrecruiters.com/v1/companies/%s/postings?limit=%d&offset=%d" % (slug, PAGE[ats], offset), None
    if ats == "workable":
        body = {"query": "", "location": [], "department": [], "worktype": [], "remote": []}
        return "https://apply.workable.com/api/v3/accounts/%s/jobs" % slug, dict(body, token=token) if token else body
    raise ValueError("%s has no job list adapter" % ats)


def list_page(target, data):
    """(listed jobs, next page token or None) from one page of a job list.

    Each job is {"title", "depts", "url", "link"}: the posting's own public
    address, and the link that detail_url and posting_base read it with.
    """
    ats, slug = target["ats"], target.get("slug") or target["id"]
    data = data if isinstance(data, dict) else {}
    jobs = []
    if ats == "workday":
        host, tenant, name = workday_site(target.get("careers_url"))
        for j in data.get("jobPostings") or []:
            path = str(j.get("externalPath") or "")
            if isinstance(j, dict) and path.startswith("/job/"):
                jobs.append({"title": T.clean(j.get("title") or ""), "depts": [],
                             "url": "https://%s/%s%s" % (host, name, path),
                             "link": {"ats": ats, "board": tenant, "job_id": path[len("/job/"):], "host": host, "site": name}})
    elif ats == "smartrecruiters":
        for j in data.get("content") or []:
            if isinstance(j, dict) and j.get("id"):
                dept = (j.get("department") or {}).get("label") if isinstance(j.get("department"), dict) else None
                jobs.append({"title": T.clean(j.get("name") or ""), "depts": [dept] if dept else [],
                             "url": "https://jobs.smartrecruiters.com/%s/%s" % (slug, j["id"]),
                             "link": {"ats": ats, "board": slug, "job_id": str(j["id"])}})
    elif ats == "workable":
        for j in data.get("results") or []:
            if isinstance(j, dict) and j.get("shortcode"):
                depts = [T.clean(str(d)) for d in (j.get("department") or []) if T.clean(str(d))] \
                    if isinstance(j.get("department"), list) else []
                jobs.append({"title": T.clean(j.get("title") or ""), "depts": depts,
                             "url": "https://apply.workable.com/%s/j/%s/" % (slug, j["shortcode"]),
                             "link": {"ats": ats, "board": slug, "job_id": str(j["shortcode"]).upper()}})
    token = data.get("nextPage") if ats == "workable" else None
    return jobs, (token if isinstance(token, str) and token else None)


def list_total(target, data):
    """How many jobs the board says it has, from the first page of its list, or None."""
    key = {"workday": "total", "smartrecruiters": "totalFound", "workable": "total"}[target["ats"]]
    n = data.get(key) if isinstance(data, dict) else None
    return n if isinstance(n, int) and not isinstance(n, bool) and n > 0 else None


def detail_url(link):
    """The public API address of one listed posting."""
    board, job = urllib.parse.quote(link["board"], safe=""), urllib.parse.quote(link["job_id"], safe="")
    if link["ats"] == "workday":
        return "https://%s/wday/cxs/%s/%s/job/%s" % (link["host"], board, urllib.parse.quote(link["site"], safe=""),
                                                     urllib.parse.quote(link["job_id"], safe="/"))
    if link["ats"] == "smartrecruiters":
        return "https://api.smartrecruiters.com/v1/companies/%s/postings/%s" % (board, job)
    return "https://apply.workable.com/api/v2/accounts/%s/jobs/%s" % (board, job)


def posting_base(link, data):
    """One posting from its API answer, or None when the board no longer gives it."""
    reader = {"workday": workday_base, "smartrecruiters": smartrecruiters_base, "workable": workable_base}[link["ats"]]
    return reader(link, data)


def bundle_postings(bundle):
    """Every posting in a saved board bundle ({"listed", "postings": [{"link", "data"}], "skipped"})."""
    for item in (bundle or {}).get("postings") or []:
        base = posting_base(item["link"], item.get("data"))
        if base is not None:
            yield base
