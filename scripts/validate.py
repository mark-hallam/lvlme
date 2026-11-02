#!/usr/bin/env python3
"""Check a workspace: every file against its schema, plus cross-file links.

Refuses (exit code 2) a workspace inside the engine repo (except the fictional
demo under examples/) or inside any git repository that has a remote.

Schema checks use a small hand-written validator for the subset of JSON
Schema the engine's schemas use: type, enum, const, properties, required,
additionalProperties, patternProperties, items, minItems, maxItems,
minLength, maxLength, pattern, minimum, maximum, exclusiveMinimum, anyOf and
local $ref. Keys starting x_ (extension fields) are allowed on the main
objects through patternProperties and are never read by the engine.

Also checks the review dispute logs, eval/reviews/<date>.json
(schemas/reviews.schema.json), against the middle-of-three rule.

Usage
  python3 scripts/validate.py --workspace PATH [--json]
Exit codes: 0 valid (warnings allowed), 1 errors found, 2 refused location.
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402
import score as S  # noqa: E402  (the evidence caps, so the warnings match the scoring)

FILES = [
    ("config.json", "config.schema.json", True),
    ("profile/evidence.json", "evidence.schema.json", True),
    ("profile/network.json", "network.schema.json", False),
    ("profile/claims-audit.json", "claims-audit.schema.json", False),
    ("market/roles/latest.json", "roles.schema.json", False),
    ("market/orgs.json", "orgs.schema.json", False),
    ("eval/judgements.json", "judgements.schema.json", True),
    ("eval/profile-dimensions.json", "profile-dimensions.schema.json", True),
    ("eval/gap-templates.json", "gap-templates.schema.json", False),
    ("eval/outlook.json", "outlook.schema.json", False),
    ("eval/swot.json", "swot.schema.json", False),
    ("eval/ceilings.json", "ceilings.schema.json", False),
    ("campaign/plan.json", "plan.schema.json", True),
]

# ------------------------------------------------------------ the validator


def _resolve(root, ref):
    if not ref.startswith("#/"):
        raise ValueError("only local $ref values are supported: %s" % ref)
    node = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def _type_ok(value, t):
    if t == "object":
        return isinstance(value, dict)
    if t == "array":
        return isinstance(value, list)
    if t == "string":
        return isinstance(value, str)
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "boolean":
        return isinstance(value, bool)
    if t == "null":
        return value is None
    return False


def _same(a, b):
    """Equality that keeps True and 1 apart."""
    return type(a) is type(b) and a == b or (a is None and b is None)


def _show(value):
    text = json.dumps(value, ensure_ascii=False)
    return text if len(text) <= 60 else text[:57] + "..."


def check(value, schema, root=None, path="$"):
    """Validate value against schema. Returns a list of error strings."""
    root = root if root is not None else schema
    errors = []
    _check(value, schema, root, path, errors)
    return errors


def _check(x, s, root, path, errs):
    while "$ref" in s:
        s = _resolve(root, s["$ref"])
    if "anyOf" in s and not any(not check(x, sub, root, path) for sub in s["anyOf"]):
        errs.append("%s: %s does not match any of the allowed forms" % (path, _show(x)))
    if "const" in s and not _same(x, s["const"]):
        errs.append("%s: must be %s" % (path, _show(s["const"])))
    if "enum" in s and not any(_same(x, e) for e in s["enum"]):
        errs.append("%s: %s is not one of %s" % (path, _show(x), ", ".join(_show(e) for e in s["enum"])))
    if "type" in s:
        types = s["type"] if isinstance(s["type"], list) else [s["type"]]
        if not any(_type_ok(x, t) for t in types):
            errs.append("%s: expected %s, got %s" % (path, " or ".join(types), _show(x)))
            return
    if isinstance(x, dict):
        props = s.get("properties") or {}
        patterns = s.get("patternProperties") or {}
        for key in s.get("required") or []:
            if key not in x:
                errs.append("%s: missing required field '%s'" % (path, key))
        extra = s.get("additionalProperties", True)
        for key, val in x.items():
            sub = "%s.%s" % (path, key)
            matched = [p for p in patterns if re.search(p, key)]
            for p in matched:
                _check(val, patterns[p], root, sub, errs)
            if key in props:
                _check(val, props[key], root, sub, errs)
            elif matched:
                continue
            elif extra is False:
                errs.append("%s: unexpected field '%s'" % (path, key))
            elif isinstance(extra, dict):
                _check(val, extra, root, sub, errs)
    if isinstance(x, list):
        if "minItems" in s and len(x) < s["minItems"]:
            errs.append("%s: needs at least %d items" % (path, s["minItems"]))
        if "maxItems" in s and len(x) > s["maxItems"]:
            errs.append("%s: allows at most %d items" % (path, s["maxItems"]))
        if "items" in s:
            for i, item in enumerate(x):
                _check(item, s["items"], root, "%s[%d]" % (path, i), errs)
    if isinstance(x, str):
        if "minLength" in s and len(x) < s["minLength"]:
            errs.append("%s: must not be empty" % path if s["minLength"] == 1
                        else "%s: shorter than %d characters" % (path, s["minLength"]))
        if "maxLength" in s and len(x) > s["maxLength"]:
            errs.append("%s: longer than %d characters" % (path, s["maxLength"]))
        if "pattern" in s and not re.search(s["pattern"], x):
            errs.append("%s: %s does not match the pattern %s" % (path, _show(x), s["pattern"]))
    if _type_ok(x, "number"):
        if "minimum" in s and x < s["minimum"]:
            errs.append("%s: %s is below the minimum %s" % (path, x, s["minimum"]))
        if "maximum" in s and x > s["maximum"]:
            errs.append("%s: %s is above the maximum %s" % (path, x, s["maximum"]))
        if "exclusiveMinimum" in s and x <= s["exclusiveMinimum"]:
            errs.append("%s: %s must be more than %s" % (path, x, s["exclusiveMinimum"]))

# --------------------------------------------------------- cross-file checks


def _dups(ids):
    seen, out = set(), set()
    for i in ids:
        (out if i in seen else seen).add(i)
    return sorted(out)


def cross_checks(ws, docs, errors, warnings):
    cfg = docs.get("config.json") or {}
    if "config.json" in docs and C.setup_problem(cfg):
        errors.append(C.setup_problem(cfg))
    ev = docs.get("profile/evidence.json") or {}
    ev_ids = {e.get("id") for e in ev.get("items", [])}
    targets = C.target_ids(cfg)
    fams = [f.get("id") for f in cfg.get("families", [])]
    classes = [c.get("id") for c in (cfg.get("locations") or {}).get("classes", [])]

    for label, ids in (("target", targets), ("family", fams), ("location class", classes),
                       ("evidence", [e.get("id") for e in ev.get("items", [])]),
                       ("open question", [q.get("id") for q in ev.get("open_questions", [])])):
        for d in _dups(ids):
            errors.append("duplicate %s id %s" % (label, d))
    if "default" in targets:
        errors.append("config.json: 'default' is reserved and cannot be a target id")
    evidence_checks(cfg, ev, warnings)
    weights = C.weights_of(cfg)
    if sum(weights.values()) != 100:
        warnings.append("config.json: weights add up to %d, not 100 (fit is rescaled to 100)" % sum(weights.values()))

    def cite(where, ids):
        for eid in ids or []:
            if eid not in ev_ids:
                errors.append("%s cites evidence %s, which is not in profile/evidence.json" % (where, eid))

    for q in ev.get("open_questions", []):
        cite("open question %s" % q.get("id"), q.get("answer_evidence"))

    roles_doc = docs.get("market/roles/latest.json")
    role_ids = {r.get("id") for r in (roles_doc or {}).get("roles", [])}
    for r in (roles_doc or {}).get("roles", []):
        if r.get("org") not in targets:
            warnings.append("market/roles/latest.json: role %s belongs to %s, not a current target"
                            % (r.get("id"), r.get("org")))
        if r.get("family") not in fams:
            warnings.append("market/roles/latest.json: role %s has family %s, not in config.json (re-run fetch_roles.py)"
                            % (r.get("id"), r.get("family")))

    jud = (docs.get("eval/judgements.json") or {}).get("roles", {})
    for rid, j in jud.items():
        for d in ("D1", "D2", "D4"):
            cite("eval/judgements.json %s %s" % (rid, d), (j.get(d) or {}).get("evidence"))
        if roles_doc is not None and rid not in role_ids:
            warnings.append("eval/judgements.json: %s is no longer an open role (kept for history)" % rid)

    prof = docs.get("eval/profile-dimensions.json") or {}
    for section in ("D3", "D5", "D7"):
        for key, entry in (prof.get(section) or {}).items():
            if key != "default" and key not in targets:
                errors.append("eval/profile-dimensions.json: %s has an entry for '%s', not a target id" % (section, key))
            cite("eval/profile-dimensions.json %s %s" % (section, key), entry.get("evidence"))
    rules = prof.get("D6_rules") or {}
    default_class = (cfg.get("locations") or {}).get("default_class") or "other"
    for key, entry in (rules.get("classes") or {}).items():
        if key not in classes and key != default_class:
            warnings.append("eval/profile-dimensions.json: D6 rule for '%s', not a location class in config.json" % key)
        cite("eval/profile-dimensions.json D6 rule %s" % key, entry.get("evidence"))
    for key in classes + [default_class]:
        if key not in (rules.get("classes") or {}):
            warnings.append("eval/profile-dimensions.json: no D6 rule for location class '%s' (scores 0)" % key)
    cite("eval/profile-dimensions.json D6 blocked", (rules.get("blocked") or {}).get("evidence"))

    gap_ids = {g.get("id") for g in (docs.get("eval/gap-templates.json") or {}).get("gaps", [])}

    plan = docs.get("campaign/plan.json") or {}
    actions = plan.get("actions", [])
    action_ids = {a.get("id") for a in actions}
    metric_ids = {m.get("id") for m in plan.get("north_star", [])}
    for d in _dups([a.get("id") for a in actions]):
        errors.append("campaign/plan.json: duplicate action id %s" % d)
    for m in plan.get("north_star", []):
        cite("campaign/plan.json metric %s" % m.get("id"), m.get("evidence"))
    active = [a for a in actions if a.get("status") in C.ACTIVE_STATUSES]
    cap = int(plan.get("max_active", 8))
    if len(active) > cap:
        warnings.append("campaign/plan.json: %d active actions (to do or in progress), more than the cap of %d. "
                        "Park the lowest priority ones as status later, or move them to the backlog."
                        % (len(active), cap))

    swot = docs.get("eval/swot.json")
    strat_ids = set()
    if swot is not None:
        grids = [("overall", swot.get("overall") or {})] + sorted((swot.get("per_org") or {}).items())
        item_ids = set()
        for scope, grid in grids:
            if scope != "overall" and scope not in targets:
                errors.append("eval/swot.json: per_org has '%s', not a target id" % scope)
            ids = []
            for quad in ("strengths", "weaknesses", "opportunities", "threats"):
                for item in grid.get(quad, []):
                    ids.append(item.get("id"))
                    if quad in ("strengths", "weaknesses"):
                        cite("eval/swot.json %s %s" % (scope, item.get("id")), item.get("evidence"))
                        if not item.get("evidence"):
                            errors.append("eval/swot.json: %s %s has no evidence (strengths and weaknesses need it)"
                                          % (scope, item.get("id")))
            for d in _dups(ids):
                errors.append("eval/swot.json: duplicate id %s in %s" % (d, scope))
            item_ids.update(ids)
        for d in _dups([s.get("id") for s in swot.get("strategies", [])]):
            errors.append("eval/swot.json: duplicate strategy id %s" % d)
        for s in swot.get("strategies", []):
            sid, kind = s.get("id"), s.get("type") or ""
            strat_ids.add(sid)
            uses = s.get("uses") or []
            letters = {u[:1] for u in uses}
            for u in uses:
                if u not in item_ids:
                    errors.append("eval/swot.json: strategy %s uses %s, which is not in the grid" % (sid, u))
            if kind and not (set(kind) <= letters and letters <= set(kind)):
                errors.append("eval/swot.json: strategy %s is %s, so it must use at least one %s item and one %s item "
                              "and nothing else" % (sid, kind, kind[0], kind[1]))
            if sid and kind and not sid.startswith(kind):
                errors.append("eval/swot.json: strategy %s should start with its type %s" % (sid, kind))
            if scope_bad(s.get("scope"), targets):
                errors.append("eval/swot.json: strategy %s has scope '%s', not 'overall' or a target id"
                              % (sid, s.get("scope")))
            for aid in s.get("actions") or []:
                if plan and aid not in action_ids:
                    errors.append("eval/swot.json: strategy %s names action %s, which is not in campaign/plan.json"
                                  % (sid, aid))

    for a in actions:
        aid = a.get("id")
        if a.get("status") == "done" and not (a.get("done_evidence") or "").strip():
            errors.append("campaign/plan.json: action %s is done but has no done_evidence (a link, file or email)" % aid)
        for sid in a.get("strategy_ids") or []:
            if swot is not None and sid not in strat_ids:
                errors.append("campaign/plan.json: action %s names strategy %s, which is not in eval/swot.json" % (aid, sid))
        if a.get("metric") and a["metric"] not in metric_ids:
            errors.append("campaign/plan.json: action %s moves metric %s, which is not a north-star metric"
                          % (aid, a["metric"]))
        if a.get("gap_id") and gap_ids and a["gap_id"] not in gap_ids:
            warnings.append("campaign/plan.json: action %s points at gap %s, not in eval/gap-templates.json"
                            % (aid, a["gap_id"]))
        if a.get("draft") and not os.path.exists(C.wpath(ws, a["draft"])):
            warnings.append("campaign/plan.json: action %s names draft %s, which does not exist" % (aid, a["draft"]))
        for e in a.get("effects") or []:
            effect_checks(aid, e, targets, fams, classes + [default_class], errors, warnings)

    net = docs.get("profile/network.json")
    for org in (net or {}).get("orgs", {}):
        if org not in targets:
            warnings.append("profile/network.json: org %s is not a current target (re-run network_map.py)" % org)
    claims = (docs.get("profile/claims-audit.json") or {}).get("claims", [])
    for d in _dups([c.get("id") for c in claims]):
        errors.append("profile/claims-audit.json: duplicate claim id %s" % d)
    for c in claims:
        cite("profile/claims-audit.json %s" % c.get("id"), c.get("evidence"))
    for org in ((docs.get("market/orgs.json") or {}).get("orgs") or {}):
        if org not in targets:
            warnings.append("market/orgs.json: %s is not a target id" % org)
    for r in (docs.get("eval/ceilings.json") or {}).get("roles", []):
        if r.get("org") not in targets:
            warnings.append("eval/ceilings.json: role %s belongs to %s, not a target id" % (r.get("role_id"), r.get("org")))
    review_checks(docs, ev_ids, errors, warnings)


# Evidence id prefixes LVLme already uses for other ids, so an evidence id with one reads as something else.
RESERVED_PREFIXES = {"D": "the factor codes D1 to D7", "A": "plan actions (A01)", "Q": "open questions (Q01)"}


def evidence_checks(cfg, ev, warnings):
    """Evidence ids with a confusing prefix, and partially verified items that support less than self-reported ones."""
    scoring = cfg.get("scoring") or {}
    self_caps = dict(S.DEFAULT_SELF_CAPS, **(scoring.get("self_reported_caps") or {}))
    partial = int(scoring.get("partially_verified_cap", S.DEFAULT_PARTIAL_CAP))
    for e in ev.get("items", []):
        eid, kind = e.get("id") or "", e.get("kind") or "other"
        prefix = re.match(r"^[A-Z]*", eid).group(0)
        if prefix in RESERVED_PREFIXES:
            warnings.append("profile/evidence.json: evidence id %s starts with %s, which LVLme uses for %s; prefer E "
                            "(or another prefix) so it is not misread" % (eid, prefix, RESERVED_PREFIXES[prefix]))
        if e.get("level") == "partially_verified":
            mine = S.level_cap("partially_verified", kind, self_caps, partial)
            theirs = S.level_cap("self_reported", kind, self_caps, partial)
            if mine < theirs:
                warnings.append("profile/evidence.json: %s is partially_verified, which supports at most %d for %s "
                                "evidence, less than self_reported (%d). Record it as self_reported, or verified "
                                "once the rest is checked." % (eid, mine, kind.replace("_", " "), theirs))


def review_checks(docs, ev_ids, errors, warnings):
    """eval/reviews/<date>.json: the file date, the middle-of-three rule, cited evidence and the judgement files."""
    jud = (docs.get("eval/judgements.json") or {}).get("roles", {})
    prof = docs.get("eval/profile-dimensions.json") or {}
    for rel in sorted(k for k in docs if k.startswith("eval/reviews/")):
        doc, day = docs[rel], os.path.basename(rel)[:-5]
        if doc.get("date") != day:
            errors.append("%s: date %s does not match the file name" % (rel, doc.get("date")))
        for n, d in enumerate(doc.get("disputes") or []):
            item = d.get("item_id", "")
            where = "%s dispute %d (%s)" % (rel, n + 1, item)
            s, r, t = (d.get(k) or {} for k in ("scorer", "reviewer", "tie_break"))
            scores = [x.get("score") for x in (s, r, t) if "score" in x]
            for who, x in (("scorer", s), ("reviewer", r), ("tie-break", t)):
                for eid in x.get("evidence") or []:
                    if eid not in ev_ids:
                        errors.append("%s: the %s cites evidence %s, which is not in profile/evidence.json" % (where, who, eid))
            if s.get("score") == r.get("score"):
                warnings.append("%s: the scorer and the reviewer agree, so it is not a dispute" % where)
            how, stands = d.get("decided_by"), d.get("stands")
            if how == "middle_of_three":
                if "score" not in t:
                    errors.append("%s: decided by the middle of three, but there is no tie-break score" % where)
                elif stands != sorted(scores)[1]:
                    errors.append("%s: the middle of %s is %d, but %s stands" % (where, scores, sorted(scores)[1], stands))
                for who, x in (("scorer", s), ("reviewer", r), ("tie-break", t)):
                    if x and not x.get("anchor"):
                        warnings.append("%s: the %s's score names no rubric anchor" % (where, who))
            elif how == "awaiting_tie_break" and "score" in t:
                errors.append("%s: awaiting a tie-break, but a tie-break score is recorded (use middle_of_three)" % where)
            elif how == "earlier_rule" and stands not in scores:
                warnings.append("%s: %s stands, which none of the recorded scores gave" % (where, stands))
            entry, container = review_entry(item, jud, prof)
            when = d.get("date") or day
            if entry is None:
                warnings.append("%s: no such judgement entry in eval/judgements.json or eval/profile-dimensions.json" % where)
                continue
            judged = entry.get("judged_on") or container.get("judged_on") or ""
            reviewed = entry.get("reviewed_on") or container.get("reviewed_on") or ""
            if judged > when:
                continue  # judged again since this review: the dispute is history
            if how == "middle_of_three" and entry.get("score") != stands:
                warnings.append("%s: %s stands, but the judgement file has %s" % (where, stands, entry.get("score")))
            if how == "middle_of_three" and reviewed < when:
                warnings.append("%s: decided, but the judgement entry has no reviewed_on on or after %s" % (where, when))
            if how == "awaiting_tie_break" and reviewed >= when:
                warnings.append("%s: still awaiting a tie-break, but the judgement entry is marked reviewed on %s"
                                % (where, reviewed))


def review_entry(item_id, jud, prof):
    """(entry, the object that holds its fallback judged_on and reviewed_on) for a review item id, or (None, None)."""
    m = re.match(r"^(D[3567])/([a-z0-9_]+)$", item_id or "")
    if m:
        dim, key = m.groups()
        sec = ((prof.get("D6_rules") or {}).get("classes") or {}) if dim == "D6" else (prof.get(dim) or {})
        return (sec.get(key), prof) if key in sec else (None, None)
    m = re.match(r"^(.+)/(D[124])$", item_id or "")
    if m and m.group(1) in jud and m.group(2) in jud[m.group(1)]:
        return jud[m.group(1)][m.group(2)], jud[m.group(1)]
    return None, None


def effect_checks(aid, e, targets, fams, classes, errors, warnings):
    """One plan action effect: exactly one of delta or set_at_least, and a scope that names known ids."""
    where = "campaign/plan.json: action %s effect on %s" % (aid, e.get("dimension"))
    if ("delta" in e) == ("set_at_least" in e):
        errors.append("%s needs exactly one of delta or set_at_least" % where)
    scope = e.get("scope") or {}
    for key, known in (("orgs", targets), ("families", fams), ("location_classes", classes)):
        for v in scope.get(key) or []:
            if v not in known:
                warnings.append("%s names %s '%s', not in config.json" % (where, key.replace("_", " "), v))


def scope_bad(scope, targets):
    return scope is not None and scope != "overall" and scope not in targets

# --------------------------------------------------------------------- main


def validate_workspace(ws):
    """Return (errors, warnings, checked files) for a workspace."""
    errors, warnings, checked, docs = [], [], [], {}
    entries = list(FILES) + [(os.path.relpath(p, ws), "run.schema.json", False)
                             for p in sorted(glob.glob(C.wpath(ws, "eval", "runs", "*.json")))]
    entries += [(os.path.relpath(p, ws), "reviews.schema.json", False)
                for p in sorted(glob.glob(C.wpath(ws, "eval", "reviews", "*.json")))]
    for rel, schema_name, required in entries:
        path = C.wpath(ws, rel)
        if not os.path.exists(path):
            if required:
                errors.append("%s: missing (run scripts/init.py to create the skeleton)" % rel)
            continue
        try:
            data = C.load_json(path)
        except ValueError as exc:
            errors.append("%s: not valid JSON (%s)" % (rel, exc))
            continue
        schema = C.load_json(os.path.join(C.SCHEMA_DIR, schema_name))
        errors.extend("%s: %s" % (rel, e) for e in check(data, schema))
        docs[rel] = data
        checked.append(rel)
    cross_checks(ws, docs, errors, warnings)
    return errors, warnings, checked


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate a LVLme workspace.")
    ap.add_argument("--workspace", help="workspace folder (default: $LVLME_HOME)")
    ap.add_argument("--json", action="store_true", help="print the result as JSON")
    args = ap.parse_args(argv)
    try:
        ws = C.resolve_workspace(args.workspace)
    except C.WorkspaceError as exc:
        print("lvlme: %s" % exc, file=sys.stderr)
        return 1
    problem = C.location_problem(ws)
    if problem:
        if args.json:
            print(json.dumps({"workspace": ws, "ok": False, "refused": problem}, indent=2))
        else:
            print("lvlme: refused. " + problem, file=sys.stderr)
        return 2
    errors, warnings, checked = validate_workspace(ws)
    if args.json:
        print(json.dumps({"workspace": ws, "ok": not errors, "errors": errors, "warnings": warnings,
                          "checked_files": checked}, indent=2, ensure_ascii=False))
    else:
        print("Checked %d files in %s" % (len(checked), ws))
        for e in errors:
            print("ERROR   " + e)
        for w in warnings:
            print("WARNING " + w)
        print("Valid." if not errors else "%d error(s) found." % len(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
