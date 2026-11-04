"""Keep a factor's score when only the AI that judged it changed (rubric 1.1, change B6).

Two AI agents can read the same evidence and score it a point apart. When a role's D1, D2 or D4 is judged
again by a different agent, and the evidence cited for it is exactly what it was at the previous run, the
previous score stands (up or down) and the run says so. When the evidence changed, the new score is used.
A judgement without a recorded agent, or a previous run without a fingerprint, works exactly as before.

    >>> label({"agent": "Codex"})
    'Codex'
    >>> label({"agent": "Claude Code", "model": "claude-opus-5-5"})
    'Claude Code (claude-opus-5-5)'
    >>> label(None)
    ''
"""
import glob
import hashlib
import json
import os

import _common as C
import _public_link as PL

DIMS = ("D1", "D2", "D4")


def label(judged_by):
    """A short, stable name for the agent (and model) that judged, or '' when it was not recorded."""
    agent = ((judged_by or {}).get("agent") or "").strip()
    model = ((judged_by or {}).get("model") or "").strip()
    return "%s (%s)" % (agent, model) if agent and model else agent


def fingerprint(evidence_by_id, ids):
    """A short hash of the cited evidence: each id with its level (after the public link rule) and claim."""
    rows = []
    for eid in sorted(set(ids or [])):
        item = evidence_by_id.get(eid)
        rows.append([eid, PL.effective_level(item) if item else None, (item or {}).get("claim")])
    raw = json.dumps(rows, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()[:16]


def previous_scores(ws, run_date):
    """{role id: {dimension: score dict}} from the latest run before run_date, or {} when there is none."""
    runs = sorted(p for p in glob.glob(C.wpath(ws, "eval", "runs", "*.json"))
                  if os.path.basename(p)[:-5] < run_date)
    if not runs:
        return {}
    run = C.load_json(runs[-1], {}) or {}
    return {r["role_id"]: {d: r["scores"][d] for d in DIMS if d in (r.get("scores") or {})}
            for r in run.get("roles") or [] if r.get("judged")}


def apply(ctx, rid, dim, scored):
    """Stamp the fingerprint and the judge on one D1, D2 or D4 score; keep the previous score when only the
    judge changed. Returns True when the previous score was kept."""
    scored["evidence_fingerprint"] = fingerprint(ctx.evidence, scored.get("evidence"))
    if ctx.judge_label:
        scored["judged_by"] = ctx.judge_label
    prev = (ctx.previous.get(rid) or {}).get(dim)
    if not (prev and ctx.judge_label and prev.get("judged_by") and prev.get("evidence_fingerprint")):
        return False
    if prev["judged_by"] == ctx.judge_label or prev["evidence_fingerprint"] != scored["evidence_fingerprint"]:
        return False
    if prev["score"] == scored["score"]:
        return False
    new = scored["score"]
    scored.update(score=prev["score"], raw=prev.get("raw", prev["score"]))
    scored.pop("capped", None)
    if prev.get("capped"):
        scored["capped"] = prev["capped"]
    scored["judge_changed"] = {"previous_score": prev["score"], "new_score": new, "previous_judge": prev["judged_by"],
                               "new_judge": ctx.judge_label, "kept": "previous"}
    line = ("The score for %s %s was kept at %d: only the judge changed (%s to %s), the evidence did not."
            % (rid, dim, prev["score"], prev["judged_by"], ctx.judge_label))
    scored["note"] = (scored.get("note") + " " if scored.get("note") else "") + line
    ctx.warn(line)
    return True
