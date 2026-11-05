"""Job match and the warm-path question (added to rubric 1.2 in LVLme 0.7.2; fit, bands and levels unchanged).

Job match answers "how well do I match this job?" from the four factors judged against the role itself:
D1 requirements match, D2 proof of work, D4 organisation edge and D6 eligibility and location, with their
weights from config.json, rescaled to 0 to 100. Fit adds the three campaign factors on top (D3 warm path,
D5 public signal, D7 application readiness), which are the same for every role at an organisation, so they
lower every fit together without telling one job from another.

A warm path the person was never asked about is not the same as knowing nobody. It still scores 0 (evidence
or zero), but the run says so and asks the question, one per target organisation.
"""

MATCH_DIMENSIONS = ("D1", "D2", "D4", "D6")
NOT_ASKED_NOTE = ("Not asked yet: LVLme has not asked whether you know anyone here who has seen your work, "
                  "so this counts as 0 until you answer.")


def match_of(scores, weights, pick):
    """Weighted job match, 0 to 100, one decimal. 0 when the four role factors all weigh 0."""
    total = sum(weights[d] for d in MATCH_DIMENSIONS)
    if total <= 0:
        return 0.0
    return round(sum(pick(scores[d]) / 5.0 * weights[d] for d in MATCH_DIMENSIONS) * 100.0 / total, 1)


def warm_path_asked(profile, org):
    """True when the person has answered the warm-path question for this organisation.

    An entry for the organisation counts as asked unless it says `asked: false`. The `default` entry counts
    as asked only when it says `asked: true` (the person answered for every target at once)."""
    section = (profile or {}).get("D3") or {}
    entry = section.get(org)
    if entry is not None:
        return entry.get("asked", True) is not False
    default = section.get("default")
    return bool(default and default.get("asked") is True)


def mark_not_asked(d3):
    """Say in the D3 note that the question was never asked. The score is unchanged."""
    old = (d3.get("note") or "").strip()
    d3["note"] = NOT_ASKED_NOTE + (" Earlier note: " + old if old else "")


def warm_path_questions(config, profile):
    """One "Do you know anyone at ...?" question per target organisation not yet asked."""
    out = []
    for t in (config or {}).get("targets") or []:
        if warm_path_asked(profile, t["id"]):
            continue
        name = t.get("name") or t["id"]
        out.append({"id": "WP-" + t["id"],
                    "question": "Do you know anyone at %s who has seen your work, or someone who could introduce "
                                "you to them? A former colleague, a client, a manager or a friend counts." % name,
                    "why": "Not asked yet, so the warm path at %s counts as 0. A named person who knows your work "
                           "can score up to 3 out of 5 once their own words back it up (an email or message)." % name,
                    "dimensions": ["D3"], "source": "warm_path_not_asked"})
    return out
