"""Checklist scoring, beside today's fit. It does not change fit, bands or chance.

A job is a list of requirements. Each one is marked met, partly, not shown, unknown
or not applicable. Plain code turns those marks into a verdict. A licence or an
eligibility rule fails the job only when most votes say it is not shown. Something
anyone can get before starting (a check, a vaccination) is a to-do, not a fail.
A soft skill counts at half weight. An unknown widens the range. It is never stored
as zero and it is never shown as a chance of getting the job. A strong match needs
most must-have rows fully met: half-met rows earn points but not that verdict.

  merge_extracts(extracts)     keep a requirement that appears in at least two reads
  score_checklist(rows, votes) the verdict, the must-have line, and the comparison points
  beside(today_fit, result)    today's fit, unchanged, next to the checklist result
"""
import re
from collections import Counter

VERDICTS = ("strong match", "worth applying", "stretch", "not yet")
POINTS = {"met": 1.0, "partly": 0.5, "not_shown": 0.0}
GATES = ("licence", "eligibility")
THIN_NOTICE = "This posting states very few requirements, so some rows are inferred."


def _norm(text):
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


# Words that say nothing about which requirement a row is, so they do not count as shared.
_STOP = set("a an the and or of to in on for with by as at from into through including include that this these "
            "those is are be been its it their your you we our will can ability skill skills experience "
            "experienced".split())
SAME_ROW_SHARED = 0.5       # share at least half of all content words (Jaccard), or
SAME_ROW_CONTAINED = 0.7    # the shorter row's words are mostly inside the longer row's


def _words(text):
    """The content words of a row, crudely stemmed, so two wordings of one requirement look alike."""
    out = set()
    for w in re.findall(r"[a-z0-9]+", (text or "").lower()):
        if w in _STOP or len(w) < 3:
            continue
        for suffix in ("ing", "ed", "es", "s"):
            if w.endswith(suffix) and len(w) - len(suffix) >= 4:
                w = w[:-len(suffix)]
                break
        out.add(w)
    return out


def same_requirement(a, b):
    """True when two rows read as the same requirement: identical text, or most content words shared."""
    if _norm(a) == _norm(b):
        return True
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return False
    both = len(wa & wb)
    return both / len(wa | wb) >= SAME_ROW_SHARED or both / min(len(wa), len(wb)) >= SAME_ROW_CONTAINED


def _common(values, default):
    vals = [v for v in values if v not in (None, "")]
    if not vals:
        return default
    return Counter(vals).most_common(1)[0][0]


def merge_extracts(extracts):
    """Keep a requirement that shows up in at least two reads of the posting.

    Two reads rarely use the same words for one requirement, so rows are matched
    by the content words they share (same_requirement), not by exact text. The
    first read's wording is kept. One read is kept as given: that is a checklist
    the person has already corrected. Rows come back numbered R1, R2, ... in
    the order they were first seen.
    """
    extracts = [list(e or []) for e in extracts]
    if len(extracts) <= 1:
        rows = extracts[0] if extracts else []
    else:
        groups = []
        for src in extracts:
            used = set()   # one row of this read per group, so a read cannot vote twice for one requirement
            for row in src:
                text = row.get("text") or ""
                if not _norm(text):
                    continue
                match = next((i for i, g in enumerate(groups)
                              if i not in used and same_requirement(text, g["text"])), None)
                if match is None:
                    groups.append({"text": text, "hits": 1, "copies": [row]})
                    used.add(len(groups) - 1)
                else:
                    groups[match]["hits"] += 1
                    groups[match]["copies"].append(row)
                    used.add(match)
        rows = []
        for group in groups:
            if group["hits"] < 2:
                continue
            copies = group["copies"]
            first = copies[0]
            rows.append({
                "text": first.get("text") or "",
                "strength": _common([c.get("strength") for c in copies], "should"),
                "type": _common([c.get("type") for c in copies], "skill"),
                "inferred": all(bool(c.get("inferred")) for c in copies),
                "applies": _common([c.get("applies") for c in copies], "everyone"),
            })
    out = []
    for i, row in enumerate(rows, 1):
        item = dict(row)
        item["id"] = "R%d" % i
        item.setdefault("strength", "should")
        item.setdefault("type", "skill")
        item.setdefault("inferred", False)
        item.setdefault("applies", "everyone")
        out.append(item)
    return out


def thin_posting(rows):
    """True when the ad itself states fewer than four real requirements."""
    stated = [r for r in rows if not r.get("inferred") and r.get("type") not in GATES + ("condition",)]
    return len(stated) < 4


def _majority(votes):
    """The verdict most votes share. A tie, or no verdict twice, is a split."""
    votes = [v for v in votes if v]
    if not votes:
        return "unknown", False
    if len(votes) == 1:
        return votes[0], False
    ranked = Counter(votes).most_common()
    if len(ranked) >= 2 and ranked[0][1] == ranked[1][1]:
        return "split", True
    if ranked[0][1] < 2:
        return "split", True
    return ranked[0][0], False


STRONG_NEEDS_MET = 0.6   # strong match: at least this share of the must-have rows fully met, not half met


def _verdict(points, gate_fail, must_met=None, must_total=None):
    if gate_fail:
        return "not yet"
    if points >= 75 and (not must_total or must_met / must_total >= STRONG_NEEDS_MET):
        return "strong match"
    if points >= 75:
        return "worth applying"   # the points are there, but too many must-haves are only half met
    if points >= 50:
        return "worth applying"
    if points >= 25:
        return "stretch"
    return "not yet"


def _cover(num, den):
    if den <= 0:
        return None
    return num / den


def _points(must, should):
    m = _cover(must[0], must[1])
    s = _cover(should[0], should[1])
    if m is None and s is None:
        return 0.0
    if m is not None and s is not None:
        return round(100 * (0.75 * m + 0.25 * s), 1)
    return round(100 * (m if m is not None else s), 1)


def score_checklist(rows, votes):
    """Score one saved checklist.

    votes maps a row id to a list of verdicts (one per read). A single verdict
    is the person's corrected mark and stands on its own.
    """
    rows = list(rows or [])
    votes = votes or {}
    must_met = must_total = 0
    known = {"must": [0.0, 0.0], "should": [0.0, 0.0]}
    low = {"must": [0.0, 0.0], "should": [0.0, 0.0]}
    high = {"must": [0.0, 0.0], "should": [0.0, 0.0]}
    gate_fail = False
    unknown_count = 0
    must_unknown = 0   # must rows nobody could judge: met in the best case, not in the worst
    todos, questions, moves = [], [], []

    for row in rows:
        verdict, split = _majority(list(votes.get(row["id"]) or []))
        if verdict == "not_applicable":
            continue
        if row.get("type") == "condition":
            if verdict != "met":
                todos.append(row.get("text") or "")
            continue
        was_split = split
        if split:
            questions.append("Split vote on: %s" % (row.get("text") or ""))
            verdict = "unknown"
        weight = 0.5 if row.get("type") == "soft_skill" else 1.0
        strength = "must" if row.get("strength") == "must" else "should"
        if strength == "must":
            must_total += 1
            if verdict == "met":
                must_met += 1
        if (row.get("type") in GATES and strength == "must" and verdict == "not_shown"):
            gate_fail = True
        if verdict == "unknown":
            unknown_count += 1
            if strength == "must":
                must_unknown += 1
            low[strength][1] += weight
            high[strength][0] += weight
            high[strength][1] += weight
            if strength == "must" and not was_split:
                questions.append("Not shown in your evidence: %s" % (row.get("text") or ""))
            continue
        gained = weight * POINTS.get(verdict, 0.0)
        for bucket in (known, low, high):
            bucket[strength][0] += gained
            bucket[strength][1] += weight
        if verdict in ("not_shown", "partly"):
            moves.append((0 if strength == "must" else 1, verdict != "not_shown", row.get("text") or ""))

    points = 0.0 if gate_fail else _points(known["must"], known["should"])
    points_low = 0.0 if gate_fail else _points(low["must"], low["should"])
    points_high = 0.0 if gate_fail else _points(high["must"], high["should"])
    verdict = _verdict(points, gate_fail, must_met, must_total)
    low_v = _verdict(points_low, False, must_met, must_total)
    high_v = _verdict(points_high, False, must_met + must_unknown, must_total)
    if not gate_fail and low_v != high_v:
        questions.append("The unknowns could move this between %s and %s." % (low_v, high_v))
    moves = ["Add evidence for: %s" % text for _, _, text in sorted(moves)[:3]]
    thin = thin_posting(rows)
    must_line = ("%d of %d must-haves met" % (must_met, must_total) if must_total
                 else "This posting states no must-haves.")
    shown = {
        "verdict": verdict,
        "must_line": must_line,
        "moves": moves,
        "questions": questions,
        "todos": todos,
        "thin_posting": thin,
        "notice": THIN_NOTICE if thin else None,
    }
    return {
        "shown": shown,
        "compare": {"points": points, "points_low": points_low, "points_high": points_high,
                    "unknown_count": unknown_count},
    }


NOT_MARKED = "not marked yet"


def unmarked(rows):
    """The result for a list nobody has marked against the evidence yet: no verdict, no points."""
    rows = list(rows or [])
    musts = sum(1 for r in rows if r.get("strength") == "must" and r.get("type") != "condition")
    return {
        "shown": {
            "verdict": NOT_MARKED,
            "must_line": ("%d must-have%s to check against your evidence" % (musts, "" if musts == 1 else "s")
                          if musts else "This posting states no must-haves."),
            "moves": [],
            "questions": [],
            "todos": [],
            "thin_posting": thin_posting(rows),
            "notice": THIN_NOTICE if thin_posting(rows) else None,
        },
        "compare": {"points": None, "points_low": None, "points_high": None, "unknown_count": len(rows)},
    }


def beside(today_fit, result):
    """Today's fit, unchanged, next to the checklist. Fit is not rewritten."""
    out = {"today_fit": today_fit, "shown": result["shown"], "compare": dict(result["compare"])}
    out["compare"]["today_fit"] = today_fit
    return out


def attach(role, entry):
    """Put the checklist on one scored role. role['fit'] is not changed.

    entry is the saved list for that role: rows, votes, and corrected.
    corrected false means the person has not yet confirmed the list.
    """
    fit = role["fit"]
    rows = list(entry.get("rows") or [])
    votes = entry.get("votes") or {}
    if not any(votes.get(r.get("id")) for r in rows):
        result = unmarked(rows)
    else:
        result = score_checklist(rows, votes)
    if entry.get("corrected") is False:
        result["shown"]["questions"] = ["Is this what the job asks for?"] + result["shown"]["questions"]
    both = beside(fit, result)
    role["checklist"] = {
        "verdict": both["shown"]["verdict"],
        "must_line": both["shown"]["must_line"],
        "moves": both["shown"]["moves"],
        "questions": both["shown"]["questions"],
        "todos": both["shown"]["todos"],
        "thin_posting": both["shown"]["thin_posting"],
        "notice": both["shown"]["notice"],
        "rows": [{"id": r.get("id"), "text": r.get("text") or "", "strength": r.get("strength") or "should",
                  "type": r.get("type") or "skill", "inferred": bool(r.get("inferred"))} for r in rows],
        "corrected": entry.get("corrected") is not False,
        "today_fit": both["today_fit"],
    }
    if role["fit"] != fit:
        raise RuntimeError("checklist changed today's fit")
    return role["checklist"]
