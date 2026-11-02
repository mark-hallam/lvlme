#!/usr/bin/env python3
"""Score every open role from the judgement files. Deterministic: the same
inputs always give the same run file, byte for byte.

Reads
  config.json                     weights, review threshold, eligibility cleared
  market/roles/latest.json        open roles (from fetch_roles.py)
  eval/judgements.json            per-role D1, D2, D4 and hard-requirement calls
  eval/profile-dimensions.json    per-org D3, D5, D7 and the D6 location rules
  eval/gap-templates.json         gaps the person could close
  eval/outlook.json               the agent's outlook band and reasons
  profile/evidence.json           evidence items (levels cap the scores)
Writes
  eval/runs/<date>.json           see schemas/run.schema.json. Not written (exit 1)
                                  when no role is judged yet: that would be a
                                  false Day 1, not a measurement.

Rules (method/RUBRIC.md v1.0), applied in this order per dimension:
  1. evidence cap: a score can be no higher than its best cited evidence
     supports (verified 5, corroborated 4, partially verified the higher of
     the kind's self-reported cap and scoring.partially_verified_cap (default
     2) but never above 4, self-reported by kind, else 0);
  2. review cap: a score above the review threshold (default 2) counts as the
     threshold until reviewed_on is set, on or after judged_on;
  3. hard requirement lacking (or an eligibility blocker): D1 capped at 1.
Then fit = sum(score / 5 x weight), bands from the fit table, and the three
adjustments: warm referral up, hard requirement lacking down, cold-only cap.

Gap leaderboard: over the top scoring.top_n_for_gaps roles overall (the
default, scoring.gap_pool "overall"), or, with gap_pool "per_org", over each
target organisation's own top scoring.top_n_per_org_for_gaps roles, so a gap
at an organisation whose roles are not in the overall top still counts.

Usage
  python3 scripts/score.py --workspace PATH [--date YYYY-MM-DD]
"""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

RUBRIC_VERSION = "1.0"
BANDS = C.BANDS
INTERVIEW_TABLE = [(85, "Strong"), (70, "Good"), (55, "Moderate"), (40, "Low"), (0, "Very low")]
OFFER_TABLE = [(85, "Good"), (70, "Moderate"), (55, "Low"), (40, "Very low"), (0, "Very low")]
LEVEL_CAPS = {"verified": 5, "corroborated": 4, "unverified": 0, "contradicted": 0}
DEFAULT_SELF_CAPS = {"job_history": 3, "education": 3, "eligibility": 5, "preference": 5, "default": 1}
DEFAULT_PARTIAL_CAP = 2
DEFAULT_TOP_N = 25
GAP_POOLS = ("overall", "per_org")
NOT_JUDGED = "Not yet judged."


def band_for(table, fit):
    for threshold, band in table:
        if fit >= threshold:
            return band
    return "Very low"


def shift(band, steps):
    return BANDS[min(max(BANDS.index(band) + steps, 0), len(BANDS) - 1)]


class Ctx:
    """Everything a scoring pass needs, loaded once."""

    def __init__(self, config, evidence, profile):
        scoring = config.get("scoring") or {}
        cand = config.get("candidate") or {}
        self.config = config
        self.weights = C.weights_of(config)
        self.total_weight = sum(self.weights.values()) or 1
        self.review_above = int(scoring.get("review_required_above", 2))
        self.top_n = int(scoring.get("top_n_for_gaps", DEFAULT_TOP_N))
        self.self_caps = dict(DEFAULT_SELF_CAPS, **(scoring.get("self_reported_caps") or {}))
        self.partial_cap = int(scoring.get("partially_verified_cap", DEFAULT_PARTIAL_CAP))
        self.gap_pool = scoring.get("gap_pool") or "overall"
        self.top_n_per_org = int(scoring.get("top_n_per_org_for_gaps", self.top_n))
        self.cleared = set(cand.get("eligibility_cleared") or [])
        self.writes_code = bool(cand.get("writes_production_code", False))
        self.evidence = {e["id"]: e for e in (evidence or {}).get("items", [])}
        self.profile = profile or {}
        self.class_order = [c["id"] for c in (config.get("locations") or {}).get("classes", [])]
        self.default_class = (config.get("locations") or {}).get("default_class") or "other"
        self.warnings = set()

    def warn(self, text):
        self.warnings.add(text)


def level_cap(level, kind, self_caps, partial_cap=DEFAULT_PARTIAL_CAP):
    """Highest score one evidence item supports, from its level and kind.

    partially_verified (some facts in the claim checked, some not) supports the
    higher of its kind's self-reported cap and partial_cap, but never more than
    corroborated evidence (4): a claim that is only partly checked can never
    outrank one that two independent sources agree on."""
    kind = kind or "other"
    self_cap = int(self_caps.get(kind, self_caps.get("default", 1)))
    if level == "self_reported":
        return self_cap
    if level == "partially_verified":
        return min(LEVEL_CAPS["corroborated"], max(self_cap, int(partial_cap)))
    return LEVEL_CAPS.get(level, 0)


def evidence_cap(ctx, ids, where):
    """Highest score the cited evidence can support, and why."""
    best, why = 0, "no evidence cited"
    seen_known = False
    for eid in ids or []:
        item = ctx.evidence.get(eid)
        if item is None:
            ctx.warn("%s: unknown evidence id %s (ignored)" % (where, eid))
            continue
        level, kind = item.get("level"), item.get("kind") or "other"
        cap = level_cap(level, kind, ctx.self_caps, ctx.partial_cap)
        if level in ("self_reported", "partially_verified"):
            label = "%s %s" % ("self-reported" if level == "self_reported" else "partially verified",
                               kind.replace("_", " "))
        else:
            label = str(level)
        if not seen_known or cap > best:
            best, why = cap, "best cited evidence is %s, which supports at most %d" % (label, cap)
            seen_known = True
    return best, why


def is_reviewed(entry, container):
    reviewed = entry.get("reviewed_on") or (container or {}).get("reviewed_on")
    judged = entry.get("judged_on") or (container or {}).get("judged_on") or ""
    return bool(reviewed) and reviewed >= judged


def score_entry(ctx, dim, entry, container, where):
    """Apply the evidence and review caps. Returns (score dict, adjustments, awaiting review)."""
    raw = min(max(int(entry.get("score", 0)), 0), 5)
    evidence = list(entry.get("evidence") or [])
    score, caps, adjustments, awaiting = raw, [], [], []
    cap, why = evidence_cap(ctx, evidence, where)
    if score > cap:
        caps.append("evidence: " + why)
        adjustments.append("%s %d counted as %d: %s" % (dim, raw, cap, why))
        score = cap
    if score > ctx.review_above and not is_reviewed(entry, container):
        caps.append("awaiting review")
        adjustments.append("%s %d counted as %d until the reviewer agrees" % (dim, score, ctx.review_above))
        awaiting.append(dim)
        score = ctx.review_above
    out = {"score": score, "raw": raw, "evidence": evidence, "note": entry.get("note", "")}
    if caps:
        out["capped"] = "; ".join(caps)
    return out, adjustments, awaiting


def profile_entry(ctx, section, org):
    sec = ctx.profile.get(section) or {}
    entry = sec.get(org) or sec.get("default")
    if entry is None:
        return {"score": 0, "evidence": [], "note": NOT_JUDGED}
    return entry


def is_blocked(ctx, role, judgement):
    if judgement and judgement.get("hard_eligibility_block"):
        return True
    if judgement and judgement.get("eligibility_blocked") is not None:
        return bool(judgement["eligibility_blocked"])
    return any(b.get("type") not in ctx.cleared for b in role.get("eligibility_blockers") or [])


def best_d6(ctx, role, judgement):
    """Pick the location class whose D6 rule scores highest (after caps)."""
    classes = (ctx.profile.get("D6_rules") or {}).get("classes") or {}
    if judgement and judgement.get("location_class"):
        candidates = [judgement["location_class"]]
    else:
        candidates = list(role.get("location_classes") or []) or [ctx.default_class]
    order = {c: i for i, c in enumerate(ctx.class_order)}
    best = None
    for cls in sorted(candidates, key=lambda c: order.get(c, 99)):
        entry = classes.get(cls) or {"score": 0, "evidence": [], "note": "No D6 rule for location class %s." % cls}
        result = score_entry(ctx, "D6", entry, ctx.profile, "D6 rule %s" % cls)
        if best is None or result[0]["score"] > best[1][0]["score"]:
            best = (cls, result)
    return best


def score_role(ctx, role, judgement):
    rid = role["id"]
    adjustments, awaiting, scores = [], [], {}
    blocked = is_blocked(ctx, role, judgement)
    if judgement is None:
        for d in ("D1", "D2", "D4"):
            scores[d] = {"score": 0, "raw": 0, "evidence": [], "note": NOT_JUDGED}
        adjustments.append("Not yet judged: D1, D2 and D4 count as 0 until the scorer judges this role")
        lacking = blocked
        lacking_note = ""
        if role.get("requires_heavy_coding") and not ctx.writes_code:
            lacking, lacking_note = True, "the posting expects production coding"
    else:
        for d in ("D1", "D2", "D4"):
            s, adj, aw = score_entry(ctx, d, judgement[d], judgement, "%s %s" % (rid, d))
            scores[d] = s
            adjustments += adj
            awaiting += aw
        lacking = bool(judgement.get("hard_requirement_lacking")) or blocked
        lacking_note = judgement.get("hard_requirement_note", "")
    org = role["org"]
    for d in ("D3", "D5", "D7"):
        s, adj, aw = score_entry(ctx, d, profile_entry(ctx, d, org), ctx.profile, "profile %s %s" % (d, org))
        scores[d] = s
        adjustments += adj
        awaiting += aw
    loc_class, (d6, adj, aw) = best_d6(ctx, role, judgement)
    if blocked:
        rule = (ctx.profile.get("D6_rules") or {}).get("blocked") or {}
        types = sorted({b.get("type") for b in role.get("eligibility_blockers") or []})
        label = ", ".join(C.BLOCKER_NAMES.get(t, t) for t in types) or "set in the judgement"
        d6 = {"score": 0, "raw": d6["raw"], "evidence": list(rule.get("evidence") or []),
              "note": rule.get("note") or "Eligibility blocker in the posting.", "capped": "eligibility blocker"}
        adjustments.append("Eligibility blocker (%s): D6 = 0" % label)
    else:
        adjustments += adj
        awaiting += aw
    scores["D6"] = d6
    if lacking and scores["D1"]["score"] > 1:
        scores["D1"]["score"] = 1
        scores["D1"]["capped"] = "; ".join(filter(None, [scores["D1"].get("capped"), "hard requirement lacking"]))
    scores = {d: scores[d] for d in C.DIMENSIONS}

    fit = round(sum(scores[d]["score"] / 5.0 * ctx.weights[d] for d in C.DIMENSIONS) * 100.0 / ctx.total_weight, 1)
    interview, offer = band_for(INTERVIEW_TABLE, fit), band_for(OFFER_TABLE, fit)
    if role.get("requires_heavy_coding"):
        adjustments.append("Posting expects production coding")
    if scores["D3"]["score"] >= 4:
        interview = shift(interview, +1)
        adjustments.append("Warm referral (D3 at least 4): interview band up one step")
    if lacking:
        interview, offer = shift(interview, -1), shift(offer, -1)
        why = lacking_note or ("an eligibility blocker" if blocked else "hard requirement lacking")
        adjustments.append("Hard requirement lacking (%s): D1 capped at 1 and both bands down one step" % why)
    if scores["D3"]["score"] <= 1 and BANDS.index(offer) > BANDS.index("Low"):
        offer = "Low"
        adjustments.append("Cold application only (D3 at most 1): offer band capped at Low")
    return {
        "role_id": rid, "org": org, "title": role["title"], "family": role["family"],
        "locations": list(role.get("locations") or []), "location_class": loc_class, "url": role.get("url"),
        "scores": scores, "fit": fit, "interview_band": interview, "offer_band": offer,
        "adjustments": adjustments, "judged": judgement is not None,
        "awaiting_review": sorted(set(awaiting)), "eligibility_blocked": blocked,
        "hard_requirement_lacking": lacking, "requires_heavy_coding": bool(role.get("requires_heavy_coding")),
        "reviewer_note": (judgement or {}).get("reviewer_note", ""),
    }


def sort_key(r):
    return (-r["fit"], -BANDS.index(r["interview_band"]), r["role_id"])


def gap_pools(ctx, scored):
    """The roles the gap leaderboard adds up over: {pool key: roles}, in run order.

    overall (the default): one pool, the top top_n_for_gaps roles overall.
    per_org: one pool per target organisation (config order, then any other
    organisation with roles), each its own top top_n_per_org_for_gaps roles."""
    if ctx.gap_pool != "per_org":
        return {None: scored[:ctx.top_n]}
    orgs = list(C.target_ids(ctx.config))
    orgs += sorted({r["org"] for r in scored} - set(orgs))
    return {o: [r for r in scored if r["org"] == o][:ctx.top_n_per_org] for o in orgs}


def gap_gain(ctx, g, r):
    """Fit points one role gains if the gap closes (0 if the gap does not apply to it)."""
    orgs, fams = g.get("orgs", "all"), g.get("families", "all")
    dim, target = g["dimension"], int(g["target_score"])
    if orgs != "all" and r["org"] not in orgs:
        return 0.0
    if fams != "all" and r["family"] not in fams:
        return 0.0
    if r["eligibility_blocked"] and (g.get("exclude_blocked") or dim == "D6"):
        return 0.0
    if g.get("location_classes") and r["location_class"] not in g["location_classes"]:
        return 0.0
    tgt = min(target, 1) if dim == "D1" and r["hard_requirement_lacking"] else target
    return max(0.0, (tgt - r["scores"][dim]["score"]) / 5.0 * ctx.weights[dim] * 100.0 / ctx.total_weight)


def compute_gaps(ctx, scored, templates):
    if ctx.gap_pool not in GAP_POOLS:
        ctx.warn("scoring.gap_pool %r is not one of %s; using overall" % (ctx.gap_pool, ", ".join(GAP_POOLS)))
        ctx.gap_pool = "overall"
    pools = gap_pools(ctx, scored)
    gaps = []
    for g in templates:
        total, affected, by_org = 0.0, 0, {}
        for key, roles in pools.items():
            pts, n = 0.0, 0
            for r in roles:
                gain = gap_gain(ctx, g, r)
                if gain > 0:
                    pts += gain
                    n += 1
            total, affected = total + pts, affected + n
            if key is not None and n:
                by_org[key] = {"points_gain": round(pts, 1), "roles_affected": n}
        gap = {"id": g["id"], "title": g["title"], "why": g.get("why", ""), "dimension": g["dimension"],
               "target_score": int(g["target_score"]), "points_gain": round(total, 1), "roles_affected": affected}
        if ctx.gap_pool == "per_org":
            gap.update(pool="per_org", by_org=by_org)
        gaps.append(gap)
    return sorted(gaps, key=lambda x: (-x["points_gain"], x["id"]))


def verify_questions(evidence):
    out = []
    for q in (evidence or {}).get("open_questions", []):
        if q.get("status") == "open":
            out.append({"id": q["id"], "question": q["question"],
                        "why": q.get("why") or "Would change at least one score.",
                        "dimensions": list(q.get("dimensions") or []), "source": "open_question"})
    for item in (evidence or {}).get("items", []):
        if item.get("level") == "unverified":
            dims = list(item.get("dimensions") or [])
            out.append({"id": item["id"], "question": "Can you point to a source for this? %s" % item["claim"],
                        "why": "Counts as 0 until there is a source" + (
                            " (feeds %s)." % ", ".join(dims) if dims else "."),
                        "dimensions": dims, "source": "unverified_evidence"})
    return out


def digest(*parts):
    h = hashlib.sha256()
    for p in parts:
        h.update(json.dumps(p, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    return "sha256:" + h.hexdigest()


def build_run(ws, config, run_date):
    roles_doc = C.load_json(C.wpath(ws, "market", "roles", "latest.json"))
    if roles_doc is None:
        raise SystemExit("lvlme: no market/roles/latest.json. Run scripts/fetch_roles.py first.")
    judgements_doc = C.load_json(C.wpath(ws, "eval", "judgements.json"), {"roles": {}}) or {"roles": {}}
    profile = C.load_json(C.wpath(ws, "eval", "profile-dimensions.json"), {}) or {}
    templates = (C.load_json(C.wpath(ws, "eval", "gap-templates.json"), {}) or {}).get("gaps", [])
    outlook = C.load_json(C.wpath(ws, "eval", "outlook.json"), None)
    evidence = C.load_json(C.wpath(ws, "profile", "evidence.json"), {"items": []}) or {"items": []}
    ctx = Ctx(config, evidence, profile)
    judgements = judgements_doc.get("roles") or {}
    roles = roles_doc.get("roles") or []

    jv = judgements_doc.get("rubric_version")
    if jv and jv != RUBRIC_VERSION:
        ctx.warn("judgements were made under rubric %s; this is rubric %s, so scores may not be comparable"
                 % (jv, RUBRIC_VERSION))
    targets = set(C.target_ids(config))
    for section in ("D3", "D5", "D7"):
        for key in (profile.get(section) or {}):
            if key != "default" and key not in targets:
                ctx.warn("profile %s has an entry for %s, which is not a target in config.json" % (section, key))

    scored = sorted((score_role(ctx, r, judgements.get(r["id"])) for r in roles), key=sort_key)
    per_org = {}
    for tid in C.target_ids(config):
        best = next((r for r in scored if r["org"] == tid), None)
        per_org[tid] = None if best is None else {k: best[k] for k in
                                                  ("role_id", "title", "fit", "interview_band", "offer_band")}
    if outlook:
        out_look = {"band": outlook.get("band", "Not yet judged"), "text": outlook.get("text", ""),
                    "reasons": list(outlook.get("reasons") or [])}
        if outlook.get("judged_on"):
            out_look["judged_on"] = outlook["judged_on"]
    else:
        out_look = {"band": "Not yet judged", "text": "The agent has not written eval/outlook.json yet.",
                    "reasons": []}
    role_ids = {r["id"] for r in roles}
    stale = sorted(set(judgements) - role_ids)
    run = {
        "schema_version": 1,
        "run_date": run_date,
        "rubric_version": RUBRIC_VERSION,
        "goal": (config.get("goal") or {}).get("title", ""),
        "weights": ctx.weights,
        "inputs_digest": digest(config, roles, judgements_doc, profile, templates, outlook, evidence),
        "counts": {
            "roles": len(scored),
            "judged": sum(1 for r in scored if r["judged"]),
            "not_judged": sum(1 for r in scored if not r["judged"]),
            "awaiting_review": sum(1 for r in scored if r["awaiting_review"]),
            "eligibility_blocked": sum(1 for r in scored if r["eligibility_blocked"]),
            "hard_requirement_lacking": sum(1 for r in scored if r["hard_requirement_lacking"]),
            "stale_judgements": len(stale),
        },
        "roles": scored,
        "per_org": per_org,
        "gaps": compute_gaps(ctx, scored, templates),
        "outlook": out_look,
        "verify_to_unlock": verify_questions(evidence),
        "warnings": sorted(ctx.warnings),
    }
    return run


def main(argv=None):
    ap = argparse.ArgumentParser(description="Score every open role from the judgement files.")
    ap.add_argument("--workspace", help="workspace folder (default: $LVLME_HOME)")
    ap.add_argument("--date", help="run date YYYY-MM-DD (default: today in the candidate's time zone)")
    args = ap.parse_args(argv)
    ws, config = C.open_workspace(args.workspace)
    if C.setup_problem(config):
        print(C.setup_problem(config), file=sys.stderr)
        return 1
    run_date = C.check_date(args.date) if args.date else C.today_in(config)
    run = build_run(ws, config, run_date)
    n = run["counts"]
    if not n["judged"]:  # nothing judged is not a measurement: saving it would make a false Day 1
        print(("%d role%s not judged yet. Ask your agent to run LVLme." % (n["roles"], "" if n["roles"] == 1 else "s"))
              if n["roles"] else "No open roles to score yet. Ask your agent to run LVLme.", file=sys.stderr)
        print("No run saved: with nothing judged it would not be a measurement.", file=sys.stderr)
        return 1
    out = C.wpath(ws, "eval", "runs", "%s.json" % run_date)
    C.write_json(out, run)
    print("Wrote eval/runs/%s.json: %d roles (%d not yet judged, %d awaiting review)"
          % (run_date, n["roles"], n["not_judged"], n["awaiting_review"]))
    names = C.target_names(config)
    for r in run["roles"][:10]:
        print("  %5.1f  %-9s %-9s %-14s %s" % (r["fit"], r["interview_band"], r["offer_band"],
                                              names.get(r["org"], r["org"])[:14], r["title"]))
    for w in run["warnings"]:
        print("WARNING: " + w, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(C.run_main(main))
