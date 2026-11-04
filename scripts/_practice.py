"""Interview practice and debriefs: a question set for one role, and a bank of questions asked (campaign/questions.json).

Practice is allowed and encouraged by employers that publish candidate
guidance; help during a live interview is not. So LVLme helps before an
interview and after it, never during one (skills/lvlme-practice).

questions_for() builds a practice set for one role, deterministically: why
this organisation, one question per hard requirement in the posting (up to
MAX_REQS), the story themes not yet covered, and questions already asked at
that organisation in real interviews. Each comes with the person's stories
that fit it best (theme first, then shared words), so feedback can cite them.
Feedback is on structure and evidence, never a script to memorise.

The question bank records each question asked, in practice or for real, rated
strong, solid or gap. A real interview's gap on a theme shows on the story
bank as "practise this". Progress only: score.py never reads it. No network.
"""
import re

import _stories as ST

REL = "campaign/questions.json"
RATINGS = ["strong", "solid", "gap"]
KINDS = ["practice", "real"]
MAX_REQS = 4
STOP = set("a an and the of to in for on with or at by from as is are be your you this that it its into tell me about "
           "time when how what did have who why years year experience comfort working work".split())
NOTE = "Help before and after interviews, never during one. Feedback is on structure and evidence, never a script."


def empty():
    return {"schema_version": 1, "questions": []}


def stem(w):
    for end in ("ing", "ed", "s"):
        if len(w) > len(end) + 3 and w.endswith(end):
            return w[:-len(end)]
    return w


def words(text):
    return {stem(w) for w in re.findall(r"[a-z][a-z0-9+-]{2,}", (text or "").lower()) if w not in STOP}


def story_text(s):
    return " ".join([s.get("title", ""), s.get("situation", ""), s.get("task", ""), s.get("action", ""),
                     s.get("result", "")])


def fits(question, theme, stories, levels, limit=2, need=2):
    """The ids of the stories that fit a question best: matching theme first, then shared words (at least
    `need`), then evidence."""
    q = words(question)
    scored = []
    for s in stories:
        on_theme = theme in (s.get("themes") or [])
        shared = len(q & words(story_text(s)))
        if on_theme or shared >= need:
            strong = ST.strength(s, levels) in ST.STRONG
            scored.append((-int(on_theme), -shared, -int(strong), s["id"]))
    return [x[-1] for x in sorted(scored)[:limit]]


def questions_for(role, org_name, stories_doc, bank, config, evidence_doc):
    """[{"text", "theme", "why", "stories"}] for one role."""
    stories, levels = (stories_doc or {}).get("stories") or [], ST.levels_of(evidence_doc)
    names = {t["id"]: t for t in ST.themes(config)}
    out = []

    def add(text, theme, why, match=None):
        out.append({"text": text, "theme": theme, "why": why,
                    "stories": fits(match or text, theme, stories, levels, need=1 if match else 2)})
    if "why_here" in names:
        add("Why %s, and why this role now?" % org_name, "why_here", "Nearly every interview asks it.")
    for req in (role.get("hard_requirements") or [])[:MAX_REQS]:
        add("Tell me about a time you showed this: %s." % req.rstrip("."), "",
            "A hard requirement in the posting.", req)
    covered = {q["theme"] for q in out}
    for t in names.values():
        if t["id"] not in covered and t.get("ask"):
            add(t["ask"], t["id"], "A common interview theme.")
    for q in (bank or {}).get("questions") or []:
        if q.get("kind") == "real" and q.get("org") == role.get("org") and q["text"] not in {x["text"] for x in out}:
            add(q["text"], q.get("theme") or "", "Asked in a real interview here on %s." % q.get("asked_on"))
    return out


def next_id(bank):
    n = max([int(q["id"][1:]) for q in (bank or {}).get("questions") or [] if re.match(r"^Q\d+$", q.get("id", ""))]
            or [0])
    return "Q%02d" % (n + 1)


def struggled(bank):
    """{theme: count} of real-interview questions rated gap."""
    out = {}
    for q in (bank or {}).get("questions") or []:
        if q.get("kind") == "real" and q.get("rating") == "gap" and q.get("theme"):
            out[q["theme"]] = out.get(q["theme"], 0) + 1
    return out


def summary(bank):
    qs = (bank or {}).get("questions") or []
    real = [q for q in qs if q.get("kind") == "real"]
    return {"practice": len(qs) - len(real), "real": len(real),
            "gaps": sum(1 for q in real if q.get("rating") == "gap"), "struggled": struggled(bank)}


def checks(bank, config, story_ids, app_ids, errors):
    if bank is None:
        return
    known, seen = {t["id"] for t in ST.themes(config)}, set()
    for q in bank.get("questions") or []:
        where = REL + ": " + str(q.get("id"))
        if q.get("id") in seen:
            errors.append(where + " is a duplicate id")
        seen.add(q.get("id"))
        if q.get("theme") and q["theme"] not in known:
            errors.append(where + " names theme %s, which is not a story theme" % q["theme"])
        for s in q.get("stories") or []:
            if story_ids is not None and s not in story_ids:
                errors.append(where + " cites story %s, which is not in profile/stories.json" % s)
        if q.get("app") and app_ids is not None and q["app"] not in app_ids:
            errors.append(where + " names application %s, which is not in campaign/applications.json" % q["app"])
